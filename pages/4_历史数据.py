import pandas as pd
import streamlit as st

from core.alarm_events import build_alarm_events
from core.config import CONDITION_LABELS, DEVICE_ID
from core.database import (
    ensure_demo_device,
    init_db,
    query_alarms,
    query_running,
)
from core.diagnosis import diagnose
from core.metrics import calculate_health_score
from core.report import generate_running_report
from utils.charts import (
    alarm_distribution_chart,
    alarm_timeline_chart,
    trend_chart,
)
from utils.ui import (
    empty_panel,
    metric_grid,
    page_header,
    section_header,
)

init_db()
ensure_demo_device()

running = query_running(5000, ascending=True)

if running.empty:
    page_header(
        "数据中心",
        "运行趋势、报警统计与数据导出",
        status_label="等待数据",
        status_tone="neutral",
        meta=f"{DEVICE_ID} · 暂无历史记录",
    )
    empty_panel(
        "暂无历史运行数据",
        "进入运行监测生成模拟数据后，可按日期和工况查询、统计并导出。",
    )
    st.stop()

running["timestamp"] = pd.to_datetime(running["timestamp"])
min_date = running["timestamp"].min().date()
max_date = running["timestamp"].max().date()

page_header(
    "数据中心",
    "按日期与工况追溯运行和报警记录",
    status_label=f"{len(running)} 条记录",
    status_tone="info",
    meta=(
        f"{DEVICE_ID} · 数据范围 {min_date.isoformat()} 至 "
        f"{max_date.isoformat()}"
    ),
)

with st.container(border=True):
    section_header(
        "查询条件",
        kicker="DATA FILTER",
        note="筛选结果同步用于图表和 CSV",
    )
    filter_col1, filter_col2 = st.columns([1.35, 1], gap="medium")
    with filter_col1:
        date_range = st.date_input(
            "日期范围",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
    with filter_col2:
        condition_options = ["全部"] + sorted(
            running["condition"].dropna().unique()
        )
        condition = st.selectbox(
            "工况筛选",
            condition_options,
            format_func=lambda key: (
                "全部工况"
                if key == "全部"
                else CONDITION_LABELS.get(key, key)
            ),
        )

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

filtered = running[
    (running["timestamp"].dt.date >= start_date)
    & (running["timestamp"].dt.date <= end_date)
]
if condition != "全部":
    filtered = filtered[filtered["condition"] == condition]

alarms = query_alarms(
    5000,
    start_date=start_date,
    end_date=end_date,
)
events = build_alarm_events(alarms, running)
unprocessed_count = (
    int((alarms["status"] != "已关闭").sum()) if not alarms.empty else 0
)
abnormal_count = int((filtered["status"] != "正常").sum())

metric_grid(
    [
        {
            "label": "筛选运行记录",
            "value": len(filtered),
            "helper": "当前查询范围",
            "tone": "blue",
        },
        {
            "label": "异常采样",
            "value": abnormal_count,
            "helper": "状态非正常",
            "tone": "warn" if abnormal_count else "good",
        },
        {
            "label": "报警记录",
            "value": len(events),
            "helper": "所选日期范围",
            "tone": "warn" if len(events) else "good",
        },
        {
            "label": "未处理报警",
            "value": unprocessed_count,
            "helper": "待处置事件",
            "tone": "danger" if unprocessed_count else "good",
        },
        {
            "label": "数据起始",
            "value": str(start_date),
            "helper": "筛选开始日期",
            "tone": "neutral",
        },
        {
            "label": "数据截止",
            "value": str(end_date),
            "helper": "筛选结束日期",
            "tone": "neutral",
        },
    ]
)

report_key = (
    str(start_date),
    str(end_date),
    str(condition),
)
if st.session_state.get("report_key") != report_key:
    st.session_state.pop("running_report_pdf", None)

report_col, report_hint_col = st.columns([1, 3])
with report_col:
    generate_report = st.button(
        "生成运行报告 PDF",
        icon=":material/picture_as_pdf:",
        type="primary",
        width="stretch",
        key="generate_report",
    )
with report_hint_col:
    st.caption(
        "报告包含筛选周期摘要、当前诊断、报警事件和最新优化建议。"
    )

if generate_report:
    latest_records = query_running(3, ascending=True).to_dict("records")
    latest_diagnosis = (
        diagnose(latest_records)
        if latest_records
        else {
            "rule_id": "-",
            "alarm_type": "正常",
            "level": "正常",
            "message": "暂无运行数据",
            "suggestion": "-",
            "evidence": [],
        }
    )
    health_score = calculate_health_score(
        latest_records[-1]["status"] if latest_records else "待采集",
        latest_diagnosis,
        unprocessed_count,
    )
    report_pdf = generate_running_report(
        device_id=DEVICE_ID,
        start_date=start_date,
        end_date=end_date,
        running=filtered,
        alarm_events=events,
        diagnosis=latest_diagnosis,
        health_score=health_score,
        optimization=st.session_state.get("optimization_result"),
    )
    st.session_state["running_report_pdf"] = report_pdf
    st.session_state["report_key"] = report_key
    st.success("运行报告已生成。")

if st.session_state.get("running_report_pdf"):
    st.download_button(
        "下载运行报告 PDF",
        data=st.session_state["running_report_pdf"],
        file_name=(
            f"smart_pump_report_{start_date}_{end_date}.pdf"
        ),
        mime="application/pdf",
        icon=":material/download:",
        type="primary",
    )

if filtered.empty:
    empty_panel(
        "当前条件无运行数据",
        "扩大日期范围或选择“全部工况”后重新查询。",
    )
else:
    with st.container(border=True):
        section_header(
            "运行趋势",
            kicker="TREND ANALYSIS",
            note=f"{len(filtered)} 条筛选结果",
        )
        fig = trend_chart(filtered)
        if fig:
            st.plotly_chart(
                fig,
                width="stretch",
                config={"displayModeBar": False},
            )

chart_col, alarm_col = st.columns([1.2, 1], gap="medium")
with chart_col:
    with st.container(border=True):
        section_header("报警时间分布", kicker="ALARM TIMELINE")
        alarm_timeline = alarm_timeline_chart(alarms)
        if alarm_timeline:
            st.plotly_chart(
                alarm_timeline,
                width="stretch",
                config={"displayModeBar": False},
            )
        else:
            empty_panel("暂无报警", "所选日期范围内没有报警记录。")

with alarm_col:
    with st.container(border=True):
        section_header("报警类型统计", kicker="ALARM MIX")
        alarm_mix = alarm_distribution_chart(alarms)
        if alarm_mix:
            st.plotly_chart(
                alarm_mix,
                width="stretch",
                config={"displayModeBar": False},
            )
        else:
            empty_panel("暂无报警", "所选日期范围内没有报警记录。")

run_tab, alarm_tab = st.tabs(["运行记录", "报警记录"])

with run_tab:
    with st.container(border=True):
        section_header(
            "历史运行数据",
            kicker="RUNNING DATA",
            note=f"共 {len(filtered)} 条",
        )
        st.dataframe(
            filtered.sort_values("timestamp", ascending=False),
            width="stretch",
            hide_index=True,
        )
        running_csv = filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "导出运行数据 CSV",
            data=running_csv,
            file_name="running_data.csv",
            mime="text/csv",
            icon=":material/download:",
            disabled=filtered.empty,
        )

with alarm_tab:
    with st.container(border=True):
        section_header(
            "历史报警记录",
            kicker="ALARM DATA",
            note=f"共 {len(events)} 个事件",
        )
        if events.empty:
            empty_panel("暂无报警记录", "所选日期范围内没有报警。")
        else:
            event_display = events.copy()
            for column in ("event_start", "event_end"):
                event_display[column] = pd.to_datetime(
                    event_display[column]
                ).dt.strftime("%Y-%m-%d %H:%M:%S")
            st.dataframe(
                event_display[
                    [
                        "timestamp",
                        "rule_id",
                        "alarm_type",
                        "level",
                        "duration_minutes",
                        "peak_current",
                        "peak_load",
                        "min_production",
                        "status",
                        "handled_by",
                        "handled_at",
                    ]
                ],
                width="stretch",
                hide_index=True,
            )
        alarm_csv = events.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "导出报警记录 CSV",
            data=alarm_csv,
            file_name="alarm_data.csv",
            mime="text/csv",
            icon=":material/download:",
            disabled=events.empty,
        )

st.caption(
    "CSV 使用 UTF-8 BOM 编码，可直接用 Microsoft Excel 打开。"
)

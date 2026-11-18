import streamlit as st

from core.config import (
    CONDITION_LABELS,
    DEVICE_ID,
    DIAGNOSIS_WINDOW_SIZE,
    LOCATION,
    MAX_HISTORY,
)
from core.database import (
    ensure_demo_device,
    init_db,
    query_alarms,
    query_running,
)
from core.diagnosis import diagnose, evaluate_rules
from core.indicator import indicator_curve, pump_metrics
from core.scenario import SCENARIO_STEPS, run_scenario, scenario_summary
from core.service import ingest_sample
from core.simulator import generate_data
from utils.charts import indicator_diagram_chart, trend_chart
from utils.ui import (
    alert_list,
    diagnosis_block,
    empty_panel,
    metric_grid,
    page_header,
    rule_cards,
    section_header,
)

init_db()
ensure_demo_device()

history = query_running(MAX_HISTORY, ascending=True)
latest_df = query_running(1)
alarms = query_alarms(50)

if latest_df.empty:
    status_label = "等待数据"
    status_tone = "neutral"
    meta = f"{DEVICE_ID} · {LOCATION}"
else:
    latest = latest_df.iloc[0]
    status_label = (
        "运行正常"
        if str(latest["status"]) == "正常"
        else f"设备{latest['status']}"
    )
    status_tone = "good" if str(latest["status"]) == "正常" else "danger"
    meta = f"{DEVICE_ID} · {LOCATION} · 最近采样 {latest['timestamp']}"

page_header(
    "运行监测",
    "工况模拟、实时指标与设备状态",
    status_label=status_label,
    status_tone=status_tone,
    meta=meta,
)

if "condition" not in st.session_state:
    st.session_state.condition = "normal"

condition_keys = list(CONDITION_LABELS)
with st.container(border=True):
    section_header(
        "工况模拟器",
        kicker="SIMULATION CONTROL",
        note="每次生成 1 条 1 分钟模拟采样",
    )
    selected = st.radio(
        "选择模拟工况",
        options=condition_keys,
        format_func=lambda key: CONDITION_LABELS[key],
        horizontal=True,
        index=condition_keys.index(st.session_state.condition),
        label_visibility="collapsed",
    )
    st.session_state.condition = selected

    action_col, hint_col = st.columns([1, 3])
    with action_col:
        generate_clicked = st.button(
            "生成模拟数据",
            type="primary",
            icon=":material/add_chart:",
            width="stretch",
            key="manual_generate",
        )
    with hint_col:
        st.caption(
            f"连续异常判断窗口 {DIAGNOSIS_WINDOW_SIZE} 条；"
            "同一连续事件只生成一条报警。"
        )

    st.markdown("---")
    scenario_col1, scenario_col2, scenario_col3 = st.columns([1, 1, 1.4])
    scenario_index = int(st.session_state.get("scenario_step_index", 0))
    with scenario_col1:
        scenario_step_clicked = st.button(
            "单步演示",
            icon=":material/skip_next:",
            width="stretch",
            key="scenario_step",
        )
    with scenario_col2:
        scenario_full_clicked = st.button(
            "一键完整演示",
            icon=":material/play_circle:",
            width="stretch",
            key="scenario_full",
        )
    with scenario_col3:
        step_preview = SCENARIO_STEPS[
            scenario_index % len(SCENARIO_STEPS)
        ]
        st.caption(
            f"场景进度 {scenario_index}/{len(SCENARIO_STEPS)} · "
            f"下一步：{step_preview['label']}"
        )
    with st.expander("查看一键演示脚本"):
        st.dataframe(
            scenario_summary(),
            width="stretch",
            hide_index=True,
        )

if generate_clicked:
    latest_before = query_running(1)
    energy_before = (
        float(latest_before.iloc[0]["energy"]) if not latest_before.empty else 0.0
    )
    record = generate_data(st.session_state.condition, energy_before)
    outcome = ingest_sample(record)
    if outcome["alarm_created"]:
        st.toast(
            f'已创建报警 {outcome["diagnosis"]["rule_id"]} · '
            f'{outcome["diagnosis"]["alarm_type"]}',
            icon=":material/notification_important:",
        )
    else:
        st.toast("模拟数据已写入数据库", icon=":material/check_circle:")
    st.rerun()

if scenario_step_clicked:
    latest_before = query_running(1)
    energy_before = (
        float(latest_before.iloc[0]["energy"]) if not latest_before.empty else 0.0
    )
    step = SCENARIO_STEPS[scenario_index % len(SCENARIO_STEPS)]
    record = generate_data(step["condition"], energy_before)
    outcome = ingest_sample(record)
    st.session_state.scenario_step_index = (
        scenario_index + 1
    ) % len(SCENARIO_STEPS)
    alarm_text = (
        f"，新增报警 {outcome['diagnosis']['rule_id']}"
        if outcome["alarm_created"]
        else ""
    )
    st.session_state["demo_notice"] = (
        f"完成场景步骤：{step['label']}{alarm_text}"
    )
    st.rerun()

if scenario_full_clicked:
    summary = run_scenario()
    st.session_state.scenario_step_index = 0
    st.session_state["demo_notice"] = (
        f"完整场景已生成：{summary['sample_count']} 条采样，"
        f"新增 {summary['alarm_count']} 条报警。"
    )
    st.rerun()

if st.session_state.get("demo_notice"):
    st.success(st.session_state.pop("demo_notice"))

latest_df = query_running(1)
history = query_running(MAX_HISTORY, ascending=True)
alarms = query_alarms(50)

if latest_df.empty:
    empty_panel(
        "暂无运行数据",
        "选择上方工况并生成第一条模拟数据，系统会同步更新看板、诊断和报警。",
    )
    st.stop()

latest = latest_df.iloc[0]
records = history.to_dict("records")
diagnosis = diagnose(records)

metric_grid(
    [
        {
            "label": "设备状态",
            "value": latest["status"],
            "helper": f"采样 {latest['timestamp'][11:]}",
            "tone": "good" if latest["status"] == "正常" else "danger",
        },
        {
            "label": "当前冲次",
            "value": f'{latest["stroke_rate"]:.2f} 次/min',
            "helper": "运行频率",
            "tone": "blue",
        },
        {
            "label": "电机电流",
            "value": f'{latest["motor_current"]:.2f} A',
            "helper": "电机电流",
            "tone": "blue",
        },
        {
            "label": "负载率",
            "value": f'{latest["load"]:.2f} %',
            "helper": "模拟负载率",
            "tone": "warn" if float(latest["load"]) >= 85 else "good",
        },
        {
            "label": "模拟产量",
            "value": f'{latest["production"]:.2f} m³/d',
            "helper": "当日模拟产量",
            "tone": "good",
        },
        {
            "label": "功率",
            "value": f'{latest["power"]:.2f} kW',
            "helper": "瞬时功率",
            "tone": "warn",
        },
        {
            "label": "累计能耗",
            "value": f'{latest["energy"]:.3f} kWh',
            "helper": "数据库续接累加",
            "tone": "blue",
        },
    ]
)

with st.container(border=True):
    section_header(
        "运行指标趋势",
        kicker="TREND",
        note=(
            f"最近 {len(records)} 条 · 连续窗口 "
            f"{min(len(records), DIAGNOSIS_WINDOW_SIZE)}/"
            f"{DIAGNOSIS_WINDOW_SIZE}"
        ),
    )
    trend_tab, indicator_tab = st.tabs(["运行趋势", "示功图分析"])
    with trend_tab:
        sample_window = st.radio(
            "显示范围",
            options=[20, 50, 100],
            index=1,
            format_func=lambda value: f"最近 {value} 条",
            horizontal=True,
            label_visibility="collapsed",
        )
        visible_history = history.tail(int(sample_window or 50))
        fig = trend_chart(visible_history, alarms)
        if fig:
            st.plotly_chart(
                fig,
                width="stretch",
                config={"displayModeBar": False},
            )
    with indicator_tab:
        metrics = pump_metrics(latest)
        condition_label = CONDITION_LABELS.get(
            str(latest["condition"]),
            str(latest["condition"]),
        )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("模拟泵效", f'{metrics["pump_efficiency"]:.1f}%')
        m2.metric("充满系数", f'{metrics["fill_factor"]:.1f}%')
        m3.metric("冲次利用率", f'{metrics["stroke_utilization"]:.1f}%')
        m4.metric("产量基准比", f'{metrics["production_ratio"]:.1f}%')
        indicator_fig = indicator_diagram_chart(
            indicator_curve(latest),
            condition_label,
        )
        st.plotly_chart(
            indicator_fig,
            width="stretch",
            config={"displayModeBar": False},
        )
        st.caption(
            "示功图、泵效和充满系数均为课程设计模拟计算，不代表真实泵况。"
        )

diagnosis_col, alarm_col = st.columns([1, 1.25], gap="medium")
rule_cards(evaluate_rules(records))
with diagnosis_col:
    with st.container(border=True):
        section_header("当前诊断", kicker="DIAGNOSIS")
        diagnosis_block(
            f'{diagnosis["rule_id"]} · {diagnosis["alarm_type"]}',
            diagnosis["message"],
            tone=(
                "danger"
                if diagnosis.get("level") == "高"
                else "warning"
                if diagnosis["has_alarm"]
                else "good"
            ),
        )
        if diagnosis.get("evidence"):
            st.dataframe(
                [
                    {
                        "指标": item["label"],
                        "当前值": f'{item["value"]} {item["unit"]}',
                        "阈值": f'{item["threshold"]} {item["unit"]}',
                        "命中": f'{item["hits"]}/{item["window_size"]}',
                        "结论": "满足" if item["passed"] else "未满足",
                    }
                    for item in diagnosis["evidence"]
                ],
                width="stretch",
                hide_index=True,
            )
        st.markdown(f'**建议**  \n{diagnosis["suggestion"]}')
        st.caption(f'采样时间：{latest["timestamp"]}')

with alarm_col:
    with st.container(border=True):
        section_header(
            "最近报警",
            kicker="RECENT EVENTS",
            note=f"共 {len(alarms)} 条",
        )
        alert_list(alarms, limit=5)

st.caption(
    "模拟数据与规则阈值仅用于课程演示，不连接真实设备，不能用于现场控制。"
)

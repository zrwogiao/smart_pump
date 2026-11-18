import streamlit as st

from core.alarm_events import build_alarm_events
from core.config import (
    CONDITION_LABELS,
    DEVICE_ID,
    DIAGNOSIS_WINDOW_SIZE,
    LOCATION,
)
from core.database import query_alarms, query_running
from core.diagnosis import diagnose
from core.indicator import indicator_curve, pump_metrics
from core.metrics import calculate_health_score, operating_efficiency
from utils.charts import (
    alarm_distribution_chart,
    alarm_timeline_chart,
    condition_donut,
    dashboard_trend_chart,
    health_gauge,
    indicator_diagram_chart,
)
from utils.ui import (
    alert_list,
    diagnosis_block,
    empty_panel,
    metric_grid,
    page_header,
    section_header,
)

history = query_running(200, ascending=True)
alarms = query_alarms(200)
all_running = query_running(5000, ascending=True)

if history.empty:
    page_header(
        "运行驾驶舱",
        "抽油机模拟运行总览与异常态势",
        status_label="等待数据",
        status_tone="neutral",
        meta=f"{DEVICE_ID} · {LOCATION} · 模拟数据",
    )
    empty_panel(
        "尚未建立运行记录",
        "进入“运行监测”生成第一条模拟数据后，驾驶舱会自动展示指标和报警态势。",
    )
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.page_link(
            "pages/1_运行总览.py",
            label="生成运行数据",
            icon=":material/add_chart:",
        )
    with p2:
        st.page_link(
            "pages/2_智能诊断.py",
            label="查看诊断中心",
            icon=":material/rule:",
        )
    with p3:
        st.page_link(
            "pages/3_运行优化.py",
            label="进入优化工作台",
            icon=":material/tune:",
        )
    with p4:
        st.page_link(
            "pages/4_历史数据.py",
            label="打开数据中心",
            icon=":material/table_chart:",
        )
    st.stop()

records = history.to_dict("records")
result = diagnose(records)
latest = records[-1]
unprocessed_alarms = (
    int((alarms["status"] != "已关闭").sum()) if not alarms.empty else 0
)
events = build_alarm_events(alarms, all_running)
health = calculate_health_score(
    latest["status"],
    result,
    unprocessed_alarms,
)
efficiency = operating_efficiency(
    latest["production"],
    latest["power"],
)

if result["has_alarm"] and result["level"] == "高":
    status_label = "存在高等级异常"
    status_tone = "danger"
elif result["has_alarm"] or str(latest["status"]) != "正常":
    status_label = "运行需要关注"
    status_tone = "warning"
else:
    status_label = "系统运行正常"
    status_tone = "good"

page_header(
    "运行驾驶舱",
    "设备指标、健康状态与报警态势的统一视图",
    status_label=status_label,
    status_tone=status_tone,
    meta=f"{DEVICE_ID} · {LOCATION} · 最近采样 {latest['timestamp']}",
)

metric_grid(
    [
        {
            "label": "设备状态",
            "value": latest["status"],
            "helper": "最新采样状态",
            "tone": "good" if latest["status"] == "正常" else "danger",
        },
        {
            "label": "电机电流",
            "value": f'{latest["motor_current"]:.2f} A',
            "helper": "当前电流负载",
            "tone": "blue",
        },
        {
            "label": "负载率",
            "value": f'{latest["load"]:.1f} %',
            "helper": "电机负载水平",
            "tone": "warn" if float(latest["load"]) >= 85 else "good",
        },
        {
            "label": "模拟产量",
            "value": f'{latest["production"]:.2f} m³/d',
            "helper": f"单位功率产量 {efficiency:.2f}",
            "tone": "good",
        },
        {
            "label": "瞬时功率",
            "value": f'{latest["power"]:.2f} kW',
            "helper": "当前模拟功率",
            "tone": "warn",
        },
        {
            "label": "累计能耗",
            "value": f'{latest["energy"]:.3f} kWh',
            "helper": "按 1 分钟采样累加",
            "tone": "blue",
        },
    ]
)

left, right = st.columns([1.85, 1], gap="medium")
with left:
    with st.container(border=True):
        section_header(
            "运行趋势",
            kicker="OPERATIONS",
            note=f"最近 {min(len(records), 40)} 条采样",
        )
        fig = dashboard_trend_chart(history, alarms)
        if fig:
            st.plotly_chart(
                fig,
                width="stretch",
                config={"displayModeBar": False},
            )

with right:
    with st.container(border=True):
        section_header("运行健康度", kicker="HEALTH")
        st.plotly_chart(
            health_gauge(health),
            width="stretch",
            config={"displayModeBar": False},
        )
        diagnosis_block(
            f'{result["rule_id"]} · {result["alarm_type"]}',
            result["message"],
            tone=(
                "danger"
                if result.get("level") == "高"
                else "warning"
                if result["has_alarm"]
                else "good"
            ),
        )
        st.caption(
            f"连续规则窗口 "
            f"{min(len(records), DIAGNOSIS_WINDOW_SIZE)}/"
            f"{DIAGNOSIS_WINDOW_SIZE} 条"
        )

trend_col, composition_col = st.columns([1.35, 1], gap="medium")
with trend_col:
    with st.container(border=True):
        section_header(
            "报警态势",
            kicker="ALARM TIMELINE",
            note=f"未处理 {unprocessed_alarms} 条",
        )
        alarm_fig = alarm_timeline_chart(alarms)
        if alarm_fig:
            st.plotly_chart(
                alarm_fig,
                width="stretch",
                config={"displayModeBar": False},
            )
        else:
            empty_panel(
                "暂无报警",
                "生成异常工况数据后，将在此显示报警时间分布。",
            )

with composition_col:
    with st.container(border=True):
        section_header("工况与机理", kicker="CONDITION / INDICATOR")
        condition_tab, indicator_tab = st.tabs(["工况构成", "示功图"])
        with condition_tab:
            condition_fig = condition_donut(history)
            if condition_fig:
                st.plotly_chart(
                    condition_fig,
                    width="stretch",
                    config={"displayModeBar": False},
                )
        with indicator_tab:
            curve = indicator_curve(latest)
            metrics = pump_metrics(latest)
            st.plotly_chart(
                indicator_diagram_chart(
                    curve,
                    CONDITION_LABELS.get(
                        str(latest["condition"]),
                        str(latest["condition"]),
                    ),
                ),
                width="stretch",
                config={"displayModeBar": False},
            )
            st.caption(
                f'模拟泵效 {metrics["pump_efficiency"]:.1f}% · '
                f'充满系数 {metrics["fill_factor"]:.1f}% · '
                f'产量基准比 {metrics["production_ratio"]:.1f}%'
            )

alarm_col, entry_col = st.columns([1.5, 1], gap="medium")
with alarm_col:
    with st.container(border=True):
        section_header(
            "最近报警",
            kicker="RECENT EVENTS",
            note=f"共 {len(alarms)} 条记录",
        )
        alert_list(events, limit=6)

with entry_col:
    with st.container(border=True):
        section_header("快捷入口", kicker="WORKSPACES")
        st.page_link(
            "pages/1_运行总览.py",
            label="运行监测",
            icon=":material/monitoring:",
        )
        st.page_link(
            "pages/2_智能诊断.py",
            label="诊断中心",
            icon=":material/rule:",
        )
        st.page_link(
            "pages/3_运行优化.py",
            label="优化工作台",
            icon=":material/tune:",
        )
        st.page_link(
            "pages/4_历史数据.py",
            label="数据中心",
            icon=":material/table_chart:",
        )
        st.caption("所有页面共享同一运行与报警数据库。")

if not alarms.empty and alarms["alarm_type"].nunique() > 1:
    with st.container(border=True):
        section_header("报警类型分布", kicker="ALARM MIX")
        distribution_fig = alarm_distribution_chart(alarms)
        if distribution_fig:
            st.plotly_chart(
                distribution_fig,
                width="stretch",
                config={"displayModeBar": False},
            )

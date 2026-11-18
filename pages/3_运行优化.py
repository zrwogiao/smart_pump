import pandas as pd
import streamlit as st

from core.config import (
    CONDITION_LABELS,
    DEVICE_ID,
    DIAGNOSIS_WINDOW_SIZE,
    LOCATION,
    MAX_STROKE,
    MIN_STROKE,
)
from core.database import ensure_demo_device, init_db, query_running
from core.diagnosis import diagnose
from core.optimizer import (
    OBJECTIVES,
    build_quick_plans,
    optimize,
    search_optimization,
)
from utils.charts import comparison_chart, pareto_chart
from utils.ui import (
    condition_banner,
    empty_panel,
    metric_grid,
    page_header,
    plan_cards,
    section_header,
)

init_db()
ensure_demo_device()

latest_df = query_running(1)
if latest_df.empty:
    page_header(
        "优化工作台",
        "冲次调整与能耗产量方案模拟",
        status_label="等待数据",
        status_tone="neutral",
        meta=f"{DEVICE_ID} · {LOCATION}",
    )
    empty_panel(
        "暂无运行数据",
        "先生成一条模拟采样，优化工作台会以最新运行指标作为输入。",
    )
    st.stop()

latest = latest_df.iloc[0]
current_stroke_default = min(
    MAX_STROKE,
    max(MIN_STROKE, float(latest["stroke_rate"])),
)
target_stroke_default = max(MIN_STROKE, round(current_stroke_default - 1.0, 1))

# 页面输入控件状态：数据更新时重置；一键方案载入时覆盖默认参数。
input_ts = str(latest["timestamp"])
if st.session_state.get("opt_input_ts") != input_ts:
    st.session_state["opt_input_ts"] = input_ts
    st.session_state["opt_current_stroke"] = current_stroke_default
    st.session_state["opt_target_stroke"] = target_stroke_default
    st.session_state["opt_current_power"] = max(0.1, float(latest["power"]))
    st.session_state["opt_current_production"] = float(latest["production"])
    st.session_state["opt_objective"] = OBJECTIVES[0]

pending_plan = st.session_state.pop("pending_quick_plan", None)
if pending_plan:
    st.session_state["applied_quick_plan"] = pending_plan
    st.session_state["opt_target_stroke"] = float(pending_plan["target_stroke"])
    st.session_state["opt_objective"] = pending_plan["objective"]

page_header(
    "优化工作台",
    "基于当前工况的一键方案与冲次参数模拟",
    status_label="参数可调整",
    status_tone="info",
    meta=f"{DEVICE_ID} · 最近采样 {latest['timestamp']}",
)

metric_grid(
    [
        {
            "label": "当前冲次",
            "value": f'{latest["stroke_rate"]:.2f} 次/min',
            "helper": "优化输入基准",
            "tone": "blue",
        },
        {
            "label": "当前功率",
            "value": f'{latest["power"]:.2f} kW',
            "helper": "瞬时功率",
            "tone": "warn",
        },
        {
            "label": "模拟产量",
            "value": f'{latest["production"]:.2f} m³/d',
            "helper": "当前产量",
            "tone": "good",
        },
        {
            "label": "累计能耗",
            "value": f'{latest["energy"]:.3f} kWh',
            "helper": "运行累计值",
            "tone": "blue",
        },
    ]
)

records = query_running(
    max(DIAGNOSIS_WINDOW_SIZE * 2, 10),
    ascending=True,
).to_dict("records")
diagnosis = diagnose(records)
quick = build_quick_plans(
    float(latest["stroke_rate"]),
    float(latest["power"]),
    float(latest["production"]),
    condition=str(latest["condition"]),
    diagnosis=diagnosis,
)

banner_tone = (
    "danger"
    if diagnosis.get("has_alarm") and diagnosis.get("level") == "高"
    else "warning"
    if diagnosis.get("has_alarm")
    else "good"
)
condition_banner(
    f'{diagnosis["rule_id"]} · {quick["condition_label"]}',
    f'当前工况判定：{quick["condition_label"]}',
    quick["summary"],
    tone=banner_tone,
)

with st.container(border=True):
    section_header(
        "一键优化方案",
        kicker="QUICK PLANS",
        note="按当前工况生成 · 点击卡片下方按钮查看预计效果",
    )
    clicked_plan_id = plan_cards(quick["plans"], key_prefix="quickplan")
    st.caption(quick["notice"])

if clicked_plan_id:
    applied = next(
        plan for plan in quick["plans"] if plan["plan_id"] == clicked_plan_id
    )
    st.session_state["pending_quick_plan"] = applied
    st.rerun()

applied = st.session_state.get("applied_quick_plan")
if applied and applied.get("expected"):
    expected = applied["expected"]
    st.success(
        f'已载入方案「{applied["name"]}」：目标冲次 '
        f'{applied["target_stroke"]:.1f} 次/min（{applied["objective"]}）。'
    )
    metric_grid(
        [
            {
                "label": "方案目标冲次",
                "value": f'{applied["target_stroke"]:.1f} 次/min',
                "helper": applied["objective"],
                "tone": "blue",
            },
            {
                "label": "预计功率",
                "value": f'{expected["optimized_power"]:.2f} kW',
                "helper": f'变化 {expected["power_change_pct"]:+.2f}%',
                "tone": (
                    "good"
                    if expected["power_change_pct"] <= 0
                    else "warn"
                ),
            },
            {
                "label": "预计日能耗",
                "value": f'{expected["optimized_energy"]:.2f} kWh',
                "helper": f'基准 {expected["current_energy"]:.2f} kWh',
                "tone": (
                    "good"
                    if expected["optimized_energy"] <= expected["current_energy"]
                    else "warn"
                ),
            },
            {
                "label": "预计产量",
                "value": f'{expected["optimized_production"]:.2f} m³/d',
                "helper": (
                    f'保留率 {expected["production_retention"] * 100:.1f}%'
                ),
                "tone": (
                    "good"
                    if expected["production_change_pct"] >= 0
                    else "warn"
                ),
            },
        ]
    )

    effect_col, detail_col = st.columns([1.4, 1], gap="medium")
    with effect_col:
        with st.container(border=True):
            section_header(
                f'{applied["name"]} · 预计效果对比',
                kicker="EXPECTED IMPACT",
                note=applied["reason"],
            )
            st.plotly_chart(
                comparison_chart(
                    expected["current_power"],
                    expected["optimized_power"],
                    expected["current_production"],
                    expected["optimized_production"],
                ),
                width="stretch",
                config={"displayModeBar": False},
                key="quick_plan_comparison_chart",
            )
    with detail_col:
        with st.container(border=True):
            section_header("预计效果明细", kicker="PROJECTION")
            effect_df = pd.DataFrame(
                [
                    [
                        "功率（kW）",
                        expected["current_power"],
                        expected["optimized_power"],
                        f'{expected["power_change_pct"]:+.2f}%',
                    ],
                    [
                        "日能耗（kWh）",
                        expected["current_energy"],
                        expected["optimized_energy"],
                        f'{(
                            expected["optimized_energy"] / expected["current_energy"] - 1
                        ) * 100:+.2f}%' if expected["current_energy"] else "-",
                    ],
                    [
                        "模拟产量（m³/d）",
                        expected["current_production"],
                        expected["optimized_production"],
                        f'{expected["production_change_pct"]:+.2f}%',
                    ],
                    [
                        "日耗电节省（kWh）",
                        0.0,
                        expected["daily_saving_kwh"],
                        "节能" if expected["daily_saving_kwh"] >= 0 else "增耗",
                    ],
                ],
                columns=["指标", "基准", "预计", "变化"],
            )
            st.dataframe(effect_df, width="stretch", hide_index=True)
            if st.button(
                "清除一键方案",
                key="clear_quick_plan",
                icon=":material/close:",
            ):
                st.session_state.pop("applied_quick_plan", None)
                st.rerun()

with st.container(border=True):
    section_header(
        "自定义优化参数",
        kicker="SCENARIO INPUT",
        note="一键方案已自动载入参数，可在此微调后重新模拟",
    )
    input_left, input_right = st.columns(2, gap="large")
    with input_left:
        current_stroke = st.number_input(
            "当前冲次（次/min）",
            min_value=float(MIN_STROKE),
            max_value=float(MAX_STROKE),
            key="opt_current_stroke",
            step=0.1,
        )
        target_stroke = st.number_input(
            "目标冲次（次/min）",
            min_value=float(MIN_STROKE),
            max_value=float(MAX_STROKE),
            key="opt_target_stroke",
            step=0.1,
        )
    with input_right:
        current_power = st.number_input(
            "当前功率（kW）",
            min_value=0.1,
            max_value=100.0,
            key="opt_current_power",
            step=0.1,
        )
        current_production = st.number_input(
            "当前模拟产量（m³/d）",
            min_value=0.0,
            max_value=100.0,
            key="opt_current_production",
            step=0.1,
        )

    objective = st.radio(
        "优化目标",
        options=OBJECTIVES,
        index=0,
        key="opt_objective",
        horizontal=True,
    )
    action_col1, action_col2 = st.columns(2)
    with action_col1:
        optimize_clicked = st.button(
            "单点模拟",
            type="secondary",
            icon=":material/tune:",
            width="stretch",
            key="optimize_single",
        )
    with action_col2:
        search_clicked = st.button(
            "方案搜索与推荐",
            type="primary",
            icon=":material/search:",
            width="stretch",
            key="optimize_search",
        )

if optimize_clicked:
    try:
        result = optimize(
            current_stroke,
            target_stroke,
            current_power,
            current_production,
            objective or OBJECTIVES[0],
        )
        st.session_state["optimization_result"] = result
    except ValueError as exc:
        st.error(str(exc))

if search_clicked:
    try:
        search_result = search_optimization(
            current_stroke,
            current_power,
            current_production,
            objective or OBJECTIVES[0],
        )
        st.session_state["optimization_search"] = search_result
    except ValueError as exc:
        st.error(str(exc))

search_result = st.session_state.get("optimization_search")
if search_result and search_result.get("recommended"):
    recommended = search_result["recommended"]
    metric_grid(
        [
            {
                "label": "推荐目标冲次",
                "value": f'{recommended["target_stroke"]:.2f} 次/min',
                "helper": search_result["objective"],
                "tone": "blue",
            },
            {
                "label": "推荐后功率",
                "value": f'{recommended["optimized_power"]:.2f} kW',
                "helper": f'变化 {recommended["power_change_pct"]:+.2f}%',
                "tone": (
                    "good"
                    if recommended["power_change_pct"] <= 0
                    else "warn"
                ),
            },
            {
                "label": "推荐后产量",
                "value": f'{recommended["optimized_production"]:.2f} m³/d',
                "helper": (
                    f'保留率 '
                    f'{recommended["production_retention"] * 100:.1f}%'
                ),
                "tone": "good",
            },
            {
                "label": "方案评分",
                "value": f'{recommended["score"]:.1f}',
                "helper": search_result["constraint_text"],
                "tone": "good",
            },
        ]
    )

    search_chart_col, search_table_col = st.columns(
        [1.45, 1],
        gap="medium",
    )
    with search_chart_col:
        with st.container(border=True):
            section_header(
                "方案搜索空间",
                kicker="PARETO SEARCH",
                note=f'{len(search_result["feasible"])} 个可行方案',
            )
            pareto_fig = pareto_chart(
                search_result["candidates"],
                recommended,
            )
            if pareto_fig:
                st.plotly_chart(
                    pareto_fig,
                    width="stretch",
                    config={"displayModeBar": False},
                    key="search_pareto_chart",
                )
    with search_table_col:
        with st.container(border=True):
            section_header(
                "推荐候选方案",
                kicker="RANKED OPTIONS",
            )
            ranked = sorted(
                search_result["feasible"],
                key=lambda item: item["score"],
                reverse=True,
            )[:8]
            candidate_df = pd.DataFrame(
                [
                    {
                        "冲次": item["target_stroke"],
                        "功率": item["optimized_power"],
                        "产量": item["optimized_production"],
                        "评分": item["score"],
                    }
                    for item in ranked
                ]
            )
            st.dataframe(
                candidate_df,
                width="stretch",
                hide_index=True,
            )
            st.info(recommended["recommendation"])

result = st.session_state.get("optimization_result")
if result:
    metric_grid(
        [
            {
                "label": "优化后功率",
                "value": f'{result["optimized_power"]:.2f} kW',
                "helper": f'变化 {result["power_change_pct"]:+.2f}%',
                "tone": "good" if result["power_change_pct"] <= 0 else "warn",
            },
            {
                "label": "优化后日能耗",
                "value": f'{result["optimized_energy"]:.2f} kWh',
                "helper": f'优化前 {result["current_energy"]:.2f} kWh',
                "tone": (
                    "good"
                    if result["optimized_energy"] <= result["current_energy"]
                    else "warn"
                ),
            },
            {
                "label": "优化后产量",
                "value": f'{result["optimized_production"]:.2f} m³/d',
                "helper": f'变化 {result["production_change_pct"]:+.2f}%',
                "tone": "good" if result["production_change_pct"] >= 0 else "warn",
            },
            {
                "label": "目标冲次",
                "value": f'{result["target_stroke"]:.2f} 次/min',
                "helper": result["objective"],
                "tone": "blue",
            },
        ]
    )

    chart_col, advice_col = st.columns([1.55, 1], gap="medium")
    with chart_col:
        with st.container(border=True):
            section_header(
                f'{result["objective"]}方案对比',
                kicker="BEFORE / AFTER",
            )
            fig = comparison_chart(
                result["current_power"],
                result["optimized_power"],
                result["current_production"],
                result["optimized_production"],
            )
            st.plotly_chart(
                fig,
                width="stretch",
                config={"displayModeBar": False},
                key="single_optimize_comparison_chart",
            )

    with advice_col:
        with st.container(border=True):
            section_header("方案评估", kicker="RECOMMENDATION")
            st.markdown(result["recommendation"])
            compare_df = pd.DataFrame(
                [
                    [
                        "功率（kW）",
                        result["current_power"],
                        result["optimized_power"],
                        f'{result["power_change_pct"]:+.2f}%',
                    ],
                    [
                        "日能耗（kWh）",
                        result["current_energy"],
                        result["optimized_energy"],
                        f'{(result["optimized_energy"] / result["current_energy"] - 1) * 100:+.2f}%',
                    ],
                    [
                        "模拟产量（m³/d）",
                        result["current_production"],
                        result["optimized_production"],
                        f'{result["production_change_pct"]:+.2f}%',
                    ],
                ],
                columns=["指标", "优化前", "优化后", "变化"],
            )
            st.dataframe(
                compare_df,
                width="stretch",
                hide_index=True,
            )

st.caption(
    "优化结果由简化公式生成，仅用于课程演示，不会下发或控制真实设备。"
)

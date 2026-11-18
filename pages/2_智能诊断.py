import pandas as pd
import streamlit as st

from core.alarm_events import build_alarm_events
from core.config import DEVICE_ID, DIAGNOSIS_WINDOW_SIZE, LOCATION
from core.database import (
    ensure_demo_device,
    init_db,
    query_alarms,
    query_running,
    update_alarm_status,
)
from core.diagnosis import diagnose, evaluate_rules
from utils.charts import alarm_distribution_chart
from utils.ui import (
    diagnosis_block,
    empty_panel,
    metric_grid,
    page_header,
    rule_cards,
    section_header,
)


def display_text(value, fallback=""):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    return str(value)


init_db()
ensure_demo_device()

history = query_running(
    limit=max(DIAGNOSIS_WINDOW_SIZE * 2, 10),
    ascending=True,
)
all_running = query_running(5000, ascending=True)
alarms = query_alarms(500)

if history.empty:
    page_header(
        "诊断中心",
        "规则判断、证据链与报警事件闭环",
        status_label="等待数据",
        status_tone="neutral",
        meta=f"{DEVICE_ID} · {LOCATION}",
    )
    empty_panel(
        "暂无诊断所需数据",
        "进入运行监测生成模拟采样后，诊断中心会展示当前规则判断。",
    )
    st.stop()

records = history.to_dict("records")
window = records[-DIAGNOSIS_WINDOW_SIZE:]
result = diagnose(records)
rules = evaluate_rules(records)
latest = records[-1]
events = build_alarm_events(alarms, all_running)
active_alarms = (
    alarms[alarms["status"] != "已关闭"] if not alarms.empty else alarms
)

if result["has_alarm"] and result["level"] == "高":
    status_label = "高等级异常"
    status_tone = "danger"
elif result["has_alarm"]:
    status_label = "中等级异常"
    status_tone = "warning"
else:
    status_label = "诊断正常"
    status_tone = "good"

page_header(
    "诊断中心",
    "规则证据、报警事件与处置状态",
    status_label=status_label,
    status_tone=status_tone,
    meta=f"{DEVICE_ID} · 最近采样 {latest['timestamp']}",
)

metric_grid(
    [
        {
            "label": "当前规则",
            "value": result["rule_id"],
            "helper": result["alarm_type"],
            "tone": (
                "danger"
                if result.get("level") == "高"
                else "warn"
                if result["has_alarm"]
                else "good"
            ),
        },
        {
            "label": "报警等级",
            "value": result["level"],
            "helper": "当前诊断结果",
            "tone": "danger" if result.get("level") == "高" else "warn",
        },
        {
            "label": "活动报警",
            "value": int(len(active_alarms)),
            "helper": "未关闭事件",
            "tone": "warn" if len(active_alarms) else "good",
        },
        {
            "label": "报警事件",
            "value": len(events),
            "helper": "连续异常过程",
            "tone": "blue",
        },
        {
            "label": "判断窗口",
            "value": f"{len(window)}/{DIAGNOSIS_WINDOW_SIZE}",
            "helper": "连续采样证据",
            "tone": "blue",
        },
        {
            "label": "电机电流",
            "value": f'{latest["motor_current"]:.2f} A',
            "helper": "当前采样",
            "tone": "blue",
        },
    ]
)

section_header(
    "规则证据链",
    kicker="RULE ENGINE",
    note="R01/R02 使用连续采样窗口",
)
rule_cards(rules)

detail_col, mix_col = st.columns([1.45, 1], gap="medium")
with detail_col:
    with st.container(border=True):
        section_header(
            "当前诊断",
            kicker="CURRENT FINDING",
            note=latest["timestamp"],
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
        st.markdown(f'**处理建议**  \n{result["suggestion"]}')

        evidence = result.get("evidence") or []
        if evidence:
            evidence_df = pd.DataFrame(
                [
                    {
                        "指标": item["label"],
                        "当前值": f'{item["value"]} {item["unit"]}',
                        "阈值": f'{item["threshold"]} {item["unit"]}',
                        "连续命中": f'{item["hits"]}/{item["window_size"]}',
                        "结论": "满足" if item["passed"] else "未满足",
                    }
                    for item in evidence
                ]
            )
            st.dataframe(
                evidence_df,
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption("当前没有触发规则，所有规则均处于正常范围。")

with mix_col:
    with st.container(border=True):
        section_header(
            "报警类型分布",
            kicker="ALARM MIX",
            note=f"共 {len(events)} 个事件",
        )
        mix_fig = alarm_distribution_chart(alarms)
        if mix_fig:
            st.plotly_chart(
                mix_fig,
                width="stretch",
                config={"displayModeBar": False},
            )
        else:
            empty_panel("暂无报警", "当前没有可用于统计的报警记录。")

with st.container(border=True):
    section_header(
        "报警事件日志",
        kicker="EVENT LEDGER",
        note=f"共 {len(events)} 个事件 · 活动 {len(active_alarms)} 个",
    )
    if events.empty:
        empty_panel("暂无报警事件", "设备正常运行时通常不会产生报警。")
    else:
        status_counts = events["status"].value_counts()
        st.caption(
            f"状态概览 · 未处理 {int(status_counts.get('未处理', 0))} / "
            f"处理中 {int(status_counts.get('处理中', 0))} / "
            f"已关闭 {int(status_counts.get('已关闭', 0))}"
        )

        filter_a, filter_b, filter_c, filter_d = st.columns([1, 1, 1, 1.6])
        with filter_a:
            status_filter = st.selectbox(
                "处理状态",
                options=["全部", "未处理", "处理中", "已关闭"],
                key="ledger_status",
            )
        with filter_b:
            level_filter = st.selectbox(
                "等级",
                options=["全部", "高", "中", "低"],
                key="ledger_level",
            )
        with filter_c:
            rule_filter = st.selectbox(
                "规则",
                options=["全部"]
                + sorted(str(v) for v in events["rule_id"].dropna().unique()),
                key="ledger_rule",
            )
        with filter_d:
            keyword = st.text_input(
                "关键词检索",
                placeholder="类型 / 编号 / 处理人 / 备注",
                key="ledger_keyword",
            )

        filtered_events = events.copy()
        if status_filter != "全部":
            filtered_events = filtered_events[
                filtered_events["status"] == status_filter
            ]
        if level_filter != "全部":
            filtered_events = filtered_events[
                filtered_events["level"] == level_filter
            ]
        if rule_filter != "全部":
            filtered_events = filtered_events[
                filtered_events["rule_id"] == rule_filter
            ]
        keyword_clean = keyword.strip()
        if keyword_clean:
            needle = keyword_clean.lower()
            searchable = ["alarm_type", "rule_id", "handled_by", "handling_note"]
            mask = pd.Series(False, index=filtered_events.index)
            for field in searchable:
                mask = mask | (
                    filtered_events[field]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(needle, regex=False)
                )
            filtered_events = filtered_events[mask]

        if filtered_events.empty:
            empty_panel("没有匹配的报警事件", "调整筛选条件或清空关键词后重试。")
        else:
            display_df = pd.DataFrame(
                {
                    "编号": filtered_events["alarm_id"].astype(int).values,
                    "触发时间": pd.to_datetime(
                        filtered_events["timestamp"]
                    ).dt.strftime("%Y-%m-%d %H:%M").values,
                    "规则": filtered_events["rule_id"].values,
                    "报警类型": filtered_events["alarm_type"].values,
                    "等级": filtered_events["level"].values,
                    "持续(min)": (
                        filtered_events["duration_minutes"]
                        .fillna(0).astype(int).values
                    ),
                    "峰值电流": (
                        filtered_events["peak_current"].fillna(0).round(2).values
                    ),
                    "峰值负载%": (
                        filtered_events["peak_load"].fillna(0).round(2).values
                    ),
                    "状态": filtered_events["status"].values,
                    "处理人": [
                        display_text(v, "-")
                        for v in filtered_events["handled_by"]
                    ],
                }
            )

            table_key = "alarm_table_" + str(
                abs(hash((status_filter, level_filter, rule_filter, keyword_clean)))
            )
            selection = st.dataframe(
                display_df,
                width="stretch",
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=table_key,
                column_config={
                    "编号": st.column_config.NumberColumn("编号", width="small"),
                    "触发时间": st.column_config.TextColumn("触发时间", width="medium"),
                    "规则": st.column_config.TextColumn("规则", width="small"),
                    "报警类型": st.column_config.TextColumn("报警类型", width="medium"),
                    "等级": st.column_config.TextColumn(
                        "等级",
                        width="small",
                        help="高 / 中 / 低",
                    ),
                    "持续(min)": st.column_config.NumberColumn(
                        "持续(min)", format="%d", width="small"
                    ),
                    "峰值电流": st.column_config.NumberColumn(
                        "峰值电流(A)", format="%.2f", width="small"
                    ),
                    "峰值负载%": st.column_config.NumberColumn(
                        "峰值负载(%)", format="%.2f", width="small"
                    ),
                    "状态": st.column_config.TextColumn(
                        "处置状态",
                        width="small",
                        help="未处理 / 处理中 / 已关闭",
                    ),
                    "处理人": st.column_config.TextColumn("处理人", width="medium"),
                },
            )
            st.caption(
                f"显示 {len(display_df)} / {len(events)} 个事件 · "
                "点击表格中的一行即可在下方查看并处置该事件"
            )

            selected_rows = []
            if selection is not None:
                sel = getattr(selection, "selection", None)
                if sel is not None:
                    if hasattr(sel, "get"):
                        selected_rows = list(sel.get("rows", []))
                    else:
                        selected_rows = list(getattr(sel, "rows", []))
            if selected_rows:
                clicked_id = int(display_df.iloc[selected_rows[0]]["编号"])
                st.session_state["selected_alarm_id"] = clicked_id

            valid_ids = set(display_df["编号"].tolist())
            selected_alarm_id = st.session_state.get("selected_alarm_id")
            if selected_alarm_id not in valid_ids:
                selected_alarm_id = int(display_df.iloc[0]["编号"])
                st.session_state["selected_alarm_id"] = selected_alarm_id
            selected_event = events[
                events["alarm_id"] == selected_alarm_id
            ].iloc[0]

            st.markdown("---")
            section_header(
                f'#{int(selected_alarm_id)} · {selected_event["rule_id"]} · '
                f'{selected_event["alarm_type"]}',
                kicker="SELECTED EVENT",
                note=f'当前状态：{selected_event["status"]}',
            )

            event_left, event_right = st.columns([1, 1], gap="medium")
            with event_left:
                st.markdown("**事件指标**")
                e1, e2 = st.columns(2)
                e1.metric(
                    "持续时间",
                    f'{selected_event["duration_minutes"]} 分钟',
                )
                e2.metric(
                    "峰值电流",
                    f'{float(selected_event["peak_current"]):.2f} A'
                    if pd.notna(selected_event["peak_current"])
                    else "-",
                )
                e3, e4 = st.columns(2)
                e3.metric(
                    "峰值负载率",
                    f'{float(selected_event["peak_load"]):.2f} %'
                    if pd.notna(selected_event["peak_load"])
                    else "-",
                )
                e4.metric(
                    "最低产量",
                    f'{float(selected_event["min_production"]):.2f} m³/d'
                    if pd.notna(selected_event["min_production"])
                    else "-",
                )
                st.caption(
                    f'事件时间：{selected_event["event_start"]} 至 '
                    f'{selected_event["event_end"]}'
                )
            with event_right:
                st.markdown("**当前处置信息**")
                st.write(f'状态：**{selected_event["status"]}**')
                st.write(
                    f'处理人：{display_text(selected_event["handled_by"], "未填写")}'
                )
                st.write(
                    f'处理备注：{display_text(selected_event["handling_note"], "暂无")}'
                )
                st.write(
                    f'处理时间：{display_text(selected_event["handled_at"], "未处理")}'
                )

            quick_a, quick_b, quick_c = st.columns(3)
            with quick_a:
                if st.button(
                    "标记处理中",
                    key="quick_status_processing",
                    icon=":material/play_arrow:",
                    width="stretch",
                ):
                    update_alarm_status(int(selected_alarm_id), "处理中")
                    st.rerun()
            with quick_b:
                if st.button(
                    "标记已关闭",
                    key="quick_status_closed",
                    icon=":material/check_circle:",
                    width="stretch",
                ):
                    if not display_text(selected_event["handled_by"]).strip():
                        st.warning("请先在下方表单填写处理人。")
                    else:
                        update_alarm_status(int(selected_alarm_id), "已关闭")
                        st.rerun()
            with quick_c:
                if st.button(
                    "重置为未处理",
                    key="quick_status_open",
                    icon=":material/restart_alt:",
                    width="stretch",
                ):
                    update_alarm_status(int(selected_alarm_id), "未处理")
                    st.rerun()

            with st.form("alarm_handling_form"):
                st.markdown("**编辑处置信息**")
                form_col1, form_col2 = st.columns(2)
                with form_col1:
                    new_status = st.selectbox(
                        "状态",
                        ["未处理", "处理中", "已关闭"],
                        index=(
                            ["未处理", "处理中", "已关闭"].index(
                                selected_event["status"]
                            )
                            if selected_event["status"]
                            in {"未处理", "处理中", "已关闭"}
                            else 0
                        ),
                    )
                    handled_by = st.text_input(
                        "处理人",
                        value=display_text(selected_event["handled_by"]),
                    )
                with form_col2:
                    handling_note = st.text_area(
                        "处理备注",
                        value=display_text(selected_event["handling_note"]),
                        height=96,
                    )
                submitted = st.form_submit_button(
                    "保存处置结果",
                    type="primary",
                    icon=":material/task_alt:",
                )
                if submitted:
                    if new_status == "已关闭" and not handled_by.strip():
                        st.error("关闭报警前请填写处理人。")
                    else:
                        updated = update_alarm_status(
                            int(selected_alarm_id),
                            new_status,
                            handled_by=handled_by.strip() or None,
                            handling_note=handling_note.strip() or None,
                        )
                        if updated:
                            st.success("报警处置状态已更新。")
                            st.rerun()

with st.expander("规则与阈值说明"):
    st.dataframe(
        pd.DataFrame(
            [
                ["R01", "电机电流/负载率连续超限", "3 条采样", "高"],
                ["R02", "运行中产量连续低于基线", "3 条采样", "中"],
                ["R03", "停机状态或关键指标接近零", "当前采样", "高"],
                ["R04", "冲次超出演示合理范围", "当前采样", "中"],
            ],
            columns=["规则", "触发条件", "判断方式", "等级"],
        ),
        width="stretch",
        hide_index=True,
    )
    st.caption("阈值均为课程设计模拟假设，不代表现场设备标准。")

import streamlit as st

from core.config import CONDITION_LABELS, DEVICE_ID, LOCATION
from core.database import (
    ensure_demo_device,
    init_db,
    query_alarms,
    query_running,
)
from utils.ui import apply_global_style, command_bar, sidebar_brand

st.set_page_config(
    page_title="智抽云 - 智能抽油机运行看板",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_style()
init_db()
ensure_demo_device()

with st.sidebar:
    sidebar_brand()

navigation = st.navigation(
    [
        st.Page(
            "pages/0_运行看板.py",
            title="运行看板",
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page(
            "pages/1_运行总览.py",
            title="运行监测",
            icon=":material/monitoring:",
        ),
        st.Page(
            "pages/2_智能诊断.py",
            title="诊断中心",
            icon=":material/rule:",
        ),
        st.Page(
            "pages/3_运行优化.py",
            title="优化工作台",
            icon=":material/tune:",
        ),
        st.Page(
            "pages/4_历史数据.py",
            title="数据中心",
            icon=":material/table_chart:",
        ),
    ],
    position="sidebar",
)

alarms = query_alarms(500)
running = query_running(1)
unprocessed = (
    int((alarms["status"] != "已关闭").sum()) if not alarms.empty else 0
)
latest_status = (
    str(running.iloc[0]["status"]) if not running.empty else "待采集"
)
latest_condition = (
    str(running.iloc[0]["condition"]) if not running.empty else ""
)
condition_label = CONDITION_LABELS.get(latest_condition, latest_condition)

with st.sidebar:
    st.markdown("---")
    st.caption("设备状态")
    st.markdown(f"**{DEVICE_ID}** ｜ {latest_status}")
    st.caption(f"未处理报警 {unprocessed} 条")
    st.caption("模拟数据 · 不连接真实设备")

command_bar(
    DEVICE_ID,
    LOCATION,
    condition_label=condition_label or None,
)

navigation.run()

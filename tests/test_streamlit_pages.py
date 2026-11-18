from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.database import insert_running, query_alarms, query_running
from core.scenario import run_scenario
from core.service import ingest_sample

ROOT = Path(__file__).resolve().parents[1]


def _seed_normal_records(make_record):
    for index in range(3):
        insert_running(
            make_record(
                timestamp=f"2026-11-12 10:00:0{index}",
                energy=0.17 * (index + 1),
            )
        )


def test_main_app_renders(isolated_db, make_record):
    _seed_normal_records(make_record)

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()

    assert not app.exception
    assert any(
        "运行驾驶舱" in markdown.value
        for markdown in app.markdown
    )


@pytest.mark.parametrize(
    "page",
    [
        "pages/1_运行总览.py",
        "pages/2_智能诊断.py",
        "pages/3_运行优化.py",
        "pages/4_历史数据.py",
    ],
)
def test_each_page_renders_without_exception(
    page,
    isolated_db,
    make_record,
):
    _seed_normal_records(make_record)

    app = AppTest.from_file(str(ROOT / page), default_timeout=20).run()

    assert not app.exception


def test_overview_button_persists_new_sample(isolated_db, make_record):
    _seed_normal_records(make_record)
    before = len(query_running(100))

    app = AppTest.from_file(
        str(ROOT / "pages/1_运行总览.py"),
        default_timeout=20,
    ).run()
    app.button[0].click().run()

    assert not app.exception
    assert len(query_running(100)) == before + 1


def test_empty_history_page_handles_no_data(isolated_db):
    app = AppTest.from_file(
        str(ROOT / "pages/4_历史数据.py"),
        default_timeout=20,
    ).run()

    assert not app.exception
    assert any(
        "暂无历史运行数据" in item.value
        for item in app.markdown
    )


def test_dashboard_handles_active_alarm(isolated_db, make_record):
    _seed_normal_records(make_record)
    for index in range(3):
        ingest_sample(
            make_record(
                timestamp=f"2026-11-12 11:00:0{index}",
                status="异常",
                condition="overload",
                motor_current=56.0 + index,
                load=93.0 + index,
            )
        )

    app = AppTest.from_file(
        str(ROOT / "app.py"),
        default_timeout=20,
    ).run()

    assert not app.exception
    assert any("存在高等级异常" in item.value for item in app.markdown)


def test_one_click_scenario_from_overview(isolated_db, make_record):
    _seed_normal_records(make_record)
    before = len(query_running(100))
    app = AppTest.from_file(
        str(ROOT / "pages/1_运行总览.py"),
        default_timeout=20,
    ).run()
    button = next(
        item for item in app.button if item.key == "scenario_full"
    )

    button.click().run()

    assert not app.exception
    assert len(query_running(100)) == before + 13


def test_data_center_generates_pdf_report(isolated_db, make_record):
    _seed_normal_records(make_record)
    app = AppTest.from_file(
        str(ROOT / "pages/4_历史数据.py"),
        default_timeout=30,
    ).run()
    button = next(
        item for item in app.button if item.key == "generate_report"
    )

    button.click().run()

    assert not app.exception
    assert app.session_state["running_report_pdf"].startswith(b"%PDF")


def test_optimization_search_renders_recommendation(
    isolated_db,
    make_record,
):
    _seed_normal_records(make_record)
    app = AppTest.from_file(
        str(ROOT / "pages/3_运行优化.py"),
        default_timeout=30,
    ).run()
    button = next(
        item for item in app.button if item.key == "optimize_search"
    )

    button.click().run()

    assert not app.exception
    search_result = app.session_state["optimization_search"]
    assert search_result["recommended"]["target_stroke"] > 0


def test_optimization_page_applies_quick_plan(isolated_db, make_record):
    _seed_normal_records(make_record)
    app = AppTest.from_file(
        str(ROOT / "pages/3_运行优化.py"),
        default_timeout=30,
    ).run()

    plan_button = next(
        item for item in app.button if item.key == "quickplan_P2"
    )
    plan_button.click().run()

    assert not app.exception
    applied = app.session_state["applied_quick_plan"]
    assert applied["plan_id"] == "P2"
    assert applied["expected"]["optimized_power"] > 0
    assert any(
        "已载入方案" in item.value for item in app.success
    )


def test_optimization_page_charts_do_not_collide(isolated_db, make_record):
    """一键方案、单点模拟、方案搜索可同屏渲染而不触发重复元素 ID。"""
    _seed_normal_records(make_record)
    app = AppTest.from_file(
        str(ROOT / "pages/3_运行优化.py"),
        default_timeout=30,
    ).run()

    next(item for item in app.button if item.key == "quickplan_P2").click().run()
    next(item for item in app.button if item.key == "optimize_single").click().run()

    assert not app.exception
    assert app.session_state["applied_quick_plan"]["plan_id"] == "P2"
    assert "optimization_result" in app.session_state


def test_diagnosis_page_renders_alarm_events(isolated_db):
    run_scenario(seed=19)
    app = AppTest.from_file(
        str(ROOT / "pages/2_智能诊断.py"),
        default_timeout=30,
    ).run()

    assert not app.exception
    assert any("报警事件日志" in item.value for item in app.markdown)


def test_diagnosis_page_filters_and_quick_action(isolated_db):
    run_scenario(seed=19)
    app = AppTest.from_file(
        str(ROOT / "pages/2_智能诊断.py"),
        default_timeout=40,
    ).run()
    assert not app.exception

    # 状态与关键词筛选均不应产生异常
    app.selectbox[0].set_value("未处理").run()
    assert not app.exception
    app.selectbox[0].set_value("全部").run()
    app.text_input[0].set_value("R01").run()
    assert not app.exception
    app.text_input[0].set_value("").run()
    assert not app.exception

    # 快捷按钮更新选中事件状态
    selected = int(app.session_state["selected_alarm_id"])
    app.button(key="quick_status_processing").click().run()
    assert not app.exception
    assert (
        query_alarms(500).set_index("alarm_id").loc[selected, "status"]
        == "处理中"
    )

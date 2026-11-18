import sqlite3

import pytest

from core.database import (
    init_db,
    insert_running,
    mark_alarm_processed,
    query_alarms,
    query_device,
    query_running,
    update_alarm_status,
)
from core.service import ingest_sample


def test_running_data_and_device_status_are_persisted(
    isolated_db,
    make_record,
):
    record = make_record(status="异常", condition="overload")
    running_id = insert_running(record)

    saved = query_running(1)
    device = query_device("PUMP-001")

    assert running_id > 0
    assert len(saved) == 1
    assert saved.iloc[0]["condition"] == "overload"
    assert saved.iloc[0]["energy"] == 0.17
    assert device["status"] == "异常"


def test_alarm_processing_state_is_persisted(isolated_db, make_record):
    outcome = ingest_sample(
        make_record(
            status="停机",
            condition="stop",
            stroke_rate=0.0,
            motor_current=0.0,
            load=0.0,
            production=0.0,
            power=0.0,
        )
    )
    alarms = query_alarms(10)

    assert outcome["alarm_created"] is True
    assert len(alarms) == 1
    assert alarms.iloc[0]["status"] == "未处理"

    assert mark_alarm_processed(int(alarms.iloc[0]["alarm_id"])) is True
    refreshed = query_alarms(10)
    assert refreshed.iloc[0]["status"] == "已关闭"


def test_consecutive_event_is_not_duplicated_until_recovery(
    isolated_db,
    make_record,
):
    created = []
    for index in range(4):
        outcome = ingest_sample(
            make_record(
                timestamp=f"2026-11-12 10:00:0{index}",
                status="异常",
                condition="overload",
                motor_current=55.0 + index,
                load=92.0 + index,
                energy=0.2 + index * 0.2,
            )
        )
        created.append(outcome["alarm_created"])

    assert created == [False, False, True, False]
    assert len(query_alarms(10)) == 1

    ingest_sample(
        make_record(
            timestamp="2026-11-12 10:00:05",
            status="正常",
            condition="normal",
            energy=1.0,
        )
    )
    for index in range(3):
        outcome = ingest_sample(
            make_record(
                timestamp=f"2026-11-12 10:00:1{index}",
                status="异常",
                condition="overload",
                motor_current=56.0 + index,
                load=93.0 + index,
                energy=1.1 + index * 0.2,
            )
        )

    assert outcome["alarm_created"] is True
    assert len(query_alarms(10)) == 2


def test_query_filters_by_condition_and_date(isolated_db, make_record):
    insert_running(
        make_record(
            timestamp="2026-11-11 09:00:00",
            condition="normal",
        )
    )
    insert_running(
        make_record(
            timestamp="2026-11-12 09:00:00",
            condition="overload",
            status="异常",
            motor_current=55.0,
            load=92.0,
        )
    )

    result = query_running(
        10,
        condition="overload",
        start_date="2026-11-12",
        end_date="2026-11-12",
    )

    assert len(result) == 1
    assert result.iloc[0]["condition"] == "overload"


def test_limited_ascending_query_returns_latest_window(
    isolated_db,
    make_record,
):
    for second in range(5):
        insert_running(
            make_record(
                timestamp=f"2026-11-12 12:00:0{second}",
                energy=float(second),
            )
        )

    latest_two = query_running(2, ascending=True)

    assert latest_two["energy"].tolist() == [3.0, 4.0]


def test_v1_alarm_table_is_migrated_without_data_loss(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE alarm (
                alarm_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                device_id TEXT NOT NULL,
                alarm_type TEXT,
                level TEXT,
                rule_id TEXT,
                message TEXT,
                suggestion TEXT,
                status TEXT DEFAULT '未处理'
            )
        """)
        conn.execute("""
            INSERT INTO alarm
            (timestamp, device_id, alarm_type, level, rule_id, message, suggestion)
            VALUES ('2026-11-11 10:00:00', 'PUMP-001', '旧报警', '中',
                    'R02', '旧记录', '保留')
        """)

    monkeypatch.setenv("SMART_PUMP_DB_PATH", str(db_path))
    init_db()

    saved = query_alarms(10)
    assert len(saved) == 1
    assert saved.iloc[0]["alarm_type"] == "旧报警"
    assert "event_key" in saved.columns


def test_invalid_running_record_is_rejected(isolated_db, make_record):
    with pytest.raises(ValueError, match="power"):
        insert_running(make_record(power=-1))

    with pytest.raises(ValueError, match="timestamp"):
        insert_running(make_record(timestamp="2026/11/12 10:00"))


def test_alarm_lifecycle_records_handler_and_note(
    isolated_db,
    make_record,
):
    outcome = ingest_sample(
        make_record(
            status="停机",
            condition="stop",
            stroke_rate=0.0,
            motor_current=0.0,
            load=0.0,
            production=0.0,
            power=0.0,
        )
    )
    alarm_id = int(query_alarms(1).iloc[0]["alarm_id"])

    assert outcome["alarm_created"] is True
    assert update_alarm_status(
        alarm_id,
        "处理中",
        handled_by="张工",
        handling_note="已到现场确认",
    )
    assert update_alarm_status(
        alarm_id,
        "已关闭",
        handled_by="张工",
        handling_note="驱动模块恢复正常",
    )
    saved = query_alarms(1).iloc[0]

    assert saved["status"] == "已关闭"
    assert saved["handled_by"] == "张工"
    assert saved["handling_note"] == "驱动模块恢复正常"
    assert saved["handled_at"]

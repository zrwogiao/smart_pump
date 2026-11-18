from core.database import (
    mark_alarm_processed,
    query_alarms,
    query_running,
)
from core.optimizer import optimize
from core.service import ingest_sample


def _ingest_condition(ingest, make_record, condition, count, start_second):
    outcomes = []
    for index in range(count):
        timestamp = f"2026-11-12 11:00:{start_second + index:02d}"
        if condition == "normal":
            overrides = {
                "status": "正常",
                "condition": "normal",
            }
        elif condition == "overload":
            overrides = {
                "status": "异常",
                "condition": "overload",
                "motor_current": 56.0 + index,
                "load": 93.0 + index,
            }
        elif condition == "low_supply":
            overrides = {
                "status": "异常",
                "condition": "low_supply",
                "production": 12.0,
                "power": 9.8,
            }
        else:
            overrides = {
                "status": "停机",
                "condition": "stop",
                "stroke_rate": 0.0,
                "motor_current": 0.0,
                "load": 0.0,
                "production": 0.0,
                "power": 0.0,
            }
        outcomes.append(
            ingest(
                make_record(
                    timestamp=timestamp,
                    energy=0.2 + (start_second + index) * 0.01,
                    **overrides,
                )
            )
        )
    return outcomes


def test_full_acceptance_loop(isolated_db, make_record):
    _ingest_condition(ingest_sample, make_record, "normal", 3, 0)
    overload = _ingest_condition(
        ingest_sample,
        make_record,
        "overload",
        3,
        3,
    )
    low_supply = _ingest_condition(
        ingest_sample,
        make_record,
        "low_supply",
        3,
        6,
    )
    stop = _ingest_condition(ingest_sample, make_record, "stop", 1, 9)
    recovery = _ingest_condition(ingest_sample, make_record, "normal", 1, 10)

    assert overload[-1]["diagnosis"]["rule_id"] == "R01"
    assert overload[-1]["alarm_created"] is True
    assert low_supply[-1]["diagnosis"]["rule_id"] == "R02"
    assert low_supply[-1]["alarm_created"] is True
    assert stop[-1]["diagnosis"]["rule_id"] == "R03"
    assert stop[-1]["alarm_created"] is True
    assert recovery[-1]["diagnosis"]["has_alarm"] is False, recovery[-1]["diagnosis"]

    latest = query_running(1)
    alarms = query_alarms(20)
    assert latest.iloc[0]["status"] == "正常"
    assert set(alarms["rule_id"]) == {"R01", "R02", "R03"}

    first_alarm_id = int(alarms.iloc[-1]["alarm_id"])
    assert mark_alarm_processed(first_alarm_id) is True
    assert (
        query_alarms(20)
        .loc[lambda frame: frame["alarm_id"] == first_alarm_id, "status"]
        .iloc[0]
            == "已关闭"
    )

    results = [
        optimize(6.0, 5.0, 10.2, 18.5, objective)
        for objective in ("节能", "产量", "综合平衡")
    ]
    assert all(
        {"optimized_power", "optimized_energy", "optimized_production"}
        <= result.keys()
        for result in results
    )

    exported = query_running(100, ascending=True).to_csv(index=False)
    assert "timestamp,device_id,status,stroke_rate" in exported

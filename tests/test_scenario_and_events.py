from core.alarm_events import build_alarm_events
from core.database import query_alarms, query_running
from core.scenario import SCENARIO_STEPS, run_scenario


def test_full_scenario_generates_alarm_loop(isolated_db):
    result = run_scenario(seed=7)

    assert result["sample_count"] == len(SCENARIO_STEPS)
    assert result["alarm_count"] == 3
    assert len(query_running(100)) == len(SCENARIO_STEPS)
    assert set(query_alarms(20)["rule_id"]) == {"R01", "R02", "R03"}


def test_alarm_events_include_duration_and_peak_metrics(isolated_db):
    run_scenario(seed=11)
    alarms = query_alarms(20)
    running = query_running(100, ascending=True)

    events = build_alarm_events(alarms, running)

    assert len(events) == 3
    assert set(events["duration_minutes"]) == {1, 3}
    assert events["peak_current"].notna().all()
    assert events["min_production"].notna().all()

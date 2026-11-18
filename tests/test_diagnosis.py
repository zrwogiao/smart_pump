from core.diagnosis import diagnose, evaluate_rules


def test_normal_records_do_not_alarm(make_record):
    records = [
        make_record(timestamp=f"2026-11-12 10:00:0{index}")
        for index in range(3)
    ]

    result = diagnose(records)

    assert result["has_alarm"] is False
    assert result["rule_id"] == "-"


def test_r01_requires_three_consecutive_overload_samples(make_record):
    two_samples = [
        make_record(motor_current=55.0, load=92.0),
        make_record(motor_current=56.0, load=93.0),
    ]
    assert diagnose(two_samples)["has_alarm"] is False

    three_samples = two_samples + [
        make_record(motor_current=57.0, load=94.0)
    ]
    result = diagnose(three_samples)

    assert result["has_alarm"] is True
    assert result["rule_id"] == "R01"
    assert result["level"] == "高"


def test_r01_recovers_after_window_contains_normal_sample(make_record):
    records = [
        make_record(motor_current=55.0, load=92.0),
        make_record(motor_current=56.0, load=93.0),
        make_record(motor_current=32.0, load=55.0),
        make_record(motor_current=57.0, load=94.0),
        make_record(motor_current=58.0, load=95.0),
    ]

    result = diagnose(records)

    assert result["has_alarm"] is False


def test_r02_requires_consecutive_low_production_while_running(make_record):
    two_samples = [
        make_record(
            status="异常",
            condition="low_supply",
            production=12.0,
            power=9.8,
        )
        for _ in range(2)
    ]
    assert diagnose(two_samples)["has_alarm"] is False

    three_samples = two_samples + [
        make_record(
            status="异常",
            condition="low_supply",
            production=11.8,
            power=9.9,
        )
    ]
    result = diagnose(three_samples)

    assert result["has_alarm"] is True
    assert result["rule_id"] == "R02"
    assert result["level"] == "中"


def test_r02_does_not_trigger_when_equipment_is_stopped(make_record):
    records = [
        make_record(
            status="停机",
            condition="stop",
            stroke_rate=0.0,
            production=0.0,
            power=0.0,
        )
        for _ in range(3)
    ]

    result = diagnose(records)

    assert result["rule_id"] == "R03"


def test_r03_detects_stop_and_has_priority(make_record):
    result = diagnose(
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

    assert result["has_alarm"] is True
    assert result["rule_id"] == "R03"
    assert result["level"] == "高"


def test_r04_detects_out_of_range_stroke(make_record):
    result = diagnose(make_record(stroke_rate=9.0))

    assert result["has_alarm"] is True
    assert result["rule_id"] == "R04"
    assert result["level"] == "中"


def test_empty_diagnosis_input_is_rejected():
    try:
        diagnose([])
    except ValueError as exc:
        assert "不能为空" in str(exc)
    else:
        raise AssertionError("空诊断输入应抛出 ValueError")


def test_evaluate_rules_exposes_window_progress_and_evidence(make_record):
    records = [
        make_record(motor_current=55.0, load=92.0),
        make_record(motor_current=56.0, load=93.0),
    ]

    rules = {item["rule_id"]: item for item in evaluate_rules(records)}

    assert rules["R01"]["status"] == "watching"
    assert rules["R01"]["hits"] == 2
    assert rules["R01"]["window_size"] == 3
    assert rules["R01"]["evidence"]

    triggered = diagnose(records + [make_record(motor_current=57.0)])
    assert triggered["has_alarm"] is True
    assert triggered["evidence"][0]["hits"] == 3

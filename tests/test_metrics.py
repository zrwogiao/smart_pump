from core.metrics import calculate_health_score, operating_efficiency


def test_health_score_reflects_alarm_severity():
    normal = calculate_health_score(
        "正常",
        {"has_alarm": False, "level": "正常"},
        0,
    )
    medium = calculate_health_score(
        "异常",
        {"has_alarm": True, "level": "中"},
        1,
    )
    high = calculate_health_score(
        "异常",
        {"has_alarm": True, "level": "高"},
        3,
    )

    assert normal > medium > high
    assert 0 <= high <= 100
    assert normal <= 100


def test_operating_efficiency_handles_zero_power():
    assert operating_efficiency(18.5, 10.2) == 1.81
    assert operating_efficiency(0, 0) == 0.0

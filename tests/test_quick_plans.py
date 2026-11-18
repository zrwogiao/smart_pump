import pytest

from core.optimizer import build_quick_plans


def test_quick_plans_normal_returns_three_options_and_recommendation():
    outcome = build_quick_plans(6.0, 10.2, 18.5, condition="normal")

    assert outcome["is_recovery"] is False
    assert len(outcome["plans"]) == 3
    assert outcome["recommended_id"] == "P2"
    assert {plan["plan_id"] for plan in outcome["plans"]} == {"P1", "P2", "P3"}
    for plan in outcome["plans"]:
        assert 3.0 <= plan["target_stroke"] <= 8.0
        assert plan["expected"]["optimized_power"] > 0
        assert plan["expected"]["optimized_energy"] > 0


def test_quick_plans_overload_recommends_load_reduction():
    outcome = build_quick_plans(
        6.0,
        14.5,
        17.8,
        condition="overload",
        diagnosis={"rule_id": "R01"},
    )

    assert outcome["recommended_id"] == "P1"
    assert outcome["plans"][0]["objective"] == "节能"
    assert outcome["plans"][0]["target_stroke"] < 6.0


def test_quick_plans_low_supply_recommends_supply_matching():
    outcome = build_quick_plans(
        6.0,
        9.8,
        12.5,
        condition="low_supply",
        diagnosis={"rule_id": "R02"},
    )

    assert outcome["recommended_id"] == "P1"
    assert outcome["plans"][0]["target_stroke"] < 6.0
    assert outcome["plans"][0]["expected"]["production_retention"] > 0


def test_quick_plans_stop_uses_baseline_reference_without_error():
    outcome = build_quick_plans(
        0.02,
        0.02,
        0.0,
        condition="stop",
        diagnosis={"rule_id": "R03"},
    )

    assert outcome["is_recovery"] is True
    assert outcome["reference"]["stroke"] == pytest.approx(6.0)
    assert outcome["reference"]["power"] == pytest.approx(10.2)
    assert len(outcome["plans"]) == 3
    assert all(
        plan["expected"]["optimized_production"] > 0
        for plan in outcome["plans"]
    )
    assert "基线" in outcome["notice"]


@pytest.mark.parametrize(
    ("stroke", "power", "production"),
    [
        (0.0, 0.0, 0.0),
        (15.0, 100.0, 60.0),
        (6.0, 10.2, 0.0),
    ],
)
def test_quick_plans_handles_edge_values(stroke, power, production):
    outcome = build_quick_plans(stroke, power, production)

    assert len(outcome["plans"]) == 3
    assert all(
        plan["expected"]["optimized_power"] >= 0.1
        for plan in outcome["plans"]
    )


def test_quick_plans_effects_match_optimize_formula():
    outcome = build_quick_plans(6.0, 10.2, 18.5, condition="normal")
    plan = outcome["plans"][0]
    expected = plan["expected"]

    assert expected["current_energy"] == pytest.approx(10.2 * 24, abs=0.01)
    assert expected["optimized_energy"] == pytest.approx(
        expected["optimized_power"] * 24, abs=0.2
    )
    assert expected["daily_saving_kwh"] == pytest.approx(
        expected["current_energy"] - expected["optimized_energy"], abs=0.01
    )

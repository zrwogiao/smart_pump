import pytest

from core.config import SAMPLING_INTERVAL_MINUTES
from core.optimizer import optimize
from core.simulator import generate_data


@pytest.mark.parametrize(
    ("condition", "expected_status"),
    [
        ("normal", "正常"),
        ("overload", "异常"),
        ("low_supply", "异常"),
        ("stop", "停机"),
    ],
)
def test_simulator_generates_all_four_conditions(
    condition,
    expected_status,
):
    record = generate_data(condition, timestamp="2026-11-12 10:00:00")

    assert record["condition"] == condition
    assert record["status"] == expected_status
    assert record["device_id"] == "PUMP-001"
    assert record["timestamp"] == "2026-11-12 10:00:00"


def test_simulator_accumulates_energy_from_rounded_power():
    record = generate_data(
        "normal",
        energy_before=1.0,
        timestamp="2026-11-12 10:00:00",
    )

    expected = 1.0 + record["power"] * (SAMPLING_INTERVAL_MINUTES / 60)
    assert record["energy"] == pytest.approx(expected, abs=0.001)


def test_optimizer_supports_all_objectives_and_energy_comparison():
    results = [
        optimize(6.0, 5.0, 10.2, 18.5, objective)
        for objective in ("节能", "产量", "综合平衡")
    ]

    assert {result["objective"] for result in results} == {
        "节能",
        "产量",
        "综合平衡",
    }
    assert all(result["optimized_energy"] > 0 for result in results)
    assert all(result["current_energy"] == 244.8 for result in results)
    assert len({result["optimized_power"] for result in results}) == 3


def test_optimizer_rejects_invalid_target():
    with pytest.raises(ValueError, match="目标冲次"):
        optimize(6.0, 16.0, 10.2, 18.5, "节能")

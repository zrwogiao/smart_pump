from core.indicator import indicator_curve, pump_metrics
from core.optimizer import search_optimization


def test_indicator_curve_and_pump_metrics_are_condition_sensitive():
    normal = {
        "condition": "normal",
        "stroke_rate": 6.0,
        "production": 18.5,
    }
    stopped = {
        "condition": "stop",
        "stroke_rate": 0.0,
        "production": 0.0,
    }

    normal_curve = indicator_curve(normal)
    stopped_curve = indicator_curve(stopped)
    normal_metrics = pump_metrics(normal)
    stopped_metrics = pump_metrics(stopped)

    assert len(normal_curve) == 180
    assert normal_curve["load"].max() > stopped_curve["load"].max()
    assert normal_metrics["pump_efficiency"] > 0
    assert stopped_metrics["pump_efficiency"] == 0


def test_optimization_search_returns_ranked_candidates_and_pareto():
    result = search_optimization(
        current_stroke=6.0,
        current_power=10.2,
        current_production=18.5,
        objective="综合平衡",
    )

    assert result["recommended"] is not None
    assert 3.0 <= result["recommended"]["target_stroke"] <= 8.0
    assert result["recommended"]["feasible"] is True
    assert any(item["is_pareto"] for item in result["candidates"])
    assert len(result["candidates"]) > 10

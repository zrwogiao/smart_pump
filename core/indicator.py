import numpy as np
import pandas as pd

from core.config import BASELINE, NORMAL_STROKE_MAX


def indicator_curve(record, points=90):
    x_up = np.linspace(0.0, 1.0, points)
    x_down = np.linspace(1.0, 0.0, points)
    condition = record.get("condition", "normal")

    if condition == "overload":
        load_up = 62 + 28 * np.sin(np.pi * x_up)
        load_down = 43 + 10 * np.sin(np.pi * x_down)
    elif condition == "low_supply":
        load_up = 38 + 12 * np.sin(np.pi * x_up) + 6 * np.sin(
            3 * np.pi * x_up
        )
        load_down = 18 + 8 * np.sin(np.pi * x_down) + 4 * np.sin(
            4 * np.pi * x_down
        )
    elif condition == "stop":
        load_up = 1.5 + 1.2 * np.sin(np.pi * x_up)
        load_down = 0.8 + 0.5 * np.sin(np.pi * x_down)
    else:
        load_up = 47 + 20 * np.sin(np.pi * x_up)
        load_down = 24 + 7 * np.sin(np.pi * x_down)

    return pd.DataFrame(
        {
            "displacement": np.concatenate([x_up, x_down]),
            "load": np.concatenate([load_up, load_down]),
            "stroke": ["上行"] * points + ["下行"] * points,
        }
    )


def pump_metrics(record):
    stroke_rate = float(record.get("stroke_rate", 0))
    production = float(record.get("production", 0))
    theoretical_daily = stroke_rate * 4.2
    fill_factor = (
        min(1.2, max(0.0, production / theoretical_daily))
        if theoretical_daily > 0
        else 0.0
    )
    pump_efficiency = fill_factor * 0.82
    stroke_utilization = min(
        1.2,
        max(0.0, stroke_rate / NORMAL_STROKE_MAX),
    )
    production_ratio = (
        production / BASELINE["production"]
        if BASELINE["production"] > 0
        else 0.0
    )
    return {
        "theoretical_daily": round(theoretical_daily, 2),
        "fill_factor": round(fill_factor * 100, 2),
        "pump_efficiency": round(pump_efficiency * 100, 2),
        "stroke_utilization": round(stroke_utilization * 100, 2),
        "production_ratio": round(production_ratio * 100, 2),
    }

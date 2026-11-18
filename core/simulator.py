import random
from datetime import datetime

from core.config import BASELINE, DEVICE_ID, SAMPLING_INTERVAL_MINUTES


def _noise(value: float, ratio: float = 0.03) -> float:
    return value * (1 + random.uniform(-ratio, ratio))


def generate_data(
    condition: str,
    energy_before: float = 0.0,
    timestamp: str | None = None,
) -> dict:
    if condition == "overload":
        stroke = _noise(6.0, 0.02)
        current = random.uniform(54, 62)
        load = random.uniform(91, 97)
        production = _noise(17.8, 0.03)
        power = random.uniform(13.5, 15.5)
        status = "异常"
    elif condition == "low_supply":
        stroke = _noise(6.0, 0.02)
        current = _noise(31.0, 0.03)
        load = _noise(53.0, 0.03)
        production = random.uniform(11.5, 14.0)
        power = _noise(9.8, 0.03)
        status = "异常"
    elif condition == "stop":
        stroke = random.uniform(0.0, 0.05)
        current = random.uniform(0.0, 2.0)
        load = random.uniform(0.0, 5.0)
        production = 0.0
        power = random.uniform(0.0, 0.05)
        status = "停机"
    else:
        condition = "normal"
        stroke = _noise(BASELINE["stroke_rate"], 0.03)
        current = _noise(BASELINE["motor_current"], 0.04)
        load = _noise(BASELINE["load"], 0.04)
        production = _noise(BASELINE["production"], 0.03)
        power = _noise(BASELINE["power"], 0.04)
        status = "正常"

    rounded_power = round(power, 2)
    energy = max(
        0.0,
        float(energy_before)
        + rounded_power * (SAMPLING_INTERVAL_MINUTES / 60.0),
    )

    return {
        "timestamp": timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "device_id": DEVICE_ID,
        "status": status,
        "stroke_rate": round(stroke, 2),
        "motor_current": round(current, 2),
        "load": round(load, 2),
        "production": round(production, 2),
        "power": rounded_power,
        "energy": round(energy, 3),
        "condition": condition,
    }

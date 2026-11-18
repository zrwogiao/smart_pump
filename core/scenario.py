import random
from datetime import datetime, timedelta

from core.config import CONDITION_LABELS, DEVICE_ID
from core.database import query_running
from core.service import ingest_sample
from core.simulator import generate_data

SCENARIO_STEPS = (
    [{"condition": "normal", "label": "建立正常基线"} for _ in range(3)]
    + [{"condition": "overload", "label": "电机过载连续采样"} for _ in range(3)]
    + [{"condition": "low_supply", "label": "供液不足连续采样"} for _ in range(3)]
    + [{"condition": "stop", "label": "异常停机采样"}]
    + [{"condition": "normal", "label": "恢复运行"} for _ in range(3)]
)


def scenario_summary():
    return [
        {
            "index": index + 1,
            "condition": step["condition"],
            "condition_label": CONDITION_LABELS[step["condition"]],
            "label": step["label"],
        }
        for index, step in enumerate(SCENARIO_STEPS)
    ]


def run_scenario(start_time: datetime | None = None, seed: int = 42) -> dict:
    random.seed(seed)
    if start_time is None:
        start_time = datetime.now().replace(microsecond=0) - timedelta(
            minutes=len(SCENARIO_STEPS) - 1
        )
    latest = query_running(1)
    energy = float(latest.iloc[0]["energy"]) if not latest.empty else 0.0

    outcomes = []
    for index, step in enumerate(SCENARIO_STEPS):
        record = generate_data(
            step["condition"],
            energy_before=energy,
            timestamp=(start_time + timedelta(minutes=index)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )
        energy = float(record["energy"])
        outcome = ingest_sample(record)
        outcome["scenario_index"] = index
        outcome["scenario_label"] = step["label"]
        outcomes.append(outcome)

    return {
        "device_id": DEVICE_ID,
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "sample_count": len(outcomes),
        "alarm_count": sum(
            1 for outcome in outcomes if outcome["alarm_created"]
        ),
        "outcomes": outcomes,
    }

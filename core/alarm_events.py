import json

import pandas as pd

RULE_CONDITIONS = {
    "R01": "overload",
    "R02": "low_supply",
    "R03": "stop",
}


def _parse_evidence(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def build_alarm_events(alarms: pd.DataFrame, running: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "alarm_id",
        "timestamp",
        "alarm_type",
        "level",
        "rule_id",
        "status",
        "handled_by",
        "handling_note",
        "handled_at",
        "event_start",
        "event_end",
        "duration_minutes",
        "sample_count",
        "peak_current",
        "peak_load",
        "peak_power",
        "min_production",
        "evidence",
    ]
    if alarms.empty:
        return pd.DataFrame(columns=columns)

    run = running.copy()
    if not run.empty:
        run["timestamp"] = pd.to_datetime(run["timestamp"])
        run = run.sort_values(["timestamp", "id"]).reset_index(drop=True)

    events = []
    for _, alarm in alarms.iterrows():
        alarm_time = pd.to_datetime(alarm["timestamp"])
        rule_id = str(alarm.get("rule_id", ""))
        condition = RULE_CONDITIONS.get(rule_id)
        block = pd.DataFrame()

        if not run.empty and condition:
            candidates = run.index[
                (run["device_id"] == alarm.get("device_id"))
                & (run["timestamp"] <= alarm_time)
            ].tolist()
            if candidates:
                start_index = candidates[-1]
                if run.at[start_index, "condition"] == condition:
                    first = start_index
                    while (
                        first > 0
                        and run.at[first - 1, "condition"] == condition
                    ):
                        first -= 1
                    last = start_index
                    while (
                        last + 1 < len(run)
                        and run.at[last + 1, "condition"] == condition
                    ):
                        last += 1
                    block = run.loc[first:last]

        if block.empty and not run.empty:
            nearest = run.iloc[
                (run["timestamp"] - alarm_time).abs().argsort()[:1]
            ]
            block = nearest

        event_start = (
            block.iloc[0]["timestamp"] if not block.empty else alarm_time
        )
        event_end = block.iloc[-1]["timestamp"] if not block.empty else alarm_time
        events.append(
            {
                "alarm_id": alarm["alarm_id"],
                "timestamp": alarm["timestamp"],
                "alarm_type": alarm["alarm_type"],
                "level": alarm["level"],
                "rule_id": alarm["rule_id"],
                "status": alarm["status"],
                "handled_by": alarm.get("handled_by"),
                "handling_note": alarm.get("handling_note"),
                "handled_at": alarm.get("handled_at"),
                "event_start": event_start,
                "event_end": event_end,
                "duration_minutes": max(1, len(block)),
                "sample_count": len(block),
                "peak_current": (
                    round(float(block["motor_current"].max()), 2)
                    if not block.empty
                    else None
                ),
                "peak_load": (
                    round(float(block["load"].max()), 2)
                    if not block.empty
                    else None
                ),
                "peak_power": (
                    round(float(block["power"].max()), 2)
                    if not block.empty
                    else None
                ),
                "min_production": (
                    round(float(block["production"].min()), 2)
                    if not block.empty
                    else None
                ),
                "evidence": _parse_evidence(alarm.get("evidence_json")),
            }
        )
    return pd.DataFrame(events, columns=columns)

from core.config import DIAGNOSIS_WINDOW_SIZE
from core.database import insert_alarm, insert_running, query_running
from core.diagnosis import diagnose


def ingest_sample(record: dict) -> dict:
    """保存一条采样并返回当前诊断；同一连续事件只生成一条报警。"""
    running_id = insert_running(record)
    history = query_running(
        limit=max(DIAGNOSIS_WINDOW_SIZE * 2, 10),
        ascending=True,
    )
    history_records = history.to_dict("records")
    result = diagnose(history_records)

    alarm_created = False
    if result["has_alarm"]:
        previous_records = history_records[:-1]
        previous_result = (
            diagnose(previous_records)
            if previous_records
            else {"has_alarm": False, "rule_id": "-"}
        )
        starts_new_event = (
            not previous_result["has_alarm"]
            or previous_result["rule_id"] != result["rule_id"]
        )
        if starts_new_event:
            event_key = (
                f"{record['device_id']}:{result['rule_id']}:{running_id}"
            )
            alarm_created = insert_alarm(
                result,
                record["device_id"],
                record["timestamp"],
                event_key=event_key,
            )

    return {
        "running_id": running_id,
        "record": record,
        "diagnosis": result,
        "alarm_created": alarm_created,
    }

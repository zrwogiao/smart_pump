def calculate_health_score(status, diagnosis, unprocessed_alarms=0):
    if diagnosis.get("has_alarm"):
        score = 42 if diagnosis.get("level") == "高" else 68
    elif str(status) in {"停机", "异常停机", "异常"}:
        score = 35
    else:
        score = 96

    penalty = min(int(unprocessed_alarms) * 2, 12)
    return max(0, min(100, score - penalty))


def operating_efficiency(production, power):
    power = float(power)
    if power <= 0:
        return 0.0
    return round(float(production) / power, 2)

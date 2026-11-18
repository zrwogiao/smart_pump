from collections.abc import Mapping, Sequence

from core.config import (
    BASELINE,
    DIAGNOSIS_WINDOW_SIZE,
    LOW_PRODUCTION_RATIO,
    NORMAL_STROKE_MAX,
    NORMAL_STROKE_MIN,
    OVERLOAD_CURRENT,
    OVERLOAD_LOAD,
    STOP_POWER,
    STOP_STROKE,
)

LEVEL_ORDER = {"高": 3, "中": 2, "低": 1}

RULE_META = {
    "R01": {"alarm_type": "电机过载", "level": "高"},
    "R02": {"alarm_type": "疑似供液不足", "level": "中"},
    "R03": {"alarm_type": "异常停机", "level": "高"},
    "R04": {"alarm_type": "参数异常", "level": "中"},
}


def _as_history(data) -> list[Mapping]:
    if isinstance(data, Mapping):
        return [data]
    if isinstance(data, Sequence) and not isinstance(data, (str, bytes)):
        return list(data)
    raise TypeError("诊断输入必须是单条记录或记录序列")


def _is_running(data: Mapping) -> bool:
    return (
        data.get("status") not in {"停机", "异常停机"}
        and float(data["stroke_rate"]) > STOP_STROKE
        and float(data["power"]) > STOP_POWER
    )


def _evidence(
    metric,
    value,
    threshold,
    operator,
    unit,
    hits,
    window_size,
    passed,
    *,
    label=None,
):
    return {
        "metric": metric,
        "label": label or metric,
        "value": value,
        "threshold": threshold,
        "operator": operator,
        "unit": unit,
        "hits": int(hits),
        "window_size": int(window_size),
        "passed": bool(passed),
    }


def _alarm(
    rule_id,
    alarm_type,
    level,
    message,
    suggestion,
    sample_count,
    evidence,
):
    return {
        "has_alarm": True,
        "alarm_type": alarm_type,
        "level": level,
        "rule_id": rule_id,
        "message": message,
        "suggestion": suggestion,
        "sample_count": sample_count,
        "evidence": evidence,
    }


def _stop_finding(data: Mapping):
    status = data.get("status")
    zero_running_data = (
        float(data["stroke_rate"]) <= STOP_STROKE
        and float(data["power"]) <= STOP_POWER
    )
    triggered = status in {"停机", "异常停机"} or zero_running_data
    evidence = [
        _evidence(
            "运行状态",
            status or "-",
            "停机状态",
            "等于",
            "",
            1 if triggered else 0,
            1,
            triggered,
            label="设备状态",
        ),
        _evidence(
            "冲次",
            round(float(data["stroke_rate"]), 2),
            STOP_STROKE,
            "<=",
            "次/min",
            1 if float(data["stroke_rate"]) <= STOP_STROKE else 0,
            1,
            float(data["stroke_rate"]) <= STOP_STROKE,
        ),
        _evidence(
            "功率",
            round(float(data["power"]), 2),
            STOP_POWER,
            "<=",
            "kW",
            1 if float(data["power"]) <= STOP_POWER else 0,
            1,
            float(data["power"]) <= STOP_POWER,
        ),
    ]
    return triggered, evidence


def _overload_finding(window: Sequence[Mapping], window_size: int):
    compound_hits = sum(
        1
        for data in window
        if float(data["motor_current"]) >= OVERLOAD_CURRENT
        or float(data["load"]) >= OVERLOAD_LOAD
    )
    current_hits = sum(
        1 for data in window if float(data["motor_current"]) >= OVERLOAD_CURRENT
    )
    load_hits = sum(
        1 for data in window if float(data["load"]) >= OVERLOAD_LOAD
    )
    triggered = len(window) >= window_size and compound_hits == window_size
    current = window[-1] if window else {}
    evidence = [
        _evidence(
            "电流/负载率",
            (
                f"{float(current.get('motor_current', 0)):.2f} A / "
                f"{float(current.get('load', 0)):.2f} %"
            ),
            f"{OVERLOAD_CURRENT:.1f} A / {OVERLOAD_LOAD:.1f} %",
            "任一超限",
            "A / %",
            compound_hits,
            window_size,
            triggered,
            label="连续超限条件",
        ),
        _evidence(
            "电机电流",
            round(float(current.get("motor_current", 0)), 2),
            OVERLOAD_CURRENT,
            ">=",
            "A",
            current_hits,
            window_size,
            current_hits == window_size,
        ),
        _evidence(
            "负载率",
            round(float(current.get("load", 0)), 2),
            OVERLOAD_LOAD,
            ">=",
            "%",
            load_hits,
            window_size,
            load_hits == window_size,
        ),
    ]
    return triggered, evidence


def _low_supply_finding(window: Sequence[Mapping], window_size: int):
    baseline_production = BASELINE["production"] * LOW_PRODUCTION_RATIO
    hits = sum(
        1
        for data in window
        if _is_running(data)
        and float(data["production"]) < baseline_production
    )
    triggered = len(window) >= window_size and hits == window_size
    current = window[-1] if window else {}
    evidence = [
        _evidence(
            "模拟产量",
            round(float(current.get("production", 0)), 2),
            round(baseline_production, 2),
            "<",
            "m³/d",
            hits,
            window_size,
            triggered,
            label="连续低产量条件",
        )
    ]
    return triggered, evidence


def _parameter_finding(data: Mapping):
    stroke_rate = float(data["stroke_rate"])
    triggered = not (
        NORMAL_STROKE_MIN <= stroke_rate <= NORMAL_STROKE_MAX
    )
    evidence = [
        _evidence(
            "冲次",
            round(stroke_rate, 2),
            f"{NORMAL_STROKE_MIN:.1f}-{NORMAL_STROKE_MAX:.1f}",
            "超出范围",
            "次/min",
            1 if triggered else 0,
            1,
            triggered,
        )
    ]
    return triggered, evidence


def check_stop(data: Mapping):
    triggered, evidence = _stop_finding(data)
    if triggered:
        return _alarm(
            "R03",
            "异常停机",
            "高",
            "设备状态或关键运行指标显示停机，系统判断为异常停机状态。",
            "检查设备运行状态、驱动系统及数据采集链路。",
            1,
            evidence,
        )
    return None


def check_overload(window: Sequence[Mapping], window_size: int):
    triggered, evidence = _overload_finding(window, window_size)
    if triggered:
        return _alarm(
            "R01",
            "电机过载",
            "高",
            f"电机电流或负载率连续 {window_size} 个采样周期超过演示阈值。",
            "检查负载情况，适当降低运行参数，并检查机械部分。",
            len(window),
            evidence,
        )
    return None


def check_low_supply(window: Sequence[Mapping], window_size: int):
    triggered, evidence = _low_supply_finding(window, window_size)
    if triggered:
        return _alarm(
            "R02",
            "疑似供液不足",
            "中",
            f"设备保持运行，但模拟产量连续 {window_size} 个采样周期低于基准水平。",
            "检查供液情况，并评估降低冲次的可行性。",
            len(window),
            evidence,
        )
    return None


def check_parameter(data: Mapping):
    triggered, evidence = _parameter_finding(data)
    if triggered:
        return _alarm(
            "R04",
            "参数异常",
            "中",
            "冲次超出系统设定的演示合理范围。",
            "检查运行参数设置是否合理。",
            1,
            evidence,
        )
    return None


def evaluate_rules(data, window_size: int | None = None) -> list[dict]:
    history = _as_history(data)
    if not history:
        raise ValueError("诊断记录不能为空")
    size = int(window_size or DIAGNOSIS_WINDOW_SIZE)
    window = history[-size:]
    current = history[-1]

    findings = {
        "R01": _overload_finding(window, size),
        "R02": _low_supply_finding(window, size),
        "R03": _stop_finding(current),
        "R04": _parameter_finding(current),
    }
    rules = []
    for rule_id in ("R01", "R02", "R03", "R04"):
        triggered, evidence = findings[rule_id]
        primary_hits = evidence[0]["hits"] if evidence else 0
        required = evidence[0]["window_size"] if evidence else size
        if triggered:
            status = "triggered"
        elif primary_hits > 0 and required > 1:
            status = "watching"
        else:
            status = "normal"
        rules.append(
            {
                "rule_id": rule_id,
                **RULE_META[rule_id],
                "status": status,
                "hits": primary_hits,
                "window_size": required,
                "evidence": evidence,
            }
        )
    return rules


def diagnose(data, window_size: int | None = None) -> dict:
    history = _as_history(data)
    if not history:
        raise ValueError("诊断记录不能为空")

    size = int(window_size or DIAGNOSIS_WINDOW_SIZE)
    if size <= 0:
        raise ValueError("诊断窗口长度必须大于 0")

    current = history[-1]
    window = history[-size:]
    results = [
        check_stop(current),
        check_overload(window, size),
        check_low_supply(window, size),
        check_parameter(current),
    ]
    results = [result for result in results if result]
    if not results:
        return {
            "has_alarm": False,
            "alarm_type": "正常",
            "level": "正常",
            "rule_id": "-",
            "message": "当前运行指标处于演示基线范围内，未发现异常。",
            "suggestion": "继续监测运行状态。",
            "sample_count": len(window),
            "evidence": [],
        }

    results.sort(key=lambda item: LEVEL_ORDER.get(item["level"], 0), reverse=True)
    result = results[0]
    result["window_size"] = size
    result["available_samples"] = len(window)
    return result

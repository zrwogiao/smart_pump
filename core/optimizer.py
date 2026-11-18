from core.config import (
    BASELINE,
    CONDITION_LABELS,
    MAX_STROKE,
    MIN_STROKE,
    NORMAL_STROKE_MAX,
    NORMAL_STROKE_MIN,
    STOP_POWER,
    STOP_STROKE,
)

OBJECTIVES = ("节能", "产量", "综合平衡")

OBJECTIVE_FACTORS = {
    "节能": (0.95, 0.97),
    "产量": (1.04, 1.03),
    "综合平衡": (0.98, 1.01),
}

SEARCH_MIN_STROKE = 3.0
SEARCH_MAX_STROKE = 8.0
SEARCH_STEP = 0.25
MIN_PRODUCTION_RETENTION = 0.85


def optimize(
    current_stroke: float,
    target_stroke: float,
    current_power: float,
    current_production: float,
    objective: str,
) -> dict:
    current_stroke = float(current_stroke)
    target_stroke = float(target_stroke)
    current_power = float(current_power)
    current_production = float(current_production)

    if not MIN_STROKE <= current_stroke <= MAX_STROKE:
        raise ValueError(f"当前冲次必须在 {MIN_STROKE}-{MAX_STROKE} 次/min 之间")
    if not MIN_STROKE <= target_stroke <= MAX_STROKE:
        raise ValueError(f"目标冲次必须在 {MIN_STROKE}-{MAX_STROKE} 次/min 之间")
    if current_power <= 0:
        raise ValueError("当前功率必须大于 0")
    if current_production < 0:
        raise ValueError("当前模拟产量不能小于 0")
    if objective not in OBJECTIVES:
        raise ValueError(f"不支持的优化目标: {objective}")

    ratio = target_stroke / current_stroke

    # 课程设计简化模型：功率随冲次比例变化，产量采用次线性关系。
    power_factor = 0.70 + 0.30 * ratio
    production_factor = max(0.50, min(1.15, ratio**0.85))
    objective_power_factor, objective_production_factor = OBJECTIVE_FACTORS[objective]
    power_factor *= objective_power_factor
    production_factor *= objective_production_factor

    optimized_power = max(0.1, current_power * power_factor)
    optimized_production = max(0.0, current_production * production_factor)
    current_energy = current_power * 24
    optimized_energy = optimized_power * 24

    if objective == "节能":
        recommendation = (
            "节能目标优先压缩模拟功率。降低冲次通常可降低能耗，"
            "但应同时关注产量下降幅度。"
        )
    elif objective == "产量":
        recommendation = (
            "产量目标允许适度增加模拟功率以换取更高产量，"
            "演示中应结合能耗变化共同评估。"
        )
    else:
        recommendation = (
            "综合平衡目标在模拟节能与产量之间折中，"
            "建议结合课程演示目标选择可接受的参数变化。"
        )

    if optimized_power < current_power:
        recommendation += " 当前方案预计降低模拟功率。"
    else:
        recommendation += " 当前方案预计增加模拟功率。"

    return {
        "objective": objective,
        "target_stroke": round(target_stroke, 2),
        "current_power": round(current_power, 2),
        "optimized_power": round(optimized_power, 2),
        "current_energy": round(current_energy, 2),
        "optimized_energy": round(optimized_energy, 2),
        "current_production": round(current_production, 2),
        "optimized_production": round(optimized_production, 2),
        "power_change_pct": round((optimized_power / current_power - 1) * 100, 2),
        "production_change_pct": round(
            (optimized_production / current_production - 1) * 100,
            2,
        )
        if current_production
        else 0.0,
        "recommendation": recommendation,
    }


def _score_candidate(result, objective):
    saving_ratio = max(
        0.0,
        (result["current_energy"] - result["optimized_energy"])
        / result["current_energy"],
    )
    production_ratio = (
        result["optimized_production"] / result["current_production"]
        if result["current_production"] > 0
        else 0.0
    )
    saving_score = min(100.0, saving_ratio * 500.0)
    production_score = min(120.0, production_ratio * 100.0)
    risk_score = max(
        0.0,
        100.0 - result["target_stroke"] / SEARCH_MAX_STROKE * 100.0,
    )

    if objective == "节能":
        return saving_score * 0.65 + min(production_score, 100) * 0.35
    if objective == "产量":
        production_gain = max(0.0, production_ratio - 1.0)
        return (
            production_score * 0.55
            + min(100.0, production_gain * 600.0) * 0.25
            + saving_score * 0.20
        )
    return (
        saving_score * 0.45
        + min(production_score, 110) * 0.45
        + risk_score * 0.10
    )


def search_optimization(
    current_stroke,
    current_power,
    current_production,
    objective,
):
    if objective not in OBJECTIVES:
        raise ValueError(f"不支持的优化目标: {objective}")
    if float(current_production) <= 0:
        raise ValueError("方案搜索要求当前模拟产量大于 0")

    targets = []
    target = SEARCH_MIN_STROKE
    while target <= SEARCH_MAX_STROKE + 1e-9:
        targets.append(round(target, 2))
        target += SEARCH_STEP

    candidates = []
    for target in targets:
        result = optimize(
            current_stroke,
            target,
            current_power,
            current_production,
            objective,
        )
        production_retention = (
            result["optimized_production"] / result["current_production"]
        )
        result["production_retention"] = round(production_retention, 4)
        result["feasible"] = (
            production_retention >= MIN_PRODUCTION_RETENTION
        )
        result["score"] = round(_score_candidate(result, objective), 2)
        candidates.append(result)

    feasible = [item for item in candidates if item["feasible"]]
    for candidate in candidates:
        dominated = False
        for other in feasible:
            if other is candidate:
                continue
            no_worse = (
                other["optimized_power"] <= candidate["optimized_power"]
                and other["optimized_production"]
                >= candidate["optimized_production"]
            )
            strictly_better = (
                other["optimized_power"] < candidate["optimized_power"]
                or other["optimized_production"]
                > candidate["optimized_production"]
            )
            if no_worse and strictly_better:
                dominated = True
                break
        candidate["is_pareto"] = candidate["feasible"] and not dominated

    ranked = sorted(
        feasible,
        key=lambda item: (item["score"], item["production_retention"]),
        reverse=True,
    )
    recommended = ranked[0] if ranked else None
    return {
        "objective": objective,
        "candidates": candidates,
        "feasible": feasible,
        "recommended": recommended,
        "constraint_text": (
            f"模拟产量不低于当前的 {MIN_PRODUCTION_RETENTION * 100:.0f}%"
        ),
    }


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _half_up(value: float) -> float:
    return round(value * 2) / 2


def build_quick_plans(
    current_stroke,
    current_power,
    current_production,
    *,
    condition="normal",
    diagnosis=None,
) -> dict:
    """根据当前运行状态生成若干一键优化方案及预计效果。

    方案目标是调整冲次，功耗与产量采用与 :func:`optimize` 相同的简化模型
    估算，保证与手动模拟、方案搜索口径一致。停机工况以基线参数作为参考
    估算启机方案，避免除零或产生误导性的“当前值”。
    """
    stroke = float(current_stroke)
    power = float(current_power)
    production = float(current_production)
    diagnosis = diagnosis or {}
    rule_id = str(diagnosis.get("rule_id", "-") or "-")
    condition = str(condition or "normal")

    stopped = (
        condition == "stop"
        or rule_id == "R03"
        or stroke <= STOP_STROKE
        or power <= STOP_POWER
    )
    if stopped:
        ref_stroke = float(BASELINE["stroke_rate"])
        ref_power = float(BASELINE["power"])
        ref_production = float(BASELINE["production"])
    else:
        ref_stroke = _clamp(stroke, MIN_STROKE, MAX_STROKE)
        ref_power = max(power, 0.1)
        ref_production = max(production, 0.0)

    base = _clamp(ref_stroke, NORMAL_STROKE_MIN, NORMAL_STROKE_MAX)

    if stopped:
        specs = [
            {
                "plan_id": "P1",
                "name": "低冲次启机",
                "badge": "稳妥启机",
                "objective": "节能",
                "tone": "blue",
                "risk": "低",
                "target": _half_up(_clamp(base - 1.0, 3.0, 8.0)),
                "reason": "以较低冲次恢复运行，降低启动负荷，适合长时间停机后的平稳启机。",
            },
            {
                "plan_id": "P2",
                "name": "基线恢复",
                "badge": "推荐",
                "objective": "综合平衡",
                "tone": "good",
                "risk": "低",
                "target": _half_up(base),
                "reason": "恢复到课程基线冲次，兼顾能耗与产量，作为启机优先参考方案。",
            },
            {
                "plan_id": "P3",
                "name": "快速提产",
                "badge": "产量优先",
                "objective": "产量",
                "tone": "warn",
                "risk": "中",
                "target": _half_up(_clamp(base + 0.5, 3.0, 8.0)),
                "reason": "适当提高启机冲次以更快恢复产量，需关注电流与负载是否在合理区间。",
            },
        ]
        recommended_id = "P2"
        summary = "设备当前停机，优化目标改为“恢复运行参数”，预计效果按基线工况估算。"
    elif rule_id == "R01" or condition == "overload":
        specs = [
            {
                "plan_id": "P1",
                "name": "降载保护",
                "badge": "优先处置",
                "objective": "节能",
                "tone": "danger",
                "risk": "低",
                "target": _half_up(_clamp(base - 1.5, 3.0, 8.0)),
                "reason": "当前存在电机过载迹象，优先降低冲次以压缩电流和负载，保护设备。",
            },
            {
                "plan_id": "P2",
                "name": "温和降载",
                "badge": "兼顾产量",
                "objective": "综合平衡",
                "tone": "blue",
                "risk": "低",
                "target": _half_up(_clamp(base - 0.5, 3.0, 8.0)),
                "reason": "小幅降低冲次，在缓解过载的同时尽量保留产量。",
            },
            {
                "plan_id": "P3",
                "name": "维持产量",
                "badge": "产量优先",
                "objective": "产量",
                "tone": "warn",
                "risk": "高",
                "target": _half_up(base),
                "reason": "维持当前冲次保产，但过载风险仍在，仅建议在排查负载后短期采用。",
            },
        ]
        recommended_id = "P1"
        summary = "检测到电机过载风险，推荐先降载运行，再结合检查机械负载决定是否提产。"
    elif rule_id == "R02" or condition == "low_supply":
        specs = [
            {
                "plan_id": "P1",
                "name": "供液适配",
                "badge": "推荐",
                "objective": "综合平衡",
                "tone": "good",
                "risk": "低",
                "target": _half_up(_clamp(base - 0.5, 3.0, 8.0)),
                "reason": "疑似供液不足时适度下调冲次，使抽汲速度与供液能力更匹配。",
            },
            {
                "plan_id": "P2",
                "name": "节能观察",
                "badge": "节能优先",
                "objective": "节能",
                "tone": "blue",
                "risk": "低",
                "target": _half_up(_clamp(base - 1.0, 3.0, 8.0)),
                "reason": "进一步降低冲次与能耗，适合在供液恢复前以观察为主的阶段。",
            },
            {
                "plan_id": "P3",
                "name": "维持产量",
                "badge": "产量优先",
                "objective": "产量",
                "tone": "warn",
                "risk": "中",
                "target": _half_up(base),
                "reason": "保持当前冲次，产量提升空间有限，需先确认供液情况。",
            },
        ]
        recommended_id = "P1"
        summary = "当前产量低于基线，建议优先适配供液能力，盲目提产难以带来有效增益。"
    else:
        specs = [
            {
                "plan_id": "P1",
                "name": "节能降耗",
                "badge": "省电优先",
                "objective": "节能",
                "tone": "good",
                "risk": "低",
                "target": _half_up(_clamp(base - 1.0, 3.0, 8.0)),
                "reason": "适度降低冲次可压缩电机功率与日耗电，适合以降本为优先的场景。",
            },
            {
                "plan_id": "P2",
                "name": "综合平衡",
                "badge": "推荐",
                "objective": "综合平衡",
                "tone": "blue",
                "risk": "低",
                "target": _half_up(base),
                "reason": "在能耗与产量之间折中，保持产量基本稳定的同时获得一定节能收益。",
            },
            {
                "plan_id": "P3",
                "name": "稳产增产",
                "badge": "产量优先",
                "objective": "产量",
                "tone": "warn",
                "risk": "中",
                "target": _half_up(_clamp(base + 0.5, 3.0, 8.0)),
                "reason": "小幅提高冲次换取更高模拟产量，需关注电流与负载是否仍在合理区间。",
            },
        ]
        recommended_id = "P2"
        summary = "设备运行正常，可按需在节能、平衡与增产三种导向之间选择。"

    plans = []
    for spec in specs:
        result = optimize(
            ref_stroke,
            spec["target"],
            ref_power,
            ref_production,
            spec["objective"],
        )
        optimized_production = result["optimized_production"]
        result["daily_saving_kwh"] = round(
            result["current_energy"] - result["optimized_energy"], 2
        )
        result["production_retention"] = (
            round(optimized_production / result["current_production"], 4)
            if result["current_production"] > 0
            else 1.0
        )
        result["score"] = round(_score_candidate(result, spec["objective"]), 1)
        plans.append(
            {
                "plan_id": spec["plan_id"],
                "name": spec["name"],
                "badge": spec["badge"],
                "tone": spec["tone"],
                "risk": spec["risk"],
                "reason": spec["reason"],
                "objective": spec["objective"],
                "target_stroke": spec["target"],
                "recommended": spec["plan_id"] == recommended_id,
                "expected": result,
            }
        )

    return {
        "condition": condition,
        "condition_label": CONDITION_LABELS.get(condition, condition),
        "rule_id": rule_id,
        "is_recovery": stopped,
        "reference": {
            "stroke": round(ref_stroke, 2),
            "power": round(ref_power, 2),
            "production": round(ref_production, 2),
        },
        "summary": summary,
        "recommended_id": recommended_id,
        "plans": plans,
        "notice": (
            "停机期间无有效能耗与产量基准，预计效果以课程基线参数估算，仅供演示。"
            if stopped
            else "预计效果由简化模型生成，仅用于课程演示，不会下发或控制真实设备。"
        ),
    }

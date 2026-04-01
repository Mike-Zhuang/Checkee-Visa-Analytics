from __future__ import annotations

import math
import random
import re
from datetime import date
from statistics import mean, median
from typing import Any

from app.core.config import BOOTSTRAP_SEED


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    arr = sorted(values)
    if len(arr) == 1:
        return arr[0]
    idx = (len(arr) - 1) * p
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return arr[lo]
    ratio = idx - lo
    return arr[lo] * (1 - ratio) + arr[hi] * ratio


def stats(values: list[int]) -> dict[str, float]:
    if not values:
        return {
            "count": 0,
            "mean": float("nan"),
            "median": float("nan"),
            "p25": float("nan"),
            "p75": float("nan"),
            "p90": float("nan"),
            "max": float("nan"),
            "std": float("nan"),
            "iqr": float("nan"),
        }
    arr = sorted(values)
    mu = mean(arr)
    var = sum((x - mu) ** 2 for x in arr) / len(arr)
    p25 = percentile(arr, 0.25)
    p75 = percentile(arr, 0.75)
    return {
        "count": len(arr),
        "mean": mu,
        "median": median(arr),
        "p25": p25,
        "p75": p75,
        "p90": percentile(arr, 0.9),
        "max": max(arr),
        "std": math.sqrt(var),
        "iqr": p75 - p25,
    }


def bootstrap_ci(values: list[int], stat_func, n_boot: int = 2500, seed: int = BOOTSTRAP_SEED) -> tuple[float, float, float]:
    if not values:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    n = len(values)
    samples = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(float(stat_func(sample)))
    point = float(stat_func(values))
    lo = percentile(samples, 0.025)
    hi = percentile(samples, 0.975)
    return point, lo, hi


def _to_int(v: str | int | float | None) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def _is_finalized(row: dict[str, Any]) -> bool:
    event = row.get("event")
    if event is None:
        return False
    if isinstance(event, bool):
        return event
    if isinstance(event, (int, float)):
        return int(event) == 1
    return str(event).strip() == "1"


def _safe_round(value: float, digits: int = 2, default: float = 0.0) -> float:
    if math.isnan(value) or math.isinf(value):
        return default
    return round(value, digits)


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))


def _binary_rate_interval(successes: int, total: int, z_score: float = 1.96) -> tuple[float, float, float]:
    if total <= 0:
        return 0.0, 0.0, 0.0

    probability = _clamp01(successes / total)
    denominator = 1.0 + (z_score ** 2) / total
    center = (probability + (z_score ** 2) / (2.0 * total)) / denominator
    margin = (
        z_score
        * math.sqrt((probability * (1.0 - probability) + (z_score ** 2) / (4.0 * total)) / total)
        / denominator
    )
    low = _clamp01(center - margin)
    high = _clamp01(center + margin)
    return probability, low, high


def _confidence_band(
    sample_size: int,
    finalized_cases: int,
    ci_width: float,
    freshness_seconds: int | None,
) -> str:
    score = 0

    if sample_size >= 80:
        score += 2
    elif sample_size >= 30:
        score += 1

    if finalized_cases >= 40:
        score += 2
    elif finalized_cases >= 15:
        score += 1

    if ci_width <= 0.15:
        score += 2
    elif ci_width <= 0.30:
        score += 1

    if freshness_seconds is None or freshness_seconds <= 3 * 24 * 60 * 60:
        score += 1
    elif freshness_seconds > 14 * 24 * 60 * 60:
        score -= 1

    if score >= 6:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def filter_rows(
    rows: list[dict[str, str]],
    visa_types: set[str] | None = None,
    consulates: set[str] | None = None,
    statuses: set[str] | None = None,
    entries: set[str] | None = None,
    months: set[str] | None = None,
    majors: set[str] | None = None,
    major_categories_l1: set[str] | None = None,
    major_categories_l2: set[str] | None = None,
    employers: set[str] | None = None,
    detail_cities: set[str] | None = None,
    detail_states: set[str] | None = None,
    has_note: bool | None = None,
    search_text: str | None = None,
) -> list[dict[str, str]]:
    compact_search = re.sub(r"\s+", " ", search_text or "").strip().lower()
    search_terms = [term for term in compact_search.split(" ") if term]

    out: list[dict[str, str]] = []
    for r in rows:
        m = (r.get("check_date") or "")[:7]
        if visa_types and (r.get("visa_type") or "").upper() not in visa_types:
            continue
        if consulates and (r.get("consulate") or "") not in consulates:
            continue
        if statuses and (r.get("status") or "") not in statuses:
            continue
        if entries and (r.get("visa_entry") or "") not in entries:
            continue
        if months and m not in months:
            continue
        if major_categories_l1 and (r.get("major_category_l1") or "") not in major_categories_l1:
            continue
        if major_categories_l2 and (r.get("major_category_l2") or "") not in major_categories_l2:
            continue
        if majors and (r.get("major") or "") not in majors:
            continue
        if employers and (r.get("detail_employer") or "") not in employers:
            continue
        if detail_cities and (r.get("detail_city") or "") not in detail_cities:
            continue
        if detail_states and (r.get("detail_state") or "") not in detail_states:
            continue
        if has_note is True and not str(r.get("detail_note") or "").strip():
            continue
        if search_terms:
            searchable = " ".join(
                [
                    str(r.get("detail_note") or ""),
                    str(r.get("detail_employer") or ""),
                ]
            ).lower()
            if not all(term in searchable for term in search_terms):
                continue
        out.append(r)
    return out


def monthly_stats(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        month = (r.get("check_date") or "")[:7]
        if not month:
            continue
        groups.setdefault(month, []).append(r)

    result: list[dict[str, Any]] = []
    for month in sorted(groups.keys()):
        g = groups[month]
        finalized = [_to_int(x.get("waiting_days_calc")) for x in g if _is_finalized(x)]
        finalized_days = [x for x in finalized if x is not None]

        clear_n = sum(1 for x in g if x.get("status") == "Clear")
        reject_n = sum(1 for x in g if x.get("status") == "Reject")
        pending_n = sum(1 for x in g if x.get("status") not in {"Clear", "Reject"})
        total_n = len(g)

        s = stats(finalized_days)
        tail_n = sum(1 for x in finalized_days if x >= 90)

        result.append(
            {
                "submit_month": month,
                "total_cases": total_n,
                "clear_cases": clear_n,
                "reject_cases": reject_n,
                "pending_cases": pending_n,
                "clear_ratio": round(clear_n / total_n, 4) if total_n else 0.0,
                "pending_ratio": round(pending_n / total_n, 4) if total_n else 0.0,
                "maturity_ratio": round((clear_n + reject_n) / total_n, 4) if total_n else 0.0,
                "finalized_count": int(s["count"]),
                "median_days": round(s["median"], 2) if s["count"] else None,
                "p90_days": round(s["p90"], 2) if s["count"] else None,
                "long_tail_90plus_ratio": round(tail_n / len(finalized_days), 4) if finalized_days else None,
            }
        )
    return result


def overview_stats(rows: list[dict[str, str]]) -> dict[str, Any]:
    finalized_days = []
    pending_observed = []

    for r in rows:
        if _is_finalized(r):
            val = _to_int(r.get("waiting_days_calc"))
            if val is not None:
                finalized_days.append(val)
        else:
            val = _to_int(r.get("observed_days"))
            if val is not None:
                pending_observed.append(val)

    s = stats(finalized_days)
    m_point, m_lo, m_hi = bootstrap_ci(finalized_days, median)
    p90_fn = lambda x: percentile([float(v) for v in x], 0.9)
    p90_point, p90_lo, p90_hi = bootstrap_ci(finalized_days, p90_fn)

    total = len(rows)
    finalized_n = len(finalized_days)
    pending_n = len(pending_observed)
    tail_ratio = sum(1 for x in finalized_days if x >= 90) / finalized_n if finalized_n else float("nan")

    return {
        "total_cases": total,
        "finalized_cases": finalized_n,
        "pending_cases": pending_n,
        "maturity_ratio": round(finalized_n / total, 4) if total else 0.0,
        "median_days": _safe_round(m_point),
        "median_ci_low": _safe_round(m_lo),
        "median_ci_high": _safe_round(m_hi),
        "p90_days": _safe_round(p90_point),
        "p90_ci_low": _safe_round(p90_lo),
        "p90_ci_high": _safe_round(p90_hi),
        "mean_days": _safe_round(s["mean"]),
        "iqr_days": _safe_round(s["iqr"]),
        "std_days": _safe_round(s["std"]),
        "long_tail_90plus_ratio": round(tail_ratio, 4) if not math.isnan(tail_ratio) else 0.0,
    }


def sensitivity_stats(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    finalized = []
    pending_observed = []
    for r in rows:
        if _is_finalized(r):
            v = _to_int(r.get("waiting_days_calc"))
            if v is not None:
                finalized.append(v)
        else:
            v = _to_int(r.get("observed_days"))
            if v is not None:
                pending_observed.append(v)

    if not finalized:
        return []

    neutral = finalized + [int(median(finalized))] * len(pending_observed)
    aggressive = finalized + pending_observed

    def row(name: str, values: list[int]) -> dict[str, Any]:
        s = stats(values)
        tail = sum(1 for x in values if x >= 90) / len(values) if values else 0.0
        return {
            "scenario": name,
            "median_days": round(s["median"], 2),
            "p90_days": round(s["p90"], 2),
            "long_tail_90plus_ratio": round(tail, 4),
        }

    return [
        row("Conservative", finalized),
        row("Neutral", neutral),
        row("Aggressive", aggressive),
    ]


def cohort_stats(rows: list[dict[str, str]], key_field: str = "visa_type") -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        key = str(row.get(key_field) or "Unknown").strip() or "Unknown"
        groups.setdefault(key, []).append(row)

    result: list[dict[str, Any]] = []
    for key in sorted(groups.keys()):
        bucket = groups[key]
        total_n = len(bucket)
        finalized_days = [
            value
            for value in (_to_int(item.get("waiting_days_calc")) for item in bucket if _is_finalized(item))
            if value is not None
        ]
        finalized_n = len(finalized_days)
        pending_n = sum(1 for item in bucket if not _is_finalized(item))
        s = stats(finalized_days)
        tail_n = sum(1 for value in finalized_days if value >= 90)

        result.append(
            {
                "cohort": key,
                "total_cases": total_n,
                "finalized_cases": finalized_n,
                "pending_cases": pending_n,
                "maturity_ratio": round(finalized_n / total_n, 4) if total_n else 0.0,
                "median_days": round(s["median"], 2) if finalized_n else None,
                "p90_days": round(s["p90"], 2) if finalized_n else None,
                "long_tail_90plus_ratio": round(tail_n / finalized_n, 4) if finalized_n else None,
            }
        )

    return result


def distribution_stats(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    finalized_days = [
        value
        for value in (_to_int(row.get("waiting_days_calc")) for row in rows if _is_finalized(row))
        if value is not None
    ]
    total = len(finalized_days)
    ranges: list[tuple[str, int, int | None]] = [
        ("0-30", 0, 30),
        ("31-60", 31, 60),
        ("61-90", 61, 90),
        ("91-120", 91, 120),
        ("120+", 121, None),
    ]

    items: list[dict[str, Any]] = []
    for label, lower, upper in ranges:
        if upper is None:
            count = sum(1 for value in finalized_days if value >= lower)
        else:
            count = sum(1 for value in finalized_days if lower <= value <= upper)
        items.append(
            {
                "bucket": label,
                "count": count,
                "ratio": round(count / total, 4) if total else 0.0,
            }
        )
    return items


def comparison_stats(rows: list[dict[str, str]]) -> dict[str, Any]:
    month_rows: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        month = (row.get("check_date") or "")[:7]
        if month:
            month_rows.setdefault(month, []).append(row)

    ordered_months = sorted(month_rows.keys(), reverse=True)
    if len(ordered_months) < 2:
        return {
            "latest_month": ordered_months[0] if ordered_months else None,
            "baseline_month": None,
            "latest": None,
            "baseline": None,
            "delta": None,
        }

    latest_month = ordered_months[0]
    baseline_month = ordered_months[1]

    def metrics(month: str) -> dict[str, float]:
        rows_in_month = month_rows[month]
        overview = overview_stats(rows_in_month)
        return {
            "median_days": overview["median_days"],
            "p90_days": overview["p90_days"],
            "pending_ratio": round(
                overview["pending_cases"] / overview["total_cases"],
                4,
            )
            if overview["total_cases"]
            else 0.0,
        }

    latest = metrics(latest_month)
    baseline = metrics(baseline_month)
    return {
        "latest_month": latest_month,
        "baseline_month": baseline_month,
        "latest": latest,
        "baseline": baseline,
        "delta": {
            "median_days": round(latest["median_days"] - baseline["median_days"], 2),
            "p90_days": round(latest["p90_days"] - baseline["p90_days"], 2),
            "pending_ratio": round(latest["pending_ratio"] - baseline["pending_ratio"], 4),
        },
    }


def recommendation_stats(
    rows: list[dict[str, str]],
    *,
    data_freshness_seconds: int | None = None,
) -> dict[str, Any]:
    overview = overview_stats(rows)
    comparison = comparison_stats(rows)
    anomaly_rows = anomalies(rows, threshold_days=120, limit=200)

    sample_size = int(overview.get("total_cases") or 0)
    finalized_cases = int(overview.get("finalized_cases") or 0)
    pending_cases = int(overview.get("pending_cases") or 0)
    maturity_ratio = float(overview.get("maturity_ratio") or 0.0)
    insufficient_data = sample_size < 5 or finalized_cases < 5

    if sample_size == 0 or finalized_cases == 0:
        return {
            "summary": {
                "sample_size": sample_size,
                "finalized_cases": finalized_cases,
                "pending_cases": pending_cases,
                "maturity_ratio": round(maturity_ratio, 4),
                "confidence_band": "insufficient",
                "insufficient_data": True,
                "data_freshness_seconds": data_freshness_seconds,
            },
            "items": [],
        }

    clear_count = sum(1 for row in rows if str(row.get("status") or "").strip() == "Clear")
    reject_count = sum(1 for row in rows if str(row.get("status") or "").strip() == "Reject")
    finalized_total = clear_count + reject_count

    approval_estimate, approval_low, approval_high = _binary_rate_interval(clear_count, finalized_total)

    finalized_days = [
        value
        for value in (_to_int(row.get("waiting_days_calc")) for row in rows if _is_finalized(row))
        if value is not None
    ]
    within_90_count = sum(1 for value in finalized_days if value <= 90)
    within_90_estimate, within_90_low, within_90_high = _binary_rate_interval(within_90_count, len(finalized_days))

    long_tail_count = sum(1 for value in finalized_days if value >= 120)
    long_tail_estimate, long_tail_low, long_tail_high = _binary_rate_interval(long_tail_count, len(finalized_days))

    ci_width = approval_high - approval_low
    confidence_band = "insufficient" if insufficient_data else _confidence_band(
        sample_size,
        finalized_cases,
        ci_width,
        data_freshness_seconds,
    )

    pending_ratio_delta = 0.0
    comparison_delta = comparison.get("delta")
    if isinstance(comparison_delta, dict):
        pending_ratio_delta = float(comparison_delta.get("pending_ratio") or 0.0)

    p90_days = float(overview.get("p90_days") or 0.0)

    items = [
        {
            "id": "approval_probability",
            "estimate": round(approval_estimate, 4),
            "probability_interval_low": round(approval_low, 4),
            "probability_interval_high": round(approval_high, 4),
            "level": confidence_band,
            "direction": "higher_is_better",
            "reasons": ["clear_ratio", "maturity_ratio", "sample_size"],
            "evidence": [
                {"metric": "clear_ratio", "value": round(approval_estimate, 4), "note": None},
                {"metric": "finalized_cases", "value": float(finalized_cases), "note": None},
                {"metric": "maturity_ratio", "value": round(maturity_ratio, 4), "note": None},
            ],
        },
        {
            "id": "within_90_days_probability",
            "estimate": round(within_90_estimate, 4),
            "probability_interval_low": round(within_90_low, 4),
            "probability_interval_high": round(within_90_high, 4),
            "level": confidence_band,
            "direction": "higher_is_better",
            "reasons": ["p90_days", "long_tail_90plus_ratio", "sample_size"],
            "evidence": [
                {"metric": "p90_days", "value": round(p90_days, 2), "note": None},
                {
                    "metric": "long_tail_90plus_ratio",
                    "value": round(float(overview.get("long_tail_90plus_ratio") or 0.0), 4),
                    "note": None,
                },
                {"metric": "sample_size", "value": float(sample_size), "note": None},
            ],
        },
        {
            "id": "long_tail_risk",
            "estimate": round(long_tail_estimate, 4),
            "probability_interval_low": round(long_tail_low, 4),
            "probability_interval_high": round(long_tail_high, 4),
            "level": confidence_band,
            "direction": "lower_is_better",
            "reasons": ["long_tail_90plus_ratio", "pending_ratio", "anomaly_count"],
            "evidence": [
                {
                    "metric": "long_tail_90plus_ratio",
                    "value": round(float(overview.get("long_tail_90plus_ratio") or 0.0), 4),
                    "note": None,
                },
                {"metric": "pending_ratio", "value": round(pending_ratio_delta, 4), "note": "delta_vs_previous_month"},
                {"metric": "anomaly_count", "value": float(len(anomaly_rows)), "note": None},
            ],
        },
    ]

    return {
        "summary": {
            "sample_size": sample_size,
            "finalized_cases": finalized_cases,
            "pending_cases": pending_cases,
            "maturity_ratio": round(maturity_ratio, 4),
            "confidence_band": confidence_band,
            "insufficient_data": insufficient_data,
            "data_freshness_seconds": data_freshness_seconds,
        },
        "items": items,
    }


def anomalies(rows: list[dict[str, str]], threshold_days: int = 120, limit: int = 50) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        finalized = _is_finalized(row)
        duration = _to_int(row.get("waiting_days_calc" if finalized else "observed_days"))
        if duration is None or duration < threshold_days:
            continue

        result.append(
            {
                "case_number": row.get("case_number") or "",
                "visa_type": row.get("visa_type") or "",
                "consulate": row.get("consulate") or "",
                "status": row.get("status") or "",
                "check_date": row.get("check_date") or "",
                "days": duration,
                "reason": "finalized_long_wait" if finalized else "pending_long_wait",
                "detail_url": row.get("detail_url") or "",
                "update_url": row.get("update_url") or "",
            }
        )

    result.sort(key=lambda item: int(item["days"]), reverse=True)
    return result[: max(1, limit)]


def options(rows: list[dict[str, str]]) -> dict[str, Any]:
    months = sorted({(r.get("check_date") or "")[:7] for r in rows if r.get("check_date")}, reverse=True)
    visa_types = sorted({(r.get("visa_type") or "").upper() for r in rows if r.get("visa_type")})
    consulates = sorted({r.get("consulate") or "" for r in rows if r.get("consulate")})
    statuses = sorted({r.get("status") or "" for r in rows if r.get("status")})
    entries = sorted({r.get("visa_entry") or "" for r in rows if r.get("visa_entry")})
    major_categories_l1 = sorted({r.get("major_category_l1") or "" for r in rows if r.get("major_category_l1")})
    major_categories_l2 = sorted({r.get("major_category_l2") or "" for r in rows if r.get("major_category_l2")})
    major_category_mapping: dict[str, set[str]] = {}
    for row in rows:
        category_l1 = str(row.get("major_category_l1") or "").strip()
        category_l2 = str(row.get("major_category_l2") or "").strip()
        if not category_l1 or not category_l2:
            continue
        major_category_mapping.setdefault(category_l1, set()).add(category_l2)

    major_category_mapping_sorted = {
        category_l1: sorted(values)
        for category_l1, values in sorted(major_category_mapping.items(), key=lambda item: item[0])
    }

    majors = sorted({r.get("major") or "" for r in rows if r.get("major")})
    employers = sorted({r.get("detail_employer") or "" for r in rows if r.get("detail_employer")})
    detail_cities = sorted({r.get("detail_city") or "" for r in rows if r.get("detail_city")})
    detail_states = sorted({r.get("detail_state") or "" for r in rows if r.get("detail_state")})
    return {
        "months": months,
        "visa_types": visa_types,
        "consulates": consulates,
        "statuses": statuses,
        "entries": entries,
        "major_categories_l1": major_categories_l1,
        "major_categories_l2": major_categories_l2,
        "major_category_mapping": major_category_mapping_sorted,
        "majors": majors,
        "employers": employers,
        "detail_cities": detail_cities,
        "detail_states": detail_states,
    }


def consulate_groups(rows: list[dict[str, str]]) -> dict[str, Any]:
    all_consulates = sorted({r.get("consulate") or "" for r in rows if r.get("consulate")})

    rules: list[tuple[str, str, set[str]]] = [
        (
            "china",
            "中国",
            {"BeiJing", "ShangHai", "GuangZhou", "ShenYang", "WuHan", "HongKong"},
        ),
        (
            "canada",
            "加拿大",
            {"Toronto", "Ottawa", "Vancouver", "Calgary"},
        ),
        ("europe", "欧洲", {"Europe"}),
        ("other", "其他", {"Others"}),
    ]

    seen: set[str] = set()
    groups: list[dict[str, Any]] = []
    for key, label, pool in rules:
        matched = sorted([c for c in all_consulates if c in pool])
        if not matched:
            continue
        seen.update(matched)
        groups.append({"key": key, "label": label, "consulates": matched})

    ungrouped = sorted([c for c in all_consulates if c not in seen])
    if ungrouped:
        groups.append({"key": "ungrouped", "label": "未分组", "consulates": ungrouped})

    return {"groups": groups, "ungrouped": ungrouped}


def markdown_report(rows: list[dict[str, str]]) -> str:
    ov = overview_stats(rows)
    monthly = monthly_stats(rows)
    sensitivity = sensitivity_stats(rows)

    report = []
    report.append("# Checkee 全签证实时分析报告")
    report.append("")
    report.append(f"- 样本总量：{ov['total_cases']}")
    report.append(f"- 结案样本：{ov['finalized_cases']}，Pending：{ov['pending_cases']}")
    report.append(f"- 中位数：{ov['median_days']} 天 (95%CI {ov['median_ci_low']}-{ov['median_ci_high']})")
    report.append(f"- P90：{ov['p90_days']} 天 (95%CI {ov['p90_ci_low']}-{ov['p90_ci_high']})")
    report.append(f"- 长尾(>=90天)：{ov['long_tail_90plus_ratio']:.2%}")
    report.append("")

    report.append("## 月度统计")
    report.append("| Month | Total | Clear | Reject | Pending | Pending% | Median | P90 | >=90d% |")
    report.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in monthly:
        report.append(
            "| {submit_month} | {total_cases} | {clear_cases} | {reject_cases} | {pending_cases} | {pending_ratio:.2%} | {median_days} | {p90_days} | {long_tail_90plus_ratio} |".format(
                submit_month=r["submit_month"],
                total_cases=r["total_cases"],
                clear_cases=r["clear_cases"],
                reject_cases=r["reject_cases"],
                pending_cases=r["pending_cases"],
                pending_ratio=r["pending_ratio"],
                median_days=r["median_days"] if r["median_days"] is not None else "-",
                p90_days=r["p90_days"] if r["p90_days"] is not None else "-",
                long_tail_90plus_ratio=(f"{r['long_tail_90plus_ratio']:.2%}" if r["long_tail_90plus_ratio"] is not None else "-"),
            )
        )

    report.append("")
    report.append("## 敏感性区间")
    report.append("| Scenario | Median | P90 | >=90d |")
    report.append("|---|---:|---:|---:|")
    for s in sensitivity:
        report.append(
            f"| {s['scenario']} | {s['median_days']} | {s['p90_days']} | {s['long_tail_90plus_ratio']:.2%} |"
        )

    return "\n".join(report)

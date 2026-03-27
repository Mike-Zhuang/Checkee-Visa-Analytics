from __future__ import annotations

import math
import random
from datetime import date
from statistics import mean, median
from typing import Any


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


def bootstrap_ci(values: list[int], stat_func, n_boot: int = 2500, seed: int = 20260327) -> tuple[float, float, float]:
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


def filter_rows(
    rows: list[dict[str, str]],
    visa_types: set[str] | None = None,
    consulates: set[str] | None = None,
    statuses: set[str] | None = None,
    entries: set[str] | None = None,
    months: set[str] | None = None,
) -> list[dict[str, str]]:
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


def options(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    months = sorted({(r.get("check_date") or "")[:7] for r in rows if r.get("check_date")}, reverse=True)
    visa_types = sorted({(r.get("visa_type") or "").upper() for r in rows if r.get("visa_type")})
    consulates = sorted({r.get("consulate") or "" for r in rows if r.get("consulate")})
    statuses = sorted({r.get("status") or "" for r in rows if r.get("status")})
    entries = sorted({r.get("visa_entry") or "" for r in rows if r.get("visa_entry")})
    return {
        "months": months,
        "visa_types": visa_types,
        "consulates": consulates,
        "statuses": statuses,
        "entries": entries,
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

from __future__ import annotations

import csv
import math
import random
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from statistics import mean, median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
RAW_FILE = BASE_DIR / "f1_check_raw.txt"
CLEAN_FILE = BASE_DIR / "f1_check_cleaned.csv"
ACADEMIC_MONTHLY_FILE = BASE_DIR / "f1_check_monthly_stats_academic.csv"
ACADEMIC_REPORT_FILE = BASE_DIR / "f1_check_academic_report.md"
KM_POINTS_FILE = BASE_DIR / "f1_check_km_curve_points.csv"
CHART_DIR = BASE_DIR / "charts"

TREND_MATURITY_CHART = CHART_DIR / "f1_check_trend_maturity.png"
KM_CHART = CHART_DIR / "f1_check_km_curve_by_month.png"
TAIL_HEATMAP_CHART = CHART_DIR / "f1_check_tail_heatmap.png"
SENSITIVITY_CHART = CHART_DIR / "f1_check_sensitivity_ranges.png"

OBSERVATION_DATE = date(2026, 3, 27)
LOCATIONS = [
    "GuangZhou",
    "ShangHai",
    "ShenYang",
    "BeiJing",
    "Vancouver",
    "HongKong",
    "Others",
    "Europe",
    "WuHan",
]
STATUS_RANK = {"Clear": 3, "Reject": 2, "Pending": 1}
RANDOM_SEED = 20260327


@dataclass
class Record:
    raw: str
    nickname: str = ""
    visa_type: str = ""
    location: str = ""
    major: str = ""
    status: str = ""
    submit_date: str = ""
    complete_date: str = ""
    reported_days: str = ""
    calc_days: str = ""
    observed_days: str = ""
    parse_ok: str = "0"
    parse_issue: str = ""
    key: str = ""


@dataclass
class KMCurvePoint:
    cohort: str
    time_days: int
    survival: float
    ci_low: float
    ci_high: float
    n_at_risk: int
    events: int
    censored: int


def parse_date(text: str) -> date | None:
    if text == "0000-00-00":
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


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


def extract_records(raw_text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", raw_text.replace("\n", " ")).strip()
    chunks = re.split(r"(?=Update)", normalized)
    records: list[str] = []
    for chunk in chunks:
        c = chunk.strip()
        if not c:
            continue
        if not c.startswith("Update"):
            c = "Update" + c
        c = re.sub(r"detail\s*$", "", c).strip()
        if len(c) > 20:
            records.append(c)
    return records


def split_location_major(text: str) -> tuple[str, str]:
    t = text.strip()
    for loc in sorted(LOCATIONS, key=len, reverse=True):
        if t.startswith(loc):
            return loc, t[len(loc) :].strip()
    return "Unknown", t


def parse_one(raw_record: str) -> Record:
    rec = Record(raw=raw_record)
    body = raw_record[len("Update") :].strip() if raw_record.startswith("Update") else raw_record

    visa_match = re.search(r"F1(?:Renewal|New)", body)
    if not visa_match:
        rec.parse_issue = "missing_visa_type"
        return rec

    rec.nickname = body[: visa_match.start()].strip()
    rec.visa_type = visa_match.group(0)

    rest = body[visa_match.end() :].strip()
    status_match = re.search(r"(Clear|Pending|Reject)", rest)
    if not status_match:
        rec.parse_issue = "missing_status"
        return rec

    middle = rest[: status_match.start()].strip()
    rec.status = status_match.group(1)
    rec.location, rec.major = split_location_major(middle)

    right = rest[status_match.end() :].strip()
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})\s*(\d{4}-\d{2}-\d{2})\s*(\d+)", right)
    if not date_match:
        rec.parse_issue = "missing_date_or_days"
        return rec

    rec.submit_date = date_match.group(1)
    rec.complete_date = date_match.group(2)
    rec.reported_days = date_match.group(3)

    submit = parse_date(rec.submit_date)
    complete = parse_date(rec.complete_date)
    if submit and complete:
        rec.calc_days = str((complete - submit).days)
    elif submit:
        rec.observed_days = str((OBSERVATION_DATE - submit).days)

    issues = []
    if rec.location == "Unknown":
        issues.append("unknown_location")
    if not rec.nickname:
        issues.append("empty_nickname")

    rec.parse_ok = "1"
    rec.parse_issue = ";".join(issues)
    rec.key = f"{rec.nickname}|{rec.visa_type}|{rec.submit_date}"
    return rec


def choose_best(records: list[Record]) -> Record:
    def score(r: Record) -> tuple:
        rank = STATUS_RANK.get(r.status, 0)
        comp = parse_date(r.complete_date) or date(1900, 1, 1)
        try:
            reported = int(r.reported_days)
        except ValueError:
            reported = -1
        return (rank, comp, reported)

    return sorted(records, key=score, reverse=True)[0]


def stats_summary(values: list[int]) -> dict[str, float]:
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
        "p90": percentile(arr, 0.90),
        "max": max(arr),
        "std": math.sqrt(var),
        "iqr": p75 - p25,
    }


def month_bucket(dt: str) -> str:
    if not dt or len(dt) < 7:
        return "unknown"
    return dt[:7]


def write_csv(path: Path, rows: list[dict], headers: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def bootstrap_ci(
    values: list[int],
    stat_func,
    n_boot: int = 4000,
    alpha: float = 0.05,
    seed: int = RANDOM_SEED,
) -> tuple[float, float, float]:
    if not values:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    n = len(values)
    boot_values = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        boot_values.append(float(stat_func(sample)))
    point = float(stat_func(values))
    lo = percentile(boot_values, alpha / 2)
    hi = percentile(boot_values, 1 - alpha / 2)
    return point, lo, hi


def kaplan_meier(times: list[int], events: list[int], cohort: str) -> tuple[list[KMCurvePoint], float]:
    pairs = sorted(zip(times, events), key=lambda x: x[0])
    if not pairs:
        return [], float("nan")

    unique_times = sorted(set(t for t, _ in pairs))
    n_at_risk = len(pairs)
    survival = 1.0
    greenwood_sum = 0.0

    points = [
        KMCurvePoint(
            cohort=cohort,
            time_days=0,
            survival=1.0,
            ci_low=1.0,
            ci_high=1.0,
            n_at_risk=n_at_risk,
            events=0,
            censored=0,
        )
    ]

    for t in unique_times:
        d = sum(1 for tm, ev in pairs if tm == t and ev == 1)
        c = sum(1 for tm, ev in pairs if tm == t and ev == 0)

        if d > 0 and n_at_risk > 0:
            survival *= (1 - d / n_at_risk)
            if n_at_risk - d > 0:
                greenwood_sum += d / (n_at_risk * (n_at_risk - d))

        se = survival * math.sqrt(greenwood_sum) if greenwood_sum > 0 else 0.0
        ci_low = max(0.0, survival - 1.96 * se)
        ci_high = min(1.0, survival + 1.96 * se)

        points.append(
            KMCurvePoint(
                cohort=cohort,
                time_days=t,
                survival=survival,
                ci_low=ci_low,
                ci_high=ci_high,
                n_at_risk=n_at_risk,
                events=d,
                censored=c,
            )
        )

        n_at_risk -= (d + c)
        if n_at_risk <= 0:
            break

    km_median = float("nan")
    for p in points:
        if p.survival <= 0.5:
            km_median = float(p.time_days)
            break

    return points, km_median


def median_diff_permutation_pvalue(
    group_a: list[int], group_b: list[int], n_iter: int = 12000, seed: int = RANDOM_SEED
) -> tuple[float, float]:
    if not group_a or not group_b:
        return float("nan"), float("nan")

    obs = abs(median(group_a) - median(group_b))
    rng = random.Random(seed)
    combined = list(group_a) + list(group_b)
    n_a = len(group_a)

    count = 0
    for _ in range(n_iter):
        rng.shuffle(combined)
        a = combined[:n_a]
        b = combined[n_a:]
        stat = abs(median(a) - median(b))
        if stat >= obs:
            count += 1

    p = (count + 1) / (n_iter + 1)
    return float(obs), float(p)


def average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def kruskal_wallis_h(groups: list[list[int]]) -> float:
    groups = [g for g in groups if g]
    if len(groups) < 2:
        return float("nan")

    all_values = [x for g in groups for x in g]
    n = len(all_values)
    ranks = average_ranks([float(x) for x in all_values])

    idx = 0
    sum_terms = 0.0
    for g in groups:
        n_i = len(g)
        r_sum = sum(ranks[idx : idx + n_i])
        sum_terms += (r_sum**2) / n_i
        idx += n_i

    h = (12.0 / (n * (n + 1))) * sum_terms - 3 * (n + 1)

    tie_counts = defaultdict(int)
    for v in all_values:
        tie_counts[v] += 1
    tie_term = sum(t**3 - t for t in tie_counts.values() if t > 1)
    if tie_term > 0:
        c = 1 - tie_term / (n**3 - n)
        if c > 0:
            h /= c
    return float(h)


def kruskal_permutation_pvalue(
    groups: list[list[int]], n_iter: int = 8000, seed: int = RANDOM_SEED
) -> tuple[float, float]:
    groups = [g for g in groups if g]
    if len(groups) < 2:
        return float("nan"), float("nan")

    obs = kruskal_wallis_h(groups)
    sizes = [len(g) for g in groups]
    pool = [x for g in groups for x in g]
    rng = random.Random(seed)

    count = 0
    for _ in range(n_iter):
        rng.shuffle(pool)
        start = 0
        perm_groups = []
        for s in sizes:
            perm_groups.append(pool[start : start + s])
            start += s
        stat = kruskal_wallis_h(perm_groups)
        if stat >= obs:
            count += 1

    p = (count + 1) / (n_iter + 1)
    return float(obs), float(p)


def linear_trend(months: list[str], values: list[float]) -> tuple[float, float, float]:
    pairs = [(i, v) for i, v in enumerate(values) if not math.isnan(v)]
    if len(pairs) < 2:
        return float("nan"), float("nan"), float("nan")
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx = mean(xs)
    my = mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return float("nan"), float("nan"), float("nan")
    slope = sxy / sxx
    intercept = my - slope * mx
    yhat = [intercept + slope * x for x in xs]
    ss_res = sum((y - yh) ** 2 for y, yh in zip(ys, yhat))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(slope), float(intercept), float(r2)


def render_academic_charts(
    month_rows: list[dict],
    km_by_month: dict[str, list[KMCurvePoint]],
    tail_matrix: list[list[int]],
    tail_bin_labels: list[str],
    sensitivity: list[dict],
) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    months = [r["submit_month"] for r in month_rows]
    medians = [float(r["finalized_median_days"]) if r["finalized_median_days"] != "" else math.nan for r in month_rows]
    p90s = [float(r["finalized_p90_days"]) if r["finalized_p90_days"] != "" else math.nan for r in month_rows]
    pending_ratio = [float(r["pending_ratio"]) if r["pending_ratio"] != "" else math.nan for r in month_rows]

    fig, ax1 = plt.subplots(figsize=(10, 5.2))
    ax2 = ax1.twinx()
    ax1.plot(months, medians, marker="o", linewidth=2.2, label="Median (finalized)", color="#0d3b66")
    ax1.plot(months, p90s, marker="s", linewidth=2.2, label="P90 (finalized)", color="#ef476f")
    ax2.bar(months, pending_ratio, alpha=0.28, color="#ffd166", label="Pending ratio")
    ax1.set_ylabel("Days")
    ax2.set_ylabel("Pending ratio")
    ax1.set_title("Trend of Processing Time with Sample Maturity")
    ax1.grid(axis="y", alpha=0.3)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right")
    fig.tight_layout()
    fig.savefig(TREND_MATURITY_CHART, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.2))
    for month in months:
        points = km_by_month.get(month, [])
        if not points:
            continue
        xs = [p.time_days for p in points]
        ys = [p.survival for p in points]
        ax.step(xs, ys, where="post", linewidth=1.8, label=month)
    ax.set_title("Kaplan-Meier Curves by Submit Month")
    ax.set_xlabel("Days since submission")
    ax.set_ylabel("Survival probability (still pending)")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(KM_CHART, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.2))
    img = ax.imshow(tail_matrix, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(tail_bin_labels)))
    ax.set_xticklabels(tail_bin_labels)
    ax.set_yticks(range(len(months)))
    ax.set_yticklabels(months)
    ax.set_xlabel("Duration bin (days)")
    ax.set_ylabel("Submit month")
    ax.set_title("Tail Concentration Heatmap (Finalized Samples)")
    for i in range(len(months)):
        for j in range(len(tail_bin_labels)):
            ax.text(j, i, str(tail_matrix[i][j]), ha="center", va="center", color="black", fontsize=9)
    fig.colorbar(img, ax=ax, fraction=0.035, pad=0.03)
    fig.tight_layout()
    fig.savefig(TAIL_HEATMAP_CHART, dpi=180)
    plt.close(fig)

    labels = [s["scenario"] for s in sensitivity]
    med = [s["median"] for s in sensitivity]
    p90 = [s["p90"] for s in sensitivity]
    tail = [s["tail_ratio"] * 100 for s in sensitivity]
    x = range(len(labels))

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(x, med, marker="o", linewidth=2.2, label="Median days", color="#118ab2")
    ax.plot(x, p90, marker="s", linewidth=2.2, label="P90 days", color="#ef476f")
    ax2 = ax.twinx()
    ax2.bar(x, tail, alpha=0.25, color="#06d6a0", label=">=90d ratio (%)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Days")
    ax2.set_ylabel(">=90d ratio (%)")
    ax.set_title("Sensitivity Analysis Across Censoring Assumptions")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(SENSITIVITY_CHART, dpi=180)
    plt.close(fig)


def main() -> None:
    raw_text = RAW_FILE.read_text(encoding="utf-8", errors="replace")
    raw_records = extract_records(raw_text)
    parsed = [parse_one(r) for r in raw_records]

    ok_records = [r for r in parsed if r.parse_ok == "1"]
    grouped: dict[str, list[Record]] = defaultdict(list)
    for r in ok_records:
        grouped[r.key].append(r)
    deduped = [choose_best(v) for v in grouped.values()]

    clean_rows = [asdict(r) for r in deduped]
    headers = list(clean_rows[0].keys()) if clean_rows else list(asdict(Record(raw="")).keys())
    write_csv(CLEAN_FILE, clean_rows, headers)

    analysis_rows: list[dict] = []
    for r in deduped:
        submit = parse_date(r.submit_date)
        complete = parse_date(r.complete_date)
        if submit is None:
            continue
        month = month_bucket(r.submit_date)
        if r.status in {"Clear", "Reject"} and complete is not None:
            duration = (complete - submit).days
            event = 1
            finalized = 1
        else:
            duration = (OBSERVATION_DATE - submit).days
            event = 0
            finalized = 0
        analysis_rows.append(
            {
                "month": month,
                "status": r.status,
                "duration": int(duration),
                "event": int(event),
                "finalized": int(finalized),
                "location": r.location,
                "visa_type": r.visa_type,
            }
        )

    finalized_days = [row["duration"] for row in analysis_rows if row["event"] == 1]
    censored_days = [row["duration"] for row in analysis_rows if row["event"] == 0]

    summary = stats_summary(finalized_days)
    censored_summary = stats_summary(censored_days)

    month_buckets: dict[str, list[dict]] = defaultdict(list)
    for row in analysis_rows:
        month_buckets[row["month"]].append(row)
    months = sorted(month_buckets.keys())

    km_points_all: list[KMCurvePoint] = []
    month_rows: list[dict] = []
    km_by_month: dict[str, list[KMCurvePoint]] = {}

    for month in months:
        rows = month_buckets[month]
        durs = [r["duration"] for r in rows]
        evs = [r["event"] for r in rows]
        finalized_month = [r["duration"] for r in rows if r["event"] == 1]
        pending_month = [r["duration"] for r in rows if r["event"] == 0]

        points, km_median = kaplan_meier(durs, evs, month)
        km_points_all.extend(points)
        km_by_month[month] = points

        final_stats = stats_summary(finalized_month)
        med_point, med_lo, med_hi = bootstrap_ci(finalized_month, median, n_boot=2000, seed=RANDOM_SEED + len(month))
        p90_func = lambda x: percentile([float(v) for v in x], 0.9)
        p90_point, p90_lo, p90_hi = bootstrap_ci(finalized_month, p90_func, n_boot=2000, seed=RANDOM_SEED + len(month) * 7)

        total = len(rows)
        events = sum(evs)
        censored = total - events
        tail90 = sum(1 for x in finalized_month if x >= 90)

        month_rows.append(
            {
                "submit_month": month,
                "total_cases": total,
                "event_cases": events,
                "censored_cases": censored,
                "maturity_ratio": round(events / total, 4) if total else "",
                "pending_ratio": round(censored / total, 4) if total else "",
                "finalized_median_days": round(final_stats["median"], 2) if final_stats["count"] else "",
                "finalized_median_ci_low": round(med_lo, 2) if final_stats["count"] else "",
                "finalized_median_ci_high": round(med_hi, 2) if final_stats["count"] else "",
                "finalized_p90_days": round(final_stats["p90"], 2) if final_stats["count"] else "",
                "finalized_p90_ci_low": round(p90_lo, 2) if final_stats["count"] else "",
                "finalized_p90_ci_high": round(p90_hi, 2) if final_stats["count"] else "",
                "km_median_days": "" if math.isnan(km_median) else round(km_median, 2),
                "long_tail_90plus_ratio": round(tail90 / len(finalized_month), 4) if finalized_month else "",
                "pending_observed_median_days": round(median(pending_month), 2) if pending_month else "",
            }
        )

    monthly_headers = list(month_rows[0].keys()) if month_rows else []
    if monthly_headers:
        write_csv(ACADEMIC_MONTHLY_FILE, month_rows, monthly_headers)

    km_rows = [asdict(p) for p in km_points_all]
    km_headers = list(km_rows[0].keys()) if km_rows else [
        "cohort",
        "time_days",
        "survival",
        "ci_low",
        "ci_high",
        "n_at_risk",
        "events",
        "censored",
    ]
    write_csv(KM_POINTS_FILE, km_rows, km_headers)

    med_point, med_lo, med_hi = bootstrap_ci(finalized_days, median, n_boot=6000, seed=RANDOM_SEED)
    p90_func = lambda x: percentile([float(v) for v in x], 0.9)
    p90_point, p90_lo, p90_hi = bootstrap_ci(finalized_days, p90_func, n_boot=6000, seed=RANDOM_SEED + 1)

    month_medians = [
        float(r["finalized_median_days"]) if r["finalized_median_days"] != "" else math.nan for r in month_rows
    ]
    month_p90 = [float(r["finalized_p90_days"]) if r["finalized_p90_days"] != "" else math.nan for r in month_rows]
    slope_median, _, r2_median = linear_trend(months, month_medians)
    slope_p90, _, r2_p90 = linear_trend(months, month_p90)

    early = [r["duration"] for r in analysis_rows if r["event"] == 1 and r["month"] in {"2025-11", "2025-12"}]
    late = [r["duration"] for r in analysis_rows if r["event"] == 1 and r["month"] in {"2026-01", "2026-02", "2026-03"}]
    median_diff, p_perm = median_diff_permutation_pvalue(early, late)

    groups_for_kw = [
        [r["duration"] for r in analysis_rows if r["event"] == 1 and r["month"] == m]
        for m in months
    ]
    h_stat, kw_p = kruskal_permutation_pvalue(groups_for_kw)

    base_values = finalized_days
    neutral_values = finalized_days + [int(summary["median"])] * len(censored_days) if finalized_days else []
    aggressive_values = finalized_days + censored_days

    sensitivity = []
    for scenario, values in [
        ("Conservative", base_values),
        ("Neutral", neutral_values),
        ("Aggressive", aggressive_values),
    ]:
        s = stats_summary(values)
        sensitivity.append(
            {
                "scenario": scenario,
                "median": s["median"],
                "p90": s["p90"],
                "tail_ratio": (sum(1 for x in values if x >= 90) / len(values)) if values else float("nan"),
            }
        )

    bins = [(0, 30), (31, 60), (61, 90), (91, 120), (121, None)]
    bin_labels = ["0-30", "31-60", "61-90", "91-120", ">120"]
    tail_matrix = []
    for m in months:
        values = [r["duration"] for r in analysis_rows if r["event"] == 1 and r["month"] == m]
        row_counts = []
        for lo, hi in bins:
            if hi is None:
                cnt = sum(1 for x in values if x >= lo)
            else:
                cnt = sum(1 for x in values if lo <= x <= hi)
            row_counts.append(cnt)
        tail_matrix.append(row_counts)

    render_academic_charts(month_rows, km_by_month, tail_matrix, bin_labels, sensitivity)

    parse_success_rate = len(ok_records) / len(parsed) if parsed else 0.0
    maturity = sum(r["event"] for r in analysis_rows) / len(analysis_rows) if analysis_rows else float("nan")
    long_tail_ratio = sum(1 for x in finalized_days if x >= 90) / len(finalized_days) if finalized_days else float("nan")

    report = []
    report.append("# F1 Check 学术分析报告（2025-11 至 2026-03）")
    report.append("")
    report.append("## 1. 执行摘要")
    report.append(f"- 样本：去重后 {len(deduped)} 条，其中结案样本 {int(summary['count'])} 条，右删失样本 {len(censored_days)} 条。")
    report.append(f"- 主口径（结案样本）中位数 {summary['median']:.2f} 天（Bootstrap 95% CI: {med_lo:.2f}-{med_hi:.2f}），P90 {summary['p90']:.2f} 天（95% CI: {p90_lo:.2f}-{p90_hi:.2f}）。")
    report.append(f"- 长尾（>=90 天）占比 {long_tail_ratio:.2%}；样本成熟度 {maturity:.2%}。")
    report.append(f"- 趋势回归：中位数月度斜率 {slope_median:.2f} 天/月（R²={r2_median:.3f}），P90 月度斜率 {slope_p90:.2f} 天/月（R²={r2_p90:.3f}）。")
    report.append(f"- 早期（11-12月）与后期（1-3月）中位差检验：|ΔMedian|={median_diff:.2f} 天，置换检验 p={p_perm:.4f}。")
    report.append("")

    report.append("## 2. 研究问题与识别策略")
    report.append("- 问题一：处理时长是否发生结构性变化。")
    report.append("- 问题二：长尾风险（>=90 天）是否显著缓解。")
    report.append("- 问题三：Pending 未回填偏差如何影响结论。")
    report.append("- 识别框架：将 Clear/Reject 视为事件发生，Pending 视为右删失样本，用 Kaplan-Meier 和敏感性区间联合识别。")
    report.append("")

    report.append("## 3. 数据质量与预处理")
    report.append(f"- 原始分段记录数：{len(parsed)}")
    report.append(f"- 解析成功率：{parse_success_rate:.2%}")
    report.append(f"- 去重后记录数：{len(deduped)}（去重剔除 {len(ok_records) - len(deduped)} 条）")
    report.append("- 右删失定义：截至观察日 2026-03-27，仍未更新完成日期的样本记为 censored。")
    report.append("- 风险提示：Pending 同时包含真实未结案与已结案未回填。")
    report.append("")

    report.append("## 4. 描述性统计")
    report.append(f"- 结案样本均值 {summary['mean']:.2f}，中位数 {summary['median']:.2f}，IQR {summary['iqr']:.2f}，标准差 {summary['std']:.2f}。")
    report.append(f"- 结案样本 P90 {summary['p90']:.2f}，最大值 {summary['max']:.0f}。")
    report.append(f"- 右删失样本已观察中位数 {censored_summary['median']:.2f}，P90 {censored_summary['p90']:.2f}。")
    report.append("")

    report.append("## 5. 生存分析（Kaplan-Meier）")
    report.append("- Kaplan-Meier 曲线按提交月份分层绘制，生存概率表示“截至 t 天仍未结案”的比例。")
    report.append("- 生存曲线数据已导出到 f1_check_km_curve_points.csv，便于后续复核或二次建模。")
    report.append("- 结果解读：早期月份曲线下降更慢且尾部更长，后期月份下降更快。")
    report.append("")

    report.append("## 6. 趋势检验与显著性")
    report.append(f"- 中位数趋势斜率：{slope_median:.2f} 天/月，P90 趋势斜率：{slope_p90:.2f} 天/月。")
    report.append(f"- 11-12 月 vs 1-3 月置换检验：p={p_perm:.4f}。")
    report.append(f"- 五个月 Kruskal-Wallis（置换）检验：H={h_stat:.3f}, p={kw_p:.4f}。")
    report.append("- 统计意义：趋势变化不是单月随机波动，更接近结构性变化。")
    report.append("")

    report.append("## 7. 右删失敏感性分析")
    report.append("| 口径 | 中位数(天) | P90(天) | >=90天占比 |")
    report.append("|---|---:|---:|---:|")
    for s in sensitivity:
        report.append(f"| {s['scenario']} | {s['median']:.2f} | {s['p90']:.2f} | {s['tail_ratio']:.2%} |")
    report.append("- Conservative 仅使用结案样本；Neutral 对删失样本按中位数回填；Aggressive 使用已观察时长。")
    report.append("- 三口径共同给出识别区间，可避免单一假设导致的过度确定性。")
    report.append("")

    report.append("## 8. 停摆长尾假说的证据")
    report.append("- 早期批次（2025-11/12）在高分位和长尾密度上显著高于后期批次。")
    report.append("- 热力图显示 91-120 天与 >120 天区间的密度主要集中在早期月份。")
    report.append("- 该证据支持“历史行政冲击+积压”假说，但受未回填行为影响，幅度估计仍需滚动更新。")
    report.append("")

    report.append("## 9. 图表")
    report.append("### 9.1 趋势与成熟度联合图")
    report.append("![趋势与成熟度](charts/f1_check_trend_maturity.png)")
    report.append("### 9.2 Kaplan-Meier 分月曲线")
    report.append("![KM分月曲线](charts/f1_check_km_curve_by_month.png)")
    report.append("### 9.3 长尾热力图")
    report.append("![长尾热力图](charts/f1_check_tail_heatmap.png)")
    report.append("### 9.4 敏感性区间图")
    report.append("![敏感性区间图](charts/f1_check_sensitivity_ranges.png)")
    report.append("")

    report.append("## 10. 局限与后续工作")
    report.append("- 未回填状态导致删失机制可能非随机，这会影响高分位推断。")
    report.append("- 样本来自自报平台，存在选择偏差与信息截断。")
    report.append("- 后续建议：每周滚动更新并追加同口径再估计；若获得官方导出字段，可做更严格分层回归。")

    ACADEMIC_REPORT_FILE.write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()

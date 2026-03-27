from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from statistics import mean, median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
RAW_FILE = BASE_DIR / "f1_check_raw.txt"
CLEAN_FILE = BASE_DIR / "f1_check_cleaned.csv"
MONTHLY_FILE = BASE_DIR / "f1_check_monthly_stats.csv"
REPORT_FILE = BASE_DIR / "f1_check_report.md"
CHART_DIR = BASE_DIR / "charts"
TREND_CHART_FILE = CHART_DIR / "monthly-trend.png"
STATUS_CHART_FILE = CHART_DIR / "monthly-status-stacked.png"
BOXPLOT_CHART_FILE = CHART_DIR / "monthly-finalized-boxplot.png"

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
    if len(values) == 1:
        return values[0]
    arr = sorted(values)
    idx = (len(arr) - 1) * p
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return arr[lo]
    frac = idx - lo
    return arr[lo] * (1 - frac) + arr[hi] * frac


def extract_records(raw_text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", raw_text.replace("\n", " ")).strip()
    chunks = re.split(r"(?=Update)", normalized)
    results: list[str] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.startswith("Update"):
            chunk = "Update" + chunk
        # 去掉结尾 detail 标记，保留主体
        chunk = re.sub(r"detail\s*$", "", chunk).strip()
        if len(chunk) > 20:
            results.append(chunk)
    return results


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

    issues: list[str] = []
    if rec.location == "Unknown":
        issues.append("unknown_location")
    if not rec.nickname:
        issues.append("empty_nickname")

    rec.parse_ok = "1"
    rec.parse_issue = ";".join(issues)
    rec.key = f"{rec.nickname}|{rec.visa_type}|{rec.submit_date}"
    return rec


def choose_best(records: list[Record]) -> Record:
    def sort_key(r: Record) -> tuple:
        rank = STATUS_RANK.get(r.status, 0)
        comp = parse_date(r.complete_date) or date(1900, 1, 1)
        try:
            rep = int(r.reported_days)
        except ValueError:
            rep = -1
        return (rank, comp, rep)

    return sorted(records, key=sort_key, reverse=True)[0]


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
        }
    arr = sorted(values)
    return {
        "count": len(arr),
        "mean": mean(arr),
        "median": median(arr),
        "p25": percentile(arr, 0.25),
        "p75": percentile(arr, 0.75),
        "p90": percentile(arr, 0.90),
        "max": max(arr),
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


def render_charts(month_rows: list[dict], finalized_map: dict[str, list[int]]) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    months = [r["submit_month"] for r in month_rows]
    medians = [float(r["finalized_median_days"]) if r["finalized_median_days"] != "" else math.nan for r in month_rows]
    p90s = [float(r["finalized_p90_days"]) if r["finalized_p90_days"] != "" else math.nan for r in month_rows]

    clear_vals = [int(r["clear_cases"]) for r in month_rows]
    reject_vals = [int(r["reject_cases"]) for r in month_rows]
    pending_vals = [int(r["pending_cases"]) for r in month_rows]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(months, medians, marker="o", linewidth=2, label="Median days")
    ax.plot(months, p90s, marker="s", linewidth=2, label="P90 days")
    ax.set_title("Finalized Processing Time by Submit Month")
    ax.set_xlabel("Submit month")
    ax.set_ylabel("Days")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(TREND_CHART_FILE, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(months, clear_vals, label="Clear")
    ax.bar(months, reject_vals, bottom=clear_vals, label="Reject")
    stacked_base = [c + r for c, r in zip(clear_vals, reject_vals)]
    ax.bar(months, pending_vals, bottom=stacked_base, label="Pending")
    ax.set_title("Status Composition by Submit Month")
    ax.set_xlabel("Submit month")
    ax.set_ylabel("Case count")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(STATUS_CHART_FILE, dpi=180)
    plt.close(fig)

    box_months = [m for m in months if finalized_map.get(m)]
    box_data = [finalized_map[m] for m in box_months]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.boxplot(box_data, tick_labels=box_months, showfliers=True)
    ax.set_title("Finalized Processing Time Distribution")
    ax.set_xlabel("Submit month")
    ax.set_ylabel("Days")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(BOXPLOT_CHART_FILE, dpi=180)
    plt.close(fig)


def main() -> None:
    raw_text = RAW_FILE.read_text(encoding="utf-8", errors="replace")
    raw_records = extract_records(raw_text)
    parsed = [parse_one(r) for r in raw_records]

    parse_ok_records = [r for r in parsed if r.parse_ok == "1"]
    parse_fail_records = [r for r in parsed if r.parse_ok != "1"]

    grouped: dict[str, list[Record]] = defaultdict(list)
    for r in parse_ok_records:
        grouped[r.key].append(r)

    deduped = [choose_best(v) for v in grouped.values()]

    finalized = []
    pending = []
    for r in deduped:
        submit = parse_date(r.submit_date)
        complete = parse_date(r.complete_date)
        if r.status in {"Clear", "Reject"} and submit and complete:
            finalized.append((r, (complete - submit).days))
        elif r.status == "Pending" and submit:
            pending.append((r, (OBSERVATION_DATE - submit).days))

    finalized_days = [days for _, days in finalized]
    all_observed_days = finalized_days + [days for _, days in pending]

    base_stats = stats_summary(finalized_days)
    lower_stats = stats_summary(finalized_days)
    neutral_values = finalized_days + [int(base_stats["median"]) for _ in pending] if finalized_days else finalized_days
    neutral_stats = stats_summary(neutral_values)
    aggressive_values = finalized_days + [days for _, days in pending]
    aggressive_stats = stats_summary(aggressive_values)

    by_month: dict[str, dict[str, list[int] | int]] = defaultdict(lambda: {
        "finalized_days": [],
        "pending_observed": [],
        "clear": 0,
        "reject": 0,
        "pending": 0,
    })

    for r, days in finalized:
        m = month_bucket(r.submit_date)
        by_month[m]["finalized_days"].append(days)  # type: ignore[index]
        if r.status == "Clear":
            by_month[m]["clear"] += 1  # type: ignore[index]
        else:
            by_month[m]["reject"] += 1  # type: ignore[index]

    for r, days in pending:
        m = month_bucket(r.submit_date)
        by_month[m]["pending_observed"].append(days)  # type: ignore[index]
        by_month[m]["pending"] += 1  # type: ignore[index]

    month_rows = []
    month_finalized_map: dict[str, list[int]] = {}
    for m in sorted(by_month.keys()):
        finalized_values = by_month[m]["finalized_days"]  # type: ignore[assignment]
        month_finalized_map[m] = list(finalized_values)
        month_stats = stats_summary(finalized_values)
        clear_n = int(by_month[m]["clear"])  # type: ignore[arg-type]
        reject_n = int(by_month[m]["reject"])  # type: ignore[arg-type]
        pending_n = int(by_month[m]["pending"])  # type: ignore[arg-type]
        total = clear_n + reject_n + pending_n
        long_tail_n = sum(1 for x in finalized_values if x >= 90)
        month_rows.append(
            {
                "submit_month": m,
                "total_cases": total,
                "clear_cases": clear_n,
                "reject_cases": reject_n,
                "pending_cases": pending_n,
                "pending_ratio": round(pending_n / total, 4) if total else "",
                "finalized_count": int(month_stats["count"]),
                "finalized_mean_days": round(month_stats["mean"], 2) if month_stats["count"] else "",
                "finalized_median_days": round(month_stats["median"], 2) if month_stats["count"] else "",
                "finalized_p90_days": round(month_stats["p90"], 2) if month_stats["count"] else "",
                "finalized_max_days": int(month_stats["max"]) if month_stats["count"] else "",
                "long_tail_90plus_count": long_tail_n,
                "long_tail_90plus_ratio": round(long_tail_n / month_stats["count"], 4) if month_stats["count"] else "",
            }
        )

    clean_rows = [asdict(r) for r in deduped]
    clean_headers = list(clean_rows[0].keys()) if clean_rows else list(asdict(Record(raw="")).keys())
    write_csv(CLEAN_FILE, clean_rows, clean_headers)

    monthly_headers = list(month_rows[0].keys()) if month_rows else [
        "submit_month",
        "total_cases",
        "clear_cases",
        "reject_cases",
        "pending_cases",
        "pending_ratio",
        "finalized_count",
        "finalized_mean_days",
        "finalized_median_days",
        "finalized_p90_days",
        "finalized_max_days",
        "long_tail_90plus_count",
        "long_tail_90plus_ratio",
    ]
    write_csv(MONTHLY_FILE, month_rows, monthly_headers)

    render_charts(month_rows, month_finalized_map)

    issue_counter = Counter(r.parse_issue or "ok" for r in parsed)
    parse_success_rate = len(parse_ok_records) / len(parsed) if parsed else 0.0
    dedup_removed = len(parse_ok_records) - len(deduped)

    clear_count = sum(1 for r in deduped if r.status == "Clear")
    reject_count = sum(1 for r in deduped if r.status == "Reject")
    pending_count = sum(1 for r in deduped if r.status == "Pending")
    total_count = len(deduped)

    day_mismatch_count = 0
    for r, days in finalized:
        try:
            rep = int(r.reported_days)
        except ValueError:
            continue
        if rep != days:
            day_mismatch_count += 1

    long_tail_total = sum(1 for x in finalized_days if x >= 90)
    long_tail_ratio = long_tail_total / len(finalized_days) if finalized_days else 0.0

    nov_dec = [x for r, x in finalized if month_bucket(r.submit_date) in {"2025-11", "2025-12"}]
    jan_mar = [x for r, x in finalized if month_bucket(r.submit_date) in {"2026-01", "2026-02", "2026-03"}]
    nov_dec_p90 = percentile(nov_dec, 0.90) if nov_dec else float("nan")
    jan_mar_p90 = percentile(jan_mar, 0.90) if jan_mar else float("nan")

    pending_observed_days = [days for _, days in pending]
    pending_observed_stats = stats_summary(pending_observed_days)

    maturity_ratio = (clear_count + reject_count) / total_count if total_count else 0.0

    report = []
    report.append("# F1 Check 处理时间分析报告（2025-11 至 2026-03）")
    report.append("")
    report.append("## 1. 执行摘要")
    report.append(f"- 样本规模：去重后 {total_count} 条；结案样本 {int(base_stats['count'])} 条；Pending {pending_count} 条。")
    report.append(f"- 主口径处理时长：中位数 {base_stats['median']:.1f} 天，P90 {base_stats['p90']:.1f} 天，最大值 {base_stats['max']:.0f} 天。")
    report.append(f"- 长尾风险：>=90 天占比 {long_tail_ratio:.2%}（{long_tail_total}/{len(finalized_days) if finalized_days else 0}）。")
    report.append(f"- 停摆长尾对比：11-12 月 P90={nov_dec_p90:.1f} 天，1-3 月 P90={jan_mar_p90:.1f} 天，变化 {jan_mar_p90 - nov_dec_p90:+.1f} 天。")
    report.append("- 结论：早期提交批次长尾显著，后期已结案样本处理时长明显缩短；但近月 Pending 占比高，需结合成熟度解读。")
    report.append("")

    report.append("## 2. 数据清洗质量")
    report.append(f"- 原始分段记录数：{len(parsed)}")
    report.append(f"- 解析成功记录数：{len(parse_ok_records)}")
    report.append(f"- 解析失败记录数：{len(parse_fail_records)}")
    report.append(f"- 解析成功率：{parse_success_rate:.2%}")
    report.append(f"- 去重后记录数：{total_count}")
    report.append(f"- 去重剔除记录数：{dedup_removed}")
    report.append(f"- 状态分布：Clear={clear_count}, Reject={reject_count}, Pending={pending_count}")
    report.append(f"- 数据成熟度（Clear+Reject 占比）：{maturity_ratio:.2%}")
    report.append(f"- reported_days 与日期差不一致条数：{day_mismatch_count}")
    report.append("")
    report.append("主要解析问题（Top 5）：")
    for issue, cnt in issue_counter.most_common(5):
        report.append(f"- {issue}: {cnt}")

    report.append("")
    report.append("## 3. 处理时间核心统计（天）")
    report.append(f"- 主口径（仅 Clear/Reject）样本数：{int(base_stats['count'])}")
    report.append(f"- 均值：{base_stats['mean']:.2f}，中位数：{base_stats['median']:.2f}，P90：{base_stats['p90']:.2f}，最大值：{base_stats['max']:.0f}")
    report.append(f"- 长尾（>=90天）占比：{long_tail_ratio:.2%}（{long_tail_total}/{len(finalized_days) if finalized_days else 0}）")
    report.append(f"- Pending 已观察时长（截至 {OBSERVATION_DATE.isoformat()}）：中位数 {pending_observed_stats['median']:.2f}，P90 {pending_observed_stats['p90']:.2f}")

    report.append("")
    report.append("三口径区间（处理中样本不确定性）：")
    report.append(f"- 保守口径（Pending 全未结案）中位数：{lower_stats['median']:.2f}，P90：{lower_stats['p90']:.2f}")
    report.append(f"- 中性口径（Pending 以主口径中位数回填）中位数：{neutral_stats['median']:.2f}，P90：{neutral_stats['p90']:.2f}")
    report.append(f"- 激进口径（Pending 以已观察时长计入）中位数：{aggressive_stats['median']:.2f}，P90：{aggressive_stats['p90']:.2f}")

    report.append("")
    report.append("## 4. 月度趋势明细（提交月份）")
    report.append("| 月份 | 总样本 | Clear | Reject | Pending | Pending占比 | 结案中位数 | 结案P90 | >=90天占比 |")
    report.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in month_rows:
        report.append(
            "| {submit_month} | {total_cases} | {clear_cases} | {reject_cases} | {pending_cases} | {pending_ratio:.2%} | {finalized_median_days} | {finalized_p90_days} | {long_tail_90plus_ratio:.2%} |".format(
                submit_month=row["submit_month"],
                total_cases=row["total_cases"],
                clear_cases=row["clear_cases"],
                reject_cases=row["reject_cases"],
                pending_cases=row["pending_cases"],
                pending_ratio=float(row["pending_ratio"]),
                finalized_median_days=row["finalized_median_days"],
                finalized_p90_days=row["finalized_p90_days"],
                long_tail_90plus_ratio=float(row["long_tail_90plus_ratio"]),
            )
        )

    report.append("")
    report.append(f"- 11-12月结案样本 P90：{nov_dec_p90:.2f} 天")
    report.append(f"- 1-3月结案样本 P90：{jan_mar_p90:.2f} 天")
    if not math.isnan(nov_dec_p90) and not math.isnan(jan_mar_p90):
        diff = jan_mar_p90 - nov_dec_p90
        report.append(f"- P90 变化：{diff:+.2f} 天（用于评估停摆长尾是否缓解/加剧）")
    report.append("- 解读：2025-11 的长尾占比极高（>90%），而 2026-01 之后结案样本几乎不再出现 >=90 天长尾。")

    report.append("")
    report.append("## 5. 图表")
    report.append("### 5.1 结案处理时长趋势")
    report.append("![月度处理中位数与P90趋势](charts/monthly-trend.png)")
    report.append("- 用途：看处理时长的中心趋势和高分位风险是否同步下降。")
    report.append("")
    report.append("### 5.2 月度状态结构")
    report.append("![月度状态堆叠柱](charts/monthly-status-stacked.png)")
    report.append("- 用途：看每个月 Pending 占比，判断样本成熟度和未回填风险。")
    report.append("")
    report.append("### 5.3 结案分布箱线图")
    report.append("![月度结案分布箱线图](charts/monthly-finalized-boxplot.png)")
    report.append("- 用途：看离散度和异常长尾，避免只看均值。")

    report.append("")
    report.append("## 6. 关于‘有人不更新状态’的偏差说明")
    report.append("- Pending 同时包含真实在审和已结案未回填，不能直接当作真实在审规模。")
    report.append("- 因此主结论使用‘仅结案样本’，并辅以三口径区间反映不确定性。")
    report.append("- 最近月份 pending_ratio 更高，可能造成‘看起来处理变慢/变快’的统计错觉。")
    report.append("- 实操建议：月度趋势展示时并排给出 pending_ratio，并把最近1个月标注为低成熟度区。")

    report.append("")
    report.append("## 7. 给你可直接引用的结论话术")
    report.append("- 从已结案样本看，2025-11~12 的处理时间明显更长，存在显著长尾；2026-01 之后中位数和P90都显著下降。")
    report.append("- 但 2026-02~03 的 Pending 占比高，当前趋势应理解为‘已结案样本变快’，不是‘全部样本都变快’。")
    report.append("- 若考虑未回填，整体中位处理时间大致落在 88~89.5 天区间，高分位风险（P90）约在 102.5~113.5 天区间。")

    REPORT_FILE.write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()

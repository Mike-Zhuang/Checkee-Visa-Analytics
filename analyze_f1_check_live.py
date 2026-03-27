from __future__ import annotations

import argparse
import csv
import math
import random
import re
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from statistics import mean, median
from typing import Iterable
from urllib.parse import parse_qs, urljoin, urlparse

import matplotlib
import requests
from bs4 import BeautifulSoup

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
BASE_URL = "https://checkee.info/"

LIVE_CASES_FILE = BASE_DIR / "f1_check_live_cases.csv"
LIVE_MONTHLY_FILE = BASE_DIR / "f1_check_live_monthly_stats.csv"
LIVE_REPORT_FILE = BASE_DIR / "f1_check_live_report.md"

CHART_DIR = BASE_DIR / "charts"
LIVE_TREND_CHART = CHART_DIR / "f1_check_live_trend_maturity.png"
LIVE_STATUS_CHART = CHART_DIR / "f1_check_live_status_stacked.png"
LIVE_BOXPLOT_CHART = CHART_DIR / "f1_check_live_monthly_boxplot.png"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
RANDOM_SEED = 20260327


@dataclass
class LiveCase:
    source_month: str
    case_number: str
    nickname: str
    visa_type: str
    visa_entry: str
    consulate: str
    major: str
    status: str
    check_date: str
    complete_date: str
    waiting_days_reported: str
    detail_url: str
    update_url: str


@dataclass
class ParsedCase:
    source_month: str
    case_number: str
    nickname: str
    visa_type: str
    visa_entry: str
    consulate: str
    major: str
    status: str
    check_date: str
    complete_date: str
    waiting_days_reported: str
    waiting_days_calc: str
    observed_days: str
    event: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch live F1 checkee data and generate report.")
    parser.add_argument(
        "--all-months",
        action="store_true",
        help="Fetch all months listed on checkee monthly selector.",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=6,
        help="Fetch recent N months (default: 6). Ignored when --all-months is set.",
    )
    parser.add_argument(
        "--from-month",
        type=str,
        default="",
        help="Fetch from this month forward, format YYYY-MM (e.g., 2025-11).",
    )
    return parser.parse_args()


def parse_date(s: str) -> date | None:
    if not s or s == "0000-00-00":
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def month_key(s: str) -> tuple[int, int]:
    y, m = s.split("-")
    return int(y), int(m)


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


def bootstrap_ci(values: list[int], stat_func, n_boot: int = 3000, alpha: float = 0.05) -> tuple[float, float, float]:
    if not values:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(RANDOM_SEED)
    n = len(values)
    samples = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(float(stat_func(sample)))
    point = float(stat_func(values))
    lo = percentile(samples, alpha / 2)
    hi = percentile(samples, 1 - alpha / 2)
    return point, lo, hi


def linear_trend(values: list[float]) -> tuple[float, float]:
    pairs = [(i, v) for i, v in enumerate(values) if not math.isnan(v)]
    if len(pairs) < 2:
        return float("nan"), float("nan")
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    mx = mean(xs)
    my = mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return float("nan"), float("nan")
    slope = sxy / sxx
    y_hat = [my + slope * (x - mx) for x in xs]
    ss_res = sum((y - yh) ** 2 for y, yh in zip(ys, y_hat))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return slope, r2


def write_csv(path: Path, rows: list[dict], headers: Iterable[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(headers))
        writer.writeheader()
        writer.writerows(rows)


def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            "Connection": "keep-alive",
            "Referer": BASE_URL,
        }
    )
    return s


def fetch_html(session: requests.Session, url: str, timeout: int = 25) -> str:
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    text = resp.text
    if "403 Forbidden" in text and "Access is forbidden" in text:
        raise RuntimeError("checkee 返回 403，当前网络环境被站点拦截。")
    return text


def extract_available_months(index_html: str) -> list[str]:
    soup = BeautifulSoup(index_html, "html.parser")
    select = soup.find("select", attrs={"name": "dispdate"})
    if not select:
        return []
    months = []
    for opt in select.find_all("option"):
        val = (opt.get("value") or "").strip()
        if re.fullmatch(r"\d{4}-\d{2}", val):
            months.append(val)
    # 去重并降序
    return sorted(set(months), key=month_key, reverse=True)


def pick_months(all_months: list[str], args: argparse.Namespace) -> list[str]:
    if not all_months:
        return []
    if args.all_months:
        return all_months
    if args.from_month:
        target = args.from_month.strip()
        return [m for m in all_months if month_key(m) >= month_key(target)]
    n = max(1, args.months)
    return all_months[:n]


def parse_case_number(update_href: str) -> str:
    if not update_href:
        return ""
    parsed = urlparse(update_href)
    qs = parse_qs(parsed.query)
    return qs.get("casenum", [""])[0]


def find_case_table(soup: BeautifulSoup):
    tables = soup.find_all("table")
    for table in tables:
        header_cells = [c.get_text(strip=True) for c in table.find_all("tr")[0].find_all("td")] if table.find_all("tr") else []
        joined = "|".join(header_cells)
        if all(k in joined for k in ["Update", "ID", "Visa Type", "US Consulate", "Status", "Check Date", "Complete Date"]):
            return table
    return None


def parse_month_cases(month: str, html: str) -> list[LiveCase]:
    soup = BeautifulSoup(html, "html.parser")
    table = find_case_table(soup)
    if table is None:
        return []

    cases: list[LiveCase] = []
    rows = table.find_all("tr")
    for tr in rows[1:]:
        tds = tr.find_all("td")
        if len(tds) < 11:
            continue

        update_link = tds[0].find("a")
        detail_link = tds[10].find("a")
        update_href = update_link.get("href", "") if update_link else ""
        detail_href = detail_link.get("href", "") if detail_link else ""

        visa_type = tds[2].get_text(strip=True)
        if visa_type.upper() != "F1":
            continue

        case = LiveCase(
            source_month=month,
            case_number=parse_case_number(update_href),
            nickname=tds[1].get_text(strip=True),
            visa_type=visa_type,
            visa_entry=tds[3].get_text(strip=True),
            consulate=tds[4].get_text(strip=True),
            major=tds[5].get_text(strip=True),
            status=tds[6].get_text(strip=True),
            check_date=tds[7].get_text(strip=True),
            complete_date=tds[8].get_text(strip=True),
            waiting_days_reported=tds[9].get_text(strip=True),
            detail_url=urljoin(BASE_URL, detail_href),
            update_url=urljoin(BASE_URL, update_href),
        )
        cases.append(case)
    return cases


def to_parsed_case(c: LiveCase, observation_date: date) -> ParsedCase | None:
    check_dt = parse_date(c.check_date)
    if check_dt is None:
        return None

    complete_dt = parse_date(c.complete_date)
    status = c.status.capitalize()
    if status == "Clear" or status == "Reject":
        if complete_dt is None:
            # 站点有时状态更新但日期未填，降级为删失
            event = 0
            duration = (observation_date - check_dt).days
            waiting_calc = ""
            observed = str(duration)
        else:
            event = 1
            duration = (complete_dt - check_dt).days
            waiting_calc = str(duration)
            observed = ""
    else:
        event = 0
        duration = (observation_date - check_dt).days
        waiting_calc = ""
        observed = str(duration)

    return ParsedCase(
        source_month=c.source_month,
        case_number=c.case_number,
        nickname=c.nickname,
        visa_type=c.visa_type,
        visa_entry=c.visa_entry,
        consulate=c.consulate,
        major=c.major,
        status=status,
        check_date=c.check_date,
        complete_date=c.complete_date,
        waiting_days_reported=c.waiting_days_reported,
        waiting_days_calc=waiting_calc,
        observed_days=observed,
        event=event,
    )


def render_charts(month_rows: list[dict], month_finalized: dict[str, list[int]]) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    months = [r["submit_month"] for r in month_rows]
    medians = [float(r["median_days"]) if r["median_days"] != "" else math.nan for r in month_rows]
    p90s = [float(r["p90_days"]) if r["p90_days"] != "" else math.nan for r in month_rows]
    pending_ratio = [float(r["pending_ratio"]) if r["pending_ratio"] != "" else math.nan for r in month_rows]

    clear_n = [int(r["clear_cases"]) for r in month_rows]
    reject_n = [int(r["reject_cases"]) for r in month_rows]
    pending_n = [int(r["pending_cases"]) for r in month_rows]

    fig, ax1 = plt.subplots(figsize=(10, 5.2))
    ax2 = ax1.twinx()
    ax1.plot(months, medians, marker="o", linewidth=2.1, label="Median (finalized)", color="#0d3b66")
    ax1.plot(months, p90s, marker="s", linewidth=2.1, label="P90 (finalized)", color="#ef476f")
    ax2.bar(months, pending_ratio, alpha=0.28, color="#ffd166", label="Pending ratio")
    ax1.set_title("Live F1 Trend with Sample Maturity")
    ax1.set_xlabel("Submit month")
    ax1.set_ylabel("Days")
    ax2.set_ylabel("Pending ratio")
    ax1.grid(axis="y", alpha=0.3)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right")
    fig.tight_layout()
    fig.savefig(LIVE_TREND_CHART, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.bar(months, clear_n, label="Clear")
    ax.bar(months, reject_n, bottom=clear_n, label="Reject")
    stack = [c + r for c, r in zip(clear_n, reject_n)]
    ax.bar(months, pending_n, bottom=stack, label="Pending")
    ax.set_title("Live F1 Monthly Status Composition")
    ax.set_xlabel("Submit month")
    ax.set_ylabel("Case count")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(LIVE_STATUS_CHART, dpi=180)
    plt.close(fig)

    box_months = [m for m in months if month_finalized.get(m)]
    box_data = [month_finalized[m] for m in box_months]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    if box_data:
        ax.boxplot(box_data, tick_labels=box_months, showfliers=True)
    ax.set_title("Live F1 Finalized Duration Distribution")
    ax.set_xlabel("Submit month")
    ax.set_ylabel("Days")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(LIVE_BOXPLOT_CHART, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    observation_date = date.today()

    session = get_session()

    try:
        index_html = fetch_html(session, BASE_URL)
    except Exception as e:
        raise SystemExit(f"无法获取 checkee 首页: {e}")

    all_months = extract_available_months(index_html)
    months = pick_months(all_months, args)
    if not months:
        raise SystemExit("未解析到可用月份，无法继续抓取。")

    live_cases: list[LiveCase] = []
    for i, m in enumerate(months):
        url = urljoin(BASE_URL, f"main.php?dispdate={m}")
        try:
            html = fetch_html(session, url)
            month_cases = parse_month_cases(m, html)
            live_cases.extend(month_cases)
        except Exception as e:
            print(f"[WARN] 月份 {m} 抓取失败: {e}")
        if i < len(months) - 1:
            time.sleep(0.2)

    if not live_cases:
        raise SystemExit("未抓取到 F1 明细数据，请检查网络或站点策略。")

    parsed_cases: list[ParsedCase] = []
    for c in live_cases:
        parsed = to_parsed_case(c, observation_date)
        if parsed is not None:
            parsed_cases.append(parsed)

    # 以 casenum 去重，保留 check_date 更新更晚的记录
    dedup: dict[str, ParsedCase] = {}
    for r in parsed_cases:
        key = r.case_number or f"{r.nickname}|{r.check_date}|{r.consulate}|{r.major}"
        prev = dedup.get(key)
        if prev is None:
            dedup[key] = r
            continue
        prev_dt = parse_date(prev.check_date) or date(1900, 1, 1)
        cur_dt = parse_date(r.check_date) or date(1900, 1, 1)
        if cur_dt >= prev_dt:
            dedup[key] = r

    rows = list(dedup.values())

    finalized = []
    pending = []
    for r in rows:
        if r.event == 1 and r.waiting_days_calc:
            finalized.append(int(r.waiting_days_calc))
        elif r.event == 0 and r.observed_days:
            pending.append(int(r.observed_days))

    if not finalized:
        raise SystemExit("抓取成功，但没有可用于分析的结案样本。")

    summary = stats_summary(finalized)
    pending_summary = stats_summary(pending)

    med_point, med_lo, med_hi = bootstrap_ci(finalized, median)
    p90_func = lambda x: percentile([float(v) for v in x], 0.9)
    p90_point, p90_lo, p90_hi = bootstrap_ci(finalized, p90_func)

    monthly_map: dict[str, list[ParsedCase]] = {}
    for r in rows:
        m = r.check_date[:7]
        monthly_map.setdefault(m, []).append(r)

    month_rows = []
    month_finalized: dict[str, list[int]] = {}
    for m in sorted(monthly_map.keys()):
        group = monthly_map[m]
        fvals = [int(x.waiting_days_calc) for x in group if x.event == 1 and x.waiting_days_calc]
        pvals = [int(x.observed_days) for x in group if x.event == 0 and x.observed_days]
        month_finalized[m] = fvals
        clear_n = sum(1 for x in group if x.status == "Clear")
        reject_n = sum(1 for x in group if x.status == "Reject")
        pending_n = sum(1 for x in group if x.status not in {"Clear", "Reject"})
        total_n = len(group)

        s = stats_summary(fvals)
        _, mlo, mhi = bootstrap_ci(fvals, median, n_boot=1500) if fvals else (float("nan"), float("nan"), float("nan"))
        _, plo, phi = bootstrap_ci(fvals, p90_func, n_boot=1500) if fvals else (float("nan"), float("nan"), float("nan"))
        tail_n = sum(1 for v in fvals if v >= 90)

        month_rows.append(
            {
                "submit_month": m,
                "total_cases": total_n,
                "clear_cases": clear_n,
                "reject_cases": reject_n,
                "pending_cases": pending_n,
                "maturity_ratio": round((clear_n + reject_n) / total_n, 4) if total_n else "",
                "pending_ratio": round(pending_n / total_n, 4) if total_n else "",
                "finalized_count": len(fvals),
                "median_days": round(s["median"], 2) if s["count"] else "",
                "median_ci_low": round(mlo, 2) if s["count"] else "",
                "median_ci_high": round(mhi, 2) if s["count"] else "",
                "p90_days": round(s["p90"], 2) if s["count"] else "",
                "p90_ci_low": round(plo, 2) if s["count"] else "",
                "p90_ci_high": round(phi, 2) if s["count"] else "",
                "long_tail_90plus_ratio": round(tail_n / len(fvals), 4) if fvals else "",
                "pending_observed_median": round(median(pvals), 2) if pvals else "",
            }
        )

    medians = [float(r["median_days"]) if r["median_days"] != "" else math.nan for r in month_rows]
    p90s = [float(r["p90_days"]) if r["p90_days"] != "" else math.nan for r in month_rows]
    slope_median, r2_median = linear_trend(medians)
    slope_p90, r2_p90 = linear_trend(p90s)

    conservative = finalized
    neutral = finalized + [int(summary["median"])] * len(pending)
    aggressive = finalized + pending

    def one_line_stats(name: str, values: list[int]) -> dict:
        s = stats_summary(values)
        return {
            "scenario": name,
            "median": s["median"],
            "p90": s["p90"],
            "tail_ratio": sum(1 for x in values if x >= 90) / len(values) if values else float("nan"),
        }

    sensitivity = [
        one_line_stats("Conservative", conservative),
        one_line_stats("Neutral", neutral),
        one_line_stats("Aggressive", aggressive),
    ]

    # 导出
    case_rows = [asdict(r) for r in rows]
    case_headers = list(case_rows[0].keys()) if case_rows else list(asdict(ParsedCase("", "", "", "", "", "", "", "", "", "", "", "", "", 0)).keys())
    write_csv(LIVE_CASES_FILE, case_rows, case_headers)

    monthly_headers = list(month_rows[0].keys()) if month_rows else []
    if monthly_headers:
        write_csv(LIVE_MONTHLY_FILE, month_rows, monthly_headers)

    render_charts(month_rows, month_finalized)

    report = []
    report.append("# F1 Check 实时自动分析报告（Live）")
    report.append("")
    report.append("## 1. 数据来源与抓取说明")
    report.append("- 来源站点：checkee.info 公共页面。")
    report.append(f"- 抓取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"- 观察日：{observation_date.isoformat()}")
    report.append(f"- 抓取月份范围：{months[-1]} 至 {months[0]}（共 {len(months)} 个月）")
    report.append("- 抓取对象：仅保留 Visa Type = F1 的明细行。")
    report.append("")

    report.append("## 2. 样本概览")
    report.append(f"- F1 样本总量（去重后）：{len(rows)}")
    report.append(f"- 结案样本（Clear/Reject）：{int(summary['count'])}")
    report.append(f"- 右删失样本（Pending）：{len(pending)}")
    report.append(f"- 样本成熟度（结案占比）：{(len(finalized) / len(rows)):.2%}")
    report.append("")

    report.append("## 3. 主结果（结案样本口径）")
    report.append(f"- 中位数：{med_point:.2f} 天（Bootstrap 95% CI: {med_lo:.2f}-{med_hi:.2f}）")
    report.append(f"- P90：{p90_point:.2f} 天（Bootstrap 95% CI: {p90_lo:.2f}-{p90_hi:.2f}）")
    report.append(f"- 均值：{summary['mean']:.2f} 天，IQR：{summary['iqr']:.2f}，标准差：{summary['std']:.2f}")
    report.append(f"- 长尾（>=90天）占比：{(sum(1 for x in finalized if x >= 90) / len(finalized)):.2%}")
    report.append("")

    report.append("## 4. 右删失诊断")
    report.append(f"- Pending 已观察时长中位数：{pending_summary['median']:.2f} 天")
    report.append(f"- Pending 已观察时长 P90：{pending_summary['p90']:.2f} 天")
    report.append("- 解释：Pending 同时含“真实未结案”和“已结案未回填”，因此报告保留区间估计。")
    report.append("")

    report.append("## 5. 趋势分析")
    report.append(f"- 月度中位数斜率：{slope_median:.2f} 天/月（R²={r2_median:.3f}）")
    report.append(f"- 月度P90斜率：{slope_p90:.2f} 天/月（R²={r2_p90:.3f}）")
    report.append("- 说明：负斜率表示最近月份处理时长在缩短，但需结合 pending_ratio 一起解读。")
    report.append("")

    report.append("## 6. 敏感性分析（Pending 假设）")
    report.append("| Scenario | Median (days) | P90 (days) | >=90d ratio |")
    report.append("|---|---:|---:|---:|")
    for s in sensitivity:
        report.append(f"| {s['scenario']} | {s['median']:.2f} | {s['p90']:.2f} | {s['tail_ratio']:.2%} |")
    report.append("")

    report.append("## 7. 月度明细")
    report.append("| Month | Total | Clear | Reject | Pending | Pending% | Median | P90 | >=90d% |")
    report.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in month_rows:
        report.append(
            "| {submit_month} | {total_cases} | {clear_cases} | {reject_cases} | {pending_cases} | {pending_ratio:.2%} | {median_days} | {p90_days} | {long_tail_90plus_ratio:.2%} |".format(
                submit_month=r["submit_month"],
                total_cases=r["total_cases"],
                clear_cases=r["clear_cases"],
                reject_cases=r["reject_cases"],
                pending_cases=r["pending_cases"],
                pending_ratio=float(r["pending_ratio"]),
                median_days=r["median_days"],
                p90_days=r["p90_days"],
                long_tail_90plus_ratio=float(r["long_tail_90plus_ratio"]) if r["long_tail_90plus_ratio"] != "" else 0.0,
            )
        )
    report.append("")

    report.append("## 8. 图表")
    report.append("![Live趋势与成熟度](charts/f1_check_live_trend_maturity.png)")
    report.append("![Live状态结构](charts/f1_check_live_status_stacked.png)")
    report.append("![Live结案分布](charts/f1_check_live_monthly_boxplot.png)")
    report.append("")

    report.append("## 9. 自动化运行")
    report.append("- 每次运行本脚本会实时抓取 checkee 最新公开页面并重建报告。")
    report.append("- 若站点策略变化导致403，可尝试更换网络或稍后重试。")

    LIVE_REPORT_FILE.write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()

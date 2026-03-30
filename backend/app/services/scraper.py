from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import (
    CHECKEE_BASE_URL,
    DETAIL_FETCH_REQUIRE_NOTE,
    DETAIL_FETCH_SAMPLE_RATIO,
    FETCH_DELAY_SECONDS,
    MAX_FETCH_MONTHS,
    REQUEST_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    RETRY_SLEEP_SECONDS,
    USER_AGENT,
)


DEFAULT_FETCH_SOURCE = "monthly_track"
LATEST_FETCH_SOURCE = "latest_snapshot"
SUPPORTED_FETCH_SOURCES = frozenset({DEFAULT_FETCH_SOURCE, LATEST_FETCH_SOURCE})


@dataclass
class CaseRow:
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
    detail_url: str
    update_url: str
    detail_employer: str
    detail_note: str
    detail_city: str
    detail_state: str


@dataclass
class FetchResult:
    rows: list[CaseRow]
    fetched_months: list[str]
    truncated_by_limit: bool
    selected_sources: list[str]
    source_discovery: dict[str, str]
    coverage: dict[str, Any]


def _parse_date(value: str) -> date | None:
    from datetime import datetime

    if not value or value == "0000-00-00":
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _month_key(value: str) -> tuple[int, int]:
    y, m = value.split("-")
    return int(y), int(m)


def _is_month_token(value: str) -> bool:
    return re.fullmatch(r"\d{4}-\d{2}", value) is not None


def _slug_text(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "unnamed"


def _dedupe_key(key_base: str, existing: set[str]) -> str:
    if key_base not in existing:
        return key_base
    suffix = 2
    while f"{key_base}_{suffix}" in existing:
        suffix += 1
    return f"{key_base}_{suffix}"


def _extract_entry_points(index_html: str) -> dict[str, str]:
    soup = BeautifulSoup(index_html, "html.parser")
    entry_points: dict[str, str] = {}

    for anchor in soup.find_all("a"):
        href = (anchor.get("href") or "").strip()
        if not href:
            continue
        label = anchor.get_text(" ", strip=True)
        if not label:
            parsed = urlparse(href)
            label = parsed.path.rsplit("/", 1)[-1] or "link"
        key_base = f"link_{_slug_text(label)}"
        key = _dedupe_key(key_base, set(entry_points))
        entry_points[key] = urljoin(CHECKEE_BASE_URL, href)

    for form in soup.find_all("form"):
        action = (form.get("action") or "").strip()
        if not action:
            continue
        label = form.get_text(" ", strip=True)
        if not label:
            parsed = urlparse(action)
            label = parsed.path.rsplit("/", 1)[-1] or "form"
        key_base = f"form_{_slug_text(label)}"
        key = _dedupe_key(key_base, set(entry_points))
        entry_points[key] = urljoin(CHECKEE_BASE_URL, action)

    return entry_points


def list_supported_sources() -> list[str]:
    return sorted(SUPPORTED_FETCH_SOURCES)


def _normalize_sources(sources: list[str] | None) -> list[str]:
    if sources is None:
        return [DEFAULT_FETCH_SOURCE]

    normalized: list[str] = []
    for raw_source in sources:
        token = str(raw_source).strip().lower().replace("-", "_")
        if not token:
            continue
        if token not in normalized:
            normalized.append(token)

    if not normalized:
        raise ValueError("sources must include at least one non-empty value")

    unsupported = [token for token in normalized if token not in SUPPORTED_FETCH_SOURCES]
    if unsupported:
        supported_str = ", ".join(list_supported_sources())
        unsupported_str = ", ".join(unsupported)
        raise ValueError(f"unsupported sources: {unsupported_str}; supported sources: {supported_str}")

    return normalized


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            "Connection": "keep-alive",
            "Referer": CHECKEE_BASE_URL,
        }
    )
    return s


def _fetch_html(session: requests.Session, url: str) -> str:
    last_error: Exception | None = None
    for attempt in range(REQUEST_RETRIES + 1):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
            html = resp.text
            if "403 Forbidden" in html and "Access is forbidden" in html:
                raise RuntimeError("checkee returned 403")
            return html
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < REQUEST_RETRIES:
                time.sleep(RETRY_SLEEP_SECONDS)
                continue
            raise RuntimeError(f"fetch failed for {url}: {exc}") from exc
    raise RuntimeError(str(last_error))


def _extract_months(index_html: str) -> list[str]:
    soup = BeautifulSoup(index_html, "html.parser")
    select = soup.find("select", attrs={"name": "dispdate"})
    if not select:
        return []
    months = []
    for opt in select.find_all("option"):
        val = (opt.get("value") or "").strip()
        if re.fullmatch(r"\d{4}-\d{2}", val):
            months.append(val)
    return sorted(set(months), key=_month_key, reverse=True)


def _pick_months(months: list[str], all_months: bool, recent_n: int, from_month: str | None) -> tuple[list[str], bool]:
    if from_month and not _is_month_token(from_month):
        raise ValueError("from_month must be in YYYY-MM format")

    if all_months:
        picked = months
    elif from_month:
        picked = [m for m in months if _month_key(m) >= _month_key(from_month)]
    else:
        picked = months[: max(1, recent_n)]

    if len(picked) > MAX_FETCH_MONTHS:
        return picked[:MAX_FETCH_MONTHS], True
    return picked, False


def _parse_case_number(update_href: str) -> str:
    if not update_href:
        return ""
    parsed = urlparse(update_href)
    return parse_qs(parsed.query).get("casenum", [""])[0]


def _find_table(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header_text = "|".join(td.get_text(strip=True) for td in rows[0].find_all("td"))
        if all(key in header_text for key in ["Update", "ID", "Visa Type", "US Consulate", "Status", "Check Date"]):
            return table
    return None


def _parse_month_rows(month: str, html: str, observation_date: date) -> list[CaseRow]:
    soup = BeautifulSoup(html, "html.parser")
    table = _find_table(soup)
    if table is None:
        return []

    parsed: list[CaseRow] = []
    for tr in table.find_all("tr")[1:]:
        tds = tr.find_all("td")
        if len(tds) < 11:
            continue

        update_link = tds[0].find("a")
        detail_link = tds[10].find("a")
        update_href = update_link.get("href", "") if update_link else ""
        detail_href = detail_link.get("href", "") if detail_link else ""

        check_date = tds[7].get_text(strip=True)
        complete_date = tds[8].get_text(strip=True)

        status_raw = tds[6].get_text(strip=True).strip()
        status = status_raw.capitalize()
        check_dt = _parse_date(check_date)
        complete_dt = _parse_date(complete_date)

        waiting_calc = ""
        observed_days = ""
        event = 0
        if check_dt is not None:
            if status in {"Clear", "Reject"} and complete_dt is not None:
                event = 1
                waiting_calc = str((complete_dt - check_dt).days)
            else:
                observed_days = str((observation_date - check_dt).days)

        parsed.append(
            CaseRow(
                source_month=month,
                case_number=_parse_case_number(update_href),
                nickname=tds[1].get_text(strip=True),
                visa_type=tds[2].get_text(strip=True).upper(),
                visa_entry=tds[3].get_text(strip=True),
                consulate=tds[4].get_text(strip=True),
                major=tds[5].get_text(strip=True),
                status=status,
                check_date=check_date,
                complete_date=complete_date,
                waiting_days_reported=tds[9].get_text(strip=True),
                waiting_days_calc=waiting_calc,
                observed_days=observed_days,
                event=event,
                detail_url=urljoin(CHECKEE_BASE_URL, detail_href),
                update_url=urljoin(CHECKEE_BASE_URL, update_href),
                detail_employer="",
                detail_note="",
                detail_city="",
                detail_state="",
            )
        )
    return parsed


def _compact_text(value: str, limit: int = 320) -> str:
    compact = re.sub(r"\s+", " ", value or "").strip()
    if len(compact) <= limit:
        return compact
    if limit <= 3:
        return compact[:limit]
    return compact[: limit - 3].rstrip() + "..."


def _normalize_detail_label(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", label.lower()).strip()


def _extract_inline_label_value(text: str) -> tuple[str, str] | None:
    compact = _compact_text(text, limit=1200)
    if not compact:
        return None
    if ":" not in compact and "：" not in compact:
        return None

    parts = re.split(r"\s*[：:]\s*", compact, maxsplit=1)
    if len(parts) != 2:
        return None

    label = parts[0].strip()
    value = _compact_text(parts[1], limit=1200)
    if not label or not value:
        return None
    if len(label) > 80:
        return None
    return label, value


def _extract_detail_pairs(soup: BeautifulSoup) -> dict[str, str]:
    pairs: dict[str, str] = {}

    def put(label: str, value: str) -> None:
        key = _normalize_detail_label(label.rstrip(":"))
        val = _compact_text(value)
        if not key or not val:
            return
        if len(key) > 80:
            return
        if key not in pairs:
            pairs[key] = val

    for tr in soup.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        for cell in cells:
            inline = _extract_inline_label_value(cell.get_text(" ", strip=True))
            if inline is not None:
                put(inline[0], inline[1])

        if len(cells) < 2:
            continue
        if _extract_inline_label_value(cells[0].get_text(" ", strip=True)) is not None:
            continue
        label = cells[0].get_text(" ", strip=True)
        value = cells[1].get_text(" ", strip=True)
        put(label, value)

    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd is None:
            continue
        put(dt.get_text(" ", strip=True), dd.get_text(" ", strip=True))

    for li in soup.find_all("li"):
        text = li.get_text(" ", strip=True)
        if ":" not in text:
            continue
        label, value = text.split(":", 1)
        put(label, value)

    return pairs


def _pick_detail_value(pairs: dict[str, str], aliases: tuple[str, ...]) -> str:
    placeholder_values = {
        "n a",
        "na",
        "none",
        "null",
        "nil",
        "not applicable",
        "not available",
    }

    for alias in aliases:
        for key, value in pairs.items():
            normalized_value = _normalize_detail_label(value)
            if alias in key and value and normalized_value not in placeholder_values:
                return value
    return ""


def _extract_detail_fields(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    detail_pairs = _extract_detail_pairs(soup)

    employer = _pick_detail_value(
        detail_pairs,
        (
            "employer",
            "company",
            "organization",
            "institution",
            "work",
        ),
    )
    note = _pick_detail_value(
        detail_pairs,
        (
            "note",
            "comment",
            "remark",
            "description",
            "summary",
            "background",
        ),
    )
    city = _pick_detail_value(detail_pairs, ("city", "location city", "current city", "residence city"))
    state = _pick_detail_value(detail_pairs, ("state", "province", "region"))

    if not note:
        for node in soup.select("textarea, .note, .comment, #note, #comment"):
            candidate = _compact_text(node.get_text(" ", strip=True))
            if candidate:
                note = candidate
                break

    return {
        "detail_employer": employer,
        "detail_note": note,
        "detail_city": city,
        "detail_state": state,
    }


def _should_sample_detail(row: CaseRow, sample_ratio: float) -> bool:
    if sample_ratio >= 1:
        return True
    if sample_ratio <= 0:
        return False

    token = row.case_number or row.detail_url or f"{row.nickname}|{row.check_date}|{row.consulate}"
    digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 10000
    threshold = int(sample_ratio * 10000)
    return bucket < threshold


def _enrich_detail_fields(rows: list[CaseRow], session: requests.Session, sample_ratio: float) -> dict[str, Any]:
    ratio = min(1.0, max(0.0, sample_ratio))
    require_note = DETAIL_FETCH_REQUIRE_NOTE
    metrics: dict[str, Any] = {
        "detail_sample_ratio": round(ratio, 4),
        "detail_require_note": require_note,
        "detail_candidate_count": 0,
        "detail_sampled_count": 0,
        "detail_skipped_count": 0,
        "detail_fetch_error_count": 0,
        "detail_parse_empty_count": 0,
        "detail_enriched_count": 0,
        "detail_forbidden_count": 0,
        "detail_blocked": False,
    }

    for row in rows:
        if not row.detail_url:
            continue

        metrics["detail_candidate_count"] += 1

        # 业务要求：只要有详情页就尽量抓 note，避免采样后长期看不到 note。
        should_fetch = require_note or _should_sample_detail(row, ratio)
        if not should_fetch:
            metrics["detail_skipped_count"] += 1
            continue

        metrics["detail_sampled_count"] += 1

        try:
            detail_html = _fetch_html(session, row.detail_url)
        except Exception as exc:  # noqa: BLE001
            metrics["detail_fetch_error_count"] += 1
            if "403" in str(exc):
                metrics["detail_forbidden_count"] += 1
            continue

        detail_fields = _extract_detail_fields(detail_html)
        row.detail_employer = detail_fields["detail_employer"]
        row.detail_note = detail_fields["detail_note"]
        row.detail_city = detail_fields["detail_city"]
        row.detail_state = detail_fields["detail_state"]

        if any(detail_fields.values()):
            metrics["detail_enriched_count"] += 1
        else:
            metrics["detail_parse_empty_count"] += 1

        time.sleep(FETCH_DELAY_SECONDS)

    metrics["detail_blocked"] = (
        metrics["detail_sampled_count"] > 0
        and metrics["detail_enriched_count"] == 0
        and metrics["detail_forbidden_count"] == metrics["detail_sampled_count"]
    )
    return metrics


def _dedupe(rows: list[CaseRow]) -> list[CaseRow]:
    latest: dict[str, CaseRow] = {}

    def score(item: CaseRow) -> tuple:
        check_dt = _parse_date(item.check_date) or date(1900, 1, 1)
        complete_dt = _parse_date(item.complete_date) or date(1900, 1, 1)
        try:
            reported = int(item.waiting_days_reported)
        except ValueError:
            reported = -1
        return (item.event, check_dt, complete_dt, reported)

    for row in rows:
        key = row.case_number or f"{row.nickname}|{row.visa_type}|{row.check_date}|{row.consulate}"
        old = latest.get(key)
        if old is None or score(row) >= score(old):
            latest[key] = row

    return list(latest.values())


def fetch_cases(
    all_months: bool = False,
    months: int = 6,
    from_month: str | None = None,
    sources: list[str] | None = None,
) -> FetchResult:
    session = _session()
    observation_date = date.today()
    selected_sources = _normalize_sources(sources)

    index_html = _fetch_html(session, CHECKEE_BASE_URL)
    source_discovery = _extract_entry_points(index_html)
    all_available_months: list[str] = []
    target_months: list[str] = []
    truncated_by_limit = False
    source_case_counts: dict[str, int] = {name: 0 for name in selected_sources}

    if DEFAULT_FETCH_SOURCE in selected_sources:
        all_available_months = _extract_months(index_html)
        target_months, truncated_by_limit = _pick_months(
            all_available_months,
            all_months=all_months,
            recent_n=months,
            from_month=from_month,
        )

    rows: list[CaseRow] = []
    months_with_rows: list[str] = []
    months_without_rows: list[str] = []
    for idx, month in enumerate(target_months):
        page_url = urljoin(CHECKEE_BASE_URL, f"main.php?dispdate={month}")
        html = _fetch_html(session, page_url)
        month_rows = _parse_month_rows(month, html, observation_date)
        rows.extend(month_rows)
        source_case_counts[DEFAULT_FETCH_SOURCE] = source_case_counts.get(DEFAULT_FETCH_SOURCE, 0) + len(month_rows)
        if month_rows:
            months_with_rows.append(month)
        else:
            months_without_rows.append(month)
        if idx < len(target_months) - 1:
            time.sleep(FETCH_DELAY_SECONDS)

    latest_snapshot_rows: list[CaseRow] = []
    if LATEST_FETCH_SOURCE in selected_sources:
        latest_url = urljoin(CHECKEE_BASE_URL, "main.php")
        latest_html = _fetch_html(session, latest_url)
        inferred_month = (
            target_months[0]
            if target_months
            else (all_available_months[0] if all_available_months else observation_date.strftime("%Y-%m"))
        )
        latest_snapshot_rows = _parse_month_rows(inferred_month, latest_html, observation_date)
        rows.extend(latest_snapshot_rows)
        source_case_counts[LATEST_FETCH_SOURCE] = source_case_counts.get(LATEST_FETCH_SOURCE, 0) + len(latest_snapshot_rows)

    deduped_rows = _dedupe(rows)
    detail_coverage = _enrich_detail_fields(deduped_rows, session, DETAIL_FETCH_SAMPLE_RATIO)

    coverage = {
        "selected_sources": selected_sources,
        "source_case_counts": source_case_counts,
        "available_month_count": len(all_available_months),
        "selected_month_count": len(target_months),
        "parsed_month_count": len(months_with_rows),
        "latest_snapshot_case_count": len(latest_snapshot_rows),
        "months_with_rows": months_with_rows,
        "months_without_rows": months_without_rows,
        "raw_case_count": len(rows),
        "deduped_case_count": len(deduped_rows),
        "dedup_removed_count": max(0, len(rows) - len(deduped_rows)),
        **detail_coverage,
    }

    return FetchResult(
        rows=deduped_rows,
        fetched_months=target_months,
        truncated_by_limit=truncated_by_limit,
        selected_sources=selected_sources,
        source_discovery=source_discovery,
        coverage=coverage,
    )

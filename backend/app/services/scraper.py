from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.core.config import (
    CHECKEE_BASE_URL,
    FETCH_DELAY_SECONDS,
    REQUEST_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    RETRY_SLEEP_SECONDS,
    USER_AGENT,
)


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


def _pick_months(months: list[str], all_months: bool, recent_n: int, from_month: str | None) -> list[str]:
    if all_months:
        return months
    if from_month:
        return [m for m in months if _month_key(m) >= _month_key(from_month)]
    return months[: max(1, recent_n)]


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
            )
        )
    return parsed


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


def fetch_cases(all_months: bool = False, months: int = 6, from_month: str | None = None) -> tuple[list[CaseRow], list[str]]:
    session = _session()
    observation_date = date.today()

    index_html = _fetch_html(session, CHECKEE_BASE_URL)
    all_available_months = _extract_months(index_html)
    target_months = _pick_months(all_available_months, all_months=all_months, recent_n=months, from_month=from_month)

    rows: list[CaseRow] = []
    for idx, month in enumerate(target_months):
        page_url = urljoin(CHECKEE_BASE_URL, f"main.php?dispdate={month}")
        html = _fetch_html(session, page_url)
        rows.extend(_parse_month_rows(month, html, observation_date))
        if idx < len(target_months) - 1:
            time.sleep(FETCH_DELAY_SECONDS)

    return _dedupe(rows), target_months

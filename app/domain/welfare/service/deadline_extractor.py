"""정책 본문에서 명확한 신청 종료일만 보수적으로 추출한다."""

import re
from collections import defaultdict
from datetime import date

from sqlmodel import Session, select

from app.common.timezone import now_kst
from app.domain.welfare.entity.models import WelfarePolicy

_PERIOD_KEYWORDS = (
    "신청기간",
    "신청 기간",
    "모집기간",
    "모집 기간",
    "신청접수기간",
    "신청접수 기간",
    "접수기간",
    "접수 기간",
)
_YEAR_PATTERN = re.compile(r"'?((?:20)?\d{2})\s*(?:년|\.)")
_DATE_PATTERN = re.compile(
    r"'?((?:20)?\d{2})?\s*(?:년|\.)?\s*"
    r"(\d{1,2})\s*(?:월|\.)\s*(\d{1,2})\s*(?:일|\.)?"
)


def _normalize_year(raw_year: str | None, fallback: int) -> int:
    if not raw_year:
        return fallback
    year = int(raw_year)
    return 2000 + year if year < 100 else year


def extract_application_deadline(text: str, reference_year: int) -> date | None:
    """신청·모집 기간의 물결표 오른쪽 종료일을 반환한다.

    본문에는 지급일, 저축 입금일, 이용 기간처럼 신청 마감과 무관한 날짜도
    많다. 오탐 알림을 막기 위해 신청/모집/접수 기간 키워드와 시작~종료 형식이
    같은 줄에 명시된 경우만 인정한다.
    """
    candidates: list[date] = []
    for line in text.splitlines():
        if "~" not in line or not any(keyword in line for keyword in _PERIOD_KEYWORDS):
            continue
        left, right = line.split("~", 1)
        years = _YEAR_PATTERN.findall(left)
        fallback_year = _normalize_year(years[-1], reference_year) if years else reference_year
        match = _DATE_PATTERN.search(right)
        if match is None:
            continue
        raw_year, month, day = match.groups()
        try:
            candidates.append(
                date(_normalize_year(raw_year, fallback_year), int(month), int(day))
            )
        except ValueError:
            continue
    return max(candidates) if candidates else None


def backfill_application_deadlines(session: Session) -> tuple[int, int]:
    """기존 정책 행에 추출 가능한 마감일을 채운다.

    과거 청크별 중복 행은 같은 service_id끼리 본문을 합쳐 분석하고, 검색 시
    어느 행이 선택돼도 같은 결과가 나오도록 해당 정책의 모든 행을 갱신한다.
    이미 관리자가 입력한 마감일은 덮어쓰지 않는다.
    """
    rows = list(session.exec(select(WelfarePolicy)).all())
    grouped: dict[str, list[WelfarePolicy]] = defaultdict(list)
    for row in rows:
        grouped[row.service_id].append(row)

    updated_policies = 0
    updated_rows = 0
    for policy_rows in grouped.values():
        if any(row.application_deadline is not None for row in policy_rows):
            continue
        combined = "\n".join(row.page_content for row in policy_rows)
        reference_year = max((row.year for row in policy_rows), default=now_kst().year)
        deadline = extract_application_deadline(combined, reference_year or now_kst().year)
        if deadline is None:
            continue
        for row in policy_rows:
            row.application_deadline = deadline
            row.updated_at = now_kst()
            session.add(row)
            updated_rows += 1
        updated_policies += 1
    session.commit()
    return updated_policies, updated_rows

"""
프로젝트 전역 한국 표준시(KST, UTC+9) 헬퍼.

모든 도메인에서 시간을 다룰 때 이 모듈의 KST 상수와 now_kst() 를 사용하여
일관되게 한국 시간을 기준으로 동작하도록 한다.

DB 컬럼이 TIMESTAMP (without tz) 이므로, aware datetime 을 저장하면
psycopg3 이 UTC 로 변환해서 저장하는 문제가 발생한다.
따라서 now_kst() 와 as_kst() 는 모두 naive KST wall time 을 반환하여
DB 에 KST 시간이 그대로 저장되고 비교도 naive 끼리 수행된다.
"""
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9), name="KST")


def now_kst() -> datetime:
    """현재 한국 시간을 naive datetime 으로 반환한다.

    naive 로 반환하는 이유:
    DB 컬럼이 TIMESTAMP (without tz) 이므로 aware datetime 을 저장하면
    psycopg3 이 UTC 로 변환해 저장한다. KST wall time 을 그대로 저장하려면
    tzinfo 를 제거한 naive 값을 전달해야 한다.
    """
    return datetime.now(KST).replace(tzinfo=None)


def as_kst(dt: datetime) -> datetime:
    """datetime 을 naive KST wall time 으로 정규화한다.

    DB 의 TIMESTAMP (without tz) 컬럼에서 읽은 naive 값은 KST wall time 으로
    해석한다. aware 값은 KST 로 변환 후 tzinfo 를 제거하여 naive 로 통일한다.
    비교 시 naive vs naive TypeError 를 피하기 위해 항상 naive 를 반환한다.
    """
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(KST).replace(tzinfo=None)
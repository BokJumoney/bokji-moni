"""
채팅 유틸 단위 테스트 (설계명세서 13.1).

- 제목 공백 정규화와 40자 절단
- 미리보기 200자 절단
- cursor encode/decode round trip
- 잘못된 base64 / timestamp / UUID cursor 거부
"""
import base64
import uuid
from datetime import datetime

import pytest

from app.common.exceptions import InvalidCursorError
from app.common.timezone import KST
from app.domain.chat.utils import (
    decode_cursor,
    encode_cursor,
    normalize_preview,
    normalize_title,
)


class TestNormalizeTitle:
    def test_simple(self):
        assert normalize_title("안녕하세요") == "안녕하세요"

    def test_whitespace_collapse(self):
        assert (
            normalize_title("실직 후 받을 수 있는\n 복지 정책이 궁금해요")
            == "실직 후 받을 수 있는 복지 정책이 궁금해요"
        )

    def test_trim(self):
        assert normalize_title("   앞뒤 공백   ") == "앞뒤 공백"

    def test_truncate_40(self):
        long = "가" * 50
        result = normalize_title(long)
        assert result.endswith("…")
        assert len(result) <= 41  # 40자 + …

    def test_exactly_40_not_truncated(self):
        exactly = "가" * 40
        assert normalize_title(exactly) == exactly

    def test_empty_returns_empty(self):
        assert normalize_title("   ") == ""


class TestNormalizePreview:
    def test_simple(self):
        assert normalize_preview("hi") == "hi"

    def test_whitespace_collapse(self):
        assert normalize_preview("a\nb  c") == "a b c"

    def test_truncate_200(self):
        long = "x" * 300
        result = normalize_preview(long)
        assert result.endswith("…")
        assert len(result) <= 201

    def test_exactly_200(self):
        exactly = "x" * 200
        assert normalize_preview(exactly) == exactly


class TestCursorEncodeDecode:
    def test_round_trip_aware(self):
        now = datetime(2026, 7, 14, 1, 24, 10, tzinfo=KST)
        cid = uuid.uuid4()
        ts2, cid2 = decode_cursor(encode_cursor(now, cid))
        assert cid2 == cid
        # decode_cursor 는 naive KST 를 반환한다
        assert ts2.tzinfo is None
        assert ts2.replace(microsecond=0) == now.replace(tzinfo=None, microsecond=0)

    def test_round_trip_naive(self):
        now = datetime(2026, 7, 14, 1, 24, 10)  # naive
        cid = uuid.uuid4()
        ts2, cid2 = decode_cursor(encode_cursor(now, cid))
        assert cid2 == cid

    def test_invalid_base64(self):
        with pytest.raises(InvalidCursorError):
            decode_cursor("!!!not-base64!!!")

    def test_missing_separator(self):
        raw = base64.urlsafe_b64encode(b"no-separator-here").decode("ascii").rstrip("=")
        with pytest.raises(InvalidCursorError):
            decode_cursor(raw)

    def test_bad_uuid(self):
        raw = base64.urlsafe_b64encode(
            f"2026-07-14T01:24:10|not-a-uuid".encode()
        ).decode("ascii").rstrip("=")
        with pytest.raises(InvalidCursorError):
            decode_cursor(raw)

    def test_bad_timestamp(self):
        raw = base64.urlsafe_b64encode(
            f"not-a-timestamp|{uuid.uuid4()}".encode()
        ).decode("ascii").rstrip("=")
        with pytest.raises(InvalidCursorError):
            decode_cursor(raw)
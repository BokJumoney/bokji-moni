"""정책 본문의 명시적인 신청 종료일 추출 규칙 테스트."""

import unittest
from datetime import date

from app.domain.welfare.service.deadline_extractor import extract_application_deadline


class DeadlineExtractorTest(unittest.TestCase):
    def test_extracts_short_year_period(self):
        text = "2026년 모집기간: '26.5.4.(월) ~ '26.5.20.(수)"
        self.assertEqual(date(2026, 5, 20), extract_application_deadline(text, 2026))

    def test_uses_context_year_when_end_has_no_year(self):
        text = "※ '26년 신규 신청기간: 3.30(월) 09:00 ~ 8.29(금) 16:00까지"
        self.assertEqual(date(2026, 8, 29), extract_application_deadline(text, 2026))

    def test_extracts_korean_full_date(self):
        text = "(신청기간) 2026년 1월 2일 ~ 2026년 1월 30일"
        self.assertEqual(date(2026, 1, 30), extract_application_deadline(text, 2026))

    def test_ignores_unrelated_monthly_deposit_deadline(self):
        text = "매월 22일 입금마감일 이전에 본인저축액을 납입합니다."
        self.assertIsNone(extract_application_deadline(text, 2026))

    def test_ignores_open_ended_policy(self):
        self.assertIsNone(extract_application_deadline("신청기간: 수시", 2026))


if __name__ == "__main__":
    unittest.main()

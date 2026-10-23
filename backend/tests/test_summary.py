import unittest
from datetime import date, datetime, timedelta, timezone

from app.models import ReadingInput
from app.services import calculate_summary, record_order_key
from seed_data import make_sample_records


class SummaryTests(unittest.TestCase):
    def test_empty_summary(self):
        summary = calculate_summary([], today=date(2026, 10, 20))
        self.assertEqual(summary["count"], 0)
        self.assertEqual(summary["trend"], "데이터 부족")
        self.assertEqual(len(summary["weekly_series"]), 7)

    def test_summary_uses_korean_date_without_system_timezone_database(self):
        summary = calculate_summary([])
        korean_today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
        self.assertEqual(summary["weekly_series"][-1]["date"], korean_today)

    def test_recent_upward_trend(self):
        first = date(2026, 10, 1)
        records = [{"date": (first + timedelta(days=index)).isoformat(), "value": 10 if index < 7 else 20} for index in range(14)]
        summary = calculate_summary(records, today=date(2026, 10, 14))
        self.assertEqual(summary["count"], 14)
        self.assertEqual(summary["total_value"], 210)
        self.assertEqual(summary["trend"], "상승")
        self.assertEqual(summary["trend_percent"], 100)
        self.assertEqual(summary["this_month_total"], 210)

    def test_sample_dataset_has_over_100_points(self):
        records = make_sample_records(today=date(2026, 10, 20))
        self.assertEqual(len(records), 120)
        self.assertEqual(len({item["date"] for item in records}), 120)
        self.assertEqual(calculate_summary(records, today=date(2026, 10, 20))["count"], 120)

    def test_best_day_combines_multiple_records(self):
        records = [
            {"date": "2026-10-19", "value": 30},
            {"date": "2026-10-20", "value": 20},
            {"date": "2026-10-20", "value": 20},
        ]
        summary = calculate_summary(records, today=date(2026, 10, 20))
        self.assertEqual(summary["best_date"], "2026-10-20")
        self.assertEqual(summary["best_day_total"], 40)

    def test_same_date_uses_creation_time_for_trend(self):
        records = [
            {"id": f"{13 - index:02}", "date": "2026-10-20", "value": 10 if index < 7 else 20,
             "created_at": f"2026-10-20T{index:02}:00:00+00:00"}
            for index in range(14)
        ]
        summary = calculate_summary(list(reversed(records)), today=date(2026, 10, 20))
        self.assertEqual(summary["recent_average"], 20)
        self.assertEqual(summary["previous_average"], 10)
        self.assertEqual(summary["trend"], "상승")
        self.assertEqual(summary["trend_percent"], 100)

    def test_old_records_without_creation_time_have_stable_fallback(self):
        records = [
            {"id": "sample-a", "date": "2026-10-20"},
            {"id": "new-record", "date": "2026-10-20", "created_at": "2026-10-20T12:00:00+00:00"},
            {"id": "sample-b", "date": "2026-10-20"},
        ]
        self.assertEqual(
            [item["id"] for item in sorted(records, key=record_order_key, reverse=True)],
            ["new-record", "sample-b", "sample-a"],
        )

    def test_nonpositive_value_is_rejected(self):
        with self.assertRaises(ValueError):
            ReadingInput(date="2026-10-20", value=0, memo="테스트")

    def test_memo_over_500_characters_is_rejected(self):
        with self.assertRaises(ValueError):
            ReadingInput(date="2026-10-20", value=20, memo="a" * 501)

    def test_date_requires_exact_yyyy_mm_dd_string(self):
        for invalid_date in (1792454400, "2026-10-20T00:00:00", "2026-2-20", "2026-02-30"):
            with self.subTest(invalid_date=invalid_date), self.assertRaises(ValueError):
                ReadingInput(date=invalid_date, value=20)

    def test_reading_time_requires_a_number_not_boolean(self):
        for invalid_value in (True, False, "20"):
            with self.subTest(invalid_value=invalid_value), self.assertRaises(ValueError):
                ReadingInput(date="2026-10-20", value=invalid_value)


if __name__ == "__main__":
    unittest.main()

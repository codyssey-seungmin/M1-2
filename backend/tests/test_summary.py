import unittest
from datetime import date, timedelta

from app.models import ReadingInput
from app.services import calculate_summary
from seed_data import make_sample_records


class SummaryTests(unittest.TestCase):
    def test_empty_summary(self):
        summary = calculate_summary([], today=date(2026, 10, 20))
        self.assertEqual(summary["count"], 0)
        self.assertEqual(summary["trend"], "데이터 부족")
        self.assertEqual(len(summary["weekly_series"]), 7)

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

    def test_nonpositive_value_is_rejected(self):
        with self.assertRaises(ValueError):
            ReadingInput(date="2026-10-20", value=0, memo="테스트")


if __name__ == "__main__":
    unittest.main()

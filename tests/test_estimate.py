"""Checks for date boundaries and published usage calculations."""

import ast
from datetime import UTC, date, datetime, timedelta
import importlib.util
import json
from pathlib import Path
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components/flemish_energy"
SPEC = importlib.util.spec_from_file_location("estimate", COMPONENT / "estimate.py")
estimate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(estimate)


class EstimateTests(unittest.TestCase):
    def test_brussels_days_cover_dst_transitions(self):
        for month, day, hours in [(3, 30, 23), (10, 26, 25), (11, 22, 24)]:
            with self.subTest(month=month):
                _, start, end = estimate.day_window(datetime(2026, month, day, tzinfo=UTC), 1)
                self.assertEqual(end - start, timedelta(hours=hours))

    def test_zero_usage_is_distinct_from_missing_data(self):
        self.assertIsNone(estimate.measured_usage([]))
        self.assertIsNone(estimate.measured_usage([{"change": None}]))
        self.assertEqual(estimate.measured_usage([{"change": 0}]), 0)
        self.assertEqual(estimate.measured_usage([{"change": 3}, {"change": -0.5}]), 2.5)

    def test_rate_must_be_finite(self):
        self.assertIsNone(estimate.finite_number("unavailable"))
        self.assertIsNone(estimate.finite_number("NaN"))
        self.assertEqual(estimate.finite_number("-0.05"), -0.05)

    def test_latest_day_uses_brussels_time_and_preserves_zero(self):
        rows = [
            {"start": datetime(2026, 3, 28, 23, tzinfo=UTC).timestamp(), "change": 0},
            {"start": datetime(2026, 3, 29, 22, tzinfo=UTC).timestamp(), "change": 8},
        ]
        self.assertEqual(
            estimate.latest_published_usage(rows, date(2026, 3, 16), date(2026, 3, 30)),
            (date(2026, 3, 29), 0),
        )

    def test_latest_day_falls_back_when_newer_rows_are_unusable(self):
        rows = [
            {"start": datetime(2026, 11, 20, 10, tzinfo=UTC).timestamp(), "change": 4},
            {"start": datetime(2026, 11, 21, 10, tzinfo=UTC).timestamp(), "change": None},
        ]
        self.assertEqual(
            estimate.latest_published_usage(rows, date(2026, 11, 8), date(2026, 11, 22)),
            (date(2026, 11, 20), 4),
        )

    def test_recent_all_zero_day_does_not_hide_weekend_off_peak_usage(self):
        today = date(2026, 11, 23)
        dates = [date(2026, 11, day) for day in (20, 21, 22)]
        starts = [datetime(day.year, day.month, day.day, 1, tzinfo=UTC).timestamp() for day in dates]

        def rows(*changes):
            return [{"start": start, "change": change} for start, change in zip(starts, changes)]

        provisional = estimate.provisional_electricity_days(
            rows(0, 67.388, 0), rows(0, 0, 0), today
        )
        self.assertEqual(provisional, frozenset({dates[2]}))
        self.assertEqual(
            estimate.latest_published_usage(
                rows(0, 0, 0), dates[0], today, exclude_days=provisional
            ),
            (dates[1], 0),
        )
        self.assertEqual(
            estimate.latest_published_usage(
                rows(0, 67.388, 0), dates[0], today, exclude_days=provisional
            ),
            (dates[1], 67.388),
        )

    def test_component_python_and_json_parse(self):
        for file in COMPONENT.rglob("*.py"):
            ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        for file in COMPONENT.rglob("*.json"):
            json.loads(file.read_text(encoding="utf-8"))

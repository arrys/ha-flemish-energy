"""Checks for date boundaries and published usage calculations."""

import ast
from datetime import UTC, datetime, timedelta
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

    def test_component_python_and_json_parse(self):
        for file in COMPONENT.rglob("*.py"):
            ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        for file in COMPONENT.rglob("*.json"):
            json.loads(file.read_text(encoding="utf-8"))

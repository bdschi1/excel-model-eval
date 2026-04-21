"""Tests for CI mode in main.py."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCIFlagLimitsScenarios(unittest.TestCase):
    """test_ci_flag_limits_scenarios: CI mode audits at most 1 model file."""

    def test_ci_flag_limits_scenarios(self):
        """_run_ci_mode audits exactly 1 model file (not multiple)."""
        from main import _run_ci_mode

        mock_ingestor = MagicMock()
        mock_ingestor.ingest.return_value = True
        mock_ingestor.sheets_formulas = {}
        mock_ingestor.sheets_values = {}

        mock_dep = MagicMock()
        mock_dep.graph = MagicMock()
        mock_dep.build_graph.return_value = None

        mock_auditor = MagicMock()
        mock_auditor.run_all_checks.return_value = [
            {"type": "Hard-coded Plug", "severity": "High", "location": "Sheet1!R1", "detail": "test"}
        ]

        ingest_calls: list[str] = []

        def fake_ingestor_init(file_path):
            ingest_calls.append(file_path)
            return mock_ingestor

        with (
            patch("main.ModelIngestor", side_effect=fake_ingestor_init),
            patch("main.DependencyEngine", return_value=mock_dep),
            patch("main.ModelAuditor", return_value=mock_auditor),
            patch("os.path.exists", return_value=True),
            patch("sys.exit"),
        ):
            _run_ci_mode("sample_models/BOBWEIR_Model.xlsx")

        # Only 1 file audited
        self.assertEqual(len(ingest_calls), 1)


class TestCIOutputIsValidJSON(unittest.TestCase):
    """test_ci_output_is_valid_json: stdout must be parseable JSON."""

    def test_ci_output_is_valid_json(self):
        """_run_ci_mode prints valid JSON to stdout."""
        import io

        from main import _run_ci_mode

        mock_ingestor = MagicMock()
        mock_ingestor.ingest.return_value = True
        mock_ingestor.sheets_formulas = {}
        mock_ingestor.sheets_values = {}

        mock_dep = MagicMock()
        mock_dep.graph = MagicMock()

        mock_auditor = MagicMock()
        mock_auditor.run_all_checks.return_value = [
            {"type": "External Link", "severity": "Medium", "location": "A1", "detail": "test"},
        ]

        captured = io.StringIO()

        with (
            patch("main.ModelIngestor", return_value=mock_ingestor),
            patch("main.DependencyEngine", return_value=mock_dep),
            patch("main.ModelAuditor", return_value=mock_auditor),
            patch("os.path.exists", return_value=True),
            patch("sys.exit"),
            patch("sys.stdout", captured),
        ):
            _run_ci_mode("sample_models/BOBWEIR_Model.xlsx")

        output_text = captured.getvalue().strip()
        self.assertTrue(output_text, "stdout should not be empty")
        parsed = json.loads(output_text)
        self.assertTrue(parsed.get("ci_mode"))
        self.assertIn("models_evaluated", parsed)
        self.assertIn("critical_issues_found", parsed)
        self.assertIn("pass", parsed)
        self.assertIn("summary", parsed)


class TestCIExits1OnThresholdFailure(unittest.TestCase):
    """test_ci_exits_1_on_threshold_failure: sys.exit(1) when critical issues exceed threshold."""

    def test_ci_exits_1_on_threshold_failure(self):
        """When critical issues exceed _CI_THRESHOLD_MAX_CRITICAL, sys.exit(1) is called."""
        from main import _CI_THRESHOLD_MAX_CRITICAL, _run_ci_mode

        mock_ingestor = MagicMock()
        mock_ingestor.ingest.return_value = True
        mock_ingestor.sheets_formulas = {}
        mock_ingestor.sheets_values = {}

        mock_dep = MagicMock()
        mock_dep.graph = MagicMock()

        # Generate more High-severity issues than the threshold
        many_issues = [
            {"type": "Hard-coded Plug", "severity": "High", "location": f"R{i}", "detail": "plug"}
            for i in range(_CI_THRESHOLD_MAX_CRITICAL + 2)  # threshold + 2 = guaranteed fail
        ]

        mock_auditor = MagicMock()
        mock_auditor.run_all_checks.return_value = many_issues

        exit_calls: list[int] = []

        def mock_exit(code=0):
            exit_calls.append(code)

        with (
            patch("main.ModelIngestor", return_value=mock_ingestor),
            patch("main.DependencyEngine", return_value=mock_dep),
            patch("main.ModelAuditor", return_value=mock_auditor),
            patch("os.path.exists", return_value=True),
            patch("sys.exit", side_effect=mock_exit),
        ):
            try:
                _run_ci_mode("sample_models/BOBWEIR_Model.xlsx")
            except SystemExit:
                pass

        self.assertTrue(exit_calls, "sys.exit should have been called")
        self.assertEqual(exit_calls[-1], 1, "Expected sys.exit(1) for too many critical issues")


if __name__ == "__main__":
    unittest.main()

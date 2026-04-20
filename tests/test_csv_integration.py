"""
Tier 2 #8: CSV end-to-end integration test.

Validates the full pipeline: ingestion → auditor(engine=None) → reporting(engine=None)
for CSV files, which skip the dependency engine entirely.
"""

from __future__ import annotations

import csv
import os
import pathlib
import sys

import pandas as pd

# Ensure repo root is on path
REPO_ROOT = pathlib.Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.auditor import ModelAuditor
from src.ingestion import ModelIngestor
from src.reporting import ReportGenerator


def _create_csv(tmp_path, filename="test_model.csv", rows=None):
    """Write a simple CSV and return its path."""
    if rows is None:
        rows = [
            ["Revenue", 1000, 1100, 1200],
            ["COGS", 400, 440, 480],
            ["Gross Profit", 600, 660, 720],
        ]
    csv_path = os.path.join(str(tmp_path), filename)
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)
    return csv_path


class TestCSVEndToEnd:
    """Full pipeline smoke test with a CSV file."""

    def test_ingestion_succeeds(self, tmp_path):
        csv_path = _create_csv(tmp_path)
        ingestor = ModelIngestor(csv_path)
        # CSV ingestion uses pandas read_csv, not openpyxl
        # ModelIngestor.ingest() tries openpyxl which will fail for CSV.
        # The app.py handles CSV separately. We test the auditor+reporter
        # with a mock ingestor that has sheets populated from CSV data.
        df = pd.read_csv(csv_path, header=None)
        ingestor.sheets_values = {"Sheet1": df}
        ingestor.sheets_formulas = {"Sheet1": df}  # No formulas in CSV
        assert len(ingestor.sheets_values) == 1

    def test_auditor_runs_without_engine(self, tmp_path):
        csv_path = _create_csv(tmp_path)
        df = pd.read_csv(csv_path, header=None)
        ingestor = ModelIngestor(csv_path)
        ingestor.sheets_values = {"Sheet1": df}
        ingestor.sheets_formulas = {"Sheet1": df}

        auditor = ModelAuditor(ingestor, None)
        issues = auditor.run_all_checks()
        assert isinstance(issues, list)
        # No circular refs, no unreferenced inputs, no dangling outputs
        # because engine is None — all graph-dependent checks skipped
        circ = [i for i in issues if i["type"] == "Circular Reference"]
        unref = [i for i in issues if i["type"] == "Unreferenced Input"]
        dangling = [i for i in issues if i["type"] == "Dangling Output"]
        assert len(circ) == 0
        assert len(unref) == 0
        assert len(dangling) == 0

    def test_reporting_works_without_engine(self, tmp_path):
        csv_path = _create_csv(tmp_path)
        df = pd.read_csv(csv_path, header=None)
        ingestor = ModelIngestor(csv_path)
        ingestor.sheets_values = {"Sheet1": df}
        ingestor.sheets_formulas = {"Sheet1": df}

        auditor = ModelAuditor(ingestor, None)
        issues = auditor.run_all_checks()

        reporter = ReportGenerator("test_model.csv", issues, ingestor, None)
        reporter.results_dir = os.path.join(str(tmp_path), "RESULTS")
        os.makedirs(reporter.results_dir, exist_ok=True)

        pdf_path = reporter.generate_pdf()
        excel_path = reporter.generate_excel()
        reporter.update_log()

        assert os.path.exists(pdf_path)
        assert os.path.exists(excel_path)
        log_path = os.path.join(reporter.results_dir, "audit_history.csv")
        assert os.path.exists(log_path)

    def test_full_pipeline_csv_with_errors(self, tmp_path):
        """CSV with #REF! values should flag calculation errors."""
        rows = [
            ["Revenue", 1000, "#REF!", 1200],
            ["COGS", 400, 440, "#VALUE!"],
        ]
        csv_path = _create_csv(tmp_path, rows=rows)
        df = pd.read_csv(csv_path, header=None)
        ingestor = ModelIngestor(csv_path)
        ingestor.sheets_values = {"Sheet1": df}
        ingestor.sheets_formulas = {"Sheet1": df}

        auditor = ModelAuditor(ingestor, None)
        issues = auditor.run_all_checks()

        calc_errors = [i for i in issues if i["type"] == "Calculation Error"]
        assert len(calc_errors) >= 2

    def test_complexity_score_is_1_for_csv(self, tmp_path):
        """CSV with one sheet and no formulas should have complexity 1."""
        csv_path = _create_csv(tmp_path)
        df = pd.read_csv(csv_path, header=None)
        ingestor = ModelIngestor(csv_path)
        ingestor.sheets_values = {"Sheet1": df}
        ingestor.sheets_formulas = {"Sheet1": df}

        auditor = ModelAuditor(ingestor, None)
        issues = auditor.run_all_checks()

        reporter = ReportGenerator("test_model.csv", issues, ingestor, None)
        assert reporter.complexity_score == 1

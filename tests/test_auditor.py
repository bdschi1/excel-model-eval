"""
Tests for src/auditor.py -- ModelAuditor

Verifies:
1. External link detection (formula with [...])
2. Calculation error detection (#REF!, #VALUE!, etc.)
3. Hard-coded plug detection
4. Balance sheet integrity check (matching and mismatching)
5. Clean model (no issues)
6. Issue structure format
7. get_explanation() helper
"""

from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock

import networkx as nx
import pandas as pd

# Ensure repo root is on path
REPO_ROOT = pathlib.Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.auditor import (
    ISSUE_EXPLANATIONS,
    ModelAuditor,
    get_explanation,
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _mock_ingestor(sheets_values=None, sheets_formulas=None):
    """Create a mock ingestor with given value and formula DataFrames."""
    ingestor = MagicMock()
    ingestor.sheets_values = sheets_values or {}
    ingestor.sheets_formulas = sheets_formulas or {}
    return ingestor


def _mock_dep_engine(graph=None):
    """Create a mock dependency engine with an optional pre-built graph."""
    engine = MagicMock()
    engine.graph = graph if graph is not None else nx.DiGraph()
    return engine


def _make_auditor(sheets_values=None, sheets_formulas=None, graph=None):
    """Convenience: build auditor with mock ingestor + dependency engine."""
    ingestor = _mock_ingestor(sheets_values, sheets_formulas)
    dep_engine = _mock_dep_engine(graph)
    return ModelAuditor(ingestor, dep_engine)


# ==================================================================
# Tests
# ==================================================================


class TestExternalLinkDetection:
    """check_external_links() -- external link nodes and calculation errors."""

    def test_detects_external_link_nodes(self):
        g = nx.DiGraph()
        g.add_edge("EXT_LINK:[OtherBook.xlsx]Sheet1!A1", "Summary!B5")
        auditor = _make_auditor(
            sheets_values={"Summary": pd.DataFrame([[1, 2]])},
            graph=g,
        )
        auditor.check_external_links()
        ext_issues = [i for i in auditor.issues if i["type"] == "External Link"]
        assert len(ext_issues) == 1
        assert ext_issues[0]["severity"] == "Medium"

    def test_no_external_links_clean(self):
        g = nx.DiGraph()
        g.add_edge("Sheet1!A1", "Sheet1!B1")
        auditor = _make_auditor(
            sheets_values={"Sheet1": pd.DataFrame([[10, 20]])},
            graph=g,
        )
        auditor.check_external_links()
        ext_issues = [i for i in auditor.issues if i["type"] == "External Link"]
        assert len(ext_issues) == 0


class TestCalculationErrorDetection:
    """check_external_links() also scans for #REF!, #VALUE!, etc."""

    def test_detects_ref_error(self):
        df_vals = pd.DataFrame([["Revenue", "#REF!", 100]])
        auditor = _make_auditor(sheets_values={"Sheet1": df_vals})
        auditor.check_external_links()
        calc_issues = [i for i in auditor.issues if i["type"] == "Calculation Error"]
        assert len(calc_issues) >= 1
        assert calc_issues[0]["severity"] == "High"

    def test_detects_value_error(self):
        df_vals = pd.DataFrame([[100, "#VALUE!", 200]])
        auditor = _make_auditor(sheets_values={"Sheet1": df_vals})
        auditor.check_external_links()
        calc_issues = [i for i in auditor.issues if i["type"] == "Calculation Error"]
        assert len(calc_issues) >= 1

    def test_detects_div_zero(self):
        df_vals = pd.DataFrame([[100, "#DIV/0!"]])
        auditor = _make_auditor(sheets_values={"Sheet1": df_vals})
        auditor.check_external_links()
        calc_issues = [i for i in auditor.issues if i["type"] == "Calculation Error"]
        assert len(calc_issues) >= 1

    def test_detects_name_error(self):
        df_vals = pd.DataFrame([["#NAME?"]])
        auditor = _make_auditor(sheets_values={"Sheet1": df_vals})
        auditor.check_external_links()
        calc_issues = [i for i in auditor.issues if i["type"] == "Calculation Error"]
        assert len(calc_issues) >= 1

    def test_no_errors_in_clean_data(self):
        df_vals = pd.DataFrame([[100, 200, 300], [400, 500, 600]])
        auditor = _make_auditor(sheets_values={"Sheet1": df_vals})
        auditor.check_external_links()
        calc_issues = [i for i in auditor.issues if i["type"] == "Calculation Error"]
        assert len(calc_issues) == 0


class TestDataSheetSkipping:
    """Verify expanded data-sheet skip list in plug detection."""

    # A row that would produce a plug finding on a normal sheet:
    # 1 label + 7 formulas + 1 hardcode = 87.5% formulas
    _PLUG_ROW = ["Label", "=A1", "=B1", "=C1", "=D1", 999, "=F1", "=G1", "=H1"]

    def test_skips_lookup_sheets(self):
        df = pd.DataFrame([self._PLUG_ROW])
        auditor = _make_auditor(sheets_formulas={"LookupTables": df})
        auditor.detect_hardcoded_plugs()
        assert len([i for i in auditor.issues if i["type"] == "Hard-coded Plug"]) == 0

    def test_skips_reference_sheets(self):
        df = pd.DataFrame([self._PLUG_ROW])
        auditor = _make_auditor(sheets_formulas={"Reference_Data": df})
        auditor.detect_hardcoded_plugs()
        assert len([i for i in auditor.issues if i["type"] == "Hard-coded Plug"]) == 0

    def test_skips_archive_sheets(self):
        df = pd.DataFrame([self._PLUG_ROW])
        auditor = _make_auditor(sheets_formulas={"archive_2024": df})
        auditor.detect_hardcoded_plugs()
        assert len([i for i in auditor.issues if i["type"] == "Hard-coded Plug"]) == 0

    def test_skips_source_sheets(self):
        df = pd.DataFrame([self._PLUG_ROW])
        auditor = _make_auditor(sheets_formulas={"SourceData": df})
        auditor.detect_hardcoded_plugs()
        assert len([i for i in auditor.issues if i["type"] == "Hard-coded Plug"]) == 0

    def test_skips_data_prefix_sheets(self):
        df = pd.DataFrame([self._PLUG_ROW])
        auditor = _make_auditor(sheets_formulas={"data_inputs": df})
        auditor.detect_hardcoded_plugs()
        assert len([i for i in auditor.issues if i["type"] == "Hard-coded Plug"]) == 0

    def test_skips_data_suffix_sheets(self):
        df = pd.DataFrame([self._PLUG_ROW])
        auditor = _make_auditor(sheets_formulas={"market_data": df})
        auditor.detect_hardcoded_plugs()
        assert len([i for i in auditor.issues if i["type"] == "Hard-coded Plug"]) == 0

    def test_normal_sheets_not_skipped(self):
        df = pd.DataFrame([self._PLUG_ROW])
        for name in ("DCF Model", "Income Statement"):
            auditor = _make_auditor(sheets_formulas={name: df})
            auditor.detect_hardcoded_plugs()
            plugs = [i for i in auditor.issues if i["type"] == "Hard-coded Plug"]
            assert len(plugs) >= 1, f"Expected plug findings for sheet '{name}'"


class TestHardcodedPlugDetection:
    """detect_hardcoded_plugs() -- heuristic plug detection."""

    def test_detects_plug_in_formula_row(self):
        """Row with >70% formulas but one hardcoded value after SKIP_COLS=3."""
        # SKIP_COLS = 3, so cols 0-2 are skipped (labels + historicals)
        # Cols 3-10: 7 formulas + 1 hardcode = 8 non-null items, 87.5% formulas
        row_data = ["Label", 2020, 2021,
                     "=A1", "=B1", "=C1", "=D1", 999, "=F1", "=G1", "=H1"]
        df_formulas = pd.DataFrame([row_data])
        auditor = _make_auditor(sheets_formulas={"DCF": df_formulas})
        auditor.detect_hardcoded_plugs()
        plug_issues = [i for i in auditor.issues if i["type"] == "Hard-coded Plug"]
        assert len(plug_issues) >= 1
        assert plug_issues[0]["severity"] == "High"

    def test_no_plug_in_all_formula_row(self):
        """Row that is 100% formulas should not flag a plug."""
        # Use None for label so _detect_label_cols sees non-numeric/non-formula
        # then all remaining cells are formulas. Must avoid having numeric values
        # like 2020, 2021 in the label zone since _detect_label_cols stops at numerics.
        row_data = [None, None, None] + ["=A1"] * 8
        df_formulas = pd.DataFrame([row_data])
        auditor = _make_auditor(sheets_formulas={"DCF": df_formulas})
        auditor.detect_hardcoded_plugs()
        plug_issues = [i for i in auditor.issues if i["type"] == "Hard-coded Plug"]
        assert len(plug_issues) == 0

    def test_no_plug_in_all_values_row(self):
        """Row that is all values (no formulas) should not flag."""
        row_data = ["Label", 2020, 2021] + [100] * 8
        df_formulas = pd.DataFrame([row_data])
        auditor = _make_auditor(sheets_formulas={"Income": df_formulas})
        auditor.detect_hardcoded_plugs()
        plug_issues = [i for i in auditor.issues if i["type"] == "Hard-coded Plug"]
        assert len(plug_issues) == 0

    def test_skips_raw_data_sheets(self):
        """Sheets named 'raw' or 'cache' should be skipped."""
        row_data = ["Label", 2020, 2021,
                     "=A1", "=B1", "=C1", "=D1", 999, "=F1", "=G1", "=H1"]
        df_formulas = pd.DataFrame([row_data])
        auditor = _make_auditor(sheets_formulas={"raw_data": df_formulas})
        auditor.detect_hardcoded_plugs()
        plug_issues = [i for i in auditor.issues if i["type"] == "Hard-coded Plug"]
        assert len(plug_issues) == 0

    def test_skips_cache_sheets(self):
        row_data = ["Label", 2020, 2021,
                     "=A1", "=B1", "=C1", "=D1", 999, "=F1", "=G1", "=H1"]
        df_formulas = pd.DataFrame([row_data])
        auditor = _make_auditor(sheets_formulas={"FactSetCache": df_formulas})
        auditor.detect_hardcoded_plugs()
        assert len(auditor.issues) == 0

    def test_short_row_not_flagged_by_threshold(self):
        """Rows with <= 5 non-null items after label cols should not trigger the
        primary (threshold) check. The secondary sandwich check may still fire
        if a numeric value is flanked by formulas."""
        # 3 items after label: "=A1", "=C1" -> 2 formulas, 0 hardcodes. No plug.
        row_data = ["Label", "=A1", "=C1"]
        df_formulas = pd.DataFrame([row_data])
        auditor = _make_auditor(sheets_formulas={"Sheet1": df_formulas})
        auditor.detect_hardcoded_plugs()
        assert len(auditor.issues) == 0


class TestBalanceSheetIntegrity:
    """verify_balance_sheet_integrity() tests."""

    def test_balanced_sheet_no_issues(self):
        """Total Assets == Total Liabilities & Equity => no issue."""
        df_vals = pd.DataFrame([
            ["Total Assets", None, 1000, 1100, 1200],
            ["Total Liabilities & Equity", None, 1000, 1100, 1200],
        ])
        auditor = _make_auditor(sheets_values={"Balance Sheet": df_vals})
        auditor.verify_balance_sheet_integrity()
        bs_issues = [i for i in auditor.issues if i["type"] == "Accounting Mismatch"]
        assert len(bs_issues) == 0

    def test_imbalanced_sheet_flags_issue(self):
        """Variance > $1 should flag critical issue."""
        df_vals = pd.DataFrame([
            ["Total Assets", None, 1000, 1100, 1200],
            ["Total Liabilities & Equity", None, 1000, 1050, 1200],
        ])
        auditor = _make_auditor(sheets_values={"Balance Sheet": df_vals})
        auditor.verify_balance_sheet_integrity()
        bs_issues = [i for i in auditor.issues if i["type"] == "Accounting Mismatch"]
        assert len(bs_issues) == 1
        assert bs_issues[0]["severity"] == "Critical"

    def test_no_balance_sheet_no_error(self):
        """If no sheet contains 'balance' or 'bs', just skip silently."""
        df_vals = pd.DataFrame([[100, 200]])
        auditor = _make_auditor(sheets_values={"Income": df_vals})
        auditor.verify_balance_sheet_integrity()
        assert len(auditor.issues) == 0

    def test_bs_abbreviation_recognized(self):
        """Sheet named 'BS' should be recognized as balance sheet."""
        df_vals = pd.DataFrame([
            ["Total Assets", None, 500, 600],
            ["Total Liabilities & Equity", None, 500, 600],
        ])
        auditor = _make_auditor(sheets_values={"BS": df_vals})
        auditor.verify_balance_sheet_integrity()
        bs_issues = [i for i in auditor.issues if i["type"] == "Accounting Mismatch"]
        assert len(bs_issues) == 0

    def test_small_rounding_difference_tolerated(self):
        """Variance <= $1 (rounding) should not flag."""
        df_vals = pd.DataFrame([
            ["Total Assets", None, 1000.50, 1100.30],
            ["Total Liabilities & Equity", None, 1000.00, 1100.00],
        ])
        auditor = _make_auditor(sheets_values={"Balance Sheet": df_vals})
        auditor.verify_balance_sheet_integrity()
        bs_issues = [i for i in auditor.issues if i["type"] == "Accounting Mismatch"]
        assert len(bs_issues) == 0


class TestRunAllChecks:
    """run_all_checks() orchestration."""

    def test_run_all_checks_returns_list(self):
        auditor = _make_auditor(
            sheets_values={"Sheet1": pd.DataFrame([[1]])},
            sheets_formulas={"Sheet1": pd.DataFrame([[1]])},
        )
        result = auditor.run_all_checks()
        assert isinstance(result, list)

    def test_clean_model_zero_issues(self):
        """A clean model should produce no issues."""
        df_vals = pd.DataFrame([[100, 200, 300]])
        df_forms = pd.DataFrame([[100, 200, 300]])
        auditor = _make_auditor(
            sheets_values={"Revenue": df_vals},
            sheets_formulas={"Revenue": df_forms},
        )
        issues = auditor.run_all_checks()
        assert len(issues) == 0


class TestIssueStructure:
    """Verify issue dict format from _add_issue()."""

    def test_issue_has_required_keys(self):
        g = nx.DiGraph()
        g.add_edge("EXT_LINK:[X.xlsx]S!A1", "S!B1")
        auditor = _make_auditor(
            sheets_values={"S": pd.DataFrame([[1]])},
            graph=g,
        )
        auditor.check_external_links()
        assert len(auditor.issues) >= 1
        issue = auditor.issues[0]
        required_keys = {"type", "severity", "location", "detail", "why", "cause", "fix"}
        assert required_keys.issubset(set(issue.keys()))

    def test_issue_explanation_populated(self):
        g = nx.DiGraph()
        g.add_edge("EXT_LINK:[X.xlsx]S!A1", "S!B1")
        auditor = _make_auditor(
            sheets_values={"S": pd.DataFrame([[1]])},
            graph=g,
        )
        auditor.check_external_links()
        issue = auditor.issues[0]
        assert issue["why"] != ""
        assert issue["fix"] != ""


class TestSandwichDetection:
    """Secondary plug check: numeric value flanked by formulas."""

    def test_sandwich_detected(self):
        """A number between two formulas should flag as a plug."""
        row_data = ["=A2", 42, "=C2"]
        df_formulas = pd.DataFrame([row_data])
        auditor = _make_auditor(sheets_formulas={"Sheet1": df_formulas})
        auditor.detect_hardcoded_plugs()
        plug_issues = [i for i in auditor.issues if i["type"] == "Hard-coded Plug"]
        assert len(plug_issues) >= 1
        assert "sandwiched" in plug_issues[0]["detail"].lower() or "Plug" in plug_issues[0]["detail"]

    def test_no_sandwich_when_not_flanked(self):
        """A number NOT flanked by formulas on both sides should not fire sandwich."""
        row_data = [42, "=A2", "=B2"]
        df_formulas = pd.DataFrame([row_data])
        auditor = _make_auditor(sheets_formulas={"Sheet1": df_formulas})
        auditor.detect_hardcoded_plugs()
        plug_issues = [i for i in auditor.issues if "sandwiched" in i.get("detail", "").lower()]
        assert len(plug_issues) == 0


class TestEngineNoneHandling:
    """Auditor should handle dependency_engine=None (CSV mode)."""

    def test_engine_none_check_external_links(self):
        """External link check should skip graph scan when engine is None."""
        ingestor = _mock_ingestor(
            sheets_values={"S": pd.DataFrame([[1, 2]])},
        )
        auditor = ModelAuditor(ingestor, None)
        auditor.check_external_links()
        # Should not crash; no external link issues from graph
        ext_issues = [i for i in auditor.issues if i["type"] == "External Link"]
        assert len(ext_issues) == 0

    def test_engine_none_run_all_checks(self):
        """run_all_checks should work with engine=None."""
        ingestor = _mock_ingestor(
            sheets_values={"Revenue": pd.DataFrame([[100, 200]])},
            sheets_formulas={"Revenue": pd.DataFrame([[100, 200]])},
        )
        auditor = ModelAuditor(ingestor, None)
        issues = auditor.run_all_checks()
        assert isinstance(issues, list)


class TestGetExplanation:
    """Test the get_explanation() helper function."""

    def test_known_issue_type(self):
        exp = get_explanation("External Link")
        assert exp["why"] != ""
        assert exp["fix"] != ""

    def test_unknown_issue_type(self):
        exp = get_explanation("NonexistentType")
        assert exp["why"] == ""
        assert exp["fix"] == ""

    def test_calculation_error_specific_subtype(self):
        exp = get_explanation("Calculation Error", error_value="#REF!")
        assert "deleted" in exp["cause"].lower() or "reference" in exp["cause"].lower()

    def test_calculation_error_unknown_subtype(self):
        exp = get_explanation("Calculation Error", error_value="#UNKNOWN!")
        assert exp["cause"] == "Unknown error type."

    def test_all_issue_types_have_explanations(self):
        for issue_type in ISSUE_EXPLANATIONS:
            exp = get_explanation(issue_type)
            assert "why" in exp
            assert "fix" in exp


# ==================================================================
# Tier 2: Unreferenced inputs & dangling outputs
# ==================================================================


class TestUnreferencedInputs:
    """_check_unreferenced_inputs() tests."""

    def test_orphaned_input_flagged(self):
        """A value cell on an 'Assumptions' sheet with no graph dependents should flag."""
        g = nx.DiGraph()
        # Cell A1 has a value but nothing references it in the graph
        df_forms = pd.DataFrame([[100, 200]])
        auditor = _make_auditor(
            sheets_values={"Assumptions": pd.DataFrame([[100, 200]])},
            sheets_formulas={"Assumptions": df_forms},
            graph=g,
        )
        auditor._check_unreferenced_inputs()
        unref = [i for i in auditor.issues if i["type"] == "Unreferenced Input"]
        assert len(unref) >= 1
        assert unref[0]["severity"] == "Medium"

    def test_referenced_input_not_flagged(self):
        """A value cell that IS referenced in the graph should not flag."""
        g = nx.DiGraph()
        # Assumptions!A1 has an outgoing edge (something depends on it)
        g.add_edge("Assumptions!A1", "DCF!B5")
        df_forms = pd.DataFrame([[100]])
        auditor = _make_auditor(
            sheets_values={"Assumptions": pd.DataFrame([[100]])},
            sheets_formulas={"Assumptions": df_forms},
            graph=g,
        )
        auditor._check_unreferenced_inputs()
        unref = [i for i in auditor.issues if i["type"] == "Unreferenced Input"]
        assert len(unref) == 0

    def test_formula_cells_skipped(self):
        """Formula cells on input sheets should not be flagged as unreferenced."""
        g = nx.DiGraph()
        df_forms = pd.DataFrame([["=SUM(B1:B5)"]])
        auditor = _make_auditor(
            sheets_values={"Inputs": pd.DataFrame([[500]])},
            sheets_formulas={"Inputs": df_forms},
            graph=g,
        )
        auditor._check_unreferenced_inputs()
        unref = [i for i in auditor.issues if i["type"] == "Unreferenced Input"]
        assert len(unref) == 0

    def test_non_input_sheets_skipped(self):
        """Sheets not named Assumptions/Inputs/Drivers should be skipped entirely."""
        g = nx.DiGraph()
        df_forms = pd.DataFrame([[100]])
        auditor = _make_auditor(
            sheets_values={"Revenue": pd.DataFrame([[100]])},
            sheets_formulas={"Revenue": df_forms},
            graph=g,
        )
        auditor._check_unreferenced_inputs()
        unref = [i for i in auditor.issues if i["type"] == "Unreferenced Input"]
        assert len(unref) == 0

    def test_engine_none_returns_empty(self):
        """With engine=None, should return empty without crashing."""
        ingestor = _mock_ingestor(
            sheets_values={"Assumptions": pd.DataFrame([[100]])},
            sheets_formulas={"Assumptions": pd.DataFrame([[100]])},
        )
        auditor = ModelAuditor(ingestor, None)
        result = auditor._check_unreferenced_inputs()
        assert result == []


class TestDanglingOutputs:
    """_check_dangling_outputs() tests."""

    def test_hardcoded_output_flagged(self):
        """An output-labeled row with a hard-coded value should flag."""
        df_vals = pd.DataFrame([
            ["IRR", None, 0.15, 0.18],
        ])
        df_forms = pd.DataFrame([
            ["IRR", None, 0.15, 0.18],  # Hard-coded, not formulas
        ])
        g = nx.DiGraph()
        auditor = _make_auditor(
            sheets_values={"Summary": df_vals},
            sheets_formulas={"Summary": df_forms},
            graph=g,
        )
        auditor._check_dangling_outputs()
        dangling = [i for i in auditor.issues if i["type"] == "Dangling Output"]
        assert len(dangling) >= 1
        assert dangling[0]["severity"] == "Medium"

    def test_formula_output_not_flagged(self):
        """An output-labeled row with formulas should not flag."""
        df_vals = pd.DataFrame([
            ["NPV", None, 1000000],
        ])
        df_forms = pd.DataFrame([
            ["NPV", None, "=SUM(B2:B10)"],
        ])
        g = nx.DiGraph()
        auditor = _make_auditor(
            sheets_values={"Output": df_vals},
            sheets_formulas={"Output": df_forms},
            graph=g,
        )
        auditor._check_dangling_outputs()
        dangling = [i for i in auditor.issues if i["type"] == "Dangling Output"]
        assert len(dangling) == 0

    def test_non_output_label_skipped(self):
        """Rows without output-keyword labels should not be checked."""
        df_vals = pd.DataFrame([
            ["Revenue", None, 50000],
        ])
        df_forms = pd.DataFrame([
            ["Revenue", None, 50000],  # Hard-coded but not output label
        ])
        g = nx.DiGraph()
        auditor = _make_auditor(
            sheets_values={"Sheet1": df_vals},
            sheets_formulas={"Sheet1": df_forms},
            graph=g,
        )
        auditor._check_dangling_outputs()
        dangling = [i for i in auditor.issues if i["type"] == "Dangling Output"]
        assert len(dangling) == 0

    def test_engine_none_returns_empty(self):
        """With engine=None, should return empty without crashing."""
        ingestor = _mock_ingestor(
            sheets_values={"Summary": pd.DataFrame([["IRR", None, 0.15]])},
            sheets_formulas={"Summary": pd.DataFrame([["IRR", None, 0.15]])},
        )
        auditor = ModelAuditor(ingestor, None)
        result = auditor._check_dangling_outputs()
        assert result == []


# ==================================================================
# BS tolerance constant (Task 4)
# ==================================================================


class TestBSToleranceConstant:
    """Verify the _BS_TOLERANCE_BPS constant is importable and correct."""

    def test_bs_tolerance_constant_exists(self):
        """_BS_TOLERANCE_BPS should be importable from src.auditor."""
        from src.auditor import _BS_TOLERANCE_BPS  # noqa: F811
        assert _BS_TOLERANCE_BPS is not None

    def test_bs_tolerance_value(self):
        """_BS_TOLERANCE_BPS should equal 0.0001 (1 basis point)."""
        from src.auditor import _BS_TOLERANCE_BPS  # noqa: F811
        assert _BS_TOLERANCE_BPS == 0.0001

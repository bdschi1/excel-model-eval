"""
Tests for src/dependency.py -- DependencyEngine

Verifies:
1. Basic formula parsing creates correct edges
2. Cross-sheet reference handling
3. External link detection
4. Circular reference detection
5. Graph structure and analyze_structure() output
6. Empty formula sheets
7. Non-formula cells ignored
"""

from __future__ import annotations

import pathlib
import sys

import networkx as nx
import pandas as pd

# Ensure repo root is on path
REPO_ROOT = pathlib.Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dependency import DependencyEngine

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_engine(sheets_formulas: dict) -> DependencyEngine:
    """Build a DependencyEngine from a dict of {sheet_name: [[row], ...]}."""
    dfs = {}
    for name, rows in sheets_formulas.items():
        dfs[name] = pd.DataFrame(rows)
    engine = DependencyEngine(dfs)
    engine.build_graph()
    return engine


# ==================================================================
# Tests
# ==================================================================


class TestBasicFormulaParsing:
    """Simple same-sheet formula parsing."""

    def test_simple_addition_creates_edges(self):
        engine = _make_engine({
            "Sheet1": [[10, 20, "=A1+B1"]],
        })
        # =A1+B1 in C1 should create edges: Sheet1!A1 -> Sheet1!C1, Sheet1!B1 -> Sheet1!C1
        assert engine.graph.has_edge("Sheet1!A1", "Sheet1!C1")
        assert engine.graph.has_edge("Sheet1!B1", "Sheet1!C1")

    def test_sum_function_creates_expanded_edges(self):
        """SUM(A1:A3) expands the range into individual cell edges."""
        engine = _make_engine({
            "Sheet1": [[10], [20], [30], ["=SUM(A1:A3)"]],
        })
        # Range is expanded: A1, A2, A3 each get an edge to A4
        assert engine.graph.has_edge("Sheet1!A1", "Sheet1!A4")
        assert engine.graph.has_edge("Sheet1!A2", "Sheet1!A4")
        assert engine.graph.has_edge("Sheet1!A3", "Sheet1!A4")

    def test_non_formula_cells_ignored(self):
        """Cells with plain values or text should not create nodes."""
        engine = _make_engine({
            "Sheet1": [[100, "hello", None], [42, "", 3.14]],
        })
        assert engine.node_count == 0
        assert engine.graph.number_of_edges() == 0

    def test_node_count_tracks_formula_cells(self):
        engine = _make_engine({
            "Sheet1": [[10, "=A1*2"], [20, "=A2*2"]],
        })
        assert engine.node_count == 2

    def test_multiplication_formula(self):
        engine = _make_engine({
            "Sheet1": [["=A2*B2", 5, 10]],
        })
        assert engine.graph.has_edge("Sheet1!A2", "Sheet1!A1")
        assert engine.graph.has_edge("Sheet1!B2", "Sheet1!A1")


class TestCrossSheetReferences:
    """Cross-sheet formula references."""

    def test_cross_sheet_reference(self):
        engine = _make_engine({
            "Summary": [["=PFNA!A1 + 100"]],
            "PFNA": [[100]],
        })
        # Should create edge from PFNA!A1 to Summary!A1
        assert engine.graph.has_edge("PFNA!A1", "Summary!A1")

    def test_cross_sheet_with_quoted_name(self):
        """Sheet names with spaces are quoted in formulas: ='Sheet Two'!A1"""
        engine = _make_engine({
            "Summary": [["='Sheet Two'!A1"]],
            "Sheet Two": [[500]],
        })
        # After quote stripping, the edge should be: Sheet Two!A1 -> Summary!A1
        assert engine.graph.has_edge("Sheet Two!A1", "Summary!A1")


class TestExternalLinks:
    """External link (workbook reference) detection."""

    def test_external_link_tagged(self):
        engine = _make_engine({
            "Sheet1": [["=[OtherBook.xlsx]Sheet1!A1"]],
        })
        # External links are tagged with "EXT_LINK:" prefix
        ext_nodes = [n for n in engine.graph.nodes if "EXT_LINK" in n]
        assert len(ext_nodes) >= 1

    def test_external_link_edge_direction(self):
        engine = _make_engine({
            "Sheet1": [["=[Data.xlsx]Prices!B5"]],
        })
        ext_nodes = [n for n in engine.graph.nodes if "EXT_LINK" in n]
        assert len(ext_nodes) == 1
        # External node should have an edge pointing TO Sheet1!A1
        assert engine.graph.has_edge(ext_nodes[0], "Sheet1!A1")


class TestCircularReferences:
    """Circular reference detection via analyze_structure()."""

    def test_direct_circular_reference(self):
        """A1 refs B1, B1 refs A1."""
        engine = _make_engine({
            "Sheet1": [["=B1", "=A1"]],
        })
        result = engine.analyze_structure()
        assert result["circular_references"] > 0

    def test_no_circular_reference(self):
        engine = _make_engine({
            "Sheet1": [[10, "=A1+1"]],
        })
        result = engine.analyze_structure()
        assert result["circular_references"] == 0

    def test_indirect_circular_reference(self):
        """A1 refs B1, B1 refs C1, C1 refs A1."""
        engine = _make_engine({
            "Sheet1": [["=C1", "=A1", "=B1"]],
        })
        result = engine.analyze_structure()
        assert result["circular_references"] > 0


class TestAnalyzeStructure:
    """analyze_structure() output format."""

    def test_structure_keys(self):
        engine = _make_engine({
            "Sheet1": [[10, "=A1"]],
        })
        result = engine.analyze_structure()
        assert "circular_references" in result
        assert "orphaned_calculations" in result
        assert "complexity_score" in result

    def test_complexity_score_nonnegative(self):
        engine = _make_engine({
            "Sheet1": [[10, "=A1*2", "=B1+1"]],
        })
        result = engine.analyze_structure()
        assert result["complexity_score"] >= 0

    def test_orphaned_calculations(self):
        """A node with in-degree > 0 and out-degree == 0 is orphaned."""
        # B1 depends on A1, but nothing depends on B1
        engine = _make_engine({
            "Sheet1": [[10, "=A1"]],
        })
        result = engine.analyze_structure()
        # Sheet1!B1 has in_degree=1 (A1) and out_degree=0 -> orphaned
        assert "Sheet1!B1" in result["orphaned_calculations"]


class TestEmptySheets:
    """Edge cases with empty or minimal data."""

    def test_empty_formula_sheet(self):
        engine = _make_engine({
            "Sheet1": [[None, None], [None, None]],
        })
        assert engine.node_count == 0
        result = engine.analyze_structure()
        assert result["circular_references"] == 0

    def test_all_values_no_formulas(self):
        engine = _make_engine({
            "Data": [[1, 2, 3], [4, 5, 6]],
        })
        assert engine.node_count == 0
        assert engine.graph.number_of_edges() == 0


class TestRangeExpansion:
    """_expand_range() and range expansion in edge creation."""

    def test_single_cell_not_expanded(self):
        cells = DependencyEngine._expand_range("A1")
        assert cells == ["A1"]

    def test_simple_range_expanded(self):
        cells = DependencyEngine._expand_range("A1:A3")
        assert cells == ["A1", "A2", "A3"]

    def test_multi_column_range(self):
        cells = DependencyEngine._expand_range("A1:B2")
        assert set(cells) == {"A1", "B1", "A2", "B2"}

    def test_dollar_signs_stripped(self):
        cells = DependencyEngine._expand_range("$A$1:$B$2")
        assert set(cells) == {"A1", "B1", "A2", "B2"}

    def test_formula_with_range_creates_individual_edges(self):
        engine = _make_engine({
            "S": [[10, 20], [30, "=SUM(A1:B1)"]],
        })
        # A1 and B1 should each have an edge to B2
        assert engine.graph.has_edge("S!A1", "S!B2")
        assert engine.graph.has_edge("S!B1", "S!B2")


class TestArrayFormulas:
    """Array formula handling ({=...} syntax)."""

    def test_array_formula_parsed(self):
        engine = _make_engine({
            "S": [[10, 20, "{=A1+B1}"]],
        })
        assert engine.node_count == 1
        assert engine.graph.has_edge("S!A1", "S!C1")
        assert engine.graph.has_edge("S!B1", "S!C1")


class TestAnalyzeStructureExtended:
    """Extended analyze_structure() fields."""

    def test_circular_reference_cells_included(self):
        engine = _make_engine({
            "S": [["=B1", "=A1"]],
        })
        result = engine.analyze_structure()
        assert "circular_reference_cells" in result
        assert len(result["circular_reference_cells"]) > 0


class TestGraphProperties:
    """Graph structure properties."""

    def test_graph_is_directed(self):
        engine = _make_engine({"S": [[10, "=A1"]]})
        assert isinstance(engine.graph, nx.DiGraph)

    def test_edge_count(self):
        engine = _make_engine({
            "S": [[10, 20, "=A1+B1"]],
        })
        # =A1+B1 creates 2 edges
        assert engine.graph.number_of_edges() == 2

    def test_multiple_formulas_in_different_sheets(self):
        engine = _make_engine({
            "A": [[10, "=A1*2"]],
            "B": [[20, "=A1+5"]],
        })
        assert engine.node_count == 2
        assert engine.graph.has_edge("A!A1", "A!B1")
        assert engine.graph.has_edge("B!A1", "B!B1")


class TestNamedRangeEdgeCases:
    """Named range resolution edge cases (Gap 11)."""

    def test_xlnm_name_skipped(self):
        """_xlnm.Print_Area should not create edges or crash."""
        dfs = {"Sheet1": pd.DataFrame([["=_xlnm.Print_Area"]])}
        engine = DependencyEngine(dfs)
        engine.build_graph()
        # No edges should be created for the built-in name
        assert engine.graph.number_of_edges() == 0

    def test_named_range_with_digits_resolves(self):
        """Rate2024 contains digits but should resolve as a named range, not a cell ref."""
        dfs = {"Sheet1": pd.DataFrame([["=Rate2024"]])}
        engine = DependencyEngine(dfs)
        # Manually set defined names (bypassing openpyxl DefinedNameList)
        engine._defined_names = {"rate2024": "Sheet1!A1"}
        engine.build_graph()
        # Rate2024 should resolve to Sheet1!A1 and create an edge to Sheet1!A1 (target)
        assert engine.graph.has_edge("Sheet1!A1", "Sheet1!A1")

    def test_cell_ref_q1_not_treated_as_named_range(self):
        """Q1 is a valid cell ref (col Q, row 1) and should NOT resolve as a named range."""
        dfs = {"Sheet1": pd.DataFrame([[None, "=Q1"]])}
        engine = DependencyEngine(dfs)
        # Even if Q1 exists in defined_names, the cell ref pattern should take priority
        engine._defined_names = {"q1": "Sheet1!Z99"}
        engine.build_graph()
        # Should create edge from Sheet1!Q1, NOT from the named range target Sheet1!Z99
        assert engine.graph.has_edge("Sheet1!Q1", "Sheet1!B1")
        assert not engine.graph.has_edge("Sheet1!Z99", "Sheet1!B1")


# ==================================================================
# Unresolved named range counter (Task 3)
# ==================================================================


class TestUnresolvedNamedRangeCounter:
    """_unresolved_named_ranges counter on DependencyEngine."""

    def test_unresolved_counter_starts_at_zero(self):
        """A freshly created engine should have zero unresolved named ranges."""
        dfs = {"Sheet1": pd.DataFrame([[10]])}
        engine = DependencyEngine(dfs)
        assert engine._unresolved_named_ranges == 0

    def test_unresolved_counter_increments_on_bad_name(self):
        """Defined names that fail to resolve should increment the counter."""
        from unittest.mock import MagicMock

        dfs = {"Sheet1": pd.DataFrame([[10]])}
        engine = DependencyEngine(dfs)

        # Build a mock DefinedNameList with a name that raises on .destinations
        bad_dn = MagicMock()
        bad_dn.is_external = False
        bad_dn.is_reserved = False
        bad_dn.name = "BrokenName"
        # .destinations raises ValueError (simulates formula-based name)
        type(bad_dn).destinations = property(
            lambda self: (_ for _ in ()).throw(ValueError("no destination"))
        )

        dn_list = MagicMock()
        dn_list.definedName = [bad_dn]

        engine.set_defined_names(dn_list)
        assert engine._unresolved_named_ranges > 0

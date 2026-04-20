"""
Shared pytest fixtures for the ModelLens test suite.

Centralizes common mock factories used across test modules.
Existing helper functions in individual test files are retained for
backward compatibility; these fixtures provide the shared versions.
"""

from __future__ import annotations

import os
import pathlib
import sys
from unittest.mock import MagicMock

import networkx as nx
import pandas as pd
import pytest

# Ensure repo root is on path
REPO_ROOT = pathlib.Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.dependency import DependencyEngine
from src.reporting import ReportGenerator

# ------------------------------------------------------------------
# Mock ingestor
# ------------------------------------------------------------------

@pytest.fixture
def mock_ingestor():
    """Returns a factory that creates a mock ingestor with configurable sheets.

    Usage:
        ing = mock_ingestor(sheet_count=5)
        ing = mock_ingestor(sheets_values={...}, sheets_formulas={...})
    """
    def _factory(
        sheet_count=5,
        sheets_values=None,
        sheets_formulas=None,
        load_errors=None,
        hidden_sheets=None,
    ):
        ingestor = MagicMock()
        if sheets_values is not None:
            ingestor.sheets_values = sheets_values
        else:
            ingestor.sheets_values = {
                f"Sheet{i}": pd.DataFrame([[1]]) for i in range(sheet_count)
            }
        ingestor.sheets_formulas = sheets_formulas or {}
        ingestor.load_errors = load_errors or []
        ingestor.hidden_sheets = hidden_sheets or set()
        return ingestor

    return _factory


# ------------------------------------------------------------------
# Dependency engine builder
# ------------------------------------------------------------------

@pytest.fixture
def make_engine():
    """Returns a factory that creates a DependencyEngine from a formula dict
    and builds the graph.

    Usage:
        engine = make_engine({"Sheet1": [[10, "=A1+1"]]})
    """
    def _factory(sheets_formulas: dict) -> DependencyEngine:
        dfs = {}
        for name, rows in sheets_formulas.items():
            dfs[name] = pd.DataFrame(rows)
        engine = DependencyEngine(dfs)
        engine.build_graph()
        return engine

    return _factory


# ------------------------------------------------------------------
# Report generator builder
# ------------------------------------------------------------------

def _sample_issues(count=3, severities=None):
    """Generate N sample issues."""
    if severities is None:
        severities = ["Critical", "High", "Medium"]
    issues = []
    for i in range(count):
        sev = severities[i % len(severities)]
        issues.append({
            "type": "Hard-coded Plug",
            "severity": sev,
            "location": f"Sheet1!Row{i+1}",
            "detail": f"Test issue {i+1}",
            "why": "Test explanation",
            "cause": "Test cause",
            "fix": "Test fix",
        })
    return issues


@pytest.fixture
def make_report_generator(mock_ingestor):
    """Returns a factory that creates a ReportGenerator with mocked inputs.

    Usage:
        rg = make_report_generator(tmp_path=tmp_path)
        rg = make_report_generator(filename="model.xlsx", issues=[...], tmp_path=tmp_path)
    """
    def _factory(
        filename="test_model.xlsx",
        issues=None,
        sheet_count=5,
        node_count=100,
        edge_count=150,
        tmp_path=None,
    ):
        if issues is None:
            issues = _sample_issues()
        ingestor = mock_ingestor(sheet_count=sheet_count)

        # Build mock dep engine with nx graph
        dep_engine = MagicMock()
        g = nx.DiGraph()
        for i in range(node_count):
            g.add_node(f"Node{i}")
        added = 0
        for i in range(node_count):
            for j in range(i + 1, node_count):
                if added >= edge_count:
                    break
                g.add_edge(f"Node{i}", f"Node{j}")
                added += 1
            if added >= edge_count:
                break
        dep_engine.graph = g

        rg = ReportGenerator(filename, issues, ingestor, dep_engine)

        if tmp_path:
            rg.results_dir = os.path.join(str(tmp_path), "RESULTS")
            os.makedirs(rg.results_dir, exist_ok=True)

        return rg

    return _factory

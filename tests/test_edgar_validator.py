"""Tests for src/edgar_validator.py and ModelAuditor.check_edgar().

No live network calls — SEC responses are mocked via a fake requests session.
"""

from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock, patch

import networkx as nx
import pandas as pd
import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.auditor import ModelAuditor  # noqa: E402
from src.edgar_validator import (  # noqa: E402
    EDGARClient,
    EDGARValidator,
    HistoricalCell,
    _extract_annual_value,
    _normalize_label,
    _severity_for_delta,
    match_concepts,
)

# ----------------------------------------------------------------------
# Fakes
# ----------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeSession:
    """Record calls; serve pre-registered responses keyed by URL substring."""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []
        self.exception = None

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        if self.exception is not None:
            raise self.exception
        for key, resp in self.responses.items():
            if key in url:
                return resp
        return _FakeResponse(404, {})


_TICKERS_PAYLOAD = {
    "0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
    "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
}


def _facts_for_nvda():
    """Synthetic company_facts payload: Revenues FY2023 = 60_922_000_000."""
    return {
        "cik": 1045810,
        "entityName": "NVIDIA CORP",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"fy": 2023, "fp": "FY", "val": 60_922_000_000, "form": "10-K"},
                            {"fy": 2022, "fp": "FY", "val": 26_974_000_000, "form": "10-K"},
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {"fy": 2023, "fp": "FY", "val": 4_368_000_000, "form": "10-K"},
                        ]
                    }
                },
                "Assets": {
                    "units": {
                        "USD": [
                            {"fy": 2023, "fp": "FY", "val": 65_728_000_000, "form": "10-K"},
                        ]
                    }
                },
            }
        },
    }


# ----------------------------------------------------------------------
# EDGARClient
# ----------------------------------------------------------------------

class TestResolveCik:
    def test_happy_path_zero_pads(self, tmp_path):
        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
        })
        client = EDGARClient(cache_dir=tmp_path, session=session)
        assert client.resolve_cik("NVDA") == "0000001045810"[-10:]
        # The API returns int 1045810; zero-padded to 10 digits -> "0001045810"
        assert client.resolve_cik("NVDA") == "0001045810"

    def test_unknown_ticker_returns_none(self, tmp_path):
        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
        })
        client = EDGARClient(cache_dir=tmp_path, session=session)
        assert client.resolve_cik("NOPE") is None

    def test_case_insensitive(self, tmp_path):
        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
        })
        client = EDGARClient(cache_dir=tmp_path, session=session)
        assert client.resolve_cik("nvda") == "0001045810"


class TestCompanyFactsCaching:
    def test_second_call_hits_cache_not_network(self, tmp_path):
        session = _FakeSession({
            "companyfacts/CIK0001045810": _FakeResponse(200, _facts_for_nvda()),
        })
        client = EDGARClient(cache_dir=tmp_path, session=session)
        first = client.company_facts("0001045810")
        second = client.company_facts("0001045810")
        assert first == second
        # Only one network call made
        assert len(session.calls) == 1


# ----------------------------------------------------------------------
# match_concepts + _extract_annual_value
# ----------------------------------------------------------------------

class TestConceptMatching:
    @pytest.mark.parametrize("label,expected_first", [
        ("Revenue", "Revenues"),
        ("Revenues", "Revenues"),
        ("Net Sales", "Revenues"),
        ("Gross Profit", "GrossProfit"),
        ("Operating Income", "OperatingIncomeLoss"),
        ("Income from Operations", "OperatingIncomeLoss"),
        ("Net Income", "NetIncomeLoss"),
        ("Net Income (Loss)", "NetIncomeLoss"),
        ("Total Assets", "Assets"),
        ("Total Liabilities", "Liabilities"),
    ])
    def test_matches_core6(self, label, expected_first):
        concepts = match_concepts(label)
        assert concepts, f"expected a match for {label!r}"
        assert concepts[0] == expected_first

    def test_no_match_returns_empty(self):
        assert match_concepts("Some Random Label") == []
        assert match_concepts("") == []

    @pytest.mark.parametrize("label,expected_first", [
        ("Total Sales/Revenues", "Revenues"),
        ("Sales, net revenue", "Revenues"),
        ("Net Sales / Revenues", "Revenues"),
        ("Net Income (Loss)", "NetIncomeLoss"),
        ("Net Income pre Pref Dividends", "NetIncomeLoss"),
        ("Operating Profit", "OperatingIncomeLoss"),
        ("EBIT (Operating Profit)", "OperatingIncomeLoss"),
        ("EBIT", "OperatingIncomeLoss"),
        ("Net income to common", "NetIncomeLossAvailableToCommonStockholdersBasic"),
        ("Net Income Attributable to Common Shareholders",
         "NetIncomeLossAvailableToCommonStockholdersBasic"),
    ])
    def test_normalization_and_compound_variants(self, label, expected_first):
        concepts = match_concepts(label)
        assert concepts and concepts[0] == expected_first

    @pytest.mark.parametrize("raw,expected", [
        ("EBIT (Operating Profit)", "EBIT"),
        ("Total Sales/Revenues", "Total Sales Revenues"),
        ("Sales, net revenue", "Sales net revenue"),
        ("  Net Income   (Loss) ", "Net Income"),
        ("Long-term debt", "Long-term debt"),
    ])
    def test_normalize_label(self, raw, expected):
        assert _normalize_label(raw) == expected

    def test_extract_annual_value_hit(self):
        val = _extract_annual_value(_facts_for_nvda(), "Revenues", 2023)
        assert val == 60_922_000_000.0

    def test_extract_annual_value_miss(self):
        assert _extract_annual_value(_facts_for_nvda(), "Revenues", 1999) is None
        assert _extract_annual_value(_facts_for_nvda(), "GrossProfit", 2023) is None


# ----------------------------------------------------------------------
# Severity scoring
# ----------------------------------------------------------------------

class TestSeverity:
    @pytest.mark.parametrize("model,edgar,expected", [
        (106.0, 100.0, "Critical"),   # 6% delta
        (102.0, 100.0, "High"),       # 2% delta
        (100.5, 100.0, "Medium"),     # 0.5% delta
        (100.05, 100.0, None),        # 0.05% delta -> Pass
        (100.0, 100.0, None),         # exact match -> Pass
    ])
    def test_tiers(self, model, edgar, expected):
        assert _severity_for_delta(model, edgar) == expected


# ----------------------------------------------------------------------
# End-to-end validator
# ----------------------------------------------------------------------

class TestValidateFlagsTieredSeverity:
    def test_three_deltas_produce_three_severities(self, tmp_path):
        # Synthesize facts where Revenues FY2023 = $100M; model cells at 6%/2%/0.5% over
        facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"fy": 2023, "fp": "FY", "val": 100_000_000.0},
                                {"fy": 2022, "fp": "FY", "val": 100_000_000.0},
                                {"fy": 2021, "fp": "FY", "val": 100_000_000.0},
                                {"fy": 2020, "fp": "FY", "val": 100_000_000.0},
                            ]
                        }
                    }
                }
            }
        }

        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
            "companyfacts/CIK0001045810": _FakeResponse(200, facts),
        })
        client = EDGARClient(cache_dir=tmp_path, session=session)
        validator = EDGARValidator(client=client)

        samples = [
            HistoricalCell(sheet="IS", row_label="Revenue", col_letter="B",
                           row_idx=1, col_idx=1, year=2023,
                           value=106_000_000.0,  # +6% -> Critical
                           concepts=["Revenues"]),
            HistoricalCell(sheet="IS", row_label="Revenue", col_letter="C",
                           row_idx=1, col_idx=2, year=2022,
                           value=102_000_000.0,  # +2% -> High
                           concepts=["Revenues"]),
            HistoricalCell(sheet="IS", row_label="Revenue", col_letter="D",
                           row_idx=1, col_idx=3, year=2021,
                           value=100_500_000.0,  # +0.5% -> Medium
                           concepts=["Revenues"]),
            HistoricalCell(sheet="IS", row_label="Revenue", col_letter="E",
                           row_idx=1, col_idx=4, year=2020,
                           value=100_050_000.0,  # +0.05% -> Pass (no issue)
                           concepts=["Revenues"]),
        ]
        issues = validator.validate("NVDA", samples)
        severities = [i["severity"] for i in issues if i["type"] == "EDGAR Mismatch"]
        assert severities == ["Critical", "High", "Medium"]


class TestSkipNotes:
    def test_skip_on_network_failure(self, tmp_path):
        import requests as _requests
        session = _FakeSession({})
        session.exception = _requests.exceptions.Timeout("boom")
        client = EDGARClient(cache_dir=tmp_path, session=session)
        validator = EDGARValidator(client=client)

        samples = [HistoricalCell(sheet="IS", row_label="Revenue", col_letter="B",
                                  row_idx=1, col_idx=1, year=2023, value=100.0,
                                  concepts=["Revenues"])]
        issues = validator.validate("NVDA", samples)
        assert len(issues) == 1
        assert issues[0]["type"] == "EDGAR Check Skipped"
        assert issues[0]["severity"] == "Medium"

    def test_no_ticker_no_issues(self):
        validator = EDGARValidator(client=EDGARClient())
        # Even with samples, None ticker short-circuits to zero issues.
        samples = [HistoricalCell(sheet="IS", row_label="Revenue", col_letter="B",
                                  row_idx=1, col_idx=1, year=2023, value=100.0,
                                  concepts=["Revenues"])]
        assert validator.validate(None, samples) == []
        assert validator.validate("", samples) == []
        assert validator.validate("   ", samples) == []

    def test_skip_when_no_samples(self, tmp_path):
        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
            "companyfacts/CIK0001045810": _FakeResponse(200, _facts_for_nvda()),
        })
        client = EDGARClient(cache_dir=tmp_path, session=session)
        validator = EDGARValidator(client=client)
        issues = validator.validate("NVDA", samples=[])
        assert len(issues) == 1
        assert issues[0]["type"] == "EDGAR Check Skipped"


class TestConceptNotInFacts:
    def test_concept_missing_silently_skipped(self, tmp_path):
        """A concept not in the filer's facts should not fabricate a mismatch."""
        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
            "companyfacts/CIK0001045810": _FakeResponse(200, _facts_for_nvda()),
        })
        client = EDGARClient(cache_dir=tmp_path, session=session)
        validator = EDGARValidator(client=client)

        samples = [HistoricalCell(sheet="IS", row_label="Gross Profit", col_letter="B",
                                  row_idx=1, col_idx=1, year=2023, value=20_000_000_000.0,
                                  concepts=["GrossProfit"])]  # not in fake facts
        issues = validator.validate("NVDA", samples)
        # No mismatch issues (concept silently skipped), no skip note either
        # because the pipeline succeeded — concept just wasn't filed.
        mismatches = [i for i in issues if i["type"] == "EDGAR Mismatch"]
        assert mismatches == []


# ----------------------------------------------------------------------
# ModelAuditor integration: period classification + end-to-end hook
# ----------------------------------------------------------------------

class TestPeriodClassification:
    def _auditor(self, sheets_values=None):
        ingestor = MagicMock()
        ingestor.sheets_values = sheets_values or {}
        ingestor.sheets_formulas = {}
        engine = MagicMock()
        engine.graph = nx.DiGraph()
        return ModelAuditor(ingestor, engine, ticker=None)

    def test_classify_historical_and_forecast(self):
        # Header row then one data row (unused here)
        df = pd.DataFrame([
            ["Line Item", "FY2022A", "FY2023A", "FY2024E", "2020"],
            ["Revenue",    100,       110,       120,        80],
        ])
        auditor = self._auditor({"IS": df})
        result = auditor._classify_period_columns(df)
        # col 0 is label; cols 1-4 are periods
        assert result[1] == ("historical", 2022)
        assert result[2] == ("historical", 2023)
        assert result[3] == ("forecast", 2024)
        assert result[4] == ("historical", 2020)  # bare year < current -> historical

    def test_ambiguous_headers_ignored(self):
        df = pd.DataFrame([
            ["Line Item", "LTM", "TTM", "Forecast"],
            ["Revenue",    100,    110,   120],
        ])
        auditor = self._auditor({"IS": df})
        assert auditor._classify_period_columns(df) == {}


class TestAuditorEdgarHook:
    def test_no_ticker_means_no_edgar_issues(self):
        df = pd.DataFrame([
            ["Line Item", "FY2023A"],
            ["Revenue",   60_000_000_000],
        ])
        ingestor = MagicMock()
        ingestor.sheets_values = {"IS": df}
        ingestor.sheets_formulas = {}
        engine = MagicMock()
        engine.graph = nx.DiGraph()
        auditor = ModelAuditor(ingestor, engine, ticker=None)

        # Patch the validator so we can assert it's never called.
        with patch("src.edgar_validator.EDGARValidator") as Mock:
            auditor.check_edgar(None)
            Mock.assert_not_called()
        assert [i for i in auditor.issues if i["type"].startswith("EDGAR")] == []

    def test_with_ticker_runs_validator(self, tmp_path):
        df = pd.DataFrame([
            ["Line Item", "FY2023A", "FY2022A"],
            ["Revenue",   60_922_000_000, 26_974_000_000],
            ["Net Income", 4_368_000_000, 9_000_000_000],  # FY22 NI missing in fake facts -> skipped
        ])
        ingestor = MagicMock()
        ingestor.sheets_values = {"IS": df}
        ingestor.sheets_formulas = {}
        ingestor.hidden_sheets = set()
        engine = MagicMock()
        engine.graph = nx.DiGraph()
        auditor = ModelAuditor(ingestor, engine, ticker="NVDA")

        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
            "companyfacts/CIK0001045810": _FakeResponse(200, _facts_for_nvda()),
        })
        client = EDGARClient(cache_dir=tmp_path, session=session)
        validator = EDGARValidator(client=client)

        auditor.check_edgar("NVDA", validator=validator)
        edgar_issues = [i for i in auditor.issues if i["type"].startswith("EDGAR")]
        # Revenue FY23 ties exactly; NetIncome FY23 ties exactly; Revenue FY22 ties exactly.
        # NetIncome FY22 missing in facts -> silently skipped (no issue).
        mismatches = [i for i in edgar_issues if i["type"] == "EDGAR Mismatch"]
        assert mismatches == []

    def test_ticker_but_no_historical_columns_emits_skip(self, tmp_path):
        df = pd.DataFrame([
            ["Line Item", "LTM", "TTM"],
            ["Revenue",   100, 110],
        ])
        ingestor = MagicMock()
        ingestor.sheets_values = {"IS": df}
        ingestor.sheets_formulas = {}
        ingestor.hidden_sheets = set()
        engine = MagicMock()
        engine.graph = nx.DiGraph()
        auditor = ModelAuditor(ingestor, engine, ticker="NVDA")

        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
            "companyfacts/CIK0001045810": _FakeResponse(200, _facts_for_nvda()),
        })
        validator = EDGARValidator(client=EDGARClient(cache_dir=tmp_path, session=session))

        auditor.check_edgar("NVDA", validator=validator)
        skips = [i for i in auditor.issues if i["type"] == "EDGAR Check Skipped"]
        assert len(skips) == 1


# ----------------------------------------------------------------------
# Phase B: Extended 15 concepts, unit buckets, EPS tolerance, derived FCF
# ----------------------------------------------------------------------

def _facts_with_eps_and_shares():
    return {
        "facts": {
            "us-gaap": {
                "EarningsPerShareDiluted": {
                    "units": {
                        "USD/shares": [
                            {"fy": 2023, "fp": "FY", "val": 2.50, "form": "10-K"},
                        ]
                    }
                },
                "WeightedAverageNumberOfDilutedSharesOutstanding": {
                    "units": {
                        "shares": [
                            {"fy": 2023, "fp": "FY", "val": 2_500_000_000, "form": "10-K"},
                        ]
                    }
                },
            }
        }
    }


def _facts_with_cfo_and_capex(capex: float | None = -8_000_000_000.0):
    us_gaap: dict = {
        "NetCashProvidedByUsedInOperatingActivities": {
            "units": {
                "USD": [
                    {"fy": 2023, "fp": "FY", "val": 28_000_000_000, "form": "10-K"},
                ]
            }
        },
    }
    if capex is not None:
        us_gaap["PaymentsToAcquirePropertyPlantAndEquipment"] = {
            "units": {
                "USD": [
                    {"fy": 2023, "fp": "FY", "val": capex, "form": "10-K"},
                ]
            }
        }
    return {"facts": {"us-gaap": us_gaap}}


class TestExtendedConceptsAndBuckets:
    def test_eps_matches_and_uses_usd_shares_bucket(self, tmp_path):
        # Label "Diluted EPS" -> EarningsPerShareDiluted; value read from
        # USD/shares; 0.5% delta falls inside the wider EPS Medium band (1%).
        concepts = match_concepts("Diluted EPS")
        assert concepts and concepts[0] == "EarningsPerShareDiluted"

        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
            "companyfacts/CIK0001045810": _FakeResponse(200, _facts_with_eps_and_shares()),
        })
        client = EDGARClient(cache_dir=tmp_path, session=session)
        validator = EDGARValidator(client=client)

        samples = [HistoricalCell(
            sheet="IS", row_label="Diluted EPS", col_letter="B",
            row_idx=10, col_idx=1, year=2023,
            value=2.5125,  # +0.5% vs 2.50
            concepts=concepts,
        )]
        issues = validator.validate("NVDA", samples)
        mismatches = [i for i in issues if i["type"] == "EDGAR Mismatch"]
        assert mismatches == []

    def test_share_count_concept_reads_shares_bucket(self, tmp_path):
        concepts = match_concepts("Diluted Shares Outstanding")
        assert concepts and concepts[0] == "WeightedAverageNumberOfDilutedSharesOutstanding"

        val = _extract_annual_value(
            _facts_with_eps_and_shares(),
            "WeightedAverageNumberOfDilutedSharesOutstanding",
            2023,
        )
        assert val == 2_500_000_000.0


class TestDerivedFreeCashFlow:
    def test_derived_fcf_critical_mismatch(self, tmp_path):
        # CFO = 28B, CapEx = -8B -> FCF = 20B. Model says 25B -> +25% -> Critical.
        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
            "companyfacts/CIK0001045810": _FakeResponse(
                200, _facts_with_cfo_and_capex(capex=8_000_000_000.0)),
        })
        client = EDGARClient(cache_dir=tmp_path, session=session)
        validator = EDGARValidator(client=client)

        concepts = match_concepts("Free Cash Flow")
        assert concepts == ["__DERIVED_FCF__"]

        samples = [HistoricalCell(
            sheet="CF", row_label="Free Cash Flow", col_letter="B",
            row_idx=20, col_idx=1, year=2023,
            value=25_000_000_000.0,
            concepts=concepts,
        )]
        issues = validator.validate("NVDA", samples)
        mismatches = [i for i in issues if i["type"] == "EDGAR Mismatch"]
        assert len(mismatches) == 1
        assert mismatches[0]["severity"] == "Critical"
        assert "derived" in mismatches[0]["detail"]

    def test_derived_fcf_missing_component_skipped(self, tmp_path):
        # CFO present, CapEx absent -> FCF cannot be derived -> silent skip.
        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
            "companyfacts/CIK0001045810": _FakeResponse(
                200, _facts_with_cfo_and_capex(capex=None)),
        })
        client = EDGARClient(cache_dir=tmp_path, session=session)
        validator = EDGARValidator(client=client)

        samples = [HistoricalCell(
            sheet="CF", row_label="Free Cash Flow", col_letter="B",
            row_idx=20, col_idx=1, year=2023,
            value=25_000_000_000.0,
            concepts=match_concepts("Free Cash Flow"),
        )]
        issues = validator.validate("NVDA", samples)
        assert [i for i in issues if i["type"] == "EDGAR Mismatch"] == []


class TestInconclusiveMatchGuard:
    """Segment / misfired-concept rows should be downgraded, not Critical."""

    def _build_validator(self, tmp_path):
        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
            "companyfacts/CIK0001045810": _FakeResponse(200, _facts_for_nvda()),
        })
        return EDGARValidator(
            client=EDGARClient(cache_dir=tmp_path, session=session))

    def test_segment_level_row_downgraded_to_medium(self, tmp_path):
        # Model says "Total revenue" = 22_000_000_000 (a segment subtotal);
        # EDGAR consolidated Revenues = 60_922_000_000. Raw delta 63.9%,
        # no scale produces a tight tie -> Medium, not Critical.
        validator = self._build_validator(tmp_path)
        samples = [HistoricalCell(
            sheet="Model", row_label="Total revenue", col_letter="R",
            row_idx=356, col_idx=17, year=2023,
            value=22_000_000_000.0,
            concepts=["Revenues"],
        )]
        issues = validator.validate("NVDA", samples)
        mismatches = [i for i in issues if i["type"] == "EDGAR Mismatch"]
        assert len(mismatches) == 1
        assert mismatches[0]["severity"] == "Medium"
        assert "investigate manually" in mismatches[0]["detail"]

    def test_legitimate_small_critical_preserved(self, tmp_path):
        # Model = 64_000_000_000 vs EDGAR 60_922_000_000 -> 5.05% delta;
        # raw delta is small (5%), so the inconclusive-match guard does not
        # fire and this stays a real Critical.
        validator = self._build_validator(tmp_path)
        samples = [HistoricalCell(
            sheet="IS", row_label="Revenue", col_letter="B",
            row_idx=10, col_idx=1, year=2023,
            value=64_000_000_000.0,
            concepts=["Revenues"],
        )]
        issues = validator.validate("NVDA", samples)
        mismatches = [i for i in issues if i["type"] == "EDGAR Mismatch"]
        assert len(mismatches) == 1
        assert mismatches[0]["severity"] == "Critical"


class TestPerGroupEmissionCap:
    """Large avalanches of same-concept Criticals should roll up to a summary."""

    def test_cap_emits_summary_row(self, tmp_path):
        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
            "companyfacts/CIK0001045810": _FakeResponse(200, _facts_for_nvda()),
        })
        validator = EDGARValidator(
            client=EDGARClient(cache_dir=tmp_path, session=session))

        # 12 cells, same sheet + concept + severity (all clean Critical at ~10%).
        samples = [HistoricalCell(
            sheet="IS", row_label="Revenue", col_letter="B",
            row_idx=10 + i, col_idx=1, year=2023,
            value=67_000_000_000.0,  # ~10% above EDGAR -> Critical
            concepts=["Revenues"],
        ) for i in range(12)]
        issues = validator.validate("NVDA", samples)
        mismatches = [i for i in issues if i["type"] == "EDGAR Mismatch"]

        # Per-group cap is 5 real rows + 1 summary row.
        assert len(mismatches) == 6
        summaries = [m for m in mismatches
                     if "suppressed to reduce noise" in m.get("detail", "")]
        assert len(summaries) == 1
        assert "7 additional" in summaries[0]["detail"]


class TestLabelAndSheetFilters:
    """Adjusted / non-GAAP labels and segment / quarterly sheets must bypass
    EDGAR validation so their intentional divergences don't surface as false
    Criticals."""

    @pytest.mark.parametrize("label", [
        "Net income (adjusted)",
        "Net income to common (adjusted)",
        "Revenue — non-GAAP",
        "Operating income (pro forma)",
        "Normalized EBIT",
        "Underlying net income",
        "Core earnings",
        "EBIT (ex-investments)",
        "Revenue ex-FX",
        "Operating income excluding special items",
    ])
    def test_non_gaap_labels_flagged(self, label):
        from src.edgar_validator import _is_non_gaap_label as fn
        assert fn(label) is True
        # Adjusted labels yield no concepts, so EDGAR validation is bypassed.
        assert match_concepts(label) == []

    @pytest.mark.parametrize("label", [
        "Net income",
        "Net income (reported)",
        "Total revenue",
        "Gross profit",
        "Total assets",
    ])
    def test_gaap_labels_not_flagged(self, label):
        from src.edgar_validator import _is_non_gaap_label as fn
        assert fn(label) is False
        assert match_concepts(label) != []

    @pytest.mark.parametrize("sheet", [
        "E&P", "R&M", "Upstream", "Downstream", "Chemicals",
        "Refining & Marketing", "Segment Data",
    ])
    def test_segment_sheets_flagged(self, sheet):
        from src.edgar_validator import _is_segment_sheet as fn
        assert fn(sheet) is True

    @pytest.mark.parametrize("sheet", ["Model", "Annual", "IS", "BS", "CF", "Summary"])
    def test_consolidated_sheets_not_segment(self, sheet):
        from src.edgar_validator import _is_segment_sheet as fn
        assert fn(sheet) is False

    @pytest.mark.parametrize("sheet", [
        "Quarterly", "Q Input", "Qtrly", "Interim Data", "MRQ",
    ])
    def test_quarterly_sheets_flagged(self, sheet):
        from src.edgar_validator import _is_quarterly_sheet as fn
        assert fn(sheet) is True

    @pytest.mark.parametrize("sheet", ["Annual", "Model", "Summary", "IS"])
    def test_annual_sheets_not_quarterly(self, sheet):
        from src.edgar_validator import _is_quarterly_sheet as fn
        assert fn(sheet) is False


class TestExtractAnnualValuePriorYearFilter:
    """Multi-entry XBRL payloads must select the entry whose period-end year
    matches the fiscal year, not the prior-year comparative bundled in a later
    10-K."""

    def test_prior_year_comparative_skipped(self):
        facts = {
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "units": {
                            "USD": [
                                # prior-year comparative from FY2010 10-K
                                {"fy": 2010, "fp": "FY", "end": "2009-12-31",
                                 "val": 233_323_000_000, "filed": "2011-02-25",
                                 "form": "10-K"},
                                # real FY2010 balance
                                {"fy": 2010, "fp": "FY", "end": "2010-12-31",
                                 "val": 302_510_000_000, "filed": "2011-02-25",
                                 "form": "10-K"},
                                # later 10-K/A restatement of same FY2010 balance
                                {"fy": 2010, "fp": "FY", "end": "2010-12-31",
                                 "val": 302_510_000_000, "filed": "2011-02-28",
                                 "form": "10-K/A"},
                            ]
                        }
                    }
                }
            }
        }
        val = _extract_annual_value(facts, "Assets", 2010)
        assert val == 302_510_000_000.0

    def test_no_end_match_falls_back_to_first(self):
        # Non-calendar filer: end date is mid-year, won't start with "2023-"
        facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"fy": 2023, "fp": "FY", "end": "2023-06-30",
                                 "val": 100_000_000, "filed": "2023-09-01",
                                 "form": "10-K"},
                            ]
                        }
                    }
                }
            }
        }
        val = _extract_annual_value(facts, "Revenues", 2023)
        assert val == 100_000_000.0


class TestDerivedLTDebtTotal:
    """Total long-term debt in a model typically includes the current portion
    of LT debt. XBRL separates them, so we derive the sum."""

    def test_noncurrent_plus_current_matches_model(self, tmp_path):
        facts = {
            "facts": {
                "us-gaap": {
                    "LongTermDebtNoncurrent": {
                        "units": {"USD": [
                            {"fy": 2009, "fp": "FY", "end": "2009-12-31",
                             "val": 9_009_000_000, "filed": "2010-02-01",
                             "form": "10-K"},
                        ]}
                    },
                    "LongTermDebtCurrent": {
                        "units": {"USD": [
                            {"fy": 2009, "fp": "FY", "end": "2009-12-31",
                             "val": 2_164_000_000, "filed": "2010-02-01",
                             "form": "10-K"},
                        ]}
                    },
                }
            }
        }
        session = _FakeSession({
            "company_tickers.json": _FakeResponse(200, _TICKERS_PAYLOAD),
            "companyfacts/CIK0001045810": _FakeResponse(200, facts),
        })
        validator = EDGARValidator(
            client=EDGARClient(cache_dir=tmp_path, session=session))

        concepts = match_concepts("Total long-term debt")
        samples = [HistoricalCell(
            sheet="Model", row_label="Total long-term debt",
            col_letter="R", row_idx=550, col_idx=17, year=2009,
            value=11_173_000_000.0,  # = 9,009M + 2,164M
            concepts=concepts,
        )]
        issues = validator.validate("NVDA", samples)
        # Best match is the derived total (~0% residual) -> Pass, no mismatch.
        assert [i for i in issues if i["type"] == "EDGAR Mismatch"] == []

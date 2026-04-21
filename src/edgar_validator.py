"""EDGAR value-check validator.

Fetches XBRL company facts from SEC EDGAR and compares historical cell values
from the model against filed values. Emits dict-shaped issues compatible with
ModelAuditor._add_issue() / ReportGenerator.

Phase A scope: Core 6 GAAP line items (Revenue, GrossProfit, OperatingIncome,
NetIncome, TotalAssets, TotalLiabilities). Phase B extends the concept map
with 8 additional items, a derived Free Cash Flow check, a unit-bucket
registry (USD / USD/shares / shares), and a per-concept tolerance override.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# SEC fair-use policy requires a User-Agent containing a contact email.
# This default is a placeholder; operators should override via the
# MODELLENS_EDGAR_UA environment variable (or the user_agent constructor
# arg) with their own contact address before running against the live
# API. See https://www.sec.gov/os/accessing-edgar-data
_DEFAULT_UA = "ModelLens/1.0 (set-MODELLENS_EDGAR_UA-env-var@example.com)"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_FACTS_URL_FMT = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h
_HTTP_TIMEOUT = 10.0

_SEVERITY_CRITICAL_PCT = 0.05   # >5%
_SEVERITY_HIGH_PCT = 0.01       # 1-5%
_SEVERITY_MEDIUM_PCT = 0.001    # 0.1-1%
# Below _SEVERITY_MEDIUM_PCT -> Pass (no issue)

# Sentinels used for derived concepts with no single XBRL tag.
_DERIVED_FCF = "__DERIVED_FCF__"
_DERIVED_LT_DEBT_TOTAL = "__DERIVED_LT_DEBT_TOTAL__"

# Row-label regex -> ordered list of XBRL concepts to try.
# Patterns are evaluated against the NORMALIZED label (parentheticals stripped,
# '/' ',' ';' replaced with space, whitespace collapsed, case-insensitive).
_CONCEPT_MAP_CORE6: dict[str, list[str]] = {
    r"^\s*(total\s+|gross\s+)?"
    r"(revenue[s]?|net\s+sales|total\s+sales|"
    r"sales\s+revenue[s]?|total\s+sales\s+revenue[s]?|"
    r"sales\s+net\s+revenue[s]?|net\s+sales\s+revenue[s]?|"
    r"net\s+revenue[s]?|"
    r"sales\s+and\s+revenue[s]?|revenue[s]?\s+and\s+sales)\s*$": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ],
    r"^\s*gross\s+profit\s*$": [
        "GrossProfit",
    ],
    r"^\s*(operating\s+(income|profit)(\s+loss)?|income\s+from\s+operations"
    r"|ebit)\s*$": [
        "OperatingIncomeLoss",
    ],
    r"^\s*net\s+income(\s+loss)?(\s+pre\s+pref\s+dividend[s]?)?\s*$": [
        "NetIncomeLoss",
        "ProfitLoss",
    ],
    r"^\s*net\s+income(\s+loss)?\s+(to|attributable\s+to|available\s+to)"
    r"\s+common(\s+(shareholders?|stockholders?|shareowners?))?\s*$": [
        "NetIncomeLossAvailableToCommonStockholdersBasic",
        "NetIncomeLoss",
    ],
    r"^\s*total\s+assets\s*$": [
        "Assets",
    ],
    r"^\s*total\s+liabilities\s*$": [
        "Liabilities",
    ],
}

# Extended 15 additions (Phase B). Regex anchors mirror the Core 6 style.
_CONCEPT_MAP_EXTENDED: dict[str, list[str]] = {
    r"^\s*(total\s+)?cost\s+of\s+(revenue|sales|goods\s+sold)s?\s*$|^\s*cogs\s*$": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
    ],
    r"^\s*(total\s+)?operating\s+(expenses|costs)\s*$|^\s*total\s+opex\s*$": [
        "OperatingExpenses",
    ],
    r"^\s*(diluted\s+eps|eps\s*[-–]\s*diluted|diluted\s+earnings\s+per\s+share|earnings\s+per\s+share\s*[-–]\s*diluted)\s*$": [
        "EarningsPerShareDiluted",
    ],
    r"^\s*(diluted\s+shares\s+outstanding|weighted[\s-]*(average|avg)[\s-]*diluted\s+shares|diluted\s+share\s+count)\s*$": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
    ],
    r"^\s*cash\s+(and|&)\s+(cash\s+)?equivalents\s*$": [
        "CashAndCashEquivalentsAtCarryingValue",
    ],
    r"^\s*(total\s+)?(long[\s-]term\s+debt|lt\s+debt)\s*$": [
        _DERIVED_LT_DEBT_TOTAL,
        "LongTermDebtNoncurrent",
    ],
    r"^\s*(cash\s+from\s+operations|operating\s+cash\s+flow|cfo|net\s+cash\s+(from|provided\s+by)\s+operating(\s+activities)?|cash\s+provided\s+by\s+operating(\s+activities)?)\s*$": [
        "NetCashProvidedByUsedInOperatingActivities",
    ],
    r"^\s*(capex|capital\s+expenditures?|capital\s+spending|purchases\s+of\s+pp&e|payments\s+for\s+pp&e)\s*$": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
    ],
    r"^\s*(free\s+cash\s+flow|fcf)\s*$": [
        _DERIVED_FCF,
    ],
}

# Merged, iteration-ordered compiled map. Core 6 first to preserve Phase A
# precedence for any overlapping label (there are none today).
_COMPILED_CONCEPT_MAP = [
    (re.compile(pat, re.IGNORECASE), concepts)
    for pat, concepts in {**_CONCEPT_MAP_CORE6, **_CONCEPT_MAP_EXTENDED}.items()
]

# Unit-bucket registry: concept -> the key under facts[concept]["units"].
# Anything not listed defaults to "USD".
_UNIT_BUCKETS: dict[str, str] = {
    "EarningsPerShareDiluted": "USD/shares",
    "EarningsPerShareBasic": "USD/shares",
    "WeightedAverageNumberOfDilutedSharesOutstanding": "shares",
    "WeightedAverageNumberOfSharesOutstandingBasic": "shares",
}


def _bucket_for(concept: str) -> str:
    return _UNIT_BUCKETS.get(concept, "USD")


# Per-concept severity tolerance overrides. Each entry supplies the cutoffs
# for Critical / High / Medium (values below Medium are Pass).
_TOLERANCE_OVERRIDES: dict[str, dict[str, float]] = {
    "EarningsPerShareDiluted": {
        "critical": 0.05,  # >5%
        "high": 0.02,      # 2-5%
        "medium": 0.01,    # 1-2%
    },
    "EarningsPerShareBasic": {
        "critical": 0.05,
        "high": 0.02,
        "medium": 0.01,
    },
}


@dataclass
class HistoricalCell:
    """A cell in the model claimed to hold a historical actual."""
    sheet: str
    row_label: str
    col_letter: str
    row_idx: int       # 0-based
    col_idx: int       # 0-based
    year: int
    value: float
    concepts: list[str]  # ordered XBRL concepts to try


class EDGARClient:
    """Thin wrapper around the SEC EDGAR public endpoints.

    Respects SEC 10 req/sec limit via an on-disk cache (24h TTL) and a
    user-agent header (required by SEC). On any network / parse failure,
    returns None rather than raising.
    """

    def __init__(self, cache_dir: str | os.PathLike | None = None,
                 user_agent: str | None = None,
                 session=None):
        self.user_agent = user_agent or os.getenv("MODELLENS_EDGAR_UA", _DEFAULT_UA)
        self.cache_dir = Path(cache_dir) if cache_dir else Path("data") / ".edgar_cache"
        self._tickers_cache: dict[str, str] | None = None
        self._facts_cache: dict[str, dict] = {}
        self._session = session  # for test injection

    # ------------------------------------------------------------------
    # Caching helpers
    # ------------------------------------------------------------------

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _read_cache(self, key: str) -> dict | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if age > _CACHE_TTL_SECONDS:
            return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None

    def _write_cache(self, key: str, payload: dict) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with self._cache_path(key).open("w", encoding="utf-8") as fh:
                json.dump(payload, fh)
        except OSError as exc:
            logger.debug("EDGAR cache write failed for %s: %s", key, exc)

    # ------------------------------------------------------------------
    # Network
    # ------------------------------------------------------------------

    def _get_json(self, url: str) -> dict | None:
        if requests is None:
            logger.info("requests not available; EDGAR check skipped")
            return None
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        session = self._session or requests
        try:
            resp = session.get(url, headers=headers, timeout=_HTTP_TIMEOUT)
        except requests.exceptions.Timeout:
            logger.info("EDGAR request timed out: %s", url)
            return None
        except requests.exceptions.RequestException as exc:
            logger.info("EDGAR request failed (%s): %s", type(exc).__name__, url)
            return None
        if resp.status_code >= 500:
            # one retry on server-side failures
            try:
                resp = session.get(url, headers=headers, timeout=_HTTP_TIMEOUT)
            except requests.exceptions.RequestException:
                return None
        if resp.status_code != 200:
            logger.info("EDGAR returned %s for %s", resp.status_code, url)
            return None
        try:
            return resp.json()
        except (ValueError, json.JSONDecodeError):
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_cik(self, ticker: str) -> str | None:
        """Return zero-padded 10-digit CIK for ticker, or None if unresolved."""
        if not ticker:
            return None
        ticker_upper = ticker.strip().upper()

        if self._tickers_cache is None:
            cached = self._read_cache("tickers")
            if cached is None:
                cached = self._get_json(_TICKERS_URL)
                if cached is None:
                    return None
                self._write_cache("tickers", cached)
            # The SEC payload is a dict keyed by row index; each value has
            # {"cik_str": int, "ticker": str, "title": str}
            table: dict[str, str] = {}
            for entry in cached.values() if isinstance(cached, dict) else []:
                t = entry.get("ticker")
                cik = entry.get("cik_str")
                if t and cik is not None:
                    table[t.upper()] = str(cik).zfill(10)
            self._tickers_cache = table

        return self._tickers_cache.get(ticker_upper)

    def company_facts(self, cik: str) -> dict | None:
        """Return parsed XBRL company facts JSON for a 10-digit CIK, or None."""
        if not cik:
            return None
        if cik in self._facts_cache:
            return self._facts_cache[cik]
        cached = self._read_cache(f"facts_{cik}")
        if cached is None:
            cached = self._get_json(_FACTS_URL_FMT.format(cik=cik))
            if cached is None:
                return None
            self._write_cache(f"facts_{cik}", cached)
        self._facts_cache[cik] = cached
        return cached


# ----------------------------------------------------------------------
# Concept lookup from facts payload
# ----------------------------------------------------------------------

def _extract_annual_value(facts: dict, concept: str, fiscal_year: int,
                          unit: str | None = None) -> float | None:
    """Return the annual value for a given concept and fiscal year.

    XBRL company facts include a separate entry for every prior-year
    comparative that appears in a later 10-K, each tagged with the SAME
    ``fy`` / ``fp`` as the filing year. Example: an ``fy=2010, fp=FY``
    Assets payload will contain entries with ``end=2009-12-31`` (prior-year
    comparative from the FY2010 10-K) as well as ``end=2010-12-31`` (the
    real FY2010 balance). Picking the first match yields the comparative
    value — a year off — which surfaces as a spurious Critical mismatch.
    We therefore filter to entries whose ``end`` date year equals
    ``fiscal_year`` and prefer the latest ``filed`` date to pick up any
    restated value (10-K/A over the original 10-K).

    The unit bucket defaults to the registry mapping for the concept (USD
    for most, USD/shares for EPS, shares for share-count concepts). Callers
    may override ``unit`` to select a specific bucket. Returns None if the
    concept, bucket, or FY entry is missing.
    """
    bucket = unit or _bucket_for(concept)
    try:
        entries = facts["facts"]["us-gaap"][concept]["units"][bucket]
    except (KeyError, TypeError):
        return None
    candidates: list[dict] = []
    for entry in entries:
        if entry.get("fy") != fiscal_year or entry.get("fp") != "FY":
            continue
        val = entry.get("val")
        if not isinstance(val, (int, float)):
            continue
        end = entry.get("end") or ""
        if end.startswith(f"{fiscal_year}-"):
            candidates.append(entry)
    if not candidates:
        # Fallback: no end-date match (e.g., fiscal year doesn't align to a
        # calendar year-end). Use the first well-typed entry, matching the
        # original behavior so non-calendar filers still resolve.
        for entry in entries:
            if entry.get("fy") == fiscal_year and entry.get("fp") == "FY":
                val = entry.get("val")
                if isinstance(val, (int, float)):
                    return float(val)
        return None
    # Prefer latest filing (10-K/A restatement takes precedence over 10-K);
    # stable tiebreaker on ``end`` keeps results deterministic.
    candidates.sort(key=lambda e: (e.get("filed") or "", e.get("end") or ""),
                    reverse=True)
    return float(candidates[0]["val"])


def _derive_fcf(facts: dict, fiscal_year: int) -> float | None:
    """Return CFO minus CapEx for ``fiscal_year`` when both tags are filed.

    EDGAR has no FCF tag. If either component is absent for the FY, return
    None so the caller silently skips the cell rather than raising a false
    mismatch.
    """
    cfo = _extract_annual_value(
        facts, "NetCashProvidedByUsedInOperatingActivities", fiscal_year)
    if cfo is None:
        return None
    capex = _extract_annual_value(
        facts, "PaymentsToAcquirePropertyPlantAndEquipment", fiscal_year)
    if capex is None:
        return None
    return cfo - capex


def _derive_lt_debt_total(facts: dict, fiscal_year: int) -> float | None:
    """Return noncurrent LT debt + current portion of LT debt for ``fiscal_year``.

    Model rows labelled "Total long-term debt" typically sum the current portion
    (amounts due within 12 months that were originally long-dated) with the
    noncurrent balance. XBRL exposes these under separate tags; summing them
    matches the common sellside presentation.

    Returns None only when the noncurrent piece is missing. The current piece
    may be genuinely zero (filer has no near-term maturities), so a missing
    ``LongTermDebtCurrent`` tag is treated as zero.
    """
    noncurrent = _extract_annual_value(facts, "LongTermDebtNoncurrent", fiscal_year)
    if noncurrent is None:
        return None
    current = _extract_annual_value(facts, "LongTermDebtCurrent", fiscal_year)
    return noncurrent + (current or 0.0)


_PAREN_RE = re.compile(r"\([^)]*\)")
_NOISE_CHARS_RE = re.compile(r"[/,;]+")
_MULTI_WS_RE = re.compile(r"\s+")

# Row-label markers that signal an explicitly non-GAAP / adjusted / segment-level
# figure. EDGAR XBRL tags are GAAP-basis, so these rows must not be compared
# against them — doing so produces spurious Critical mismatches when the user's
# model intentionally diverges (e.g., "Net income (adjusted)" excludes one-time
# items). Matched case-insensitively against the RAW (pre-normalized) label so
# parenthetical markers like "(adjusted)" remain visible before stripping.
_NON_GAAP_LABEL_RE = re.compile(
    r"\b(adjusted|non[\s-]?gaap|pro\s+forma|normalized|underlying|"
    r"core(?:\s+earnings)?|operating\s+(?:adj|adjusted)|recurring|"
    r"ex[\s-]?(?:investments?|items?|one[\s-]?time|special|fx|"
    r"currency|charges?|restructuring|impairments?)|"
    r"excluding|excl\.)\b",
    re.IGNORECASE,
)

# Segment / business-line sheet names that hold divisional (not consolidated)
# totals. Consolidated XBRL tags don't tie to segment rollups, so we skip
# validation on these sheets entirely. Matched case-insensitively with word
# boundaries against the full sheet name.
_SEGMENT_SHEET_TOKENS = (
    "e&p", "r&m", "upstream", "downstream", "midstream",
    "chemical", "chemicals", "refining", "marketing",
    "exploration", "production", "segment", "segments",
)

# Quarterly / interim-period sheet names. XBRL company facts hold fiscal-year
# (annual) values, so quarter-end balance sheet cells and quarterly income
# statement totals do not tie to EDGAR's FY data even when the column header
# parses as a year. Skip these sheets to avoid comparing mid-year snapshots
# to year-end XBRL.
_QUARTERLY_SHEET_TOKENS = (
    "quarterly", "quarter", "qtrly", "q input", "q-input", "qinput",
    "interim", "mrq",
)


def _is_non_gaap_label(row_label: str) -> bool:
    """True when the row label flags an explicitly non-GAAP / adjusted metric
    that should not be compared against filed GAAP XBRL values.
    """
    if not isinstance(row_label, str):
        return False
    return _NON_GAAP_LABEL_RE.search(row_label) is not None


def _is_segment_sheet(sheet_name: str) -> bool:
    """True when the sheet holds segment-level (not consolidated) totals."""
    if not isinstance(sheet_name, str):
        return False
    lowered = sheet_name.lower()
    return any(tok in lowered for tok in _SEGMENT_SHEET_TOKENS)


def _is_quarterly_sheet(sheet_name: str) -> bool:
    """True when the sheet holds quarterly / interim (non-FY) data."""
    if not isinstance(sheet_name, str):
        return False
    lowered = sheet_name.lower()
    return any(tok in lowered for tok in _QUARTERLY_SHEET_TOKENS)


def _normalize_label(row_label: str) -> str:
    """Strip parentheticals and punctuation noise so regex matchers see a
    canonical form. ``"EBIT (Operating Profit)"`` -> ``"EBIT"``;
    ``"Total Sales/Revenues"`` -> ``"Total Sales Revenues"``;
    ``"Sales, net revenue"`` -> ``"Sales net revenue"``. Hyphens are preserved
    so ``"long-term debt"`` still matches.
    """
    s = _PAREN_RE.sub(" ", row_label)
    s = _NOISE_CHARS_RE.sub(" ", s)
    s = _MULTI_WS_RE.sub(" ", s).strip()
    return s


def match_concepts(row_label: str) -> list[str]:
    """Return the ordered concept list for a row label, or [] if no match.

    Explicitly non-GAAP / adjusted labels (``"Net income (adjusted)"``,
    ``"Revenue — ex-investments"``, etc.) return ``[]`` so callers skip
    EDGAR validation on them.
    """
    if not isinstance(row_label, str):
        return []
    if _is_non_gaap_label(row_label):
        return []
    normalized = _normalize_label(row_label)
    if not normalized:
        return []
    for pattern, concepts in _COMPILED_CONCEPT_MAP:
        if pattern.search(normalized):
            return list(concepts)
    return []


# ----------------------------------------------------------------------
# Severity scoring
# ----------------------------------------------------------------------

def _severity_for_delta(model_val: float, edgar_val: float,
                        concept: str | None = None) -> str | None:
    """Return severity string or None if within Pass threshold.

    When ``concept`` has an entry in ``_TOLERANCE_OVERRIDES`` those cutoffs
    are used instead of the defaults. EPS uses a wider Medium band to allow
    legitimate rounding to one or two decimals.
    """
    if edgar_val == 0:
        return "High" if abs(model_val) > 1.0 else None
    override = _TOLERANCE_OVERRIDES.get(concept) if concept else None
    if override is not None:
        crit, high, med = override["critical"], override["high"], override["medium"]
    else:
        crit, high, med = _SEVERITY_CRITICAL_PCT, _SEVERITY_HIGH_PCT, _SEVERITY_MEDIUM_PCT
    pct = abs(model_val - edgar_val) / abs(edgar_val)
    if pct > crit:
        return "Critical"
    if pct > high:
        return "High"
    if pct > med:
        return "Medium"
    return None


def _format_detail(label: str, year: int, model_val: float, edgar_val: float) -> str:
    delta = model_val - edgar_val
    if edgar_val != 0:
        pct = abs(delta) / abs(edgar_val) * 100.0
    else:
        pct = float("inf")
    model_m = model_val / 1_000_000.0
    edgar_m = edgar_val / 1_000_000.0
    delta_m = delta / 1_000_000.0
    pct_str = f"{pct:.1f}%" if pct != float("inf") else "n/a"
    sign = "+" if delta >= 0 else "-"
    return (
        f"{label.strip()} FY{year}: model ${model_m:,.1f}M vs EDGAR ${edgar_m:,.1f}M "
        f"({sign}${abs(delta_m):,.1f}M, {pct_str})"
    )


def _scale_check_hit(model_val: float, edgar_val: float,
                     tolerance: float = _SEVERITY_MEDIUM_PCT) -> float | None:
    """Return a likely scale multiplier (1000, 1_000_000, or 1_000_000_000)
    if model is a scaled copy of edgar within ``tolerance``, else None.

    The default ``tolerance`` matches the Medium severity cutoff (0.1%), which
    is strict enough to only fire on exact rounding-grade slips. Callers that
    want to infer a *probable* unit mismatch (e.g., the magnitude-aware best
    match in ``validate``) should pass a looser tolerance.
    """
    if edgar_val == 0 or model_val == 0:
        return None
    for mult in (1_000.0, 1_000_000.0, 1_000_000_000.0):
        scaled = model_val * mult
        if abs(scaled - edgar_val) / abs(edgar_val) <= tolerance:
            return mult
    return None


_SCALE_CANDIDATES = (1.0, 1_000.0, 1_000_000.0, 1_000_000_000.0)
# When a best-match scale factor produces a residual delta within this band
# *and* the raw 1x comparison was worse by a wide margin, treat it as an
# inferred unit mismatch (Medium) instead of a Critical data-tie failure.
_INFERRED_SCALE_TOLERANCE = 0.10  # 10% residual


# ----------------------------------------------------------------------
# Main validator
# ----------------------------------------------------------------------

class EDGARValidator:
    """Compares historical cell samples against EDGAR company facts."""

    def __init__(self, client: EDGARClient | None = None):
        self.client = client or EDGARClient()

    def validate(self,
                 ticker: str | None,
                 samples: list[HistoricalCell]) -> list[dict]:
        """Return a list of issue dicts (EDGAR Mismatch or EDGAR Check Skipped).

        Emits one 'EDGAR Check Skipped' note when validation cannot proceed,
        zero issues when no ticker was supplied, and otherwise one
        'EDGAR Mismatch' per failing sample.
        """
        if ticker is None or not ticker.strip():
            # Not requested -> no issues at all.
            return []

        issues: list[dict] = []

        if not samples:
            return [_skip_issue("no Core 6 historical rows matched in model")]

        cik = self.client.resolve_cik(ticker)
        if cik is None:
            return [_skip_issue(f"CIK not resolved for ticker '{ticker}'")]

        facts = self.client.company_facts(cik)
        if facts is None:
            return [_skip_issue(f"EDGAR company_facts unavailable for CIK {cik}")]

        # Cap the number of issues per (sheet, concept, severity) group so a
        # single mis-labelled sheet can't generate hundreds of near-identical
        # flags. After N flags for the same group we stop emitting individual
        # rows and record a single summary note at the end.
        emission_counts: dict[tuple[str, str, str], int] = {}
        suppressed_counts: dict[tuple[str, str, str], int] = {}
        _PER_GROUP_CAP = 5

        def _emit(issue: dict, sheet: str, concept: str) -> bool:
            key = (sheet, concept, issue["severity"])
            n = emission_counts.get(key, 0)
            if n >= _PER_GROUP_CAP:
                suppressed_counts[key] = suppressed_counts.get(key, 0) + 1
                return False
            emission_counts[key] = n + 1
            issues.append(issue)
            return True

        for cell in samples:
            # Gather every candidate EDGAR value across the cell's concept list.
            candidates: list[tuple[str, float, bool]] = []
            for concept in cell.concepts:
                if concept == _DERIVED_FCF:
                    val = _derive_fcf(facts, cell.year)
                    if val is not None:
                        candidates.append((concept, val, True))
                    continue
                if concept == _DERIVED_LT_DEBT_TOTAL:
                    val = _derive_lt_debt_total(facts, cell.year)
                    if val is not None:
                        candidates.append((concept, val, True))
                    continue
                val = _extract_annual_value(facts, concept, cell.year)
                if val is not None:
                    candidates.append((concept, val, False))
            if not candidates:
                continue

            # Across candidates and USD scale factors (1x, 1e3, 1e6, 1e9),
            # find the (concept, scale) pair that minimises the residual
            # percent delta. Per-share / share-count concepts are never
            # scaled — their unit bucket already matches the raw XBRL value.
            best: tuple[str, float, float, float, bool] | None = None
            primary_concept = candidates[0][0]
            primary_val = candidates[0][1]
            for concept, edgar_val, derived in candidates:
                bucket = _bucket_for(concept)
                scale_opts = (1.0,) if bucket != "USD" else _SCALE_CANDIDATES
                for scale in scale_opts:
                    if edgar_val == 0:
                        continue
                    scaled_model = cell.value * scale
                    delta_pct = abs(scaled_model - edgar_val) / abs(edgar_val)
                    if best is None or delta_pct < best[3]:
                        best = (concept, edgar_val, scale, delta_pct, derived)

            if best is None:
                continue
            matched_concept, edgar_val, scale_used, best_delta, derived = best
            if matched_concept == _DERIVED_FCF:
                derived_note = " (derived: CFO \u2212 CapEx)"
            elif matched_concept == _DERIVED_LT_DEBT_TOTAL:
                derived_note = " (derived: LT debt noncurrent + current)"
            else:
                derived_note = ""
            scaled_model = cell.value * scale_used
            location = f"{cell.sheet}!{cell.col_letter}{cell.row_idx + 1}"

            # Exact scale match (rounding-grade): Medium, "scale mismatch".
            if _bucket_for(matched_concept) != "USD/shares":
                mult = _scale_check_hit(cell.value, edgar_val)
                if mult is not None:
                    _emit(_mismatch_issue(
                        severity="Medium",
                        location=location,
                        detail=(
                            f"{cell.row_label.strip()} FY{cell.year}: model ${cell.value:,.0f} "
                            f"vs EDGAR ${edgar_val:,.0f}. Likely scale mismatch (model appears "
                            f"to be off by {int(mult):,}x). Concept: us-gaap:{matched_concept}."
                            f"{derived_note}"
                        ),
                    ), cell.sheet, matched_concept)
                    continue

            # If the raw (1x) comparison against the PREFERRED concept is
            # already catastrophic (>>100%) but a non-trivial scale factor
            # brings any concept within the inferred-scale tolerance, treat
            # it as a probable sheet-level unit ambiguity and downgrade to
            # Medium. Prevents avalanches of false Criticals on sheets that
            # lack an explicit unit hint.
            if scale_used != 1.0 and best_delta <= _INFERRED_SCALE_TOLERANCE:
                primary_bucket = _bucket_for(primary_concept)
                raw_delta = float("inf")
                if primary_val != 0 and primary_bucket != "USD/shares":
                    raw_delta = abs(cell.value - primary_val) / abs(primary_val)
                if raw_delta > 0.5:
                    _emit(_mismatch_issue(
                        severity="Medium",
                        location=location,
                        detail=(
                            f"{cell.row_label.strip()} FY{cell.year}: inferred unit mismatch "
                            f"(model value fits EDGAR after x{int(scale_used):,} scale). "
                            f"Concept: us-gaap:{matched_concept}. Residual {best_delta*100:.1f}%."
                            f"{derived_note}"
                        ),
                    ), cell.sheet, matched_concept)
                    continue

            # Inconclusive-match guard: when the raw 1x delta against the
            # preferred concept is large (>40%) AND even the best (concept,
            # scale) pair still exceeds the Critical threshold, the cell almost
            # certainly maps to a different underlying line item than the label
            # regex inferred — typical culprits are segment totals vs
            # consolidated, per-share metrics, growth rates, or restated bases.
            # Downgrade to Medium so these don't avalanche as false Criticals.
            _EXTREME_RAW_DELTA = 0.40
            _INCONCLUSIVE_BEST_DELTA = _SEVERITY_CRITICAL_PCT  # 5%
            primary_bucket = _bucket_for(primary_concept)
            raw_primary_delta = float("inf")
            if primary_val != 0 and primary_bucket != "USD/shares":
                raw_primary_delta = abs(cell.value - primary_val) / abs(primary_val)
            if (raw_primary_delta > _EXTREME_RAW_DELTA
                    and best_delta > _INCONCLUSIVE_BEST_DELTA):
                _emit(_mismatch_issue(
                    severity="Medium",
                    location=location,
                    detail=(
                        f"{cell.row_label.strip()} FY{cell.year}: model ${cell.value:,.0f} "
                        f"does not tie to EDGAR under any tested concept or unit scale "
                        f"(best residual {best_delta*100:.1f}%). Possible concept or unit "
                        f"mismatch — investigate manually. Concept tried: "
                        f"us-gaap:{matched_concept}.{derived_note}"
                    ),
                ), cell.sheet, matched_concept)
                continue

            # Use the best-matching (concept, scale) for severity; scale_used
            # only kicks in above when it brings the residual inside tolerance.
            sev = _severity_for_delta(scaled_model, edgar_val, concept=matched_concept)
            if sev is None:
                continue
            detail = _format_detail(cell.row_label, cell.year, cell.value, edgar_val)
            detail += f" Concept: us-gaap:{matched_concept}.{derived_note}"
            _emit(_mismatch_issue(severity=sev, location=location, detail=detail),
                  cell.sheet, matched_concept)

        # Emit a single summary line per suppressed (sheet, concept, severity)
        # group so the user knows how many additional flags were rolled up.
        for (sheet, concept, sev), n in suppressed_counts.items():
            issues.append(_mismatch_issue(
                severity=sev,
                location=f"{sheet}!-",
                detail=(
                    f"{n} additional '{sev}' EDGAR Mismatch rows on sheet '{sheet}' for "
                    f"us-gaap:{concept} were suppressed to reduce noise "
                    f"(cap {_PER_GROUP_CAP} per sheet/concept/severity). Review the first "
                    f"{_PER_GROUP_CAP} flagged rows; if they share a root cause, the rest "
                    f"likely do too."
                ),
            ))

        return issues


# ----------------------------------------------------------------------
# Issue constructors (kept local so EDGAR issues don't depend on auditor)
# ----------------------------------------------------------------------

_MISMATCH_WHY = "Historical values in a financial model should tie to the company's audited SEC filings."
_MISMATCH_CAUSE = "Transcription error, stale copy-paste from a prior filing, or an undocumented non-GAAP adjustment."
_MISMATCH_FIX = ("Update the cell to match the 10-K / 10-Q value, or if the delta is intentional "
                 "(e.g., non-GAAP adjustment) document it in a notes tab.")

_SKIP_WHY = "EDGAR validation was requested but could not be performed."
_SKIP_CAUSE = "Ticker unresolved, network unavailable, or no matching historical rows detected."
_SKIP_FIX = "Confirm the ticker is a SEC registrant, check network connectivity, or label historical columns clearly (e.g., FY2023A)."


def _mismatch_issue(severity: str, location: str, detail: str) -> dict:
    return {
        "type": "EDGAR Mismatch",
        "severity": severity,
        "location": location,
        "detail": detail,
        "why": _MISMATCH_WHY,
        "cause": _MISMATCH_CAUSE,
        "fix": _MISMATCH_FIX,
    }


def _skip_issue(reason: str) -> dict:
    return {
        "type": "EDGAR Check Skipped",
        "severity": "Medium",
        "location": "-",
        "detail": f"EDGAR check skipped: {reason}.",
        "why": _SKIP_WHY,
        "cause": _SKIP_CAUSE,
        "fix": _SKIP_FIX,
    }

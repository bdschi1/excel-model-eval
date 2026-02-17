"""Pydantic v2 output schemas for model results."""
from __future__ import annotations

from pydantic import BaseModel, Field

from builder.assumptions import ModelAssumptions


# ------------------------------------------------------------------
# Projection line items
# ------------------------------------------------------------------
class YearProjection(BaseModel):
    """One year of projected financials."""

    year: int
    revenue: float
    revenue_growth: float
    ebitda: float
    ebitda_margin: float
    depreciation: float
    ebit: float
    taxes: float
    nopat: float
    capex: float
    nwc_change: float
    fcf: float
    discount_factor: float
    pv_fcf: float


# ------------------------------------------------------------------
# Terminal value
# ------------------------------------------------------------------
class TerminalValue(BaseModel):
    """Terminal-value computation detail."""

    method: str = "Gordon Growth"
    terminal_fcf: float
    growth_rate: float
    terminal_value: float
    pv_terminal: float
    implied_exit_multiple: float
    tv_as_pct_of_ev: float


# ------------------------------------------------------------------
# Scenario
# ------------------------------------------------------------------
class ScenarioResult(BaseModel):
    """Result for a single probability-weighted scenario."""

    name: str
    probability: float
    equity_value_per_share: float
    ev: float
    key_assumptions: dict[str, object] = Field(default_factory=dict)


# ------------------------------------------------------------------
# Valuation roll-up
# ------------------------------------------------------------------
class ValuationSummary(BaseModel):
    """Top-level valuation numbers."""

    ev: float
    equity_value: float
    equity_value_per_share: float
    tv_as_pct_of_ev: float
    implied_exit_multiple: float


# ------------------------------------------------------------------
# Full model output
# ------------------------------------------------------------------
class ModelOutput(BaseModel):
    """Everything returned by :meth:`DCFModelBuilder.build`."""

    assumptions: ModelAssumptions
    projections: list[YearProjection]
    terminal_value: TerminalValue
    valuation: ValuationSummary
    scenarios: list[ScenarioResult] = Field(default_factory=list)


# ------------------------------------------------------------------
# Sensitivity grid
# ------------------------------------------------------------------
class SensitivityGrid(BaseModel):
    """Two-dimensional sensitivity table."""

    param1_name: str
    param2_name: str
    param1_values: list[float]
    param2_values: list[float]
    grid: list[list[float]]
    base_value: float


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------
class ValidationIssue(BaseModel):
    """A single warning or error surfaced by the validator."""

    severity: str = Field(pattern=r"^(warning|error)$")
    dimension: str
    message: str
    threshold: str = ""

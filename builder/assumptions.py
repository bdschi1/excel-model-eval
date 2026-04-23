"""Pydantic v2 schemas for model assumptions and scenarios."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

# Plausibility bounds for per-year lists. Intentionally wide so stress
# scenarios remain representable, but tight enough to catch unit errors
# (e.g. passing 10 instead of 0.10 for a 10% growth rate).
_GROWTH_MIN, _GROWTH_MAX = -0.95, 2.0
_MARGIN_MIN, _MARGIN_MAX = -1.0, 1.0


class ScenarioAssumption(BaseModel):
    """One probability-weighted scenario overlay."""

    name: str
    probability: float = Field(ge=0.0, le=1.0)
    revenue_growth_override: list[float] | None = None
    margin_override: list[float] | None = None
    terminal_growth_override: float | None = None
    description: str = ""


class ModelAssumptions(BaseModel):
    """Full set of inputs required by :class:`DCFModelBuilder`."""

    company_name: str
    ticker: str
    sector: str

    # Time horizon
    base_year: int = 2024
    projection_years: int = Field(default=7, ge=3, le=15)

    # Revenue & margins
    revenue_base: float = Field(
        gt=0.0, description="Base-year revenue in $M (must be positive)"
    )
    revenue_growth_by_year: list[float]
    ebitda_margin_by_year: list[float]

    # Cost / investment
    da_pct: float = Field(default=0.03, ge=0.0, le=1.0)
    capex_pct: float = Field(default=0.05, ge=0.0, le=1.0)
    nwc_change_pct: float = Field(default=0.01, ge=-1.0, le=1.0)
    tax_rate: float = Field(default=0.25, ge=0.0, le=1.0)

    # Discount rate & terminal
    wacc: float = Field(ge=0.03, le=0.25)
    terminal_growth: float = Field(ge=0.0, le=0.05)

    # Equity bridge
    shares_outstanding: float = Field(
        gt=0.0,
        description="Diluted shares outstanding in millions (must be positive)",
    )
    net_debt: float = Field(
        description="Net debt in $M (negative = net cash)"
    )

    # Scenarios
    scenarios: list[ScenarioAssumption] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # Field-level validators
    # ------------------------------------------------------------------
    @field_validator("revenue_growth_by_year")
    @classmethod
    def _check_growth_bounds(cls, v: list[float]) -> list[float]:
        for i, g in enumerate(v):
            if g < _GROWTH_MIN or g > _GROWTH_MAX:
                raise ValueError(
                    f"revenue_growth_by_year[{i}]={g} outside plausible "
                    f"range [{_GROWTH_MIN}, {_GROWTH_MAX}] "
                    "(expressed as a fraction, not a percent)"
                )
        return v

    @field_validator("ebitda_margin_by_year")
    @classmethod
    def _check_margin_bounds(cls, v: list[float]) -> list[float]:
        for i, m in enumerate(v):
            if m < _MARGIN_MIN or m > _MARGIN_MAX:
                raise ValueError(
                    f"ebitda_margin_by_year[{i}]={m} outside plausible "
                    f"range [{_MARGIN_MIN}, {_MARGIN_MAX}] "
                    "(expressed as a fraction, not a percent)"
                )
        return v

    # ------------------------------------------------------------------
    # Cross-field validators
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def _check_terminal_below_wacc(self) -> ModelAssumptions:
        # Gordon Growth is only defined when wacc > terminal_growth.
        if self.terminal_growth >= self.wacc:
            raise ValueError(
                f"terminal_growth ({self.terminal_growth:.2%}) must be "
                f"strictly less than wacc ({self.wacc:.2%}); "
                "Gordon Growth is undefined otherwise"
            )
        return self

    @model_validator(mode="after")
    def _check_list_lengths(self) -> ModelAssumptions:
        n = self.projection_years
        if len(self.revenue_growth_by_year) != n:
            raise ValueError(
                f"revenue_growth_by_year has {len(self.revenue_growth_by_year)}"
                f" items but projection_years={n}"
            )
        if len(self.ebitda_margin_by_year) != n:
            raise ValueError(
                f"ebitda_margin_by_year has {len(self.ebitda_margin_by_year)}"
                f" items but projection_years={n}"
            )
        return self

    @model_validator(mode="after")
    def _check_scenario_probabilities(self) -> ModelAssumptions:
        if not self.scenarios:
            return self
        total = sum(s.probability for s in self.scenarios)
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Scenario probabilities sum to {total:.4f}; "
                "expected ~1.0"
            )
        # Validate override list lengths where provided
        n = self.projection_years
        for s in self.scenarios:
            if (
                s.revenue_growth_override is not None
                and len(s.revenue_growth_override) != n
            ):
                raise ValueError(
                    f"Scenario '{s.name}' revenue_growth_override "
                    f"has {len(s.revenue_growth_override)} items "
                    f"but projection_years={n}"
                )
            if (
                s.margin_override is not None
                and len(s.margin_override) != n
            ):
                raise ValueError(
                    f"Scenario '{s.name}' margin_override "
                    f"has {len(s.margin_override)} items "
                    f"but projection_years={n}"
                )
        return self

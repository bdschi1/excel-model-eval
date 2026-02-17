"""Pydantic v2 schemas for model assumptions and scenarios."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


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
        description="Base-year revenue in $M"
    )
    revenue_growth_by_year: list[float]
    ebitda_margin_by_year: list[float]

    # Cost / investment
    da_pct: float = 0.03
    capex_pct: float = 0.05
    nwc_change_pct: float = 0.01
    tax_rate: float = 0.25

    # Discount rate & terminal
    wacc: float = Field(ge=0.03, le=0.25)
    terminal_growth: float = Field(ge=0.0, le=0.05)

    # Equity bridge
    shares_outstanding: float = Field(
        description="Diluted shares outstanding in millions"
    )
    net_debt: float = Field(
        description="Net debt in $M (negative = net cash)"
    )

    # Scenarios
    scenarios: list[ScenarioAssumption] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
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

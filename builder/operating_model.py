"""Bottom-up operating model builder.

Ground-truth reference: `references/fsp-skills/skills/3-statements/SKILL.md`
(vendored from `anthropics/financial-services-plugins`, `financial-analysis`
plugin). See `references/fsp-skills/INDEX.md` for the full mapping.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

# Plausibility bounds for unit-growth lists. Matches revenue_growth_by_year
# in builder.assumptions so a unit-error (10 vs 0.10) is caught.
_UNIT_GROWTH_MIN, _UNIT_GROWTH_MAX = -0.95, 2.0


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------
class Segment(BaseModel):
    """One revenue segment (e.g. product line, geography)."""

    name: str
    units_base: float = Field(ge=0.0)
    unit_growth_by_year: list[float]
    asp_base: float = Field(ge=0.0)
    asp_growth: float = Field(default=0.0, ge=-1.0, le=1.0)

    @field_validator("unit_growth_by_year")
    @classmethod
    def _check_unit_growth_bounds(cls, v: list[float]) -> list[float]:
        for i, g in enumerate(v):
            if g < _UNIT_GROWTH_MIN or g > _UNIT_GROWTH_MAX:
                raise ValueError(
                    f"unit_growth_by_year[{i}]={g} outside plausible "
                    f"range [{_UNIT_GROWTH_MIN}, {_UNIT_GROWTH_MAX}] "
                    "(expressed as a fraction, not a percent)"
                )
        return v


class CostStructure(BaseModel):
    """Cost percentages expressed as a fraction of revenue."""

    cogs_pct: float = Field(default=0.40, ge=0.0, le=1.0)
    sga_pct: float = Field(default=0.15, ge=0.0, le=1.0)
    rnd_pct: float = Field(default=0.10, ge=0.0, le=1.0)
    interest_expense: float = Field(default=0.0, ge=0.0)
    tax_rate: float = Field(default=0.25, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_cost_pcts_sum(self) -> CostStructure:
        # COGS + SG&A + R&D cannot exceed 100% of revenue, else EBIT
        # is structurally negative regardless of revenue level.
        total = self.cogs_pct + self.sga_pct + self.rnd_pct
        if total > 1.0:
            raise ValueError(
                f"cogs_pct + sga_pct + rnd_pct = {total:.4f} exceeds 1.0; "
                "EBIT would be structurally negative"
            )
        return self


class WorkingCapitalDrivers(BaseModel):
    """Working-capital assumptions in days."""

    dso: float = Field(default=45.0, ge=0.0, le=365.0)
    dio: float = Field(default=30.0, ge=0.0, le=365.0)
    dpo: float = Field(default=40.0, ge=0.0, le=365.0)


class OperatingAssumptions(BaseModel):
    """Full set of inputs for the operating model."""

    company_name: str = ""
    projection_years: int = Field(default=5, ge=1, le=15)
    segments: list[Segment]
    cost_structure: CostStructure = Field(
        default_factory=CostStructure
    )
    working_capital_drivers: WorkingCapitalDrivers = Field(
        default_factory=WorkingCapitalDrivers
    )


# ------------------------------------------------------------------
# Per-year row
# ------------------------------------------------------------------
class OperatingYear(BaseModel):
    """One year of the operating model output."""

    year: int
    segment_revenues: dict[str, float]
    total_revenue: float
    cogs: float
    gross_profit: float
    gross_margin: float
    sga: float
    rnd: float
    ebit: float
    ebit_margin: float
    interest: float
    ebt: float
    taxes: float
    net_income: float
    net_margin: float
    receivables: float
    inventory: float
    payables: float
    net_working_capital: float


class OperatingModelOutput(BaseModel):
    """Result of :meth:`OperatingModelBuilder.build`."""

    assumptions: OperatingAssumptions
    years: list[OperatingYear]


# ------------------------------------------------------------------
# Builder
# ------------------------------------------------------------------
class OperatingModelBuilder:
    """Build a bottom-up operating model from segments.

    Usage::

        builder = OperatingModelBuilder(assumptions)
        output = builder.build()
        print(builder.to_markdown())
    """

    def __init__(
        self,
        assumptions: OperatingAssumptions | None = None,
    ) -> None:
        self._assumptions = assumptions
        self._output: OperatingModelOutput | None = None

    def set_assumptions(
        self, assumptions: OperatingAssumptions
    ) -> None:
        self._assumptions = assumptions
        self._output = None

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def build(self) -> OperatingModelOutput:
        if self._assumptions is None:
            raise RuntimeError("Call set_assumptions() first")

        a = self._assumptions
        cs = a.cost_structure
        wc = a.working_capital_drivers
        years: list[OperatingYear] = []

        for yi in range(a.projection_years):
            seg_revs: dict[str, float] = {}
            for seg in a.segments:
                # Compound units year-by-year using per-year unit growth.
                # If the growth vector is shorter than the projection,
                # fall back to 0% growth for the remaining years.
                units = seg.units_base
                for j in range(yi + 1):
                    growth = (
                        seg.unit_growth_by_year[j]
                        if j < len(seg.unit_growth_by_year)
                        else 0.0
                    )
                    units = units * (1.0 + growth)
                # ASP compounds at a constant rate across the projection
                # horizon: year N = asp_base * (1 + asp_growth) ** N.
                asp = seg.asp_base * (1.0 + seg.asp_growth) ** (yi + 1)
                seg_revs[seg.name] = round(units * asp, 2)

            total_rev = sum(seg_revs.values())
            cogs = total_rev * cs.cogs_pct
            gp = total_rev - cogs
            gp_margin = gp / total_rev if total_rev else 0.0
            sga = total_rev * cs.sga_pct
            rnd = total_rev * cs.rnd_pct
            ebit = gp - sga - rnd
            ebit_margin = ebit / total_rev if total_rev else 0.0
            interest = cs.interest_expense
            ebt = ebit - interest
            taxes = max(ebt * cs.tax_rate, 0.0)
            ni = ebt - taxes
            ni_margin = ni / total_rev if total_rev else 0.0

            # Working capital
            recv = total_rev * wc.dso / 365.0
            inv = cogs * wc.dio / 365.0
            pay = cogs * wc.dpo / 365.0
            nwc = recv + inv - pay

            years.append(
                OperatingYear(
                    year=yi + 1,
                    segment_revenues=seg_revs,
                    total_revenue=round(total_rev, 2),
                    cogs=round(cogs, 2),
                    gross_profit=round(gp, 2),
                    gross_margin=round(gp_margin, 4),
                    sga=round(sga, 2),
                    rnd=round(rnd, 2),
                    ebit=round(ebit, 2),
                    ebit_margin=round(ebit_margin, 4),
                    interest=round(interest, 2),
                    ebt=round(ebt, 2),
                    taxes=round(taxes, 2),
                    net_income=round(ni, 2),
                    net_margin=round(ni_margin, 4),
                    receivables=round(recv, 2),
                    inventory=round(inv, 2),
                    payables=round(pay, 2),
                    net_working_capital=round(nwc, 2),
                )
            )

        self._output = OperatingModelOutput(
            assumptions=a, years=years
        )
        return self._output

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------
    def to_markdown(self) -> str:
        if self._output is None:
            raise RuntimeError("Call build() first")

        out = self._output
        a = out.assumptions
        lines: list[str] = []

        title = a.company_name or "Operating Model"
        lines.append(f"# {title}")
        lines.append("")

        # Revenue build-up
        lines.append("## Revenue Build-Up")
        lines.append("")
        seg_names = [s.name for s in a.segments]
        header = "| Year |"
        sep = "|------|"
        for sn in seg_names:
            header += f" {sn} |"
            sep += "------|"
        header += " **Total** |"
        sep += "----------|"
        lines.append(header)
        lines.append(sep)
        for yr in out.years:
            row = f"| {yr.year} |"
            for sn in seg_names:
                v = yr.segment_revenues.get(sn, 0.0)
                row += f" {v:,.1f} |"
            row += f" **{yr.total_revenue:,.1f}** |"
            lines.append(row)
        lines.append("")

        # Margin waterfall
        lines.append("## Margin Waterfall")
        lines.append("")
        lines.append(
            "| Year | Revenue | COGS | Gross Profit "
            "| GP% | SG&A | R&D | EBIT | EBIT% "
            "| Net Income | NI% |"
        )
        lines.append(
            "|------|---------|------|-------------|"
            "-----|------|-----|------|-------|"
            "------------|-----|"
        )
        for yr in out.years:
            lines.append(
                f"| {yr.year} "
                f"| {yr.total_revenue:,.1f} "
                f"| {yr.cogs:,.1f} "
                f"| {yr.gross_profit:,.1f} "
                f"| {yr.gross_margin:.1%} "
                f"| {yr.sga:,.1f} "
                f"| {yr.rnd:,.1f} "
                f"| {yr.ebit:,.1f} "
                f"| {yr.ebit_margin:.1%} "
                f"| {yr.net_income:,.1f} "
                f"| {yr.net_margin:.1%} |"
            )
        lines.append("")

        # Working capital
        lines.append("## Working Capital Summary")
        lines.append("")
        lines.append(
            "| Year | Receivables | Inventory "
            "| Payables | Net WC |"
        )
        lines.append(
            "|------|------------|-----------|"
            "----------|--------|"
        )
        for yr in out.years:
            lines.append(
                f"| {yr.year} "
                f"| {yr.receivables:,.1f} "
                f"| {yr.inventory:,.1f} "
                f"| {yr.payables:,.1f} "
                f"| {yr.net_working_capital:,.1f} |"
            )
        lines.append("")

        return "\n".join(lines)

"""Discounted-cash-flow model builder."""
from __future__ import annotations

from typing import Any

from builder.assumptions import ModelAssumptions
from builder.base import BaseModelBuilder
from builder.outputs import (
    ModelOutput,
    ScenarioResult,
    SensitivityGrid,
    TerminalValue,
    ValidationIssue,
    ValuationSummary,
    YearProjection,
)
from builder.validators import validate


class DCFModelBuilder(BaseModelBuilder):
    """Build a full DCF valuation from :class:`ModelAssumptions`.

    Usage::

        builder = DCFModelBuilder()
        builder.set_assumptions(assumptions)
        output = builder.build()
        print(builder.to_markdown())
    """

    def __init__(self) -> None:
        self._assumptions: ModelAssumptions | None = None
        self._output: ModelOutput | None = None

    # ------------------------------------------------------------------
    # Interface
    # ------------------------------------------------------------------
    def set_assumptions(self, assumptions: Any) -> None:
        if not isinstance(assumptions, ModelAssumptions):
            raise TypeError(
                "Expected ModelAssumptions, "
                f"got {type(assumptions).__name__}"
            )
        self._assumptions = assumptions
        self._output = None

    def build(self) -> ModelOutput:
        if self._assumptions is None:
            raise RuntimeError("Call set_assumptions() first")
        self._output = self._build_core(self._assumptions)

        # Scenarios
        if self._assumptions.scenarios:
            self._output.scenarios = self._build_scenarios()

        return self._output

    def validate(self) -> list[ValidationIssue]:
        if self._output is None:
            raise RuntimeError("Call build() first")
        return validate(self._output)

    def sensitivity_table(
        self,
        param1: str,
        param2: str,
        range1: list[float],
        range2: list[float],
    ) -> SensitivityGrid:
        if self._assumptions is None:
            raise RuntimeError("Call set_assumptions() first")

        base_output = self._build_core(self._assumptions)
        base_val = base_output.valuation.equity_value_per_share

        grid: list[list[float]] = []
        for v1 in range1:
            row: list[float] = []
            for v2 in range2:
                tweaked = self._tweak(self._assumptions, param1, v1)
                tweaked = self._tweak(tweaked, param2, v2)
                out = self._build_core(tweaked)
                row.append(round(out.valuation.equity_value_per_share, 2))
            grid.append(row)

        return SensitivityGrid(
            param1_name=param1,
            param2_name=param2,
            param1_values=range1,
            param2_values=range2,
            grid=grid,
            base_value=round(base_val, 2),
        )

    def to_markdown(self) -> str:
        if self._output is None:
            raise RuntimeError("Call build() first")
        return self._render_markdown(self._output)

    # ------------------------------------------------------------------
    # Core DCF engine
    # ------------------------------------------------------------------
    def _build_core(self, a: ModelAssumptions) -> ModelOutput:
        projections: list[YearProjection] = []
        prev_revenue = a.revenue_base

        for i in range(a.projection_years):
            year = a.base_year + i + 1
            growth = a.revenue_growth_by_year[i]
            revenue = prev_revenue * (1.0 + growth)
            margin = a.ebitda_margin_by_year[i]
            ebitda = revenue * margin
            depreciation = revenue * a.da_pct
            ebit = ebitda - depreciation
            taxes = ebit * a.tax_rate
            nopat = ebit - taxes
            capex = revenue * a.capex_pct
            nwc_change = (revenue - prev_revenue) * a.nwc_change_pct
            fcf = nopat + depreciation - capex - nwc_change
            discount_factor = 1.0 / (1.0 + a.wacc) ** (i + 1)
            pv_fcf = fcf * discount_factor

            projections.append(
                YearProjection(
                    year=year,
                    revenue=round(revenue, 2),
                    revenue_growth=round(growth, 4),
                    ebitda=round(ebitda, 2),
                    ebitda_margin=round(margin, 4),
                    depreciation=round(depreciation, 2),
                    ebit=round(ebit, 2),
                    taxes=round(taxes, 2),
                    nopat=round(nopat, 2),
                    capex=round(capex, 2),
                    nwc_change=round(nwc_change, 2),
                    fcf=round(fcf, 2),
                    discount_factor=round(discount_factor, 6),
                    pv_fcf=round(pv_fcf, 2),
                )
            )
            prev_revenue = revenue

        # Terminal value (Gordon Growth)
        terminal_fcf = projections[-1].fcf
        spread = a.wacc - a.terminal_growth
        if spread <= 0:
            # Gordon Growth model is invalid when tgr >= wacc.
            # Use a very large terminal value to signal the problem.
            tv = terminal_fcf * 1000.0 if terminal_fcf != 0 else 0.0
        else:
            tv = terminal_fcf * (1.0 + a.terminal_growth) / spread
        pv_tv = tv / (1.0 + a.wacc) ** a.projection_years

        sum_pv_fcf = sum(p.pv_fcf for p in projections)
        ev = sum_pv_fcf + pv_tv
        equity_value = ev - a.net_debt
        per_share = equity_value / a.shares_outstanding

        implied_exit = tv / terminal_fcf if terminal_fcf != 0 else 0.0
        tv_pct = (pv_tv / ev * 100.0) if ev != 0 else 0.0

        terminal = TerminalValue(
            terminal_fcf=round(terminal_fcf, 2),
            growth_rate=a.terminal_growth,
            terminal_value=round(tv, 2),
            pv_terminal=round(pv_tv, 2),
            implied_exit_multiple=round(implied_exit, 2),
            tv_as_pct_of_ev=round(tv_pct, 2),
        )

        valuation = ValuationSummary(
            ev=round(ev, 2),
            equity_value=round(equity_value, 2),
            equity_value_per_share=round(per_share, 2),
            tv_as_pct_of_ev=round(tv_pct, 2),
            implied_exit_multiple=round(implied_exit, 2),
        )

        return ModelOutput(
            assumptions=a,
            projections=projections,
            terminal_value=terminal,
            valuation=valuation,
        )

    # ------------------------------------------------------------------
    # Scenarios
    # ------------------------------------------------------------------
    def _build_scenarios(self) -> list[ScenarioResult]:
        assert self._assumptions is not None
        results: list[ScenarioResult] = []
        for sc in self._assumptions.scenarios:
            tweaked = self._apply_scenario(self._assumptions, sc)
            out = self._build_core(tweaked)
            key_assumptions: dict[str, object] = {
                "terminal_growth": tweaked.terminal_growth,
            }
            if sc.revenue_growth_override:
                key_assumptions["revenue_growth"] = (
                    sc.revenue_growth_override
                )
            if sc.margin_override:
                key_assumptions["ebitda_margins"] = sc.margin_override
            results.append(
                ScenarioResult(
                    name=sc.name,
                    probability=sc.probability,
                    equity_value_per_share=round(
                        out.valuation.equity_value_per_share, 2
                    ),
                    ev=round(out.valuation.ev, 2),
                    key_assumptions=key_assumptions,
                )
            )
        return results

    @staticmethod
    def _apply_scenario(
        base: ModelAssumptions,
        sc: Any,
    ) -> ModelAssumptions:
        data = base.model_dump()
        if sc.revenue_growth_override is not None:
            data["revenue_growth_by_year"] = list(
                sc.revenue_growth_override
            )
        if sc.margin_override is not None:
            data["ebitda_margin_by_year"] = list(sc.margin_override)
        if sc.terminal_growth_override is not None:
            data["terminal_growth"] = sc.terminal_growth_override
        # Strip scenarios to prevent recursion
        data["scenarios"] = []
        return ModelAssumptions(**data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _tweak(
        assumptions: ModelAssumptions,
        param: str,
        value: float,
    ) -> ModelAssumptions:
        data = assumptions.model_dump()
        if param not in data:
            raise KeyError(f"Unknown assumption field: {param}")
        data[param] = value
        data["scenarios"] = []
        return ModelAssumptions(**data)

    # ------------------------------------------------------------------
    # Markdown rendering
    # ------------------------------------------------------------------
    def _render_markdown(self, out: ModelOutput) -> str:
        a = out.assumptions
        v = out.valuation
        tv = out.terminal_value
        lines: list[str] = []

        # Executive summary
        lines.append(f"# DCF Valuation -- {a.company_name} ({a.ticker})")
        lines.append("")
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(
            f"**Implied equity value per share: "
            f"${v.equity_value_per_share:,.2f}**"
        )
        lines.append(
            f"- Enterprise Value: ${v.ev:,.2f}M"
        )
        lines.append(
            f"- Equity Value: ${v.equity_value:,.2f}M"
        )
        lines.append(
            f"- WACC: {a.wacc:.1%} | Terminal Growth: "
            f"{a.terminal_growth:.1%}"
        )
        lines.append("")

        # Projection table
        lines.append("## Projection Table")
        lines.append("")
        header = (
            "| Year | Revenue ($M) | Growth | EBITDA ($M) "
            "| Margin | FCF ($M) | PV of FCF ($M) |"
        )
        sep = "|------|-------------|--------|------------|"
        sep += "--------|---------|----------------|"
        lines.append(header)
        lines.append(sep)
        for p in out.projections:
            lines.append(
                f"| {p.year} | {p.revenue:,.1f} "
                f"| {p.revenue_growth:.1%} "
                f"| {p.ebitda:,.1f} | {p.ebitda_margin:.1%} "
                f"| {p.fcf:,.1f} | {p.pv_fcf:,.1f} |"
            )
        lines.append("")

        # Terminal value
        lines.append("## Terminal Value")
        lines.append("")
        lines.append(f"- Method: {tv.method}")
        lines.append(f"- Terminal FCF: ${tv.terminal_fcf:,.2f}M")
        lines.append(
            f"- Terminal Value: ${tv.terminal_value:,.2f}M"
        )
        lines.append(
            f"- PV of Terminal Value: ${tv.pv_terminal:,.2f}M"
        )
        lines.append(
            f"- Implied Exit Multiple: {tv.implied_exit_multiple:.1f}x"
        )
        lines.append(
            f"- TV as % of EV: {tv.tv_as_pct_of_ev:.1f}%"
        )
        lines.append("")

        # Scenario analysis
        if out.scenarios:
            lines.append("## Scenario Analysis")
            lines.append("")
            lines.append(
                "| Scenario | Probability | EV ($M) "
                "| Equity/Share |"
            )
            lines.append(
                "|----------|------------|---------|"
                "-------------|"
            )
            for s in out.scenarios:
                lines.append(
                    f"| {s.name} | {s.probability:.0%} "
                    f"| {s.ev:,.1f} | ${s.equity_value_per_share:,.2f} |"
                )
            weighted = sum(
                s.probability * s.equity_value_per_share
                for s in out.scenarios
            )
            lines.append(
                f"| **Weighted** | 100% | -- "
                f"| **${weighted:,.2f}** |"
            )
            lines.append("")

        # Validation
        issues = validate(out)
        if issues:
            lines.append("## Validation Issues")
            lines.append("")
            for iss in issues:
                tag = "WARNING" if iss.severity == "warning" else "ERROR"
                lines.append(
                    f"- **[{tag}]** {iss.dimension}: {iss.message}"
                )
            lines.append("")

        return "\n".join(lines)

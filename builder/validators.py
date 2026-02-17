"""Sanity checks for DCF model outputs."""
from __future__ import annotations

from builder.outputs import ModelOutput, ValidationIssue

# Sector-level WACC benchmarks: (low, high)
SECTOR_WACC_BENCHMARKS: dict[str, tuple[float, float]] = {
    "Technology": (0.08, 0.12),
    "Healthcare": (0.08, 0.11),
    "Financial Services": (0.08, 0.12),
    "Consumer Staples": (0.06, 0.09),
    "Consumer Discretionary": (0.07, 0.11),
    "Industrials": (0.07, 0.10),
    "Energy": (0.08, 0.12),
    "Real Estate": (0.06, 0.09),
    "Utilities": (0.05, 0.08),
    "Materials": (0.07, 0.10),
    "Communication Services": (0.07, 0.11),
}


def validate(output: ModelOutput) -> list[ValidationIssue]:
    """Run all validation checks and return issues found.

    Parameters
    ----------
    output:
        A fully built :class:`ModelOutput`.

    Returns
    -------
    list[ValidationIssue]
        Zero or more warnings / errors sorted by severity.
    """
    issues: list[ValidationIssue] = []
    a = output.assumptions
    tv = output.terminal_value

    # 1. Terminal growth > long-term GDP (~3%)
    if a.terminal_growth > 0.03:
        issues.append(
            ValidationIssue(
                severity="warning",
                dimension="Terminal Growth",
                message=(
                    f"Terminal growth rate {a.terminal_growth:.1%} "
                    "exceeds long-term GDP growth (~3%)."
                ),
                threshold="3.0%",
            )
        )

    # 2. Terminal growth >= WACC (model breaks)
    if a.terminal_growth >= a.wacc:
        issues.append(
            ValidationIssue(
                severity="error",
                dimension="Terminal Growth",
                message=(
                    f"Terminal growth {a.terminal_growth:.1%} >= "
                    f"WACC {a.wacc:.1%}. "
                    "Gordon Growth model is invalid."
                ),
                threshold=f"< {a.wacc:.1%}",
            )
        )

    # 3. TV as % of EV > 85%
    if tv.tv_as_pct_of_ev > 85.0:
        issues.append(
            ValidationIssue(
                severity="warning",
                dimension="Terminal Value Weight",
                message=(
                    f"Terminal value is {tv.tv_as_pct_of_ev:.1f}% of EV. "
                    "Model is overly dependent on terminal assumptions."
                ),
                threshold="<= 85%",
            )
        )

    # 4. TV as % of EV < 40%
    if tv.tv_as_pct_of_ev < 40.0:
        issues.append(
            ValidationIssue(
                severity="warning",
                dimension="Terminal Value Weight",
                message=(
                    f"Terminal value is only "
                    f"{tv.tv_as_pct_of_ev:.1f}% of EV "
                    "(unusually low)."
                ),
                threshold=">= 40%",
            )
        )

    # 5. WACC outside sector benchmark range
    sector = a.sector
    if sector in SECTOR_WACC_BENCHMARKS:
        lo, hi = SECTOR_WACC_BENCHMARKS[sector]
        if a.wacc < lo or a.wacc > hi:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    dimension="WACC",
                    message=(
                        f"WACC {a.wacc:.1%} is outside the "
                        f"{sector} benchmark range "
                        f"({lo:.0%}-{hi:.0%})."
                    ),
                    threshold=f"{lo:.0%}-{hi:.0%}",
                )
            )

    # 6. Implied exit multiple > 30x
    if tv.implied_exit_multiple > 30.0:
        issues.append(
            ValidationIssue(
                severity="warning",
                dimension="Exit Multiple",
                message=(
                    f"Implied exit multiple of "
                    f"{tv.implied_exit_multiple:.1f}x "
                    "is unusually high."
                ),
                threshold="<= 30x",
            )
        )

    # 7. Revenue growth in any year > 30%
    for p in output.projections:
        if p.revenue_growth > 0.30:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    dimension="Revenue Growth",
                    message=(
                        f"Year {p.year} revenue growth of "
                        f"{p.revenue_growth:.1%} exceeds 30%."
                    ),
                    threshold="<= 30%",
                )
            )

    # 8. Margin expansion > 500 bps in any year
    margins = [p.ebitda_margin for p in output.projections]
    for i in range(1, len(margins)):
        expansion = margins[i] - margins[i - 1]
        if expansion > 0.05:
            yr = output.projections[i].year
            issues.append(
                ValidationIssue(
                    severity="warning",
                    dimension="Margin Expansion",
                    message=(
                        f"Year {yr} EBITDA margin expands "
                        f"{expansion:.0%} vs. prior year "
                        "(> 500 bps)."
                    ),
                    threshold="<= 500 bps/yr",
                )
            )

    # 9. FCF negative in final projection year
    if output.projections and output.projections[-1].fcf < 0:
        issues.append(
            ValidationIssue(
                severity="warning",
                dimension="Free Cash Flow",
                message=(
                    "FCF is negative in the final projection year "
                    f"({output.projections[-1].year}). "
                    "Terminal value may be invalid."
                ),
                threshold=">= 0",
            )
        )

    return issues

"""End-to-end DCF valuation of a hypothetical SaaS company."""
from __future__ import annotations

from builder.assumptions import ModelAssumptions, ScenarioAssumption
from builder.dcf_builder import DCFModelBuilder
from builder.validators import validate


def main() -> None:
    # Define assumptions for "CloudMetrics Inc."
    assumptions = ModelAssumptions(
        company_name="CloudMetrics Inc.",
        ticker="CLDM",
        sector="Technology",
        revenue_base=500.0,  # $500M
        revenue_growth_by_year=[
            0.25, 0.22, 0.18, 0.15, 0.12, 0.10, 0.08,
        ],
        ebitda_margin_by_year=[
            0.20, 0.22, 0.24, 0.26, 0.28, 0.29, 0.30,
        ],
        wacc=0.10,
        terminal_growth=0.03,
        shares_outstanding=100.0,
        net_debt=-200.0,  # Net cash
        scenarios=[
            ScenarioAssumption(
                name="Bull",
                probability=0.25,
                terminal_growth_override=0.035,
                description="Accelerated enterprise adoption",
            ),
            ScenarioAssumption(
                name="Base",
                probability=0.50,
                description="Steady execution",
            ),
            ScenarioAssumption(
                name="Bear",
                probability=0.25,
                revenue_growth_override=[
                    0.18, 0.15, 0.12, 0.10, 0.08, 0.06, 0.05,
                ],
                description="Competitive pressure",
            ),
        ],
    )

    builder = DCFModelBuilder()
    builder.set_assumptions(assumptions)
    output = builder.build()

    # Validate
    issues = validate(output)
    for issue in issues:
        print(
            f"[{issue.severity}] {issue.dimension}: "
            f"{issue.message}"
        )

    # Sensitivity
    grid = builder.sensitivity_table(
        "wacc",
        "terminal_growth",
        [0.08, 0.09, 0.10, 0.11, 0.12],
        [0.02, 0.025, 0.03, 0.035, 0.04],
    )
    print(f"\nSensitivity grid shape: {len(grid.grid)}x"
          f"{len(grid.grid[0])}")
    print(f"Base value: ${grid.base_value}")

    # Output
    print("\n" + builder.to_markdown())


if __name__ == "__main__":
    main()

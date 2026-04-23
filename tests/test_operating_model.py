"""Tests for the operating model builder."""
from __future__ import annotations

import pytest

from builder.operating_model import (
    CostStructure,
    OperatingAssumptions,
    OperatingModelBuilder,
    Segment,
    WorkingCapitalDrivers,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
def _sample_assumptions(
    projection_years: int = 3,
) -> OperatingAssumptions:
    return OperatingAssumptions(
        company_name="OpCo",
        projection_years=projection_years,
        segments=[
            Segment(
                name="Product A",
                units_base=1000.0,
                unit_growth_by_year=[0.10, 0.08, 0.05],
                asp_base=100.0,
                asp_growth=0.02,
            ),
            Segment(
                name="Product B",
                units_base=500.0,
                unit_growth_by_year=[0.20, 0.15, 0.10],
                asp_base=200.0,
                asp_growth=0.03,
            ),
        ],
        cost_structure=CostStructure(
            cogs_pct=0.40,
            sga_pct=0.15,
            rnd_pct=0.10,
            interest_expense=5.0,
            tax_rate=0.25,
        ),
        working_capital_drivers=WorkingCapitalDrivers(
            dso=45.0,
            dio=30.0,
            dpo=40.0,
        ),
    )


@pytest.fixture()
def assumptions() -> OperatingAssumptions:
    return _sample_assumptions()


@pytest.fixture()
def op_builder(
    assumptions: OperatingAssumptions,
) -> OperatingModelBuilder:
    b = OperatingModelBuilder(assumptions)
    return b


# ==================================================================
# TestOperatingModel
# ==================================================================
class TestOperatingModel:
    """Operating model builder tests."""

    def test_revenue_buildup(
        self, op_builder: OperatingModelBuilder
    ) -> None:
        out = op_builder.build()
        yr1 = out.years[0]
        # Product A: 1000 * 1.10 * (100*1.02) = 1100 * 102 = 112200
        # Product B: 500 * 1.20 * (200*1.03) = 600 * 206 = 123600
        assert yr1.total_revenue == pytest.approx(
            yr1.segment_revenues["Product A"]
            + yr1.segment_revenues["Product B"],
            rel=1e-4,
        )
        assert yr1.total_revenue > 0

    def test_margin_waterfall(
        self, op_builder: OperatingModelBuilder
    ) -> None:
        out = op_builder.build()
        yr1 = out.years[0]
        rev = yr1.total_revenue
        assert yr1.cogs == pytest.approx(rev * 0.40, rel=1e-4)
        assert yr1.gross_profit == pytest.approx(
            rev - yr1.cogs, rel=1e-4
        )
        assert yr1.sga == pytest.approx(rev * 0.15, rel=1e-4)
        assert yr1.rnd == pytest.approx(rev * 0.10, rel=1e-4)
        assert yr1.ebit == pytest.approx(
            yr1.gross_profit - yr1.sga - yr1.rnd, rel=1e-4
        )

    def test_working_capital(
        self, op_builder: OperatingModelBuilder
    ) -> None:
        out = op_builder.build()
        yr1 = out.years[0]
        expected_recv = yr1.total_revenue * 45.0 / 365.0
        expected_inv = yr1.cogs * 30.0 / 365.0
        expected_pay = yr1.cogs * 40.0 / 365.0
        assert yr1.receivables == pytest.approx(
            expected_recv, rel=1e-3
        )
        assert yr1.inventory == pytest.approx(
            expected_inv, rel=1e-3
        )
        assert yr1.payables == pytest.approx(
            expected_pay, rel=1e-3
        )
        assert yr1.net_working_capital == pytest.approx(
            expected_recv + expected_inv - expected_pay, rel=1e-3
        )

    def test_to_markdown(
        self, op_builder: OperatingModelBuilder
    ) -> None:
        op_builder.build()
        md = op_builder.to_markdown()
        assert "## Revenue Build-Up" in md
        assert "## Margin Waterfall" in md
        assert "## Working Capital Summary" in md
        assert "Product A" in md
        assert "Product B" in md

    def test_single_segment(self) -> None:
        a = OperatingAssumptions(
            projection_years=3,
            segments=[
                Segment(
                    name="Only",
                    units_base=100.0,
                    unit_growth_by_year=[0.05, 0.05, 0.05],
                    asp_base=50.0,
                ),
            ],
        )
        b = OperatingModelBuilder(a)
        out = b.build()
        assert len(out.years) == 3
        assert out.years[0].total_revenue > 0

    def test_tax_floor_zero(self) -> None:
        """If EBT is negative, taxes should be zero."""
        a = OperatingAssumptions(
            projection_years=3,
            segments=[
                Segment(
                    name="LossCo",
                    units_base=10.0,
                    unit_growth_by_year=[0.0, 0.0, 0.0],
                    asp_base=1.0,
                ),
            ],
            cost_structure=CostStructure(
                # Sum (0.70 + 0.15 + 0.10) = 0.95, within bounds.
                # High interest_expense drives EBT negative so tax
                # floor kicks in regardless of EBIT sign.
                cogs_pct=0.70,
                sga_pct=0.15,
                rnd_pct=0.10,
                interest_expense=100.0,
                tax_rate=0.25,
            ),
        )
        b = OperatingModelBuilder(a)
        out = b.build()
        for yr in out.years:
            assert yr.taxes == 0.0

    def test_revenue_grows_over_time(
        self, op_builder: OperatingModelBuilder
    ) -> None:
        out = op_builder.build()
        for i in range(1, len(out.years)):
            assert (
                out.years[i].total_revenue
                > out.years[i - 1].total_revenue
            )

    def test_build_without_assumptions_raises(self) -> None:
        b = OperatingModelBuilder()
        with pytest.raises(RuntimeError):
            b.build()

    def test_asp_compounds_each_year(self) -> None:
        """ASP must compound at (1+g)^N, not stick at year-1 level."""
        a = OperatingAssumptions(
            projection_years=3,
            segments=[
                Segment(
                    name="S",
                    units_base=100.0,
                    unit_growth_by_year=[0.0, 0.0, 0.0],
                    asp_base=100.0,
                    asp_growth=0.10,
                ),
            ],
        )
        out = OperatingModelBuilder(a).build()
        # units constant at 100; rev = 100 * 100*(1.1)^N
        assert out.years[0].total_revenue == pytest.approx(
            100 * 110.00, rel=1e-4
        )
        assert out.years[1].total_revenue == pytest.approx(
            100 * 121.00, rel=1e-4
        )
        assert out.years[2].total_revenue == pytest.approx(
            100 * 133.10, rel=1e-4
        )

    def test_asp_growth_out_of_bounds_rejected(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Segment(
                name="X",
                units_base=1.0,
                unit_growth_by_year=[0.0],
                asp_base=1.0,
                asp_growth=1.5,  # > 1.0 -> reject
            )

    def test_unit_growth_out_of_bounds_rejected(self) -> None:
        from pydantic import ValidationError
        # 10 as a unit-growth rate = 1000% — likely a unit error.
        with pytest.raises(ValidationError):
            Segment(
                name="X",
                units_base=1.0,
                unit_growth_by_year=[10.0],
                asp_base=1.0,
            )

    def test_cost_pct_above_one_rejected(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CostStructure(cogs_pct=1.2)

    def test_cost_pct_negative_rejected(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CostStructure(sga_pct=-0.1)

    def test_cost_pcts_sum_above_one_rejected(self) -> None:
        from pydantic import ValidationError
        # 0.50 + 0.30 + 0.25 = 1.05 > 1.0 → structurally negative EBIT
        with pytest.raises(ValidationError):
            CostStructure(cogs_pct=0.50, sga_pct=0.30, rnd_pct=0.25)

    def test_cost_pcts_sum_exactly_one_allowed(self) -> None:
        # 0.50 + 0.30 + 0.20 = 1.0 is the edge of allowed
        cs = CostStructure(cogs_pct=0.50, sga_pct=0.30, rnd_pct=0.20)
        assert cs.cogs_pct == 0.50

    def test_dso_above_365_rejected(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            WorkingCapitalDrivers(dso=400.0)

    def test_dso_negative_rejected(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            WorkingCapitalDrivers(dso=-5.0)

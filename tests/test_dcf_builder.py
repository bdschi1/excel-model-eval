"""Comprehensive tests for the DCF model builder."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from builder.assumptions import ModelAssumptions, ScenarioAssumption
from builder.dcf_builder import DCFModelBuilder
from builder.outputs import ModelOutput


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
def _base_kwargs(
    projection_years: int = 5,
    **overrides: object,
) -> dict:
    """Return a minimal valid set of ModelAssumptions kwargs."""
    defaults: dict = dict(
        company_name="TestCo",
        ticker="TST",
        sector="Technology",
        revenue_base=1000.0,
        revenue_growth_by_year=[0.10] * projection_years,
        ebitda_margin_by_year=[0.20] * projection_years,
        wacc=0.10,
        terminal_growth=0.03,
        shares_outstanding=100.0,
        net_debt=200.0,
        projection_years=projection_years,
    )
    defaults.update(overrides)
    return defaults


def _make_assumptions(**overrides: object) -> ModelAssumptions:
    return ModelAssumptions(**_base_kwargs(**overrides))


@pytest.fixture()
def base_assumptions() -> ModelAssumptions:
    return _make_assumptions()


@pytest.fixture()
def builder(base_assumptions: ModelAssumptions) -> DCFModelBuilder:
    b = DCFModelBuilder()
    b.set_assumptions(base_assumptions)
    return b


# ==================================================================
# TestModelAssumptions
# ==================================================================
class TestModelAssumptions:
    """Pydantic schema validation tests."""

    def test_valid_assumptions(self) -> None:
        a = _make_assumptions()
        assert a.company_name == "TestCo"
        assert a.projection_years == 5

    def test_wacc_out_of_range_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_assumptions(wacc=0.02)
        with pytest.raises(ValidationError):
            _make_assumptions(wacc=0.30)

    def test_terminal_growth_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_assumptions(terminal_growth=-0.01)

    def test_growth_list_length_mismatch_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_assumptions(
                revenue_growth_by_year=[0.10, 0.10],
                projection_years=5,
            )

    def test_margin_list_length_mismatch_raises(self) -> None:
        with pytest.raises(ValidationError):
            _make_assumptions(
                ebitda_margin_by_year=[0.20, 0.20],
                projection_years=5,
            )

    def test_scenario_probabilities_sum(self) -> None:
        with pytest.raises(ValidationError):
            _make_assumptions(
                scenarios=[
                    ScenarioAssumption(
                        name="A", probability=0.5
                    ),
                    ScenarioAssumption(
                        name="B", probability=0.3
                    ),
                ]
            )

    def test_defaults(self) -> None:
        a = _make_assumptions()
        assert a.base_year == 2024
        assert a.da_pct == 0.03
        assert a.capex_pct == 0.05
        assert a.nwc_change_pct == 0.01
        assert a.tax_rate == 0.25

    def test_projection_years_range(self) -> None:
        with pytest.raises(ValidationError):
            _make_assumptions(
                projection_years=2,
                revenue_growth_by_year=[0.10, 0.10],
                ebitda_margin_by_year=[0.20, 0.20],
            )

    def test_scenario_override_length_mismatch(self) -> None:
        with pytest.raises(ValidationError):
            _make_assumptions(
                scenarios=[
                    ScenarioAssumption(
                        name="Bad",
                        probability=1.0,
                        revenue_growth_override=[0.05, 0.05],
                    ),
                ]
            )


# ==================================================================
# TestDCFBuilder
# ==================================================================
class TestDCFBuilder:
    """Core DCF calculation tests."""

    def test_basic_build_returns_output(
        self, builder: DCFModelBuilder
    ) -> None:
        output = builder.build()
        assert isinstance(output, ModelOutput)
        assert len(output.projections) == 5

    def test_revenue_projection_grows_correctly(
        self, builder: DCFModelBuilder
    ) -> None:
        output = builder.build()
        # Base=1000, growth=10% => year 1 = 1100
        assert output.projections[0].revenue == pytest.approx(
            1100.0, rel=1e-4
        )
        # year 2 = 1100 * 1.10 = 1210
        assert output.projections[1].revenue == pytest.approx(
            1210.0, rel=1e-4
        )

    def test_ebitda_margin_applied(
        self, builder: DCFModelBuilder
    ) -> None:
        output = builder.build()
        p = output.projections[0]
        assert p.ebitda == pytest.approx(
            p.revenue * 0.20, rel=1e-4
        )

    def test_fcf_calculation(self) -> None:
        """Verify exact FCF with known inputs.

        revenue=1000 (base) => year-1 revenue = 1000*(1+0) = 1000
        margin=0.2 => ebitda=200
        da=0.03 => depreciation=30
        ebit = 200-30 = 170
        tax=0.25 => taxes=42.5
        nopat = 127.5
        capex=0.05 => 50
        nwc_change=0.01 * (1000-1000) = 0 (same revenue since 0 growth)
        fcf = 127.5 + 30 - 50 - 0 = 107.5
        """
        a = _make_assumptions(
            revenue_base=1000.0,
            revenue_growth_by_year=[0.0] * 5,
            ebitda_margin_by_year=[0.20] * 5,
        )
        b = DCFModelBuilder()
        b.set_assumptions(a)
        out = b.build()
        assert out.projections[0].fcf == pytest.approx(
            107.5, rel=1e-4
        )

    def test_terminal_value_gordon_growth(
        self, builder: DCFModelBuilder
    ) -> None:
        output = builder.build()
        tv = output.terminal_value
        expected_tv = (
            tv.terminal_fcf * (1 + 0.03) / (0.10 - 0.03)
        )
        assert tv.terminal_value == pytest.approx(
            expected_tv, rel=1e-3
        )

    def test_terminal_value_with_zero_growth(self) -> None:
        a = _make_assumptions(terminal_growth=0.0)
        b = DCFModelBuilder()
        b.set_assumptions(a)
        out = b.build()
        tv = out.terminal_value
        # TV = FCF * (1+0) / (wacc - 0) = FCF / wacc
        expected = tv.terminal_fcf / 0.10
        assert tv.terminal_value == pytest.approx(
            expected, rel=1e-3
        )

    def test_discount_factor_year_1(
        self, builder: DCFModelBuilder
    ) -> None:
        output = builder.build()
        expected = 1.0 / (1.0 + 0.10)
        assert output.projections[0].discount_factor == pytest.approx(
            expected, rel=1e-4
        )

    def test_pv_sums_to_ev(
        self, builder: DCFModelBuilder
    ) -> None:
        output = builder.build()
        sum_pv = sum(p.pv_fcf for p in output.projections)
        expected_ev = sum_pv + output.terminal_value.pv_terminal
        assert output.valuation.ev == pytest.approx(
            expected_ev, rel=1e-2
        )

    def test_equity_value(
        self, builder: DCFModelBuilder
    ) -> None:
        output = builder.build()
        expected = output.valuation.ev - 200.0  # net_debt
        assert output.valuation.equity_value == pytest.approx(
            expected, rel=1e-2
        )

    def test_per_share_value(
        self, builder: DCFModelBuilder
    ) -> None:
        output = builder.build()
        expected = output.valuation.equity_value / 100.0
        assert output.valuation.equity_value_per_share == pytest.approx(
            expected, rel=1e-2
        )

    def test_tv_pct_of_ev(
        self, builder: DCFModelBuilder
    ) -> None:
        output = builder.build()
        pv_tv = output.terminal_value.pv_terminal
        ev = output.valuation.ev
        expected_pct = pv_tv / ev * 100.0
        assert output.valuation.tv_as_pct_of_ev == pytest.approx(
            expected_pct, rel=1e-1
        )

    def test_implied_exit_multiple(
        self, builder: DCFModelBuilder
    ) -> None:
        output = builder.build()
        tv = output.terminal_value
        expected = tv.terminal_value / tv.terminal_fcf
        assert tv.implied_exit_multiple == pytest.approx(
            expected, rel=1e-2
        )

    def test_sensitivity_grid_shape(
        self, builder: DCFModelBuilder
    ) -> None:
        grid = builder.sensitivity_table(
            "wacc", "terminal_growth",
            [0.08, 0.10, 0.12],
            [0.02, 0.03, 0.04],
        )
        assert len(grid.grid) == 3
        assert all(len(row) == 3 for row in grid.grid)

    def test_sensitivity_grid_base_value_in_center(
        self, builder: DCFModelBuilder
    ) -> None:
        grid = builder.sensitivity_table(
            "wacc", "terminal_growth",
            [0.08, 0.10, 0.12],
            [0.02, 0.03, 0.04],
        )
        # Center cell should equal the base value
        center_val = grid.grid[1][1]
        assert center_val == pytest.approx(
            grid.base_value, rel=1e-2
        )

    def test_scenario_weighted_value(self) -> None:
        a = _make_assumptions(
            scenarios=[
                ScenarioAssumption(
                    name="Bull",
                    probability=0.25,
                    terminal_growth_override=0.04,
                ),
                ScenarioAssumption(
                    name="Base", probability=0.50
                ),
                ScenarioAssumption(
                    name="Bear",
                    probability=0.25,
                    terminal_growth_override=0.01,
                ),
            ]
        )
        b = DCFModelBuilder()
        b.set_assumptions(a)
        out = b.build()
        assert len(out.scenarios) == 3
        total_prob = sum(s.probability for s in out.scenarios)
        assert total_prob == pytest.approx(1.0, abs=0.01)

    def test_scenario_uses_overrides(self) -> None:
        a = _make_assumptions(
            scenarios=[
                ScenarioAssumption(
                    name="High",
                    probability=0.5,
                    terminal_growth_override=0.04,
                ),
                ScenarioAssumption(
                    name="Low",
                    probability=0.5,
                    terminal_growth_override=0.01,
                ),
            ]
        )
        b = DCFModelBuilder()
        b.set_assumptions(a)
        out = b.build()
        high = [s for s in out.scenarios if s.name == "High"][0]
        low = [s for s in out.scenarios if s.name == "Low"][0]
        assert high.equity_value_per_share > low.equity_value_per_share

    def test_to_markdown_contains_tables(
        self, builder: DCFModelBuilder
    ) -> None:
        builder.build()
        md = builder.to_markdown()
        assert "## Projection Table" in md
        assert "|" in md

    def test_to_markdown_contains_summary(
        self, builder: DCFModelBuilder
    ) -> None:
        builder.build()
        md = builder.to_markdown()
        assert "Executive Summary" in md
        assert "Enterprise Value" in md

    def test_build_without_assumptions_raises(self) -> None:
        b = DCFModelBuilder()
        with pytest.raises(RuntimeError, match="set_assumptions"):
            b.build()

    def test_set_assumptions_wrong_type_raises(self) -> None:
        b = DCFModelBuilder()
        with pytest.raises(TypeError):
            b.set_assumptions({"not": "valid"})

    def test_net_cash_increases_equity(self) -> None:
        """Negative net_debt (net cash) should increase equity."""
        a_debt = _make_assumptions(net_debt=200.0)
        a_cash = _make_assumptions(net_debt=-200.0)
        b1 = DCFModelBuilder()
        b1.set_assumptions(a_debt)
        b2 = DCFModelBuilder()
        b2.set_assumptions(a_cash)
        out1 = b1.build()
        out2 = b2.build()
        # EV is the same (same operating assumptions)
        assert out1.valuation.ev == pytest.approx(
            out2.valuation.ev, rel=1e-4
        )
        # But equity/share is much higher with net cash
        assert (
            out2.valuation.equity_value_per_share
            > out1.valuation.equity_value_per_share
        )

"""Tests for the DCF validation rules."""
from __future__ import annotations

import pytest

from builder.assumptions import ModelAssumptions
from builder.dcf_builder import DCFModelBuilder
from builder.outputs import ValidationIssue
from builder.validators import validate


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _build_output(**overrides: object):
    """Build a ModelOutput with optional assumption overrides."""
    n = overrides.pop("projection_years", 5)
    defaults = dict(
        company_name="TestCo",
        ticker="TST",
        sector="Technology",
        revenue_base=1000.0,
        revenue_growth_by_year=[0.10] * n,
        ebitda_margin_by_year=[0.20] * n,
        wacc=0.10,
        terminal_growth=0.025,
        shares_outstanding=100.0,
        net_debt=200.0,
        projection_years=n,
    )
    defaults.update(overrides)
    a = ModelAssumptions(**defaults)
    b = DCFModelBuilder()
    b.set_assumptions(a)
    return b.build()


def _has_issue(
    issues: list[ValidationIssue],
    dimension: str,
    severity: str | None = None,
) -> bool:
    for i in issues:
        if dimension.lower() in i.dimension.lower():
            if severity is None or i.severity == severity:
                return True
    return False


# ==================================================================
# TestValidators
# ==================================================================
class TestValidators:
    """Validation rule tests."""

    def test_valid_model_no_issues(self) -> None:
        out = _build_output(
            wacc=0.10,
            terminal_growth=0.025,
        )
        issues = validate(out)
        # There should be no errors. Warnings are acceptable
        # if the model happens to trigger threshold checks.
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_terminal_growth_exceeds_gdp_warning(self) -> None:
        out = _build_output(terminal_growth=0.04)
        issues = validate(out)
        assert _has_issue(issues, "Terminal Growth", "warning")

    def test_terminal_growth_exceeds_wacc_error(self) -> None:
        # tg >= wacc is rejected at construction (Pydantic), not at validate()
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _build_output(wacc=0.04, terminal_growth=0.04)

    def test_tv_pct_too_high_warning(self) -> None:
        # Very low near-term FCF + high terminal => high TV%
        # Use tiny margins so near-term FCF is low
        out = _build_output(
            ebitda_margin_by_year=[0.06] * 5,
            terminal_growth=0.04,
            wacc=0.05,
        )
        issues = validate(out)
        assert _has_issue(
            issues, "Terminal Value Weight", "warning"
        )

    def test_wacc_outside_sector_range(self) -> None:
        # Technology benchmark is 0.08..0.12
        out = _build_output(wacc=0.05, terminal_growth=0.02)
        issues = validate(out)
        assert _has_issue(issues, "WACC", "warning")

    def test_implied_multiple_too_high(self) -> None:
        # Very high terminal_growth relative to wacc
        # => large implied multiple
        out = _build_output(
            wacc=0.05,
            terminal_growth=0.045,
        )
        issues = validate(out)
        assert _has_issue(issues, "Exit Multiple", "warning")

    def test_negative_fcf_error(self) -> None:
        # Tiny margins => negative terminal FCF; Gordon Growth is
        # undefined so severity is error, not warning.
        out = _build_output(
            ebitda_margin_by_year=[0.02] * 5,
            revenue_growth_by_year=[0.0] * 5,
        )
        if out.projections[-1].fcf <= 0:
            issues = validate(out)
            assert _has_issue(
                issues, "Free Cash Flow", "error"
            )
        else:
            pytest.skip("FCF not negative with these params")

    def test_terminal_fcf_clamped_to_zero(self) -> None:
        # When terminal_fcf <= 0, TV and PV(TV) are clamped to 0.
        out = _build_output(
            ebitda_margin_by_year=[0.02] * 5,
            revenue_growth_by_year=[0.0] * 5,
        )
        if out.projections[-1].fcf <= 0:
            assert out.terminal_value.terminal_value == 0.0
            assert out.terminal_value.pv_terminal == 0.0
        else:
            pytest.skip("FCF not negative with these params")

    def test_ev_negative_error(self) -> None:
        # Extremely negative FCFs across projections push EV below 0.
        # With terminal_fcf <= 0 the TV component is clamped to 0, so
        # if the sum of PV(FCF) is deeply negative, EV < 0.
        out = _build_output(
            ebitda_margin_by_year=[-0.50] * 5,
            revenue_growth_by_year=[0.0] * 5,
        )
        if out.valuation.ev < 0:
            issues = validate(out)
            assert _has_issue(
                issues, "Enterprise Value", "error"
            )
        else:
            pytest.skip("EV not negative with these params")

    def test_equity_per_share_negative_error(self) -> None:
        # Positive but small EV combined with huge net_debt drives
        # equity_value_per_share below 0.
        out = _build_output(
            net_debt=100_000.0,
        )
        if out.valuation.equity_value_per_share < 0:
            issues = validate(out)
            assert _has_issue(
                issues, "Equity Value", "error"
            )
        else:
            pytest.skip("Equity per share not negative with these params")

    def test_high_revenue_growth_warning(self) -> None:
        out = _build_output(
            revenue_growth_by_year=[0.35, 0.10, 0.10, 0.10, 0.10],
        )
        issues = validate(out)
        assert _has_issue(issues, "Revenue Growth", "warning")

    def test_margin_expansion_warning(self) -> None:
        # Jump from 15% to 25% in one year = 1000 bps
        out = _build_output(
            ebitda_margin_by_year=[
                0.15, 0.26, 0.27, 0.28, 0.29,
            ],
        )
        issues = validate(out)
        assert _has_issue(issues, "Margin Expansion", "warning")

    def test_wacc_within_range_no_warning(self) -> None:
        out = _build_output(
            sector="Technology", wacc=0.10
        )
        issues = validate(out)
        wacc_issues = [
            i for i in issues
            if "wacc" in i.dimension.lower()
        ]
        assert len(wacc_issues) == 0

    def test_unknown_sector_no_wacc_warning(self) -> None:
        out = _build_output(sector="Crypto")
        issues = validate(out)
        wacc_issues = [
            i for i in issues
            if "wacc" in i.dimension.lower()
        ]
        assert len(wacc_issues) == 0

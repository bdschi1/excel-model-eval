"""Tests for the comparable-company analysis builder."""
from __future__ import annotations

import pytest

from builder.comps_builder import CompsTableBuilder, PeerCompany


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
def _sample_peers() -> list[PeerCompany]:
    return [
        PeerCompany(
            ticker="AAA",
            name="AlphaCo",
            ev_to_ebitda=12.0,
            pe=20.0,
            ev_to_revenue=4.0,
            peg=1.5,
            market_cap=5000.0,
        ),
        PeerCompany(
            ticker="BBB",
            name="BetaCo",
            ev_to_ebitda=14.0,
            pe=22.0,
            ev_to_revenue=5.0,
            peg=1.8,
            market_cap=8000.0,
        ),
        PeerCompany(
            ticker="CCC",
            name="GammaCo",
            ev_to_ebitda=10.0,
            pe=18.0,
            ev_to_revenue=3.0,
            peg=1.2,
            market_cap=3000.0,
        ),
    ]


@pytest.fixture()
def peers() -> list[PeerCompany]:
    return _sample_peers()


@pytest.fixture()
def comps_builder(peers: list[PeerCompany]) -> CompsTableBuilder:
    return CompsTableBuilder(peers=peers)


# ==================================================================
# TestCompsBuilder
# ==================================================================
class TestCompsBuilder:
    """Comps table builder tests."""

    def test_median_calculation(
        self, comps_builder: CompsTableBuilder
    ) -> None:
        stats = comps_builder.build()
        # ev_to_ebitda values: 10, 12, 14 => median = 12
        assert stats["ev_to_ebitda"]["median"] == 12.0

    def test_mean_calculation(
        self, comps_builder: CompsTableBuilder
    ) -> None:
        stats = comps_builder.build()
        # ev_to_ebitda values: 10, 12, 14 => mean = 12.0
        assert stats["ev_to_ebitda"]["mean"] == 12.0
        # pe values: 18, 20, 22 => mean = 20.0
        assert stats["pe"]["mean"] == 20.0

    def test_implied_value_from_ev_ebitda(
        self, comps_builder: CompsTableBuilder
    ) -> None:
        comps_builder.build()
        result = comps_builder.implied_value(
            target_ebitda=100.0,
            target_earnings=50.0,
            target_revenue=500.0,
            shares=100.0,
            net_debt=200.0,
        )
        # median EV/EBITDA = 12, implied EV = 1200
        # equity = 1200 - 200 = 1000, per share = 10.0
        assert result["ev_to_ebitda"] == 10.0

    def test_implied_value_from_pe(
        self, comps_builder: CompsTableBuilder
    ) -> None:
        comps_builder.build()
        result = comps_builder.implied_value(
            target_ebitda=100.0,
            target_earnings=50.0,
            target_revenue=500.0,
            shares=100.0,
            net_debt=200.0,
        )
        # median P/E = 20, implied equity = 20*50 = 1000
        # per share = 1000/100 = 10.0
        assert result["pe"] == 10.0

    def test_implied_value_from_ev_revenue(
        self, comps_builder: CompsTableBuilder
    ) -> None:
        comps_builder.build()
        result = comps_builder.implied_value(
            target_ebitda=100.0,
            target_earnings=50.0,
            target_revenue=500.0,
            shares=100.0,
            net_debt=200.0,
        )
        # median EV/Revenue = 4.0, implied EV = 2000
        # equity = 2000-200 = 1800, per share = 18.0
        assert result["ev_to_revenue"] == 18.0

    def test_to_markdown_format(
        self, comps_builder: CompsTableBuilder
    ) -> None:
        comps_builder.build()
        md = comps_builder.to_markdown()
        assert "## Comparable Company Analysis" in md
        assert "AlphaCo" in md
        assert "Median" in md or "median" in md.lower()

    def test_empty_peers(self) -> None:
        builder = CompsTableBuilder(peers=[])
        stats = builder.build()
        assert stats["ev_to_ebitda"]["median"] is None
        assert stats["pe"]["mean"] is None

    def test_partial_data(self) -> None:
        """Peers with some None multiples."""
        peers = [
            PeerCompany(
                ticker="X",
                name="XCo",
                ev_to_ebitda=15.0,
                pe=None,
            ),
            PeerCompany(
                ticker="Y",
                name="YCo",
                ev_to_ebitda=20.0,
                pe=None,
            ),
        ]
        builder = CompsTableBuilder(peers=peers)
        stats = builder.build()
        assert stats["ev_to_ebitda"]["median"] is not None
        assert stats["pe"]["median"] is None

    def test_implied_value_none_without_target(
        self, comps_builder: CompsTableBuilder
    ) -> None:
        comps_builder.build()
        result = comps_builder.implied_value(
            shares=100.0, net_debt=0.0
        )
        assert result["ev_to_ebitda"] is None
        assert result["pe"] is None

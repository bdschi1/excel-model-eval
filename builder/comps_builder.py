"""Comparable-company analysis builder."""
from __future__ import annotations

import statistics

from pydantic import BaseModel


class PeerCompany(BaseModel):
    """One comparable company with its trading multiples."""

    ticker: str
    name: str
    ev_to_ebitda: float | None = None
    pe: float | None = None
    ev_to_revenue: float | None = None
    peg: float | None = None
    market_cap: float | None = None


class CompsTableBuilder:
    """Build a comps table and derive implied valuations.

    Usage::

        builder = CompsTableBuilder(peers=[...])
        stats = builder.build()
        implied = builder.implied_value(
            target_ebitda=100, target_earnings=50,
            target_revenue=500, shares=100, net_debt=200,
        )
        print(builder.to_markdown())
    """

    def __init__(self, peers: list[PeerCompany] | None = None) -> None:
        self.peers: list[PeerCompany] = peers or []
        self._stats: dict[str, dict[str, float | None]] = {}

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def build(self) -> dict[str, dict[str, float | None]]:
        """Compute median and mean for each multiple.

        Returns
        -------
        dict
            ``{"ev_to_ebitda": {"median": ..., "mean": ...}, ...}``
        """
        metrics = [
            "ev_to_ebitda",
            "pe",
            "ev_to_revenue",
            "peg",
        ]
        self._stats = {}
        for m in metrics:
            vals = [
                getattr(p, m)
                for p in self.peers
                if getattr(p, m) is not None
            ]
            if vals:
                self._stats[m] = {
                    "median": round(statistics.median(vals), 2),
                    "mean": round(statistics.mean(vals), 2),
                }
            else:
                self._stats[m] = {"median": None, "mean": None}
        return self._stats

    # ------------------------------------------------------------------
    # Implied value
    # ------------------------------------------------------------------
    def implied_value(
        self,
        target_ebitda: float | None = None,
        target_earnings: float | None = None,
        target_revenue: float | None = None,
        shares: float = 1.0,
        net_debt: float = 0.0,
    ) -> dict[str, float | None]:
        """Derive implied per-share prices from comps medians.

        Parameters
        ----------
        target_ebitda:
            LTM or NTM EBITDA of the target in $M.
        target_earnings:
            LTM or NTM net income in $M.
        target_revenue:
            LTM or NTM revenue in $M.
        shares:
            Diluted share count in millions.
        net_debt:
            Net debt in $M.

        Returns
        -------
        dict
            Mapping of metric name to implied per-share price.
        """
        if not self._stats:
            self.build()

        result: dict[str, float | None] = {}

        # EV / EBITDA -> implied EV -> equity -> per share
        med_ev_ebitda = self._stats["ev_to_ebitda"]["median"]
        if med_ev_ebitda is not None and target_ebitda is not None:
            implied_ev = med_ev_ebitda * target_ebitda
            result["ev_to_ebitda"] = round(
                (implied_ev - net_debt) / shares, 2
            )
        else:
            result["ev_to_ebitda"] = None

        # P/E -> implied equity -> per share
        med_pe = self._stats["pe"]["median"]
        if med_pe is not None and target_earnings is not None:
            result["pe"] = round(
                med_pe * target_earnings / shares, 2
            )
        else:
            result["pe"] = None

        # EV / Revenue -> implied EV -> equity -> per share
        med_ev_rev = self._stats["ev_to_revenue"]["median"]
        if med_ev_rev is not None and target_revenue is not None:
            implied_ev = med_ev_rev * target_revenue
            result["ev_to_revenue"] = round(
                (implied_ev - net_debt) / shares, 2
            )
        else:
            result["ev_to_revenue"] = None

        return result

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------
    def to_markdown(self) -> str:
        """Render the comps table as Markdown."""
        if not self._stats:
            self.build()

        lines: list[str] = []
        lines.append("## Comparable Company Analysis")
        lines.append("")

        # Peer table
        header = (
            "| Ticker | Name | EV/EBITDA | P/E "
            "| EV/Revenue | PEG | Mkt Cap ($M) |"
        )
        sep = (
            "|--------|------|-----------|-----|"
            "------------|-----|--------------|"
        )
        lines.append(header)
        lines.append(sep)
        for p in self.peers:
            def _fmt(v: float | None) -> str:
                return f"{v:.1f}" if v is not None else "--"

            lines.append(
                f"| {p.ticker} | {p.name} "
                f"| {_fmt(p.ev_to_ebitda)} "
                f"| {_fmt(p.pe)} "
                f"| {_fmt(p.ev_to_revenue)} "
                f"| {_fmt(p.peg)} "
                f"| {_fmt(p.market_cap)} |"
            )
        lines.append("")

        # Summary stats
        lines.append("### Summary Statistics")
        lines.append("")
        lines.append("| Metric | Median | Mean |")
        lines.append("|--------|--------|------|")
        for m, vals in self._stats.items():
            med = vals["median"]
            mn = vals["mean"]
            med_s = f"{med:.2f}" if med is not None else "--"
            mn_s = f"{mn:.2f}" if mn is not None else "--"
            label = m.replace("_", "/").upper()
            lines.append(f"| {label} | {med_s} | {mn_s} |")
        lines.append("")

        return "\n".join(lines)

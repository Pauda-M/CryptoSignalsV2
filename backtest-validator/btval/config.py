from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class Config:
    initial_capital: float = 10_000.0
    # Costs are charged PER SIDE on every unit of turnover. A full flip
    # long->short is turnover 2 and pays twice. (The usual "round-trip fee"
    # label applied per unit of turnover double-counts or half-counts
    # depending on who reads it; per side is unambiguous.)
    fee_bps: float = 5.0
    slippage_bps: float = 3.0
    max_leverage: float = 1.0
    # Bars between the signal being known and the position being held.
    # 1 = trade at the close of the bar the signal was computed on, which is
    # already optimistic; the critic re-runs at lag 2 to see if the edge
    # lives in one bar.
    execution_lag: int = 1
    # None -> inferred from the index spacing (24/7 calendar).
    periods_per_year: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Gates:
    """Thresholds for the three hard gates. Decide them before you look."""
    dsr_min: float = 0.95
    wf_min_positive_fold_ratio: float = 0.6
    # None = auto: the worst fold must be no worse than the worst fold a
    # ZERO-skill strategy would produce across the same number of folds
    # (Bonferroni 5%). A fixed number gets stricter as folds are added and
    # rejects real edges: a 90-day fold's annualized Sharpe has SE ~2.
    wf_min_worst_fold_sharpe: float | None = None
    wf_min_oos_sharpe: float = 0.0
    implausible_sharpe_warn: float = 2.0
    implausible_sharpe_fail: float = 3.0
    lag2_retained_min: float = 0.25  # fraction of lag-1 Sharpe that must survive lag 2

    def to_dict(self) -> dict:
        return asdict(self)

"""Strategy registry. A strategy is a CAUSAL signal function plus a param grid.

Contract:
  signal(prices, **params) -> pd.Series in [-1, 1], same index as prices,
  where value at t uses only prices[:t+1]. The critic verifies this by
  truncation, so lying here gets caught.
"""
from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass, field
from itertools import product
from typing import Callable

import pandas as pd


@dataclass
class Strategy:
    name: str
    signal_fn: Callable[..., pd.Series]
    grid: dict[str, list] = field(default_factory=dict)
    warmup: int = 0  # bars of history the signal needs before it is valid
    mechanism: str = ""  # who is on the other side and why they lose

    def param_sets(self) -> list[dict]:
        if not self.grid:
            return [{}]
        keys = list(self.grid)
        return [dict(zip(keys, vals)) for vals in product(*self.grid.values())]

    def signal(self, prices: pd.Series, **params) -> pd.Series:
        return self.signal_fn(prices, **params)

    def source(self) -> str | None:
        """Module source for the static scan; None when unavailable (REPL, C ext)."""
        try:
            return inspect.getsource(inspect.getmodule(self.signal_fn) or self.signal_fn)
        except (OSError, TypeError):
            return None


_BUILTIN = ["sma_cross", "tsmom"]


def get_strategy(name: str) -> Strategy:
    if name not in _BUILTIN and "." not in name:
        raise KeyError(f"unknown strategy {name!r}; builtins: {_BUILTIN}, or pass a dotted module path")
    mod = importlib.import_module(f"btval.strategies.{name}" if name in _BUILTIN else name)
    return mod.STRATEGY


def list_strategies() -> list[dict]:
    out = []
    for n in _BUILTIN:
        s = get_strategy(n)
        out.append({"name": s.name, "grid": s.grid, "warmup": s.warmup, "mechanism": s.mechanism})
    return out

"""btval — standalone backtest validation.

Generation is free; validation is the job. Nothing in this package imports
from the rest of the trading stack.
"""
from .config import Config
from .engine import backtest
from .metrics import metrics
from .stats import deflated_sharpe, probabilistic_sharpe

__all__ = ["Config", "backtest", "metrics", "deflated_sharpe", "probabilistic_sharpe"]
__version__ = "0.1.0"

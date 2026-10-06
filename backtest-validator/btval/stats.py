"""Multiple-testing correction (Bailey & López de Prado, 2012/2014).

Everything here works on PER-PERIOD Sharpe ratios. Feeding an annualized
Sharpe into the sqrt(T-1) z-score (as most blog versions do) inflates the
statistic by sqrt(periods_per_year) and passes almost anything.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm

EULER_GAMMA = 0.5772156649015329


def _sr_std_err(sr: float, n_obs: int, skew: float, kurtosis: float) -> float:
    var = (1 - skew * sr + (kurtosis - 1) / 4 * sr**2) / (n_obs - 1)
    return float(np.sqrt(max(var, 1e-18)))


def probabilistic_sharpe(sr: float, n_obs: int, skew: float = 0.0,
                         kurtosis: float = 3.0, sr_benchmark: float = 0.0) -> float:
    """P(true per-period SR > sr_benchmark)."""
    if n_obs < 3:
        return float("nan")
    return float(norm.cdf((sr - sr_benchmark) / _sr_std_err(sr, n_obs, skew, kurtosis)))


def expected_max_sharpe(n_trials: int, trials_sr_std: float) -> float:
    """E[max SR] of n_trials independent zero-skill strategies (per period)."""
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")
    if n_trials == 1:
        return 0.0  # the blog formula gives -inf here
    z = (1 - EULER_GAMMA) * norm.ppf(1 - 1 / n_trials) + EULER_GAMMA * norm.ppf(
        1 - 1 / (n_trials * np.e)
    )
    return float(trials_sr_std * z)


def deflated_sharpe(sr: float, n_trials: int, n_obs: int, skew: float = 0.0,
                    kurtosis: float = 3.0, trial_sharpes: list[float] | None = None,
                    threshold: float = 0.95) -> dict:
    """Deflated Sharpe ratio.

    sr: PER-PERIOD Sharpe of the selected (best) strategy.
    n_trials: every variation you ever ran on this data. Be honest.
    trial_sharpes: per-period Sharpes of all trials, if you kept them. Their
        dispersion (floored at the null dispersion) sets the noise bar. Without them we use the null-hypothesis
        dispersion 1/sqrt(T-1), which UNDERSTATES the bar when your trials
        were genuinely different strategies — keep your trial log.
    """
    if n_obs < 3:
        return {"error": "insufficient_data"}
    null_std = 1.0 / np.sqrt(n_obs - 1)
    if trial_sharpes is not None and len(trial_sharpes) >= 2:
        # Floor at the null dispersion: highly correlated trials shrink the
        # observed spread while n_trials still counts them all.
        sr_std = max(float(np.std(trial_sharpes, ddof=1)), null_std)
        n_eff = max(n_trials, len(trial_sharpes))
        source = "trial_log"
    else:
        sr_std = null_std
        n_eff = n_trials
        source = "null_assumption"
    sr0 = expected_max_sharpe(n_eff, sr_std)
    dsr = probabilistic_sharpe(sr, n_obs, skew, kurtosis, sr_benchmark=sr0)
    return {
        "deflated_sharpe": round(dsr, 4),
        "psr_vs_zero": round(probabilistic_sharpe(sr, n_obs, skew, kurtosis), 4),
        "expected_max_sr_per_period": sr0,
        "observed_sr_per_period": sr,
        "n_trials": int(n_eff),
        "n_obs": int(n_obs),
        "dispersion_source": source,
        "verdict": "PASS" if dsr > threshold else "REJECT",
    }


def min_track_record_length(sr: float, skew: float = 0.0, kurtosis: float = 3.0,
                            sr_benchmark: float = 0.0, confidence: float = 0.95) -> float:
    """Bars needed before sr (per period) is distinguishable from sr_benchmark."""
    if sr <= sr_benchmark:
        return float("inf")
    z = norm.ppf(confidence)
    return float(1 + (1 - skew * sr + (kurtosis - 1) / 4 * sr**2) * (z / (sr - sr_benchmark)) ** 2)


def holm_bonferroni(pvalues: list[float], alpha: float = 0.05) -> list[bool]:
    """Step-down Holm: which hypotheses survive family-wise error control."""
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p)
    m = len(p)
    reject = np.zeros(m, dtype=bool)
    for rank, idx in enumerate(order):
        if p[idx] <= alpha / (m - rank):
            reject[idx] = True
        else:
            break
    return reject.tolist()

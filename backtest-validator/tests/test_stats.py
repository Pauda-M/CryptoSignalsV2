import numpy as np
import pytest

from btval.stats import (deflated_sharpe, expected_max_sharpe, holm_bonferroni,
                         min_track_record_length, probabilistic_sharpe)


def test_single_trial_is_finite():
    assert expected_max_sharpe(1, 0.1) == 0.0
    assert np.isfinite(deflated_sharpe(0.05, 1, 1000)["deflated_sharpe"])


def test_noise_bar_rises_with_trials():
    assert expected_max_sharpe(1000, 0.03) > expected_max_sharpe(10, 0.03) > 0


def test_best_of_many_noise_strategies_rejected():
    rng = np.random.default_rng(0)
    T, N = 1000, 200
    srs = [(x := rng.normal(0, 0.02, T)).mean() / x.std(ddof=1) for _ in range(N)]
    best = max(srs)
    assert probabilistic_sharpe(best, T) > 0.95          # looks significant alone
    assert deflated_sharpe(best, N, T, trial_sharpes=srs)["verdict"] == "REJECT"


def test_annualized_input_would_have_passed():
    # The common bug: annualized SR into the per-period formula.
    per_period, T, N = 0.03, 1000, 50
    assert deflated_sharpe(per_period, N, T)["verdict"] == "REJECT"
    assert deflated_sharpe(per_period * np.sqrt(365), N, T)["verdict"] == "PASS"


def test_fat_tails_lower_confidence():
    assert probabilistic_sharpe(0.08, 500, skew=-1, kurtosis=10) < probabilistic_sharpe(0.08, 500)


def test_mintrl():
    assert min_track_record_length(0.0) == float("inf")
    assert min_track_record_length(0.1) < min_track_record_length(0.05)


def test_holm():
    assert holm_bonferroni([0.001, 0.02, 0.04, 0.5]) == [True, False, False, False]

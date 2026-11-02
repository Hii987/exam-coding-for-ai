import math

import numpy as np
import pytest

from analyst import stats


def test_mean_std_known():
    assert stats.mean([1, 2, 3, 4]) == 2.5
    assert stats.std([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(math.sqrt(32 / 7))


def test_single_value_and_empty():
    assert stats.std([5]) == 0.0
    ci = stats.mean_ci([5])
    assert ci["low"] == ci["high"] == 5
    with pytest.raises(ValueError):
        stats.mean_ci([])
    with pytest.raises(ValueError):
        stats.mean([float("nan")])


def test_mean_ci_known():
    # m = 2.5, s = sqrt(5/3), n = 4 -> demi-largeur 1.96 * s / 2
    ci = stats.mean_ci([1, 2, 3, 4])
    half = 1.959963984540054 * math.sqrt(5 / 3) / 2
    assert ci["low"] == pytest.approx(2.5 - half)
    assert ci["high"] == pytest.approx(2.5 + half)


def test_prop_ci_wilson_known():
    ci = stats.prop_ci(50, 100)  # valeurs de référence de Wilson
    assert ci["low"] == pytest.approx(0.4038, abs=1e-4)
    assert ci["high"] == pytest.approx(0.5962, abs=1e-4)
    zero = stats.prop_ci(0, 10)
    assert zero["low"] == pytest.approx(0, abs=1e-12) and 0 < zero["high"] < 1
    with pytest.raises(ValueError):
        stats.prop_ci(3, 0)


def test_diff_means_sign_and_coverage():
    rng = np.random.default_rng(1)
    a, b = rng.normal(10, 1, 5000), rng.normal(8, 1, 5000)
    ci = stats.diff_means_ci(a, b)
    assert ci["low"] < 2 < ci["high"]


def test_bootstrap_contains_median_and_is_reproducible():
    x = np.arange(101)
    c1, c2 = stats.bootstrap_ci(x, np.median, seed=3), stats.bootstrap_ci(x, np.median, seed=3)
    assert c1 == c2
    assert c1["estimate"] == 50 and c1["low"] <= 50 <= c1["high"]


def test_diff_props():
    ci = stats.diff_props_ci(60, 100, 40, 100)
    assert ci["estimate"] == pytest.approx(0.2)
    assert ci["low"] < 0.2 < ci["high"]

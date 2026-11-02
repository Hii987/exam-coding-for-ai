"""Statistiques écrites à la main (brique 8) : intervalles de confiance.

Pas de scipy : la moyenne, l'écart-type, le bootstrap et l'intervalle d'une
proportion sont codés ici, et testés dans tests/test_stats.py.
"""
from __future__ import annotations

import math

import numpy as np

Z95 = 1.959963984540054  # quantile 97,5 % de la loi normale


def _as_array(x) -> np.ndarray:
    a = np.asarray(x, dtype=float)
    a = a[~np.isnan(a)]
    if a.size == 0:
        raise ValueError("série vide : pas d'intervalle possible")
    return a


def mean(x) -> float:
    a = _as_array(x)
    return float(a.sum() / a.size)


def std(x) -> float:
    """Écart-type corrigé (n-1). Une seule valeur : 0.0."""
    a = _as_array(x)
    if a.size == 1:
        return 0.0
    m = a.sum() / a.size
    return float(math.sqrt(((a - m) ** 2).sum() / (a.size - 1)))


def mean_ci(x, level: float = 0.95) -> dict:
    """IC normal de la moyenne : m ± z * s / sqrt(n)."""
    if level != 0.95:
        raise ValueError("seul le niveau 0.95 est implémenté")
    a = _as_array(x)
    m, s = mean(a), std(a)
    half = Z95 * s / math.sqrt(a.size)
    return {"estimate": m, "low": m - half, "high": m + half, "n": int(a.size)}


def bootstrap_ci(x, stat=np.median, n_boot: int = 2000, seed: int = 0) -> dict:
    """IC bootstrap percentile à 95 % pour n'importe quelle statistique."""
    a = _as_array(x)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, a.size, size=(n_boot, a.size))
    boots = np.array([stat(a[i]) for i in idx])
    return {"estimate": float(stat(a)), "low": float(np.percentile(boots, 2.5)),
            "high": float(np.percentile(boots, 97.5)), "n": int(a.size)}


def diff_means_ci(a, b) -> dict:
    """Différence de moyennes (a - b), IC de Welch approché par la loi normale."""
    xa, xb = _as_array(a), _as_array(b)
    d = mean(xa) - mean(xb)
    se = math.sqrt(std(xa) ** 2 / xa.size + std(xb) ** 2 / xb.size)
    return {"estimate": d, "low": d - Z95 * se, "high": d + Z95 * se,
            "n_a": int(xa.size), "n_b": int(xb.size)}


def prop_ci(k: int, n: int) -> dict:
    """IC de Wilson pour une proportion k/n (reste dans [0, 1], même si k = 0)."""
    if n <= 0:
        raise ValueError("n doit être > 0")
    if not 0 <= k <= n:
        raise ValueError("il faut 0 <= k <= n")
    p = k / n
    z2 = Z95 ** 2
    centre = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return {"estimate": p, "low": centre - half, "high": centre + half, "n": n}


def diff_props_ci(k1: int, n1: int, k2: int, n2: int) -> dict:
    """Différence de proportions p1 - p2 (comparaison A/B), IC normal."""
    p1, p2 = k1 / n1, k2 / n2
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    d = p1 - p2
    return {"estimate": d, "low": d - Z95 * se, "high": d + Z95 * se}

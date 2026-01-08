# src/atlantica2/formulas/damage.py
# All comments in this project are written in English.

from __future__ import annotations


def base_mitigation(*, defense: float, k: float) -> float:
    """
    BaseMA = A/(A+K), BaseMS = MR/(MR+K)
    Clamp to [0, 0.95] to avoid extreme.
    """
    if defense <= 0:
        return 0.0
    m = defense / (defense + k)
    if m < 0.0:
        m = 0.0
    if m > 0.95:
        m = 0.95
    return m


def apply_mitigation(*, raw_damage: float, mitigation: float) -> float:
    """
    Final = raw * (1 - mitigation)
    """
    if raw_damage <= 0:
        return 0.0
    return raw_damage * (1.0 - mitigation)


def crit_multiplier(*, crit_damage_pct: float) -> float:
    """
    crit_damage_pct is percent points (e.g., 150 => 1.5)
    """
    return max(0.0, crit_damage_pct / 100.0)


def compute_raw_attack(*, attack: float, ratio: float, is_crit: bool, crit_damage_pct: float) -> float:
    """
    raw = attack * ratio * (crit_mult if crit)
    """
    raw = attack * ratio
    if is_crit:
        raw *= crit_multiplier(crit_damage_pct=crit_damage_pct)
    return raw

# src/atlantica2/formulas/attribute_derivation.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DerivedFromAttributes:
    attack_base: float
    mhr_base: float          # multi-hit rate base (percent points)
    mp_base: float
    mr_base: float
    hp_base: float
    skill_power: float       # SP (not percent), used in skill formulas later


def derive_from_attributes(*, str_: float, dex: float, int_: float, vit: float, k: float) -> DerivedFromAttributes:
    """
    Based on your sheet:
    - 1 STR => +1 base attack
    - 1 DEX => +0.05% base multi-hit rate  (percent points)
    - 1 INT => +100 base mana, +1 base MR, +0.0005125% * K skill power
    - 1 VIT => +50 base HP
    """
    attack_base = 1.0 * str_
    mhr_base = 0.05 * dex
    mp_base = 100.0 * int_
    mr_base = 1.0 * int_
    hp_base = 50.0 * vit

    # SP = INT * K * 0.0005125% = INT * K * 0.000005125
    skill_power = float(int_ * k * 0.000005125)

    return DerivedFromAttributes(
        attack_base=attack_base,
        mhr_base=mhr_base,
        mp_base=mp_base,
        mr_base=mr_base,
        hp_base=hp_base,
        skill_power=skill_power,
    )

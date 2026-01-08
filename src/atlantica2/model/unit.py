# src/atlantica2/model/unit.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from src.atlantica2.data.gear import Gear
from src.atlantica2.data.offhands import build_offhand_package
from src.atlantica2.data.weapons import build_weapon_package
from src.atlantica2.formulas.attribute_derivation import derive_from_attributes
from src.atlantica2.formulas.stats import evaluate_stat
from src.atlantica2.formulas.ap import compute_ap_gain


@dataclass
class UnitBuild:
    """
    Defines how a unit is equipped.
    """
    main_weapon_key: str
    main_weapon_passive_choice: int = 0  # 0=default, 1..3=choose passive 1..3 in sheet

    offhand_key: Optional[str] = None
    offhand_passive_choice: int = 0      # 0=default, 1..3=choose passive 1..3 in sheet

    gear: Optional[Gear] = None
    k: int = 4000


@dataclass
class UnitBase:
    """
    Base (non-gear) attributes for formula input.
    """
    level: int
    str_: float
    dex: float
    int_: float
    vit: float

    # Defaults (can be overridden later via mods)
    crit_chance: float = 5.0        # %
    crit_damage: float = 150.0      # %
    accuracy: float = 100.0         # %
    evasion: float = 0.0            # %
    skill_evasion: float = 0.0      # %


@dataclass
class UnitStats:
    """
    Final computed stats for battle runtime.
    """
    hp_max: float
    mp_max: float
    attack: float
    armour: float
    mr: float

    mhr: float              # multi-hit rate (%)
    crit_chance: float      # %
    crit_damage: float      # %
    accuracy: float         # %
    evasion: float          # %
    skill_evasion: float    # %

    ap_gain: float          # AP gained per team-turn tick


@dataclass
class Unit:
    """
    A battle unit: identity + base + build + current resources.
    """
    uid: str               # e.g. "A-1"
    team: str              # "A" or "B"
    slot: int              # 1..9

    base: UnitBase
    build: UnitBuild

    stats: Optional[UnitStats] = None

    hp: float = 0.0
    mp: float = 0.0
    ap: float = 0.0

    # runtime containers (later):
    statuses: List[Any] = field(default_factory=list)
    skills: List[Any] = field(default_factory=list)

    def is_alive(self) -> bool:
        return self.hp > 0

    def _collect_mods(self) -> List[Any]:
        """
        Gather all stat mods from gear + weapon + offhand.
        Mods can be:
          - (stat, tag, value) tuples
          - dict {"stat","tag","value"}
          - objects with .stat .tag .value
        """
        mods: List[Any] = []

        if self.build.gear is not None:
            mods.extend(self.build.gear.all_mods())

        w = build_weapon_package(
            weapon_key=self.build.main_weapon_key,
            passive_choice=self.build.main_weapon_passive_choice,
            k=self.build.k,
        )
        mods.extend(w.get("mods", []))

        if self.build.offhand_key:
            o = build_offhand_package(
                offhand_key=self.build.offhand_key,
                passive_choice=self.build.offhand_passive_choice,
                k=self.build.k,
            )
            mods.extend(o.get("mods", []))

        return mods

    def recompute_stats(self) -> UnitStats:
        """
        Compute final stats from:
          - derived stats from attributes
          - gear/weapon/offhand mods via base/inc/more/less pipeline
        """
        k = int(self.build.k)
        d = derive_from_attributes(
            str_=self.base.str_,
            dex=self.base.dex,
            int_=self.base.int_,
            vit=self.base.vit,
            k=k,
        )

        mods = self._collect_mods()

        # Core stats
        hp_max = evaluate_stat(stat_key="hp", base_value=d.hp_base, mods=mods, clamp_min=1.0)
        mp_max = evaluate_stat(stat_key="mp", base_value=d.mp_base, mods=mods, clamp_min=0.0)
        attack = evaluate_stat(stat_key="attack", base_value=d.attack_base, mods=mods, clamp_min=0.0)
        armour = evaluate_stat(stat_key="armour", base_value=0.0, mods=mods, clamp_min=0.0)
        mr = evaluate_stat(stat_key="mr", base_value=d.mr_base, mods=mods, clamp_min=0.0)

        # Rates
        mhr = evaluate_stat(stat_key="mhr", base_value=d.mhr_base, mods=mods, clamp_min=0.0)
        crit_chance = evaluate_stat(stat_key="crit_chance", base_value=self.base.crit_chance, mods=mods, clamp_min=0.0)
        crit_damage = evaluate_stat(stat_key="crit_damage", base_value=self.base.crit_damage, mods=mods, clamp_min=0.0)
        accuracy = evaluate_stat(stat_key="accuracy", base_value=self.base.accuracy, mods=mods, clamp_min=0.0)
        evasion = evaluate_stat(stat_key="evasion", base_value=self.base.evasion, mods=mods, clamp_min=0.0)
        skill_evasion = evaluate_stat(stat_key="skill_evasion", base_value=self.base.skill_evasion, mods=mods, clamp_min=0.0)

        # AP gain
        ap_gain = compute_ap_gain(mods=mods, base_ap_gain=100.0)

        st = UnitStats(
            hp_max=hp_max,
            mp_max=mp_max,
            attack=attack,
            armour=armour,
            mr=mr,
            mhr=mhr,
            crit_chance=crit_chance,
            crit_damage=crit_damage,
            accuracy=accuracy,
            evasion=evasion,
            skill_evasion=skill_evasion,
            ap_gain=ap_gain,
        )
        self.stats = st

        # Initialize current resources if empty
        if self.hp <= 0:
            self.hp = hp_max
        if self.mp <= 0:
            self.mp = mp_max

        return st

# src/atlantica2/data/weapons.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from ..core.types import WeaponAOE, WeaponLocation, WeaponRange

PassiveId = Literal[1, 2, 3]
ModTag = Literal["base", "inc", "more", "less", "special"]


@dataclass(frozen=True)
class Proc:
    """A non-stat effect (on hit, conditional damage, special rules)."""
    name: str
    chance_pct: float = 100.0
    params: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True)
class Mod:
    """
    Lightweight modifier record.

    - tag="base": +X base (flat add)
    - tag="inc" : +X% increased (additive among inc lines)
    - tag="more": +X% more (multiplicative)
    - tag="less": +X% less (multiplicative)
    - tag="special": handled by rules/formulas later
    """
    stat: str
    tag: ModTag
    value: float
    source: str = ""


@dataclass(frozen=True)
class PassiveOption:
    id: PassiveId
    name: str
    mods: List[Mod] = field(default_factory=list)
    procs: List[Proc] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class WeaponDef:
    """
    Main-hand weapon definition (MAX ROLL).
    """
    key: str
    attack_range: WeaponRange
    aoe: WeaponAOE
    location: WeaponLocation

    # Basic attack ratios
    main_ratio: float = 1.0
    aoe_ratio_1: float = 0.0  # used for the 1st extra target (if any)
    aoe_ratio_2: float = 0.0  # used for the 2nd extra target (if any)

    # AP gain adjustment per team turn (ap gain is calculated elsewhere)
    ap_base_delta: float = 0.0     # +X base AP gain
    ap_less_pct: float = 0.0       # X% less AP gain (e.g., 20 => *0.8)
    ap_more_pct: float = 0.0       # X% more AP gain

    # Default passive always present
    default_mods: List[Mod] = field(default_factory=list)
    default_procs: List[Proc] = field(default_factory=list)

    # Choose exactly ONE of 1/2/3 for build
    passives: Dict[PassiveId, PassiveOption] = field(default_factory=dict)


WEAPONS: Dict[str, WeaponDef] = {}

# -------------------------
# Weapon catalog (MAX ROLL)
# -------------------------

# Sword
# range: melee, aoe: single, location: frontline
# AP: -20 base
# default: skill point +10-30 -> max 30 (special)
# p1: retaliate chance 4-20% -> max 20 (proc)
# p2: all attribute +2-10% -> max 10% increased (inc)
# p3: attack +1-5% per turn up to 40% (special proc)
WEAPONS["Sword"] = WeaponDef(
    key="Sword",
    attack_range=WeaponRange.MELEE,
    aoe=WeaponAOE.SINGLE,
    location=WeaponLocation.FRONTLINE,
    main_ratio=1.0,
    ap_base_delta=-20.0,
    default_mods=[Mod(stat="skill_points", tag="special", value=30.0, source="Sword: default (max)")],
    passives={
        1: PassiveOption(
            id=1,
            name="Retaliate chance 20% (max)",
            procs=[Proc(name="retaliate_on_hit", chance_pct=20.0, params={}, notes="Base retaliate chance.")],
        ),
        2: PassiveOption(
            id=2,
            name="All attributes +10% (max, increased)",
            mods=[
                Mod(stat="str", tag="inc", value=10.0, source="Sword: passive2 (max)"),
                Mod(stat="dex", tag="inc", value=10.0, source="Sword: passive2 (max)"),
                Mod(stat="int", tag="inc", value=10.0, source="Sword: passive2 (max)"),
                Mod(stat="vit", tag="inc", value=10.0, source="Sword: passive2 (max)"),
            ],
        ),
        3: PassiveOption(
            id=3,
            name="Attack +5% per turn, up to 40% (max)",
            procs=[Proc(name="attack_ramp_per_turn", chance_pct=100.0, params={"inc_per_turn_pct": 5.0, "cap_pct": 40.0})],
        ),
    },
)

# Spear
# range: melee, aoe: line (2 cells), location: frontline
# ratios: main 100%, behind1 50%
# AP: -20 base
# default: retaliate 20-40 -> max 40
# p1: bleeding 5-25 -> max 25 (proc)
# p2: spear throw no retaliate, aim to row2 (special)
# p3: final damage +4-20% per member advantage -> max 20 (special)
WEAPONS["Spear"] = WeaponDef(
    key="Spear",
    attack_range=WeaponRange.MELEE,
    aoe=WeaponAOE.LINE,
    location=WeaponLocation.FRONTLINE,
    main_ratio=1.0,
    aoe_ratio_1=0.5,
    ap_base_delta=-20.0,
    default_procs=[Proc(name="retaliate_on_hit", chance_pct=40.0, params={}, notes="Base retaliate chance (max).")],
    passives={
        1: PassiveOption(
            id=1,
            name="Bleeding chance 25% (max)",
            procs=[Proc(name="bleed_on_hit", chance_pct=25.0, params={"duration": 1}, notes="Apply bleeding on hit.")],
        ),
        2: PassiveOption(
            id=2,
            name="Spear throw (no retaliate, aim row2)",
            procs=[Proc(name="spear_throw_mode", chance_pct=100.0, params={"disable_retaliate": True, "aim_row": 1})],
        ),
        3: PassiveOption(
            id=3,
            name="Final damage +20% per member advantage (max)",
            mods=[Mod(stat="fd_more_per_member_advantage_pct", tag="special", value=20.0, source="Spear: passive3 (max)")],
        ),
    },
)

# Axe
# range: melee, aoe: adjacent_1, location: frontline
# ratios: main 100%, adjacent 50%
# AP: 30% less AP
# default: stun chance 4-20 -> max 20
# p1: dmg vs non-melee +4-20 -> max 20 (special)
# p2: final damage up to +20% when HP low (special)
# p3: final damage +4-20% per member disadvantage -> max 20 (special)
WEAPONS["Axe"] = WeaponDef(
    key="Axe",
    attack_range=WeaponRange.MELEE,
    aoe=WeaponAOE.ADJACENT_1,
    location=WeaponLocation.FRONTLINE,
    main_ratio=1.0,
    aoe_ratio_1=0.5,
    ap_less_pct=30.0,
    default_procs=[Proc(name="stun_on_hit", chance_pct=20.0, params={"duration_turns": 1}, notes="Base stun chance (max).")],
    passives={
        1: PassiveOption(
            id=1,
            name="Damage vs non-melee +20% (max)",
            mods=[Mod(stat="dmg_more_vs_non_melee_pct", tag="special", value=20.0, source="Axe: passive1 (max)")],
        ),
        2: PassiveOption(
            id=2,
            name="Final damage up to +20% when HP decreases",
            mods=[Mod(stat="fd_ramp_when_hp_low_pct", tag="special", value=20.0, source="Axe: passive2 (max)")],
        ),
        3: PassiveOption(
            id=3,
            name="Final damage +20% per member disadvantage (max)",
            mods=[Mod(stat="fd_more_per_member_disadvantage_pct", tag="special", value=20.0, source="Axe: passive3 (max)")],
        ),
    },
)

# Gun
# range: ranged, aoe: line (full line), location: frontline
# ratios: main 100%, behind1 50%, behind2 75% (as your sheet)
# AP: -10 base
# default: pure chance 4-20 -> max 20
# p1: accuracy +2-10 -> max 10
# p2: dmg to cannon +4-20% more -> max 20 (special)
# p3: dmg to caster +4-20% more -> max 20 (special)
WEAPONS["Gun"] = WeaponDef(
    key="Gun",
    attack_range=WeaponRange.RANGED,
    aoe=WeaponAOE.LINE,
    location=WeaponLocation.FRONTLINE,
    main_ratio=1.0,          # corrected: NOT 200%
    aoe_ratio_1=0.5,
    aoe_ratio_2=0.75,
    ap_base_delta=-10.0,
    default_procs=[Proc(name="pure_damage_on_hit", chance_pct=20.0, params={}, notes="Pure damage chance (max).")],
    passives={
        1: PassiveOption(
            id=1,
            name="Accuracy +10% (max)",
            mods=[Mod(stat="accuracy", tag="base", value=10.0, source="Gun: passive1 (max)")],
        ),
        2: PassiveOption(
            id=2,
            name="Damage to cannon +20% more (max)",
            mods=[Mod(stat="dmg_more_vs_cannon_pct", tag="special", value=20.0, source="Gun: passive2 (max)")],
        ),
        3: PassiveOption(
            id=3,
            name="Damage to caster +20% more (max)",
            mods=[Mod(stat="dmg_more_vs_caster_pct", tag="special", value=20.0, source="Gun: passive3 (max)")],
        ),
    },
)

# Bow
# range: ranged, aoe: single, location: anywhere
# AP: -5 base
# default: critical chance +8-40 -> max 40 (base add)
# p1: multi-hit 4-20 -> max 20 (base add)
# p2: AP +2-10 base -> max 10 (base AP gain)
# p3: final damage +1-5% per distance -> max 5 (special)
WEAPONS["Bow"] = WeaponDef(
    key="Bow",
    attack_range=WeaponRange.RANGED,
    aoe=WeaponAOE.SINGLE,
    location=WeaponLocation.ANYWHERE,
    main_ratio=1.0,
    ap_base_delta=-5.0,
    default_mods=[Mod(stat="cc", tag="base", value=40.0, source="Bow: default (max)")],
    passives={
        1: PassiveOption(
            id=1,
            name="Multi-hit rate +20% base (max)",
            mods=[Mod(stat="mhr", tag="base", value=20.0, source="Bow: passive1 (max)")],
        ),
        2: PassiveOption(
            id=2,
            name="AP +10 base (max)",
            mods=[Mod(stat="ap_base", tag="base", value=10.0, source="Bow: passive2 (max)")],
        ),
        3: PassiveOption(
            id=3,
            name="Final damage +5% per distance (max)",
            mods=[Mod(stat="fd_more_per_distance_pct", tag="special", value=5.0, source="Bow: passive3 (max)")],
        ),
    },
)

# Cannon
# range: ranged, aoe: cross, location: anywhere
# ratios: main 100%, cross neighbors 50%
# AP: 20% less AP
# default: ignore guard stance (special)
# p1: Shred SP*10 (special)
# p2: Dull 2-10 -> max 10 (proc)
# p3: Weaken 2-10 -> max 10 (proc)
WEAPONS["Cannon"] = WeaponDef(
    key="Cannon",
    attack_range=WeaponRange.RANGED,
    aoe=WeaponAOE.CROSS,
    location=WeaponLocation.ANYWHERE,
    main_ratio=1.0,
    aoe_ratio_1=0.5,
    ap_less_pct=20.0,
    default_procs=[Proc(name="ignore_guard_stance", chance_pct=100.0, params={}, notes="Basic attacks ignore guard stance.")],
    passives={
        1: PassiveOption(
            id=1,
            name="Shred = SP * 10 (special)",
            procs=[Proc(name="apply_shred_on_hit", chance_pct=100.0, params={"multiplier": 10.0})],
        ),
        2: PassiveOption(
            id=2,
            name="Dull 10% base (max)",
            procs=[Proc(name="apply_dull_on_hit", chance_pct=10.0, params={}, notes="Accuracy reduction status.")],
        ),
        3: PassiveOption(
            id=3,
            name="Weaken 10% base (max)",
            procs=[Proc(name="apply_weaken_on_hit", chance_pct=10.0, params={}, notes="Attack damage reduction status.")],
        ),
    },
)

# Staff
# range: ranged, aoe: cross, location: frontline
# ratios: main 100%, cross neighbors 100% (as your sheet)
# AP: 20% less AP
# default: skill point +10-30 -> max 30
# p1: attack damage +10% (inc)
# p2: spell crit 4-20 -> max 20 (base add)
# p3: healing crit 4-20 -> max 20 (special)
WEAPONS["Staff"] = WeaponDef(
    key="Staff",
    attack_range=WeaponRange.RANGED,
    aoe=WeaponAOE.CROSS,
    location=WeaponLocation.FRONTLINE,
    main_ratio=1.0,
    aoe_ratio_1=1.0,
    ap_less_pct=20.0,
    default_mods=[Mod(stat="skill_points", tag="special", value=30.0, source="Staff: default (max)")],
    passives={
        1: PassiveOption(
            id=1,
            name="Attack damage +10% increased",
            mods=[Mod(stat="attack", tag="inc", value=10.0, source="Staff: passive1")],
        ),
        2: PassiveOption(
            id=2,
            name="Spell crit chance +20% base (max)",
            mods=[Mod(stat="scc", tag="base", value=20.0, source="Staff: passive2 (max)")],
        ),
        3: PassiveOption(
            id=3,
            name="Healing crit +20% (max)",
            mods=[Mod(stat="healing_crit", tag="special", value=20.0, source="Staff: passive3 (max)")],
        ),
    },
)

# Wand
# range: ranged, aoe: single, location: frontline
# AP: -10 base
# default: skill point +10-30 -> max 30
# p1: skill duration +1 (special)
# p2: counterspell chance 2-10 -> max 10 (proc)
# p3: mana buff unlock, mana cost -50% (special)
WEAPONS["Wand"] = WeaponDef(
    key="Wand",
    attack_range=WeaponRange.RANGED,
    aoe=WeaponAOE.SINGLE,
    location=WeaponLocation.FRONTLINE,
    main_ratio=1.0,
    ap_base_delta=-10.0,
    default_mods=[Mod(stat="skill_points", tag="special", value=30.0, source="Wand: default (max)")],
    passives={
        1: PassiveOption(
            id=1,
            name="Skill duration +1",
            mods=[Mod(stat="skill_duration_plus", tag="special", value=1.0, source="Wand: passive1")],
        ),
        2: PassiveOption(
            id=2,
            name="Counterspell chance 10% (max)",
            procs=[Proc(name="counterspell_on_enemy_cast", chance_pct=10.0, params={}, notes="Chance to counter an enemy skill.")],
        ),
        3: PassiveOption(
            id=3,
            name="Mana buff unlock, all skill mana cost -50%",
            mods=[Mod(stat="mana_cost_less_pct", tag="special", value=50.0, source="Wand: passive3 (max)")],
        ),
    },
)


# -------------------------
# Helpers
# -------------------------

def get_weapon(key: str) -> WeaponDef:
    if key not in WEAPONS:
        raise KeyError(f"Unknown weapon: {key}")
    return WEAPONS[key]


def build_weapon_package(*, weapon_key: str, passive_choice: Optional[PassiveId]) -> Dict[str, Any]:
    """
    Return a package of:
    - targeting properties (range/aoe/location/ratios)
    - ap modifiers
    - mods/procs (default + chosen passive)
    """
    w = get_weapon(weapon_key)

    mods = list(w.default_mods)
    procs = list(w.default_procs)

    chosen = None
    if passive_choice is not None:
        if passive_choice not in w.passives:
            raise KeyError(f"Weapon {weapon_key} has no passive {passive_choice}")
        chosen = w.passives[passive_choice]
        mods.extend(chosen.mods)
        procs.extend(chosen.procs)

    return {
        "key": weapon_key,
        "passive_choice": passive_choice,
        "attack_range": w.attack_range,
        "aoe": w.aoe,
        "location": w.location,
        "main_ratio": w.main_ratio,
        "aoe_ratio_1": w.aoe_ratio_1,
        "aoe_ratio_2": w.aoe_ratio_2,
        "ap_base_delta": w.ap_base_delta,
        "ap_less_pct": w.ap_less_pct,
        "ap_more_pct": w.ap_more_pct,
        "mods": mods,
        "procs": procs,
        "chosen_passive_name": chosen.name if chosen else None,
    }

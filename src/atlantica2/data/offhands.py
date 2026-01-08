# src/atlantica2/data/offhands.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

PassiveId = Literal[1, 2, 3]
ModTag = Literal["base", "inc", "more", "less", "special"]


@dataclass(frozen=True)
class Proc:
    """
    A non-stat effect triggered by some condition (on hit, on block, on battle start, etc.)
    """
    name: str
    chance_pct: float = 100.0
    params: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass(frozen=True)
class Mod:
    """
    A lightweight modifier record.

    - tag="base": +X base (flat add)
    - tag="inc" : +X% increased (additive among inc lines)
    - tag="more": +X% more (multiplicative)
    - tag="less": +X% less (multiplicative)
    - tag="special": custom stat handled by rules/formulas layer later

    value meaning:
    - If scale is None: value is the final numeric value used directly
    - If scale={"k_pct":0.10}: final = value * (k_pct * K) where value is typically 1.0
      (We use value=1.0 convention for scaled lines)
    """
    stat: str
    tag: ModTag
    value: float
    scale: Optional[Dict[str, float]] = None
    source: str = ""


@dataclass(frozen=True)
class PassiveOption:
    id: PassiveId
    name: str
    mods: List[Mod] = field(default_factory=list)
    procs: List[Proc] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class OffhandDef:
    key: str
    # AP is handled by formulas/ap.py later. Here we store only definition-level changes.
    ap_base_delta: float = 0.0          # +X base AP gain
    ap_less_pct: float = 0.0            # X% less AP gain (e.g., 20 => *0.8)
    ap_more_pct: float = 0.0            # X% more AP gain

    default_mods: List[Mod] = field(default_factory=list)
    default_procs: List[Proc] = field(default_factory=list)

    # Choose exactly ONE of 1/2/3 for build
    passives: Dict[PassiveId, PassiveOption] = field(default_factory=dict)


def _k_scaled(stat: str, tag: ModTag, k_pct: float, source: str) -> Mod:
    """
    Represent 'X%K base' without embedding K in data.
    Resolve later with resolve_mods(K).
    """
    return Mod(stat=stat, tag=tag, value=1.0, scale={"k_pct": k_pct}, source=source)


# -------------------------
# Offhand catalog (MAX ROLL)
# -------------------------

OFFHANDS: Dict[str, OffhandDef] = {}

# Maintain Kit (off-hand)
# Sheet:
# default: weapon damage +20-40% base  -> max 40%
# p1: accuracy +2-10%                  -> max 10
# p2: attribute +2-10%                 -> user changed to base = 10%K each attribute (max)
# p3: basic attack AoE penalty -2-10%  -> max 10 (special)
OFFHANDS["MaintainKit"] = OffhandDef(
    key="MaintainKit",
    ap_base_delta=0.0,
    ap_less_pct=0.0,
    default_mods=[
        # IMPORTANT: this is NOT "+0.40*K". It means +40% of MAIN weapon base damage.
        Mod(stat="weapon_damage_base_pct", tag="special", value=0.40, source="MaintainKit: default (max)"),
    ],
    passives={
        1: PassiveOption(
            id=1,
            name="Accuracy +10% (max)",
            mods=[Mod(stat="accuracy", tag="base", value=10.0, source="MaintainKit: passive1 (max)")],
        ),
        2: PassiveOption(
            id=2,
            name="Attributes +10%K base each (max, custom rule)",
            mods=[
                _k_scaled("str", "base", 0.10, "MaintainKit: passive2 (max)"),
                _k_scaled("dex", "base", 0.10, "MaintainKit: passive2 (max)"),
                _k_scaled("int", "base", 0.10, "MaintainKit: passive2 (max)"),
                _k_scaled("vit", "base", 0.10, "MaintainKit: passive2 (max)"),
            ],
            notes="Custom: attribute is flat base = 10%K each, not 'increase'.",
        ),
        3: PassiveOption(
            id=3,
            name="Basic attack AoE penalty -10% base (max)",
            mods=[Mod(stat="basic_aoe_penalty_reduction_pct", tag="special", value=10.0, source="MaintainKit: passive3 (max)")],
        ),
    },
)

# Shield
# Sheet:
# AP: 20% less AP
# default: self block chance 10-20% base -> max 20
# p1: Allies behind take 10-20% less Skill damage -> max 20% less
# p2: When blocked, allies behind also has 50% chance to block (special proc)
# p3: guard effectiveness 4-20% -> max 20% (special)
OFFHANDS["Shield"] = OffhandDef(
    key="Shield",
    ap_less_pct=20.0,
    default_mods=[
        Mod(stat="block_chance", tag="base", value=20.0, source="Shield: default (max)"),
    ],
    passives={
        1: PassiveOption(
            id=1,
            name="Allies behind take 20% less skill damage (max)",
            mods=[Mod(stat="allies_behind_skill_damage_less_pct", tag="special", value=20.0, source="Shield: passive1 (max)")],
        ),
        2: PassiveOption(
            id=2,
            name="Behind ally block chain (50%)",
            procs=[
                Proc(
                    name="block_chain_behind",
                    chance_pct=100.0,
                    params={"behind_block_share_pct": 50.0},
                    notes="If self blocks, allies behind can also block with 50% of this unit block chance.",
                )
            ],
        ),
        3: PassiveOption(
            id=3,
            name="Guard effectiveness +20% (max)",
            mods=[Mod(stat="guard_effectiveness_pct", tag="special", value=20.0, source="Shield: passive3 (max)")],
        ),
    },
)

# Orb
# Sheet:
# default: immu 4 turn at the start
# p1: energy shield = intel*20 (special)
# p2: mana shield: absorb 50% damage cost 2x mana (special)
# p3: Skill check (placeholder)
OFFHANDS["Orb"] = OffhandDef(
    key="Orb",
    ap_base_delta=0.0,
    default_procs=[Proc(name="start_immunity", chance_pct=100.0, params={"turns": 4}, notes="Immunity at battle start.")],
    passives={
        1: PassiveOption(
            id=1,
            name="Energy shield = INT * 20",
            procs=[Proc(name="energy_shield", chance_pct=100.0, params={"int_multiplier": 20.0})],
        ),
        2: PassiveOption(
            id=2,
            name="Mana shield (50% absorb, 2x mana cost)",
            procs=[Proc(name="mana_shield", chance_pct=100.0, params={"absorb_pct": 50.0, "mana_cost_multiplier": 2.0})],
        ),
        3: PassiveOption(
            id=3,
            name="Skill check (TBD)",
            procs=[Proc(name="orb_skill_check", chance_pct=100.0, params={})],
        ),
    },
)

# Book
# Sheet:
# AP: 10% less AP
# default: skill point +10-30 -> max 30 (special)
# p1: talent point +1 (special)
# p2: intel +2-10% -> user likely means base add 10%K or +10%? keep as inc for now
# p3: Ignore neglect effect (special)
OFFHANDS["Book"] = OffhandDef(
    key="Book",
    ap_less_pct=10.0,
    default_mods=[Mod(stat="skill_points", tag="special", value=30.0, source="Book: default (max)")],
    passives={
        1: PassiveOption(
            id=1,
            name="Talent point +1",
            mods=[Mod(stat="talent_points", tag="special", value=1.0, source="Book: passive1")],
        ),
        2: PassiveOption(
            id=2,
            name="INT +10% (max, increased)",
            mods=[Mod(stat="int", tag="inc", value=10.0, source="Book: passive2 (max)")],
        ),
        3: PassiveOption(
            id=3,
            name="Ignore neglect effect",
            procs=[Proc(name="ignore_neglect", chance_pct=100.0, params={})],
        ),
    },
)

# Quiver
# Sheet:
# default: accuracy +4-20% -> max 20 (base)
# p1: critical damage +25% (base add)
# p2: Apply slow -10 (proc, on hit)
# p3: Split Arrow, all arrow deal 50% damage (special)
OFFHANDS["Quiver"] = OffhandDef(
    key="Quiver",
    default_mods=[Mod(stat="accuracy", tag="base", value=20.0, source="Quiver: default (max)")],
    passives={
        1: PassiveOption(
            id=1,
            name="Critical damage +25% (base)",
            mods=[Mod(stat="crd", tag="base", value=25.0, source="Quiver: passive1")],
        ),
        2: PassiveOption(
            id=2,
            name="Apply Slow (-10 base AP) on hit",
            procs=[Proc(name="apply_slow", chance_pct=100.0, params={"slow_ap_base_delta": -10.0})],
        ),
        3: PassiveOption(
            id=3,
            name="Split Arrow (all arrows deal 50% damage)",
            mods=[Mod(stat="split_arrow_damage_ratio", tag="special", value=0.50, source="Quiver: passive3")],
        ),
    },
)

# Bullet
# Sheet:
# default: attack damage +20%  -> treat as increased
# p1: critical damage +25%    -> base add
# p2: enemy AP -1-5 per hit   -> max 5 (proc on hit)
# p3: stun chance 1-5%        -> max 5 (proc roll)
OFFHANDS["Bullet"] = OffhandDef(
    key="Bullet",
    default_mods=[Mod(stat="attack", tag="inc", value=20.0, source="Bullet: default (max)")],
    passives={
        1: PassiveOption(
            id=1,
            name="Critical damage +25% (base)",
            mods=[Mod(stat="crd", tag="base", value=25.0, source="Bullet: passive1")],
        ),
        2: PassiveOption(
            id=2,
            name="Enemy AP -5 per hit (max)",
            procs=[Proc(name="drain_enemy_ap_on_hit", chance_pct=100.0, params={"ap_drain_flat": 5.0})],
        ),
        3: PassiveOption(
            id=3,
            name="Stun chance 5% (max)",
            procs=[Proc(name="stun_on_hit", chance_pct=5.0, params={"duration_turns": 1})],
        ),
    },
)

# Cannon Ball
# Sheet:
# default: Multi-hit rate -20, Attack damage +40%
# p1: Dex -10%, Strength +20%
# p2: final damage +4-20% when army equal -> max 20% (special)
# p3: Basic attack AoE penalty -2-10% base -> max 10% (special)
OFFHANDS["CannonBall"] = OffhandDef(
    key="CannonBall",
    default_mods=[
        Mod(stat="mhr", tag="base", value=-20.0, source="CannonBall: default (max)"),
        Mod(stat="attack", tag="inc", value=40.0, source="CannonBall: default (max)"),
    ],
    passives={
        1: PassiveOption(
            id=1,
            name="DEX -10% (inc), STR +20% (inc)",
            mods=[
                Mod(stat="dex", tag="inc", value=-10.0, source="CannonBall: passive1"),
                Mod(stat="str", tag="inc", value=20.0, source="CannonBall: passive1"),
            ],
        ),
        2: PassiveOption(
            id=2,
            name="Final damage +20% when army size equal (max)",
            mods=[Mod(stat="final_damage_more_when_equal_army_pct", tag="special", value=20.0, source="CannonBall: passive2 (max)")],
        ),
        3: PassiveOption(
            id=3,
            name="Basic attack AoE penalty -10% base (max)",
            mods=[Mod(stat="basic_aoe_penalty_reduction_pct", tag="special", value=10.0, source="CannonBall: passive3 (max)")],
        ),
    },
)


# -------------------------
# Helpers
# -------------------------

def get_offhand(key: str) -> OffhandDef:
    if key not in OFFHANDS:
        raise KeyError(f"Unknown offhand: {key}")
    return OFFHANDS[key]


def resolve_mods(mods: List[Mod], *, k: float) -> List[Mod]:
    """
    Convert K-scaled mods into concrete numeric values (keeping same Mod type).
    """
    out: List[Mod] = []
    for m in mods:
        if not m.scale:
            out.append(m)
            continue
        k_pct = m.scale.get("k_pct")
        if k_pct is None:
            out.append(m)
            continue
        out.append(Mod(stat=m.stat, tag=m.tag, value=m.value * (k_pct * k), scale=None, source=m.source))
    return out


def build_offhand_package(
    *,
    offhand_key: str,
    passive_choice: Optional[PassiveId],
    k: float,
) -> Dict[str, Any]:
    """
    Return a resolved package of:
    - ap modifiers
    - resolved mods (K applied)
    - procs

    The stat builder will later merge these into unit stats.
    """
    d = get_offhand(offhand_key)

    mods = resolve_mods(d.default_mods, k=k)
    procs = list(d.default_procs)

    chosen = None
    if passive_choice is not None:
        if passive_choice not in d.passives:
            raise KeyError(f"Offhand {offhand_key} has no passive {passive_choice}")
        chosen = d.passives[passive_choice]
        mods.extend(resolve_mods(chosen.mods, k=k))
        procs.extend(chosen.procs)

    return {
        "key": offhand_key,
        "passive_choice": passive_choice,
        "ap_base_delta": d.ap_base_delta,
        "ap_less_pct": d.ap_less_pct,
        "ap_more_pct": d.ap_more_pct,
        "mods": mods,
        "procs": procs,
        "chosen_passive_name": chosen.name if chosen else None,
    }

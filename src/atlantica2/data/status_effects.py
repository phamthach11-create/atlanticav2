# src/atlantica2/data/status_effects.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class StatusKind(str, Enum):
    BUFF = "buff"
    DEBUFF = "debuff"
    CONTROL = "control"   # stun, immobilized, etc.
    DOT = "dot"           # bleeding, burn, poison, etc.
    SPECIAL = "special"   # anything custom


class TickTiming(str, Enum):
    """
    When the status does its periodic effect.
    We will hook these in rules/status_pipeline.py.
    """
    NONE = "none"
    ON_TURN_START = "on_turn_start"
    ON_TURN_END = "on_turn_end"
    ON_TEAM_TURN_START = "on_team_turn_start"
    ON_HIT = "on_hit"
    BEFORE_DAMAGE = "before_damage"
    AFTER_DAMAGE = "after_damage"


@dataclass(frozen=True)
class StatusDef:
    """
    Pure data definition of a status effect.

    duration is in your "two-turn rule" units:
    - Duration decreases by 1 every two full team turns.
    - Expire at the start of turn (Y + X*2) if applied at turn Y with duration X.
    """

    key: str
    kind: StatusKind
    is_positive: bool

    # stacking rules
    stackable: bool = False
    max_stacks: int = 1
    refresh_on_reapply: bool = True

    # default duration (can be overridden by skill/weapon)
    default_duration: int = 1

    # tick hook
    tick_timing: TickTiming = TickTiming.NONE

    # generic parameters (e.g., { "ap_base_delta": -10 } for Slow)
    params: Dict[str, Any] = field(default_factory=dict)

    # UI/notes
    description: str = ""


# -------------------------
# Status catalog (based on your sheet)
# -------------------------

STATUS: Dict[str, StatusDef] = {}

# Immunity: immune to spell and debuff
STATUS["immunity"] = StatusDef(
    key="immunity",
    kind=StatusKind.BUFF,
    is_positive=True,
    stackable=False,
    max_stacks=1,
    default_duration=4,
    description="Immune to spells and debuffs.",
)

# Silence: can't use active and aura skill
STATUS["silence"] = StatusDef(
    key="silence",
    kind=StatusKind.DEBUFF,
    is_positive=False,
    default_duration=1,
    description="Cannot use active and aura skills.",
)

# Disarm: can't use basic attack
STATUS["disarm"] = StatusDef(
    key="disarm",
    kind=StatusKind.DEBUFF,
    is_positive=False,
    default_duration=1,
    description="Cannot use basic attacks.",
)

# Break: can't use passive skill and talent point
STATUS["break"] = StatusDef(
    key="break",
    kind=StatusKind.DEBUFF,
    is_positive=False,
    default_duration=1,
    description="Disables passive skills and talent bonuses.",
)

# Panic: skill damage -X% less
STATUS["panic"] = StatusDef(
    key="panic",
    kind=StatusKind.DEBUFF,
    is_positive=False,
    default_duration=1,
    params={"skill_damage_less_pct": 0.0},
    description="Skill damage is reduced by X% (less).",
)

# Weaken: attack damage -X% less
STATUS["weaken"] = StatusDef(
    key="weaken",
    kind=StatusKind.DEBUFF,
    is_positive=False,
    default_duration=1,
    params={"attack_damage_less_pct": 0.0},
    description="Attack damage is reduced by X% (less).",
)

# Slow: AP -X base at start of turn during 1 turn
STATUS["slow"] = StatusDef(
    key="slow",
    kind=StatusKind.DEBUFF,
    is_positive=False,
    default_duration=1,
    tick_timing=TickTiming.ON_TURN_START,
    params={"ap_base_delta": -0.0},
    description="At turn start, AP gain base is reduced by X for 1 turn.",
)

# Bleeding: deal 30% damage in 1 turn based on triggered hit
STATUS["bleeding"] = StatusDef(
    key="bleeding",
    kind=StatusKind.DOT,
    is_positive=False,
    default_duration=1,
    tick_timing=TickTiming.ON_TURN_START,
    params={"dot_ratio_of_last_triggered_hit": 0.30},
    description="At turn start, take 30% of the last triggered-hit damage.",
)

# Shred: armour reduced X (flat or percent decided by params)
STATUS["shred"] = StatusDef(
    key="shred",
    kind=StatusKind.DEBUFF,
    is_positive=False,
    default_duration=1,
    params={"armour_base_delta": -0.0},
    description="Armour reduced by X (base).",
)

# Sunder: magic resistance reduced X
STATUS["sunder"] = StatusDef(
    key="sunder",
    kind=StatusKind.DEBUFF,
    is_positive=False,
    default_duration=1,
    params={"mr_base_delta": -0.0},
    description="Magic resistance reduced by X (base).",
)

# Immobilized: can't act
STATUS["immobilized"] = StatusDef(
    key="immobilized",
    kind=StatusKind.CONTROL,
    is_positive=False,
    default_duration=1,
    description="Cannot act.",
)

# Stun: can't act, can't gain AP by turn
STATUS["stun"] = StatusDef(
    key="stun",
    kind=StatusKind.CONTROL,
    is_positive=False,
    default_duration=1,
    description="Cannot act and cannot gain AP from turn start.",
)

# Dull: accuracy -X%
STATUS["dull"] = StatusDef(
    key="dull",
    kind=StatusKind.DEBUFF,
    is_positive=False,
    default_duration=1,
    params={"accuracy_inc_pct": -0.0},
    description="Accuracy reduced by X% (increased is negative).",
)

# Brand: damage received X% more
STATUS["brand"] = StatusDef(
    key="brand",
    kind=StatusKind.DEBUFF,
    is_positive=False,
    default_duration=1,
    params={"damage_taken_more_pct": 0.0},
    description="Damage received is increased by X% (more).",
)

# Chill: AP -5 base, Multi-hit rate -10%
STATUS["chill"] = StatusDef(
    key="chill",
    kind=StatusKind.DEBUFF,
    is_positive=False,
    default_duration=1,
    tick_timing=TickTiming.ON_TURN_START,
    params={"ap_base_delta": -5.0, "mhr_base_delta": -10.0},
    description="AP base -5 at turn start; Multi-hit rate base -10%.",
)

# Deliberate: chance to neglect +X% base (special)
STATUS["deliberate"] = StatusDef(
    key="deliberate",
    kind=StatusKind.BUFF,
    is_positive=True,
    default_duration=1,
    params={"neglect_chance_base_delta": 0.0},
    description="Neglect chance increased by X% base.",
)


def get_status(key: str) -> StatusDef:
    if key not in STATUS:
        raise KeyError(f"Unknown status: {key}")
    return STATUS[key]

# src/atlantica2/core/types.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Literal, Optional

# ----------------------------
# Core identifiers
# ----------------------------

TeamId = Literal["A", "B"]
SlotId = int          # 1..9 (validated in grid.py)
UnitId = str          # e.g. "A-1", "B-9"
StatKey = str         # e.g. "HP", "Attack", "Armour", "MR", "MhR", "CC", "CrD", "Accuracy"


# ----------------------------
# Gameplay enums
# ----------------------------

class DamageType(str, Enum):
    ATTACK = "attack"   # mitigated by Armour
    SKILL = "skill"     # mitigated by MR
    PURE = "pure"       # no mitigation


class ActionType(str, Enum):
    BASIC_ATTACK = "basic_attack"
    SKILL = "skill"
    MOVE = "move"
    SWAP = "swap"
    GUARD = "guard"
    SKIP = "skip"


class SkillCategory(str, Enum):
    ACTIVE = "active"
    PASSIVE = "passive"
    AURA = "aura"


class WeaponRange(str, Enum):
    MELEE = "melee"
    RANGED = "range"


class WeaponAOE(str, Enum):
    SINGLE = "single_target"        # one cell
    ADJACENT_1 = "adjacent_1"       # one adjacent cell (weapon-defined ratio)
    LINE = "line"                   # full line (1-4-7 or 2-5-8 or 3-6-9)
    CROSS = "cross"                 # cross around main target (weapon-defined)


class WeaponLocation(str, Enum):
    FRONTLINE = "frontline"         # can only pick exposed frontline targets (rules/targeting.py)
    ANYWHERE = "anywhere"           # can pick any alive target


class ModifierKind(str, Enum):
    BASE = "base"   # +X base stat
    INC = "inc"     # +X% increased (as fraction, e.g. 10% => 0.10)
    MORE = "more"   # +X% more (as fraction)
    LESS = "less"   # +X% less (as fraction, e.g. 20% less => -0.20)


# ----------------------------
# Stat modifier lines (data -> formulas)
# ----------------------------

@dataclass(frozen=True)
class ModifierLine:
    """
    A single modifier line used by the stat pipeline.
    - kind=BASE: value is absolute number added to base stat.
    - kind=INC/MORE/LESS: value is a fraction (10% => 0.10, 20% less => -0.20).
    """
    stat: StatKey
    kind: ModifierKind
    value: float
    source: str = ""   # optional, for debug/logging


# ----------------------------
# Runtime containers (lightweight types)
# ----------------------------

@dataclass
class CooldownState:
    remaining: int = 0  # "two-turn rule" ticks handled in rules/cooldowns.py


@dataclass
class DurationState:
    remaining: int = 0  # "two-turn rule" ticks handled in rules/cooldowns.py


@dataclass
class ProcResult:
    """
    A generic result for procs (pure damage, AP drain on hit, status application, etc.)
    Use flexible payload so we can extend without changing the type.
    """
    name: str
    triggered: bool
    payload: Dict[str, float] | Dict[str, int] | Dict[str, str] | Dict[str, object] | None = None


# ----------------------------
# Simple error type
# ----------------------------

class GameRuleError(RuntimeError):
    """Raised when a game rule is violated by code (invalid state/action)."""
    pass

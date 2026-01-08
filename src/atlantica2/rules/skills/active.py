# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.atlantica2.model.effect import Proc
from src.atlantica2.core.grid import (
    behind_in_line,
    cross_neighbors,
    row_neighbors,
)

if TYPE_CHECKING:
    from src.atlantica2.model.unit import Unit
    from src.atlantica2.model.battle_state import BattleState


class SkillCastError(RuntimeError):
    """Raised when an active skill cannot be cast."""


@dataclass(frozen=True)
class ActiveCastPlan:
    """
    A pure plan describing what the cast intends to do.
    The sim/engine will apply damage/status/procs based on this plan.
    """

    skill_key: str
    skill_name: str

    caster_team: str
    caster_slot: int

    primary_target_team: str
    primary_target_slot: int

    # Final resolved target slots on defender side (AoE expanded).
    target_slots: List[int]

    # Resource changes + cooldown set.
    ap_cost: int
    mp_cost: int
    cooldown_set_to: int

    # Proc list attached to this skill (engine executes them).
    procs: List[Proc]


def _lazy_get_active_skill(skill_key: str) -> Any:
    """
    Lazy import to avoid hard dependency order while we are building files.
    Expected return object fields:
      - key, name
      - ap_cost, mp_cost
      - cooldown
      - aoe (str)
      - location (optional str, used by targeting later)
      - procs: List[Proc]
    """
    from src.atlantica2.data.skills_data import get_active_skill  # lazy

    return get_active_skill(skill_key)


def _get_cd_map(unit: Unit) -> Dict[str, int]:
    cd = getattr(unit, "cooldowns", None)
    if cd is None:
        cd = {}
        setattr(unit, "cooldowns", cd)
    return cd


def cd_remaining(unit: Unit, skill_key: str) -> int:
    return int(_get_cd_map(unit).get(skill_key, 0))


def set_cooldown(unit: Unit, skill_key: str, value: int) -> None:
    _get_cd_map(unit)[skill_key] = max(0, int(value))


def can_cast_active(unit: Unit, skill_key: str) -> tuple[bool, str]:
    if not getattr(unit, "alive", True):
        return False, "caster is dead"
    if cd_remaining(unit, skill_key) > 0:
        return False, f"cooldown remaining={cd_remaining(unit, skill_key)}"
    skill = _lazy_get_active_skill(skill_key)
    ap = int(getattr(unit, "ap", 0))
    mp = int(getattr(unit, "mp", 0))
    if ap < int(skill.ap_cost):
        return False, f"not enough AP ({ap} < {skill.ap_cost})"
    if mp < int(skill.mp_cost):
        return False, f"not enough MP ({mp} < {skill.mp_cost})"
    return True, "ok"


def _resolve_aoe_slots(primary_slot: int, aoe: str) -> List[int]:
    """
    Local AoE resolver for skills.
    Weapons AoE will be handled in rules/aoe.py later; this is for skills.
    Supported:
      - "single"
      - "adjacent_1" (row neighbors)
      - "cross"
      - "line_2" (primary + behind 1 + behind 2)
    """
    aoe = (aoe or "single").lower().strip()
    out: List[int] = [primary_slot]

    if aoe == "single":
        return out

    if aoe == "adjacent_1":
        for s in row_neighbors(primary_slot):
            if s not in out:
                out.append(s)
        return out

    if aoe == "cross":
        for s in cross_neighbors(primary_slot):
            if s not in out:
                out.append(s)
        return out

    if aoe == "line_2":
        s1 = behind_in_line(primary_slot, steps=1)
        if s1 is not None and s1 not in out:
            out.append(s1)
        s2 = behind_in_line(primary_slot, steps=2)
        if s2 is not None and s2 not in out:
            out.append(s2)
        return out

    # Unknown AoE: fallback to single target
    return out


def build_active_cast_plan(
    state: BattleState,
    caster: Unit,
    skill_key: str,
    target_team: str,
    target_slot: int,
) -> ActiveCastPlan:
    """
    Build the cast plan AND mutate caster resources/cooldown (rules-level responsibility).
    Damage/status execution is done by the engine from the returned plan.
    """
    ok, reason = can_cast_active(caster, skill_key)
    if not ok:
        raise SkillCastError(f"Cannot cast {skill_key}: {reason}")

    skill = _lazy_get_active_skill(skill_key)

    # Spend resources now (so planning matches logs/state).
    caster.ap = int(getattr(caster, "ap", 0)) - int(skill.ap_cost)
    caster.mp = int(getattr(caster, "mp", 0)) - int(skill.mp_cost)

    # Set cooldown now.
    set_cooldown(caster, skill_key, int(skill.cooldown))

    # Resolve AoE slots (defender-side slots).
    target_slots = _resolve_aoe_slots(int(target_slot), str(getattr(skill, "aoe", "single")))

    plan = ActiveCastPlan(
        skill_key=str(skill.key),
        skill_name=str(skill.name),
        caster_team=str(getattr(caster, "team", "")),
        caster_slot=int(getattr(caster, "slot", 0)),
        primary_target_team=str(target_team),
        primary_target_slot=int(target_slot),
        target_slots=target_slots,
        ap_cost=int(skill.ap_cost),
        mp_cost=int(skill.mp_cost),
        cooldown_set_to=int(skill.cooldown),
        procs=list(getattr(skill, "procs", [])),
    )

    # Optional logging
    if hasattr(state, "log"):
        state.log(
            f"CAST: {plan.caster_team}-{plan.caster_slot} uses {plan.skill_name} "
            f"-> {plan.primary_target_team}-{plan.primary_target_slot} "
            f"(AoE={getattr(skill,'aoe','single')} targets={plan.target_slots}) "
            f"AP-{plan.ap_cost} MP-{plan.mp_cost} CD={plan.cooldown_set_to}"
        )

    return plan

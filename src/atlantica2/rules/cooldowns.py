# src/atlantica2/rules/cooldowns.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from src.atlantica2.core.types import TeamId
from src.atlantica2.model.unit import Unit


@dataclass(frozen=True)
class TickConfig:
    """
    Two-turn tick rule:
    - We only decrement cooldown/duration counters every 2 TEAM turns.
    - Example: at TEAM TURN 15 in your log: "[TICK] Two-turn rule tick: cooldowns/durations -1"
    """
    every_team_turns: int = 2


def _dec_nonneg(x: int, amount: int = 1) -> int:
    return x - amount if x > 0 else 0


def should_tick(two_turn_counter: int, cfg: TickConfig) -> bool:
    """
    Return True when we should apply the -1 tick.
    We use a simple counter that increments each TEAM TURN.
    """
    return (two_turn_counter % cfg.every_team_turns) == 0


def apply_two_turn_tick_to_unit(u: Unit) -> List[str]:
    """
    Apply a -1 tick to:
      - active skill cooldowns
      - status durations
    Also perform expirations if something reaches 0.

    Returns log lines (optional).
    """
    logs: List[str] = []

    # --- Skill cooldowns ---
    # u.skill_cooldowns: Dict[str, int]
    if hasattr(u, "skill_cooldowns") and isinstance(u.skill_cooldowns, dict):
        for k in list(u.skill_cooldowns.keys()):
            old = int(u.skill_cooldowns.get(k, 0))
            new = _dec_nonneg(old, 1)
            u.skill_cooldowns[k] = new
            # No spam logging by default; enable if you want.
            # if old != new:
            #     logs.append(f"    CD tick: {u.uid} {k}: {old}->{new}")

    # --- Status durations ---
    # u.statuses: Dict[str, int]  (remaining turns)
    if hasattr(u, "statuses") and isinstance(u.statuses, dict):
        expired: List[str] = []
        for s in list(u.statuses.keys()):
            old = int(u.statuses.get(s, 0))
            new = _dec_nonneg(old, 1)
            u.statuses[s] = new
            if new == 0 and old > 0:
                expired.append(s)
        for s in expired:
            # Remove status when duration ends.
            u.statuses.pop(s, None)
            # Optional log:
            # logs.append(f"    STATUS expired: {u.uid} {s}")

    return logs


def apply_two_turn_tick(
    *,
    units: Iterable[Unit],
    team_turn: int,
    cfg: TickConfig = TickConfig(),
) -> Tuple[bool, List[str]]:
    """
    Apply the global two-turn tick on a TEAM TURN.

    Usage pattern (engine):
      - increment team_turn counter (1,2,3,...)
      - if apply_two_turn_tick(...)[0] is True => you printed "[TICK] ..."

    Returns:
      (ticked?, logs)
    """
    if team_turn <= 0:
        return False, []

    if not should_tick(team_turn, cfg):
        return False, []

    logs: List[str] = ["  [TICK] Two-turn rule tick: cooldowns/durations -1"]
    for u in units:
        logs.extend(apply_two_turn_tick_to_unit(u))
    return True, logs


def start_battle_cooldown_lock(
    *,
    units: Iterable[Unit],
    skill_base_cooldowns: Dict[str, int],
) -> None:
    """
    Important rule you defined:
    - At battle start, skills cannot be used immediately.
    - They START counting down from their cooldown value.

    This helper initializes u.skill_cooldowns[skill_key] = base_cd
    for each active skill the unit has.

    Assumptions:
    - Unit has u.skills: List[str] or similar skill keys.
    - skill_base_cooldowns maps skill_key -> base cooldown (in 'two-turn ticks' system).
    """
    for u in units:
        if not hasattr(u, "skill_cooldowns") or u.skill_cooldowns is None:
            u.skill_cooldowns = {}
        if not hasattr(u, "skills") or u.skills is None:
            continue

        for sk in u.skills:
            base_cd = int(skill_base_cooldowns.get(sk, 0))
            if base_cd > 0:
                u.skill_cooldowns[sk] = base_cd


def is_skill_ready(u: Unit, skill_key: str) -> bool:
    """
    Skill is ready when cooldown is 0 or missing.
    """
    cd = 0
    if hasattr(u, "skill_cooldowns") and isinstance(u.skill_cooldowns, dict):
        cd = int(u.skill_cooldowns.get(skill_key, 0))
    return cd <= 0


def put_skill_on_cooldown(u: Unit, skill_key: str, base_cd: int) -> None:
    """
    After using a skill, set its cooldown back to base_cd.
    base_cd is in your two-turn tick system.
    """
    if not hasattr(u, "skill_cooldowns") or u.skill_cooldowns is None:
        u.skill_cooldowns = {}
    u.skill_cooldowns[skill_key] = int(max(0, base_cd))

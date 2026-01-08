# src/atlantica2/sim/engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence

from ..model.battle_state import BattleState
from ..model.unit import Unit

from ..formulas.ap import compute_ap_gain  # expected: compute_ap_gain(unit) -> int
from ..rules import cooldowns as cooldown_rules
from ..rules import status_pipeline as status_rules
from ..rules import turn_order as turn_order_rules
from . import actions as action_rules


@dataclass(frozen=True)
class EngineConfig:
    """
    Engine-level configuration.
    Tune these without touching combat logic modules.
    """
    max_team_turns: int = 200
    action_ap_cost: int = 100
    ap_threshold: int = 100
    normal_max_actors: int = 5


def _u_label(u: Unit) -> str:
    """Human-readable label used in logs."""
    # Try common fields used in our earlier logs: "A-1 Viking warrior"
    team = getattr(u, "team", "?")
    slot = getattr(u, "slot", "?")
    name = getattr(u, "name", getattr(u, "unit_name", "Unit"))
    return f"{team}-{slot} {name}"


def _is_alive(u: Unit) -> bool:
    val = getattr(u, "is_alive", None)
    if callable(val):
        return bool(val())
    if isinstance(val, bool):
        return val
    hp = getattr(u, "hp", 1)
    return hp > 0


def _set_ap(u: Unit, ap_value: int) -> None:
    if hasattr(u, "ap"):
        u.ap = ap_value  # type: ignore[attr-defined]
    elif hasattr(u, "ap_current"):
        u.ap_current = ap_value  # type: ignore[attr-defined]
    else:
        raise AttributeError("Unit has no AP field (expected .ap or .ap_current).")


def _get_ap(u: Unit) -> int:
    if hasattr(u, "ap"):
        return int(u.ap)  # type: ignore[attr-defined]
    if hasattr(u, "ap_current"):
        return int(u.ap_current)  # type: ignore[attr-defined]
    raise AttributeError("Unit has no AP field (expected .ap or .ap_current).")


def _team_units(state: BattleState, team: str) -> List[Unit]:
    """
    Retrieve units by team with minimal assumptions about Board implementation.
    Board should ideally expose one of:
      - board.team_units(team)
      - board.living_units(team)
      - board.units (iterable of all units)
    """
    b = state.board

    if hasattr(b, "team_units"):
        return list(b.team_units(team))  # type: ignore[attr-defined]

    if hasattr(b, "units"):
        all_units = list(b.units) if not callable(b.units) else list(b.units())  # type: ignore[misc]
        return [u for u in all_units if getattr(u, "team", None) == team]

    if hasattr(b, "by_id"):
        return [u for u in b.by_id.values() if getattr(u, "team", None) == team]  # type: ignore[attr-defined]

    raise AttributeError("Board missing team accessors (expected team_units/units/by_id).")


def _living_team_units(state: BattleState, team: str) -> List[Unit]:
    units = _team_units(state, team)
    return [u for u in units if _is_alive(u)]


def _team_defeated(state: BattleState, team: str) -> bool:
    return len(_living_team_units(state, team)) == 0


class BattleEngine:
    def __init__(self, config: EngineConfig | None = None):
        self.cfg = config or EngineConfig()

    def run(self, state: BattleState) -> str:
        """
        Run the simulation until:
          - a team is defeated, or
          - max_team_turns reached.

        Returns: "A", "B", or "DRAW"
        """
        # Optional: battle-start aura hook
        if hasattr(status_rules, "on_battle_start"):
            status_rules.on_battle_start(state)  # type: ignore[attr-defined]

        for _ in range(self.cfg.max_team_turns):
            winner = self.step_team_turn(state)
            if winner:
                return winner

        return "DRAW"

    def step_team_turn(self, state: BattleState) -> str:
        """
        Execute exactly one TEAM TURN (Team A or Team B acts).
        Returns winner team key "A"/"B" if battle ends; else "".
        """
        # Increment global team turn counter (1-based in logs)
        state.team_turn = int(getattr(state, "team_turn", 0)) + 1

        starts_team = getattr(state, "starts_team", "A")
        # Determine acting team from turn order rules (fallback if missing)
        team = (
            turn_order_rules.get_acting_team(state.team_turn, starts_team)
            if hasattr(turn_order_rules, "get_acting_team")
            else (starts_team if state.team_turn % 2 == 1 else ("B" if starts_team == "A" else "A"))
        )

        state.log("=" * 42)
        state.log(f"TEAM TURN {state.team_turn} - Team {team} starts")
        state.log("=" * 42)

        # Two-turn tick for cooldowns/durations (if your rule module supports it)
        if hasattr(cooldown_rules, "maybe_two_turn_tick"):
            ticked = cooldown_rules.maybe_two_turn_tick(state)  # type: ignore[attr-defined]
            if ticked:
                state.log("  [TICK] Two-turn rule tick: cooldowns/durations -1")

        # Turn-start status processing (poison ticks, etc.) if implemented
        if hasattr(status_rules, "on_team_turn_start"):
            status_rules.on_team_turn_start(state, team)  # type: ignore[attr-defined]

        # AP gain for acting team only (as in your logs)
        living = _living_team_units(state, team)
        for u in living:
            before = _get_ap(u)
            gain = int(compute_ap_gain(u))
            after = before + gain
            _set_ap(u, after)
            state.log(f"  AP gain: {_u_label(u)}: {before} -> {after} (+{gain})")

        # Build turn rule (2/3/4/5 opener then normal)
        if hasattr(turn_order_rules, "get_turn_rule"):
            rule = turn_order_rules.get_turn_rule(
                team_turn=state.team_turn,
                starts_team=starts_team,
                ap_threshold=self.cfg.ap_threshold,
                normal_max_actors=self.cfg.normal_max_actors,
            )  # type: ignore[attr-defined]
            max_actors = int(rule.max_actors)
            ignore_ap_rule = bool(rule.ignore_ap_rule)
            ap_threshold = int(getattr(rule, "ap_threshold", self.cfg.ap_threshold))
        else:
            # Fallback rule: exactly as your spec when starts_team acts first.
            opener = {1: 2, 2: 3, 3: 4, 4: 5}
            max_actors = opener.get(state.team_turn, self.cfg.normal_max_actors)
            ignore_ap_rule = state.team_turn in (1, 2, 3, 4)
            ap_threshold = self.cfg.ap_threshold

        # Select actors (highest AP first)
        candidates = _living_team_units(state, team)
        candidates.sort(key=_get_ap, reverse=True)

        if not ignore_ap_rule:
            candidates = [u for u in candidates if _get_ap(u) >= ap_threshold]

        actors = candidates[:max_actors]

        if hasattr(turn_order_rules, "format_actor_list"):
            actor_str = turn_order_rules.format_actor_list(actors)  # type: ignore[attr-defined]
        else:
            actor_str = ", ".join([f"{getattr(a,'slot','?')}(AP={_get_ap(a)})" for a in actors])

        rule_name = "IGNORE_AP_RULE" if ignore_ap_rule else f"AP>={ap_threshold}"
        state.log(f"  Actors selected: max={max_actors}, rule={rule_name}: {actor_str}")

        # Execute actions
        for actor in actors:
            if not _is_alive(actor):
                continue

            # Optional: per-actor turn-start status hook (stun check, etc.)
            if hasattr(status_rules, "on_actor_action_start"):
                can_act = status_rules.on_actor_action_start(state, actor)  # type: ignore[attr-defined]
                if can_act is False:
                    continue

            # Delegate action selection/execution to sim.actions
            # Expected: execute_default_action(state, actor, team, action_ap_cost)
            if hasattr(action_rules, "execute_default_action"):
                action_rules.execute_default_action(
                    state=state,
                    actor=actor,
                    acting_team=team,
                    action_ap_cost=self.cfg.action_ap_cost,
                )  # type: ignore[attr-defined]
            else:
                raise RuntimeError(
                    "Missing sim.actions.execute_default_action(). "
                    "Create it to resolve basic attack/skills."
                )

            # Optional: per-actor after-action hook
            if hasattr(status_rules, "on_actor_action_end"):
                status_rules.on_actor_action_end(state, actor)  # type: ignore[attr-defined]

            # Victory check
            enemy = "B" if team == "A" else "A"
            if _team_defeated(state, enemy):
                state.log(f"==> Team {team} wins (Team {enemy} defeated)")
                return team

        # End-of-team-turn status hook (if needed)
        if hasattr(status_rules, "on_team_turn_end"):
            status_rules.on_team_turn_end(state, team)  # type: ignore[attr-defined]

        return ""

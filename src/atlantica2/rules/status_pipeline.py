# src/atlantica2/rules/status_pipeline.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.atlantica2.data.status_effects import get_status, StatusKind, TickTiming, StatusDef


# -------------------------
# Runtime status instance
# -------------------------

@dataclass
class StatusInstance:
    key: str
    remaining: int
    stacks: int = 1
    params: Dict[str, Any] = field(default_factory=dict)
    source_uid: Optional[str] = None  # e.g. "A-3"


# -------------------------
# Status output (what status changes)
# -------------------------

@dataclass
class StatusEvent:
    """
    Engine can consume these events to apply damage/heal/log.
    """
    type: str                      # "damage", "log", ...
    target_uid: str
    amount: float = 0.0
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StatusFrame:
    """
    Aggregated effects from all statuses for a specific phase.
    Keep this small and extend when needed.
    """
    # Action permission flags
    can_act: bool = True
    can_use_active_skills: bool = True
    can_basic_attack: bool = True
    ignore_passives: bool = False
    block_ap_gain: bool = False

    # Damage multipliers
    attack_damage_mult: float = 1.0     # Weaken -> < 1.0
    skill_damage_mult: float = 1.0      # Panic -> < 1.0
    damage_taken_mult: float = 1.0      # Brand -> > 1.0

    # Stat deltas (applied by engine/formulas later)
    ap_gain_base_delta: float = 0.0     # Slow/Chill
    mhr_base_delta: float = 0.0         # Chill
    accuracy_inc_pct_delta: float = 0.0 # Dull (negative)

    armour_base_delta: float = 0.0      # Shred
    mr_base_delta: float = 0.0          # Sunder

    # Events (DoT etc.)
    events: List[StatusEvent] = field(default_factory=list)


# -------------------------
# Helpers: normalize container
# -------------------------

def _ensure_status_map(unit: Any) -> Dict[str, StatusInstance]:
    """
    Normalize unit.statuses into Dict[str, StatusInstance] and return it.
    Supports:
      - dict[str, int]  (remaining)
      - dict[str, dict] ({"remaining":..,"stacks":..,"params":..})
      - dict[str, StatusInstance]
      - list[str] (keys)
    """
    statuses = getattr(unit, "statuses", None)

    # Default empty map
    if statuses is None:
        statuses = {}
        setattr(unit, "statuses", statuses)

    # If already correct
    if isinstance(statuses, dict):
        # convert dict[str, int] or dict[str, dict] to dict[str, StatusInstance]
        out: Dict[str, StatusInstance] = {}
        for k, v in statuses.items():
            if isinstance(v, StatusInstance):
                out[str(k)] = v
            elif isinstance(v, int):
                out[str(k)] = StatusInstance(key=str(k), remaining=int(v))
            elif isinstance(v, dict):
                out[str(k)] = StatusInstance(
                    key=str(k),
                    remaining=int(v.get("remaining", 0)),
                    stacks=int(v.get("stacks", 1)),
                    params=dict(v.get("params", {})),
                    source_uid=v.get("source_uid"),
                )
            else:
                raise TypeError(f"Unsupported status value: {k} -> {type(v)}")
        setattr(unit, "statuses", out)
        return out

    # If list[str]
    if isinstance(statuses, list):
        out = {}
        for k in statuses:
            sd = get_status(str(k))
            out[str(k)] = StatusInstance(key=str(k), remaining=int(sd.default_duration))
        setattr(unit, "statuses", out)
        return out

    raise TypeError(f"Unsupported unit.statuses container: {type(statuses)}")


def cleanup_expired_statuses(unit: Any) -> None:
    sm = _ensure_status_map(unit)
    for k in list(sm.keys()):
        if sm[k].remaining <= 0:
            sm.pop(k, None)


def has_status(unit: Any, key: str) -> bool:
    sm = _ensure_status_map(unit)
    inst = sm.get(key)
    return inst is not None and inst.remaining > 0


# -------------------------
# Apply / refresh / stack
# -------------------------

def apply_status(
    unit: Any,
    key: str,
    *,
    duration: Optional[int] = None,
    stacks_add: int = 1,
    params: Optional[Dict[str, Any]] = None,
    source_uid: Optional[str] = None,
) -> bool:
    """
    Apply a status to a unit with stacking/refresh rules.
    Returns True if applied, False if blocked (e.g., immunity).
    """
    sm = _ensure_status_map(unit)
    sd = get_status(key)

    # Immunity blocks debuffs (and control/dot) by default.
    if has_status(unit, "immunity") and not sd.is_positive:
        return False

    dur = int(duration if duration is not None else sd.default_duration)
    if dur < 0:
        dur = 0

    existing = sm.get(key)
    if existing is None:
        sm[key] = StatusInstance(
            key=key,
            remaining=dur,
            stacks=1 if not sd.stackable else max(1, min(sd.max_stacks, stacks_add)),
            params=dict(params or {}),
            source_uid=source_uid,
        )
        return True

    # Already exists
    if sd.stackable:
        existing.stacks = max(1, min(sd.max_stacks, existing.stacks + int(stacks_add)))

    if sd.refresh_on_reapply:
        existing.remaining = max(existing.remaining, dur)

    # Merge/override params if provided
    if params:
        existing.params.update(params)

    if source_uid is not None:
        existing.source_uid = source_uid

    return True


# -------------------------
# Priority & phase execution
# -------------------------

# Priority order for flags/multipliers (extend later):
# CONTROL first (stun/immobilized), then locks (silence/disarm/break),
# then multipliers (panic/weaken/brand), then stat deltas (slow/chill/shred/sunder),
# then DOT events (bleeding).
PRIORITY: List[str] = [
    "stun",
    "immobilized",
    "silence",
    "disarm",
    "break",
    "panic",
    "weaken",
    "brand",
    "dull",
    "slow",
    "chill",
    "shred",
    "sunder",
    "bleeding",
]


def _pct_less_to_mult(pct_less: float) -> float:
    """
    pct_less = 20 => 0.8
    """
    p = max(0.0, float(pct_less))
    return max(0.0, 1.0 - p / 100.0)


def _pct_more_to_mult(pct_more: float) -> float:
    """
    pct_more = 20 => 1.2
    """
    p = float(pct_more)
    return max(0.0, 1.0 + p / 100.0)


def _iter_statuses_in_order(unit: Any) -> List[Tuple[str, StatusInstance, StatusDef]]:
    sm = _ensure_status_map(unit)
    keys = [k for k in PRIORITY if k in sm and sm[k].remaining > 0]
    # include unknown statuses after the known ones, stable order
    for k in sm.keys():
        if k not in keys and sm[k].remaining > 0:
            keys.append(k)
    out: List[Tuple[str, StatusInstance, StatusDef]] = []
    for k in keys:
        inst = sm[k]
        out.append((k, inst, get_status(k)))
    return out


# -------------------------
# Phase APIs used by sim/engine
# -------------------------

def build_start_turn_frame(unit: Any) -> StatusFrame:
    """
    Called at unit's action start (or team turn start per your engine design).
    This collects flags and creates DoT events with TickTiming.ON_TURN_START.
    """
    cleanup_expired_statuses(unit)
    frame = StatusFrame()
    uid = str(getattr(unit, "uid", f"{getattr(unit,'team','?')}-{getattr(unit,'slot','?')}"))

    for key, inst, sd in _iter_statuses_in_order(unit):
        # CONTROL flags
        if key == "stun":
            from src.atlantica2.rules.status_handlers.stun import on_start_turn as _stun_start
            _stun_start(unit, inst, frame)

        elif key == "immobilized":
            frame.can_act = False

        # Locks
        elif key == "silence":
            frame.can_use_active_skills = False

        elif key == "disarm":
            frame.can_basic_attack = False

        elif key == "break":
            frame.ignore_passives = True

        # Multipliers
        elif key == "panic":
            pct = float(inst.params.get("skill_damage_less_pct", 0.0))
            frame.skill_damage_mult *= _pct_less_to_mult(pct)

        elif key == "weaken":
            pct = float(inst.params.get("attack_damage_less_pct", 0.0))
            frame.attack_damage_mult *= _pct_less_to_mult(pct)

        elif key == "brand":
            pct = float(inst.params.get("damage_taken_more_pct", 0.0))
            frame.damage_taken_mult *= _pct_more_to_mult(pct)

        elif key == "dull":
            frame.accuracy_inc_pct_delta += float(inst.params.get("accuracy_inc_pct", 0.0))

        # Stat deltas
        elif key == "slow":
            # at turn start only; consumed by engine when calculating AP gain
            frame.ap_gain_base_delta += float(inst.params.get("ap_base_delta", 0.0))

        elif key == "chill":
            frame.ap_gain_base_delta += float(inst.params.get("ap_base_delta", -5.0))
            frame.mhr_base_delta += float(inst.params.get("mhr_base_delta", -10.0))

        elif key == "shred":
            frame.armour_base_delta += float(inst.params.get("armour_base_delta", 0.0))

        elif key == "sunder":
            frame.mr_base_delta += float(inst.params.get("mr_base_delta", 0.0))

        # DOT events
        elif key == "bleeding":
            from src.atlantica2.rules.status_handlers.bleeding import on_start_turn as _bleed_start
            _bleed_start(unit, inst, frame)

        else:
            # Unknown status: ignore at this stage (handlers can be added later).
            pass

    # If cannot act, you may want to also disable basic attack/skills implicitly.
    if not frame.can_act:
        frame.can_basic_attack = False
        frame.can_use_active_skills = False

    # Optional: add a compact log event
    if not frame.can_act:
        frame.events.append(StatusEvent(type="log", target_uid=uid, payload={"msg": f"{uid} cannot act due to status"}))

    return frame


def build_before_damage_frame(attacker: Any, defender: Any) -> StatusFrame:
    """
    Hook for future: e.g. guard, shields, damage redirects.
    For now, only defender damage_taken_mult from Brand is computed at start-turn frame.
    """
    cleanup_expired_statuses(attacker)
    cleanup_expired_statuses(defender)
    return StatusFrame()


def build_after_damage_frame(attacker: Any, defender: Any) -> StatusFrame:
    """
    Hook for future: e.g. on-hit procs, reflect, lifesteal.
    """
    cleanup_expired_statuses(attacker)
    cleanup_expired_statuses(defender)
    return StatusFrame()

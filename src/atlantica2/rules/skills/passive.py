# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

from src.atlantica2.model.effect import Proc

if TYPE_CHECKING:
    from src.atlantica2.model.unit import Unit


@dataclass(frozen=True)
class PassiveBundle:
    """
    A normalized collection of passive procs coming from many sources.
    Engine decides when to trigger (on_attack / on_hit / start_turn / etc.).
    """
    source: str
    procs: List[Proc]


def _get_list(obj: object, attr: str) -> list:
    v = getattr(obj, attr, None)
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return list(v)


def collect_passive_bundles(unit: Unit) -> List[PassiveBundle]:
    """
    Collect passive procs from:
      - weapon package
      - offhand package
      - passive skills list (optional)
    This function is intentionally "data-agnostic" (duck typing).
    """
    bundles: List[PassiveBundle] = []

    # Weapon package (created by data/weapons.py)
    weapon_pkg = getattr(unit, "weapon_package", None)
    if isinstance(weapon_pkg, dict):
        procs = weapon_pkg.get("procs", [])
        if procs:
            bundles.append(PassiveBundle(source=f"weapon:{weapon_pkg.get('key','?')}", procs=list(procs)))

    # Offhand package (created by data/offhands.py)
    offhand_pkg = getattr(unit, "offhand_package", None)
    if isinstance(offhand_pkg, dict):
        procs = offhand_pkg.get("procs", [])
        if procs:
            bundles.append(PassiveBundle(source=f"offhand:{offhand_pkg.get('key','?')}", procs=list(procs)))

    # Passive skills (optional): unit.passive_skill_keys = ["...", ...]
    passive_keys = _get_list(unit, "passive_skill_keys")
    if passive_keys:
        # Lazy import so this file can exist before skills_data is fully built.
        from src.atlantica2.data.skills_data import get_passive_skill  # lazy

        for k in passive_keys:
            s = get_passive_skill(str(k))
            procs = list(getattr(s, "procs", []))
            if procs:
                bundles.append(PassiveBundle(source=f"passive_skill:{s.key}", procs=procs))

    return bundles


def collect_passive_procs(unit: Unit, trigger: Optional[str] = None) -> List[Proc]:
    """
    Flatten all passive bundles into a single list.
    If trigger is provided, filter by proc.params["trigger"] == trigger.
    """
    out: List[Proc] = []
    for b in collect_passive_bundles(unit):
        for p in b.procs:
            if trigger is None:
                out.append(p)
                continue
            trg = (p.params or {}).get("trigger")
            if trg == trigger:
                out.append(p)
    return out

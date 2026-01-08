# src/atlantica2/data/gear.py
# All comments in this project are written in English.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


# Keep StatKey lightweight for now to avoid import dependency issues.
# We can later move this into core/types.py and import it everywhere.
StatKey = Literal[
    "hp",
    "mp",
    "attack",
    "armour",
    "mr",
    "ap_base",   # base AP gain per team turn (before inc/more/less)
    "ap_inc",    # +X% increased AP gain
    "ap_more",   # +X% more AP gain
    "ap_less",   # -X% less AP gain (store as positive 20 = 20% less)
    "str",
    "dex",
    "int",
    "vit",
    "accuracy",
    "evasion",
    "skill_accuracy",
    "skill_evasion",
    "cc",
    "crd",
    "mhr",
]


ModTag = Literal["base", "inc", "more", "less"]


GearSlot = Literal[
    "helmet",
    "armor",
    "gloves",
    "boots",
    "weapon_main",
    "weapon_off",
    "ring",
    "necklace",
    "belt",
    "misc",
]


@dataclass(frozen=True)
class StatMod:
    """
    A single stat modifier line.

    - tag="base": +X base (flat) added into Total Base{Stat}
    - tag="inc" : +X% increased (additive among inc lines), value is in percent (10 means +10%)
    - tag="more": +X% more (multiplicative), value is in percent
    - tag="less": +X% less (multiplicative), value is in percent (20 means 20% less => multiplier 0.8)
    """

    stat: StatKey
    tag: ModTag
    value: float
    source: str = ""


@dataclass
class GearItem:
    """
    A gear item contains multiple StatMod lines.
    """

    name: str
    slot: GearSlot
    mods: List[StatMod] = field(default_factory=list)


@dataclass
class GearSet:
    """
    All equipped items of a unit.
    """

    items: Dict[GearSlot, GearItem] = field(default_factory=dict)

    def equip(self, item: GearItem) -> None:
        self.items[item.slot] = item

    def unequip(self, slot: GearSlot) -> None:
        self.items.pop(slot, None)

    def all_mods(self) -> List[StatMod]:
        out: List[StatMod] = []
        for it in self.items.values():
            out.extend(it.mods)
        return out


def make_basic_gear_from_k(
    *,
    k: float,
    name: str = "Prototype Gear",
    # Base stats as "%K base" (use 1.0 = 100%K, 0.5 = 50%K, 25.0 = 2500%K)
    armour_base_pct_k: float = 0.0,
    mr_base_pct_k: float = 0.0,
    hp_base_pct_k: float = 0.0,
    mp_base_pct_k: float = 0.0,
    attack_base_pct_k: float = 0.0,
    # Optional flat base AP gain contribution
    ap_base_flat: Optional[float] = None,
) -> GearSet:
    """
    Quick constructor for your Excel-style setup:
    - armour = X%K base
    - mr     = X%K base
    - hp     = X%K base
    - mp     = X%K base
    - attack = X%K base

    This function ONLY creates "base" mods.
    Increased/more/less can be added later via separate items/mods.
    """

    mods: List[StatMod] = []

    def add_base(stat: StatKey, val: float, src: str) -> None:
        if val != 0:
            mods.append(StatMod(stat=stat, tag="base", value=val, source=src))

    add_base("armour", armour_base_pct_k * k, f"{name}: armour {armour_base_pct_k}K")
    add_base("mr", mr_base_pct_k * k, f"{name}: mr {mr_base_pct_k}K")
    add_base("hp", hp_base_pct_k * k, f"{name}: hp {hp_base_pct_k}K")
    add_base("mp", mp_base_pct_k * k, f"{name}: mp {mp_base_pct_k}K")
    add_base("attack", attack_base_pct_k * k, f"{name}: attack {attack_base_pct_k}K")

    if ap_base_flat is not None and ap_base_flat != 0:
        add_base("ap_base", ap_base_flat, f"{name}: ap_base flat")

    # Put everything into one item for now (easy for prototype).
    item = GearItem(name=name, slot="armor", mods=mods)

    gs = GearSet()
    gs.equip(item)
    return gs


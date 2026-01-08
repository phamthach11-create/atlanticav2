# src/atlantica2/formulas/stats.py
# All comments in this project are written in English.

from __future__ import annotations

from typing import Any, Iterable, Optional, Tuple


def _norm_tag(tag: Any) -> str:
    s = str(tag).lower()
    # support Enum string like "ModTag.INC" or "inc"
    if "." in s:
        s = s.split(".")[-1]
    return s


def _iter_mod_tuples(mods: Iterable[Any]) -> Iterable[Tuple[str, str, float]]:
    """
    Normalize any mod shape into (stat_key, tag, value).

    Supported:
    - objects with attributes: .stat .tag .value
    - dict: {"stat": ..., "tag": ..., "value": ...}
    - tuple/list: (stat, tag, value)
    """
    for m in mods:
        if m is None:
            continue
        if hasattr(m, "stat") and hasattr(m, "tag") and hasattr(m, "value"):
            yield str(getattr(m, "stat")), _norm_tag(getattr(m, "tag")), float(getattr(m, "value"))
        elif isinstance(m, dict):
            yield str(m["stat"]), _norm_tag(m["tag"]), float(m["value"])
        elif isinstance(m, (tuple, list)) and len(m) == 3:
            yield str(m[0]), _norm_tag(m[1]), float(m[2])
        else:
            raise TypeError(f"Unsupported mod type: {type(m)} -> {m}")


def evaluate_stat(
    *,
    stat_key: str,
    base_value: float,
    mods: Iterable[Any],
    clamp_min: Optional[float] = None,
    clamp_max: Optional[float] = None,
) -> float:
    """
    Stat = (base_value + sum(base)) * (1 + sum(inc)/100) * Π(1 + more/100) * Π(1 + less/100)

    Notes:
    - We store percentages as "percent points" (e.g., +20 means +20%).
    - For 'less', if data is stored as +20 (meaning 20% less), we convert to -20 internally.
      If data already uses negative (e.g., -20), we keep it.
    """
    base_add = 0.0
    inc_sum = 0.0
    more_mul = 1.0
    less_mul = 1.0

    for s, tag, v in _iter_mod_tuples(mods):
        if s != stat_key:
            continue
        if tag == "base":
            base_add += v
        elif tag == "inc":
            inc_sum += v
        elif tag == "more":
            more_mul *= (1.0 + v / 100.0)
        elif tag == "less":
            # accept both conventions: -20 or +20 meaning "less 20%"
            vv = v if v <= 0 else -v
            less_mul *= (1.0 + vv / 100.0)
        else:
            # ignore unknown tags so we can extend later
            continue

    out = (base_value + base_add) * (1.0 + inc_sum / 100.0) * more_mul * less_mul

    if clamp_min is not None:
        out = max(clamp_min, out)
    if clamp_max is not None:
        out = min(clamp_max, out)
    return out

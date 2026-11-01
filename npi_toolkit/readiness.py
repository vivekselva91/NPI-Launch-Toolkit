"""Build readiness: clear-to-build and issue burn-down for C/D builds."""
from __future__ import annotations

import pandas as pd


def clear_to_build(bom: pd.DataFrame, inventory: pd.DataFrame, build_plan: pd.DataFrame) -> pd.DataFrame:
    """Shortage view of every part against every planned build.

    bom:        part, qty_per_unit
    inventory:  part, on_hand, inbound_qty, inbound_date
    build_plan: build, date, units
    """
    rows = []
    consumed = {p: 0 for p in bom["part"]}   # parts used by earlier builds
    inv_by_part = inventory.set_index("part")
    for _, b in build_plan.sort_values("date").iterrows():
        for _, p in bom.iterrows():
            inv = inv_by_part.loc[p["part"]]
            arrived = inv["inbound_qty"] if pd.Timestamp(inv["inbound_date"]) <= pd.Timestamp(b["date"]) else 0
            available = inv["on_hand"] + arrived - consumed[p["part"]]
            need = p["qty_per_unit"] * b["units"]
            consumed[p["part"]] += min(need, max(available, 0))
            rows.append({"build": b["build"], "date": b["date"], "part": p["part"],
                         "need": need, "available": available,
                         "shortage": max(0, need - available),
                         "buildable_units": int(available // p["qty_per_unit"])})
    df = pd.DataFrame(rows)
    return df


def buildable_by_build(ctb: pd.DataFrame) -> pd.DataFrame:
    """Units each build can actually make (limited by the scarcest part)."""
    return ctb.groupby(["build", "date"], as_index=False).agg(
        planned=("need", "first"), buildable=("buildable_units", "min"),
        limiting_part=("buildable_units", lambda s: ctb.loc[s.idxmin(), "part"]))


def allocate(units_available: int, requests: pd.DataFrame) -> pd.DataFrame:
    """Allocate scarce units by priority (1 = gates design/PV release first)."""
    out = requests.sort_values("priority").copy()
    remaining, granted = units_available, []
    for q in out["requested"]:
        g = min(q, remaining)
        granted.append(g)
        remaining -= g
    out["granted"] = granted
    return out


def issue_burndown(issues: pd.DataFrame, freq: str = "W", end=None) -> pd.DataFrame:
    """Open issues over time from opened/closed dates."""
    issues = issues.copy()
    issues["opened"] = pd.to_datetime(issues["opened"])
    issues["closed"] = pd.to_datetime(issues["closed"])
    end = pd.Timestamp(end) if end is not None else issues[["opened", "closed"]].max().max()
    idx = pd.date_range(issues["opened"].min(), end, freq=freq)
    open_counts = [((issues["opened"] <= d) & ((issues["closed"].isna()) | (issues["closed"] > d))).sum() for d in idx]
    return pd.DataFrame({"date": idx, "open_issues": open_counts})

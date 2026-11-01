"""Line balancing and constraint analysis for NPI ramp readiness.

Load = demand x cycle time / (available time x parallel cells).
The station with the highest load is the constraint; anything above the
planning ceiling (default 85%) needs action before run-at-rate.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class LinePlan:
    demand_per_day: float          # units/day required
    shifts: int = 2
    net_hours_per_shift: float = 10.5
    ceiling: float = 0.85          # max planned load, leaves room for OEE losses

    @property
    def available_s(self) -> float:
        return self.shifts * self.net_hours_per_shift * 3600

    @property
    def takt_s(self) -> float:
        return self.available_s / self.demand_per_day


def station_loading(stations: pd.DataFrame, plan: LinePlan,
                    cycle_col: str = "cycle_s") -> pd.DataFrame:
    """Return per-station effective cycle, load, and max daily output."""
    df = stations.copy()
    cells = df.get("cells", 1)
    df["effective_s"] = df[cycle_col] / cells
    df["load"] = df["effective_s"] / plan.takt_s
    df["max_units_day"] = plan.available_s / df["effective_s"]
    df["status"] = pd.cut(
        df["load"], bins=[0, plan.ceiling, 1.0, float("inf")],
        labels=["OK", "Above ceiling", "Over capacity"])
    return df


def constraint(stations: pd.DataFrame, plan: LinePlan, cycle_col: str = "cycle_s") -> pd.Series:
    """The single station that limits line output."""
    df = station_loading(stations, plan, cycle_col)
    return df.loc[df["load"].idxmax()]


def floor_check(predicted_max: float, measured: float) -> float:
    """Implied uptime if the predicted constraint is the real one.

    If measured output / predicted max lands near your known uptime (~0.9-0.98),
    the model has found the true constraint.
    """
    return measured / predicted_max

"""Reproduce the case-study analysis and charts with synthetic data.

Run from the repo root:  python examples/run_all.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from npi_toolkit import line_balance as lb, physics as ph, readiness as rd  # noqa: E402

DATA, DOCS = ROOT / "data", ROOT / "docs"
DOCS.mkdir(exist_ok=True)
INK, MUTED, ACCENT, BLUE = "#1B2128", "#6B7380", "#C2410C", "#1E56C8"
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK})

# 1. Line balance -----------------------------------------------------------
plan = lb.LinePlan(demand_per_day=500_000 / 250)
st = pd.read_csv(DATA / "stations.csv")
c = lb.station_loading(st, plan, "cycle_s_c_build")
d = lb.station_loading(st, plan, "cycle_s_d_build")
con = lb.constraint(st, plan, "cycle_s_c_build")
print(f"Takt: {plan.takt_s:.1f} s  |  demand {plan.demand_per_day:.0f}/day")
print(f"C-build constraint: {con['station']} at {con['load']:.0%}, max {con['max_units_day']:.0f}/day")
print(f"Implied uptime at measured 1,590/day: {lb.floor_check(con['max_units_day'], 1590):.0%}")
print(f"D-build max load: {d['load'].max():.0%} ({d.loc[d['load'].idxmax(), 'station']})\n")

fig, ax = plt.subplots(figsize=(9, 4.2))
y = range(len(st))[::-1]
ax.barh([i + 0.2 for i in y], c["load"] * 100, height=0.38, color=ACCENT, label="C build")
ax.barh([i - 0.2 for i in y], d["load"] * 100, height=0.38, color=BLUE, label="D build")
ax.axvline(100, color=INK, lw=1); ax.axvline(85, color=MUTED, lw=1, ls="--")
ax.text(101, -0.75, "takt", color=INK, fontsize=9)
ax.text(84, -0.75, "85% ceiling", color=MUTED, fontsize=9, ha="right")
ax.set_yticks(list(y)); ax.set_yticklabels(st["station"])
ax.set_xlabel("Station load (% of takt)")
for i, (lc, ld) in zip(y, zip(c["load"], d["load"])):
    ax.text(lc * 100 + 1, i + 0.2, f"{lc:.0%}", va="center", fontsize=9, color=INK)
    ax.text(ld * 100 + 1, i - 0.2, f"{ld:.0%}", va="center", fontsize=9, color=INK)
ax.legend(frameon=False, loc="lower right"); ax.set_xlim(0, 135); ax.set_ylim(-1.1, len(st) - 0.4)
ax.set_title("Station loading: constraint found at C build and removed by D build", loc="left", color=INK)
fig.tight_layout(); fig.savefig(DOCS / "station_loading.png", dpi=160); plt.close(fig)

# 2. Calibration cycle breakdown ----------------------------------------------
steps = ["Load", "LED warm-up", "Measure", "Compute & write", "Unload"]
before, after = [4, 16, 18, 4, 4], [4, 4, 10, 4, 4]
fig, ax = plt.subplots(figsize=(9, 2.6))
colors = [MUTED, ACCENT, ACCENT, MUTED, MUTED]
for row, vals in enumerate([after, before]):
    left = 0
    for s, v, col in zip(steps, vals, colors):
        ax.barh(row, v, left=left, color=col, edgecolor="white")
        if v >= 4:
            ax.text(left + v / 2, row, f"{v}s", ha="center", va="center", color="white", fontsize=9)
        left += v
    ax.text(left + 0.6, row, f"{left} s", va="center", color=INK, fontsize=10, fontweight="bold")
ax.set_yticks([0, 1]); ax.set_yticklabels(["After", "Before"]); ax.set_xlim(0, 52)
ax.set_xlabel("Seconds (orange = waiting set by LED physics)")
ax.set_title("Calibration cycle: 46 s to 26 s", loc="left", color=INK)
fig.tight_layout(); fig.savefig(DOCS / "calibration_cycle.png", dpi=160); plt.close(fig)

# 3. Clear-to-build and allocation ---------------------------------------------
ctb = rd.clear_to_build(pd.read_csv(DATA / "bom_critical.csv"), pd.read_csv(DATA / "inventory.csv"),
                        pd.read_csv(DATA / "build_plan.csv"))
print("Clear-to-build (shortages only):")
print(ctb[ctb["shortage"] > 0][["build", "part", "need", "available", "shortage"]].to_string(index=False), "\n")
alloc = rd.allocate(700, pd.read_csv(DATA / "unit_requests.csv"))
print("C build wave 1 allocation of 700 MCU-limited units:")
print(alloc[["requester", "purpose", "priority", "requested", "granted"]].to_string(index=False), "\n")

# 4. Issue burn-down -----------------------------------------------------------
issues = pd.read_csv(DATA / "issues_synthetic.csv")
bd = rd.issue_burndown(issues, freq="D", end="2024-05-05")
fig, ax = plt.subplots(figsize=(9, 3.2))
ax.plot(bd["date"], bd["open_issues"], color=BLUE, lw=2)
ax.fill_between(bd["date"], bd["open_issues"], color=BLUE, alpha=0.12)
gate = pd.Timestamp("2024-05-03")
ax.axvline(gate, color=ACCENT, lw=1.5); ax.text(gate, ax.get_ylim()[1] * 0.92, " D-build gate", color=ACCENT, fontsize=9)
ax.set_ylabel("Open build issues")
ax.set_title(f"Issue burn-down: {len(issues)} C/D build issues closed before the D gate (synthetic)", loc="left", color=INK)
fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(DOCS / "issue_burndown.png", dpi=160); plt.close(fig)

# 5. Physics checks --------------------------------------------------------------
print("First-principles checks:")
for y_mm, label in [(1.2, "nominal"), (1.6, "worst-case stack")]:
    e = ph.cantilever_snap_strain(y_mm, 1.2, 10)
    print(f"  Clip strain at {label}: {e:.2%}  (PC/ABS allowable ~2.5%)")
print(f"  Red LED flux drift for +18 K warm-up: {ph.led_flux_drift(18):+.0%}")
print(f"  Integration time at 10% vs 100% brightness: {ph.integration_time_s(0.1)/ph.integration_time_s(1):.0f}x")

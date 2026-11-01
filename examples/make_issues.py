"""Generate a synthetic C/D build issue log (no real program data)."""
import numpy as np, pandas as pd
rng = np.random.default_rng(7)
cats = ["Material", "Process", "Test", "Design", "Supplier quality", "Equipment"]
owners = ["Process eng.", "Quality", "Supply chain", "Mech design", "Test eng.", "Equipment vendor"]
start = pd.Timestamp("2024-02-12"); gate = pd.Timestamp("2024-05-03")
rows = []
for i in range(64):
    opened = start + pd.Timedelta(days=int(rng.integers(0, 60)))
    closed = min(opened + pd.Timedelta(days=int(rng.integers(3, 30))), gate - pd.Timedelta(days=int(rng.integers(0, 4))))
    closed = max(closed, opened + pd.Timedelta(days=1))
    rows.append({"id": f"BLD-{i+1:03d}", "category": rng.choice(cats), "owner": rng.choice(owners),
                 "severity": rng.choice(["High", "Medium", "Low"], p=[.25, .5, .25]),
                 "opened": opened.date(), "closed": closed.date()})
pd.DataFrame(rows).to_csv("data/issues_synthetic.csv", index=False)

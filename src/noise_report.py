"""Label-noise tables: (a) manual-audit estimate with Wilson CI, (b) cross-validated disagreement per class.  python -m src.noise_report"""
import math, numpy as np, pandas as pd
from .common import *

def wilson(k, n, z=1.96):
    p = k / n; c = (p + z * z / (2 * n)) / (1 + z * z / n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n); return c - h, c + h

a = pd.read_csv(RESULTS / "audit_dev300.csv"); rows = []
k, n = int((a.silver != a.gold_audit).sum()), len(a); lo, hi = wilson(k, n)
rows.append(dict(scope="ALL dev (audit n=300)", silver_class="all", n=n, disagree=k, rate=k / n, ci95_low=lo, ci95_high=hi))
for c, g in a.groupby("silver"):
    k = int((g.silver != g.gold_audit).sum()); lo, hi = wilson(k, len(g))
    rows.append(dict(scope="by silver label (audit)", silver_class=c, n=len(g), disagree=k, rate=k / len(g), ci95_low=lo, ci95_high=hi))
f = pd.read_csv(RESULTS / "train_cv_flags.csv"); f["strong"] = f.flagged & (f.cv_conf >= 0.7)
for c, g in f.groupby("intent"):
    rows.append(dict(scope="train: CV model disagrees with label (conf>=0.7)", silver_class=c, n=len(g), disagree=int(g.strong.sum()), rate=g.strong.mean(), ci95_low=np.nan, ci95_high=np.nan))
rows.append(dict(scope="train: CV model disagrees with label (conf>=0.7)", silver_class="all", n=len(f), disagree=int(f.strong.sum()), rate=f.strong.mean(), ci95_low=np.nan, ci95_high=np.nan))
out = pd.DataFrame(rows).round(3); out.to_csv(RESULTS / "label_noise_estimate.csv", index=False); print(out.to_string())
pairs = f[f.strong].groupby(["intent", "cv_pred"]).size().sort_values(ascending=False).head(12).reset_index(name="rows")
pairs.columns = ["silver_label", "model_says", "rows"]; pairs.to_csv(RESULTS / "label_noise_top_confusions_train.csv", index=False); print(pairs.to_string())

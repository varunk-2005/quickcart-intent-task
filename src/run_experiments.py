"""Runs every experiment and writes CSV tables into results/.   python -m src.run_experiments"""
import json, time, sys
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import ComplementNB
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from .common import *
from .features import Feats, prep_df, is_hinglish

tr, dv, te = load()
audit = pd.read_csv(RESULTS / "audit_dev300.csv")           # my blind relabel of 300 random dev rows
aud_idx = audit.dev_row.values
rows = []

def evaluate(name, pred_dev, notes=""):
    """pred_dev: predictions for all 4000 dev rows."""
    m, per = metrics(dv.intent, pred_dev)
    ma, _ = metrics(audit.gold_audit, np.asarray(pred_dev)[aud_idx])
    rows.append(dict(experiment=name, dev_silver_acc=m["accuracy"], dev_silver_macro_f1=m["macro_f1"],
                     audit300_acc=ma["accuracy"], audit300_macro_f1=ma["macro_f1"], notes=notes))
    print(f"{name:55s} silver acc={m['accuracy']:.3f} mF1={m['macro_f1']:.3f} | audit300 acc={ma['accuracy']:.3f} mF1={ma['macro_f1']:.3f}")
    return per

# ---------- E0: the starter baseline, reproduced and re-scored correctly ----------
from baseline.baseline import TaxonomyMatcher
bm = TaxonomyMatcher(); bp, _ = bm.predict(dv.utterance.tolist())
per0 = evaluate("E0 starter baseline (taxonomy TF-IDF, thr=0.10)", bp, "metrics re-computed with correct label alignment")
per0.to_csv(RESULTS / "baseline_per_class_corrected.csv", index=False)

# ---------- preprocessing variants (cached) ----------
variants = {"raw": dict(filler=False, markers=False), "filler": dict(filler=True, markers=False), "filler+markers": dict(filler=True, markers=True)}
P = {}
for k, kw in variants.items():
    t0 = time.time()
    P[k] = {n: prep_df(d, **kw) for n, d in [("tr", tr), ("dv", dv), ("te", te)]}
    print("prep", k, round(time.time() - t0, 1), "s")

def fit_pred(vk, clf, ytr=None, mask=None, keep=None):
    Xt = P[vk]["tr"][0]; y = tr.intent.values if ytr is None else ytr
    if mask is not None:
        Xt = [t for t, m in zip(Xt, mask) if m]; y = y[mask]
    f = Feats().fit(Xt); clf.fit(f.transform(Xt), y)
    return f, clf, clf.predict(f.transform(P[vk]["dv"][0]))

# ---------- E1..E3: supervised models and preprocessing ablation ----------
for vk in variants:
    _, _, p = fit_pred(vk, LogisticRegression(C=10, max_iter=400))
    evaluate(f"E{1 + list(variants).index(vk)} LR word+char, preprocessing={vk}", p)

# ---------- model family comparison (best preprocessing) ----------
vk = "filler+markers"
for nm, clf in [("LinearSVC C=0.5", LinearSVC(C=0.5)), ("ComplementNB", ComplementNB(alpha=0.1)), ("LR C=1", LogisticRegression(C=1, max_iter=400)), ("LR C=30", LogisticRegression(C=30, max_iter=500))]:
    t0 = time.time(); _, _, p = fit_pred(vk, clf); evaluate(f"M {nm}, {vk}", p, f"train+predict {time.time()-t0:.0f}s")

# ---------- label-noise cleaning on train (cross-validated, confident-learning style) ----------
Xt = P[vk]["tr"][0]; f = Feats().fit(Xt); XT = f.transform(Xt)
cvp = cross_val_predict(LogisticRegression(C=10, max_iter=400), XT, tr.intent, cv=StratifiedKFold(5, shuffle=True, random_state=0), method="predict_proba", n_jobs=2)
cls = np.array(sorted(INTENTS)); pred_cv = cls[cvp.argmax(1)]; conf = cvp.max(1)
flag = (pred_cv != tr.intent.values)
np.save("/tmp/cvp.npy", cvp)
print("train rows where CV disagrees with label:", flag.sum(), flag.mean())
for thr in [0.5, 0.7, 0.9]:
    sus = flag & (conf >= thr)
    _, _, p = fit_pred(vk, LogisticRegression(C=10, max_iter=400), mask=~sus)
    evaluate(f"N drop suspected-noisy train rows (CV conf>={thr}, n={sus.sum()})", p)
    y2 = np.where(sus, pred_cv, tr.intent.values)
    _, _, p = fit_pred(vk, LogisticRegression(C=10, max_iter=400), ytr=y2)
    evaluate(f"N relabel suspected-noisy train rows (CV conf>={thr}, n={sus.sum()})", p)

pd.DataFrame(rows).to_csv(RESULTS / "experiments_v1.csv", index=False)
tr.assign(cv_pred=pred_cv, cv_conf=conf, flagged=flag).to_csv(RESULTS / "train_cv_flags.csv", index=False)

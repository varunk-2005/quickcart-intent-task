"""Final-system evaluation (trained on train only) + all breakdown tables.   python -m src.analysis"""
import json, time, re, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from sklearn.svm import LinearSVC
from sklearn.metrics import confusion_matrix
from .common import *; from .features import *; from .system import IntentSystem
from .preprocess import prep
from baseline.baseline import TaxonomyMatcher

tr, dv, te = load(); audit = pd.read_csv(RESULTS / "audit_dev300.csv"); ai = audit.dev_row.values
bm = TaxonomyMatcher(); bpred, _ = bm.predict(dv.utterance.tolist())
S = IntentSystem().fit(tr.utterance, tr.intent); fpred = np.array(S.predict(dv.utterance))

# ---- per-class before / after ----
_, pb = metrics(dv.intent, bpred); _, pf = metrics(dv.intent, fpred)
_, pba = metrics(audit.gold_audit, np.array(bpred)[ai]); _, pfa = metrics(audit.gold_audit, fpred[ai])
pc = pb.merge(pf, on=["intent", "support"], suffixes=("_baseline", "_final"))
pc["f1_gain"] = pc.f1_final - pc.f1_baseline
pc = pc.merge(pfa[["intent", "f1"]].rename(columns={"f1": "f1_final_on_audit300"}), on="intent")
pc.round(3).to_csv(RESULTS / "per_class_before_after_dev.csv", index=False); print(pc.round(3).to_string())

# ---- headline summary ----
rows = []
for nm, p in [("starter baseline", np.array(bpred)), ("final system", fpred)]:
    m, _ = metrics(dv.intent, p); ma, _ = metrics(audit.gold_audit, p[ai])
    rows.append(dict(system=nm, dev_silver_accuracy=m["accuracy"], dev_silver_macro_f1=m["macro_f1"], dev_silver_weighted_f1=m["weighted_f1"],
                     audit300_accuracy=ma["accuracy"], audit300_macro_f1=ma["macro_f1"]))
pd.DataFrame(rows).round(4).to_csv(RESULTS / "headline_before_after.csv", index=False); print(pd.DataFrame(rows).round(4).to_string())

# ---- breakdowns on dev (silver labels!) ----
dv["pred"] = fpred; dv["bpred"] = bpred
dv["words"] = dv.utterance.str.split().str.len(); dv["info"] = [prep(u)[1] for u in dv.utterance]
dv["hinglish"] = dv.utterance.map(is_hinglish)
dv["len_bucket"] = pd.cut(dv.words, [0, 5, 9, 15, 25, 100], labels=["1-5", "6-9", "10-15", "16-25", "26+"])
dv["structure"] = np.where(dv["info"] == "none", "single request / plain", "multi-request or changed mind")
bk = []
for col in ["len_bucket", "hinglish", "structure", "info"]:
    for k, g in dv.groupby(col, observed=True):
        bk.append(dict(breakdown=col, group=str(k), n=len(g), baseline_acc=(g.bpred == g.intent).mean(), final_acc=(g.pred == g.intent).mean(),
                       final_macro_f1=metrics(g.intent, g.pred)[0]["macro_f1"]))
pd.DataFrame(bk).round(3).to_csv(RESULTS / "breakdowns_dev.csv", index=False); print(pd.DataFrame(bk).round(3).to_string())

# ---- confusion matrix (correct label order) ----
cm = pd.DataFrame(confusion_matrix(dv.intent, fpred, labels=INTENTS), index=INTENTS, columns=INTENTS); cm.to_csv(RESULTS / "confusion_final_dev.csv")

# ---- intent closeness vs confusion ----
Xtr = [prep(u)[0] for u in tr.utterance]; f = Feats().fit(Xtr); X = f.transform(Xtr)
cent = np.vstack([np.asarray(X[(tr.intent == i).values].mean(0)).ravel() for i in INTENTS]); cent /= np.linalg.norm(cent, axis=1, keepdims=True)
cos = cent @ cent.T
conf_rate = cm.values / cm.values.sum(1, keepdims=True)
pairs = []
for i in range(12):
    for j in range(i + 1, 12):
        pairs.append(dict(intent_a=INTENTS[i], intent_b=INTENTS[j], centroid_cosine=cos[i, j], confusion_rate_ab_plus_ba=conf_rate[i, j] + conf_rate[j, i]))
pp = pd.DataFrame(pairs).sort_values("centroid_cosine", ascending=False)
from scipy.stats import spearmanr
print("spearman(centroid cosine, confusion rate) =", spearmanr(pp.centroid_cosine, pp.confusion_rate_ab_plus_ba))
pp.round(4).to_csv(RESULTS / "intent_distance_vs_confusion.csv", index=False); print(pp.head(8).round(3).to_string())

# ---- learning curve, and taxonomy-only vs train data (same classifier) ----
lc = []
tax = [(n, e) for n, ex in bm.examples.items() for e in ex]
for n in [0, 92, 500, 2000, 8000, 30000]:
    if n == 0: continue
    if n == 92: t_txt = [prep(e)[0] for _, e in tax]; t_y = [i for i, _ in tax]; src = "taxonomy examples only"
    else:
        s = tr.sample(n, random_state=0) if n < len(tr) else tr
        t_txt = [prep(u)[0] for u in s.utterance]; t_y = s.intent.tolist(); src = "train.csv sample"
    ff = Feats(min_df=1).fit(t_txt); c = LinearSVC(C=0.5).fit(ff.transform(t_txt), t_y)
    p = c.predict(ff.transform([prep(u)[0] for u in dv.utterance]))
    m, _ = metrics(dv.intent, p); ma, _ = metrics(audit.gold_audit, p[ai])
    lc.append(dict(training_data=src, n_examples=len(t_txt), dev_silver_acc=m["accuracy"], dev_silver_macro_f1=m["macro_f1"], audit300_acc=ma["accuracy"], audit300_macro_f1=ma["macro_f1"]))
pd.DataFrame(lc).round(4).to_csv(RESULTS / "learning_curve_and_taxonomy_vs_train.csv", index=False); print(pd.DataFrame(lc).round(3).to_string())

# ---- starter matcher: taxonomy v1 vs repaired taxonomy v2 (same TF-IDF-centroid code, same threshold) ----
tv2 = {i["name"]: i["examples"] for i in json.load(open(ROOT / "taxonomy" / "taxonomy_v2.json", encoding="utf-8"))["intents"]}
rows_t = []
for nm, thr in [("v1 (original)", None), ("v2 (repaired)", None)]:
    m2 = TaxonomyMatcher()
    if nm.startswith("v2"):
        m2.examples = tv2; m2.centroids = m2._build_centroids()
    for T in [0.0, 0.03, 0.05, 0.10, 0.20]:
        import baseline.baseline as bb; bb.THRESHOLD = T
        p, _ = m2.predict(dv.utterance.tolist()); mm, _ = metrics(dv.intent, p); ma, _ = metrics(audit.gold_audit, np.array(p)[ai])
        rows_t.append(dict(taxonomy=nm, oos_threshold=T, dev_silver_acc=mm["accuracy"], dev_silver_macro_f1=mm["macro_f1"], audit300_acc=ma["accuracy"], audit300_macro_f1=ma["macro_f1"]))
bb.THRESHOLD = 0.10
pd.DataFrame(rows_t).round(4).to_csv(RESULTS / "starter_matcher_taxonomy_v1_vs_v2.csv", index=False); print(pd.DataFrame(rows_t).round(3).to_string())

# ---- baseline on dev rows that are verbatim taxonomy examples (leak check) ----
tex = {re.sub(r"\s+", " ", e.lower()) for _, e in tax}
isx = dv.utterance.map(lambda u: re.sub(r"\s+", " ", u.lower()) in tex)
print("dev rows equal to a taxonomy example:", isx.sum(), "baseline acc on them", (dv.bpred[isx] == dv.intent[isx]).mean(), "elsewhere", (dv.bpred[~isx] == dv.intent[~isx]).mean())

# ---- latency: single message, one thread ----
import os; os.environ["OMP_NUM_THREADS"] = "1"
msgs = te.utterance.sample(1000, random_state=0).tolist()
S.predict(msgs[:20]); t0 = time.perf_counter()
for m in msgs: S.predict([m])
ms = (time.perf_counter() - t0) / len(msgs) * 1000
lat = []
for m in msgs[:300]:
    t = time.perf_counter(); S.predict([m]); lat.append((time.perf_counter() - t) * 1000)
print("latency ms/msg mean", round(ms, 2), "p50", np.percentile(lat, 50).round(2), "p95", np.percentile(lat, 95).round(2), "p99", np.percentile(lat, 99).round(2))
import pickle, sys
pickle.dump((S.f, S.clf), open("/tmp/model.pkl", "wb")); print("model size MB", round(os.path.getsize("/tmp/model.pkl") / 1e6, 1))
pd.DataFrame([dict(hardware=f"{os.cpu_count()} vCPU sandbox, 1 thread", mean_ms=ms, p50_ms=np.percentile(lat, 50), p95_ms=np.percentile(lat, 95), p99_ms=np.percentile(lat, 99), model_mb=os.path.getsize("/tmp/model.pkl") / 1e6)]).round(3).to_csv(RESULTS / "latency.csv", index=False)

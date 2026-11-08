"""Train the final system on train+dev (silver, noise-filtered) and write the test predictions.
   python -m src.make_predictions --name candidate"""
import argparse, pandas as pd
from .common import load, ROOT, INTENTS
from .system import IntentSystem

ap = argparse.ArgumentParser(); ap.add_argument("--name", default="candidate"); a = ap.parse_args()
tr, dv, te = load()
full = pd.concat([tr, dv], ignore_index=True)
sysm = IntentSystem().fit(full.utterance, full.intent)
pred, margin = sysm.predict(te.utterance, return_margin=True)
out = pd.DataFrame({"id": te["id"], "intent": pred})
assert len(out) == 3000 and set(out.intent) <= set(INTENTS) and out.id.is_unique
path = ROOT / "submissions" / f"{a.name}_predictions.csv"; out.to_csv(path, index=False)
te.assign(pred=pred, margin=margin).to_csv(ROOT / "results" / "test_predictions_with_margin.csv", index=False)
print("noisy rows relabelled:", int(sysm.noisy_.sum()), "of", len(full)); print("wrote", path); print(out.intent.value_counts().to_string())

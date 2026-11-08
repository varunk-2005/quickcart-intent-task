"""Build a repaired taxonomy (taxonomy/taxonomy_v2.json) from the original + clean, frequent, label-pure phrases in train.
Fixes: (1) removes examples that sit under two intents or under the wrong intent, (2) fills the two empty intents,
(3) adds a one-line definition + boundary note per intent so a new agent (or a prompt) can tell neighbours apart.
Only train.csv is used (never dev/test).   python -m src.build_taxonomy_v2"""
import json, re, numpy as np, pandas as pd
from collections import Counter
from .common import *
from .preprocess import prep

tr, _, _ = load()
orig = {i["name"]: i["examples"] for i in json.load(open(DATA / "taxonomy.json"))["intents"]}
REMOVE = {  # (example, intent it was wrongly listed under) -> why
    ("where's my food", "delivery_delay"): "also listed under order_status; a bare 'where is it' is a status question",
    ("my order is incomplete", "wrong_item"): "also under missing_item; incomplete = something absent",
    ("an item is missing from my order", "wrong_item"): "something absent is missing_item (rule 4)",
    ("cancel my food order, taking too long", "delivery_delay"): "explicit request to cancel -> cancel_order (rule 1)",
}
fl = pd.read_csv(RESULTS / "train_cv_flags.csv")
good = fl[~fl.flagged]                                    # rows the CV model agrees with
txt = [prep(u, markers=False)[0] for u in good.utterance]
cnt = Counter(zip(txt, good.intent)); tot = Counter(txt)
cand = pd.DataFrame([(t, i, n, n / tot[t]) for (t, i), n in cnt.items()], columns=["text", "intent", "n", "purity"])
cand_all = cand[(cand.text.str.split().str.len().between(3, 9)) & (cand.text != "<empty>")]
cand = cand[(cand.n >= 6) & (cand.purity >= 0.95) & (cand.text.str.split().str.len().between(3, 9)) & (cand.text != "<empty>")]
wf = Counter(w for u in tr.utterance for w in prep(u, markers=False)[0].split())
new = {}
for i in INTENTS:
    keep = [e for e in orig[i] if (e.lower(), i) not in REMOVE]
    c = cand[cand.intent == i].sort_values("n", ascending=False)
    if not orig[i]:      # the two empty intents: pick confident, typo-free, distinct phrases from clean rows
        g = good[(good.intent == i) & (good.cv_conf >= 0.9)].copy()
        g["t"] = [prep(u, markers=False)[0] for u in g.utterance]
        g = g[(g.t.str.split().str.len().between(3, 9)) & g.t.map(lambda t: all(wf[w] >= 15 for w in t.split()))]
        POL = set("hi hello hey namaste pls please thanks thank you help me urgent asap team kindly check i there excuse good evening morning quickcart".split())
        g["t"] = g.t.map(lambda t: " ".join(w for w in t.split() if w not in POL))      # drop greetings / politeness
        g = g[g.t.str.split().str.len() >= 3]
        g["stem"] = g.t
        g = g.drop_duplicates("stem").sort_values("cv_conf", ascending=False)
        c = pd.DataFrame({"text": g.t.values})
    else:
        c = cand[cand.intent == i].sort_values("n", ascending=False)
    add = []
    for t in c.text:
        if len(add) >= (14 if not orig[i] else 6): break
        if not any(t == e.lower() for e in keep): add.append(t)
    new[i] = keep + add
DEF = {
 "order_status": ("Asks where the order is / what stage it is at / ETA, with no complaint.", "A complaint that it is late is delivery_delay."),
 "delivery_delay": ("Complains the order is late or slow, or says the promised time has passed.", "Neutral 'where is it / status' is order_status; an explicit 'cancel' is cancel_order."),
 "cancel_order": ("Wants the order cancelled (also 'how do I cancel').", "Cancel + refund: order not yet delivered = cancel_order; delivered = refund_request."),
 "refund_request": ("Wants money back / asks about a refund or its status.", "Refund for a delivered order. 'Charged twice, refund one' sits next to payment_failed - keep with payment_failed."),
 "missing_item": ("Something ordered did not arrive or the order is incomplete.", "Something DIFFERENT arrived = wrong_item."),
 "wrong_item": ("Received a different item, another customer's order, or the wrong variant.", "Something absent = missing_item."),
 "payment_failed": ("Payment error, money deducted without an order, stuck/declined transaction.", "Problems with a coupon/discount are promo_code_issue; payment page failing at login OTP is account_help."),
 "promo_code_issue": ("Coupon / promo / offer / discount will not apply, expired, or vanished.", "A failed payment is payment_failed even if a coupon was used."),
 "change_address": ("Wants the delivery address or drop point changed or corrected.", "Profile changes (name, phone, e-mail) are account_help."),
 "account_help": ("Login, password, OTP for login, account locked/deleted, profile details (name, email, phone), app settings.", "Delivery address changes are change_address."),
 "talk_to_agent": ("Only asks for a human / supervisor / escalation / support number.", "If another real request is also present, the other request wins (rule 5)."),
 "out_of_scope": ("Anything not about QuickCart orders, accounts or payments: small talk, greetings/thanks alone, gibberish, other companies, services QuickCart does not offer (gift cards, loyalty points, tax invoices, tipping, restaurant feedback).", "A greeting plus a real request takes the request's label."),
}
out = {"version": 2, "note": "Repaired from taxonomy.json using train.csv only (see src/build_taxonomy_v2.py).",
       "intents": [{"name": i, "definition": DEF[i][0], "boundary_note": DEF[i][1], "examples": new[i]} for i in INTENTS]}
(ROOT / "taxonomy").mkdir(exist_ok=True); json.dump(out, open(ROOT / "taxonomy" / "taxonomy_v2.json", "w"), indent=2, ensure_ascii=False)
pd.DataFrame([dict(intent=i, examples_v1=len(orig[i]), examples_v2=len(new[i])) for i in INTENTS]).to_csv(RESULTS / "taxonomy_v1_vs_v2_counts.csv", index=False)
pd.DataFrame([dict(example=e, listed_under=i, problem=w) for (e, i), w in REMOVE.items()]).to_csv(RESULTS / "taxonomy_flaws_removed.csv", index=False)
print({i: len(v) for i, v in new.items()}); print("account_help:", new["account_help"]); print("promo_code_issue:", new["promo_code_issue"])

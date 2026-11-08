"""Shared helpers: data loading, text cleaning, correct metrics."""
import re, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support, confusion_matrix

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
INTENTS = [i["name"] for i in json.load(open(DATA / "taxonomy.json", encoding="utf-8"))["intents"]]


def load():
    return (pd.read_csv(DATA / "train.csv"), pd.read_csv(DATA / "dev.csv"), pd.read_csv(DATA / "test.csv"))


def clean(t):
    """lowercase, collapse whitespace, replace long digit runs / order ids with a token (rule 8: ids never matter)."""
    t = str(t).lower()
    t = re.sub(r"#?\b(?:qc-)?\d{3,}\b", " <num> ", t)
    return " ".join(t.split())


def metrics(y, p):
    """Correct metrics. labels= is passed explicitly so names and numbers always line up."""
    pr, rc, f1, sup = precision_recall_fscore_support(y, p, labels=INTENTS, zero_division=0)
    per = pd.DataFrame({"intent": INTENTS, "precision": pr, "recall": rc, "f1": f1, "support": sup})
    return {"accuracy": accuracy_score(y, p),
            "macro_f1": f1_score(y, p, labels=INTENTS, average="macro", zero_division=0),
            "weighted_f1": f1_score(y, p, labels=INTENTS, average="weighted", zero_division=0)}, per

"""Documents how the 300-row audit sample was drawn (random_state=42 from dev.csv).
The labels in results/audit_dev300.csv (column gold_audit) were written BLIND (silver label hidden) by applying the README
rules by hand to each message - NOT by a model - and then joined with the silver labels.  They are a small pseudo-gold set,
not real gold: one annotator, 300 rows, ambiguous cases decided by the annotator."""
import pandas as pd
from .common import DATA
dv = pd.read_csv(DATA / "dev.csv")
s = dv.sample(300, random_state=42)
print(s.head())            # utterances only were shown to the annotator, in this order

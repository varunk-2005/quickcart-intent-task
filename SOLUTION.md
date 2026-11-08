# Solution overview

Final system = rule-aware text clean-up + word/char TF-IDF + LinearSVC, trained on cross-validation-relabelled silver labels.
~1 ms per message on one CPU thread, 3.7 MB model.  Full story: see the write-up (docs/writeup.docx) and results/*.csv.

## Reproduce (order matters)
```
pip install -r requirements.txt
python -m src.run_experiments      # baseline re-score, ablations, CV noise flags  -> results/experiments_v1.csv, train_cv_flags.csv
python -m src.noise_report         # label-noise tables
python -m src.build_taxonomy_v2    # repaired taxonomy -> taxonomy/taxonomy_v2.json
python -m src.analysis             # final-system numbers, per-class, breakdowns, latency (trains on train.csv only)
python -m src.make_predictions --name <your_name>   # trains on train+dev, writes submissions/<your_name>_predictions.csv
```
`results/audit_dev300.csv` was relabelled by Claude (one AI annotator), typed in by hand rather than script-generated (see src/make_audit_sample.py). `experiments/` holds the one-off scripts behind the
negative results (and-split/threshold, noise-handling variants, spelling normaliser).

## Layout
src/preprocess.py  normalise, drop filler, apply README rules 1/2/5     src/features.py  TF-IDF features, Hinglish flag
src/system.py      final classifier (+ CV noise relabelling)            src/common.py    correct metrics (explicit label order)

# Results index

**Read these first**
- `headline_before_after.csv` - starter vs final, dev (silver labels) and audit-300
- `experiment_log.csv` - every experiment, with an adopted yes/no column
- `per_class_before_after_dev.csv` - precision / recall / F1 per intent, starter vs final
- `label_noise_estimate.csv` - audit noise rate with 95% CI, and train rows the CV model contradicts
- `latency.csv` - per-message latency and model size

**Supporting**
- `audit_dev300.csv` - the 300 hand-relabelled dev rows (hand-made, not produced by a script)
- `breakdowns_dev.csv`, `confusion_final_dev.csv`, `learning_curve_and_taxonomy_vs_train.csv`, `intent_distance_vs_confusion.csv`
- `starter_matcher_taxonomy_v1_vs_v2.csv`, `taxonomy_*.csv`, `label_noise_top_confusions_train.csv`, `baseline_per_class_corrected.csv`
- `train_cv_flags.csv`, `experiments_v1.csv`, `test_predictions_with_margin.csv` - intermediate files used by the scripts

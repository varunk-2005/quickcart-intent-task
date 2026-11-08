"""The final intent system: rule-aware preprocessing + word/char TF-IDF + LinearSVC, trained on cross-validation-relabelled silver labels.

Inference path per message (all on one CPU thread):
  prep() -> TF-IDF -> LinearSVC.decision_function -> argmax  (+ gated 'X and Y' split: first request wins)
"""
import re, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.svm import LinearSVC
from .features import Feats
from .preprocess import prep

PAIR_OK = {"cancel_order", "refund_request"}      # rule 3: 'cancel and refund' must not be split


def find_noisy(texts, labels, conf=0.7, seed=0):
    """Cross-validated disagreement: a row is 'suspected noisy' if a model trained on the other folds predicts
    another label with probability >= conf."""
    f = Feats().fit(texts); X = f.transform(texts)
    proba = cross_val_predict(LogisticRegression(C=10, max_iter=400), X, labels,
                              cv=StratifiedKFold(5, shuffle=True, random_state=seed), method="predict_proba", n_jobs=2)
    cls = np.array(sorted(set(labels))); pred = cls[proba.argmax(1)]
    return (pred != np.asarray(labels)) & (proba.max(1) >= conf), pred, proba.max(1)


class IntentSystem:
    def __init__(self, C=0.5, conf=0.7, and_split=True):
        self.C, self.conf, self.and_split = C, conf, and_split

    def fit(self, utterances, labels):
        texts = [prep(u)[0] for u in utterances]; labels = np.asarray(labels)
        self.noisy_, cvpred, _ = find_noisy(texts, labels, self.conf)
        clean_labels = np.where(self.noisy_, cvpred, labels)       # relabel suspected-noisy rows (keeps all the data)
        self.f = Feats().fit(texts)
        self.clf = LinearSVC(C=self.C).fit(self.f.transform(texts), clean_labels)
        return self

    def _raw(self, texts):
        d = self.clf.decision_function(self.f.transform(texts)); return self.clf.classes_[d.argmax(1)], d

    def predict(self, utterances, return_margin=False):
        texts = [prep(u)[0] for u in utterances]
        pred, d = self._raw(texts); pred = list(pred)
        if self.and_split:
            for i, t in enumerate(texts):
                m = re.search(r"\s+and\s+", t)
                if not m: continue
                x, y = t[:m.start()].strip(), t[m.end():].strip()
                if len(x.split()) < 3 or len(y.split()) < 3: continue
                px, py = self._raw([x])[0][0], self._raw([y])[0][0]
                if px != py and {px, py} != PAIR_OK and "out_of_scope" not in (px, py):
                    pred[i] = py if px == "talk_to_agent" else px   # rule 1: first request wins; rule 5: a bare agent request loses
        return (pred, d.max(1)) if return_margin else pred

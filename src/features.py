import re, numpy as np, pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from .preprocess import prep

HINGLISH = set("mera mere meri hai nahi nahin kab karo karna kya aaj bahut paisa abhi tak aaya batao kahan chahiye wapas galat badalna insaan baat raha rahi dikha kaam der gayi bhai yaar arre namaste kaise kata kat gaya hua hui lagao do".split())


def prep_df(df, col="utterance", **kw):
    out = [prep(u, **kw) for u in df[col]]
    return [t for t, _ in out], [i for _, i in out]


def is_hinglish(u):
    return len(set(re.findall(r"[a-z]+", str(u).lower())) & HINGLISH) > 0


class Feats:
    """word 1-2gram + char_wb 2-5gram TF-IDF, fitted on the training text only."""
    def __init__(self, char=(2, 5), word=(1, 2), min_df=2):
        self.w = TfidfVectorizer(ngram_range=word, min_df=min_df, sublinear_tf=True)
        self.c = TfidfVectorizer(analyzer="char_wb", ngram_range=char, min_df=min_df, sublinear_tf=True)

    def fit(self, texts):
        self.w.fit(texts); self.c.fit(texts); return self

    def transform(self, texts):
        return hstack([self.w.transform(texts), self.c.transform(texts)]).tocsr()

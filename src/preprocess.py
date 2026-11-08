"""Structure-aware preprocessing driven by the README labelling rules.

Steps (each switchable so every step can be ablated):
  1. normalise  : lowercase, strip emoji/odd symbols, mask order ids/amounts (rule 8)
  2. drop filler: remove sentences that are chit-chat (rule 7). The filler list was found from the data:
                  21 sentences that each occur 200-1700 times, spread evenly over all 12 labels (so carry no label info).
                  Matching is fuzzy (rapidfuzz) so typos like 'my wifi is aalso actng up' are still caught.
  3. markers    : rule 2 (last request wins) -> keep text after 'scratch that', 'actually forget it', ...
                  rule 1 (first request wins) -> keep text before 'also', 'and by the way', 'plus', 'one more thing'
                  rule 5 (agent + other request -> other wins) -> if the first part is an agent request keep the second part
"""
import re
from rapidfuzz import fuzz, process

FILLERS = [
    "sorry for the long message", "i was stuck in a meeting till 5 pm", "btw the app looks good after the update",
    "my kid is crying in the background", "this is the worst day i've had this week",
    "we have guests coming over in the evening", "it's been a really long day",
    "i tried calling earlier but the line was busy", "i am at work right now and cannot talk much",
    "the weather is terrible here today", "my wifi is also acting up", "my brother told me to try your app",
    "my neighbour also uses this app", "it's my mom's birthday today", "i just moved to this area last month",
    "my friend recommended your service", "i have been a loyal customer for three years",
    "i usually order from you every weekend", "i don't usually complain about things",
    "my phone battery is almost dead so please be quick",
]
REVISION = ["actually never mind", "actually forget it", "scratch that", "ignore what i just said",
            "sorry wrong thing", "no wait forget that"]
BUT_FIRST = ["but first", "but before that"]
ALSO = [r"and by the way", r"and also", r"one more thing", r"\balso\b", r"\bplus\b", r"\bby the way\b"]
AGENT = re.compile(r"(human|agent|person|supervisor|manager|executive|customer care|customer service|"
                   r"someone from your team|escalat|senior team|real person|connect me|put me through|"
                   r"stop the bot|a bot|speak|talk to|someone who can|support)")


def normalise(u):
    t = str(u).lower()
    t = re.sub(r"[^\w\s.,!?'₹:/#-]", " ", t)              # strip emoji and symbols
    t = re.sub(r"#?\b(?:qc-?)?\d{3,}\b", " ", t)            # order ids / amounts (rule 8)
    t = re.sub(r"₹\s*", " ", t)
    return " ".join(t.split())


def _sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if s.strip(" .!?,")]


def drop_filler(t, thr=85):
    """Cut every (fuzzy) occurrence of a known filler phrase out of the text, even when it sits inside a longer sentence."""
    for _ in range(4):                                     # a message has at most ~3 fillers
        changed = False
        for f in FILLERS:
            al = fuzz.partial_ratio_alignment(f, t, score_cutoff=thr)
            if al is not None:
                t = (t[:al.dest_start] + " . " + t[al.dest_end:]).strip()
                changed = True
        if not changed:
            break
    t = re.sub(r"(\s*\.\s*)+", " . ", t)
    return t.strip(" .")


def _fuzzy_cut(t, phrases, thr=84):
    """Return (before, after) around the LAST fuzzy occurrence of any phrase (punctuation ignored), else None."""
    flat = re.sub(r"[.,!?:]", " ", t)
    flat = " ".join(flat.split())
    best = None
    for p in phrases:
        al = fuzz.partial_ratio_alignment(p, flat, score_cutoff=thr)
        if al is not None and (best is None or al.dest_start > best[0]):
            best = (al.dest_start, al.dest_end)
    if best is None:
        return None
    return flat[:best[0]].strip(), flat[best[1]:].strip()


def apply_markers(t):
    """Returns (target_text, info) where info is 'revision' / 'but_first' / 'also_first' / 'also_agent' / 'none'."""
    cut = _fuzzy_cut(t, REVISION)
    if cut and cut[1]:
        return cut[1], "revision"
    cut = _fuzzy_cut(t, BUT_FIRST)
    if cut and cut[0] and cut[1]:
        return cut[1], "but_first"
    flat = re.sub(r"\s+", " ", t)
    for pat in ALSO:
        m = re.search(r"[, ]*" + pat + r"[, :]*", flat)
        if m and flat[:m.start()].strip(" ,") and flat[m.end():].strip():
            x, y = flat[:m.start()].strip(" ,"), flat[m.end():].strip()
            if AGENT.search(x) and not AGENT.search(y):
                return y, "also_agent"
            return x, "also_first"
    return t, "none"


def prep(u, filler=True, markers=True):
    t = normalise(u)
    if filler:
        t = drop_filler(t)
    info = "none"
    if markers:
        t, info = apply_markers(t)
    t = re.sub(r"[.,!?:]", " ", t)
    t = " ".join(t.split())
    return t if t else "<empty>", info

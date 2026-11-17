"""Stage 2: draft captions on the cut timeline from the word timings -> subs_draft.tsv (start, end, text).

usage: subs_draft.py EPISODE_DIR
Traditional characters are converted to simplified. The draft MUST be proofread into subs.tsv
(misheard words, brand/finance terms, English spelling) before the graphics stage.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ep
from opencc import OpenCC

ep = Ep(sys.argv[1]); t2s = OpenCC("t2s").convert
edl = json.load(open(ep.w("edl.json"), encoding="utf-8"))["segments"]
words = [w for s in json.load(open(ep.w("transcript.json"), encoding="utf-8"))["segments"] for w in s["words"]]
MAXC, GAP, MIN_DUR = 11, 0.25, 0.6
width = lambda t: sum(1 if ord(c) > 0x2E80 else 0.55 for c in t)
cues = []
for seg in edl:
    ws = [w for w in words if min(w["e"], seg["src_out"]) - max(w["s"], seg["src_in"]) > 0.04]
    cur, c0, last = "", None, None
    def flush(end):
        global cur, c0
        txt = re.sub(r"[，。,.!?？！、]+$", "", cur.strip())
        if txt: cues.append([c0, end, t2s(txt)])
        cur, c0 = "", None
    for w in ws:
        o_s = seg["out_in"] + (w["s"] - seg["src_in"]); o_e = seg["out_in"] + (w["e"] - seg["src_in"]); tok = w["w"]
        if c0 is not None and (o_s - last > GAP or width(cur + tok) > MAXC): flush(last)
        if c0 is None: c0 = max(seg["out_in"], o_s)
        if cur and re.match(r"[A-Za-z0-9]", tok.strip()[:1] or " ") and re.search(r"[A-Za-z0-9]$", cur): cur += " "
        cur += tok.strip(); last = min(o_e, seg["out_out"])
        if re.search(r"[，。,.!?？！]$", tok): flush(last)
    if c0 is not None: flush(last)
for i, c in enumerate(cues):
    nxt = cues[i + 1][0] if i + 1 < len(cues) else c[1] + 1
    c[1] = min(max(c[1] + 0.15, c[0] + MIN_DUR), nxt - 0.02)
open(ep.p("subs_draft.tsv"), "w", encoding="utf-8").write("".join(f"{a:.2f}\t{b:.2f}\t{t}\n" for a, b, t in cues))
print(f"{len(cues)} draft cues -> subs_draft.tsv  (proofread into subs.tsv)")

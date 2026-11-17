"""After trimming the cut (blocks.json changed), move every hand-placed time after the edit point.

usage: shift.py EPISODE_DIR CUT_T DELTA [DROP_FROM DROP_TO]
CUT_T, DELTA: cut-timeline seconds; DELTA > 0 means the cut got SHORTER by that much.
Rewrites subs.tsv (cues fully inside [DROP_FROM, DROP_TO) are removed), kinetic.json, cards.json,
mg.json, episode.json (steps, cta, designer_cards). Keeps *.bak copies.
Find DELTA by comparing work/edl.json before/after (edl.py prints the new length).
"""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ep

ep = Ep(sys.argv[1]); CUT, D = float(sys.argv[2]), float(sys.argv[3])
drop = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else None
sh = lambda x: round(x - D, 3) if isinstance(x, (int, float)) and not isinstance(x, bool) and x >= CUT else x
TIME_KEYS = {"a", "b", "t", "t_value", "out_in", "out_out", "big_at", "crack_at", "gift_at", "checks"}

def walk(o, key=None):
    if isinstance(o, dict): return {k: walk(v, k) for k, v in o.items()}
    if isinstance(o, list):
        if key == "sfx": return [[sh(s[0]), *s[1:]] for s in o]          # mg.json: [t, id, in, out, peak, target]
        if key == "steps": return [[sh(s[0]), sh(s[1]), s[2]] for s in o]
        return [walk(v, key) for v in o]
    return sh(o) if key in TIME_KEYS else o

for name in ("kinetic.json", "cards.json", "mg.json", "episode.json"):
    p = ep.p(name)
    if not os.path.exists(p): continue
    shutil.copy(p, p + ".bak")
    ep.save(name, walk(json.load(open(p, encoding="utf-8"))))
p = ep.p("subs.tsv"); shutil.copy(p, p + ".bak"); out, dropped = [], []
for line in open(p + ".bak", encoding="utf-8"):
    if not line.strip(): continue
    a, b, t = line.rstrip("\n").split("\t"); a, b = float(a), float(b)
    if drop and a >= drop[0] and b <= drop[1]: dropped.append(t); continue
    out.append(f"{sh(a):.2f}\t{sh(b):.2f}\t{t}")
open(p, "w", encoding="utf-8").write("\n".join(out) + "\n")
print(f"shifted every time >= {CUT} by -{D}s; dropped captions: {dropped}")

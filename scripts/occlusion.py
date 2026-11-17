"""Front or behind? For every kinetic item, measure how much the presenter covers it and decide.

usage: occlusion.py EPISODE_DIR  -> work/occlusion.json (+ a table)
coverage = mean share of the item's text box covered by the matte (alpha > 0.5), from 0.3 s after it appears.
  > 25 %                      -> FRONT (too much hidden to read)
  digits / RM and > 10 %      -> FRONT (numbers are read whole)
  otherwise                   -> BEHIND (a little overlap reads as depth)
occlusion_overrides.json in the episode, {"k07": [true, null, false]}, forces items (true = front).
"""
import json, os, re, subprocess, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ep, FPS
from fontTools.ttLib import TTFont

ep = Ep(sys.argv[1]); SC = 4
tl = json.load(open(ep.w("timeline.json"), encoding="utf-8"))
def adv(path):
    f = TTFont(path); cm = f["cmap"].getBestCmap(); hm = f["hmtx"]; upm = f["head"].unitsPerEm
    return lambda ch: hm[cm[ord(ch)]][0] / upm if ord(ch) in cm else 0.75
cjk, latin = adv(ep.font), adv("C:/Windows/Fonts/ariblk.ttf")
def boxes(it):
    fs = it["fs"]
    if it["v"]:
        return [(it["x"] - fs / 2, it["y"] + i * fs * 1.02 - fs / 2, it["x"] + fs / 2, it["y"] + i * fs * 1.02 + fs / 2) for i, _ in enumerate(it["text"])]
    w = sum((latin if it["latin"] else cjk)(c) for c in it["text"]) * fs
    return [(it["x"] - w / 2, it["y"] - fs / 2, it["x"] + w / 2, it["y"] + fs / 2)]
over = ep.load("occlusion_overrides.json", {})
plan, front_n = {}, 0
for gi, g in enumerate(tl["kinetic"], 1):
    d = ep.f("matte", f"k{gi:02d}")
    A = None
    if os.path.isdir(d):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-framerate", "30000/1001", "-start_number", "0", "-i", f"{d}/%05d.webp",
                              "-vf", f"alphaextract,scale={1080 // SC}:{1920 // SC}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             capture_output=True).stdout
        A = np.frombuffer(raw, np.uint8).reshape(-1, 1920 // SC, 1080 // SC) > 127
    flags = []
    for ii, it in enumerate(g["items"]):
        cov = 0.0
        if A is not None and len(A):
            f0 = int(max(0, it["t"] - g["a"] + .3) * FPS); tot = hit = 0
            for x0, y0, x1, y1 in boxes(it):
                xs, xe, ys, ye = int(max(0, x0) / SC), int(min(1080, x1) / SC), int(max(0, y0) / SC), int(min(1920, y1) / SC)
                if xe > xs and ye > ys and len(A) > f0:
                    reg = A[f0:, ys:ye, xs:xe]; hit += int(reg.sum()); tot += reg.size
            cov = hit / tot if tot else 0.0
        key = bool(re.search(r"\d|RM", it["text"]))
        front = cov > .25 or (key and cov > .10)
        lst = over.get(f"k{gi:02d}", []); forced = lst[ii] if ii < len(lst) else None
        if forced is not None: front = bool(forced)
        flags.append(bool(front)); front_n += front
        print(f"  k{gi:02d} {it['text']:<14s} covered {cov * 100:5.1f}%  -> {'FRONT' if front else 'behind'}{'  (override)' if forced is not None else ''}")
    plan[str(gi)] = flags
json.dump(plan, open(ep.w("occlusion.json"), "w"), indent=1)
print(f"  {front_n} of {sum(len(v) for v in plan.values())} items in front of the presenter")

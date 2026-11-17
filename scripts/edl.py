"""Build work/edl.json from blocks.json (the chosen takes) and the audio envelope.

usage: edl.py EPISODE_DIR
blocks.json: [{"a": src_sec, "b": src_sec, "label": "HOOK", "note": "why this take"}, ...]
- every block edge is snapped to the nearest sustained silence (never inside a word)
- pauses >= min_pause inside a block are tightened to ~2*hold
- segments are quantised to the frame grid (audio and video stay the same length)
- edges sitting on breath/room get a 40 ms fade, clean edges 8 ms
- jump cuts alternate 100% / punch_in framing
"""
import json, math, os, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ep, FPS, FPS_STR

ep = Ep(sys.argv[1])
BLOCKS = ep.load("blocks.json")
if not BLOCKS:
    sys.exit("blocks.json is empty: pick the takes first (work/transcript.txt)")
MIN_PAUSE = float(ep.get("min_pause", 0.45))
HOLD = float(ep.get("hold", 0.12))
PUNCH = float(ep.get("punch_in", 1.12))
HOP = 0.01

with wave.open(ep.w("audio16k.wav")) as wf:
    sr = wf.getframerate()
    x = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
n = int(len(x) / (sr * HOP))
env = 20 * np.log10(np.sqrt((x[: n * int(sr * HOP)].reshape(n, -1) ** 2).mean(1)) + 1e-9)
floor, speech = np.percentile(env, 10), np.percentile(env, 90)
TH = floor + 0.35 * (speech - floor)
quiet = env < TH
print(f"noise floor {floor:.1f} dBFS, speech p90 {speech:.1f}, silence threshold {TH:.1f}")
idx = lambda t: max(0, min(n - 1, int(round(t / HOP))))
t_ = lambda i: i * HOP

def snap_in(t):
    i, lo = idx(t + 0.15), idx(t - 0.30)
    while i > lo and not quiet[i]:
        i -= 1
    return max(t_(i + 1) - 0.08, t - 0.30)

def snap_out(t):
    i, hi = idx(t - 0.15), idx(t + 0.30)
    while i < hi and not all(quiet[i:i + 3]):
        i += 1
    return min(t_(i) + 0.10, t + 0.30)

def pauses(a, b):
    out, j0 = [], None
    for i in range(idx(a), idx(b)):
        if quiet[i] and j0 is None: j0 = i
        if not quiet[i] and j0 is not None:
            if t_(i) - t_(j0) >= MIN_PAUSE and t_(j0) > a + 0.2 and t_(i) < b - 0.2:
                out.append((t_(j0), t_(i)))
            j0 = None
    return out

segs = []
for bl in BLOCKS:
    a2, b2 = snap_in(bl["a"]), snap_out(bl["b"])
    cur = a2
    ps = pauses(a2, b2)
    for p0, p1 in ps:
        segs.append({"src_in": round(cur, 3), "src_out": round(p0 + HOLD, 3), "block": bl["label"]})
        cur = p1 - HOLD
    segs.append({"src_in": round(cur, 3), "src_out": round(b2, 3), "block": bl["label"]})
    print(f"{bl['label']:10s} {a2:7.2f}-{b2:7.2f}  pauses tightened: {len(ps)}")

for s in segs:
    s["src_in"] = round(math.floor(s["src_in"] * FPS + 1e-6) / FPS, 4)
    s["src_out"] = round(math.ceil(s["src_out"] * FPS - 1e-6) / FPS, 4)
edge = lambda a, b: float(env[idx(a):max(idx(a) + 1, idx(b))].max())
for s in segs:
    s["fade_in"] = 0.04 if edge(s["src_in"], s["src_in"] + 0.05) > TH else 0.008
    s["fade_out"] = 0.04 if edge(s["src_out"] - 0.05, s["src_out"]) > TH else 0.008

t = 0.0
for k, s in enumerate(segs):
    s.update(id=k, zoom=PUNCH if k % 2 else 1.0, out_in=round(t, 3))
    t += s["src_out"] - s["src_in"]
    s["out_out"] = round(t, 3)

json.dump({"source": ep.get("source"), "mezzanine": ep.w("mezz.mov"), "fps": FPS_STR, "out_size": [1080, 1920],
           "block_notes": {b["label"]: b.get("note", "") for b in BLOCKS}, "segments": segs},
          open(ep.w("edl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(segs)} segments, cut length {t:.2f}s ({int(t // 60)}:{t % 60:05.2f}); at {ep.speed}x: {t / ep.speed:.1f}s")

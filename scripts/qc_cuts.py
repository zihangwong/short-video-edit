"""Check every cut in a render: level right at the splice and the jump across it.

usage: qc_cuts.py DIR RENDER.wav
Flags a cut when the 20 ms either side of the splice is hot (speech, not air),
or when short-term level jumps > 6 dB across it (audible change in room/level).
"""
import json, sys, wave
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
d, wav = sys.argv[1], sys.argv[2]
edl = json.load(open(f"{d}/edl.json", encoding="utf-8"))
with wave.open(wav) as wf:
    sr, ch = wf.getframerate(), wf.getnchannels()
    x = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
x = x.reshape(-1, ch).mean(1)
def rms(a, b):
    seg = x[max(0, int(a * sr)): max(0, int(b * sr))]
    return 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9) if len(seg) else -120
bad = 0
# thresholds relative to this render's speech level, so make-up gain doesn't move them
hop = int(0.05 * sr)
frames = x[: len(x) // hop * hop].reshape(-1, hop)
lv = 20 * np.log10(np.sqrt((frames ** 2).mean(1)) + 1e-9)
speech = np.percentile(lv, 75)
HOT, AIR = speech - 18, speech - 18
print(f"speech level ~{speech:.0f} dBFS; splice counts as hot above {HOT:.0f}")
for s in edl["segments"][1:]:
    t = s["out_in"]
    at = rms(t - 0.02, t + 0.02)
    before, after = rms(t - 0.25, t - 0.03), rms(t + 0.03, t + 0.25)
    flag = []
    if at > HOT: flag.append(f"hot splice {at:.0f} dBFS")
    if abs(before - after) > 6 and max(before, after) < AIR: flag.append(f"air jump {before:.0f}->{after:.0f} dB")
    if flag:
        bad += 1
        m, sec = divmod(t, 60)
        print(f"cut #{s['id']:2d} @ {int(m)}:{sec:05.2f} (src {s['src_in']:.2f}, {s['block']}): " + "; ".join(flag))
print(f"{len(edl['segments']) - 1} cuts checked, {bad} flagged")

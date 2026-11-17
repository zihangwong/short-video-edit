"""Full-resolution presenter matte for every kinetic window and every MG window that should sit
behind him (target / bucket / breakdown). Text and graphics can then be layered BEHIND the presenter.

usage: matte_plate.py EPISODE_DIR MODEL.onnx [only=id,id,...]
reads film/assets/plate.mp4, work/timeline.json, mg.json; writes film/matte/<id>/00000.webp ... (RGBA)
"""
import json, os, subprocess, sys, numpy as np, onnxruntime as ort
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ep, FPS

ep = Ep(sys.argv[1]); model = sys.argv[2]
only = set(sys.argv[3].split(",")) if len(sys.argv) > 3 and sys.argv[3] else None
tl = json.load(open(ep.w("timeline.json"), encoding="utf-8"))
W, H = 1080, 1920
wins = [(f"k{gi:02d}", g["a"], g["b"]) for gi, g in enumerate(tl["kinetic"], 1)]
wins += [(m["id"], m["a"], m["b"]) for m in ep.load("mg.json", []) if m["type"] in ("target", "bucket", "breakdown")]
sess = ort.InferenceSession(model, providers=["DmlExecutionProvider", "CPUExecutionProvider"])
dsr = np.array([0.25], np.float32)
for wid, a, b in wins:
    if only and wid not in only:
        continue
    n = int(np.ceil((b - a) * FPS)) + 1
    out = ep.f("matte", wid); os.makedirs(out, exist_ok=True)
    for f in os.listdir(out): os.remove(os.path.join(out, f))
    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{a:.4f}", "-i", ep.f("assets", "plate.mp4"), "-frames:v", str(n),
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    wr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", "30000/1001",
                           "-i", "-", "-c:v", "libwebp", "-quality", "88", "-compression_level", "4", "-start_number", "0",
                           f"{out}/%05d.webp"], stdin=subprocess.PIPE)
    rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
    for k in range(n):
        buf = rd.stdout.read(W * H * 3)
        if len(buf) < W * H * 3: break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        src = img.astype(np.float32).transpose(2, 0, 1)[None] / 255.0
        for _ in range(3 if k == 0 else 1):        # warm the recurrent state on the first frame
            fgr, pha, *rec = sess.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3], "downsample_ratio": dsr})
        wr.stdin.write(np.dstack([img, (np.clip(pha[0, 0], 0, 1) * 255 + .5).astype(np.uint8)]).tobytes())
    wr.stdin.close(); wr.wait(); rd.stdout.close(); rd.wait()
    print(f"  {wid}: {a:.2f}-{b:.2f}  {len(os.listdir(out))} frames", flush=True)

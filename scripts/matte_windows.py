"""Matte the presenter (RobustVideoMatting, ONNX on DirectML) for each black-frame
window and write one RGBA clip per window.

usage: matte_windows.py BASE_NOZOOM.mov WINDOWS_JSON MODEL.onnx OUTDIR [scale=0.5]
Each clip covers [a, b] of the base timeline at 29.97 fps, size = base*scale,
alpha ramps in/out over 0.15 s so the cut-out fades with the black frame.
"""
import json, subprocess, sys, numpy as np, onnxruntime as ort

base, wins_json, model, outdir = sys.argv[1:5]
scale = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
W, H = int(1080 * scale) // 2 * 2, int(1920 * scale) // 2 * 2
FPS = 30000 / 1001
FADE = 0.15
wins = json.load(open(wins_json))["black"]

sess = ort.InferenceSession(model, providers=["DmlExecutionProvider", "CPUExecutionProvider"])
print("providers:", sess.get_providers(), flush=True)

for wi, (a, b) in enumerate(wins):
    n = int(round((b - a) * FPS))
    rd = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{a:.4f}", "-i", base,
                           "-frames:v", str(n), "-vf", f"scale={W}:{H}:flags=area", "-f", "rawvideo",
                           "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    out = f"{outdir}/cutout_w{wi}.mov"
    wr = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
                           "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", "30000/1001", "-i", "-",
                           "-c:v", "qtrle", "-pix_fmt", "argb", out], stdin=subprocess.PIPE)
    rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
    dsr = np.array([0.4], np.float32)      # downsample ratio for a ~540-wide frame
    for k in range(n):
        buf = rd.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        src = img.astype(np.float32).transpose(2, 0, 1)[None] / 255.0
        fgr, pha, *rec = sess.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3],
                                         "downsample_ratio": dsr})
        alpha = pha[0, 0]
        t = k / FPS
        env = min(1.0, t / FADE, ((b - a) - t) / FADE)
        alpha = np.clip(alpha * max(0.0, env), 0, 1)
        rgba = np.dstack([img, (alpha * 255 + 0.5).astype(np.uint8)])
        wr.stdin.write(rgba.tobytes())
    wr.stdin.close(); wr.wait(); rd.stdout.close(); rd.wait()
    print(f"window {wi}: {a:.2f}-{b:.2f}  {n} frames -> {out}", flush=True)

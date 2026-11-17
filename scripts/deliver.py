"""Stage 5: sound + BGM + delivery.

usage: deliver.py EPISODE_DIR [--audio-only]
1. voice: the plate's good channel as dual mono (work/audio_report.json), + every <audio> clip of film.html
2. speed-up, compression, loudnorm: voice peaks in 0..-6 dB on a level meter, true peak <= -1.2 dBTP
3. BGM (episode.json "bgm", an OpenFilm CC0 music id) looped, ~16 dB under speech, side-chain ducked
4. mux with film/film.mp4 (rendered by OpenFilm) at `speed`, platform check, L/R check,
   out/<name>.mp4 + out/<name>.srt + out/<name>_preview720.mp4 (< 30 MB, for phones) + out/<name>_levels.png
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ep, run, duration, stage

ep = Ep(sys.argv[1]); F, W = ep.f, ep.w
sp = ep.speed
name = ep.get("out_name", os.path.basename(ep.root))
chan = json.load(open(W("audio_report.json"))).get("voice_channel", "mix") if os.path.exists(W("audio_report.json")) else "mix"
pan = {"left": "pan=stereo|c0=c0|c1=c0", "right": "pan=stereo|c0=c1|c1=c1", "mix": "anull"}[chan]

stage("sound")
html = open(F("film.html"), encoding="utf-8").read()
clips = re.findall(r'<audio src="([^"#]+)#t=([\d.]+),([\d.]+)" at="([\d.]+)" volume="([\d.]+)"', html)
cmd = ["ffmpeg", "-v", "error", "-y", "-i", F("assets", "plate.mp4")]
fc = [f"[0:a]{pan}[voice]"]
for i, (src, tin, tout, at, vol) in enumerate(clips):
    cmd += ["-i", F(src)]; ms = int(round(float(at) * 1000))
    fc.append(f"[{i+1}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim={tin}:{tout},asetpts=PTS-STARTPTS,volume={vol},adelay={ms}|{ms}[s{i}]")
fc.append("[voice]" + "".join(f"[s{i}]" for i in range(len(clips))) + f"amix=inputs={len(clips)+1}:duration=first:normalize=0[mix]")
run(*cmd, "-filter_complex", ";".join(fc), "-map", "[mix]", "-c:a", "pcm_s16le", "-ar", "48000", W("mix.wav"))
run("ffmpeg", "-v", "error", "-y", "-i", W("mix.wav"), "-af",
    f"atempo={sp},acompressor=threshold=-20dB:ratio=2.5:attack=8:release=150:makeup=2,loudnorm=I=-13:TP=-1.2:LRA=8,"
    "alimiter=limit=0.87:attack=3:release=50:level=false", "-ar", "48000", W("voice_final.wav"))
dur = duration(W("voice_final.wav"))
bgm = ep.get("bgm")
if bgm:
    run("ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", F("assets", f"{bgm}.mp3"), "-i", W("voice_final.wav"), "-filter_complex",
        f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,"
        f"loudnorm=I={ep.get('bgm_lufs', -17)}:TP=-4:LRA=7,afade=t=in:d=0.3,afade=t=out:st={dur - 1.5:.3f}:d=1.5[bed];"
        "[bed][1:a]sidechaincompress=threshold=0.04:ratio=4:attack=25:release=380:makeup=1[duck];"
        "[1:a][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.85:attack=3:release=60:level=false[o]",
        "-map", "[o]", "-ar", "48000", W("final_audio.wav"))
else:
    os.replace(W("voice_final.wav"), W("final_audio.wav"))
if "--audio-only" in sys.argv:
    sys.exit(0)

stage("mux")
film = F("film.mp4")
if not os.path.exists(film):
    sys.exit("film/film.mp4 missing: render the OpenFilm project first (run.py EP bgm does it)")
out = ep.o(f"{name}.mp4")
run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", film, "-i", W("final_audio.wav"), "-filter_complex",
    f"[0:v]setpts=PTS/{sp},fps=30000/1001[v]", "-map", "[v]", "-map", "1:a", "-c:v", "h264_nvenc", "-preset", "p6", "-rc", "vbr",
    "-cq", "19", "-b:v", "0", "-profile:v", "high", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
    "-c:a", "aac", "-b:a", "320k", "-aac_coder", "twoloop", "-ar", "48000", "-shortest", "-movflags", "+faststart", out)

stage("checks")
check = os.path.expanduser("~/.claude/skills/ffmpeg-skill/scripts/check.py")
if os.path.exists(check):
    r = subprocess.run([sys.executable, check, out, "--platform", ep.get("platform", "tiktok")], capture_output=True, text=True)
    print("\n".join(l for l in r.stdout.splitlines() if re.search(r"FAIL|duration|loudness|true peak|checks", l)))
lr = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", out, "-vn", "-af", "astats=measure_perchannel=RMS_level:measure_overall=none",
                     "-f", "null", "-"], capture_output=True, text=True).stderr
print("  L/R RMS:", [l.split(":")[-1].strip() for l in lr.splitlines() if "RMS level" in l])

stage("extras")
subs = [l.rstrip("\n").split("\t") for l in open(ep.p("subs.tsv"), encoding="utf-8") if l.strip()]
st = lambda x: "%02d:%02d:%02d,%03d" % (int(x // 3600), int(x % 3600 // 60), int(x % 60), int(round((x % 1) * 1000)) % 1000)
open(ep.o(f"{name}.srt"), "w", encoding="utf-8").write("".join(
    f"{i}\n{st(float(a) / sp)} --> {st(float(b) / sp)}\n{t}\n\n" for i, (a, b, t) in enumerate(subs, 1)))
run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", out, "-vf", "scale=720:1280:flags=lanczos", "-c:v", "h264_nvenc",
    "-preset", "p6", "-rc", "vbr", "-b:v", "1.2M", "-maxrate", "1.8M", "-bufsize", "3M", "-c:a", "aac", "-b:a", "96k",
    "-movflags", "+faststart", ep.o(f"{name}_preview720.mp4"))
try:
    import wave, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    fm.fontManager.addfont("C:/Windows/Fonts/msyh.ttc"); plt.rcParams["font.family"] = "Microsoft YaHei"
    def peaks(p):
        w = wave.open(p); sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32) / 32768
        m = np.abs(x).max(1); h = int(sr * .1); k = len(m) // h; return np.arange(k) * .1, 20 * np.log10(m[:k * h].reshape(k, h).max(1) + 1e-9)
    t, pv = peaks(W("voice_final.wav")) if os.path.exists(W("voice_final.wav")) else peaks(W("final_audio.wav"))
    fig, ax = plt.subplots(figsize=(14, 4), dpi=100)
    ax.axhspan(-6, 0, color="#2BD96B", alpha=.15, label="0 ~ -6 dB"); ax.plot(t, pv, color="#E0A800", lw=.9, label="人声 + 音效")
    ax.axhline(0, color="red", lw=1); ax.set_ylim(-45, 3); ax.set_xlim(0, t[-1]); ax.legend(loc="lower right")
    a = pv[pv > -30]; ax.set_title(f"{name}：有声段 {np.mean((a >= -6) & (a <= 0)) * 100:.0f}% 落在 0~-6 dB，最高 {pv.max():.1f} dB")
    plt.tight_layout(); plt.savefig(ep.o(f"{name}_levels.png"))
except Exception as e:
    print("  (level chart skipped:", e, ")")
print(f"\ndelivered: {out}\n  + {name}.srt, {name}_preview720.mp4, {name}_levels.png")

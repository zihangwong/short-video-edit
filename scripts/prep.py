"""Stage 1a: look at the source, find the voice channel, transcribe, make the SDR mezzanine.

usage: prep.py EPISODE_DIR
writes work/probe.json, work/audio_report.json, work/audio16k.wav, work/transcript.json,
       work/transcript.txt (one line per segment, for picking takes), work/mezz.mov
Every step is skipped when its output already exists (delete it to redo).
"""
import glob, json, os, site, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ep, run, stage, FPS_STR

ep = Ep(sys.argv[1])
src = ep.get("source")
if not os.path.exists(src):
    sys.exit(f"source not found: {src}")

# ---------------------------------------------------------------- probe
stage("probe")
pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", src],
                               capture_output=True, text=True).stdout)
v = next(s for s in pr["streams"] if s["codec_type"] == "video")
rot = 0
for sd in v.get("side_data_list", []):
    if "rotation" in sd: rot = int(sd["rotation"])
w, h = (v["height"], v["width"]) if abs(rot) == 90 else (v["width"], v["height"])
hdr = v.get("color_transfer") in ("arib-std-b67", "smpte2084")
info = {"width": w, "height": h, "rotation": rot, "hdr": hdr, "transfer": v.get("color_transfer"),
        "fps": v.get("avg_frame_rate"), "duration": float(pr["format"]["duration"]), "codec": v["codec_name"]}
json.dump(info, open(ep.w("probe.json"), "w"), indent=1)
print(f"  {w}x{h}  {info['duration']:.1f}s  {v['codec_name']}  {'HDR ' + info['transfer'] if hdr else 'SDR'}  fps {info['fps']}")

# ---------------------------------------------------------------- which channel carries the voice?
stage("left / right balance")
out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-vn", "-af",
                      "astats=measure_perchannel=RMS_level:measure_overall=none", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
rms = [float(l.split(":")[-1]) for l in out.splitlines() if "RMS level dB" in l]
if len(rms) >= 2:
    diff = rms[0] - rms[1]
    chan = "left" if diff > 6 else ("right" if diff < -6 else "mix")
else:
    diff, chan = 0.0, "mix"
rep = {"rms_left": rms[0] if rms else None, "rms_right": rms[1] if len(rms) > 1 else None, "diff_db": diff,
       "voice_channel": ep.get("voice_channel", chan)}
json.dump(rep, open(ep.w("audio_report.json"), "w"), indent=1)
print(f"  L {rep['rms_left']} dB  R {rep['rms_right']} dB  -> voice from: {rep['voice_channel']}"
      + ("   (one channel is nearly empty: the deliverable will be dual mono from the good side)" if chan != "mix" else ""))
pan = {"left": "pan=mono|c0=c0", "right": "pan=mono|c0=c1", "mix": "pan=mono|c0=0.5*c0+0.5*c1"}[rep["voice_channel"]]

# ---------------------------------------------------------------- transcribe (local, GPU when possible)
if not os.path.exists(ep.w("transcript.json")):
    stage("transcribe")
    run("ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-af", pan, "-ar", "16000", ep.w("audio16k.wav"))
    for d in glob.glob(os.path.join(site.getsitepackages()[-1], "nvidia", "*", "bin")):
        os.add_dll_directory(d); os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]
    import wave, numpy as np
    from faster_whisper import WhisperModel
    with wave.open(ep.w("audio16k.wav")) as wf:
        audio = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768.0
    model = ep.get("asr_model", "large-v3-turbo")
    try:
        m = WhisperModel(model, device="cuda", compute_type="float16"); list(m.transcribe(audio[:16000 * 5], beam_size=1)[0]); dev = "cuda"
    except Exception as e:
        print("  cuda unavailable:", e); m = WhisperModel(model, device="cpu", compute_type="int8"); dev = "cpu"
    t0 = time.time()
    segs, inf = m.transcribe(audio, word_timestamps=True, vad_filter=False, beam_size=5, condition_on_previous_text=False,
                             language=ep.get("language"), initial_prompt=ep.get("asr_prompt", "嗯，呃，那个，就是，然后。Um, uh."))
    res = {"language": inf.language, "device": dev, "segments": []}
    lines = []
    for s in segs:
        res["segments"].append({"start": s.start, "end": s.end, "text": s.text,
                                "words": [{"s": round(x.start, 3), "e": round(x.end, 3), "w": x.word, "p": round(x.probability, 3)}
                                          for x in (s.words or [])]})
        lines.append(f"[{s.start:7.2f}-{s.end:7.2f}] {s.text.strip()}")
    json.dump(res, open(ep.w("transcript.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(ep.w("transcript.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"  {len(lines)} segments, {dev}, {time.time() - t0:.0f}s -> work/transcript.txt")
else:
    print("  transcript.json exists, skipped")

# ---------------------------------------------------------------- SDR mezzanine (portrait, 1.33x the delivery size)
if not os.path.exists(ep.w("mezz.mov")):
    stage("mezzanine")
    MW, MH = (1440, 2560) if h >= w else (2560, 1440)
    if hdr:
        tin = info["transfer"]
        vf = (f"fps={FPS_STR},zscale=tin={tin}:pin=bt2020:min=bt2020nc:rin=tv:t=linear:npl=100:w={MW}:h={MH}:filter=spline36,"
              f"format=gbrpf32le,zscale=p=bt709,tonemap=tonemap={ep.get('tonemap', 'mobius')}:desat=0:peak=10,"
              "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
    else:
        vf = f"fps={FPS_STR},scale={MW}:{MH}:flags=lanczos,format=yuv420p"
    t0 = time.time()
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", src, "-map", "0:v:0", "-map", "0:a:0", "-vf", vf,
        "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "constqp", "-qp", "14", "-g", "15", "-bf", "0",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
        "-c:a", "pcm_s16le", ep.w("mezz.mov"))
    print(f"  mezz.mov {MW}x{MH} in {time.time() - t0:.0f}s")
else:
    print("  mezz.mov exists, skipped")
print("\nnext: pick the takes into blocks.json (see work/transcript.txt), then  run.py EP cut")

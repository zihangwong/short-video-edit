"""Render edl.json from the SDR mezzanine.

usage: render.py DIR OUT.mp4 [--preview]
--preview burns the output timecode top-right so feedback can be given by TC.
Audio: 8 ms fades at every segment edge (edges are snapped to silence), then
80 Hz high-pass, 3:1 compression, limiter. Loudness normalisation is a
separate two-pass step afterwards.
"""
import json, subprocess, sys

d, out = sys.argv[1], sys.argv[2]
preview = "--preview" in sys.argv
_edl = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--edl=")), "edl.json")
edl = json.load(open(f"{d}/{_edl}", encoding="utf-8"))
W, H = edl["out_size"]
MW, MH = 1440, 2560
FADE = 0.008
GAIN = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--gain=")), "8"))

cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
fc = []
for k, s in enumerate(edl["segments"]):
    dur = s["src_out"] - s["src_in"]
    cmd += ["-ss", f"{s['src_in']:.3f}", "-t", f"{dur:.3f}", "-i", edl["mezzanine"]]
    z = s["zoom"]
    if z != 1.0:
        cw, ch = int(MW / z) // 2 * 2, int(MH / z) // 2 * 2
        x, y = (MW - cw) // 2, int((MH - ch) * 0.35) // 2 * 2   # bias up: keep the face in frame
        v = f"crop={cw}:{ch}:{x}:{y},"
    else:
        v = ""
    nf = round(dur * 30000 / 1001)
    fc.append(f"[{k}:v]{v}scale={W}:{H}:flags=lanczos,setsar=1,setpts=PTS-STARTPTS,"
              f"trim=end_frame={nf}[v{k}]")
    fd = nf * 1001 / 30000
    fc.append(f"[{k}:a]asetpts=PTS-STARTPTS,atrim=end={fd:.6f},apad=whole_dur={fd:.6f},"
              f"afade=t=in:d={s.get('fade_in', FADE)},"
              f"afade=t=out:st={fd - s.get('fade_out', FADE):.6f}:d={s.get('fade_out', FADE)}[a{k}]")
n = len(edl["segments"])
fc.append("".join(f"[v{k}][a{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")
vpost = "format=yuv420p"
def opt(name):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), None)
ASS = opt("ass")
if ASS:                      # relative to DIR (ffmpeg runs with cwd=DIR)
    vpost = f"ass={ASS}," + vpost
# v3: --ass-under, --card=PATH|out_in|out_out|src_in, --ass-top, --sfx=JSON|TICKWAV
UNDER, CARD, TOP, SFX = opt("ass-under"), opt("card"), opt("ass-top"), opt("sfx")
extra_in = n_in = len(edl["segments"])
vchain = "[vc]"
if UNDER:
    fc.append(f"{vchain}ass={UNDER}:fontsdir=fonts[vu]"); vchain = "[vu]"
# every --card=PATH|out_in|out_out|src_in|y  is a designer B-roll clip with alpha (any number of them)
for k, CARD in enumerate(a.split("=", 1)[1] for a in sys.argv if a.startswith("--card=")):
    parts = CARD.split("|")
    cpath, c_in, c_out, c_src = parts[:4]
    c_y = int(parts[4]) if len(parts) > 4 else 0
    c_in, c_out, c_src = float(c_in), float(c_out), float(c_src)
    cmd += ["-ss", f"{c_src:.3f}", "-i", cpath]
    ci = extra_in; extra_in += 1
    dur = c_out - c_in
    fc.append(f"[{ci}:v]format=yuva444p,fps=30000/1001,trim=duration={dur:.3f},tpad=stop_mode=clone:stop_duration={dur:.3f},"
              f"trim=duration={dur:.3f},fade=t=in:st=0:d=0.20:alpha=1,fade=t=out:st={dur-0.15:.3f}:d=0.15:alpha=1,"
              f"setpts=PTS-STARTPTS+{c_in:.4f}/TB[card{k}]")
    fc.append(f"{vchain}[card{k}]overlay=0:{c_y}:eof_action=pass:format=auto[vk{k}]"); vchain = f"[vk{k}]"
CUT = opt("cutouts")         # JSON|prefix|x|y  -> prefix{i}.mov placed at each black window
if CUT:
    cj, cpre, cx, cy = CUT.split("|")
    for i, (wa, wb) in enumerate(json.load(open(f"{d}/{cj}"))["black"]):
        cmd += ["-i", f"{cpre}{i}.mov"]; ci = extra_in; extra_in += 1
        fc.append(f"[{ci}:v]format=yuva444p,setpts=PTS-STARTPTS+{wa:.4f}/TB[co{i}]")
        fc.append(f"{vchain}[co{i}]overlay={cx}:{cy}:eof_action=pass:format=auto[vco{i}]"); vchain = f"[vco{i}]"
OVL = opt("overlay")         # full-length alpha video (Remotion captions + kinetic text), on top of everything
if OVL:
    cmd += ["-i", OVL]; oi = extra_in; extra_in += 1
    fc.append(f"[{oi}:v]format=yuva444p,setpts=PTS-STARTPTS[ovl]")
    fc.append(f"{vchain}[ovl]overlay=0:0:eof_action=pass:format=auto[vov]"); vchain = "[vov]"
if TOP:
    fc.append(f"{vchain}ass={TOP}:fontsdir=fonts[vt]"); vchain = "[vt]"
if vchain != "[vc]":
    fc.append(f"{vchain}null[vc2]"); vin = "[vc2]"
else:
    vin = "[vc]"
if preview:
    vpost = ("drawtext=fontfile='C\\:/Windows/Fonts/consola.ttf':fontsize=34:fontcolor=white:"
             "box=1:boxcolor=black@0.55:boxborderw=8:x=w-tw-24:y=24:"
             "text='%{pts\\:hms}'," + vpost)
fc.append(f"{vin}{vpost}[vo]")
fc.append("[ac]highpass=f=80,acompressor=threshold=-24dB:ratio=3:attack=5:release=120:makeup=4,"
          f"volume={GAIN}dB,alimiter=limit=0.75:attack=3:release=60:level=false" + ("[av]" if SFX else "[ao]"))  # sample peaks <= -2.5 dBFS
if SFX:
    sjson, swav = SFX.split("|")
    ticks = json.load(open(f"{d}/{sjson}"))["ticks"]
    cmd += ["-i", swav]; si = extra_in; extra_in += 1
    fc.append(f"[{si}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=-9dB,asplit={len(ticks)}" + "".join(f"[t{i}]" for i in range(len(ticks))))
    for i, t in enumerate(ticks):
        ms = int(round(t * 1000))
        fc.append(f"[t{i}]adelay={ms}|{ms}[d{i}]")
    mixins = [f"[d{i}]" for i in range(len(ticks))]
    # v6: extra one-shot SFX events {t, wav, gain} (kinetic text)
    evs = json.load(open(f"{d}/{sjson}")).get("events", [])
    for wav in sorted({e["wav"] for e in evs}):
        group = [e for e in evs if e["wav"] == wav]
        cmd += ["-i", wav]; wi = extra_in; extra_in += 1
        tag = wav.split(".")[0]
        fc.append(f"[{wi}:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit={len(group)}"
                  + "".join(f"[{tag}{k}]" for k in range(len(group))))
        for k, e in enumerate(group):
            ms = int(round(e["t"] * 1000))
            fc.append(f"[{tag}{k}]volume={e['gain']}dB,adelay={ms}|{ms}[{tag}d{k}]")
            mixins.append(f"[{tag}d{k}]")
    fc.append("[av]aformat=channel_layouts=stereo[avs];[avs]" + "".join(mixins)
              + f"amix=inputs={len(mixins)+1}:duration=first:normalize=0,"
              "alimiter=limit=0.75:attack=2:release=50:level=false[ao]")   # SFX can stack on speech peaks
SPEED = opt("speed")
vmap, amap = "[vo]", "[ao]"
if SPEED:                    # retime the finished picture + sound together (pitch kept by atempo)
    sp = float(SPEED)
    fc.append(f"[vo]setpts=PTS/{sp},fps=30000/1001[vsp]")
    fc.append(f"[ao]atempo={sp}[asp]")
    vmap, amap = "[vsp]", "[asp]"
cmd += ["-filter_complex", ";".join(fc), "-map", vmap, "-map", amap,
        "-c:v", "h264_nvenc", "-preset", "p6", "-rc", "vbr", "-cq", "19" if not preview else "23",
        "-b:v", "0", "-profile:v", "high", "-r", edl["fps"],
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
        "-c:a", "pcm_s16le" if out.endswith(".mov") else "aac", "-b:a", "256k", "-ar", "48000",
        "-movflags", "+faststart", out]
r = subprocess.run(cmd, cwd=d)
sys.exit(r.returncode)

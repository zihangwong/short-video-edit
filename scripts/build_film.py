"""Write the OpenFilm project (film/) from work/timeline.json, mg.json, mattes and the SFX library.

usage: build_film.py EPISODE_DIR
Tracks, top first: captions (WebVTT) / kinetic text IN FRONT / presenter cut-out / kinetic text BEHIND /
motion graphics / plate video / sound effects. Every piece is its own clip, editable in Studio.
Every animated element gets a sound (assets/sfx_library.json), rotated through variants.
"""
import json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ep, SKILL, SCRIPTS, OPENFILM

ep = Ep(sys.argv[1]); F = ep.f
tl = json.load(open(ep.w("timeline.json"), encoding="utf-8"))
MG = ep.load("mg.json", [])
OCC = json.load(open(ep.w("occlusion.json"))) if os.path.exists(ep.w("occlusion.json")) else {}
shutil.copy(ep.font, F("lib", "caption.ttf"))
for js, name in (("kinetic_engine.js", "kinetic.js"), ("mg_engine.js", "mg.js")):
    shutil.copy(os.path.join(SCRIPTS, js), F("lib", name))
cap = ep.get("captions", {})
SAFE = ep.get("title_safe", [108, 192, 972, 1728])                 # captions too: bottom edge (line ..%,end) inside the box
for key, dflt in (("line", "71%"), ("line_black", "84%")):
    bottom = float(cap.get(key, dflt).rstrip("%")) / 100 * 1920; top = bottom - cap.get("size", 110) * 1.2
    if bottom > SAFE[3] or top < SAFE[1]:
        sys.exit(f"captions.{key} = {cap.get(key, dflt)} puts captions outside the title-safe box (y {SAFE[1]}-{SAFE[3]})")

def page(name, title, module, fn, arg):
    open(F(name), "w", encoding="utf-8").write(
        f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title></head><body>\n'
        f'<script type="module">\nimport {{ {fn} }} from "./lib/{module}";\n{fn}({json.dumps(arg, ensure_ascii=False)});\n</script>\n</body></html>\n')

def clip(cid, name, a, b):
    return f'    <iframe id="{cid}" src="{name}#t=0,{b - a:.3f}" at="{a:.3f}"></iframe>'

# ------------------------------------------------------------------ captions.vtt (one line, keyword colour, pop-in)
vt = lambda t: "%02d:%02d:%06.3f" % (int(t // 3600), int(t % 3600 // 60), t % 60)
out = ["WEBVTT", "", f"""STYLE
::cue {{
  font-family: "CapFont", "Noto Sans SC", sans-serif;
  font-size: {cap.get('size', 110)}px; line-height: 1.06; color: #ffffff; background: transparent;
  text-shadow: 0 2px 4px rgba(0,0,0,.7), 0 0 16px rgba(0,0,0,.5), 0 8px 28px rgba(0,0,0,.4);
  animation: capin .2s cubic-bezier(.2,1.4,.4,1) both;
}}
::cue(.k) {{ color: {cap.get('key_color', '#FFE600')}; font-size: 1.12em; }}
@keyframes capin {{ from {{ scale: .84; opacity: 0; filter: blur(6px); }} 40% {{ opacity: 1; }} to {{ scale: 1; opacity: 1; filter: blur(0); }} }}
"""]
for i, c in enumerate(tl["captions"], 1):
    pos = cap.get("line_black", "84%") if c["black"] else cap.get("line", "71%")
    text = "\n".join("".join(f"<c.k>{s}</c>" if k else s for s, k in ln) for ln in c["lines"])
    out += [f"c{i}", f"{vt(c['a'])} --> {vt(c['b'])} line:{pos},end position:50% align:center size:96%", text, ""]
open(F("captions.vtt"), "w", encoding="utf-8").write("\n".join(out))

# ------------------------------------------------------------------ presenter cut-out page
open(F("lib", "person.js"), "w", encoding="utf-8").write("""// Presenter cut-out: shows the matte frame for t (pure function of t), decoded on demand.
export function person({ dir, n, len }) {
  document.body.style.cssText = "margin:0;width:1080px;height:1920px;overflow:hidden;background:transparent";
  const fps = 30000 / 1001, im = new Image();
  Object.assign(im.style, { position: "absolute", left: 0, top: 0, width: "1080px", height: "1920px" });
  document.body.appendChild(im);
  const src = (i) => `${dir}/${String(Math.min(n - 1, Math.max(0, i))).padStart(5, "0")}.webp`;
  window.film = { duration: len, frame(t) { const s = src(Math.round(t * fps)); if (im.getAttribute("src") === s) return; im.src = s; return im.decode(); } };
}
""")
def person_clip(wid, a, b, title):
    d = F("matte", wid)
    if not os.path.isdir(d): return None
    n = len([f for f in os.listdir(d) if f.endswith(".webp")])
    if not n: return None
    page(f"p{wid}.html", "人物 " + title, "person.js", "person", {"dir": f"matte/{wid}", "n": n, "len": round(b - a, 3)})
    return clip(f"p{wid}", f"p{wid}.html", a, b)

# ------------------------------------------------------------------ kinetic text: behind / in front
kclips, fclips, pclips = [], [], []
for f in os.listdir(F()):
    if f.endswith(".html") and f != "film.html": os.remove(F(f))            # stale pages from an earlier build
for gi, g in enumerate(tl["kinetic"], 1):
    wid = f"k{gi:02d}"; flags = OCC.get(str(gi), [False] * len(g["items"]))
    label = "".join(it["text"] for it in g["items"])[:24]
    for keep, bucket, suffix in ((False, kclips, ""), (True, fclips, "f")):
        items = [it for it, fl in zip(g["items"], flags) if fl == keep]
        if items:
            page(f"{wid}{suffix}.html", ("前 " if keep else "") + label, "kinetic.js", "kinetic", dict(g, items=items))
            bucket.append(clip(f"{wid}{suffix}", f"{wid}{suffix}.html", g["a"], g["b"]))
    pc = person_clip(wid, g["a"], g["b"], label)
    if pc: pclips.append(pc)
mclips = []
for m in MG:
    page(f"{m['id']}.html", "MG " + m["type"], "mg.js", "mg", {k: v for k, v in m.items() if k != "sfx"})
    mclips.append(clip(m["id"], f"{m['id']}.html", m["a"], m["b"]))
    if m["type"] in ("target", "bucket", "breakdown"):
        pc = person_clip(m["id"], m["a"], m["b"], "MG")
        if pc: pclips.append(pc)
pclips.sort(key=lambda h: float(h.split('at="')[1].split('"')[0]))

# ------------------------------------------------------------------ sound for every animation
LIB = json.load(open(os.path.join(SKILL, "assets", "sfx_library.json"), encoding="utf-8"))
DECO_AT = {"box": .18, "underline": .18, "strike": .28, "check": .32}
FAMILY = {"slam": "slam", "drop": "drop", "rise": "drop", "slide_l": "slide", "slide_r": "slide", "pop": "pop", "fade": "fade",
          "type": "type", "stamp": "stamp", "flip": "flip", "shake": "shake", "wave": "wave", "split": "slide"}
RANK = {"slam": 4, "stamp": 4, "shake": 4, "drop": 3, "slide": 3, "flip": 3, "black": 3, "pop": 2, "wave": 2, "type": 2,
        "check": 2, "strike": 2, "box": 1, "underline": 1, "fade": 1}
events = [(it["t"], FAMILY[it["anim"]]) for g in tl["kinetic"] for it in g["items"]]
events += [(it["t"] + DECO_AT[it["deco"]] * g.get("slow", 1), it["deco"]) for g in tl["kinetic"] for it in g["items"] if it.get("deco")]
events += [(wa, "black") for wa, wb in tl["black"]]
kept = []
for t, fam in sorted(events):                       # two sounds within 80 ms: keep the stronger
    if kept and t - kept[-1][0] < 0.08:
        if RANK[fam] > RANK[kept[-1][1]]: kept[-1] = (t, fam)
        continue
    kept.append((t, fam))
turn, sounds = {k: 0 for k in LIB}, []
for t, fam in kept:
    name, tin, tout, peak, target, off = LIB[fam][turn[fam] % len(LIB[fam])]; turn[fam] += 1
    sounds.append((max(0.0, t + off), name, tin, tout, peak, target))
for m in MG:
    sounds += [tuple(s) for s in m.get("sfx", [])]
tracks = []
def pack(a, b, html):
    for tr in tracks:
        if all(b <= s or a >= e for s, e, _ in tr): tr.append((a, b, html)); return
    tracks.append([(a, b, html)])
for a, name, tin, tout, peak, target in sounds:
    vol = min(1.0, round(10 ** ((target - peak) / 20), 3))
    pack(a, a + (tout - tin), f'    <audio src="assets/{name}.mp3#t={tin},{tout}" at="{a:.3f}" volume="{vol}"></audio>')

film = ["<!doctype html>", "<html>", "<head>", '<meta charset="utf-8">', '<meta name="viewport" content="width=1080, height=1920">',
        f"<title>{ep.get('title', 'episode')}</title>", "<style>", '  @font-face { font-family: "CapFont"; src: url("lib/caption.ttf"); }', "</style>",
        "</head>", "<body>",
        ]
for track in ([ '    <track kind="captions" src="captions.vtt" srclang="zh" label="字幕">'], fclips, pclips, kclips, mclips,
              ['    <video id="plate" src="assets/plate.mp4"></video>'], *[[h for _, _, h in sorted(tr)] for tr in tracks]):
    if track:                                       # OpenFilm: no empty tracks
        film += ["<section>", *track, "</section>"]
film += ["</body>", "</html>", ""]
open(F("film.html"), "w", encoding="utf-8").write("\n".join(film))

# ------------------------------------------------------------------ fetch any CC0 sound not in the project yet
missing = sorted({s[1] for s in sounds if not os.path.exists(F("assets", f"{s[1]}.mp3"))})
bgm = ep.get("bgm")
if bgm and not os.path.exists(F("assets", f"{bgm}.mp3")):
    subprocess.run([*OPENFILM, "get", "music-search", "--take", f"openfilm/audio/music/{bgm}.mp3"], cwd=F(), shell=(os.name == "nt"))
for name in missing:
    subprocess.run([*OPENFILM, "get", "sfx-search", "--take", f"openfilm/audio/sfx/{name}.mp3"], cwd=F(), shell=(os.name == "nt"),
                   capture_output=True)
still = [n for n in missing if not os.path.exists(F("assets", f"{n}.mp3"))]
print(f"film.html: {len(tl['captions'])} captions, {len(kclips) + len(fclips)} kinetic clips ({len(fclips)} in front), "
      f"{len(pclips)} presenter layers, {len(mclips)} MG, {len(sounds)} sounds on {len(tracks)} tracks"
      + (f"; MISSING sounds: {still}" if still else ""))

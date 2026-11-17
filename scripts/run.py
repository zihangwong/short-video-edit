"""One command for the whole edit, or one stage at a time.

usage: run.py EPISODE_DIR STAGE [--preview]
  new       make an episode folder from the templates (EPISODE_DIR must not exist yet; then edit episode.json)
  cut       1 粗剪      probe, voice channel, transcribe, SDR mezzanine, edl from blocks.json, cut preview + cut QC
  subs      2 识别字幕  draft captions -> subs_draft.tsv (proofread into subs.tsv)
  text      3 字幕特效  captions + kinetic.json timing + cards -> work/timeline.json, graphics_under.ass
  broll     4 B-roll/MG plate (cut + cards + designer clips + black-frame cut-outs), mattes, front/behind, OpenFilm project
  bgm       5 BGM/交付  OpenFilm render (motion blur), voice + SFX + BGM mix, speed-up, checks, deliverables
  all       cut -> text -> broll -> bgm   (subs.tsv, kinetic.json, cards.json, mg.json must already be written)
  final [--dry]  定稿 (ONLY when the user says the video is final): final mp4 -> Videos folder, every other video
            of the episode -> Recycle Bin (add --also DIR for an older project of the same episode)
  look T    draw one frame of the OpenFilm film at cut-time T (seconds) -> prints the PNG path
"""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SKILL, SCRIPTS, PY, OPENFILM, run, py, stage, need, copy_if_newer, ensure_model, ensure_tick

if len(sys.argv) < 3:
    sys.exit(__doc__)
EPD, STAGE = os.path.abspath(sys.argv[1]).replace("\\", "/"), sys.argv[2]
MODEL = os.path.join(SKILL, "assets", "models", "rvm_mobilenetv3_fp32.onnx")

if STAGE == "new":
    if os.path.exists(EPD): sys.exit(f"{EPD} already exists")
    shutil.copytree(os.path.join(SKILL, "templates", "episode"), EPD)
    print(f"created {EPD}: fill in episode.json (source, title, out_name, font, bgm), then  run.py {EPD} cut"); sys.exit()

from common import Ep
ep = Ep(EPD)
for f in ("NotoSansSC-Black-Static.ttf", "NotoSansSC-Bold-Static.ttf"):            # fonts for the ASS card layer
    copy_if_newer(os.path.join(SKILL, "assets", "fonts", f), ep.w("fonts", f))

def s_cut():
    stage("1 粗剪 — prep"); py("prep.py", EPD)
    if not ep.load("blocks.json"):
        print("\nblocks.json is empty: pick the takes (work/transcript.txt), then run `cut` again"); sys.exit()
    stage("1 粗剪 — edit list"); py("edl.py", EPD)
    stage("1 粗剪 — preview"); py("render_edl.py", ep.w(), ep.o("cut_preview.mp4"), "--preview", f"--gain={ep.get('plate_gain', 10)}", cwd=ep.w())
    run("ffmpeg", "-v", "error", "-y", "-i", ep.o("cut_preview.mp4"), "-vn", "-ac", "1", "-c:a", "pcm_s16le", ep.w("cut_preview.wav"))
    py("qc_cuts.py", ep.w(), ep.w("cut_preview.wav"))
    print(f"\nwatch out/cut_preview.mp4 (timecode top-right = cut time). Next: run.py {EPD} subs")

def s_subs():
    need(ep.w("edl.json"), "run the cut stage first")
    stage("2 识别字幕"); py("subs_draft.py", EPD)

def s_text():
    need(ep.p("subs.tsv"), "proofread subs_draft.tsv into subs.tsv")
    stage("3 字幕特效 — captions / kinetic / cards"); py("graphics.py", EPD)

def s_broll():
    s_text()
    ensure_model(MODEL); tick = ensure_tick(os.path.join(SKILL, "assets", "card_tick.wav"))
    plan = json.load(open(ep.w("plan.json")))
    if plan["black"]:
        stage("4 B-roll — presenter cut-outs for the black-frame windows")
        e = json.load(open(ep.w("edl.json"), encoding="utf-8"))
        for s in e["segments"]: s["zoom"] = 1.0
        json.dump(e, open(ep.w("edl_nozoom.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        py("render_edl.py", ep.w(), ep.w("base_nozoom.mov"), "--edl=edl_nozoom.json", cwd=ep.w())
        py("matte_windows.py", ep.w("base_nozoom.mov"), ep.w("plan.json"), MODEL, ep.w(), "0.6")
    stage("4 B-roll — plate")
    dy = plan["card_dy"]
    cards = [f"--card={d['file']}|{d['out_in']}|{d['out_out']}|{d['src_in']}|{d.get('y', dy)}" for d in plan["designer"]]
    cut = ["--cutouts=plan.json|cutout_w|0|768"] if plan["black"] else []
    py("render_edl.py", ep.w(), ep.w("plate_raw.mov"), f"--gain={ep.get('plate_gain', 10)}", "--ass-under=graphics_under.ass",
       *cards, *cut, f"--sfx=plan.json|{tick}", cwd=ep.w())
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", ep.w("plate_raw.mov"), "-map", "0:v", "-map", "0:a", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", ep.f("assets", "plate.mp4"))
    stage("4 B-roll — mattes for text / MG behind the presenter"); py("matte_plate.py", EPD, MODEL)
    stage("4 B-roll — front or behind"); py("occlusion.py", EPD)
    stage("4 B-roll — OpenFilm project"); py("build_film.py", EPD)
    print(f"\nopen it in Studio:  npx -y openfilm@0.3.2 open \"{ep.f()}\"   or check frames:  run.py {EPD} look <t>")

def s_bgm():
    need(ep.f("film.html"), "run the broll stage first")
    stage("5 BGM — OpenFilm render (motion blur)")
    run(*OPENFILM, "render", "--fps", "29.97", "--blur", "--workers", str(ep.get("workers", 6)), cwd=ep.f())
    stage("5 BGM — sound, speed-up, delivery"); py("deliver.py", EPD)

STAGES = {"cut": s_cut, "subs": s_subs, "text": s_text, "broll": s_broll, "bgm": s_bgm}
if STAGE == "all":
    s_cut(); s_broll(); s_bgm()
elif STAGE == "final":
    py("final.py", EPD, *sys.argv[3:])
elif STAGE == "look":
    run(*OPENFILM, "look", sys.argv[3], cwd=ep.f())
elif STAGE in STAGES:
    STAGES[STAGE]()
else:
    sys.exit(__doc__)

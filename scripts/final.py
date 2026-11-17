"""Stage 6 定稿: ONLY after the user says this version is final ("满意 / final").

usage: final.py EPISODE_DIR [--dry] [--also DIR ...]
- moves out/<out_name>.mp4 to the Windows Videos folder (视频, e.g. C:/Users/<you>/Videos/<out_name>.mp4;
  an existing file there with the same name is replaced only after being sent to the Recycle Bin)
- sends EVERY other video file of the episode (previews, cut preview, mezzanine, plate, cut-outs, renders,
  caches), plus any in the --also folders (e.g. an older hand-built project of the same episode), to the
  Recycle Bin, so nothing is lost for good by mistake
- keeps everything that is not a video (episode.json, blocks/subs/kinetic/cards/mg, .srt, mattes) so the
  episode can still be rebuilt from the source footage
- copies the final into Google Drive (Drive for desktop must be installed and signed in): My Drive/<drive_folder>,
  only when episode.json sets "drive_folder" (e.g. "Final videos"); Drive for desktop uploads it in the background
--dry lists what would happen and changes nothing.  --upload-only: just copy an already finalized video to Drive.
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ep

VIDEO = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mxf"}
args = sys.argv[1:]
if not args: sys.exit(__doc__)
ep = Ep(args[0]); dry = "--dry" in args
also = [args[i + 1] for i, a in enumerate(args) if a == "--also" and i + 1 < len(args)]
final = os.path.normpath(ep.o(ep.get("out_name") + ".mp4"))
def videos_dir():
    out = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('MyVideos')"],
                         capture_output=True, text=True).stdout.strip()
    return out or os.path.join(os.path.expanduser("~"), "Videos")

def my_drive():
    """My Drive folder of Google Drive for desktop (a virtual drive such as G:)."""
    import string
    for L in string.ascii_uppercase:
        for name in ("My Drive", "我的云端硬盘", "我的雲端硬碟"):
            p = f"{L}:\\{name}"
            if os.path.isdir(p): return p
    return None

def to_drive(video):
    if not ep.get("drive_folder"):
        print("Google Drive: skipped (no drive_folder in episode.json)"); return None
    root = my_drive()
    if not root:
        print("Google Drive for desktop is not signed in / not running: final NOT uploaded "
              "(sign in, then  run.py EP final --upload-only)"); return None
    folder = os.path.join(root, ep.get("drive_folder")); os.makedirs(folder, exist_ok=True)
    out = os.path.join(folder, os.path.basename(video)); __import__("shutil").copy2(video, out)
    print(f"Google Drive: {out}  (Drive for desktop uploads it in the background)"); return out

def recycle(paths):
    if not paths: return
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8-sig") as fh:
        fh.write("\n".join(paths)); lst = fh.name
    ps = ("$ErrorActionPreference='Stop'; Add-Type -AssemblyName Microsoft.VisualBasic; "
          f"Get-Content -LiteralPath '{lst}' -Encoding UTF8 | Where-Object {{ $_ }} | ForEach-Object {{ "
          "[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($_, 'OnlyErrorDialogs', 'SendToRecycleBin') }")
    try: subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    finally: os.remove(lst)
    left = [p for p in paths if os.path.exists(p)]
    if left: sys.exit(f"could not move to the Recycle Bin: {left}")

keep = {os.path.normpath(x) for x in [ep.get("source", "")] + [d["file"] for d in ep.get("designer_cards", [])] if x}
keep |= {os.path.normpath(x) for x in ep.get("keep", [])}          # raw footage / B-roll never goes, even inside the folder
if "--upload-only" in args:
    rec = ep.o("FINAL.txt")
    if not os.path.exists(rec): sys.exit("not finalized yet: run  run.py EP final  first")
    to_drive(open(rec, encoding="utf-8").read().split(": ", 1)[1].strip()); sys.exit()
if not os.path.exists(final): sys.exit(f"no final video at {final}: run the bgm stage first")
others = []
for root in [ep.p()] + also:
    for d, _, files in os.walk(root):
        if "node_modules" in d: continue
        for f in files:
            p = os.path.normpath(os.path.join(d, f))
            if os.path.splitext(f)[1].lower() in VIDEO and p != final and p not in keep: others.append(p)
dest = os.path.join(videos_dir(), os.path.basename(final))
mb = lambda p: os.path.getsize(p) / 1e6
print(f"final : {final}  ({mb(final):.0f} MB)\n   -> {dest}")
print(f"to Recycle Bin: {len(others)} other video files, {sum(map(mb, others)):.0f} MB")
for p in others: print(f"   {p}")
if ep.get("drive_folder"): print(f"Google Drive: {my_drive() or 'NOT signed in'} / {ep.get('drive_folder')}")
if dry: print("(dry run: nothing changed)"); sys.exit()
if os.path.exists(dest): recycle([dest])
os.makedirs(os.path.dirname(dest), exist_ok=True)
os.replace(final, dest) if os.path.splitdrive(final)[0].lower() == os.path.splitdrive(dest)[0].lower() else __import__("shutil").move(final, dest)
recycle(others)
open(ep.o("FINAL.txt"), "w", encoding="utf-8").write(f"final video: {dest}\n")
print(f"done: {dest}")
to_drive(dest)

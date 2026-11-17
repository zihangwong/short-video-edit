"""Shared paths and helpers for the short-video-edit pipeline.

An episode is a folder:
  episode.json  blocks.json  subs.tsv  kinetic.json  cards.json  mg.json   (what the editor decides)
  work/   intermediate files      film/   the OpenFilm project      out/   deliverables
"""
import json, os, shutil, subprocess, sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL, "scripts")
PY = sys.executable
FPS_STR, FPS = "30000/1001", 30000 / 1001
OPENFILM = ["npx", "-y", "openfilm@0.3.2"]
RVM_URL = "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx"


class Ep:
    def __init__(self, root):
        self.root = os.path.abspath(root).replace("\\", "/")
        self.cfg = json.load(open(self.p("episode.json"), encoding="utf-8"))
        for d in ("work", "film", "out", "film/assets", "film/lib", "work/fonts"):
            os.makedirs(self.p(d), exist_ok=True)

    def p(self, *parts):
        return "/".join([self.root, *parts])

    def w(self, *parts):
        return self.p("work", *parts)

    def f(self, *parts):
        return self.p("film", *parts)

    def o(self, *parts):
        return self.p("out", *parts)

    def get(self, key, default=None):
        return self.cfg.get(key, default)

    def load(self, name, default=None):
        path = self.p(name)
        if not os.path.exists(path):
            return default
        return json.load(open(path, encoding="utf-8"))

    def save(self, name, obj):
        json.dump(obj, open(self.p(name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    @property
    def speed(self):
        return float(self.get("speed", 1.0))

    @property
    def font(self):
        """caption / kinetic CJK font file (absolute)"""
        f = self.get("font", "work/fonts/NotoSansSC-Black-Static.ttf")
        return f if os.path.isabs(f) else self.p(f)


def run(*cmd, cwd=None, quiet=False):
    """run a command, fail loudly"""
    cmd = [str(c) for c in cmd]
    if not quiet:
        print("  $", " ".join(cmd[:6]) + (" ..." if len(cmd) > 6 else ""), flush=True)
    r = subprocess.run(cmd, cwd=cwd, shell=(os.name == "nt" and cmd[0] in ("npx", "npm")))
    if r.returncode:
        sys.exit(f"command failed ({r.returncode}): {' '.join(cmd[:4])}")


def py(script, *args, cwd=None):
    run(PY, os.path.join(SCRIPTS, script), *args, cwd=cwd)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout
    return float(out.strip())


def stage(title):
    print(f"\n=== {title} ===", flush=True)


def need(path, hint):
    if not os.path.exists(path):
        sys.exit(f"missing {path}\n  -> {hint}")


def ensure_model(path):
    """Download the RobustVideoMatting model on first use (GPL-3.0, so it is not bundled with this repo)."""
    if os.path.exists(path):
        return path
    import urllib.request
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print(f"  downloading the RVM matting model (~15 MB, GPL-3.0) from\n    {RVM_URL}", flush=True)
    tmp = path + ".part"
    urllib.request.urlretrieve(RVM_URL, tmp)
    os.replace(tmp, path)
    return path


def ensure_tick(path):
    """Generate the short card 'tick' sound with ffmpeg if it is missing."""
    if os.path.exists(path):
        return path
    run("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=2200:duration=0.06:sample_rate=48000",
        "-af", "afade=t=in:d=0.003,afade=t=out:st=0.015:d=0.045,volume=0.6", "-ac", "2", "-c:a", "pcm_s16le", path,
        quiet=True)
    return path


def copy_if_newer(src, dst):
    if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
        shutil.copy(src, dst)

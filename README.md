# short-video-edit

An agent skill that edits a vertical talking-head short (TikTok / Reels / 小红书 / Shorts) end to end, from raw
footage to a platform-checked delivery, the way a professional editor would. Built for Claude Code; works with any
agent that loads `SKILL.md` skills.

[中文说明](README.zh-CN.md)

## What it does

| Step | What happens |
|---|---|
| 1 粗剪 Rough cut | Transcribes the footage, compares what was said with the script (flags changed numbers), picks the best takes, tightens pauses, renders a cut preview with timecode and splice QC |
| 2 识别字幕 Captions | faster-whisper word timings → one-line captions broken on jieba word boundaries |
| 3 字幕特效 Kinetic text | 12 animations (slam, drop, type, stamp, wave …) with an automatic sound effect for each, title-safe checks, timing that survives the 1.2× speed-up |
| 4 B-roll & MG | Data cards, designer clips, motion graphics; RobustVideoMatting cut-outs decide whether each text sits in front of or behind the speaker |
| 5 BGM & delivery | Motion-blurred render, single-channel voice repair, −13 LUFS loudness, side-chained BGM, true peak ≤ −1.2 dBTP, `.srt`, phone preview and a TikTok/Reels check |
| 6 定稿 Final | Only on the user's word: final to the Videos folder, every intermediate video to the Recycle Bin (never deleted for good) |

The agent makes the editorial calls (takes, proofreading, which words to animate); the scripts do the measuring and
rendering, and refuse to call anything done before it has been looked at and measured.

## Requirements

- Windows 10/11 (the final step and a few system fonts are Windows-specific)
- Python 3.12, `pip install -r requirements.txt`
- FFmpeg 7+ on PATH (NVENC used when available)
- Node.js 20+ (for `npx openfilm@0.3.2`)
- An NVIDIA GPU is recommended for faster-whisper; it falls back to CPU

## Install

Copy this folder into your project's skills directory:

```
git clone https://github.com/bubeishisuqiangua/short-video-edit.git .claude/skills/short-video-edit
pip install -r .claude/skills/short-video-edit/requirements.txt
```

Then ask your agent: *"Use short-video-edit to edit episodes/ep01 from this footage and script."*

## Use

```
python .claude/skills/short-video-edit/scripts/run.py episodes/ep01 new      # then fill in episode.json
python .claude/skills/short-video-edit/scripts/run.py episodes/ep01 cut|subs|text|broll|bgm|look <t>|final --dry
```

See [SKILL.md](SKILL.md) for every file format and the editing standards the agent follows.

## Third-party assets

- **Noto Sans SC** fonts in `assets/fonts/` — SIL Open Font License 1.1 (`assets/fonts/OFL.txt`).
- **RobustVideoMatting** model — GPL-3.0, *not* bundled; downloaded on first use from the
  [official release](https://github.com/PeterL1n/RobustVideoMatting).
- Sound effects and BGM come from the OpenFilm CC0 library at render time; none are stored here.
- Use only footage, fonts and music you have the rights to.

## License

MIT for the code in this repository. Third-party assets keep their own licences (above).

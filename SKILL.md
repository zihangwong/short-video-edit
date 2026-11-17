---
name: short-video-edit
description: Edit a vertical talking-head short (TikTok / Reels / 小红书 / Shorts) end to end in the editor's 5-step flow — 1 粗剪 rough cut, 2 识别字幕 captions, 3 字幕特效+音效 kinetic text with sound, 4 B-roll & MG (data cards, designer clips, motion graphics, presenter cut-outs), 5 BGM and delivery — with ffmpeg + OpenFilm. Use when the user hands over raw footage (and usually a script PDF) for a new episode, asks to run or re-run any of those steps, or to change an episode made this way.
---

# Short-video edit (OpenFilm pipeline)

The user is a professional editor. Work to their standard: every cut, number and sound is checked, nothing is
claimed "done" before it was looked at (frames) and measured (levels, platform check).

Scripts: `.claude/skills/short-video-edit/scripts/` (call them via `run.py`). Python 3.12, ffmpeg 9 (NVENC),
Node (for `npx -y openfilm@0.3.2`), faster-whisper on CUDA, onnxruntime-directml (RVM matting) are installed.

```
python .claude/skills/short-video-edit/scripts/run.py <episode-dir> new|cut|subs|text|broll|bgm|all|look <t>
```

## The episode folder (`episodes/<name>/`)
| file | step | who writes it |
|---|---|---|
| `episode.json` | all | source, title, out_name, speed (1.2), font (default Noto Sans SC Black; any CJK font you hold a licence for), bgm (OpenFilm CC0 id), keywords (yellow in captions), words (jieba), steps (STEP pills), cta, designer_cards, drive_folder (optional) |
| `blocks.json` | 1 | **you**: the takes, `[{a, b, label, note}]` in source seconds |
| `subs.tsv` | 2 | **you**: proofread captions `start<TAB>end<TAB>text` on the cut timeline |
| `kinetic.json` | 3 | **you**: emphasis groups (format below) |
| `cards.json`, `mg.json` | 4 | **you**: data cards and motion graphics |
| `work/` `film/` `out/` | | scripts: intermediate, the OpenFilm project, deliverables |

All times in subs/kinetic/cards/mg/steps/cta are on the **cut timeline before speed-up**. Speed is applied at delivery.

## Step 1 — 粗剪 rough cut
1. `run.py EP new` → fill `episode.json`. Then `run.py EP cut` (stops after prep if `blocks.json` is empty).
2. Prep reports the **left/right balance**. Phone and lav recordings often carry the voice on ONE channel only
   (the other ≈ -25 dB): the delivery is made dual mono from the good side automatically (`voice_channel`).
   Never average L+R.
3. Read `work/transcript.txt` next to the script PDF. Diff what he said against the script and **tell the user**
   where he deviates (numbers especially) — on-screen numbers follow what he SAYS, not the script.
4. Pick takes into `blocks.json`: structure follows the script; keep his extra elaboration; cut retakes, false starts,
   prompter voices, swearing, dead air. Last clean take of a repeated line wins unless the user says otherwise.
   Inside a block, pauses ≥ 0.45 s are tightened automatically.
5. `run.py EP cut` again → `out/cut_preview.mp4` (timecode burned in) + cut QC. **Show the user and get the cut
   approved before step 2.** Flagged "hot splices" are usually breath tails (already 40 ms faded) — say which.
6. Re-cutting later: change `blocks.json`, re-run `cut`, then `scripts/shift.py EP <cut_t> <delta>` moves every
   hand-placed time after the edit (delta = old length − new length).

## Step 2 — 识别字幕 captions
`run.py EP subs` → `subs_draft.tsv`. Proofread into `subs.tsv`: fix misheard words (whisper often turns a
spoken phrase into same-sounding nonsense characters), English spelling, simplified Chinese, drop off-script asides. Flag guesses to the user.
Captions render **one line only**: anything wider than ~10 CJK becomes the next caption automatically, timed from
word timings, broken on jieba word boundaries, never inside an English phrase, never starting with 的/了/吗/」.

## Step 3 — 字幕特效 + 音效 kinetic text
Write `kinetic.json`. Pick the punchlines, numbers, contrasts, step titles (≈ one every 5–8 s, not in card windows).
Running captions hide automatically while a group is up.
```json
{"a": 34.20, "b": 35.72, "items": [
  {"text": "会很", "x": 290, "y": 450, "fs": 96, "col": "W", "anim": "fade", "at": "会很"},
  {"text": "丢脸", "x": 800, "y": 380, "fs": 210, "col": "R", "anim": "slam", "at": "丢脸", "v": true, "rot": 4}]}
```
- `at`: a phrase he says (resolved to the real time) or a number of seconds after `a`.
- x/y = centre px on 1080×1920; keep y ≈ 380–700 (around/above the head), x 200–880. `v`: vertical stack.
- **Title-safe** (the user's standard = Premiere's inner 10% guide): everything readable stays in x 108–972,
  y 192–1728. The `text` stage moves any kinetic item that crosses it back inside (prints "title-safe … moved"),
  and the build refuses caption positions outside it. Design inside it from the start; `title_safe` in
  episode.json overrides the box.
- `col`: W Y R C or `#hex`; `latin`: Arial Black for English/numbers; `italic`; `rot` degrees.
- `anim`: fade drop rise slide_l slide_r pop **slam** type wave flip stamp split shake.
- `deco`: box underline strike check (drawn after the text lands, with its own sound).
- No outlines on any text (captions, kinetic, MG labels): soft layered drop shadow only — the user's taste ("比较高级").
- Mix sizes (a 90 px setup word + a 150–230 px punch word), mix vertical and horizontal, white/yellow/red.
Speed-up safety (automatic, `text` stage prints what it did): animations play `speed`× slower in the film so they look
as designed after the 1.2× speed-up, and every item gets land + 0.45 s hold (real time, `kinetic_hold`) + exit before its
group ends — the group is extended into free time (never into the next group / black card / MG, max 1.2 s), otherwise
the item starts up to 0.3 s before its word. Captions still return on the written time. Read the report; if an item
starts far before its word, shorten the group's text or move the next group.
Every animation and decoration gets a sound automatically (`assets/sfx_library.json`, OpenFilm CC0, rotated variants).
`run.py EP text` builds the timing; check with `look` after step 4.

## Step 4 — B-roll & MG
- **Designer clips** (ProRes 4444 with alpha, e.g. `A下卡` cards): list them in `episode.json` `designer_cards`
  `{file, out_in, out_out, src_in}`. **Check their numbers against what he says first** — designer cards are made from
  the script; if they contradict him, rebuild the card in `cards.json` in the same style instead and tell the user.
- **Data cards** (`cards.json`, designer style): `{a, b, badge, keep_bg_after?, rows:[step|value|big]}` —
  step `{t, y, num, title, sub}`, value `{t, y, label, value, t_value?, color: green|yellow|sub, strike?}`,
  big `{t, number, line}`. `[[word]]` = yellow. During cards the frame goes black, the card sits high and the
  presenter cut-out (RVM matte) sits bottom-left; captions move above him.
- **MG** (`mg.json`): types `target` (grows on `big_at`), `bucket` (`mode` overflow|fill, `label`), `frost`,
  `checklist` (`rows`, `checks`), `breakdown` (`crack_at`), `cta` (`word` = the comment keyword, `gift_at`); each with `sfx`
  `[[t, id, in, out, file_peak, target_peak], ...]`. Place MG in gaps (no kinetic / card) and tie it to the words.
- `run.py EP broll` renders the plate, mattes every kinetic/MG window at full res, decides **front vs behind** per
  text item (covered > 25 %, or a number covered > 10 % → in front; else behind for depth; force with
  `occlusion_overrides.json {"k07": [true, null]}`), and writes the OpenFilm project.
- Check frames: `run.py EP look 35.4` (prints the PNG) — look at every group/MG at least once, especially numbers.
  The user can open the project in OpenFilm Studio and drag anything.

## Step 5 — BGM & delivery
`run.py EP bgm`: OpenFilm render with motion blur (~20–30 min for 3 min), then the sound:
voice dual mono → speed-up → compression → loudnorm −13 LUFS: voice peaks sit in **0 to −6 dB on the level meter**
(the user's standard; 剪映 equivalent ≈ +13 dB), true peak ≤ −1.2 dBTP; BGM looped, side-chain ducked ≈16 dB under
speech. Delivers `out/<name>.mp4` (+ `.srt`, `_preview720.mp4` under 30 MB for the phone, `_levels.png`), runs the
TikTok/Reels check and prints L/R RMS (must match).

## Step 6 — 定稿 final (only on the user's word)
Run this ONLY when the user says this version is final (满意 / final / 定稿) — never on your own, never because a
render passed. First `run.py EP final --dry` and tell the user the one-line summary (what goes to 视频, how many
videos / MB go to the Recycle Bin), then `run.py EP final`:
the final `out/<out_name>.mp4` moves to the Windows Videos folder (`%USERPROFILE%\Videos`); every other video of
the episode (versions, previews, cut preview, mezzanine, plate, cut-outs, renders, caches) goes to the **Recycle Bin**
(not permanent). The source footage and designer clips listed in episode.json (and `keep`) are never touched; the
project files (json, subs, .srt, mattes) stay, so the episode can be rebuilt from the source. Add
`--also <dir>` for an older project folder of the same episode. `out/FINAL.txt` records where the final went.
Optional: if episode.json sets `drive_folder`, the final is also copied into that folder of the user's own My Drive
via Google Drive for desktop (installed, signed in, mounted as a drive letter); it uploads in the background. Never
copy into a client's shared folder unless the user says so. If Drive isn't signed in the step says so; after
sign-in run `run.py EP final --upload-only`.

## Step 7 — 发布文案 (when the user says 我要发布 / 发布这个视频)
If the project has a publishing-copy skill, load it and follow it; otherwise write the 小红书 / TikTok title, body,
tags and cover text from this episode's `subs.tsv` + script into `out/publish_copy.md`. Don't post for the user.

## Standards & gotchas (learned the hard way)
- iPhone footage is HDR (Dolby Vision HLG): the mezzanine is tone-mapped (mobius) to SDR BT.709. Never upload HDR as is.
- Measure L/R before anything (voice on one channel happens). Voice level: meter 0 to −6 dB.
- Springs: `slam` uses a firm spring with clamped undershoot — never let scale dip below ~0.94 (it looked like the text shrank away).
- Fonts: the caption font must cover every character (check with fontTools); 剪映's cached fonts/SFX are licensed for
  剪映 only — use one outside only when the user confirms a licence.
- 剪映 11.x drafts are encrypted: no code round-trip; deliver media + SRT if the user wants to finish in 剪映.
- Before every render, `look` at changed moments; after it, report the platform check, loudness, true peak and L/R.
- Long renders run in the background; never claim a render is done before it is.

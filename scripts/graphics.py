"""Stages 2-4 text layer: captions, kinetic emphasis timing, data cards (ASS), black frames, STEP pills, CTA.

usage: graphics.py EPISODE_DIR
reads  work/edl.json, work/transcript.json, subs.tsv, kinetic.json, cards.json, episode.json
writes work/graphics_under.ass  (cards, black frames, STEP pills, CTA card: burned into the plate)
       work/plan.json           (card ticks, black windows, designer clips -> plate + mattes)
       work/timeline.json       (one-line captions + kinetic groups with resolved times -> OpenFilm)

Times in subs.tsv / kinetic.json / cards.json / mg.json are on the CUT timeline (before speed-up).
Kinetic item "at" may be a phrase ("关键词"): it is resolved to when he actually says it.
"""
import difflib, json, logging, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Ep
from opencc import OpenCC
import jieba

ep = Ep(sys.argv[1]); t2s = OpenCC("t2s").convert
edl = json.load(open(ep.w("edl.json"), encoding="utf-8"))["segments"]
END = edl[-1]["out_out"]
SPEED = ep.speed
tr = json.load(open(ep.w("transcript.json"), encoding="utf-8"))

# ------------------------------------------------------------------ ASS helpers
def bgr(hexrgb, a=0):
    hexrgb = hexrgb.lstrip("#"); r, g, b = hexrgb[0:2], hexrgb[2:4], hexrgb[4:6]
    return f"&H{a:02X}{b}{g}{r}&".upper()
def ts(t):
    t = max(0.0, t); h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"
EV = []
def ev(a, b, layer, text, style="Base"):
    EV.append((a, f"Dialogue: {layer},{ts(a)},{ts(b)},{style},,0,0,0,,{text}"))
def rr(x, y, w, h, r):
    x2, y2 = x + w, y + h
    return (f"m {x+r} {y} l {x2-r} {y} b {x2} {y} {x2} {y} {x2} {y+r} l {x2} {y2-r} "
            f"b {x2} {y2} {x2} {y2} {x2-r} {y2} l {x+r} {y2} b {x} {y2} {x} {y2} {x} {y2-r} l {x} {y+r} b {x} {y} {x} {y} {x+r} {y}")
def circle(cx, cy, r):
    k = 0.5523 * r
    return (f"m {cx} {cy-r} b {cx+k} {cy-r} {cx+r} {cy-k} {cx+r} {cy} b {cx+r} {cy+k} {cx+k} {cy+r} {cx} {cy+r} "
            f"b {cx-k} {cy+r} {cx-r} {cy+k} {cx-r} {cy} b {cx-r} {cy-k} {cx-k} {cy-r} {cx} {cy-r}")
tw = lambda text, size: sum(size if ord(c) > 0x2E80 else size * 0.58 for c in text)

# ------------------------------------------------------------------ data cards (designer "A下卡" style)
C_CARD, C_EDGE, C_ROW, C_ROWEDGE = "111318", "1E2128", "171A20", "222630"
C_BLUE, C_YEL, C_WHITE, C_SUB, C_GREEN = "7FB4F2", "E3B341", "F3F6F8", "9A9DA3", "26A65B"
COLS = {"green": C_GREEN, "sub": C_SUB, "yellow": C_YEL, "white": C_WHITE}
FONT, FONTB, NUMF = "Noto Sans SC Black Static", "Noto Sans SC Bold Static", "Arial Black"
ENTER, OUT = 0.27, 0.15
DY = int(ep.get("card_dy", -775))        # cards sit high on a black frame; presenter cut-out bottom-left
CX, CY, CW, CH = 20, 1005 + DY, 1040, 830
TICKS, CARDWIN = [], []
def hl(text, base=C_WHITE):
    return re.sub(r"\[\[(.+?)\]\]", lambda m: "{\\1c" + bgr(C_YEL) + "\\3c" + bgr(C_YEL) + "}" + m.group(1)
                  + "{\\1c" + bgr(base) + "\\3c" + bgr(base) + "}", text)
pop = lambda: f"\\fad(180,{int(OUT*1000)})"

def card_shell(a, b, badge, keep_bg_after=0.0):
    mv = f"\\move(0,40,0,0,0,{int(ENTER*1000)})"
    ev(a, b + keep_bg_after, 1, "{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\blur30\\1c&H000000&\\1a&H8C&"
       f"\\fad({int(ENTER*1000)},{int(OUT*1000)})\\move(0,64,0,24,0,{int(ENTER*1000)})}}" + rr(CX, CY, CW, CH, 46))
    ev(a, b + keep_bg_after, 2, "{\\an7\\pos(0,0)\\p1\\bord1.5\\shad0\\1c" + bgr(C_CARD) + "\\3c" + bgr(C_EDGE)
       + f"\\fad({int(ENTER*1000)},{int(OUT*1000)}){mv}}}" + rr(CX, CY, CW, CH, 46))
    ba, pf = a + 0.20, f"\\fad(160,{int(OUT*1000)})"
    ev(ba, b, 3, "{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c" + bgr(C_BLUE) + pf + "}" + rr(63, 1042 + DY, tw(badge, 32) + 46, 63, 31))
    ev(ba, b, 4, "{\\an4" + f"\\pos(86,{1074 + DY})" + "\\fn" + FONT + "\\b0\\fs32\\bord0\\shad0\\1c&H101010&\\3c&H101010&" + pf + "}" + badge)

def step_row(t, b, y, num, title, sub=None):
    y += DY; TICKS.append(t)
    ev(t, b, 3, "{\\an7\\pos(0,0)\\p1\\bord1.5\\shad0\\1c" + bgr(C_ROW) + "\\3c" + bgr(C_ROWEDGE) + pop() + "\\move(0,16,0,0,0,180)}" + rr(63, y, 954, 157, 36))
    ev(t, b, 4, "{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c" + bgr(C_BLUE) + pop() + "\\move(0,16,0,0,0,180)}" + circle(135, y + 78, 40))
    ev(t, b, 5, "{\\an5" + f"\\move(135,{y+94},135,{y+78},0,180)" + "\\fn" + NUMF + "\\fs40\\bord0\\shad0\\1c&H101010&" + pop() + "}" + str(num))
    ty = y + (58 if sub else 78)
    ev(t, b, 5, "{\\an4" + f"\\move(203,{ty+16},203,{ty},0,180)" + "\\fn" + FONT + "\\b0\\fs48\\bord0\\shad0\\1c" + bgr(C_WHITE) + "\\3c" + bgr(C_WHITE) + pop() + "}" + hl(title))
    if sub:
        ev(t, b, 5, "{\\an4" + f"\\move(204,{y+130},204,{y+114},0,180)" + "\\fn" + FONTB + "\\b0\\fs30\\bord0\\shad0\\1c" + bgr(C_SUB) + pop() + "}" + sub)

def value_row(t, b, y, label, value=None, t_value=None, color="green", strike=False):
    y += DY; TICKS.append(t)
    ev(t, b, 5, "{\\an4" + f"\\move(63,{y+14},63,{y},0,180)" + "\\fn" + FONT + "\\b0\\fs44\\bord0\\shad0\\1c" + bgr(C_WHITE) + "\\3c" + bgr(C_WHITE) + pop() + "}" + hl(label))
    if value:
        tv = t_value if t_value is not None else t
        if tv != t: TICKS.append(tv)
        ev(tv, b, 5, "{\\an6" + f"\\move(1017,{y+14},1017,{y},0,180)" + "\\fn" + NUMF + f"\\fs64{'\\s1' if strike else ''}\\bord0\\shad0\\1c"
           + bgr(COLS.get(color, color)) + pop() + "}" + value)

def big_number(t, b, number, line):
    TICKS.append(t)
    ev(t, b, 5, "{\\an5\\fn" + NUMF + "\\fs150\\bord0\\shad0\\1c" + bgr(C_GREEN)
       + "\\fad(160,150)\\fscx80\\fscy80\\t(0,180,\\fscx104\\fscy104)\\t(180,260,\\fscx100\\fscy100)" + f"\\pos(540,{1250 + DY})}}" + number)
    ev(t + 0.25, b, 5, "{\\an5" + f"\\pos(540,{1455 + DY})" + "\\fn" + FONT + "\\b0\\fs44\\bord0\\shad0\\1c" + bgr(C_WHITE) + "\\3c" + bgr(C_WHITE) + "\\fad(180,150)}" + hl(line))

for c in ep.load("cards.json", []):
    CARDWIN.append((c["a"], c["b"]))
    card_shell(c["a"], c["b"], c["badge"], c.get("keep_bg_after", 0.0))
    for r in c.get("rows", []):
        if r["type"] == "step": step_row(r["t"], c["b"], r["y"], r["num"], r["title"], r.get("sub"))
        elif r["type"] == "value": value_row(r["t"], c["b"], r["y"], r["label"], r.get("value"), r.get("t_value"), r.get("color", "green"), r.get("strike", False))
        elif r["type"] == "big": big_number(r["t"], c["b"], r["number"], r["line"])
DESIGNER = ep.get("designer_cards", [])          # [{"file", "out_in", "out_out", "src_in"}]
for d in DESIGNER:
    CARDWIN.append((d["out_in"], d["out_out"]))

BLACK = []                                        # card windows merged -> full-frame black + presenter cut-out
for a, b in sorted(CARDWIN):
    if BLACK and a - BLACK[-1][1] < 0.6: BLACK[-1][1] = max(BLACK[-1][1], b)
    else: BLACK.append([a, b])
for a, b in BLACK:
    ev(a, b, 0, "{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c&H000000&\\fad(150,150)}m 0 0 l 1080 0 l 1080 1920 l 0 1920")

def minus(a, b, wins, pad=0.15):
    out, cur = [], a
    for wa, wb in sorted(wins):
        if wb + pad <= cur or wa - pad >= b: continue
        if wa - pad > cur: out.append((cur, wa - pad))
        cur = max(cur, wb + pad)
    if cur < b: out.append((cur, b))
    return out

POP = r"{\fad(120,120)\fscx70\fscy70\t(0,160,\fscx104\fscy104)\t(160,240,\fscx100\fscy100)}"
for a, b, label in ep.get("steps", []):          # STEP pills stay up for the whole step (hidden on black frames)
    for pa, pb in minus(a, b, BLACK):
        if pb - pa > 0.5: ev(pa, pb, 6, "{\\fad(150,150)}" + label, "Pill")
cta = ep.get("cta")
if cta:
    ev(cta["a"], min(cta.get("b", END), END), 6, POP + cta["text"] + ("\\N{\\fs54}" + cta["sub"] if cta.get("sub") else ""), "Cta")

# ------------------------------------------------------------------ word times on the cut timeline
CJK = "⺀-鿿"
WORDS = [w for s in tr["segments"] for w in s["words"]]
WCH = []
for seg in edl:
    for w in WORDS:
        if min(w["e"], seg["src_out"]) - max(w["s"], seg["src_in"]) <= 0.04: continue
        s0 = seg["out_in"] + max(w["s"], seg["src_in"]) - seg["src_in"]
        e0 = seg["out_in"] + min(w["e"], seg["src_out"]) - seg["src_in"]
        toks = re.findall("[a-z0-9']+|[" + CJK + "]", t2s(w["w"].strip()).lower())
        for i, tok in enumerate(toks):
            WCH.append((tok, s0 + (e0 - s0) * i / max(1, len(toks))))
WCH.sort(key=lambda x: x[1])

# ------------------------------------------------------------------ kinetic groups (kinetic.json)
KDATA, KWIN = [], []
def find_time(phrase, a, b, after=None):
    keys = re.findall(r"[a-z0-9']+|[" + CJK + "]", phrase.lower())
    win = [w for w in WCH if (after if after is not None else a - 0.3) <= w[1] <= b + 0.3]
    for i in range(len(win)):
        if keys and all(i + j < len(win) and win[i + j][0] == k for j, k in enumerate(keys)):
            return win[i][1]
    return next((w[1] for w in win if keys and w[0] == keys[0]), None)
NAMED = {"W": "#FFFFFF", "Y": "#FFE600", "R": "#FF2B2B", "C": "#7FD4FF"}
for g in ep.load("kinetic.json", []):
    a, b = g["a"], g["b"]; KWIN.append((a, b)); last = None; items = []
    for it in g["items"]:
        at = it.get("at", 0.0)
        t = a + at if isinstance(at, (int, float)) else (find_time(at, a, b, after=last) or a)
        t = max(a, min(t, b - 0.25)); last = t
        items.append({"text": it["text"], "x": it["x"], "y": it["y"], "fs": it["fs"], "col": NAMED.get(it.get("col", "W"), it.get("col")),
                      "anim": it["anim"], "t": round(t, 3), "v": bool(it.get("v")), "rot": it.get("rot", 0),
                      "latin": bool(it.get("latin")), "italic": bool(it.get("italic")), "deco": it.get("deco")})
    KDATA.append({"a": round(a, 3), "b": round(b, 3), "items": items, "slow": SPEED})

# ---- every entrance must FINISH and be readable at the delivered speed --------------------------
# The film runs on the cut timeline and is sped up at delivery, so the engine plays each animation
# SPEED x slower (group["slow"]) and every item needs  land + hold + exit  of real time before its
# group ends. Extend the group into free time first (never into the next group / black card / MG);
# if there is no room, start the item a little earlier (before the word) and report it.
LAND = {"fade": .17, "drop": .35, "rise": .35, "slide_l": .35, "slide_r": .35, "pop": .45, "slam": .3, "flip": .45,
        "stamp": .25, "shake": .55, "split": .35}
DECO_END = {"box": .34, "underline": .34, "strike": .44, "check": .54}
HOLD, EXIT, MAX_EXT = float(ep.get("kinetic_hold", 0.45)), 0.17, 1.2      # real seconds / cut seconds
def land(it):
    n = len(it["text"])
    if it["anim"] == "type": x = (n - 1) * .07 + .06
    elif it["anim"] == "wave": x = (n - 1) * .07 + .35
    else: x = LAND[it["anim"]]
    if it["v"]: x += (n - 1) * .045
    if it.get("deco"): x = max(x, DECO_END[it["deco"]])
    return x
walls = sorted([g["a"] for g in KDATA] + [w[0] for w in BLACK] + [m["a"] for m in ep.load("mg.json", [])])
# KWIN keeps the WRITTEN windows: running captions come back on time (low on screen) while the
# kinetic text above finishes; the two may share the screen for a moment.
MIN_HOLD, MAX_EARLY = 0.15, 0.30          # real s the landed text must stay at least; cut s an item may lead its word
for g in sorted(KDATA, key=lambda g: g["a"]):
    cap = min([w for w in walls if w > g["a"] + 0.01] + [END]) - 0.08
    need = max(it["t"] + SPEED * (land(it) + HOLD + EXIT) for it in g["items"])
    if need > g["b"]:
        nb = min(need, cap, g["b"] + MAX_EXT)
        if nb > g["b"] + 1e-3: print(f"  kinetic {g['a']:7.2f}: end {g['b']:.2f} -> {nb:.2f} so every entrance lands")
        g["b"] = round(max(g["b"], nb), 3)
    for it in g["items"]:
        ideal = g["b"] - SPEED * (land(it) + HOLD + EXIT)              # full hold
        floor = g["b"] - SPEED * (land(it) + MIN_HOLD + EXIT)          # must at least land and be seen
        t0 = it["t"]
        if t0 > ideal: it["t"] = max(ideal, t0 - MAX_EARLY)
        if it["t"] > floor: it["t"] = floor
        it["t"] = round(max(g["a"], it["t"]), 3)
        if t0 - it["t"] > 1e-3:
            print(f"  kinetic {g['a']:7.2f}: '{it['text']}' starts {t0 - it['t']:.2f}s before its word (no room after it)")

# ---- title-safe box (the user's standard: Premiere's inner 10% guide = x 108-972, y 192-1728) -----
# Every kinetic item is kept inside it: if its box crosses an edge it is moved in (size kept) and
# reported; if it is wider/taller than the box it is also scaled down. Rotation is ignored.
SAFE = ep.get("title_safe", [108, 192, 972, 1728])
def ext(it):
    fs, n = it["fs"], len(it["text"])
    if it["v"]: return fs, fs * 1.02 * n, 0.0, fs * 1.02 * (n - 1) / 2      # w, h, dx, dy (vertical: y is the first char)
    w = sum(fs if ord(c) > 0x2E80 else fs * (.68 if it["latin"] else .58) for c in it["text"])
    return w, fs, 0.0, 0.0
for g in KDATA:
    for it in g["items"]:
        w, h, _, dy = ext(it)
        k = min(1.0, (SAFE[2] - SAFE[0]) / w, (SAFE[3] - SAFE[1]) / h)
        if k < 1: it["fs"] = int(it["fs"] * k); w, h, _, dy = ext(it)
        cx, cy = it["x"], it["y"] + dy
        nx = min(max(cx, SAFE[0] + w / 2), SAFE[2] - w / 2)
        ny = min(max(cy, SAFE[1] + h / 2), SAFE[3] - h / 2)
        if k < 1 or abs(nx - cx) > .5 or abs(ny - cy) > .5:
            print(f"  title-safe {g['a']:7.2f}: '{it['text']}' moved {nx - cx:+.0f},{ny - cy:+.0f}px" + (f", size x{k:.2f}" if k < 1 else ""))
        it["x"], it["y"] = round(nx), round(ny - dy)

# ------------------------------------------------------------------ one-line captions (subs.tsv)
jieba.setLogLevel(logging.WARNING)
for w in ep.get("words", []): jieba.add_word(w)
KEY = re.compile(r"(RM[\d,]+\+?|\d[\d,]*\s*(?:k|万块|万|块|个月|million)?" + "".join("|" + re.escape(k) for k in ep.get("keywords", [])) + ")", re.I)
MAXW = float(ep.get("caption_max_width", 10))    # display width per caption (CJK = 1, latin ~0.56); one line only
toks_of = lambda text: re.findall("[A-Za-z0-9'][A-Za-z0-9',.+]*|[" + CJK + "]|\\s+|.", text)
width = lambda s: sum(1 if ord(c) > 0x2E80 else 0.56 for c in s)

def token_times(a, b, toks):
    keys = [re.sub("[^a-z0-9" + CJK + "]", "", t.lower()) for t in toks]
    idx = [i for i, k in enumerate(keys) if k]
    window = [w for w in WCH if a - 0.25 <= w[1] <= b + 0.1]
    sm = difflib.SequenceMatcher(None, [keys[i] for i in idx], [w[0] for w in window], autojunk=False)
    return {idx[blk.a + j]: window[blk.b + j][1] for blk in sm.get_matching_blocks() for j in range(blk.size)}

def ok_breaks(toks):
    text = "".join(toks); cuts, pos = set(), 0
    for w in jieba.cut(text, HMM=False):
        pos += len(w); cuts.add(pos)
    ok, off = set(), 0
    lat = lambda t: bool(re.match("[A-Za-z0-9']", t))
    for k, t in enumerate(toks):
        if k and off in cuts:
            inside = (lat(toks[k - 1]) or toks[k - 1].isspace()) and (lat(t) or t.isspace()) and \
                     any(lat(x) for x in toks[max(0, k - 2):k]) and any(lat(x) for x in toks[k:k + 2])
            if not inside: ok.add(k)
        off += len(t)
    return ok

def split_cue(a, b, text):
    if width(text) <= MAXW: return [(a, b, text)]
    toks = toks_of(text); tt = token_times(a, b, toks)
    units, k = [], 0
    while k < len(toks):                          # a latin phrase never splits
        if re.match("[A-Za-z0-9]", toks[k]):
            j = k
            while j + 1 < len(toks) and (re.match("[A-Za-z0-9]", toks[j + 1]) or
                                         (toks[j + 1].isspace() and j + 2 < len(toks) and re.match("[A-Za-z0-9]", toks[j + 2]))):
                j += 1
            units.append(list(range(k, j + 1))); k = j + 1
        else:
            units.append([k]); k += 1
    chunks, cur = [], []
    for u in units:
        if all(toks[j].isspace() for j in u):
            if cur: cur += u
            continue
        cw = sum(width(toks[j]) for j in cur); uw = width("".join(toks[j] for j in u))
        if cur and cw + uw > MAXW and not (cw < 3 and cw + uw <= 12):
            chunks.append(cur); cur = []
        cur += u
        if toks[u[-1]] in "，、？！。," and sum(width(toks[j]) for j in cur) >= 4:
            chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    for k in range(1, len(chunks)):
        while chunks[k] and toks[chunks[k][0]] in "的了吗呢啊吧？！，、" and len(chunks[k]) > 1:
            chunks[k - 1].append(chunks[k].pop(0))
    chunks = [c for c in chunks if c]
    if len(chunks) > 1 and width("".join(toks[j] for j in chunks[-1]).strip()) < 2.5:
        last = chunks.pop(); chunks[-1] += last
    if len(chunks) > 1:                           # chunk edges on Chinese word boundaries
        OK = ok_breaks(toks)
        for i in range(len(chunks) - 1):
            while chunks[i + 1] and chunks[i + 1][0] not in OK and len(chunks[i]) > 1:
                chunks[i + 1].insert(0, chunks[i].pop())
        chunks = [c for c in chunks if c]
    starts = [next((tt[j] for j in ch if j in tt), None) for ch in chunks]; starts[0] = a
    for k in range(1, len(starts)):
        if starts[k] is None or starts[k] <= starts[k - 1] + 0.25 or starts[k] >= b - 0.2:
            w0 = sum(width("".join(toks[j] for j in c)) for c in chunks[:k])
            starts[k] = max(starts[k - 1] + 0.3, a + (b - a) * w0 / width(text))
    return [(starts[k], starts[k + 1] - 0.02 if k + 1 < len(chunks) else b, "".join(toks[j] for j in ch).strip())
            for k, ch in enumerate(chunks)]

def segs(line):
    out, pos = [], 0
    for m in KEY.finditer(line):
        if m.start() > pos: out.append([line[pos:m.start()], False])
        out.append([m.group(0), True]); pos = m.end()
    if pos < len(line): out.append([line[pos:], False])
    return out

CDATA = []
for line in open(ep.p("subs.tsv"), encoding="utf-8"):
    if not line.strip(): continue
    a, b, text = line.rstrip("\n").split("\t"); a, b = float(a), float(b)
    for ca, cb, ct in split_cue(a, b, text):
        if cb - ca < 0.12 or not ct: continue
        if any(ka - 0.05 <= ca < kb for ka, kb in KWIN): continue      # kinetic text owns this moment
        black = any(wa - 0.05 <= ca < wb for wa, wb in BLACK)
        CDATA.append({"a": round(ca, 3), "b": round(cb, 3), "black": black, "y": 1590 if black else 1330, "lines": [segs(ct)]})

# ------------------------------------------------------------------ write
HEAD = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,{FONT},40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Pill,{FONT},54,&H00FFFFFF,&H00FFFFFF,{bgr("FF8C1E")},&H00000000,0,0,0,0,100,100,2,0,3,14,0,8,70,140,230,1
Style: Cta,{FONT},64,&H00000000,&H00000000,{bgr("FFE600")},&H00000000,0,0,0,0,100,100,2,0,3,22,0,8,70,140,330,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
EV.sort(key=lambda e: e[0])
open(ep.w("graphics_under.ass"), "w", encoding="utf-8-sig").write(HEAD + "\n".join(e[1] for e in EV) + "\n")
json.dump({"ticks": sorted(TICKS), "black": BLACK, "card_dy": DY, "designer": DESIGNER, "kinetic": KWIN},
          open(ep.w("plan.json"), "w"), indent=1)
json.dump({"fps": 30000 / 1001, "duration": END, "captions": CDATA, "kinetic": KDATA, "black": BLACK},
          open(ep.w("timeline.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"graphics: {len(CDATA)} captions, {len(KDATA)} kinetic groups, {len(ep.load('cards.json', []))} cards, "
      f"{len(DESIGNER)} designer clips, black windows {BLACK}")

// Kinetic emphasis text for OpenFilm pages (v10). Pure function of t: closed-form springs and
// deterministic "noise", so the same t always draws the same picture. Motion blur comes from
// `openfilm render --blur`.
//
// anims: fade drop rise slide_l slide_r pop slam | type wave flip stamp split shake
// deco : box underline strike check  (drawn after the text lands, each with its own sound in film.html)
const spring = (t, k, c, m) => {
  if (t <= 0) return 0;
  const w0 = Math.sqrt(k / m), z = c / (2 * Math.sqrt(k * m));
  if (z < 1) { const wd = w0 * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + (z * w0 / wd) * Math.sin(wd * t)); }
  return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
};
const bouncy = (t) => spring(t, 190, 11, 0.6);
const firm = (t) => spring(t, 240, 18, 0.6);
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const lerp = (x, x0, x1, y0, y1) => y0 + (y1 - y0) * clamp((x - x0) / (x1 - x0), 0, 1);
const easeOut = (x) => 1 - Math.pow(1 - clamp(x, 0, 1), 3);
export const DECO_AT = { box: 0.18, underline: 0.18, strike: 0.28, check: 0.32 };   // seconds after the item starts

const PER_CHAR = new Set(["type", "wave", "split"]);

function textStyle(el, it) {
  const sw = Math.max(4, Math.round(it.fs / 26));
  Object.assign(el.style, {
    fontFamily: it.latin ? "'Arial Black', CapFont" : "CapFont", fontStyle: it.italic ? "italic" : "normal",
    fontSize: it.fs + "px", lineHeight: "1", color: it.col, whiteSpace: "nowrap",
    // no outline: a tight contact shadow + a wide soft one (reads on bright backgrounds, looks less "meme")
    textShadow: `0 ${Math.round(sw * .5)}px ${Math.round(sw * .9)}px rgba(0,0,0,.7), 0 0 ${Math.round(sw * 3)}px rgba(0,0,0,.5), ` +
                `0 ${Math.round(sw * 1.6)}px ${Math.round(sw * 5)}px rgba(0,0,0,.45)`,
  });
}

export function kinetic(group) {
  const root = document.body;
  root.style.cssText = "margin:0;width:1080px;height:1920px;overflow:hidden;background:transparent;perspective:900px";
  const units = [];                      // one per moving element
  group.items.forEach((it) => {
    const vchars = it.v ? Array.from(it.text) : [it.text];
    vchars.forEach((txt, ci) => {
      const wrap = document.createElement("div");
      Object.assign(wrap.style, { position: "absolute", left: it.x + "px",
        top: (it.y + (it.v ? ci * it.fs * 1.02 : 0)) + "px", transformStyle: "preserve-3d" });
      const box = document.createElement("div");
      textStyle(box, it);
      const spans = [];
      if (PER_CHAR.has(it.anim) && !it.v) {
        for (const ch of Array.from(txt)) {
          const s = document.createElement("span");
          s.textContent = ch; s.style.display = "inline-block"; s.style.whiteSpace = "pre";
          box.appendChild(s); spans.push(s);
        }
      } else box.textContent = txt;                     // editable text in Studio
      wrap.appendChild(box); root.appendChild(wrap);
      const deco = ci === vchars.length - 1 && it.deco ? makeDeco(it.deco, it.col) : null;
      if (deco) wrap.appendChild(deco);
      units.push({ wrap, box, spans, it, delay: ci * 0.045, deco });
    });
  });
  const len = group.b - group.a;
  const font = new FontFace("CapFont", "url(lib/caption.ttf)");
  window.film = {
    duration: len,
    ready: font.load().then((f) => { document.fonts.add(f); layoutDeco(units); }),
    frame(t) { for (const u of units) draw(u, t, group, len); },
  };
}

function makeDeco(kind, col) {
  const d = document.createElement("div");
  d.style.position = "absolute";
  if (kind === "check") {
    d.innerHTML = '<svg viewBox="0 0 100 100" width="100%" height="100%"><path d="M12 54 L40 80 L90 18" fill="none" ' +
      'stroke="#2BD96B" stroke-width="16" stroke-linecap="round" stroke-linejoin="round" pathLength="1" ' +
      'stroke-dasharray="1" style="filter:drop-shadow(0 4px 4px rgba(0,0,0,.6))"/></svg>';
  }
  d.dataset.kind = kind; d.dataset.col = col;
  return d;
}

function layoutDeco(units) {
  for (const u of units) {
    if (!u.deco) continue;
    const w = u.box.offsetWidth, h = u.box.offsetHeight, fs = u.it.fs, k = u.deco.dataset.kind;
    const s = u.deco.style;
    // coordinates are relative to the wrapper's top-left, which is the text box's top-left
    if (k === "box") Object.assign(s, { left: -fs * .18 + "px", top: -fs * .12 + "px", width: w + fs * .36 + "px",
      height: h + fs * .24 + "px", border: `${Math.round(fs * .07)}px solid ${u.deco.dataset.col}`, borderRadius: fs * .16 + "px",
      boxShadow: "0 4px 10px rgba(0,0,0,.5)", boxSizing: "border-box" });
    if (k === "underline") Object.assign(s, { left: "0px", top: h + fs * .04 + "px", width: w + "px",
      height: Math.round(fs * .13) + "px", background: u.deco.dataset.col, borderRadius: "6px", boxShadow: "0 3px 6px rgba(0,0,0,.6)" });
    if (k === "strike") Object.assign(s, { left: -fs * .1 + "px", top: h / 2 - fs * .07 + "px", width: w + fs * .2 + "px",
      height: Math.round(fs * .14) + "px", background: "#FF2B2B", borderRadius: "8px", transform: "rotate(-7deg)",
      boxShadow: "0 3px 6px rgba(0,0,0,.6)" });
    if (k === "check") Object.assign(s, { left: w + fs * .12 + "px", top: h / 2 - fs * .45 + "px", width: fs * .9 + "px", height: fs * .9 + "px" });
  }
}

function draw(u, t, group, len) {
  const { wrap, box, spans, it, delay, deco } = u;
  const S = group.slow || 1;                                // film is sped up S x at delivery: play S x slower
  const lt = (t - (it.t - group.a)) / S - delay;
  if (lt < 0) { wrap.style.visibility = "hidden"; return; }
  wrap.style.visibility = "visible";
  let tx = 0, ty = 0, sc = 1, rot = it.rot, op = 1, blur = 0, rx = 0;
  const b = bouncy(lt), f = firm(lt);
  switch (it.anim) {
    case "fade": op = lerp(lt, 0, .13, 0, 1); blur = lerp(lt, 0, .17, 10, 0); break;
    case "drop": ty = (1 - f) * -170; op = lerp(lt, 0, .07, .3, 1); break;
    case "rise": ty = (1 - f) * 170; op = lerp(lt, 0, .07, .3, 1); break;
    case "slide_l": tx = (1 - f) * -520; break;
    case "slide_r": tx = (1 - f) * 520; break;
    case "pop": sc = .2 + .8 * b; rot = it.rot + (1 - b) * -20; break;
    case "slam": sc = 1 + Math.max(1 - f, -0.013) * 4.6; op = lerp(lt, 0, .1, .35, 1); blur = lerp(lt, 0, .13, 4, 0); break;
    case "flip": rx = (1 - b) * 92; op = lerp(lt, 0, .05, 0, 1); break;
    case "stamp": {                                  // hits fast, then a short decaying jolt
      const k = easeOut(lt / .11); sc = 2.3 - 1.3 * k; rot = it.rot - 14 * (1 - k); op = lerp(lt, 0, .05, 0, 1);
      if (lt > .11) { const d = Math.exp(-(lt - .11) * 22); tx = 7 * Math.sin(lt * 90) * d; ty = 5 * Math.cos(lt * 77) * d; }
      blur = lerp(lt, 0, .1, 5, 0); break; }
    case "shake": {
      sc = 1 + Math.max(1 - f, -0.02) * .35; op = lerp(lt, 0, .05, 0, 1);
      const d = lt > .08 ? Math.exp(-(lt - .08) * 7) : 0; tx = 16 * Math.sin(lt * 63) * d; rot = it.rot + 3.5 * Math.sin(lt * 41) * d; break; }
    case "type": case "wave": case "split": break;   // per character below
  }
  if (spans.length) {
    const n = spans.length;
    spans.forEach((s, i) => {
      let st = "", so = 1;
      if (it.anim === "type") { const li = lt - i * .07; so = li >= 0 ? 1 : 0; const k = easeOut(li / .06); st = `scale(${1.35 - .35 * k})`; }
      if (it.anim === "wave") { const li = lt - i * .07; so = lerp(li, 0, .05, 0, 1); st = `translateY(${(1 - bouncy(li)) * 70}px)`; }
      if (it.anim === "split") { const side = i < n / 2 ? -1 : 1; so = lerp(lt, 0, .05, 0, 1); st = `translateX(${side * (1 - f) * 460}px)`; }
      s.style.transform = st; s.style.opacity = so;
    });
  }
  const k = lerp(t, len - .17 * S, len, 0, 1);            // exit
  sc *= 1 - .3 * k; op *= 1 - k; blur += 6 * k;
  wrap.style.transform = `translate(-50%,-50%) translate(${tx}px,${ty}px) scale(${sc}) rotate(${rot}deg) rotateX(${rx}deg)`;
  wrap.style.opacity = op;
  wrap.style.filter = blur ? `blur(${blur}px)` : "none";
  if (deco) {
    const dk = deco.dataset.kind, dt = lt - DECO_AT[dk];
    const p = easeOut(dt / (dk === "check" ? .22 : .16));
    if (dk === "check") { deco.style.opacity = dt >= 0 ? 1 : 0; const path = deco.querySelector("path"); if (path) path.style.strokeDashoffset = 1 - p; }
    else { deco.style.opacity = dt >= 0 ? 1 : 0; deco.style.clipPath = `inset(0 ${100 - 100 * p}% 0 0)`; }
  }
}

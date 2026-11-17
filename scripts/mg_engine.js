// Motion-graphics pages for OpenFilm (vector SVG/DOM). Pure function of t.
// types: target | bucket (overflow | fill) | frost | checklist | breakdown | cta
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
const ease = (x) => 1 - Math.pow(1 - clamp(x, 0, 1), 3);
const rnd = (i) => { const s = Math.sin(i * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };   // fixed noise
const YEL = "#FFE600", RED = "#FF2B2B", GOLD = "#F5B800", GOLD2 = "#FFD84D";
const TXT = "font-family:CapFont;text-shadow:0 2px 4px rgba(0,0,0,.7),0 0 16px rgba(0,0,0,.5),0 8px 28px rgba(0,0,0,.4)";

const el = (html) => { const d = document.createElement("div"); d.innerHTML = html.trim(); return d.firstElementChild; };
const exitK = (t, len) => lerp(t, len - .2, len, 0, 1);

const COIN = (r) => `<svg width="${2 * r}" height="${2 * r}" viewBox="-50 -50 100 100"><circle r="46" fill="${GOLD}" stroke="#000" stroke-width="7"/>` +
  `<circle r="32" fill="none" stroke="${GOLD2}" stroke-width="6"/><text y="17" text-anchor="middle" font-size="46" font-family="Arial Black" fill="#8a5a00">$</text></svg>`;

export function mg(spec) {
  document.body.style.cssText = "margin:0;width:1080px;height:1920px;overflow:hidden;background:transparent";
  const len = spec.b - spec.a, rel = (x) => x - spec.a;
  const font = new FontFace("CapFont", "url(lib/caption.ttf)");
  const builders = { target, bucket, frost, checklist, breakdown, cta };
  const frame = builders[spec.type](spec, len, rel);
  window.film = { duration: len, ready: font.load().then((f) => document.fonts.add(f)), frame };
}

// ---------------------------------------------------------------- a target that keeps growing
function target(s, len, rel) {
  const g = el(`<div style="position:absolute;left:${s.x}px;top:${s.y}px;width:0;height:0"></div>`);
  const svg = el(`<svg width="420" height="420" viewBox="-110 -110 220 220" style="position:absolute;left:-210px;top:-210px;overflow:visible;filter:drop-shadow(0 8px 10px rgba(0,0,0,.5))">
    <circle r="100" fill="${RED}" stroke="#000" stroke-width="8"/><circle r="72" fill="#fff" stroke="#000" stroke-width="6"/>
    <circle r="46" fill="${RED}" stroke="#000" stroke-width="6"/><circle r="20" fill="#fff" stroke="#000" stroke-width="5"/>
    <g class="arrow"><line x1="0" y1="0" x2="150" y2="-150" stroke="#000" stroke-width="16" stroke-linecap="round"/>
    <line x1="0" y1="0" x2="150" y2="-150" stroke="${YEL}" stroke-width="8" stroke-linecap="round"/>
    <path d="M150 -150 l-6 40 l-34 -34 z" fill="${YEL}" stroke="#000" stroke-width="5"/></g></svg>`);
  const rings = [0, 1, 2].map(() => el(`<div style="position:absolute;left:-210px;top:-210px;width:420px;height:420px;border-radius:50%;border:10px solid ${YEL};opacity:0"></div>`));
  rings.forEach((r) => g.appendChild(r)); g.appendChild(svg); document.body.appendChild(g);
  const arrow = svg.querySelector(".arrow"); const big = rel(s.big_at);
  return (t) => {
    const appear = bouncy(t);
    let sc = .35 * appear + .25 * ease((t - .4) / 1.6);              // slowly growing...
    sc += .9 * (1 - Math.exp(-Math.max(0, t - big) * 5));            // ...then BIG on "很大的目标"
    const pulse = t > big ? .05 * Math.sin((t - big) * 14) * Math.exp(-(t - big) * 2) : 0;
    const k = exitK(t, len);
    g.style.transform = `scale(${(sc + pulse) * (1 - .3 * k)})`; g.style.opacity = 1 - k;
    arrow.style.transform = `translate(${(1 - firm(t - .5)) * 220}px,${(1 - firm(t - .5)) * -220}px)`;
    arrow.style.opacity = t > .5 ? 1 : 0;
    rings.forEach((r, i) => { const rt = (t - big - i * .22); const on = rt > 0 && rt < .7;
      r.style.opacity = on ? (1 - rt / .7) * .9 : 0; r.style.transform = `scale(${1 + rt * 1.1})`; });
  };
}

// ---------------------------------------------------------------- a bucket of gold
function bucket(s, len, rel) {
  const g = el(`<div style="position:absolute;left:${s.x}px;top:${s.y}px;width:0;height:0"></div>`);
  const W = 300, H = 250;
  const svg = el(`<svg width="${W + 40}" height="${H + 40}" viewBox="-20 -20 ${W + 40} ${H + 40}" style="position:absolute;left:${-W / 2 - 20}px;top:${-H / 2 - 20}px;overflow:visible;filter:drop-shadow(0 8px 10px rgba(0,0,0,.55))">
    <defs><clipPath id="inside"><path d="M10 30 L${W - 10} 30 L${W - 40} ${H} L40 ${H} Z"/></clipPath></defs>
    <path d="M10 30 L${W - 10} 30 L${W - 40} ${H} L40 ${H} Z" fill="#6b4a1f" stroke="#000" stroke-width="9"/>
    <rect class="fill" x="0" y="${H}" width="${W}" height="${H}" fill="${GOLD}" clip-path="url(#inside)"/>
    <path d="M10 30 L${W - 10} 30 L${W - 40} ${H} L40 ${H} Z" fill="none" stroke="#000" stroke-width="9"/>
    <rect x="22" y="${H * .45}" width="${W - 44}" height="16" fill="#3b2a12"/><rect x="34" y="${H * .8}" width="${W - 68}" height="14" fill="#3b2a12"/>
    <ellipse cx="${W / 2}" cy="30" rx="${W / 2 - 4}" ry="22" fill="#2a1d0c" stroke="#000" stroke-width="8"/>
    <path d="M18 34 Q${W / 2} -150 ${W - 18} 34" fill="none" stroke="#000" stroke-width="12"/><path d="M18 34 Q${W / 2} -150 ${W - 18} 34" fill="none" stroke="#9a9a9a" stroke-width="5"/></svg>`);
  const label = el(`<div style="position:absolute;left:0;top:${H * .2}px;transform:translate(-50%,-50%);white-space:nowrap;font-size:${s.label.length > 4 ? 70 : 92}px;color:${YEL};${TXT}">${s.label}</div>`);
  g.appendChild(svg); g.appendChild(label); document.body.appendChild(g);
  const fill = svg.querySelector(".fill");
  const N = s.mode === "overflow" ? 14 : 6;
  const coins = Array.from({ length: N }, (_, i) => { const c = el(`<div style="position:absolute;left:-40px;top:-40px">${COIN(40)}</div>`); g.appendChild(c); return c; });
  return (t) => {
    const k = exitK(t, len), a = bouncy(t);
    g.style.transform = `scale(${(.3 + .7 * a) * (1 - .3 * k)}) rotate(${(1 - a) * -12}deg)`; g.style.opacity = 1 - k;
    if (s.mode === "overflow") {
      fill.setAttribute("y", 30);                                   // already full: coins burst out of the top
      coins.forEach((c, i) => { const ct = t - .15 - i * .07; if (ct < 0) { c.style.opacity = 0; return; }
        const vx = (rnd(i) - .5) * 900, vy = -700 - rnd(i + 9) * 600, g2 = 1900;
        const x = vx * ct, y = -60 + vy * ct + .5 * g2 * ct * ct;
        c.style.opacity = 1; c.style.transform = `translate(${x}px,${Math.min(y, 160)}px) rotate(${ct * 600 * (rnd(i) - .5)}deg) scale(${.7 + .5 * rnd(i + 3)})`; });
    } else {
      const lvl = clamp((t - .2) / 2.0, 0, 1) * .75;                // fill rises as coins drop in
      fill.setAttribute("y", H - lvl * (H - 30));
      coins.forEach((c, i) => { const ct = t - .22 - i * .4; if (ct < 0 || ct > .32) { c.style.opacity = 0; return; }
        const y = -520 + 520 * ease(ct / .3); c.style.opacity = 1; c.style.transform = `translate(${(rnd(i) - .5) * 80}px,${y}px) rotate(${ct * 500}deg)`; });
    }
  };
}

// ---------------------------------------------------------------- frost creeping in from the edges
function frost(s, len) {
  const d = el(`<svg width="1080" height="1920" style="position:absolute;left:0;top:0">
    <defs><radialGradient id="v" cx="50%" cy="45%" r="75%"><stop offset="55%" stop-color="#bfe8ff" stop-opacity="0"/>
      <stop offset="85%" stop-color="#d8f2ff" stop-opacity=".55"/><stop offset="100%" stop-color="#ffffff" stop-opacity=".92"/></radialGradient>
      <filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".012 .02" numOctaves="3" seed="7"/><feColorMatrix values="0 0 0 0 .9  0 0 0 0 .97  0 0 0 0 1  0 0 0 1.4 -.55"/></filter>
      <mask id="m"><rect width="1080" height="1920" fill="url(#v)"/></mask></defs>
    <rect class="tint" width="1080" height="1920" fill="#6fc6ff" opacity="0"/>
    <rect width="1080" height="1920" fill="url(#v)"/>
    <rect width="1080" height="1920" filter="url(#n)" mask="url(#m)"/>
    <g class="flakes"></g></svg>`);
  document.body.appendChild(d);
  const flakes = d.querySelector(".flakes"), tint = d.querySelector(".tint");
  const pos = [[90, 160], [990, 140], [70, 1760], [1010, 1790], [60, 960], [1020, 1000]];
  const F = pos.map(([x, y], i) => { const f = document.createElementNS("http://www.w3.org/2000/svg", "g");
    f.innerHTML = [0, 60, 120].map((a) => `<g transform="rotate(${a})"><line x1="-60" y1="0" x2="60" y2="0" stroke="#fff" stroke-width="7" stroke-linecap="round"/>` +
      `<line x1="34" y1="0" x2="50" y2="-14" stroke="#fff" stroke-width="5"/><line x1="34" y1="0" x2="50" y2="14" stroke="#fff" stroke-width="5"/>` +
      `<line x1="-34" y1="0" x2="-50" y2="-14" stroke="#fff" stroke-width="5"/><line x1="-34" y1="0" x2="-50" y2="14" stroke="#fff" stroke-width="5"/></g>`).join("");
    f.dataset.x = x; f.dataset.y = y; flakes.appendChild(f); return f; });
  return (t) => {
    const k = Math.min(lerp(t, 0, .5, 0, 1), 1 - lerp(t, len - .35, len, 0, 1));
    d.style.opacity = k; tint.setAttribute("opacity", .12 * k);
    F.forEach((f, i) => { const sc = .2 + .8 * bouncy(t - .1 - i * .08);
      f.setAttribute("transform", `translate(${f.dataset.x},${f.dataset.y}) rotate(${t * 20 + i * 30}) scale(${sc})`); });
  };
}

// ---------------------------------------------------------------- the three steps, ticked off
function checklist(s, len, rel) {
  const panel = el(`<div style="position:absolute;left:90px;top:300px;width:900px;padding:34px 40px;border-radius:40px;background:rgba(17,19,24,.88);border:2px solid #2a2f38;box-shadow:0 20px 40px rgba(0,0,0,.5)"></div>`);
  const rows = s.rows.map((r, i) => { const row = el(`<div style="display:flex;align-items:center;gap:28px;margin:14px 0">
      <div style="flex:none;width:78px;height:78px;border-radius:20px;border:6px solid #7FB4F2;display:flex;align-items:center;justify-content:center">
        <svg width="60" height="60" viewBox="0 0 100 100"><path d="M14 54 L40 78 L88 22" fill="none" stroke="#2BD96B" stroke-width="16" stroke-linecap="round" stroke-linejoin="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/></svg></div>
      <div style="font-family:CapFont;font-size:62px;color:#fff;white-space:nowrap">${i + 1}. ${r}</div></div>`);
    panel.appendChild(row); return row; });
  document.body.appendChild(panel);
  return (t) => {
    const k = exitK(t, len), a = firm(t);
    panel.style.transform = `translateY(${(1 - a) * -80}px) scale(${1 - .3 * k})`; panel.style.opacity = Math.min(lerp(t, 0, .12, 0, 1), 1 - k);
    rows.forEach((row, i) => { const ct = t - rel(s.checks[i]);
      row.querySelector("path").style.strokeDashoffset = 1 - ease(ct / .2);
      row.lastElementChild.style.color = ct > .1 ? YEL : "#fff";
      row.style.transform = ct > 0 && ct < .25 ? `scale(${1 + .06 * Math.sin(ct / .25 * Math.PI)})` : "none"; });
  };
}

// ---------------------------------------------------------------- RM20,000 breaks into 12 months
function breakdown(s, len, rel) {
  const X0 = 90, W = 900, Y = 470, H = 130, n = 12, gap = 14, sw = (W - gap * (n - 1)) / n;
  const root = el(`<div style="position:absolute;left:0;top:0;width:1080px;height:1920px"></div>`);
  const segs = Array.from({ length: n }, (_, i) => { const sg = el(`<div style="position:absolute;top:${Y}px;height:${H}px;background:${GOLD};border:6px solid #000;box-sizing:border-box;box-shadow:0 8px 12px rgba(0,0,0,.5)"></div>`); root.appendChild(sg); return sg; });
  const big = el(`<div style="position:absolute;left:540px;top:${Y + H / 2}px;transform:translate(-50%,-50%);font-size:96px;color:#fff;white-space:nowrap;font-family:'Arial Black';text-shadow:0 2px 4px rgba(0,0,0,.7),0 0 16px rgba(0,0,0,.5),0 8px 28px rgba(0,0,0,.4)">RM20,000</div>`);
  const per = el(`<div style="position:absolute;left:540px;top:${Y - 95}px;transform:translate(-50%,-50%);font-size:84px;color:${YEL};white-space:nowrap;${TXT}">÷ 12 个月</div>`);
  const nums = Array.from({ length: n }, (_, i) => { const m = el(`<div style="position:absolute;top:${Y + H / 2}px;transform:translate(-50%,-50%);font-family:'Arial Black';font-size:38px;color:#3b2a00">${i + 1}</div>`); root.appendChild(m); return m; });
  root.appendChild(big); root.appendChild(per); document.body.appendChild(root);
  const c = rel(s.crack_at);
  return (t) => {
    const k = exitK(t, len), a = firm(t), sp = ease((t - c) / .35);
    root.style.opacity = Math.min(lerp(t, 0, .1, 0, 1), 1 - k);
    segs.forEach((sg, i) => {
      const whole = X0 + i * (W / n), split = X0 + i * (sw + gap);
      const x = whole + (split - whole) * sp, w = (W / n) + (sw - W / n) * sp;
      const drop = t > c ? Math.sin(i * 1.7) * 30 * Math.exp(-(t - c) * 4) * sp : 0;
      sg.style.left = (x - (1 - a) * 900) + "px"; sg.style.width = (w + .5) + "px";
      sg.style.transform = `translateY(${drop}px) rotate(${t > c ? (rnd(i) - .5) * 10 * sp * Math.exp(-(t - c) * 3) : 0}deg)`;
      sg.style.borderRadius = (sp * 14) + "px";
      nums[i].style.left = (split + sw / 2) + "px"; nums[i].style.opacity = sp;
    });
    big.style.opacity = 1 - sp; big.style.transform = `translate(-50%,-50%) scale(${1 + .4 * sp})`; big.style.filter = `blur(${sp * 8}px)`;
    per.style.opacity = lerp(t - c, .1, .25, 0, 1); per.style.transform = `translate(-50%,-50%) scale(${.4 + .6 * bouncy(t - c - .1)})`;
  };
}

// ---------------------------------------------------------------- comment CTA
function cta(s, len, rel) {
  const bub = el(`<div style="position:absolute;left:600px;top:960px;padding:22px 36px;border-radius:40px 40px 40px 8px;background:#fff;border:6px solid #000;box-shadow:0 10px 18px rgba(0,0,0,.45);font-family:CapFont;font-size:64px;color:#111;white-space:nowrap;transform-origin:0 100%"></div>`);
  const dots = el(`<span style="letter-spacing:10px">• • •</span>`); const word = el(`<span>留言「<b style="color:#E0A800"></b>」</span>`); word.querySelector("b").textContent = s.word || "关键词";
  bub.appendChild(dots); bub.appendChild(word);
  const arrow = el(`<svg width="160" height="200" viewBox="0 0 160 200" style="position:absolute;left:880px;top:1090px;overflow:visible;filter:drop-shadow(0 6px 6px rgba(0,0,0,.5))">
    <path d="M30 10 Q120 40 110 150" fill="none" stroke="#000" stroke-width="22" stroke-linecap="round"/><path d="M30 10 Q120 40 110 150" fill="none" stroke="${YEL}" stroke-width="12" stroke-linecap="round"/>
    <path d="M70 140 L112 190 L150 132 Z" fill="${YEL}" stroke="#000" stroke-width="7" stroke-linejoin="round"/></svg>`);
  const gift = el(`<svg width="230" height="230" viewBox="0 0 100 100" style="position:absolute;left:70px;top:900px;overflow:visible;filter:drop-shadow(0 8px 8px rgba(0,0,0,.5))">
    <rect x="12" y="44" width="76" height="50" fill="${RED}" stroke="#000" stroke-width="4"/><rect x="6" y="30" width="88" height="18" fill="${RED}" stroke="#000" stroke-width="4"/>
    <rect x="44" y="30" width="12" height="64" fill="${YEL}" stroke="#000" stroke-width="3"/><path d="M50 30 C30 4 14 26 50 30 C86 26 70 4 50 30" fill="${YEL}" stroke="#000" stroke-width="4"/>
    <text x="50" y="80" text-anchor="middle" font-size="16" font-family="Arial Black" fill="#fff">FREE</text></svg>`);
  [bub, arrow, gift].forEach((x) => document.body.appendChild(x));
  const g0 = rel(s.gift_at);
  return (t) => {
    const k = exitK(t, len), b = bouncy(t - .25);
    bub.style.opacity = t > .25 ? 1 - k : 0; bub.style.transform = `scale(${(.2 + .8 * b) * (1 - .3 * k)})`;
    const typed = t > .95; dots.style.display = typed ? "none" : "inline"; word.style.display = typed ? "inline" : "none";
    dots.style.opacity = .4 + .6 * Math.abs(Math.sin(t * 8));
    const ab = t - 1.1; arrow.style.opacity = ab > 0 ? 1 - k : 0;
    arrow.style.transform = `translate(${Math.sin(ab * 7) * 10}px,${ab > 0 ? Math.abs(Math.sin(ab * 5)) * 26 : 0}px) scale(${.3 + .7 * firm(ab)})`;
    const gt = t - g0; gift.style.opacity = gt > 0 ? 1 - k : 0;
    gift.style.transform = `scale(${.2 + .8 * bouncy(gt)}) rotate(${gt > 0 ? Math.sin(gt * 9) * 8 * Math.exp(-gt * 2) : 0}deg)`;
  };
}

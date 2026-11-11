"use strict";
/* The page body is rendered here from JSON data islands, using only createElement and textContent. */
const island = id => { const el = document.getElementById(id); return el ? JSON.parse(el.textContent) : null; };
const UI = island('ui-text');
const MAP = island('map-data');
const NOTES = island('notes-data');

function t(key, vars) {
  const one = vars && vars.n === 1 && UI[key + '_one'];
  const text = one || UI[key];
  return vars ? text.replace(/\{(\w+)\}/g, (_, name) => String(vars[name])) : text;
}

const hasTrans = MAP.blocks.some(b => b.translation);
const S = {view: NOTES ? 'notes' : 'reader', lang: hasTrans ? 'both' : 'orig', q: '', spk: new Set(), hits: [], cur: -1, names: {}};

/* ---------- Indexes ---------- */
const byId = new Map(MAP.blocks.map(b => [b.id, b]));
const secOf = new Map(); MAP.sections.forEach((s, i) => s.block_ids.forEach(id => secOf.set(id, i)));
const frameById = new Map(MAP.frames.map(f => [f.id, f]));
const framesByBlock = new Map();
MAP.frames.forEach(f => {
  if (!f.related_blocks.length) return;
  const k = f.related_blocks[0];
  if (!framesByBlock.has(k)) framesByBlock.set(k, []);
  framesByBlock.get(k).push(f);
});
const citedBy = new Map();
if (NOTES) NOTES.units.forEach((u, ui) => u.paragraphs.forEach((p, pi) => (p.cites || []).forEach(c => {
  if (!citedBy.has(c)) citedBy.set(c, []);
  citedBy.get(c).push({ui, pi});
})));
const anonNo = {}; {let n = 0; MAP.speakers.forEach(s => { if (!s.name) anonNo[s.id] = ++n; });}
let anonMax = Object.keys(anonNo).length;
const anonLabel = id => `${t('anon')} ${anonNo[id] ??= ++anonMax}`;
const spkIdx = id => id == null ? 'none' : (MAP.speakers.findIndex(s => s.id === id) % 8);
const spkColor = id => `var(--s${spkIdx(id)})`;
const fileName = id => MAP.speakers.find(x => x.id === id).name || '';
const fileLabel = id => fileName(id) || anonLabel(id);
/* A rename draft is only a preview; clearing a name previews the anonymous label. */
const spkName = id => { if (id == null) return t('unknown'); return (S.names[id] ?? fileName(id)).trim() || anonLabel(id); };
const uncertain = b => b.speaker != null && (b.speaker_confidence === 'low' || b.speaker_confidence === 'unknown');

/* ---------- Tools ---------- */
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const k in attrs || {}) {
    const v = attrs[k];
    if (v == null || v === false) continue;
    if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'class') e.className = v;
    else if (k === 'text') e.textContent = v;
    else if (k === 'style') e.style.cssText = v;
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat()) { if (c == null || c === false) continue; e.append(c); }
  return e;
}
const toMs = stamp => {
  const [time, fraction = '0'] = stamp.replace(',', '.').split('.');
  const [hh, mm, ss] = time.split(':').map(Number);
  return ((hh * 60 + mm) * 60 + ss) * 1000 + Number(fraction);
};
const clock = stamp => stamp.replace(/[.,].*$/, '');
const longMedia = MAP.media.duration_seconds >= 3600;
const fmtT = stamp => longMedia ? clock(stamp) : clock(stamp).slice(3);
const fmtR = (a, b) => `${a ? fmtT(a) : '?'}–${b ? fmtT(b) : '?'}`;

/* ---------- Speaker labels ---------- */
function whoNodes(id, low) {
  return [h('span', {class: 'spk-name', 'data-sid': id, 'data-q': !!low, text: spkName(id) + (low ? '?' : '')})];
}

/* ---------- Frames ---------- */
const frameSrc = f => f.image_path.split('/').map(encodeURIComponent).join('/');
const frameEls = new Map();
function frameEl(f, scope) {
  const b = h('button', {class: 'frame', type: 'button', onclick: () => openLightbox(f)});
  const img = h('img', {src: frameSrc(f), alt: `${f.id} ${fmtT(f.timestamp)}`, loading: 'lazy', onerror: () => b.classList.add('broken')});
  b.append(img, h('span', {class: 'miss', text: `${t('missing')} · ${f.id}`}));
  if (scope === 'reader') frameEls.set(f.id, b);
  return b;
}
function openLightbox(f) {
  const d = document.getElementById('lb');
  d.replaceChildren(h('img', {src: frameSrc(f), alt: f.id}), h('div', {class: 'cap', text: `${fmtT(f.timestamp)} · ${f.id}`}));
  d.showModal();
  d.onclick = () => d.close();
}

/* ---------- Reader ---------- */
const blockEls = new Map(); const paraEls = new Map();
function backrefs(id) {
  const refs = citedBy.get(id);
  if (!refs) return null;
  /* One entry per unit, even when several of its paragraphs cite this block. */
  const seen = new Map(); refs.forEach(r => { if (!seen.has(r.ui)) seen.set(r.ui, r); });
  const list = [...seen.values()];
  if (list.length === 1) {
    const heading = NOTES.units[list[0].ui].heading;
    return h('button', {class: 'backref badge', title: heading, 'aria-label': heading, onclick: e => jumpToPara(list[0], e.currentTarget), text: '↩'});
  }
  return h('details', {class: 'pop', style: 'display:inline-block'},
    h('summary', {style: 'border:0;background:none;padding:0 4px;font-size:13px;color:var(--faint)', text: `↩ ${list.length}`}),
    h('div', {class: 'pop-body'}, h('ul', null, list.map(r => h('li', null, h('a', {onclick: e => jumpToPara(r, e.currentTarget), text: NOTES.units[r.ui].heading}))))));
}
/* A timed limitation shows under the first block that starts inside its range; whole-source ones are not shown. */
function limitNotesFor(b) {
  return MAP.limitations
    .filter(l => l.kind !== 'coverage' && l.start && l.end
      && MAP.blocks.find(x => toMs(x.start) >= toMs(l.start) && toMs(x.start) < toMs(l.end)) === b)
    .map(l => h('div', {class: 'lim-note', text: l.detail}));
}
function renderBlock(b) {
  const tx = h('div', {class: 'tx-wrap'},
    h('p', {class: 'tx orig' + (b.translation ? '' : ' only'), text: b.original_text}),
    b.translation ? h('p', {class: 'tx trans', text: b.translation}) : null);
  const timeEl = h('span', {class: 't', title: `${fmtR(b.start, b.end)} · ${b.id}`, text: fmtT(b.start)});
  const meta = h('div', {class: 'meta'}, b.confidence === 'low' ? h('span', {class: 'tag warn', text: t('lowtxt')}) : null);
  const frames = framesByBlock.get(b.id) || [];
  const body = h('div', {class: 'b-body'}, h('div', {class: 't-row'}, timeEl, backrefs(b.id)), tx, meta, limitNotesFor(b));
  const el = h('div', {class: 'block', 'data-bid': b.id}, body,
    frames.length ? h('div', {class: 'frames'}, frames.map(f => frameEl(f, 'reader'))) : null);
  blockEls.set(b.id, el);
  return el;
}
function groupTurns(blocks) {
  const out = []; let cur = null;
  blocks.forEach(b => {
    const same = cur && b.speaker != null && cur.speaker === b.speaker
      && uncertain(cur.blocks[0]) === uncertain(b);
    if (same) cur.blocks.push(b);
    else out.push(cur = {speaker: b.speaker, blocks: [b]});
  });
  return out;
}
function renderTurn(turn) {
  const first = turn.blocks[0];
  return h('div', {class: 'turn' + (turn.speaker == null ? ' unknown' : ''), 'data-spk': turn.speaker ?? 'none', style: `--c:${spkColor(turn.speaker)}`},
    h('div', {class: 'turn-head'}, whoNodes(turn.speaker, uncertain(first))),
    turn.blocks.map(renderBlock));
}
/* Recording gaps and frames without related blocks sit on the timeline, ahead of the first block at or after them. */
function timelineItems() {
  const gaps = MAP.limitations.filter(l => l.kind === 'coverage' && l.start)
    .map(l => ({at: toMs(l.start), make: () => h('div', {class: 'gap', text: t('gapLine', {range: fmtR(l.start, l.end), detail: l.detail})})}));
  const frames = MAP.frames.filter(f => !f.related_blocks.length)
    .map(f => ({at: toMs(f.timestamp), make: () => h('div', {class: 'frames'}, frameEl(f, 'reader'))}));
  return [...gaps, ...frames].sort((a, b) => a.at - b.at);
}
function renderReader() {
  const col = h('div', {class: 'col'});
  const items = timelineItems(); let next = 0;
  const due = at => { const out = []; while (next < items.length && items[next].at <= at) out.push(items[next++].make()); return out; };
  MAP.sections.forEach((s, si) => {
    const blocks = s.block_ids.map(id => byId.get(id));
    if (blocks.length) col.append(...due(toMs(blocks[0].start)));
    col.append(h('h2', {class: 'sec-title', 'data-sec': si},
      h('span', {class: 'tx orig' + (s.title_translation ? '' : ' only'), text: s.title_original}),
      s.title_translation ? h('span', {class: 'tx trans second', text: s.title_translation}) : null,
      h('span', {class: 'sec-time', text: fmtR(s.start, s.end)})));
    let run = [];
    const flush = () => { groupTurns(run).forEach(turn => col.append(renderTurn(turn))); run = []; };
    blocks.forEach(b => {
      const here = due(toMs(b.start));
      if (here.length) { flush(); col.append(...here); }
      run.push(b);
    });
    flush();
  });
  col.append(...due(Infinity));
  if (!MAP.blocks.length) col.append(h('p', {class: 'lim-note', text: t('noSpeech')}));
  return col;
}

/* ---------- Notes ---------- */
function citeRanges(cites) {
  const blocks = cites.map(c => byId.get(c)).sort((a, b) => a.order - b.order), out = [];
  blocks.forEach(b => {
    const last = out[out.length - 1];
    if (last && b.order === last[last.length - 1].order + 1 && secOf.get(b.id) === secOf.get(last[0].id)) last.push(b);
    else out.push([b]);
  });
  return out;
}
function chipFor(range) {
  const a = range[0], b = range[range.length - 1], time = fmtR(a.start, b.end), ids = range.length > 1 ? `${a.id}–${b.id}` : a.id;
  return h('button', {class: 'chip', title: `${time} · ${ids}`, onclick: e => jumpToBlocks(range.map(x => x.id), e.currentTarget), text: time});
}
function paraLow(p, id) {
  const blocks = (p.cites || []).map(c => byId.get(c)).filter(b => b.speaker === id);
  return blocks.length > 0 && blocks.every(uncertain);
}
function renderPara(p, ui, pi) {
  const speakers = p.speakers || [], cites = p.cites || [];
  const el = h('div', {class: 'para', 'data-spk': speakers.join(' ')});
  if (speakers.length) el.append(h('div', {class: 'para-spk'}, speakers.map(id => h('span', {class: 'who', style: `--c:${spkColor(id)}`}, whoNodes(id, paraLow(p, id))))));
  const line = h('p', {style: 'margin:0'}, h('span', {class: 'tx', text: p.text}));
  citeRanges(cites).forEach(r => line.append(chipFor(r)));
  el.append(line);
  (p.frames || []).forEach(fid => el.append(frameEl(frameById.get(fid), 'notes')));
  paraEls.set(`${ui}.${pi}`, el);
  return el;
}
/* The orientation cites nothing, so beside the Transcript it has no partner; the wide layout shows it across both panes. */
let orientEls = [];
const hasOrient = () => NOTES.units.length > 1 && NOTES.units[0].paragraphs.every(p => !(p.cites || []).length && !(p.frames || []).length);
function renderNotes() {
  const col = h('div', {class: 'col'});
  orientEls = [];
  const unit = (ui, tag) => {
    const els = [h(tag, {'data-unit': ui}, h('span', {class: 'tx', text: NOTES.units[ui].heading})),
      ...NOTES.units[ui].paragraphs.map((p, pi) => renderPara(p, ui, pi))];
    if (ui === 0 && hasOrient()) orientEls = els;
    col.append(...els);
  };
  noteGroups().groups.forEach(g => {
    if (g.sec == null) { g.units.forEach(ui => unit(ui, 'h2')); return; }
    const s = MAP.sections[g.sec];
    col.append(h('h2', {class: 'nsec-title', 'data-nsec': g.sec}, h('span', {class: 'tx', text: secName(s)}), h('span', {class: 'sec-time', text: fmtR(s.start, s.end)})));
    g.units.forEach(ui => unit(ui, 'h3'));
  });
  return col;
}

/* ---------- Jumps ---------- */
const isSplit = () => !!NOTES && matchMedia('(min-width:1100px)').matches;
let hlEls = [];
function mark(els) {
  hlEls.forEach(e => e.classList.remove('hl', 'flash'));
  hlEls = els;
  els.forEach(e => { e.classList.add('hl'); void e.offsetWidth; e.classList.add('flash'); });
}
function pushNav(hash, toView) {
  try {
    history.replaceState({...(history.state || {}), view: S.view, y: scrollY}, '');
    const depth = (history.state?.depth || 0) + 1;
    history.pushState({depth, view: toView, from: S.view}, '', hash);
  } catch (e) { console.warn('history', e); }
}
function showBack() {
  const b = document.getElementById('back'); const st = history.state || {};
  b.hidden = !(st.depth > 0 && st.from && st.from !== S.view && !isSplit());
  if (!b.hidden) b.textContent = t('backTo', {view: st.from === 'notes' ? t('notes') : t('reader')});
}
function setView(v) { S.view = v; lastSwitch = null; applyPanes(); }
/* On a narrow screen the tabs show one pane at a time. Switching shows the counterpart of what sits at the top, at the same height:
   a note paragraph's first cited block or frame, a block's note paragraph, a section heading's twin. Above the first match, the top. */
const viewTop = () => document.querySelector('.hdr').getBoundingClientRect().bottom;
const secOfBlock = new Map(MAP.sections.flatMap((s, si) => s.block_ids.map(id => [id, si])));
/* Called once the destination pane shows, so it can skip what the speaker filter hides. */
function counterpart(el) {
  if (el.dataset.nsec != null) return document.querySelector(`.pane-reader [data-sec="${el.dataset.nsec}"]`);
  if (el.dataset.sec != null) return document.querySelector(`.pane-notes [data-nsec="${el.dataset.sec}"]`);
  if (el.classList.contains('para')) {
    const key = [...paraEls].find(([, v]) => v === el)?.[0]; if (!key) return null;
    const [ui, pi] = key.split('.').map(Number), p = NOTES.units[ui].paragraphs[pi];
    const blocks = (p.cites || []).map(c => byId.get(c)).sort((a, b) => a.order - b.order).map(b => blockEls.get(b.id));
    return [...blocks, ...(p.frames || []).map(f => frameEls.get(f))].find(vis) || null;
  }
  /* A block goes to the first paragraph whose cites span it, else to the one citing the nearest earlier block, else to its section. */
  const o = byId.get(el.dataset.bid).order, span = [], near = [];
  NOTES.units.forEach((u, ui) => u.paragraphs.forEach((p, pi) => {
    const os = (p.cites || []).map(c => byId.get(c).order), pe = paraEls.get(`${ui}.${pi}`), before = os.filter(x => x <= o);
    if (!before.length) return;
    if (Math.max(...os) >= o) span.push(pe);
    near.push({pe, at: Math.max(...before)});
  }));
  near.sort((a, b) => b.at - a.at);
  return [...span, ...near.map(n => n.pe), document.querySelector(`.pane-notes [data-nsec="${secOfBlock.get(el.dataset.bid)}"]`)].find(vis) || null;
}
/* A note covers several blocks, so switching straight back without scrolling returns to the exact place left. */
let lastSwitch = null;
function switchView(v, rerender) {
  if (v === S.view) return;
  const left = {from: S.view, y: scrollY}, back = lastSwitch && lastSwitch.from === v && Math.abs(scrollY - lastSwitch.landed) < 2;
  const land = () => { lastSwitch = {...left, landed: scrollY}; };
  if (back) { const y = lastSwitch.y; setView(v); rerender(); scrollTo(0, y); land(); return; }
  const from = document.querySelector(S.view === 'notes' ? '.pane-notes' : '.pane-reader'), top = viewTop();
  const shown = x => { const r = x.getBoundingClientRect(); return r.height > 0 && r.bottom > top; };
  /* A skipped off-screen turn reports stale positions for its blocks, so check the turn first. */
  const items = [...from.querySelectorAll('[data-nsec], .para, [data-sec], .block')].filter(x => !x.closest('.band'));
  const i = scrollY > 2 ? items.findIndex(x => (!x.closest('.turn') || shown(x.closest('.turn'))) && shown(x)) : -1;
  const rel = i >= 0 ? Math.max(0, headOf(items[i]).getBoundingClientRect().top - top) : 0;
  setView(v); rerender();
  let target = null; for (let k = i; k >= 0 && !target; k--) { target = counterpart(items[k]); if (target && !vis(target)) target = null; }
  if (!target) { scrollTo(0, 0); land(); return; }
  const fix = () => scrollBy(0, headOf(target).getBoundingClientRect().top - (viewTop() + rel));
  /* Off-screen turns keep placeholder heights until laid out, so correct again once they are. */
  target.scrollIntoView({block: 'start'}); fix(); land();
  requestAnimationFrame(() => { fix(); requestAnimationFrame(() => { fix(); land(); }); });
}
/* A target hidden by the speaker filter would stay unreachable, so following a link to one clears the filter.
   Search results belong to the visible pane, so changing pane or filter recomputes them. */
function jumpTo(els, hash, view, src) {
  const filtered = els.some(el => el.closest('.turn,.para').hidden);
  if (filtered) S.spk.clear();
  const switching = !isSplit();
  if (switching) { pushNav(hash, view); setView(view); }
  if (filtered || switching) { rerenderChrome(); runFilters(); }
  mark(els);
  if (switching) els[0].scrollIntoView({block: 'center'});
  else jumpBeside(els[0], src);
  showBack();
}
const jumpToBlocks = (ids, src) => jumpTo(ids.map(i => blockEls.get(i)), '#' + ids[0], 'reader', src);
const jumpToPara = ({ui, pi}, src) => jumpTo([paraEls.get(`${ui}.${pi}`)], `#n-${ui}-${pi}`, 'notes', src);
window.addEventListener('popstate', e => {
  const st = e.state || {};
  S.view = st.view || S.view;
  applyPanes(); rerenderChrome(); runFilters();
  if (st.y != null) scrollTo(0, st.y);
  showBack();
  hlEls.forEach(x => x.classList.remove('hl')); hlEls = [];
});

/* ---------- Synchronized scrolling ---------- */
/* The reading line sits at 40% of the pane. A paragraph start that crosses it becomes current, and both panes align on it.
   The line moves to the pane's top at the top of the page and to its bottom near the end, so the first and last paragraphs get a turn.
   An anchor pairs a Notes paragraph with the first block it cites, or its first frame when it has no cites.
   A longest increasing subsequence drops out-of-order paragraphs, such as a closing unit that cites earlier blocks. */
let syncAnch = null, ease = null, master = null, syncTick = false, syncHold = false;
const LINE = .4;
function lineGeom(pane) { const H = pane.clientHeight, max = pane.scrollHeight - H, k = max > 0 ? Math.min(1, max / H) : 1, y = H * LINE; return {H, max, k, y, a: y * k, b: (H - y) * k}; }
function lineAt(pane, s) { const g = lineGeom(pane), rest = g.max - s; return s + (s < g.a ? s / g.k : rest < g.b ? g.H - rest / g.k : g.y); }
function scrollForLine(pane, d) {
  const g = lineGeom(pane), rate = 1 + 1 / g.k, bot = g.max - g.b + g.y;
  if (d <= g.a * rate) return d / rate;
  return d >= bot ? g.max - g.b + (d - bot) / rate : d - g.y;
}
const vis = el => el && el.getClientRects().length > 0;
const yIn = (pane, el) => el.getBoundingClientRect().top - pane.getBoundingClientRect().top + pane.scrollTop;
/* Align on the start of the content: a paragraph with its unit heading, a block with its speaker line.
   Section headings pair with each other, so each Notes section heading sits level with the same Transcript section. */
function headOf(el) {
  if (el.classList.contains('block')) {
    const turn = el.closest('.turn');
    return turn.querySelector('.block') === el ? turn : el;
  }
  const p = el.previousElementSibling;
  return p && p.matches('h2,h3') ? p : el;
}
function buildAnchors() {
  const L = document.querySelector('.pane-notes'), R = document.querySelector('.pane-reader');
  let raw = [];
  NOTES.units.forEach((u, ui) => u.paragraphs.forEach((p, pi) => {
    const cites = p.cites || [], frames = p.frames || [];
    const targets = cites.length
      ? cites.map(c => byId.get(c)).sort((a, b) => a.order - b.order).map(b => blockEls.get(b.id))
      : frames.map(f => frameEls.get(f)).filter(Boolean);
    if (!targets.length) return;
    const pe = paraEls.get(`${ui}.${pi}`); if (!vis(pe)) return;
    const first = targets.find(vis); if (!first) return;
    raw.push({l: yIn(L, headOf(pe)), r: yIn(R, headOf(first)), pe, blocks: targets});
  }));
  /* Section headings always pair; a paragraph that would sit on the wrong side of one, such as an orientation citing
     the first section, gives up its anchor. */
  const secs = [...L.querySelectorAll('[data-nsec]')].map(el => [el, R.querySelector(`[data-sec="${el.dataset.nsec}"]`)])
    .filter(([el, sec]) => vis(el) && vis(sec)).map(([el, sec]) => ({l: yIn(L, el), r: yIn(R, sec)}));
  raw = [...raw.filter(p => secs.every(s => (p.l < s.l) === (p.r < s.r))), ...secs].sort((a, b) => a.l - b.l);
  const n = raw.length, len = Array(n).fill(1), prev = Array(n).fill(-1); let best = -1;
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < i; j++) if (raw[j].r < raw[i].r && raw[j].l < raw[i].l && len[j] + 1 > len[i]) { len[i] = len[j] + 1; prev[i] = j; }
    if (best < 0 || len[i] >= len[best]) best = i;
  }
  const chain = []; for (let i = best; i >= 0; i = prev[i]) chain.unshift(raw[i]);
  const pts = [{l: -1, r: -1}];
  chain.forEach(a => { const last = pts[pts.length - 1]; if (a.l > last.l && a.r > last.r) pts.push(a); });
  pts.push({l: Math.max(L.scrollHeight, pts[pts.length - 1].l + 1), r: Math.max(R.scrollHeight, pts[pts.length - 1].r + 1)});
  return {L, R, pts};
}
/* The current paragraph is the last one at or above the reading line; a section heading keeps the one before it current. */
function curAt(pts, i) { for (let k = i; k > 0; k--) if (pts[k].pe) return pts[k]; return pts.find(p => p.pe) || {}; }
function segOf(pts, key, x) { let lo = 0, hi = pts.length - 2; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (pts[m][key] <= x + 1) lo = m; else hi = m - 1; } return lo; }
/* Map a reading-line position in one pane to the other pane's, returning the segment it falls in. */
function mapLine(pane, d) {
  const {L, pts} = syncAnch, a = pane === L ? 'l' : 'r', b = pane === L ? 'r' : 'l', i = segOf(pts, a, d), p = pts[i], q = pts[i + 1];
  const frac = q[a] > p[a] ? (d - p[a]) / (q[a] - p[a]) : 0;
  return {i, at: p[b] + Math.max(0, Math.min(1, frac)) * (q[b] - p[b])};
}
/* After a link jump the other pane sits off the mapping by an offset that fades as the driving pane scrolls: over one pane height,
   or less so that it finishes at a nearer end, but never faster than 8px of offset per pixel scrolled, so a distant target takes longer.
   When the other pane takes over or the layout changes, the offset is measured again from where both panes are. */
const startEase = (pane, other, d) => ({pane, anch: syncAnch, d0: d, off: lineAt(other, other.scrollTop) - mapLine(pane, d).at});
function syncFrom(pane) {
  if (!isSplit()) return;
  if (!syncAnch) syncAnch = buildAnchors();
  const {L, R, pts} = syncAnch, other = pane === L ? R : L, d = lineAt(pane, pane.scrollTop), m = mapLine(pane, d);
  if (ease && (ease.pane !== pane || ease.anch !== syncAnch)) ease = startEase(pane, other, d);
  const room = ease && (d < ease.d0 ? ease.d0 : pane.scrollHeight - ease.d0);
  const span = ease && Math.max(Math.min(pane.clientHeight, room), Math.abs(ease.off) / 8);
  const w = ease && span > 0 ? Math.max(0, 1 - Math.abs(d - ease.d0) / span) : 0;
  if (!w) ease = null;
  other.scrollTop = scrollForLine(other, m.at + (ease ? ease.off * w : 0));
  markLinked(curAt(pts, m.i));
}
/* Opening, switching language, and filtering need a current paragraph without any scrolling. */
function refreshLinked() {
  if (!isSplit()) return;
  if (!syncAnch) syncAnch = buildAnchors();
  const {L, R, pts} = syncAnch, pane = master || L, a = pane === R ? 'r' : 'l';
  markLinked(curAt(pts, segOf(pts, a, lineAt(pane, pane.scrollTop))));
}
/* A contents jump puts the heading on the reading line, makes it current, and aligns the other pane. */
function jumpToHeading(pane, el) {
  if (!isSplit()) { el.scrollIntoView({block: 'start'}); return; }
  if (el.closest('.band')) { ease = null; document.querySelectorAll('.pane').forEach(p => { p.scrollTop = 0; }); scrollTo(0, 0); bandState(); return; }
  bandAway();
  ease = null; syncAnch = null;
  master = pane; pane.scrollTop = scrollForLine(pane, yIn(pane, el.querySelector('h2') || el)); syncFrom(pane);
}
/* A link scrolls only the other pane, putting the target beside the clicked paragraph or block, or higher if the target would end below view.
   The next scroll in either pane then eases back to the usual alignment instead of snapping. */
function jumpBeside(el, src) {
  bandAway();
  const pane = el.closest('.pane'), from = src.closest('.pane'), srcEl = src.closest('.block,.para');
  const top = Math.max(srcEl.getBoundingClientRect().top, from.getBoundingClientRect().top);
  pane.scrollTop += headOf(el).getBoundingClientRect().top - top;
  const box = el.getBoundingClientRect(), view = pane.getBoundingClientRect();
  if (box.bottom > view.bottom) pane.scrollTop += Math.min(box.bottom - view.bottom, box.top - view.top);
  syncAnch = buildAnchors(); master = from; ease = startEase(from, pane, lineAt(from, from.scrollTop));
  refreshLinked();
}
let linked = [];
function markLinked(p) { linked.forEach(e => e.classList.remove('linked')); linked = p.pe ? [p.pe, ...p.blocks] : []; linked.forEach(e => e.classList.add('linked')); }
function initSync() {
  syncAnch = null; ease = null; master = null; linked = [];
  const L = document.querySelector('.pane-notes'), R = document.querySelector('.pane-reader'); if (!L) return;
  [L, R].forEach(pane => {
    ['wheel', 'touchstart', 'pointerdown', 'keydown', 'mouseenter'].forEach(ev => pane.addEventListener(ev, () => { master = pane; }, {passive: true}));
    pane.addEventListener('scroll', () => { if (master !== pane || syncTick || syncHold) return; syncTick = true; requestAnimationFrame(() => { syncTick = false; syncFrom(pane); }); }, {passive: true});
  });
  /* Anything that changes layout (language, filter, images, window width) invalidates the anchors. */
  const ro = new ResizeObserver(() => { syncAnch = null; });
  ro.observe(L.firstElementChild); ro.observe(R.firstElementChild);
}

/* ---------- Header ---------- */
/* Each language is named in itself (English, 简体中文); Chinese by script, not region (中文（中国）). */
function langName(tag) {
  try {
    const loc = new Intl.Locale(tag).maximize();
    const name = loc.language === 'zh' ? `zh-${loc.script}` : tag;
    return new Intl.DisplayNames([name], {type: 'language'}).of(name) || tag;
  } catch (e) { return tag; }
}
function fmtDur(s) { const whole = Math.floor(s), m = Math.floor(whole / 60); return whole >= 3600 ? `${Math.floor(whole / 3600)}h ${String(m % 60).padStart(2, '0')}m` : `${m}m ${String(whole % 60).padStart(2, '0')}s`; }
function infoPop() {
  const m = MAP.media;
  const langs = `${m.spoken_languages.map(langName).join(t('listSep'))} → ${langName(m.target_language)}`;
  return h('details', {class: 'pop', id: 'info'},
    h('summary', {title: t('info')}, fmtDur(m.duration_seconds), h('span', {class: 'info-langs', text: ` · ${langs}`}), h('span', {class: 'ic ic-chev'})),
    h('div', {class: 'pop-body'},
      h('h3', {text: t('src')}),
      h('dl', {class: 'kv', style: 'margin:0'},
        h('dt', {text: t('src')}), h('dd', {text: m.origin}),
        h('dt', {text: t('dur')}), h('dd', {text: fmtDur(m.duration_seconds)}),
        h('dt', {text: t('langs')}), h('dd', {text: langs}),
        h('dt', {text: t('type')}), h('dd', {text: m.reading_type}),
        h('dt', {text: t('prov')}), h('dd', {text: m.transcript_provenance}),
        h('dt', {text: t('spks')}), h('dd', {id: 'info-spks', text: MAP.speakers.map(s => spkName(s.id)).join(t('listSep'))}))));
}
/* Renaming happens in the speaker chip and previews across the page; an agent writes the file from one merged prompt. */
function bundleDir() {
  if (location.protocol !== 'file:') return t('promptHere');
  return decodeURIComponent(location.pathname).replace(/\/[^/]*$/, '').replace(/^\/([A-Za-z]:)/, '$1');
}
function nameChanges() {
  return MAP.speakers.map(s => ({id: s.id, old: s.name || '', now: (S.names[s.id] ?? (s.name || '')).trim(), label: fileLabel(s.id)})).filter(c => c.now !== c.old);
}
/* Bundle text is untrusted, so the prompt carries no old labels and quotes every value as a JSON string:
   a name or path with line breaks cannot start a new line of instructions. */
function buildPrompt() {
  const ch = nameChanges(); if (!ch.length) return '';
  const value = c => c.now ? JSON.stringify(c.now) : `null ${t('promptClear')}`;
  return [t('promptHead'), '', `${t('promptDir')}: ${JSON.stringify(bundleDir())}`, '', `${t('promptChange')}:`,
    ...ch.map(c => `- ${c.id} -> ${value(c)}`), '', ...UI.promptRules.map(r => `- ${r}`)].join('\n');
}
function refreshNames() {
  document.querySelectorAll('.spk-name[data-sid]').forEach(e => { e.textContent = spkName(e.dataset.sid) + (e.hasAttribute('data-q') ? '?' : ''); });
  const ch = nameChanges(), changed = new Set(ch.map(c => c.id));
  document.querySelectorAll('.spk-chip[data-sid]').forEach(c => {
    const id = c.dataset.sid;
    c.querySelector('.spk-label').textContent = spkName(id);
    c.classList.toggle('changed', changed.has(id));
    c.querySelector('.spk-sel').title = changed.has(id) ? t('origName', {name: fileLabel(id)}) : '';
  });
  const dd = document.getElementById('info-spks'); if (dd) dd.textContent = MAP.speakers.map(s => spkName(s.id)).join(t('listSep'));
  document.getElementById('rn-pending').hidden = !ch.length;
  document.getElementById('rn-copy').textContent = t('copy', {n: ch.length});
  document.getElementById('rn-out').value = buildPrompt();
  if (!ch.length) document.getElementById('rn-more').open = false;
  syncAnch = null;
}
async function copyPrompt() {
  const out = document.getElementById('rn-out'), btn = document.getElementById('rn-copy'); let ok = false;
  try { await navigator.clipboard.writeText(out.value); ok = true; }
  catch (e) { document.getElementById('rn-more').open = true; out.select(); ok = document.execCommand('copy'); }
  if (ok) { btn.textContent = t('copied'); clearTimeout(S.copyTm); S.copyTm = setTimeout(() => { btn.textContent = t('copy', {n: nameChanges().length}); }, 2000); }
}
function renamePending() {
  const n = nameChanges().length;
  return h('div', {class: 'rn-pending', id: 'rn-pending', hidden: !n},
    h('button', {id: 'rn-copy', type: 'button', onclick: copyPrompt, text: t('copy', {n})}),
    h('details', {class: 'pop', id: 'rn-more'},
      h('summary', {title: t('previewPrompt'), 'aria-label': t('previewPrompt')}, h('span', {class: 'ic ic-chev'})),
      h('div', {class: 'pop-body'},
        h('p', {class: 'hint', style: 'margin:0 0 8px', text: t('previewHint')}),
        h('textarea', {id: 'rn-out', readonly: true, rows: 11}, buildPrompt()),
        h('button', {id: 'rn-discard', type: 'button', onclick: () => { S.names = {}; refreshNames(); }, text: t('discard')}))));
}
function spkChip(id) {
  const sel = h('button', {class: 'spk-sel', type: 'button', 'aria-pressed': String(S.spk.has(id)),
    onclick: () => { S.spk.has(id) ? S.spk.delete(id) : S.spk.add(id); const on = S.spk.has(id); sel.setAttribute('aria-pressed', String(on)); chip.classList.toggle('on', on); runFilters(); }},
    h('span', {class: 'spk-label', text: spkName(id)}));
  const chip = h('span', {class: 'spk-chip' + (S.spk.has(id) ? ' on' : ''), style: `--c:${spkColor(id)}`, 'data-sid': id}, sel);
  if (id == null) return chip;
  const ic = h('span', {class: 'ic ic-pencil'});
  const edit = h('button', {class: 'spk-edit', type: 'button', title: t('rename'), 'aria-label': `${t('rename')}: ${spkName(id)}`,
    onmousedown: e => e.preventDefault(), /* Keep input focus: the pencil itself decides between starting and finishing. */
    onclick: () => { chip.finish ? chip.finish(true) : start(); }}, ic);
  function start() {
    const inp = h('input', {class: 'spk-input', type: 'text', maxlength: 60, value: S.names[id] ?? fileName(id), placeholder: fileName(id) ? anonLabel(id) : fileLabel(id), 'aria-label': `${t('rename')}: ${spkName(id)}`});
    const box = h('span', {class: 'spk-box'}, inp);
    let done = false;
    chip.finish = save => {
      if (done) return;
      done = true; chip.finish = null;
      if (save) S.names[id] = inp.value;
      box.remove(); sel.hidden = false; chip.classList.remove('editing');
      ic.className = 'ic ic-pencil'; edit.title = t('rename');
      refreshNames();
    };
    inp.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === 'Escape') { e.preventDefault(); chip.finish(e.key === 'Enter'); edit.focus(); } });
    inp.addEventListener('blur', () => chip.finish && chip.finish(true));
    sel.hidden = true; sel.before(box); chip.classList.add('editing');
    ic.className = 'ic ic-check'; edit.title = t('renameDone');
    inp.focus(); inp.select();
  }
  chip.append(edit);
  return chip;
}
/* Each unit's place is its earliest cited block (or, with no cites, its earliest frame) at or after the previous unit's time,
   in a section at or after the previous unit's section, so times only move forward and a unit that cites only earlier
   material shows no time. A frame no section range contains does not place a unit when the source has sections, so a
   time never sits under a section that does not contain it. */
const secAt = (ms, from) => { const i = MAP.sections.findIndex((s, si) => si >= from && toMs(s.start) <= ms && ms <= toMs(s.end)); return i < 0 ? null : i; };
function unitPlaces() {
  let at = -1, sec = 0;
  return NOTES.units.map(u => {
    const cites = u.paragraphs.flatMap(p => p.cites || []).map(c => byId.get(c)).filter(Boolean);
    const marks = cites.length
      ? cites.map(b => ({start: b.start, sec: secOf.get(b.id)}))
      : u.paragraphs.flatMap(p => p.frames || []).map(id => frameById.get(id)).filter(Boolean).map(f => ({start: f.timestamp, sec: secAt(toMs(f.timestamp), sec)}));
    const next = marks.filter(m => toMs(m.start) >= at && (MAP.sections.length ? m.sec != null && m.sec >= sec : true)).sort((x, y) => toMs(x.start) - toMs(y.start))[0];
    if (!next) return {start: null, sec};
    at = toMs(next.start); sec = next.sec ?? sec;
    return {start: next.start, sec};
  });
}
/* The Notes and their Contents share one outline. With sections, the orientation opens on its own, every section follows
   with the units placed in it, and the closing run of units that cite only earlier material or cite sections more than one
   apart, such as next steps and the source boundary, stands on its own after the last section. Without sections each
   unit stands on its own. */
const secName = s => s.title_translation || s.title_original;
function noteGroups() {
  const places = unitPlaces(), n = NOTES.units.length;
  if (!MAP.sections.length) return {places, groups: NOTES.units.map((_, ui) => ({sec: null, units: [ui]}))};
  const spread = ui => { const secs = NOTES.units[ui].paragraphs.flatMap(p => p.cites || []).map(c => secOf.get(c)).filter(x => x != null); return secs.length ? Math.max(...secs) - Math.min(...secs) : 0; };
  let end = n;
  while (end > 1 && (!places[end - 1].start || spread(end - 1) > 1)) end--;
  const groups = [{sec: null, units: [0]}, ...MAP.sections.map((_, si) => ({sec: si, units: []}))];
  for (let ui = 1; ui < end; ui++) groups[places[ui].sec + 1].units.push(ui);
  for (let ui = end; ui < n; ui++) groups.push({sec: null, units: [ui]});
  return {places, groups};
}
/* Beside or in place of the Notes, the Contents mirror the Notes outline; on the Transcript alone they list its sections. */
function tocPop() {
  let det;
  const link = (go, ...kids) => h('a', {onclick: () => { go(); det.open = false; }}, ...kids);
  const go = (view, sel) => () => { setView(view); jumpToHeading(document.querySelector(`.pane-${view}`), document.querySelector(sel)); };
  const secLink = (si, view) => { const s = MAP.sections[si];
    return link(go(view, view === 'notes' ? `[data-nsec="${si}"]` : `[data-sec="${si}"]`),
      h('span', {text: view === 'notes' ? secName(s) : s.title_translation && S.lang !== 'orig' ? s.title_translation : s.title_original}), h('span', {class: 'toc-t', text: fmtR(s.start, s.end)})); };
  let items;
  if (NOTES && (isSplit() || S.view === 'notes')) {
    const {places, groups} = noteGroups();
    const unitLink = (ui, time) => link(go('notes', `[data-unit="${ui}"]`),
      time ? h('span', {class: 'toc-t', text: places[ui].start ? fmtT(places[ui].start) : ''}) : null, h('span', {text: NOTES.units[ui].heading}));
    const unitLi = ui => h('li', {class: 'toc-unit'}, unitLink(ui, true));
    items = MAP.sections.length
      ? groups.flatMap(g => g.sec == null ? g.units.map(ui => h('li', {class: 'toc-sec'}, unitLink(ui, false)))
        : [h('li', {class: 'toc-sec'}, secLink(g.sec, 'notes'), g.units.length ? h('ul', null, g.units.map(unitLi)) : null)])
      : NOTES.units.map((_, ui) => unitLi(ui));
  } else items = MAP.sections.map((_, si) => h('li', {class: 'toc-sec'}, secLink(si, 'reader')));
  det = h('details', {class: 'pop', id: 'toc'}, h('summary', {title: t('toc')}, h('span', {class: 'ic ic-list'}), t('toc')),
    h('div', {class: 'pop-body'}, h('ul', null, items)));
  return det;
}
function renderHeader() {
  const seg = (val, opts, on) => h('div', {class: 'seg', role: 'group'}, opts.map(o => h('button', {'aria-pressed': String(val === o.v), onclick: () => on(o.v), text: o.t})));
  const title = NOTES ? NOTES.title : MAP.media.title;
  const speakers = MAP.speakers.map(s => s.id);
  if (MAP.blocks.some(b => b.speaker == null)) speakers.push(null);
  return h('header', {class: 'hdr'},
    h('h1', {title, text: title}),
    h('div', {class: 'views'},
      NOTES ? h('span', {id: 'tabs'}, seg(S.view, [{v: 'notes', t: t('notes')}, {v: 'reader', t: t('reader')}], v => switchView(v, () => { rerenderChrome(); runFilters(); }))) : null,
      hasTrans ? h('span', {id: 'langseg'}, seg(S.lang, [{v: 'both', t: t('both')}, {v: 'orig', t: t('orig')}, {v: 'trans', t: t('trans')}], v => keepReaderPlace(() => { S.lang = v; rootAttrs(); rerenderChrome(); runFilters(); }))) : null),
    infoPop(),
    h('div', {class: 'hdr-tools'},
      h('span', {class: 'hint', id: 'other'}),
      tocPop(),
      h('label', {class: 'search'},
        h('span', {class: 'ic ic-search'}),
        h('input', {type: 'search', id: 'q', placeholder: t('search'), value: S.q,
          oninput: e => { S.q = e.target.value; clearTimeout(S.tm); S.tm = setTimeout(runFilters, 120); },
          onkeydown: e => { if (e.key === 'Enter') { e.preventDefault(); step(e.shiftKey ? -1 : 1); } if (e.key === 'Escape') { e.target.value = ''; S.q = ''; runFilters(); } }}),
        h('span', {class: 'cnt', id: 'cnt'}),
        h('button', {type: 'button', title: t('prev'), onclick: e => { e.preventDefault(); step(-1); }, text: '↑'}),
        h('button', {type: 'button', title: t('next'), onclick: e => { e.preventDefault(); step(1); }, text: '↓'}))),
    h('div', {class: 'spk-bar'},
      speakers.length ? h('span', {class: 'bar-label', text: t('spks')}) : null,
      h('div', {class: 'chips'}, speakers.map(spkChip)),
      renamePending()));
}

/* ---------- Search and filters (Custom Highlight API, no DOM changes) ---------- */
/* Lowercasing can change a string's length (İ becomes two code units), so fold one code point at a time
   and record which original character each folded unit came from. Final sigma folds with sigma. */
function fold(text) {
  let low = ''; const starts = [], ends = [];
  for (const ch of text) {
    const at = starts.length ? ends[ends.length - 1] : 0, folded = ch.toLowerCase().replace('ς', 'σ');
    for (let k = 0; k < folded.length; k++) { starts.push(at); ends.push(at + ch.length); }
    low += folded;
  }
  return {low, starts, ends};
}
function rangesIn(el, needle) {
  const out = [], nodes = []; const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let n, txt = '';
  while ((n = w.nextNode())) { nodes.push({n, at: txt.length}); txt += n.data; }
  const {low, starts, ends} = fold(txt); let i = 0;
  const loc = p => { let k = nodes.length - 1; while (k > 0 && nodes[k].at > p) k--; return [nodes[k].n, p - nodes[k].at]; };
  while ((i = low.indexOf(needle, i)) >= 0) {
    const end = i + needle.length, r = document.createRange();
    const last = ends[end - 1];
    const [a, ao] = loc(starts[i]); const [b, bo] = loc(last - 1);
    r.setStart(a, ao); r.setEnd(b, bo + 1); out.push(r); i = end;
  }
  return out;
}
function panes() {
  const r = document.querySelector('.pane-reader'), c = document.querySelector('.pane-notes');
  if (isSplit()) return c ? [document.getElementById('band'), c, r] : [r];
  return [S.view === 'notes' && c ? c : r];
}
function runFilters() {
  const reader = document.querySelector('.pane-reader'), notes = document.querySelector('.pane-notes');
  const on = S.spk.size > 0;
  reader.querySelectorAll('.turn').forEach(turn => { turn.hidden = on && !S.spk.has(turn.dataset.spk === 'none' ? null : turn.dataset.spk); });
  if (notes) document.querySelectorAll('.pane-notes .para, .band .para').forEach(p => { const ids = p.dataset.spk ? p.dataset.spk.split(' ') : []; p.hidden = on && ids.length > 0 && !ids.some(i => S.spk.has(i)); });

  const needle = fold(S.q.trim()).low; S.hits = []; let other = 0;
  if (needle) {
    panes().forEach(p => p.querySelectorAll('.tx').forEach(el => {
      const host = el.closest('.block,.para,h2,h3');
      if (host && (host.hidden || host.closest('.turn')?.hidden)) return;
      const inHiddenLang = (S.lang === 'orig' && el.classList.contains('trans')) || (S.lang === 'trans' && el.classList.contains('orig') && !el.classList.contains('only'));
      const rs = rangesIn(el, needle);
      if (inHiddenLang) other += rs.length; else S.hits.push(...rs);
    }));
  }
  S.cur = -1;
  if (window.CSS && CSS.highlights && window.Highlight) { CSS.highlights.set('hit', new Highlight(...S.hits)); CSS.highlights.delete('cur'); }
  document.getElementById('cnt').textContent = needle ? (S.hits.length ? `${S.hits.length}` : t('noHit')) : '';
  document.getElementById('other').textContent = needle && other ? t('inOther', {n: other}) : '';

  reader.querySelectorAll('.fold').forEach(f => f.remove());
  if (on) {
    let run = [];
    const flush = () => { if (run.length) { const n = run.reduce((a, turn) => a + turn.querySelectorAll('.block').length, 0); run[0].before(h('div', {class: 'fold'}, h('span', {text: t('hidden', {n})}))); run = []; } };
    reader.querySelectorAll('.col > *').forEach(el => { if (el.classList.contains('turn') && el.hidden) run.push(el); else flush(); });
    flush();
  }
  syncAnch = null;
  requestAnimationFrame(refreshLinked);
}
function step(d) {
  if (!S.hits.length) return;
  S.cur = (S.cur + d + S.hits.length) % S.hits.length;
  const r = S.hits[S.cur];
  if (window.Highlight) CSS.highlights.set('cur', new Highlight(r));
  document.getElementById('cnt').textContent = `${S.cur + 1}/${S.hits.length}`;
  const hostEl = r.startContainer.parentElement;
  master = hostEl.closest('.pane');
  hostEl.scrollIntoView({block: 'center'});
}

/* ---------- Assembly ---------- */
function rootAttrs() {
  document.documentElement.dataset.lang = S.lang;
  document.body.classList.toggle('is-split', isSplit());
}
function applyPanes() {
  const split = isSplit();
  document.body.classList.toggle('is-split', split);
  const c = document.querySelector('.pane-notes'), r = document.querySelector('.pane-reader');
  if (c) c.hidden = !split && S.view !== 'notes';
  r.hidden = !split && S.view !== 'reader';
  const tabs = document.getElementById('tabs'); if (tabs) tabs.hidden = split;
  const ls = document.getElementById('langseg'); if (ls) ls.hidden = !split && S.view !== 'reader';
  const seg = tabs && tabs.querySelectorAll('button');
  if (seg && seg.length) { seg[0].setAttribute('aria-pressed', String(S.view === 'notes')); seg[1].setAttribute('aria-pressed', String(S.view === 'reader')); }
  placeOrient(split);
  showBack();
}
/* In the wide layout the page scrolls the band away first; until then the panes stay put and the wheel moves the page. */
const hdrSize = new ResizeObserver(() => sizeSplit());
function placeOrient(split) {
  const band = document.getElementById('band'), c = document.querySelector('.pane-notes');
  hdrSize.disconnect(); hdrSize.observe(document.querySelector('.hdr'));
  if (band && orientEls.length) {
    const home = split ? band.firstElementChild : c.firstElementChild;
    if (orientEls[0].parentNode !== home) split ? home.append(...orientEls) : home.prepend(...orientEls);
    band.hidden = !split;
  }
  sizeSplit();
}
function sizeSplit() {
  const hdr = document.querySelector('.hdr');
  if (hdr) document.body.style.setProperty('--hdr-h', `${hdr.getBoundingClientRect().height}px`);
  bandState();
}
function bandIn() {
  const band = document.getElementById('band');
  return isSplit() && band && !band.hidden && band.getBoundingClientRect().bottom > document.querySelector('.hdr').getBoundingClientRect().bottom + 1;
}
function bandState() { document.body.classList.toggle('band-in', !!bandIn()); }
function bandAway() { if (bandIn()) { scrollTo(0, document.scrollingElement.scrollHeight); bandState(); } }
addEventListener('scroll', bandState, {passive: true});
/* A wheel gesture stays with the scroller it started on, so handing over between the page and a pane would stall until the next
   gesture. While the band exists the page routes the wheel itself: down fills the page first and passes the rest to the pane under
   the pointer, up empties that pane first and passes the rest to the page. */
addEventListener('wheel', e => {
  const band = document.getElementById('band');
  if (!isSplit() || !band || band.hidden || e.ctrlKey) return;
  const dy = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? innerHeight : 1);
  if (!dy || Math.abs(e.deltaX) > Math.abs(dy)) return;
  /* A popup that can still scroll this way keeps the wheel to itself. */
  const pop = e.target.closest?.('.pop-body');
  if (pop && (dy > 0 ? pop.scrollTop + pop.clientHeight < pop.scrollHeight - 1 : pop.scrollTop > 0)) return;
  const pane = document.elementFromPoint(e.clientX, e.clientY)?.closest('.pane');
  if (!pane && !e.target.closest?.('.band')) return;
  e.preventDefault();
  const page = document.scrollingElement, room = page.scrollHeight - innerHeight - scrollY;
  const pageMove = dy > 0 ? Math.min(dy, Math.max(0, room)) : -Math.min(-dy - (pane ? Math.min(-dy, pane.scrollTop) : 0), scrollY);
  const paneMove = dy - pageMove;
  if (pageMove) scrollBy(0, pageMove);
  if (pane && paneMove) { master = pane; pane.scrollTop += paneMove; }
  bandState();
}, {passive: false});
/* Switching language changes every paragraph's height; keep the topmost visible reader block where it was. */
function keepReaderPlace(change) {
  const pane = document.querySelector('.pane-reader'), scroller = isSplit() ? pane : document.scrollingElement;
  const top = isSplit() ? pane.getBoundingClientRect().top : viewTop();
  const bottom = isSplit() ? pane.getBoundingClientRect().bottom : innerHeight;
  const seen = el => { const r = el.getBoundingClientRect(); return r.bottom > top && r.top < bottom; };
  /* A skipped off-screen turn reports stale positions for its blocks, so check the turn first. */
  const block = pane && [...pane.querySelectorAll('.block')].find(b => seen(b.closest('.turn')) && seen(b));
  if (!block) { change(); return; }
  const box = block.getBoundingClientRect(), before = box.top;
  /* A block cut by the top edge keeps the same share of itself above the edge, so a shorter block still crosses it. */
  const share = before < top ? (top - before) / box.height : 0;
  const fix = () => {
    const now = block.getBoundingClientRect();
    scroller.scrollTop += now.top - (share ? top - share * now.height : before);
  };
  /* Restoring the transcript must not scroll the notes: hold sync, then ease from where both panes are, as after a link jump. */
  const split = isSplit(), notes = document.querySelector('.pane-notes');
  if (split) syncHold = true;
  scroller.style.overflowAnchor = 'none';
  change(); fix();
  /* Off-screen turns keep placeholder heights until laid out, which can cap the first correction. */
  requestAnimationFrame(() => {
    fix(); scroller.style.overflowAnchor = '';
    if (!split) return;
    requestAnimationFrame(() => {
      syncAnch = buildAnchors();
      const driver = master || pane;
      ease = startEase(driver, driver === pane ? notes : pane, lineAt(driver, driver.scrollTop));
      syncHold = false;
    });
  });
}
function rerenderChrome() {
  const old = document.querySelector('.hdr'); const q = document.getElementById('q'); const had = document.activeElement === q;
  old.replaceWith(renderHeader());
  applyPanes();
  if (had) document.getElementById('q').focus();
}
function render() {
  blockEls.clear(); paraEls.clear(); frameEls.clear(); rootAttrs();
  const main = h('main', {class: 'split'},
    NOTES ? h('section', {class: 'pane pane-notes'}, renderNotes()) : null,
    h('section', {class: 'pane pane-reader'}, renderReader()));
  const band = h('section', {class: 'band', id: 'band', hidden: true}, h('div', {class: 'col'}));
  document.getElementById('app').replaceChildren(renderHeader(), band, main);
  applyPanes(); initSync(); runFilters();
}

document.addEventListener('keydown', e => {
  if (e.target.matches('input,textarea,select,[contenteditable]')) return;
  if (e.key === '/') { e.preventDefault(); document.getElementById('q').focus(); }
});
document.getElementById('back').addEventListener('click', () => history.back());
matchMedia('(min-width:1100px)').addEventListener('change', () => { rerenderChrome(); applyPanes(); syncAnch = null; runFilters(); });
document.addEventListener('click', e => {
  document.querySelectorAll('details.pop[open]').forEach(d => { if (!d.contains(e.target)) d.open = false; });
});

render();
/* Deep links: #S012 opens a block, #n-1-0 opens a Notes paragraph. */
(function () {
  const m = location.hash.slice(1); if (!m) return;
  if (byId.has(m)) { S.view = 'reader'; rerenderChrome(); const el = blockEls.get(m); mark([el]); el.scrollIntoView({block: 'center'}); return; }
  const c = m.match(/^n-(\d+)-(\d+)$/);
  if (c && NOTES) { S.view = 'notes'; rerenderChrome(); const el = paraEls.get(`${c[1]}.${c[2]}`); if (el) { mark([el]); el.scrollIntoView({block: 'center'}); } }
})();

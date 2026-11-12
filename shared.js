/* Shared catalogue logic for every Al Farash design.
   Each page defines window.DESIGN = { card(p), tile(cat, name, count, p), pageSize } before this runs,
   and uses these element ids where it wants them: grid, count, empty, more, reset, reset2, q, size,
   sort, cats, cols, styles, yr. Any <img data-pid="..."> is filled with that product's photo,
   and any [data-price-of="..."] with its price. */
// Small fallback so older browsers (Safari before 12.1, Chrome before 73) can run the page
if (!Object.fromEntries) Object.fromEntries = it => { const o = {}; for (const [k, v] of it) o[k] = v; return o; };
const PRODUCTS = /*__PRODUCTS__*/[];
const IMG = (k, s = 500) => `https://i.ebayimg.com/images/g/${k}/s-l${s}.webp`;
const URL_FOR = id => `https://www.ebay.co.uk/itm/${id}`;
const gbp = n => '£' + n.toFixed(2);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const $ = id => document.getElementById(id);

const CATS = [
  ['all', 'Everything'],
  ['greek', 'Greek key borders'],
  ['circles', 'Round Greek key'],
  ['stones', 'Diamante & crystal'],
  ['geometric', 'Moroccan, geometric & baroque'],
  ['motifs', 'Horses, bees & motifs'],
  ['curtains', 'Curtains & blinds'],
  ['table', 'Table runners & mats'],
];
// Main colour = the colour of the velvet itself; each product has exactly one (p.mc).
// Detail colours = the Greek key, border or motif, usually gold or silver (p.dt, a list).
const COLS = [
  ['black', 'Black', '#16151a'],
  ['white', 'White', '#ffffff'],
  ['offwhite', 'Off-white', '#f7f2e7'],
  ['ivory', 'Ivory & cream', '#efe4c8'],
  ['grey', 'Grey & silver', 'linear-gradient(135deg,#6f7177,#c9cacd 55%,#85878c)'],
  ['navy', 'Navy & blue', '#1d2747'],
  ['red', 'Red & maroon', '#7c1b25'],
  ['teal', 'Turquoise & teal', '#1f8a8a'],
  ['brown', 'Brown & beige', '#6b4a2f'],
  ['pink', 'Pink & purple', '#8a3a78'],
  ['yellow', 'Yellow & mustard', '#d9a91c'],
  ['green', 'Green', '#2f6b45'],
  ['gold', 'Gold', 'linear-gradient(135deg,#8a6420,#e6c879 55%,#a57b2c)'],
];
const DETAILS = [
  ['gold', 'Gold', 'linear-gradient(135deg,#8a6420,#e6c879 55%,#a57b2c)'],
  ['silver', 'Silver', 'linear-gradient(135deg,#8d8f95,#e3e4e7 55%,#9a9ca2)'],
  ['black', 'Black', '#16151a'],
  ['white', 'White', '#ffffff'],
  ['offwhite', 'Off-white', '#f7f2e7'],
  ['ivory', 'Ivory', '#efe4c8'],
  ['red', 'Red', '#7c1b25'],
  ['teal', 'Turquoise', '#1f8a8a'],
  ['navy', 'Navy', '#1d2747'],
  ['pink', 'Pink & purple', '#8a3a78'],
  ['brown', 'Brown', '#6b4a2f'],
  ['yellow', 'Yellow', '#d9a91c'],
  ['green', 'Green', '#2f6b45'],
];
const CAT_NAME = Object.fromEntries(CATS);
const BY_ID = Object.fromEntries(PRODUCTS.map(p => [p.id, p]));
// A product can belong to several categories (p.cs), so each category counts every product tagged with it
const COUNTS = PRODUCTS.reduce((m, p) => (p.cs.forEach(c => m[c] = (m[c] || 0) + 1), m), {});
const TILE_PICK = { greek: '334597439540', circles: '333693205871', stones: '333765205132', geometric: '332814808029', motifs: '334020803277', curtains: '336393096850' };
const D = window.DESIGN || {};
const PAGE = D.pageSize || 24;
const state = { q: '', cat: 'all', size: '', sort: 'f', shown: PAGE };

// UK cushion sizes are sold in both inches and centimetres (17 in is the standard 43 cm cover)
const CM = { 16: 40, 17: 43, 18: 45, 20: 50, 22: 55, 24: 60 };
const cmOf = n => CM[n] || Math.round(n * 2.54);
const METRIC = !!D.metric;  // designs that also show sizes in centimetres
const sizeLabel = p => p.c === 'curtains' ? 'Curtain & blind set' : p.c === 'table' ? (p.tl || 'Table set') : (p.s ? `${p.s} × ${p.s} in` + (METRIC ? ` · ${cmOf(p.s)} cm` : '') : 'Cushion cover');

// Fill any product photo / price placeholders in the page
document.querySelectorAll('img[data-pid]').forEach(img => {
  const p = BY_ID[img.dataset.pid];
  if (!p) { img.closest('[data-optional]')?.remove(); return; }      // listing ended: drop optional blocks (hero slides)
  if (img.dataset.img) {                                              // a chosen gallery photo; fall back to the main one
    img.addEventListener('error', () => { img.removeAttribute('srcset'); img.src = IMG(p.img, img.dataset.size || 640); }, { once: true });
  }
  if (!img.getAttribute('src')) img.src = IMG(img.dataset.img || p.img, img.dataset.size || 640);
  if (!img.hasAttribute('alt')) img.alt = p.t;
  const a = img.closest('a[data-link]'); if (a) { a.href = URL_FOR(p.id); a.target = '_blank'; a.rel = 'noopener'; }
});
document.querySelectorAll('[data-price-of]').forEach(el => { const p = BY_ID[el.dataset.priceOf]; if (p) el.textContent = gbp(p.p); });
document.querySelectorAll('[data-title-of]').forEach(el => { const p = BY_ID[el.dataset.titleOf]; if (p) el.textContent = p.t + ' (opens eBay in a new tab)'; });
document.querySelectorAll('[data-count]').forEach(el => { el.textContent = el.dataset.count === 'all' ? PRODUCTS.length : (COUNTS[el.dataset.count] || 0); });

// Shop-by-style tiles
if ($('styles') && D.tile) {
  $('styles').innerHTML = CATS.slice(1, 7).map(([k, n]) => {
    const p = BY_ID[TILE_PICK[k]] || PRODUCTS.find(x => x.cs.includes(k));
    return D.tile(k, n, COUNTS[k] || 0, p);
  }).join('');
  $('styles').addEventListener('click', e => {
    const b = e.target.closest('[data-cat]'); if (!b) return;
    e.preventDefault(); setCat(b.dataset.cat); $('shop').scrollIntoView();
  });
}
const COL_BG = Object.fromEntries(DETAILS.concat(COLS).map(([k, , bg]) => [k, bg]));
const COL_NAME = Object.fromEntries(COLS.map(([k, n]) => [k, n]));
const DET_NAME = Object.fromEntries(DETAILS.map(([k, n]) => [k, n]));
const COL_COUNTS = PRODUCTS.reduce((m, p) => (p.mc && (m[p.mc] = (m[p.mc] || 0) + 1), m), {});
const DET_ALL = PRODUCTS.reduce((m, p) => (p.dt.forEach(d => m[d] = (m[d] || 0) + 1), m), {});
const SHOWN_COLS = COLS.filter(([k]) => COL_COUNTS[k]);
const SHOWN_DETS = DETAILS.filter(([k]) => (DET_ALL[k] || 0) >= 3);   // detail colours worth offering as a filter

// What the product is (shown as tabs) and what its design is (a filter). A cushion can carry more than one design tag.
const TYPES = [['all', 'Everything'], ['cushions', 'Cushion covers'], ['curtains', 'Curtains & blinds'], ['table', 'Table runners & mats']];
const TYPE_NAME = Object.fromEntries(TYPES);
const typeOf = p => p.c === 'curtains' ? 'curtains' : p.c === 'table' ? 'table' : 'cushions';
const DESIGNS = [['greek', 'Greek key border'], ['circles', 'Round Greek key & medallion'], ['geometric', 'Moroccan, geometric & baroque'], ['motifs', 'Animals & motifs']];
const DES_NAME = Object.fromEntries(DESIGNS);

// ---- Filter state. Design, colour and detail allow several choices at once (e.g. Black or Navy). ----
Object.assign(state, { type: 'all', des: [], stones: false, col: [], det: [] });
const toggle = (arr, v) => arr.includes(v) ? arr.filter(x => x !== v) : arr.concat(v);
// One test per filter group. Counts for a group use every OTHER group, so each number says what you'd get by adding it.
const words = () => state.q.split(/\s+/).filter(Boolean);
const HAY = {};
const hay = p => HAY[p.id] || (HAY[p.id] = (p.t + ' ' + (p.k || '') + ' ' + p.cs.map(c => CAT_NAME[c] + ' ' + (DES_NAME[c] || '')).join(' ') + ' ' + (COL_NAME[p.mc] || '') + ' ' + TYPE_NAME[typeOf(p)] + (p.s ? ` ${p.s}in ${cmOf(p.s)}cm ${cmOf(p.s)} cm` : '')).toLowerCase());
function sizeOk(p) { return !state.size || p.s === Number(state.size); }   // exact size in inches, from the eBay item details
const TESTS = {
  cat: p => state.cat === 'all' || p.cs.includes(state.cat),
  type: p => state.type === 'all' || typeOf(p) === state.type,
  des: p => !state.des.length || state.des.some(d => p.cs.includes(d)),
  stones: p => !state.stones || p.cs.includes('stones'),
  col: p => !state.col.length || state.col.includes(p.mc),
  det: p => !state.det.length || state.det.some(d => p.dt.includes(d)),
  size: sizeOk,
  q: p => { const w = words(); return !w.length || w.every(x => hay(p).includes(x)); },
};
const passing = except => PRODUCTS.filter(p => Object.keys(TESTS).every(k => k === except || TESTS[k](p)));
const countBy = (list, keyFn) => list.reduce((m, p) => ([].concat(keyFn(p)).forEach(k => k && (m[k] = (m[k] || 0) + 1)), m), {});

// ---- Build the filter controls that this design has room for ----
if ($('cats')) {   // older designs: one "style" list
  $('cats').innerHTML = CATS.map(([k, n]) =>
    `<button class="chip" type="button" data-cat="${k}" aria-pressed="${k === 'all'}">${n}<small>${k === 'all' ? PRODUCTS.length : (COUNTS[k] || 0)}</small></button>`).join('');
  $('cats').addEventListener('click', e => { const b = e.target.closest('[data-cat]'); if (b) setCat(b.dataset.cat); });
}
if ($('types')) {
  $('types').innerHTML = TYPES.map(([k, n]) => `<button class="type-tab" type="button" data-type="${k}" aria-pressed="${k === 'all'}">${n}<small data-type-count="${k}"></small></button>`).join('');
  $('types').addEventListener('click', e => {
    const b = e.target.closest('[data-type]'); if (!b) return;
    state.type = b.dataset.type;
    if (state.type === 'curtains' || state.type === 'table') { state.des = []; state.stones = false; }   // design filters are for cushion covers
    refilter();
  });
}
if ($('designs')) {
  $('designs').innerHTML = DESIGNS.map(([k, n]) => `<button class="chip" type="button" data-des="${k}" aria-pressed="false">${n}<small data-des-count="${k}"></small></button>`).join('');
  $('designs').addEventListener('click', e => { const b = e.target.closest('[data-des]'); if (!b || b.disabled) return; state.des = toggle(state.des, b.dataset.des); refilter(); });
}
if ($('stones')) $('stones').addEventListener('change', e => { state.stones = e.target.checked; refilter(); });
if ($('cols')) {
  $('cols').insertAdjacentHTML('beforeend', SHOWN_COLS.map(([k, n, bg]) =>
    D.swatchCounts  // designs with room for it show how many pieces come in each colour
      ? `<button class="swatch" type="button" data-col="${k}" aria-pressed="false"><i style="background:${bg}"></i><span>${n}</span><small data-col-count="${k}">${COL_COUNTS[k] || 0}</small></button>`
      : `<button class="swatch" type="button" data-col="${k}" aria-pressed="false" title="${n}" aria-label="${n}"><i style="background:${bg}"></i><span>${n}</span></button>`).join(''));
  // One base colour at a time: picking another colour replaces the first, picking the same one again clears it
  $('cols').addEventListener('click', e => { const b = e.target.closest('[data-col]'); if (!b || b.disabled) return; state.col = state.col.includes(b.dataset.col) ? [] : [b.dataset.col]; refilter(); });
}
// Detail colour (the Greek key / border colour). Its counts follow the other choices, e.g. Ivory -> gold 33
if ($('dets')) {
  $('dets').innerHTML = SHOWN_DETS.map(([k, n, bg]) =>
    `<button class="swatch" type="button" data-det="${k}" aria-pressed="false"><i style="background:${bg}"></i><span>${n}</span><small data-det-count="${k}"></small></button>`).join('');
  $('dets').addEventListener('click', e => { const b = e.target.closest('[data-det]'); if (!b || b.disabled) return; state.det = toggle(state.det, b.dataset.det); refilter(); });
}
// Size dropdown: one option per real size, with how many cushions come in it
if ($('size')) {
  const bySize = PRODUCTS.reduce((m, p) => (p.s ? (m[p.s] = (m[p.s] || 0) + 1, m) : m), {});
  $('size').innerHTML = '<option value="">Any size</option>' + Object.keys(bySize).map(Number).sort((a, b) => a - b)
    .map(n => `<option value="${n}">${n} × ${n} in${METRIC ? ` / ${cmOf(n)} cm` : ''} (${bySize[n]})</option>`).join('');
}
// Links elsewhere on the page that jump into the catalogue with filters set, e.g. the colour tiles and "Complete the look"
document.addEventListener('click', e => {
  const a = e.target.closest('[data-goto-cat], [data-goto-col], [data-goto-type], [data-goto-det]');
  if (!a) return;
  e.preventDefault();
  if (a.dataset.gotoCat) { state.cat = a.dataset.gotoCat; }
  if (a.dataset.gotoCol || a.dataset.gotoDet || a.dataset.gotoType) {
    Object.assign(state, { cat: 'all', type: a.dataset.gotoType || 'all', des: [], stones: false,
      col: a.dataset.gotoCol ? [a.dataset.gotoCol] : [], det: a.dataset.gotoDet ? [a.dataset.gotoDet] : [] });
  }
  refilter(); $('shop').scrollIntoView();
});
function setCat(k) { state.cat = k; refilter(); }
// After any filter, search or sort change. When the visitor had scrolled down into a long list, the new (often much
// shorter) list would otherwise leave them stranded at the bottom of the page, so bring the start of the results back
// into view. "Show more" doesn't use this, so it never moves the page.
function refilter() { state.shown = PAGE; render(); keepResultsInView(); }
function keepResultsInView(evenIfBelow) {
  const root = document.documentElement;
  if (root.classList.contains('drawer-open') || !$('grid')) return;   // the phone filter panel scrolls when it closes
  const head = document.querySelector('header');
  const headH = parseFloat(getComputedStyle(root).getPropertyValue('--head-h')) || (head && getComputedStyle(head).position === 'sticky' ? head.getBoundingClientRect().height : 0);
  const top = $('grid').parentElement.getBoundingClientRect().top;
  if (top < headH || (evenIfBelow && top > innerHeight * 0.6)) {
    const prev = root.style.scrollBehavior;
    root.style.scrollBehavior = 'auto';   // jump straight there; the list itself has just changed
    window.scrollTo(0, Math.max(0, scrollY + top - headH - 12));
    root.style.scrollBehavior = prev;
  }
}
let timer;
$('q') && $('q').addEventListener('input', e => { clearTimeout(timer); timer = setTimeout(() => { state.q = e.target.value.trim().toLowerCase(); refilter(); }, 120); });
// Browsers can restore a dropdown's last choice after a reload or "back" without firing a change event,
// so the page always reads the controls' current values instead of trusting its own defaults.
function syncFromControls() {
  if ($('q')) state.q = $('q').value.trim().toLowerCase();
  if ($('size')) state.size = $('size').value;
  if ($('sort')) state.sort = $('sort').value || 'f';
  if ($('stones')) state.stones = $('stones').checked;
}
function onSizeOrSort(e) {
  const before = state.sort;
  syncFromControls(); state.shown = PAGE; render();
  // A new sort order should show its first results, even if the list was scrolled down or sits below the controls
  keepResultsInView(e && e.target.id === 'sort' && state.sort !== before);
}
['size', 'sort'].forEach(id => { if ($(id)) { $(id).addEventListener('change', onSizeOrSort); $(id).addEventListener('input', onSizeOrSort); } });
window.addEventListener('pageshow', () => { syncFromControls(); render(); });
$('more') && $('more').addEventListener('click', () => { state.shown += PAGE; render(); });

// Filters are kept in the page address (e.g. ?type=cushions&design=greek&colour=black,navy&size=24), so a filtered
// view can be bookmarked or sent to a customer, and survives a reload
function readURL() {
  let qs; try { qs = new URLSearchParams(location.search); } catch (e) { return; }
  const get = k => (qs.get(k) || '').trim();
  const list = (k, names) => get(k).split(',').map(x => x.trim()).filter(x => names[x]);
  const style = get('style');   // links made before the type / design split still work
  if (style && $('cats') && CAT_NAME[style]) state.cat = style;
  else if (style === 'curtains' || style === 'table') state.type = style;
  else if (style === 'stones') state.stones = true;
  else if (DES_NAME[style]) state.des = [style];
  if (TYPE_NAME[get('type')]) state.type = get('type');
  if (get('design')) state.des = list('design', DES_NAME);
  if (get('stones') === '1') state.stones = true;
  state.col = list('colour', COL_NAME).slice(0, 1);   // one base colour at a time (older links could list several)
  state.det = list('detail', DET_NAME);
  if ($('stones')) $('stones').checked = state.stones;
  if ($('size') && get('size') && [...$('size').options].some(o => o.value === get('size'))) $('size').value = get('size');
  if ($('sort') && get('sort') && [...$('sort').options].some(o => o.value === get('sort'))) $('sort').value = get('sort');
  if ($('q') && get('q')) $('q').value = get('q');
}
function writeURL() {
  try {
    const vals = [['style', state.cat !== 'all' && state.cat], ['type', state.type !== 'all' && state.type], ['design', state.des.join(',')],
      ['stones', state.stones && '1'], ['colour', state.col.join(',')], ['detail', state.det.join(',')], ['size', state.size],
      ['sort', state.sort !== 'f' && state.sort], ['q', state.q]];
    const qs = vals.filter(([, v]) => v).map(([k, v]) => k + '=' + encodeURIComponent(v).replace(/%2C/g, ',')).join('&');
    const next = location.pathname + (qs ? '?' + qs : '') + location.hash;
    if (next !== location.pathname + location.search + location.hash) history.replaceState(history.state, '', next);
  } catch (e) { /* some browsers block this on local files; filtering still works */ }
}
// Removable chips for each active filter (shown above the results)
function activeChips() {
  const c = [];
  if (state.cat !== 'all') c.push(['cat:', CAT_NAME[state.cat]]);
  if (state.type !== 'all') c.push(['type:', TYPE_NAME[state.type]]);
  state.des.forEach(d => c.push(['des:' + d, DES_NAME[d]]));
  if (state.stones) c.push(['stones:', 'With crystal stones']);
  state.col.forEach(k => c.push(['col:' + k, COL_NAME[k]]));
  state.det.forEach(k => c.push(['det:' + k, `${DET_NAME[k]} detail`]));
  if (state.size) c.push(['size:', `${state.size} in / ${cmOf(Number(state.size))} cm`]);
  if (state.q) c.push(['q:', `“${state.q}”`]);
  return c;
}
function renderActive() {
  const box = $('active'); if (!box) return;
  const chips = activeChips();
  box.hidden = !chips.length;
  box.innerHTML = chips.map(([k, n]) => `<button type="button" class="active-chip" data-clear="${k}" aria-label="Remove filter: ${esc(n)}">${esc(n)}<span aria-hidden="true">×</span></button>`).join('');
}
$('active') && $('active').addEventListener('click', e => {
  const b = e.target.closest('[data-clear]'); if (!b) return;
  const [k, v] = b.dataset.clear.split(':');
  if (k === 'cat') state.cat = 'all';
  if (k === 'type') state.type = 'all';
  if (k === 'des') state.des = state.des.filter(x => x !== v);
  if (k === 'stones') { state.stones = false; if ($('stones')) $('stones').checked = false; }
  if (k === 'col') state.col = state.col.filter(x => x !== v);
  if (k === 'det') state.det = state.det.filter(x => x !== v);
  if (k === 'size') { state.size = ''; if ($('size')) $('size').value = ''; }
  if (k === 'q') { state.q = ''; if ($('q')) $('q').value = ''; }
  refilter();
  const next = $('active').querySelector('.active-chip') || $('grid');
  if (next === $('grid')) { $('grid').setAttribute('tabindex', '-1'); }
  next.focus({ preventScroll: true });
});
function resetAll() {
  Object.assign(state, { q: '', cat: 'all', type: 'all', des: [], stones: false, col: [], det: [], size: '', shown: PAGE });
  if ($('q')) $('q').value = ''; if ($('size')) $('size').value = ''; if ($('stones')) $('stones').checked = false; refilter();
}
['reset', 'reset2', 'reset3'].forEach(id => $(id) && $(id).addEventListener('click', resetAll));
const activeCount = () => activeChips().length;

// Update one group's buttons: pressed state, live count, and greyed out when choosing it would show nothing
function syncGroup(sel, attr, counts, chosen) {
  document.querySelectorAll(sel).forEach(b => {
    const k = b.dataset[attr], n = counts[k] || 0, on = chosen.includes(k);
    b.setAttribute('aria-pressed', on); b.disabled = !n && !on;
    const c = b.querySelector('small'); if (c && c.hasAttribute(`data-${attr}-count`)) c.textContent = n;
  });
}
function render() {
  const list = passing();
  if ($('types')) {
    const tc = countBy(passing('type'), typeOf); tc.all = passing('type').length;
    document.querySelectorAll('#types [data-type]').forEach(b => { b.setAttribute('aria-pressed', b.dataset.type === state.type); b.querySelector('small').textContent = tc[b.dataset.type] || 0; });
  }
  if ($('designs')) syncGroup('#designs [data-des]', 'des', countBy(passing('des'), p => p.cs), state.des);
  if ($('stones')) { const n = passing('stones').filter(p => p.cs.includes('stones')).length; const c = $('stones-count'); if (c) c.textContent = n; $('stones').checked = state.stones; $('stones').disabled = !n && !state.stones; }
  if ($('cols')) syncGroup('#cols [data-col]', 'col', countBy(passing('col'), p => p.mc), state.col);
  if ($('dets')) syncGroup('#dets [data-det]', 'det', countBy(passing('det'), p => p.dt), state.det);
  list.sort({
    f: (a, b) => a.f - b.f || (a.c === 'curtains') - (b.c === 'curtains') || b.id.localeCompare(a.id),
    pa: (a, b) => a.p - b.p || a.f - b.f, pd: (a, b) => b.p - a.p || a.f - b.f, n: (a, b) => b.id.localeCompare(a.id),
  }[state.sort]);
  document.querySelectorAll('#cats [data-cat]').forEach(b => b.setAttribute('aria-pressed', b.dataset.cat === state.cat));
  if ($('reset')) $('reset').hidden = !activeCount();
  if ($('count')) $('count').textContent = `Showing ${Math.min(state.shown, list.length)} of ${list.length} ${list.length === 1 ? 'piece' : 'pieces'}`;
  if ($('empty')) $('empty').hidden = list.length > 0;
  if ($('more')) { $('more').hidden = list.length <= state.shown; $('more').textContent = `Show ${Math.min(PAGE, list.length - state.shown)} more`; }
  $('grid').innerHTML = list.slice(0, state.shown).map(D.card).join('');
  renderActive();
  writeURL();
  if (D.afterRender) D.afterRender(list, state);
}
if ($('yr')) $('yr').textContent = new Date().getFullYear();
readURL();
syncFromControls();
render();

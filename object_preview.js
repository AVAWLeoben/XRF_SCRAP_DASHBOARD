/* Browser-only photo tooltip. It reads Plotly point metadata, never changes data. */
(() => {
  'use strict';
  const scriptURL = document.currentScript.src;
  const base = new URL('.', scriptURL);
  let manifest;
  function getManifest() {
    if (!manifest) manifest = fetch(new URL('image-index.json', base))
      .then(r => { if (!r.ok) throw Error('Photo index unavailable'); return r.json(); })
      .then(data => data.images || {}).catch(() => {
        manifest = undefined; // Allow a later hover to retry a transient failure.
        return {};
      });
    return manifest;
  }
  const card = document.createElement('div');
  card.id = 'xrf-object-photo';
  card.setAttribute('role', 'tooltip');
  card.style.cssText = 'display:none;position:fixed;z-index:10000;pointer-events:none;width:190px;padding:12px;background:#111722;color:#f1f5f9;border:1px solid #3a506f;border-radius:14px;box-shadow:0 12px 36px #0008;font:13px system-ui,sans-serif';
  const title = document.createElement('strong');
  const detail = document.createElement('div');
  detail.style.cssText = 'font-size:11px;color:#93a4b8;margin:5px 0 8px';
  const img = document.createElement('img');
  img.style.cssText = 'display:none;width:190px;height:150px;object-fit:contain;background:#fff;border-radius:8px';
  const status = document.createElement('div');
  status.style.cssText = 'color:#93a4b8;font-size:12px';
  card.append(title, detail, img, status);
  document.body.appendChild(card);
  let pointer = {x: 0, y: 0}, token = 0;
  function position() {
    const rect = card.getBoundingClientRect();
    let left = pointer.x + 24, top = pointer.y + 24;
    if (left + rect.width > innerWidth - 8) left = pointer.x - rect.width - 24;
    if (top + rect.height > innerHeight - 8) top = pointer.y - rect.height - 24;
    card.style.left = Math.max(8, left) + 'px';
    card.style.top = Math.max(8, top) + 'px';
  }
  function hide() { token++; card.style.display = 'none'; img.removeAttribute('src'); }
  document.addEventListener('pointermove', e => {
    pointer = {x: e.clientX, y: e.clientY};
    if (card.style.display !== 'none') position();
  }, {passive: true});
  document.addEventListener('scroll', hide, true);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') hide(); });
  document.addEventListener('pointerdown', e => {
    if (e.composedPath().some(el => el.classList?.contains('bk-tab'))) hide();
  });
  async function show(event) {
    const point = event?.points?.[0];
    const type = point?.data?.type;
    // Summary boxes, heatmaps and histogram bins do not identify one object.
    if (!point || !['scatter', 'scattergl', 'violin'].includes(type)
        || !Number.isInteger(point.pointNumber)) { hide(); return; }
    const raw = point.customdata?.[0];
    if (raw === undefined || raw === null || raw === '') { hide(); return; }
    const number = Number(raw);
    if (!Number.isFinite(number) || number < 0) { hide(); return; }
    const id = String(Math.trunc(number));
    const current = ++token;
    // Short dwell avoids fetching photos while the pointer sweeps across points.
    await new Promise(resolve => setTimeout(resolve, 120));
    if (current !== token) return;
    const index = await getManifest();
    if (current !== token) return;
    title.textContent = 'Object ' + id;
    detail.textContent = Number.isInteger(number) ? 'Object photograph' : 'Measurement ID: ' + String(raw);
    img.style.display = 'none';
    img.removeAttribute('src');
    status.textContent = index[id] ? 'Loading photo…' : 'No photo available';
    card.style.display = 'block';
    position();
    if (!index[id]) return;
    img.alt = 'Photograph of object ' + id;
    img.onload = () => {
      if (current !== token) return;
      img.style.display = 'block'; status.textContent = ''; position();
    };
    img.onerror = () => {
      if (current !== token) return;
      img.style.display = 'none'; status.textContent = 'Photo could not be loaded'; position();
    };
    img.src = new URL(index[id], base).href;
  }
  const bound = new WeakSet();
  // Panel components use nested shadow roots. Discover plots without changing
  // their rendering lifecycle or invoking Plotly resize/relayout methods.
  const observed = new WeakSet();
  let scanQueued = false;
  const observer = new MutationObserver(() => {
    if (scanQueued) return;
    scanQueued = true;
    requestAnimationFrame(() => { scanQueued = false; discover(document); });
  });
  function discover(root) {
    if (!observed.has(root)) {
      observer.observe(root, {childList:true, subtree:true});
      observed.add(root);
    }
    function visit(element) {
      if (element.classList?.contains('js-plotly-plot') && typeof element.on === 'function' && !bound.has(element)) {
        bound.add(element);
        element.on('plotly_hover', show);
        element.on('plotly_unhover', hide);
        element.on('plotly_beforeplot', hide);
        element.addEventListener('pointerleave', hide);
      }
      // Never walk Plotly's thousands of SVG points when discovering widgets.
      if (element.classList?.contains('js-plotly-plot')) return;
      if (element.shadowRoot) discover(element.shadowRoot);
      for (const child of element.children || []) visit(child);
    }
    for (const element of root.children || []) visit(element);
  }
  discover(document);
  setInterval(() => discover(document), 1500);
})();

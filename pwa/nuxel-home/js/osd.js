// Nuxel OSD (A32, mission 12) — the visible volume/display indicator.
//
// /runtime/osd.json is published by the Nuxel hardware-button manager into the
// launcher's own docroot (the launcher's static server already serves it), so the
// OSD needs no extra service, no socket and no privileged API.  It renders a
// transient overlay for volume changes and for display state changes.
(function (global) {
  'use strict';
  var el = null, hideTimer = null, lastTs = 0;

  function ensure() {
    if (el) return el;
    el = document.createElement('div');
    el.id = 'nuxel-osd';
    el.style.cssText = [
      'position:fixed', 'left:50%', 'top:calc(var(--status-bar-height, 36px) + 18px)',
      'transform:translateX(-50%)', 'background:rgba(10,22,40,0.92)',
      'border:1px solid rgba(96,165,250,0.35)', 'border-radius:14px',
      'padding:10px 16px', 'min-width:132px', 'text-align:center', 'z-index:100000',
      'color:#e8f0ff', 'font:600 14px/1.35 -apple-system,system-ui,sans-serif',
      'box-shadow:0 10px 30px rgba(0,0,0,0.45)', 'opacity:0',
      'transition:opacity 180ms ease', 'pointer-events:none'
    ].join(';');
    document.body.appendChild(el);
    return el;
  }

  function show(kind, text, value, max) {
    var e = ensure();
    var label = kind === 'volume' ? 'Volume' : (kind === 'power' ? 'Power' : kind);
    e.innerHTML = '<div style="font-size:11px;letter-spacing:.06em;text-transform:uppercase;' +
                  'color:#9fd0ff">' + label + '</div>' +
                  '<div style="font-size:20px;font-weight:700">' + text + '</div>' +
                  (max ? ('<div style="height:4px;border-radius:2px;background:rgba(255,255,255,.15);margin-top:7px">' +
                          '<div style="height:4px;border-radius:2px;background:#3b82f6;width:' +
                          Math.max(0, Math.min(100, Math.round((value / max) * 100))) + '%"></div></div>') : '');
    e.style.opacity = '1';
    clearTimeout(hideTimer);
    hideTimer = setTimeout(function () { e.style.opacity = '0'; }, 1800);
  }

  var interval = 1500, timer = null;
  function schedule() { clearTimeout(timer); timer = setTimeout(poll, interval); }
  function poll() {
    fetch('/runtime/osd.json', { cache: 'no-store' })
      .then(function (r) {
        if (r.status === 404) { interval = Math.min(interval * 2, 10000); return null; }  // no publisher yet
        interval = 1500;
        return r.ok ? r.json() : null;
      })
      .then(function (j) {
        if (!j || !j.ts || j.ts === lastTs) return;
        lastTs = j.ts;
        show(j.kind || 'osd', j.text || '', j.value || 0, j.max || 0);
      })
      .catch(function () { /* stay silent */ })
      .then(schedule);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', schedule);
  else schedule();
  global.NuxelOSD = { show: show, poll: poll };
})(window);

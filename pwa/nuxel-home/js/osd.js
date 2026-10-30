// Nuxel OSD (A32, mission 12) — the visible volume/display indicator and the
// A34 power menu.
//
// /runtime/osd.json is published by the Nuxel hardware-button manager into the
// launcher's own docroot (the launcher's static server already serves it), so
// the OSD needs no extra service, no socket and no privileged API.  It renders
// a transient overlay for volume changes and for display state changes, and a
// persistent, selectable power menu while `kind:"power-menu"` carries entries.
//
// A34 TOUCHDOWN: the power menu used to be published with entries/index but
// this file ignored both, so a long press only produced a tiny empty box that
// vanished after 1.8 s.  The owner test correctly reported "the menu did
// nothing".  The entries are rendered here, the selected row follows the
// hardware Volume keys, and tapping a row selects it through the SAME button
// control FIFO the keys use (NuxelHost.action -> nuxel-button-manager).
(function (global) {
  'use strict';
  var el = null, hideTimer = null, lastTs = 0;
  var menu = null, menuKey = '';
  var interval = 1500, timer = null;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function hostAction(action) {
    try {
      if (global.NuxelHost && global.NuxelHost.available && global.NuxelHost.action) {
        global.NuxelHost.action(action);
      }
    } catch (e) { /* no host (VM/desktop): the menu stays read-only */ }
  }

  function ensure() {
    if (el) return el;
    el = document.createElement('div');
    el.id = 'nuxel-osd';
    el.style.cssText = [
      'position:fixed', 'left:50%', 'top:calc(var(--status-bar-height, 36px) + 18px)',
      'transform:translateX(-50%)', 'background:rgba(10,22,40,0.92)',
      'border:1px solid rgba(96,165,250,0.35)', 'border-radius:14px',
      'padding:10px 16px', 'min-width:132px', 'max-width:86vw', 'text-align:center', 'z-index:100001',
      'color:#e8f0ff', 'font:600 14px/1.35 -apple-system,system-ui,sans-serif',
      'box-shadow:0 2px 4px rgba(0,0,0,0.45)', 'opacity:0',
      'transition:opacity 180ms ease', 'pointer-events:none'
    ].join(';');
    document.body.appendChild(el);
    return el;
  }

  function show(kind, text, value, max, holdMs) {
    var e = ensure();
    var label = kind === 'volume' ? 'Volume' : (kind === 'power' ? 'Power' : kind);
    e.innerHTML = '<div style="font-size:11px;letter-spacing:.06em;text-transform:uppercase;' +
                  'color:#9fd0ff">' + esc(label) + '</div>' +
                  '<div style="font-size:20px;font-weight:700">' + esc(text) + '</div>' +
                  (max ? ('<div style="height:4px;border-radius:2px;background:rgba(255,255,255,.15);margin-top:7px">' +
                          '<div style="height:4px;border-radius:2px;background:#3b82f6;width:' +
                          Math.max(0, Math.min(100, Math.round((value / max) * 100))) + '%"></div></div>') : '');
    e.style.opacity = '1';
    clearTimeout(hideTimer);
    hideTimer = setTimeout(function () { e.style.opacity = '0'; }, holdMs || 1800);
  }

  function hideMenu() {
    if (menu) menu.style.display = 'none';
    menuKey = '';
    interval = 1500;
  }

  function ensureMenu() {
    if (menu) return menu;
    menu = document.createElement('div');
    menu.id = 'nuxel-power-menu';
    menu.setAttribute('role', 'dialog');
    menu.setAttribute('aria-label', 'Power menu');
    menu.style.cssText = [
      'position:fixed', 'left:0', 'right:0', 'top:0', 'bottom:0', 'z-index:100001',
      'display:none', 'background:rgba(2,6,14,0.62)',
      'font:14px/1.35 -apple-system,system-ui,sans-serif', 'color:#e8f0ff'
    ].join(';');
    menu.addEventListener('click', function (ev) {
      // Tap outside the card = Cancel/close, exactly like the first menu entry.
      if (ev.target === menu) hostAction('menu-close');
    });
    document.body.appendChild(menu);
    return menu;
  }

  function renderMenu(j) {
    var m = ensureMenu();
    var entries = j.entries || [];
    var idx = (typeof j.index === 'number') ? j.index : 0;
    var key = j.ts + ':' + idx + ':' + entries.length + ':' +
              (j.text || '') + ':' + entries.map(function (x) { return x.id + (x.allowed ? '1' : '0'); }).join(',');
    if (key === menuKey) { m.style.display = 'block'; return; }
    menuKey = key;

    var html = '<div id="nuxel-power-card" style="position:absolute;left:50%;top:50%;' +
      'transform:translate(-50%,-50%);min-width:250px;max-width:86vw;' +
      'background:rgba(12,22,38,0.98);border:1px solid rgba(96,165,250,.35);' +
      'border-radius:18px;box-shadow:0 2px 4px rgba(0,0,0,.6);overflow:hidden">' +
      '<div style="padding:14px 16px 10px;font-size:12px;letter-spacing:.08em;' +
      'text-transform:uppercase;color:#9fd0ff;border-bottom:1px solid rgba(96,165,250,.18)">Power</div>' +
      /* The merged 15-entry menu is taller than the panel on small screens;
       * the card scrolls, and the selected row is scrolled into view below. */
      '<div style="padding:8px;max-height:62vh;overflow-y:auto">';
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i] || {};
      var sel = (i === idx);
      html += '<div data-idx="' + i + '" role="button" tabindex="0" style="' +
        'display:flex;align-items:center;justify-content:space-between;gap:10px;' +
        'padding:11px 12px;margin:2px 0;border-radius:11px;cursor:pointer;' +
        (sel ? 'background:#1d4ed8;color:#fff;' : 'background:transparent;color:#dbeafe;') +
        '">' +
        '<span>' + esc(e.label || e.id || ('Entry ' + i)) + '</span>' +
        (e.allowed === false ? '<span style="font-size:11px;color:#fca5a5">gated</span>' :
          (sel ? '<span style="font-size:11px;opacity:.85">selected</span>' : '')) +
        '</div>';
    }
    html += '</div><div style="padding:9px 14px 12px;font-size:11px;color:#93a7c4;' +
      'border-top:1px solid rgba(96,165,250,.14)">' +
      'Volume Up/Down to move &middot; short Power to choose &middot; tap an entry</div></div>';
    m.innerHTML = html;
    m.style.display = 'block';
    interval = 500;   // follow hardware navigation quickly

    var rows = m.querySelectorAll('[data-idx]');
    for (var k = 0; k < rows.length; k++) {
      (function (ix, row) {
        row.addEventListener('click', function (ev) {
          ev.stopPropagation();
          // Ask the manager to select this exact row (it owns the FSM index).
          hostAction('menu-select ' + ix);
        });
      })(parseInt(rows[k].getAttribute('data-idx'), 10), rows[k]);
    }
    /* Keep the highlighted row visible without moving the whole page. */
    var selRow = rows[idx];
    if (selRow && selRow.scrollIntoView) {
      try { selRow.scrollIntoView({ block: 'nearest' }); } catch (e) { /* old WebKit */ }
    }
  }

  function schedule() { clearTimeout(timer); timer = setTimeout(poll, interval); }
  function poll() {
    fetch('/runtime/osd.json', { cache: 'no-store' })
      .then(function (r) {
        if (r.status === 404) { interval = Math.min(interval * 2, 10000); return null; }  // no publisher yet
        return r.ok ? r.json() : null;
      })
      .then(function (j) {
        if (!j || !j.ts) return;
        if (j.kind === 'power-menu') {
          if (j.entries && j.entries.length) {
            renderMenu(j);
            lastTs = j.ts;
          } else {
            hideMenu();
            if (j.ts !== lastTs) {
              lastTs = j.ts;
              // A refusal reason is shown as a full-width OSD line, not hidden.
              if (j.text) show('power', j.text, 0, 0, 7000);
            }
          }
          return;
        }
        hideMenu();
        if (j.ts === lastTs) return;
        lastTs = j.ts;
        show(j.kind || 'osd', j.text || '', j.value || 0, j.max || 0);
      })
      .catch(function () { /* stay silent */ })
      .then(schedule);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', schedule);
  else schedule();
  global.NuxelOSD = { show: show, poll: poll, hideMenu: hideMenu };
})(window);

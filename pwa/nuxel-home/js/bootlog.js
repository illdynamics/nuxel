// Nuxel Boot Log overlay (A33, briq-02b) — the on-glass half of verbose boot.
//
// WHY
//   The handset has no usable kernel console on this kernel (# CONFIG_DRM is not
//   set, Plymouth cannot run, fbcon is not the owner of the panel - nuxel-wl-fb
//   is).  When verbose boot is enabled the operator therefore needs the Nuxel
//   boot evidence ON THE GLASS, not only over a USB console: this overlay shows
//   the boot-stage markers the services publish, in the same order the live group
//   greps them out of dmesg.
//
// CONTRACT
//   * Only shown when verbose boot is EFFECTIVE for this boot.  The decision is
//     read from /run/nuxel/verbose-boot (published by nuxel-verbose-boot.service);
//     when the host cannot read it the local durable setting from
//     NuxelSettings ('verbose-boot') is the fallback, so the VM/desktop build
//     behaves the same way.
//   * Never blocks the launcher: no host => the overlay is not shown at all
//     (there is nothing to show on a machine that has no boot services).
//   * Read-only: it calls NuxelHost.statusRead/configGet only.  It writes nothing.
//   * Dismissible and self-hiding: a boot log that cannot be closed is a bug.
//
// The overlay is built entirely from JS (no index.html markup) and injects its
// own styles, so the launcher's own layout, safe zones and the VM screenshot
// parity surface are untouched when verbose boot is off (the default).
(function (global) {
  'use strict';

  var REFRESH_MS = 2000;
  var AUTOHIDE_MS = 30000;
  var STATE_NAME = 'verbose-boot-state';
  var LOG_NAME = 'boot-stage-log';
  var SOURCES = [
    ['boot-stage-log', 'Nuxel boot stage log'],
    ['verbose-boot-state', 'verbose-boot decision'],
    ['fb-owner', 'framebuffer ownership (single owner)'],
    ['anim-handoff', 'animation handoff receipt'],
    ['anim-state', 'animation state'],
    ['launcher-state', 'launcher markers'],
    ['display-state', 'display state']
  ];

  var el = null, bodyEl = null, footEl = null, timer = null, hideTimer = null;
  var visible = false;

  function host() {
    var h = global.NuxelHost;
    return (h && h.available) ? h : null;
  }

  function read(name) {
    var h = host();
    if (!h) return Promise.resolve({ ok: false, offline: true });
    return h.statusRead(name).then(function (res) { return res || { ok: false }; },
                                   function () { return { ok: false }; });
  }

  function diag(line) {
    try {
      if (global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag) {
        global.webkit.messageHandlers.nuxelDiag.postMessage(line);
      } else if (global.console && global.console.log) {
        global.console.log('[bootlog] ' + line);
      }
    } catch (e) {}
  }

  function ensureStyle() {
    if (document.getElementById('nuxel-bootlog-css')) return;
    var st = document.createElement('style');
    st.id = 'nuxel-bootlog-css';
    st.textContent = [
      '#nuxel-bootlog{position:fixed;left:8px;right:8px;top:calc(env(safe-area-inset-top,0px) + 34px);',
      'bottom:calc(env(safe-area-inset-bottom,0px) + 12px);z-index:9000;display:flex;flex-direction:column;',
      'background:rgba(6,12,20,.94);border:1px solid #33e0ff55;border-radius:12px;',
      'box-shadow:0 2px 4px #000c;color:#cfe9ff;font:12px/1.45 ui-monospace,monospace;overflow:hidden}',
      '#nuxel-bootlog[hidden]{display:none}',
      '.nuxel-bootlog-hd{display:flex;align-items:center;gap:8px;padding:8px 10px;background:#0d1b2a;',
      'border-bottom:1px solid #33e0ff33}',
      '.nuxel-bootlog-hd b{font:600 12px/1.2 system-ui,sans-serif;color:#7fe3ff;letter-spacing:.04em}',
      '.nuxel-bootlog-hd span{font:11px/1.2 system-ui,sans-serif;color:#8ea9c0}',
      '.nuxel-bootlog-btn{margin-left:auto;background:#12324a;color:#bfe9ff;border:1px solid #33e0ff55;',
      'border-radius:8px;padding:4px 10px;font:11px system-ui,sans-serif;cursor:pointer}',
      '.nuxel-bootlog-btn+ .nuxel-bootlog-btn{margin-left:6px}',
      '.nuxel-bootlog-body{flex:1;overflow:auto;padding:8px 10px;white-space:pre-wrap;word-break:break-word}',
      '.nuxel-bootlog-body h4{margin:8px 0 2px;font:600 11px system-ui,sans-serif;color:#68d6a8;letter-spacing:.05em}',
      '.nuxel-bootlog-body .miss{color:#e0a34a}',
      '.nuxel-bootlog-ft{padding:6px 10px;border-top:1px solid #33e0ff33;font:11px system-ui,sans-serif;color:#8ea9c0}'
    ].join('');
    document.head.appendChild(st);
  }

  function build() {
    if (el) return el;
    ensureStyle();
    el = document.createElement('div');
    el.id = 'nuxel-bootlog';
    el.hidden = true;
    el.setAttribute('role', 'log');
    el.setAttribute('aria-label', 'Nuxel verbose boot log');
    var hd = document.createElement('div');
    hd.className = 'nuxel-bootlog-hd';
    hd.innerHTML = '<b>NUXEL VERBOSE BOOT</b><span id="nuxel-bootlog-src">reading…</span>';
    var hide = document.createElement('button');
    hide.className = 'nuxel-bootlog-btn';
    hide.textContent = 'Hide';
    hide.addEventListener('click', function () { close('user'); });
    var keep = document.createElement('button');
    keep.className = 'nuxel-bootlog-btn';
    keep.textContent = 'Keep open';
    keep.addEventListener('click', function () {
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; keep.textContent = 'Auto-hide'; }
      else { armAutoHide(); keep.textContent = 'Keep open'; }
    });
    hd.appendChild(keep); hd.appendChild(hide);
    bodyEl = document.createElement('div');
    bodyEl.className = 'nuxel-bootlog-body';
    footEl = document.createElement('div');
    footEl.className = 'nuxel-bootlog-ft';
    footEl.textContent = 'read-only view of /run/nuxel/* and /var/lib/nuxel/* through NuxelHost';
    el.appendChild(hd); el.appendChild(bodyEl); el.appendChild(footEl);
    document.body.appendChild(el);
    return el;
  }

  function armAutoHide() {
    if (hideTimer) clearTimeout(hideTimer);
    hideTimer = setTimeout(function () { close('auto'); }, AUTOHIDE_MS);
  }

  function close(why) {
    if (!el || !visible) return;
    visible = false;
    el.hidden = true;
    if (timer) { clearInterval(timer); timer = null; }
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
    diag('BOOTLOG_HIDDEN why=' + why);
  }

  function render(blocks, srcLabel) {
    var out = [];
    blocks.forEach(function (b) {
      out.push('<h4>' + b.title + '</h4>');
      if (b.text) out.push(escapeHtml(b.text.trim()));
      else out.push('<span class="miss">(no data — ' + escapeHtml(b.name) + ' not published)</span>');
    });
    bodyEl.innerHTML = out.join('\n');
    var src = document.getElementById('nuxel-bootlog-src');
    if (src) src.textContent = srcLabel;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c];
    });
  }

  function refresh() {
    var jobs = SOURCES.map(function (s) {
      return read(s[0]).then(function (res) {
        return { name: s[0], title: s[1], text: (res && res.ok && res.text) ? res.text : null };
      });
    });
    return Promise.all(jobs).then(function (blocks) {
      var stb = blocks.filter(function (b) { return b.name === 'verbose-boot-state'; })[0] || {};
      var st = null;
      try { st = JSON.parse(stb.text || '{}'); } catch (e) { st = null; }
      var srcLabel = 'effective=' + (st && st.EFFECTIVE !== undefined ? st.EFFECTIVE : '?') +
                     ' source=' + (st && st.SOURCE ? st.SOURCE : '?') +
                     ' override=' + (st && st.OVERRIDE_CAPABILITY ? st.OVERRIDE_CAPABILITY : '?');
      render(blocks, srcLabel);
      return blocks;
    });
  }

  function effectiveState() {
    // Prefer the live boot-stage decision; fall back to the durable setting.
    return read(STATE_NAME).then(function (res) {
      if (res && res.ok && res.text && /EFFECTIVE=1/.test(res.text)) {
        return { show: true, why: 'host:/run/nuxel/verbose-boot' };
      }
      if (res && res.ok && res.text && /EFFECTIVE=0/.test(res.text)) {
        return { show: false, why: 'host:EFFECTIVE=0' };
      }
      var local = (global.NuxelSettings && global.NuxelSettings.verboseBoot)
        ? global.NuxelSettings.verboseBoot() : false;
      return { show: !!local, why: local ? 'durable-setting' : 'off' };
    }, function () { return { show: false, why: 'no-host' }; });
  }

  function show() {
    if (!host()) { diag('BOOTLOG_SKIPPED no_host'); return Promise.resolve(false); }
    build();
    el.hidden = false;
    visible = true;
    armAutoHide();
    return refresh().then(function (blocks) {
      var shown = blocks.filter(function (b) { return b.text; }).length;
      diag('BOOTLOG_SHOWN blocks=' + shown + '/' + blocks.length);
      if (!timer) timer = setInterval(function () { refresh(); }, REFRESH_MS);
      return true;
    });
  }

  function init() {
    effectiveState().then(function (verdict) {
      diag('BOOTLOG_VERDICT show=' + (verdict.show ? 1 : 0) + ' why=' + verdict.why);
      if (verdict.show) return show();
      return false;
    });
  }

  global.NuxelBootLog = {
    init: init,
    show: show,
    hide: function () { close('api'); },
    refresh: refresh,
    visible: function () { return visible; },
    sources: function () { return SOURCES.map(function (s) { return s[0]; }); },
    autoHideMs: AUTOHIDE_MS,
    refreshMs: REFRESH_MS
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);

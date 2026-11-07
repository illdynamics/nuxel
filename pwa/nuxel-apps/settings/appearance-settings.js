/* Nuxel Settings — system appearance (PWNAGE-81000).
 * The bridge applies gsettings color-scheme + GTK theme as the session user and
 * writes per-user GTK3/GTK4 settings.ini.  This page never sets GTK_THEME in a
 * process environment and never claims that non-GTK toolkits are themed.
 */
(function () {
  'use strict';
  function $(id) { return document.getElementById(id); }
  function bridge() {
    if (window.NuxelBridge && typeof window.NuxelBridge.call === 'function') return window.NuxelBridge;
    try {
      if (window.parent && window.parent !== window && window.parent.NuxelBridge &&
          typeof window.parent.NuxelBridge.call === 'function') return window.parent.NuxelBridge;
    } catch (e) {}
    return null;
  }
  function call(verb, params) {
    var b = bridge();
    if (!b) return Promise.resolve({ success: false, error: 'Nuxel bridge unavailable' });
    try { return Promise.resolve(b.call('appearance', verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, error: String(e && e.message || e) }); }
  }
  function text(id, value) { var e = $(id); if (e) e.textContent = value; }
  function applyShell(mode) {
    try {
      document.documentElement.setAttribute('data-appearance', mode || 'system');
      localStorage.setItem('nuxel.appearance', mode || 'system');
    } catch (e) {}
    try {
      if (window.parent && window.parent !== window && window.parent.document) {
        window.parent.document.documentElement.setAttribute('data-appearance', mode || 'system');
        try { window.parent.localStorage.setItem('nuxel.appearance', mode || 'system'); } catch (e) {}
      }
    } catch (e) {}
    try { window.dispatchEvent(new CustomEvent('nuxel:appearance-changed', { detail: { mode: mode } })); } catch (e) {}
  }
  function render(doc) {
    if (!doc || doc.success === false) {
      text('appearance-state', 'Appearance provider unavailable: ' + ((doc && (doc.error || doc.detail)) || 'unknown error'));
      return;
    }
    var mode = doc.mode || 'system';
    var theme = doc.gtk_theme || 'Adwaita';
    var m = $('appearance-mode'), t = $('appearance-theme');
    if (m) m.value = mode;
    if (t) t.value = theme === 'Adwaita-dark' ? 'Adwaita-dark' : 'Adwaita';
    applyShell(mode);
    var rb = doc.readback || {};
    var portal = doc.portal || {};
    var exts = doc.flatpak_theme_extensions || [];
    text('appearance-state',
      'mode           : ' + mode + '\n' +
      'GTK theme      : ' + theme + '\n' +
      'color-scheme   : ' + (rb.color_scheme || 'not reported') + '\n' +
      'gtk-theme read : ' + (rb.gtk_theme || 'not reported') + '\n' +
      'portal settings: ' + (portal.available ? 'available' : 'not available') + '\n' +
      'Flatpak themes : ' + (exts.length ? exts.join(' | ') : 'none detected'));
    text('appearance-detail',
      'Native GTK3/GTK4 and libadwaita apps read the color-scheme setting. Flatpak GTK apps use the ' +
      'portal and the matching Flatpak theme extension; Electron/Qt apps that implement their own themes ' +
      'are not claimed to follow this switch.');
  }
  function refresh() {
    text('appearance-state', 'Reading appearance providers…');
    return call('get', {}).then(render).catch(function (e) {
      text('appearance-state', 'Appearance error: ' + (e && e.message ? e.message : e));
    });
  }
  function apply() {
    var mode = ($('appearance-mode') || {}).value || 'system';
    var theme = ($('appearance-theme') || {}).value || 'Adwaita';
    if (mode === 'dark' && theme === 'Adwaita') theme = 'Adwaita-dark';
    if (mode === 'light') theme = 'Adwaita';
    text('appearance-state', 'Applying ' + mode + ' / ' + theme + '…');
    return call('set', { mode: mode, gtk_theme: theme }).then(function (r) {
      render(r);
      if (r && r.success !== false) {
        text('appearance-detail', 'Applied and persisted. Verify an open GTK/libadwaita app and a Flatpak app; ' +
          'non-GTK toolkits may still use their own theme.');
      }
      return r;
    });
  }
  function motionApply(mode) {
    if (window.NuxelTheme && typeof window.NuxelTheme.applyMotion === 'function') {
      window.NuxelTheme.applyMotion(mode);
    } else {
      try {
        document.documentElement.setAttribute('data-motion', mode || 'system');
        localStorage.setItem('nuxel.motion', mode || 'system');
      } catch (e) {}
    }
    try {
      if (window.parent && window.parent !== window && window.parent.document) {
        window.parent.document.documentElement.setAttribute('data-motion', mode || 'system');
        try { window.parent.localStorage.setItem('nuxel.motion', mode || 'system'); } catch (e) {}
      }
    } catch (e) {}
    text('motion-state', mode === 'off' ? 'Motion off (near-instant).'
      : mode === 'reduced' ? 'Reduced motion (essential feedback only).'
      : mode === 'full' ? 'Full subtle motion.'
      : 'Following the system reduced-motion preference.');
  }
  function motionInit() {
    var pick = $('motion-mode');
    if (!pick) return;
    var cur = 'system';
    try {
      cur = (window.NuxelTheme && window.NuxelTheme.motion) ? window.NuxelTheme.motion()
        : (localStorage.getItem('nuxel.motion') || 'system');
    } catch (e) {}
    pick.value = cur;
    motionApply(cur);
    pick.addEventListener('change', function () { motionApply(pick.value); });
  }
  function bind() {
    var a = $('appearance-apply'); if (a) a.addEventListener('click', apply);
    var r = $('appearance-refresh'); if (r) r.addEventListener('click', refresh);
    document.querySelectorAll('.tab').forEach(function (tab) {
      if (tab.dataset.tab === 'theme') tab.addEventListener('click', refresh);
    });
    motionInit();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { bind(); refresh(); });
  else { bind(); refresh(); }
  window.nuxelAppearanceSettings = { refresh: refresh, apply: apply, motion: motionApply };
})();

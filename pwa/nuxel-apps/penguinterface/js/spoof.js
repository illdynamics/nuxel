/* PenguInterface spoof panel (PWNAGE-88000).
 *
 * Shows the real current user agent, real os-release/uname, and applies an
 * app-scoped spoof through the bridge `spoof` namespace.  Reset removes every
 * spoof and verifies the underlying system is unchanged.  Nothing here touches
 * credentials or writes outside /run/nuxel/spoof.
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
    if (!b) return Promise.resolve({ success: false, error: 'Nuxel bridge unavailable', offline: true });
    try { return Promise.resolve(b.call('spoof', verb, params || {})); }
    catch (e) { return Promise.resolve({ success: false, error: String(e && e.message || e) }); }
  }
  function toast(msg) {
    var el = $('spoof-toast');
    if (!el) return;
    el.textContent = msg;
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { el.textContent = ''; }, 3200);
  }
  function render(state) {
    $('spoof-ua-current').textContent = navigator.userAgent || 'unavailable';
    var r = state.real || {};
    $('spoof-real-uname').textContent = r.uname || 'unavailable';
    var os = r.os_release || {};
    $('spoof-real-os').textContent = (os.NAME || 'unavailable') + ' ' + (os.VERSION_ID || '') +
      (os.error ? ' (' + os.error + ')' : '');
    $('spoof-lib').textContent = state.lib ? 'aarch64 libnuxel-spoof.so present' : 'libnuxel-spoof.so not built/deployed';
    if (state.enabled) {
      $('spoof-status').textContent = 'spoof active' +
        (state.targets && state.targets.length ? ' for: ' + state.targets.join(', ') : '');
    } else {
      $('spoof-status').textContent = 'no spoof active';
    }
  }
  function refresh() {
    call('status', {}).then(function (r) {
      if (r && r.success !== false) render(r.spoof || {});
      else toast((r && (r.detail || r.error)) || 'spoof status failed');
    });
  }
  function apply() {
    var uname = {
      sysname: $('spoof-uname-sysname').value.trim() || 'Linux',
      nodename: $('spoof-uname-nodename').value.trim() || 'nuxel-spoof',
      release: $('spoof-uname-release').value.trim() || '6.1.0-nuxel-spoof',
      version: $('spoof-uname-version').value.trim() || '#1 SMP PREEMPT_DYNAMIC',
      machine: $('spoof-uname-machine').value.trim() || 'aarch64'
    };
    call('set', {
      enabled: true,
      ua: $('spoof-ua-input').value.trim(),
      targets: ($('spoof-targets').value || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean),
      os_release_text: $('spoof-os-release').value,
      uname: uname
    }).then(function (r) {
      if (r && r.success !== false) { render(r.spoof || {}); toast('Spoof applied (app-scoped only).'); }
      else toast((r && (r.detail || r.error)) || 'apply failed');
    });
  }
  function reset() {
    call('reset', {}).then(function (r) {
      if (r && r.success !== false) {
        toast('All spoofs removed. Real identity verified unchanged.');
        $('spoof-os-release').value = '';
        $('spoof-ua-input').value = '';
        refresh();
      } else toast((r && (r.detail || r.error)) || 'reset failed');
    });
  }
  document.addEventListener('DOMContentLoaded', function () {
    $('spoof-apply').addEventListener('click', apply);
    $('spoof-reset').addEventListener('click', reset);
    $('spoof-refresh').addEventListener('click', refresh);
    refresh();
  });
}());

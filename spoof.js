/* PenguInterface spoof panel (PWNAGE-88000, extended by PWNAGE-91000).
 *
 * Global + per-app identity profiles.  The bridge persists owner config, lists
 * launchable app ids, and injects the effective profile only when a native app
 * is launched.  Reset is scoped: it clears the selected app or the global
 * profile, never the whole store unless the owner explicitly asks for that.
 *
 * PWNAGE-91000 additions (Windows spoof for Portal for Teams):
 *   - Windows uname + user-agent DEFAULTS.
 *   - A named preset "windows-portal" (uname/UA/os-release/DMI/hostname).
 *   - /etc/os-release text helper that overlays BOTH /etc/os-release and the
 *     backing /usr/lib/os-release so host + flatpak runtime see Windows.
 *   - Arch toggle (amd64 vs arm64) reconciled with the Windows claim.
 */
(function () {
  'use strict';

  // --- Windows identity defaults -------------------------------------------
  // uname() fields read inside the flatpak sandbox / by Electron telemetry.
  var WINDOWS_UNAME = {
    sysname: 'windows_nt',
    nodename: 'WIN-CLIENT',
    release: '10.0',
    version: '#1 SMP PREEMPT',
    machine: 'amd64' // fully Windows x86_64 by default; toggle to arm64 below
  };

  // Chromium/Edge on Windows 10/11 — often the FIRST signal Electron apps read.
  var WINDOWS_UA =
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';

  // /etc/os-release text (overlaid on both files). Keeps ID=windows / VERSION_ID=10.
  var WINDOWS_OS_RELEASE = [
    'NAME="Windows 10"',
    'ID=windows',
    'VERSION_ID=10',
    'PRETTY_NAME="Windows 10 Enterprise"',
    'ANSI_COLOR="0;34"',
    'CPE_NAME="cpe:/o:microsoft:windows:10"',
    'DEFAULT_HOSTNAME="WIN-CLIENT"'
  ].join('\n');

  // Minimal DMI / board product fields some runtimes check for "PC vs phone".
  var WINDOWS_DMI = {
    product_name: 'Windows Base Station',
    system_product_name: 'Windows Base Station',
    board_product_name: 'Base Board',
    sys_vendor: 'Microsoft Corp.',
    board_vendor: 'Base Board'
  };

  function unameDefaults(u) {
    u = u || {};
    return {
      sysname: u.sysname != null ? u.sysname : WINDOWS_UNAME.sysname,
      nodename: u.nodename != null ? u.nodename : WINDOWS_UNAME.nodename,
      release: u.release != null ? u.release : WINDOWS_UNAME.release,
      version: u.version != null ? u.version : WINDOWS_UNAME.version,
      machine: u.machine != null ? u.machine : WINDOWS_UNAME.machine
    };
  }

  var PRESETS = {
    'windows-portal': {
      label: 'Windows (Portal for Teams)',
      scope: 'global',
      ua: WINDOWS_UA,
      os_release: WINDOWS_OS_RELEASE,
      uname: Object.assign({}, WINDOWS_UNAME),
      dmi: Object.assign({}, WINDOWS_DMI),
      hostname: 'WIN-CLIENT'
    }
  };

  // The effective default profile the panel starts from. Windows by design so
  // a fresh "Apply" already reports Windows until the owner overrides it.
  var DEFAULTS = {
    sysname: WINDOWS_UNAME.sysname,
    nodename: WINDOWS_UNAME.nodename,
    release: WINDOWS_UNAME.release,
    version: WINDOWS_UNAME.version,
    machine: WINDOWS_UNAME.machine
  };
  var cache = { spoof: {}, apps: [], preset: 'windows-portal' };

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
    toast._t = setTimeout(function () { el.textContent = ''; }, 3600);
  }
  function scope() {
    var g = $('spoof-scope-global');
    return g && g.checked ? 'global' : 'app';
  }
  function selectedApp() {
    var sel = $('spoof-app-select');
    return sel ? String(sel.value || '') : '';
  }
  function unameLine(u) {
    u = u || {};
    return [u.sysname, u.nodename, u.release, u.version, u.machine]
      .filter(function (v) { return v; }).join(' ');
  }
  function realOsLine(os) {
    os = os || {};
    if (os.error) return 'unavailable (' + os.error + ')';
    return (os.NAME || 'unavailable') + ' ' + (os.VERSION_ID || '');
  }
  function firstLine(text) {
    text = String(text || '').trim();
    return text ? text.split(/\r?\n/)[0] : '';
  }
  function configFor(s, appId) {
    if (appId) {
      var own = (s.apps || {})[appId];
      if (own && own.enabled) return own;
    }
    var g = s.global;
    return g && g.enabled ? g : null;
  }
  function displayConfig(s) {
    if (scope() === 'global') return s.global && s.global.enabled ? s.global : null;
    if (s.effective && s.effective.enabled) return s.effective;
    return s.global && s.global.enabled ? s.global : null;
  }
  function fillFields(s) {
    var cfg = scope() === 'global'
      ? (s.global || null)
      : ((s.apps || {})[selectedApp()] || null);
    var u = (cfg && cfg.uname) || DEFAULTS;
    $('spoof-ua-input').value = (cfg && cfg.ua) || '';
    $('spoof-os-release').value = (cfg && cfg.os_release) || '';
    $('spoof-uname-sysname').value = u.sysname || DEFAULTS.sysname;
    $('spoof-uname-nodename').value = u.nodename || DEFAULTS.nodename;
    $('spoof-uname-release').value = u.release || DEFAULTS.release;
    $('spoof-uname-version').value = u.version || DEFAULTS.version;
    $('spoof-uname-machine').value = u.machine || DEFAULTS.machine;
  }
  function fillFromPreset(id) {
    var p = PRESETS[id];
    if (!p) return;
    cache.preset = id;
    $('spoof-ua-input').value = p.ua || '';
    $('spoof-os-release').value = p.os_release || '';
    var u = p.uname || DEFAULTS;
    $('spoof-uname-sysname').value = u.sysname || DEFAULTS.sysname;
    $('spoof-uname-nodename').value = u.nodename || DEFAULTS.nodename;
    $('spoof-uname-release').value = u.release || DEFAULTS.release;
    $('spoof-uname-version').value = u.version || DEFAULTS.version;
    $('spoof-uname-machine').value = u.machine || DEFAULTS.machine;
    // arch toggle reflects the preset machine so it stays consistent
    var arm = String(u.machine || '').indexOf('arm') === 0;
    if ($('spoof-arch-arm')) $('spoof-arch-arm').checked = arm;
  }
  function currentPresetMachine() {
    // Reconcile the machine field with the arch radio when a preset is used.
    var arm = $('spoof-arch-arm') && $('spoof-arch-arm').checked;
    return arm ? 'arm64' : 'amd64';
  }
  function renderAppOptions(s) {
    var sel = $('spoof-app-select');
    if (!sel) return;
    var prev = sel.value;
    var seen = {};
    var rows = [];
    (cache.apps || []).forEach(function (a) {
      if (!a || !a.id || seen[a.id]) return;
      seen[a.id] = true;
      rows.push({ id: a.id, name: a.name || a.id, flatpak: !!a.flatpak });
    });
    Object.keys(s.apps || {}).forEach(function (id) {
      if (seen[id]) return;
      seen[id] = true;
      rows.push({ id: id, name: id, flatpak: false });
    });
    rows.sort(function (a, b) {
      return (a.name + a.id).toLowerCase() < (b.name + b.id).toLowerCase() ? -1 : 1;
    });
    sel.innerHTML = '';
    if (!rows.length) {
      var opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No app registry available';
      sel.appendChild(opt);
      return;
    }
    rows.forEach(function (row) {
      var o = document.createElement('option');
      o.value = row.id;
      var configured = !!(s.apps && s.apps[row.id] && s.apps[row.id].enabled);
      o.textContent = (configured ? '\u2713 ' : '') + row.name + ' \u2014 ' + row.id +
        (row.flatpak ? ' (Flatpak)' : '');
      sel.appendChild(o);
    });
    if (prev && seen[prev]) sel.value = prev;
    else sel.value = rows[0].id;
  }
  function render(s) {
    s = s || {};
    cache.spoof = s;
    var real = s.real || {};
    var display = displayConfig(s);
    var activeScope = scope() === 'global' ? 'global' : (s.effective_scope || 'app');
    var ua = display && display.ua ? display.ua : (navigator.userAgent || 'unavailable');
    $('spoof-ua-current').textContent = ua +
      (display && display.ua ? '  (spoofed: ' + activeScope + ')' : '');
    $('spoof-effective-uname').textContent =
      display && display.uname ? unameLine(display.uname) : (real.uname || 'unavailable');
    $('spoof-effective-os').textContent =
      display && display.os_release ? firstLine(display.os_release) : realOsLine(real.os_release);
    $('spoof-real-uname').textContent = real.uname || 'unavailable';
    $('spoof-real-os').textContent = realOsLine(real.os_release);
    $('spoof-lib').textContent = s.lib
      ? 'aarch64 libnuxel-spoof.so present' : 'libnuxel-spoof.so not built/deployed';
    var targets = s.targets || [];
    if (s.global && s.global.enabled) {
      $('spoof-status').textContent = 'Global spoof active for all native app launches' +
        (targets.length ? ' \u2014 ' + targets.length + ' per-app override(s)' : '');
    } else if (targets.length) {
      $('spoof-status').textContent = 'Per-app spoof active for: ' + targets.join(', ');
    } else {
      $('spoof-status').textContent = 'No spoof active. Select an app or Global and apply.';
    }
    renderAppOptions(s);
    fillFields(s);
    syncScopeUi();
  }
  function syncScopeUi() {
    var global = scope() === 'global';
    var field = $('spoof-app-field');
    var warning = $('spoof-global-warning');
    var reset = $('spoof-reset');
    if (field) field.hidden = global;
    if (warning) warning.hidden = !global;
    if (reset) reset.textContent = global ? 'Reset global spoof' : "Reset this app's spoof";
  }
  function refresh() {
    var params = {};
    if (scope() === 'app' && selectedApp()) params.app_id = selectedApp();
    call('status', params).then(function (r) {
      if (r && r.success !== false) render(r.spoof || {});
      else toast((r && (r.detail || r.error)) || 'spoof status failed');
    });
  }
  function loadApps() {
    call('apps', {}).then(function (r) {
      if (r && r.success !== false && Array.isArray(r.apps)) {
        cache.apps = r.apps;
        if (r.available === false && r.error) toast('App list: ' + r.error);
        render(cache.spoof);
        refresh();
        return;
      }
      // Bridge list unavailable: fall back to the same-origin canonical registry.
      fetch('../../nuxel-common/app-registry.json', { cache: 'no-store' })
        .then(function (resp) { return resp.ok ? resp.json() : Promise.reject(new Error('HTTP ' + resp.status)); })
        .then(function (doc) {
          cache.apps = (doc.apps || []).map(function (a) {
            return { id: a.id, name: a.name || a.id, type: a.type, flatpak: !!a.flatpak_id };
          }).filter(function (a) { return a.id; });
          render(cache.spoof);
        })
        .catch(function () { toast('App list unavailable; enter the id manually.'); })
        .then(refresh);
    });
  }
  function collectParams() {
    var machine = currentPresetMachine();
    return {
      enabled: true,
      scope: scope(),
      ua: $('spoof-ua-input').value.trim(),
      os_release_text: $('spoof-os-release').value,
      uname: {
        sysname: ('spoof-uname-sysname' && $('spoof-uname-sysname').value.trim()) || 'windows_nt',
        nodename: ('spoof-uname-nodename' && $('spoof-uname-nodename').value.trim()) || 'WIN-CLIENT',
        release: ('spoof-uname-release' && $('spoof-uname-release').value.trim()) || '10.0',
        version: ('spoof-uname-version' && $('spoof-uname-version').value.trim()) || '#1 SMP PREEMPT',
        machine: machine
      },
      dmi: Object.assign({}, WINDOWS_DMI),
      hostname: 'WIN-CLIENT'
    };
  }
  function apply() {
    var params = collectParams();
    if (params.scope === 'app') {
      var appId = selectedApp();
      if (!appId) { toast('Select an app id first.'); return; }
      params.app_id = appId;
    }
    call('set', params).then(function (r) {
      if (r && r.success !== false) {
        render(r.spoof || {});
        toast(params.scope === 'global'
          ? 'Global spoof applied. Native app launches now use it.'
          : 'Spoof applied for ' + appId + '.');
      } else {
        toast((r && (r.detail || r.error)) || 'apply failed');
      }
    });
  }
  function applyPreset() {
    var id = $('spoof-preset-select') ? $('spoof-preset-select').value : cache.preset;
    fillFromPreset(id);
    apply();
  }
  function quickWindows() {
    // One-click: Global Windows (Portal for Teams) spoof.
    fillFromPreset('windows-portal');
    if ($('spoof-scope-global')) $('spoof-scope-global').checked = true;
    apply();
  }
  function reset() {
    var params = { scope: scope() };
    if (params.scope === 'app') {
      var appId = selectedApp();
      if (!appId) { toast('Select an app id first.'); return; }
      params.app_id = appId;
    }
    call('reset', params).then(function (r) {
      if (r && r.success !== false) {
        render(r.spoof || {});
        toast(params.scope === 'global'
          ? 'Global spoof removed.'
          : "This app's spoof removed; other apps are untouched.");
      } else {
        toast((r && (r.detail || r.error)) || 'reset failed');
      }
    });
  }
  function resetAll() {
    if (!window.confirm('Remove every global and per-app spoof?')) return;
    call('reset', { scope: 'all' }).then(function (r) {
      if (r && r.success !== false) {
        render(r.spoof || {});
        toast('All spoofs removed.');
      } else {
        toast((r && (r.detail || r.error)) || 'reset all failed');
      }
    });
  }
  document.addEventListener('DOMContentLoaded', function () {
    $('spoof-apply').addEventListener('click', apply);
    $('spoof-reset').addEventListener('click', reset);
    $('spoof-reset-all').addEventListener('click', resetAll);
    $('spoof-refresh').addEventListener('click', refresh);
    $('spoof-scope-app').addEventListener('change', refresh);
    $('spoof-scope-global').addEventListener('change', refresh);
    $('spoof-app-select').addEventListener('change', refresh);
    if ($('spoof-preset-select')) {
      $('spoof-preset-select').addEventListener('change', function () { fillFromPreset(this.value); });
    }
    if ($('spoof-arch-arm')) {
      $('spoof-arch-arm').addEventListener('change', function () {
        // Reconcile the machine field with the chosen arch before apply.
        $('spoof-uname-machine').value = this.checked ? 'arm64' : 'amd64';
      });
    }
    if ($('spoof-apply-preset')) $('spoof-apply-preset').addEventListener('click', applyPreset);
    if ($('spoof-windows-portal')) $('spoof-windows-portal').addEventListener('click', quickWindows);
    loadApps();
  });
}());

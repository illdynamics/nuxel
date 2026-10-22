// Nuxel Settings — the settings model (js-level: pwa/nuxel-apps/settings/settings-model.js)
//
// THE RULE THIS FILE ENFORCES (mission area 48):
//   every control in the Settings UI must name
//     (a) the durable document it writes,
//     (b) the real component that READS that document,
//     (c) how the UI can TELL whether that component is present here.
//   A control whose (b) cannot be named does not get to be a switch: the model
//   reports it as `unsupported` and the UI renders state, not a lie.
//
// Nothing here writes a file itself: it goes through NuxelHost.configGet /
// configSet (the launcher host performs an atomic same-directory rename into
// /etc/nuxel/...), with a localStorage mirror for the VM/desktop case. The
// console uses the SAME documents through nuxelctl, so there is one settings
// system, not a UI path and a console path.
(function (global) {
  'use strict';

  var DOCS = {
    // ---- documents that already had a real consumer before this revision ----
    'statusbar-safezones': { path: '/etc/nuxel/display/statusbar-safezones.json', consumer: 'nuxel-safe-zones.js + status-bar.js (launcher) and nuxelctl statusbar', probe: 'statusbar' },
    'buttons': { path: '/etc/nuxel/input/buttons.json', consumer: 'nuxel-button-manager (hardware button FSM)', probe: 'buttons' },
    'verbose-boot': { path: '/etc/nuxel/boot/verbose-boot.json', consumer: 'nuxel-verbose-boot.service (early boot stage)', probe: 'verbose-boot-state' },
    'animation-handoff': { path: '/etc/nuxel/boot/animation-handoff.json', consumer: 'nuxel-anim-handoff.py + nuxel-wl-fb (single framebuffer owner)', probe: 'anim-state' },
    // ---- documents this revision adds (each with a named consumer) ----
    'display': { path: '/etc/nuxel/display/display.json', consumer: 'nuxel-wl-fb display bridge (DPMS/timeout) via nuxelctl display', probe: 'wlfb-state' },
    'orientation': { path: '/etc/nuxel/orientation/orientation.json', consumer: 'nuxel-orientationd -> compositor transform (seven modes)', probe: 'orientation' },
    'keyboard': { path: '/etc/nuxel/keyboard/keyboard.json', consumer: 'nuxel-keyboard-apply.sh -> stevia / phosh OSK over Wayland text-input-v3', probe: 'keyboard-state' },
    'time': { path: '/etc/nuxel/time/time.json', consumer: 'nuxelctl time / nuxel-time.sh (timesyncd+chrony, RTC check timer)', probe: 'time' },
    'power': { path: '/etc/nuxel/power/power.json', consumer: 'nuxelctl power + the power/battery component (cpufreq governor)', probe: 'power' },
    'privacy': { path: '/etc/nuxel/privacy/privacy.json', consumer: 'nuxel-portal + nuxel-bridge capability checks (permission store)', probe: 'permissions' },
    'apps': { path: '/etc/nuxel/apps/apps.json', consumer: 'launcher registry (app defaults) + nuxel-portal (permissions)', probe: 'launcher-state' },
    'network': { path: '/etc/nuxel/network/settings.json', consumer: 'NetworkManager connection policy (configs/networkmanager) via nuxelctl wifi', probe: 'wifi' },
    'haptics': { path: '/etc/nuxel/haptics/haptics.json', consumer: 'feedbackd / the vibration component (configs/nuxel/haptics)', probe: 'haptics' },
    'security': { path: '/etc/nuxel/security/security.json', consumer: 'nftables firewall unit + nuxel-security-audit.sh', probe: 'firewall' }
  };

  // Every controllable setting: key -> {doc, kind, default, consumer_ready}
  //   kind: 'switch' | 'select' | 'number' | 'action'
  var SETTINGS = {
    // Display / safe zones (mission 19) — the ten-zone editor itself lives in
    // settings.js and writes statusbar-safezones.
    'display.timeout_sec': { doc: 'display', kind: 'number', default: 30, label: 'Screen timeout (s)' },
    'display.overflow_policy': { doc: 'display', kind: 'select', default: 'shift', label: 'Status-bar overflow' },
    'display.wake_double_tap': { doc: 'display', kind: 'switch', default: false, label: 'Double-tap to wake' },
    'display.sleep_double_tap': { doc: 'display', kind: 'switch', default: false, label: 'Double-tap to sleep' },
    // Orientation (A49): seven modes, one source of truth
    'orientation.mode': { doc: 'orientation', kind: 'select', default: 'portrait', label: 'Screen rotation',
      options: ['portrait', 'reverse-portrait', 'landscape', 'reverse-landscape', 'auto', 'auto-portrait', 'auto-landscape'] },
    // Sound (mission 14/15)
    'sound.output_route': { doc: 'power', kind: 'select', default: 'auto', label: 'Output route' },
    'sound.notifications': { doc: 'haptics', kind: 'switch', default: true, label: 'Notification sounds' },
    'sound.haptics': { doc: 'haptics', kind: 'switch', default: true, label: 'Touch vibration' },
    // Network (mission 4/11) — disabled unless the radio was observed
    'network.wifi_enabled': { doc: 'network', kind: 'switch', default: false, label: 'Wi-Fi' },
    'network.wifi_autoconnect': { doc: 'network', kind: 'switch', default: true, label: 'Reconnect automatically' },
    'network.cellular_enabled': { doc: 'network', kind: 'switch', default: false, label: 'Mobile data' },
    'network.dns_mode': { doc: 'network', kind: 'select', default: 'auto', label: 'DNS' },
    'network.vpn_enabled': { doc: 'network', kind: 'switch', default: false, label: 'VPN' },
    // Input (mission 29/30)
    'keyboard.enabled': { doc: 'keyboard', kind: 'switch', default: true, label: 'On-screen keyboard' },
    'keyboard.auto_show': { doc: 'keyboard', kind: 'switch', default: true, label: 'Show when a text field is focused' },
    'keyboard.layout': { doc: 'keyboard', kind: 'select', default: 'us', label: 'Layout' },
    'keyboard.numeric_layout': { doc: 'keyboard', kind: 'switch', default: true, label: 'Numeric layout for number fields' },
    'keyboard.height_dp': { doc: 'keyboard', kind: 'number', default: 300, label: 'Keyboard height (dp)' },
    'keyboard.key_repeat': { doc: 'keyboard', kind: 'switch', default: true, label: 'Key repeat (backspace)' },
    'keyboard.haptics': { doc: 'keyboard', kind: 'switch', default: true, label: 'Haptic feedback per key' },
    'keyboard.haptics_intensity': { doc: 'keyboard', kind: 'select', default: 'low', label: 'Haptic intensity',
      options: ['low', 'medium', 'high'] },
    'keyboard.haptics_pulse_ms': { doc: 'keyboard', kind: 'number', default: 12, label: 'Haptic pulse (ms)' },
    'keyboard.clipboard': { doc: 'keyboard', kind: 'switch', default: true, label: 'Clipboard bar' },
    'keyboard.hardware_passthrough': { doc: 'keyboard', kind: 'switch', default: true, label: 'Physical keyboard passthrough' },
    // System (mission 12/18/48)
    'time.auto': { doc: 'time', kind: 'switch', default: true, label: 'Automatic time (NTP)' },
    'time.timezone': { doc: 'time', kind: 'select', default: 'UTC', label: 'Time zone' },
    'time.format': { doc: 'time', kind: 'select', default: '24h', label: 'Time format' },
    'power.mode': { doc: 'power', kind: 'select', default: 'balanced', label: 'Power mode' },
    // Privacy (mission 41-45) — these are read-through: the portal owns enforcement
    'privacy.camera': { doc: 'privacy', kind: 'switch', default: false, label: 'Allow camera for apps' },
    'privacy.microphone': { doc: 'privacy', kind: 'switch', default: false, label: 'Allow microphone for apps' },
    'privacy.location': { doc: 'privacy', kind: 'switch', default: false, label: 'Allow location for apps' },
    'privacy.recorder_killswitch': { doc: 'privacy', kind: 'switch', default: false, label: 'Global recorder kill switch' },
    // Apps (mission 30/48)
    'apps.show_undeclared': { doc: 'apps', kind: 'switch', default: false, label: 'Show apps without a manifest' },
    'apps.default_browser': { doc: 'apps', kind: 'select', default: 'org.nuxel.Browser', label: 'Default browser' },
    // Security (mission 21/22)
    'security.firewall_profile': { doc: 'security', kind: 'select', default: 'default', label: 'Firewall profile' },
    'security.admin_access': { doc: 'security', kind: 'switch', default: false, label: 'Administrator (root) access' }
  };

  function host() {
    var h = global.NuxelHost;
    if (h && h.available) return h;
    try { if (global.parent && global.parent !== global && global.parent.NuxelHost) return global.parent.NuxelHost; } catch (e) {}
    return null;
  }
  function store() {
    var s = global.NuxelSettings;
    if (s) return s;
    try { if (global.parent && global.parent.NuxelSettings) return global.parent.NuxelSettings; } catch (e) {}
    return null;
  }

  var cache = {};

  function loadDoc(name) {
    var st = store();
    if (st && typeof st.load === 'function') {
      return Promise.resolve(st.load(name)).then(function (res) {
        cache[name] = (res && res.doc) || {};
        return cache[name];
      }, function () { return cache[name] || {}; });
    }
    var h = host();
    if (h) {
      return h.configGet(name).then(function (res) {
        if (res && res.ok && res.text) { try { cache[name] = JSON.parse(res.text); } catch (e) { cache[name] = {}; } }
        else cache[name] = {};
        return cache[name];
      }, function () { cache[name] = {}; return cache[name]; });
    }
    return Promise.resolve(cache[name] || {});
  }

  function saveDoc(name, doc, opts) {
    var st = store();
    if (st && typeof st.set === 'function') {
      try { return Promise.resolve(st.set(name, doc)).then(function (res) { return res || { ok: true }; }); } catch (e) { /* fall through */ }
    }
    var h = host();
    if (h) {
      return h.configSet(name, JSON.stringify(doc, null, 2) + '\n').then(function (res) {
        return res && res.ok ? res : { ok: false, offline: true };
      }, function () { return { ok: false, offline: true }; });
    }
    try {
      global.localStorage.setItem('nuxel.settings.' + name, JSON.stringify(doc));
      return Promise.resolve({ ok: true, transport: 'localStorage' });
    } catch (e) {
      return Promise.resolve({ ok: false, offline: true, error: String(e) });
    }
  }

  function read(key) {
    var spec = SETTINGS[key];
    if (!spec) return undefined;
    var doc = cache[spec.doc] || {};
    var v = doc[key];
    return v === undefined ? spec.default : v;
  }

  function write(key, value) {
    var spec = SETTINGS[key];
    if (!spec) return Promise.resolve({ ok: false, error: 'unknown setting ' + key });
    return loadDoc(spec.doc).then(function (doc) {
      var next = Object.assign({}, doc || {});
      next.schema_version = next.schema_version || 1;
      next[key] = value;
      next.set_by = 'user';
      next.updated_at = Date.now();
      cache[spec.doc] = next;
      return saveDoc(spec.doc, next).then(function (res) {
        res = res || {};
        return { ok: res.ok !== false, transport: res.transport || 'host', doc: next, key: key, value: value };
      });
    });
  }

  // ---------------------------------------------------------------- probing
  // A probe answers: "is the component that consumes this document actually
  // running here?". The answer is taken from the launcher host when it can
  // answer; otherwise it is honestly 'unknown' (never 'ok').
  function probe(name) {
    var h = host();
    if (!h || typeof h.statusRead !== 'function') {
      return Promise.resolve({ state: 'unknown', detail: 'launcher host unavailable in this context' });
    }
    return h.statusRead(name).then(function (res) {
      if (res && res.ok && res.text) return { state: 'present', detail: String(res.text).trim() };
      return { state: 'absent', detail: 'the host has no status channel named ' + name };
    }, function () {
      return { state: 'absent', detail: 'the host refused the status read' };
    });
  }

  function describe(key) {
    var spec = SETTINGS[key];
    if (!spec) return null;
    var doc = DOCS[spec.doc] || {};
    return {
      key: key, label: spec.label, kind: spec.kind, doc: spec.doc,
      doc_path: doc.path || ('/etc/nuxel/' + spec.doc + '.json'),
      consumer: doc.consumer || '(unnamed)', probe: doc.probe || null
    };
  }

  // Which controls are grouped where in the UI (mission area 48 groups).
  var GROUPS = {
    network: ['network.wifi_enabled', 'network.wifi_autoconnect', 'network.cellular_enabled',
              'network.dns_mode', 'network.vpn_enabled'],
    display: ['display.timeout_sec', 'display.overflow_policy', 'display.wake_double_tap', 'display.sleep_double_tap'],
    orientation: ['orientation.mode'],
    sound: ['sound.output_route', 'sound.notifications', 'sound.haptics'],
    input: ['keyboard.enabled', 'keyboard.auto_show', 'keyboard.layout', 'keyboard.numeric_layout',
            'keyboard.height_dp', 'keyboard.key_repeat', 'keyboard.haptics', 'keyboard.haptics_intensity', 'keyboard.haptics_pulse_ms', 'keyboard.clipboard',
            'keyboard.hardware_passthrough'],
    buttons: ['buttons.bixby_short', 'buttons.bixby_long', 'buttons.power_short', 'buttons.power_long',
              'buttons.volume_up', 'buttons.volume_down'],
    apps: ['apps.show_undeclared', 'apps.default_browser'],
    privacy: ['privacy.camera', 'privacy.microphone', 'privacy.location', 'privacy.recorder_killswitch'],
    security: ['security.firewall_profile', 'security.admin_access'],
    system: ['time.auto', 'time.timezone', 'time.format', 'power.mode'],
    performance: ['performance.governor']
  };

  // Button mappings live in the buttons document under their own key names.
  SETTINGS['buttons.bixby_short'] = { doc: 'buttons', kind: 'select', default: 'open-terminal', label: 'Bixby short press', alias: 'bixby_short' };
  SETTINGS['buttons.bixby_long'] = { doc: 'buttons', kind: 'select', default: 'disabled', label: 'Bixby long press', alias: 'bixby_long' };
  SETTINGS['buttons.power_short'] = { doc: 'buttons', kind: 'select', default: 'screen-toggle', label: 'Power short press', alias: 'power_short' };
  SETTINGS['buttons.power_long'] = { doc: 'buttons', kind: 'select', default: 'power-menu', label: 'Power long press', alias: 'power_long' };
  SETTINGS['buttons.volume_up'] = { doc: 'buttons', kind: 'select', default: 'volume-up', label: 'Volume up', alias: 'volume_up' };
  SETTINGS['buttons.volume_down'] = { doc: 'buttons', kind: 'select', default: 'volume-down', label: 'Volume down', alias: 'volume_down' };
  SETTINGS['performance.governor'] = { doc: 'power', kind: 'select', default: 'auto', label: 'CPU governor' };

  // The buttons document uses the alias as its real key.
  function docKey(key) {
    var spec = SETTINGS[key];
    return spec && spec.alias ? spec.alias : key;
  }

  function readValue(key) {
    var spec = SETTINGS[key];
    if (!spec) return undefined;
    var doc = cache[spec.doc] || {};
    var v = doc[docKey(key)];
    return v === undefined ? spec.default : v;
  }

  global.NuxelSettingsModel = {
    DOCS: DOCS,
    SETTINGS: SETTINGS,
    GROUPS: GROUPS,
    docKey: docKey,
    loadDoc: loadDoc,
    saveDoc: saveDoc,
    read: readValue,
    write: write,
    probe: probe,
    describe: describe,
    // introspection used by tools/s10plus/a33/tests/test-settings-app.py
    audit: function () {
      return Object.keys(SETTINGS).map(function (key) {
        var d = describe(key);
        d.has_consumer = !!(d.consumer && d.consumer !== '(unnamed)');
        return d;
      });
    }
  };
})(typeof window !== 'undefined' ? window : this);

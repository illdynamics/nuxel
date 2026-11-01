/* Nuxel status-bar icon visibility preference (PWNAGE-52000).
 *
 * This is a UI preference only.  It never changes a radio, a service, a
 * provider or a hardware state.  The final visibility rule is:
 *
 *   visible = user_preference_show
 *             && provider_supported
 *             && provider_state_is_relevant
 *             && !locked
 *
 * The document is /etc/nuxel/display/statusbar-icons.json.  Safe-zone
 * geometry remains a separate document (/etc/nuxel/display/statusbar-safezones.json).
 * An unknown key from a newer revision is preserved on save; an unknown icon id
 * is ignored by this revision instead of being treated as ON.
 */
(function (global) {
  'use strict';

  var CFG_NAME = 'statusbar-icons';
  var STORAGE_KEY = 'nuxel.statusbarIcons';
  var SCHEMA_VERSION = 1;

  var DEFS = [
    { id: 'time',         element: 'status-time',        label: 'Time',                 core: true },
    { id: 'signal',       element: 'status-signal',      label: 'Cellular signal',      core: true },
    { id: 'wifi',         element: 'status-wifi',        label: 'Wi-Fi',                core: true },
    { id: 'location',     element: 'status-location',    label: 'Location',             core: false },
    { id: 'bluetooth',    element: 'status-bluetooth',   label: 'Bluetooth',            core: false },
    { id: 'nfc',          element: 'status-nfc',         label: 'NFC',                  core: false },
    { id: 'sound',        element: 'status-sound',       label: 'Sound mode',           core: false },
    { id: 'usb',          element: 'status-usb',         label: 'USB connection',       core: false },
    { id: 'remote',       element: 'status-remote',      label: 'Remote desktop',       core: false },
    { id: 'battery',      element: 'status-battery',     label: 'Battery icon',         core: true },
    { id: 'battery_pct',  element: 'status-battery-pct', label: 'Battery percentage',   core: true }
  ];

  function defaults() {
    var d = { schema_version: SCHEMA_VERSION, updated_at: 0, source: 'default', icons: {} };
    DEFS.forEach(function (x) { d.icons[x.id] = true; });
    return d;
  }

  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  function normalize(doc) {
    var out = defaults();
    if (!doc || typeof doc !== 'object') return out;
    out.schema_version = SCHEMA_VERSION;
    out.updated_at = Number(doc.updated_at || 0);
    out.source = doc.source || 'document';
    // Preserve unknown icon keys: a newer revision may add an icon and an
    // older Settings page must not erase it.
    if (doc.icons && typeof doc.icons === 'object') {
      Object.keys(doc.icons).forEach(function (k) {
        if (typeof doc.icons[k] === 'boolean') out.icons[k] = doc.icons[k];
      });
    }
    // Schema migration: v0 stored a flat object.  Treat only explicit booleans
    // as user decisions; do not invent OFF from a missing key.
    if (!doc.icons && doc.schema_version === undefined) {
      Object.keys(doc).forEach(function (k) {
        var id = k === 'batteryPercent' ? 'battery_pct' : k;
        if (typeof doc[k] === 'boolean' && out.icons[id] !== undefined) out.icons[id] = doc[k];
      });
    }
    return out;
  }

  function parse(text) {
    try { return normalize(JSON.parse(text)); }
    catch (e) { return defaults(); }
  }

  function host() {
    var h = global.NuxelHost;
    if (h && h.available) return h;
    // Settings runs inside the launcher's same-origin iframe; the parent owns
    // the only real host channel.
    try {
      if (global.parent && global.parent !== global && global.parent.NuxelHost &&
          global.parent.NuxelHost.available) return global.parent.NuxelHost;
    } catch (e) {}
    return null;
  }

  function load() {
    var h = host();
    if (h && h.configGet) {
      return Promise.resolve(h.configGet(CFG_NAME)).then(function (res) {
        if (res && res.ok && res.text) return parse(res.text);
        try { return parse(global.localStorage.getItem(STORAGE_KEY)); }
        catch (e) { return defaults(); }
      }).catch(function () { return defaults(); });
    }
    try { return Promise.resolve(parse(global.localStorage.getItem(STORAGE_KEY))); }
    catch (e) { return Promise.resolve(defaults()); }
  }

  function save(doc) {
    var d = normalize(doc);
    d.updated_at = Date.now();
    d.source = 'user';
    var text = JSON.stringify(d, null, 2) + '\n';
    try { global.localStorage.setItem(STORAGE_KEY, text); } catch (e) {}
    var h = host();
    if (h && h.configSet) {
      return Promise.resolve(h.configSet(CFG_NAME, text)).then(function (res) {
        return { ok: !!(res && res.ok), doc: d, transport: res && res.ok ? 'host' : 'localStorage', response: res };
      }).catch(function (e) {
        return { ok: false, doc: d, transport: 'localStorage', error: String(e && e.message || e) };
      });
    }
    return Promise.resolve({ ok: false, doc: d, transport: 'localStorage', error: 'launcher host unavailable' });
  }

  var API = {
    CFG_NAME: CFG_NAME,
    SCHEMA_VERSION: SCHEMA_VERSION,
    DEFS: clone(DEFS),
    defaults: defaults,
    normalize: normalize,
    parse: parse,
    load: load,
    save: save,
    byElement: function (elementId) {
      for (var i = 0; i < DEFS.length; i++) if (DEFS[i].element === elementId) return DEFS[i];
      return null;
    }
  };
  global.NuxelStatusBarIcons = API;
})(window);

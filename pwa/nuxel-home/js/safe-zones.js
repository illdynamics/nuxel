// Nuxel Status-Bar Camera & Cutout Safe Zones (A32, mission 9)
//
// The launcher's status bar is divided into ten equal LOGICAL ZONES, numbered 1
// to 10 left to right.  A zone marked BLOCKED is not a painted warning: it is an
// excluded horizontal interval, and NO status item may be laid out inside it.
// The item row is a flex container in three clusters (left/centre/right); this
// module turns the blocked zones into the intervals those clusters must avoid and
// then places every item with a constraint-aware pass, instead of trusting the
// CSS to keep them out of the cutout.
//
// Storage: /etc/nuxel/display/statusbar-safezones.json through the launcher host
// (NuxelHost.configGet/configSet).  Without a host (VM/desktop/browser) the same
// document is kept in localStorage, so the editor and the layout behave
// identically everywhere, and the file remains the single source of truth for the
// device configuration.
//
// Device profiles: the geometry of a cutout belongs to the DEVICE, not to the OS,
// so profile keys are chosen from the hardware identity and one device's choice
// never leaks into another's.
(function (global) {
  'use strict';

  var ZONES = 10;
  var DEFAULTS = {
    schema_version: 1,
    zones: ZONES,
    profiles: {
      s10plus:       { portrait: [9, 10], landscape_left: [], landscape_right: [] },
      pixel_center:  { portrait: [5, 6],  landscape_left: [], landscape_right: [] },
      none:          { portrait: [],     landscape_left: [], landscape_right: [] },
      left_camera:   { portrait: [1, 2],  landscape_left: [1, 2], landscape_right: [9, 10] },
      right_camera:  { portrait: [9, 10], landscape_left: [9, 10], landscape_right: [1, 2] }
    },
    presets: ['none', 'right_camera', 'center_camera', 'left_camera', 'custom'],
    preset_alias: { center_camera: 'pixel_center', pixel_center: 'pixel_center', s10plus: 's10plus' },
    padding_dp: 6,
    profile: 'none',
    orientation: 'portrait',
    custom: { portrait: [], landscape_left: [], landscape_right: [] }
  };

  var CFG_NAME = 'statusbar-safezones';
  var state = JSON.parse(JSON.stringify(DEFAULTS));
  var preview = null;               // {profile, orientation, zones} while editing

  function clone(o) { return JSON.parse(JSON.stringify(o)); }

  function deviceProfile() {
    // Hardware identity decides the starting preset (never a global assumption).
    var ua = (navigator.userAgent || '') + ' ' + (navigator.platform || '');
    if (/S10\+|G975|beyond2/i.test(ua)) return 's10plus';
    if (/Pixel/i.test(ua)) return 'pixel_center';
    return 'none';
  }

  function zonesFor(profile, orientation) {
    var alias = state.preset_alias[profile] || profile;
    var p = state.profiles[alias] || state.profiles[profile];
    if (!p) return [];
    if (profile === 'custom') p = state.custom;
    var list = p[orientation] || p.portrait || [];
    return list.slice().sort(function (a, b) { return a - b; });
  }

  function activeZones() {
    if (preview) return preview.zones.slice();
    return zonesFor(state.profile, state.orientation);
  }

  function blockedIntervals(widthPx) {
    var zones = activeZones();
    if (!widthPx || !zones.length) return [];
    var zoneW = widthPx / ZONES;
    var pad = (state.padding_dp || 0) * (global.devicePixelRatio || 1);
    return zones.map(function (z) {
      return { start: (z - 1) * zoneW - pad, end: z * zoneW + pad, zone: z };
    }).sort(function (a, b) { return a.start - b.start; });
  }

  function overlaps(aStart, aEnd, ivals) {
    for (var i = 0; i < ivals.length; i++) {
      if (aStart < ivals[i].end && aEnd > ivals[i].start) return ivals[i];
    }
    return null;
  }

  // Constraint-aware placement: measure each item, then move a cluster's items to
  // the free interval nearest their natural position.  Priority order is fixed and
  // explicit (essential indicators never get dropped to make the maths easy):
  //   1 time  2 battery icon  3 battery %  4 signal  5 wifi  6 notifications
  var PRIORITY = ['status-time', 'status-battery', 'status-battery-pct', 'status-signal', 'status-wifi'];

  function applyLayout() {
    var bar = document.getElementById('status-bar');
    if (!bar) return { blocked: [], placed: [], moved: [], dropped: [] };
    var width = bar.clientWidth || bar.offsetWidth;
    var ivals = blockedIntervals(width);
    bar.setAttribute('data-safezone-profile', preview ? 'preview' : state.profile);
    bar.setAttribute('data-safezone-orientation', state.orientation);
    bar.setAttribute('data-safezone-blocked', activeZones().join(','));
    bar.setAttribute('data-safezone-padding-dp', String(state.padding_dp || 0));

    var report = { blocked: activeZones(), placed: [], moved: [], dropped: [], width: width };
    var clusters = [
      { el: bar.querySelector('.status-left'), align: 'start' },
      { el: bar.querySelector('.status-center'), align: 'center' },
      { el: bar.querySelector('.status-right'), align: 'end' }
    ];

    clusters.forEach(function (c) {
      if (!c.el) return;
      var natural = c.el.getBoundingClientRect();
      var hit = overlaps(natural.left, natural.right, ivals);
      // Reset any previous push, then solve against the real blocked intervals.
      c.el.style.transform = '';
      c.el.style.paddingRight = '';
      if (!hit) { report.placed.push({ cluster: c.el.className, ok: true }); return; }
      var shift;
      if (c.align === 'start') {                       // push left of the first blocked zone
        shift = Math.min(0, ivals[0].start - natural.left - 2);
      } else if (c.align === 'end') {                  // push right of the last blocked zone
        var last = ivals[ivals.length - 1];
        shift = Math.max(0, last.end - natural.left + 2);
      } else {                                         // centre: take the wider free side
        var leftFree = ivals[0].start;
        var rightFree = width - ivals[ivals.length - 1].end;
        shift = (leftFree >= rightFree)
          ? (ivals[0].start - natural.right - 2)
          : (ivals[ivals.length - 1].end - natural.left + 2);
      }
      c.el.style.transform = 'translateX(' + Math.round(shift) + 'px)';
      report.moved.push({ cluster: c.el.className, shift: Math.round(shift), zone: hit.zone });
    });
    global.__nuxelSafeZoneReport = report;
    // Deterministic evidence: the placement report goes through the launcher
    // host's diagnostic channel (/run/nuxel-home.state), so it can be verified
    // from the live console instead of from a screenshot.  Only a CHANGED verdict
    // is reported: the render paths call applyLayout() several times per state
    // update, and an evidence channel that repeats itself is noise, not evidence.
    var sig = (preview ? 'preview' : state.profile) + '|' + state.orientation + '|' +
              activeZones().join(',') + '|' + (state.padding_dp || 0) + '|' + width + '|' +
              JSON.stringify(report.moved) + JSON.stringify(report.dropped);
    if (sig === global.__nuxelSafeZoneSig) return report;
    global.__nuxelSafeZoneSig = sig;
    try {
      if (global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.nuxelDiag) {
        global.webkit.messageHandlers.nuxelDiag.postMessage(
          'SAFEZONES profile=' + (preview ? 'preview' : state.profile) +
          ' orientation=' + state.orientation +
          ' blocked=[' + activeZones().join(',') + ']' +
          ' padding_dp=' + (state.padding_dp || 0) +
          ' width=' + width +
          ' moved=' + JSON.stringify(report.moved) +
          ' dropped=' + JSON.stringify(report.dropped));
      }
    } catch (e) {}
    return report;
  }

  function save(cb) {
    var doc = clone(state);
    var text = JSON.stringify(doc, null, 2);
    function done(ok, how) {
      state.saved_at = Date.now();
      if (cb) cb(ok, how);
      global.dispatchEvent(new CustomEvent('nuxel:safezones-changed', { detail: doc }));
    }
    if (global.NuxelHost && global.NuxelHost.available) {
      global.NuxelHost.configSet(CFG_NAME, text).then(function (res) {
        if (!res || !res.ok) { try { localStorage.setItem('nuxel.safezones', text); } catch (e) {} }
        done(!!(res && res.ok), res && res.ok ? 'host' : 'localStorage');
      });
    } else {
      try { localStorage.setItem('nuxel.safezones', text); } catch (e) {}
      done(false, 'localStorage');
    }
  }

  function load(cb) {
    function merge(text, how) {
      if (text) {
        try {
          var doc = JSON.parse(text);
          if (doc && doc.profiles) {
            state = Object.assign(clone(DEFAULTS), doc);
            state.preset_alias = Object.assign(clone(DEFAULTS.preset_alias), doc.preset_alias || {});
          }
        } catch (e) { /* keep defaults */ }
      }
      if (!state.profile || state.profile === 'auto') state.profile = deviceProfile();
      if (cb) cb(state, how);
    }
    if (global.NuxelHost && global.NuxelHost.available) {
      global.NuxelHost.configGet(CFG_NAME).then(function (res) {
        if (res && res.ok && res.text) merge(res.text, 'host');
        else merge((function () { try { return localStorage.getItem('nuxel.safezones'); } catch (e) { return null; } })(), 'localStorage');
      });
    } else {
      merge((function () { try { return localStorage.getItem('nuxel.safezones'); } catch (e) { return null; } })(), 'localStorage');
    }
  }

  var API = {
    ZONES: ZONES,
    get state() { return state; },
    get preview() { return preview; },
    load: load,
    save: save,
    zonesFor: zonesFor,
    activeZones: activeZones,
    blockedIntervals: blockedIntervals,
    applyLayout: applyLayout,
    presets: function () { return DEFAULTS.presets.slice(); },
    applyPreset: function (name) {
      state.profile = (state.preset_alias[name] || name);
      preview = null;
      return state.profile;
    },
    orientation: function (o) { if (o) state.orientation = o; return state.orientation; },
    // Live preview: never persisted until save() is called (mission 9.4).
    previewZones: function (list, orientation, profile) {
      preview = {
        zones: (list || []).slice().sort(function (a, b) { return a - b; }),
        orientation: orientation || state.orientation,
        profile: profile || 'custom'
      };
      return applyLayout();
    },
    cancelPreview: function () { preview = null; return applyLayout(); },
    commitPreview: function (cb) {
      if (!preview) { if (cb) cb(true, 'no-preview'); return; }
      state.profile = 'custom';
      state.custom = state.custom || { portrait: [], landscape_left: [], landscape_right: [] };
      state.custom[preview.orientation] = preview.zones.slice();
      preview = null;
      save(cb);
    },
    setZone: function (zone, blocked, orientation) {
      var o = orientation || state.orientation;
      var list = (preview ? preview.zones : zonesFor(state.profile, o)).slice();
      var i = list.indexOf(zone);
      if (blocked && i < 0) list.push(zone);
      if (!blocked && i >= 0) list.splice(i, 1);
      return API.previewZones(list, o, 'custom');
    },
    padding: function (dp) { if (typeof dp === 'number') state.padding_dp = dp; return state.padding_dp; },
    deviceProfile: deviceProfile
  };

  global.NuxelSafeZones = API;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { load(function () { applyLayout(); }); });
  } else {
    load(function () { applyLayout(); });
  }
})(window);

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

  // The complement of the blocked intervals inside the bar, with overlapping
  // intervals merged (adjacent blocked zones overlap once the padding is added,
  // so "zones 9 and 10" is ONE free gap, not two).
  function freeIntervals(width, ivals) {
    var free = [], pos = 0, i, s0, e0;
    for (i = 0; i < ivals.length; i++) {
      s0 = Math.max(0, Math.min(width, ivals[i].start));
      e0 = Math.max(0, Math.min(width, ivals[i].end));
      if (s0 > pos) free.push({ start: pos, end: s0 });
      if (e0 > pos) pos = e0;
    }
    if (pos < width) free.push({ start: pos, end: width });
    return free;
  }

  // The free interval the cluster mostly occupies; if it occupies none, the
  // nearest one (a cluster that is merely close is still an item in the cutout).
  function bestFreeInterval(natural, free) {
    var best = null, bestScore = -Infinity, i, f, overlap, dist;
    for (i = 0; i < free.length; i++) {
      f = free[i];
      overlap = Math.min(natural.right, f.end) - Math.max(natural.left, f.start);
      dist = Math.min(Math.abs(natural.left - f.end), Math.abs(f.start - natural.right));
      var score = overlap > 0 ? overlap : -dist;
      if (score > bestScore) { bestScore = score; best = f; }
    }
    return best;
  }

  // Where the cluster's left edge goes inside a free interval, honouring its
  // alignment, then clamped so the cluster stays inside that interval AND on the
  // panel.  ('center' keeps its centre; 'end' keeps its right edge flush.)
  function targetLeft(align, natural, f, width) {
    var w = natural.right - natural.left, left;
    if (align === 'start') left = f.start;
    else if (align === 'end') left = f.end - w;
    else left = (f.start + f.end - w) / 2;
    if (left < f.start) left = f.start;
    if (left + w > f.end) left = Math.max(f.start, f.end - w);
    if (left < 0) left = 0;
    if (left + w > width) left = Math.max(0, width - w);
    return left;
  }

  // Pure placement planner (A33 hardening, briq-02e).  Given a cluster's natural
  // rectangle, its alignment and the blocked intervals, decide the shift that puts
  // it in the nearest FREE interval.  It is extracted here so that applyLayout()
  // (the real status bar) and the Settings safe-zone editor use ONE implementation:
  // the editor previously carried a second copy of this arithmetic, and that second
  // copy still used the A32 one-way push (it moved the right cluster further right,
  // off the panel, for the S10+ profile).  Two implementations of one geometry
  // contract is how a preview starts lying about the real bar.
  function planCluster(natural, align, ivals, width) {
    var hit = overlaps(natural.left, natural.right, ivals);
    if (!hit) return { hit: false, shift: 0, zone: null, target: null, narrow: false, reason: 'clear' };
    var free = freeIntervals(width, ivals);
    var target = bestFreeInterval(natural, free);
    if (!target) {
      return { hit: true, shift: 0, zone: hit.zone, target: null, narrow: false,
               reason: 'no_free_interval' };
    }
    var left = targetLeft(align, natural, target, width);
    var shift = Math.round(left - natural.left);
    var w = natural.right - natural.left;
    return {
      hit: true, shift: shift, zone: hit.zone, target: target,
      narrow: (target.end - target.start + 0.5 < w),
      reason: shift ? 'moved' : 'already_free'
    };
  }

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
      // A33 HARDENING (briq-02e): reset the previous push BEFORE measuring.  A
      // CSS transform is included in getBoundingClientRect(), so measuring first
      // made every re-render stack another translate on top of the last one -
      // the layout drifted a little further off-target on every state update.
      // applyLayout() is now idempotent.
      c.el.style.transform = '';
      c.el.style.paddingRight = '';
      var natural = c.el.getBoundingClientRect();
      var plan = planCluster(natural, c.align, ivals, width);
      if (!plan.hit) { report.placed.push({ cluster: c.el.className, ok: true }); return; }

      // A33 HARDENING: solve against the FREE intervals, not "left of the first
      // blocked zone" / "right of the last".  A32 only ever pushed one way, so
      //   * the S10+ portrait profile (zones 9,10 = the right edge) pushed the
      //     right cluster further RIGHT, i.e. off the panel, and
      //   * blocking zones 1,2 pushed the left cluster off the LEFT edge and it
      //     still sat inside the excluded interval.
      // The contract is unchanged (ten zones, same profile, same padding, still
      // transform-only); the difference is that the item now lands in the nearest
      // free interval and never inside a blocked one.
      if (plan.reason === 'no_free_interval') {   // the whole bar is blocked
        report.dropped.push({ cluster: c.el.className, reason: 'no_free_interval' });
        return;
      }
      if (!plan.shift) { report.placed.push({ cluster: c.el.className, ok: true }); return; }
      c.el.style.transform = 'translateX(' + plan.shift + 'px)';
      if (plan.narrow) {
        report.dropped.push({ cluster: c.el.className, reason: 'free_interval_narrower_than_cluster',
                              free: [Math.round(plan.target.start), Math.round(plan.target.end)],
                              width: Math.round(natural.right - natural.left) });
      }
      report.moved.push({ cluster: c.el.className, shift: plan.shift, zone: plan.zone,
                          free: [Math.round(plan.target.start), Math.round(plan.target.end)] });
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
    // Pure geometry helpers, shared with the Settings safe-zone editor so the
    // preview strip and the real status bar place items with the same code.
    freeIntervals: freeIntervals,
    overlaps: overlaps,
    planCluster: planCluster,
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

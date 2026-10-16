#!/usr/bin/env python3
# =============================================================================
# docs/beta-finalization/vm/guest-launcher-parity.py   (briq-11a, group bg-11)
#
# GUEST-SIDE Nuxel Home / launcher parity harness.
#
# Runs INSIDE the UTM Fedora 43 ARM64 guest as the `nuxel` user, inside the LIVE
# Phosh 0.54 / phoc 0.54 Wayland session, so that what is rendered is the real
# Nuxel Home PWA running on the real reference stack (WebKitGTK 4.1 -> Phoc ->
# Wayland).  It is driven from the host by docs/beta-finalization/vm/run-vm-parity.sh.
#
# WHAT IT PROVES (and what it does NOT)
#   * the launcher page loads from the served tree and its JavaScript BUILDS the
#     UI (app grid tiles, dock, status-bar items) - checked from inside the page;
#   * status-bar.js is the single source of truth: the running revision is read
#     out of the live page and compared with manifest.json + sw.js;
#   * the ten-zone safe-area engine is present, has exactly 10 zones, and the
#     blocked-zone -> exclusion invariant holds for a MATRIX of zone sets
#     (measured on the real DOM rectangles of the status items);
#   * the ten-zone editor in the Settings app drives the REAL launcher status bar
#     when it is embedded in the launcher (same-origin iframe), and its preview
#     report agrees with the launcher's own placement report;
#   * the wallpaper and the colour pipeline produce the expected BYTES: the
#     wallpaper asset is fetched in-page and SHA-256'd against the repository
#     file, and a canvas round-trip proves the exact RGBA bytes WebKit emits for
#     known colours;
#   * every refreshed PWA in the launcher registry loads without console errors
#     and its DOM is dumped.
#   It does NOT prove anything about the S10+ handset (a VM PASS is
#   VERIFIED_IN_VM_ONLY), it does NOT prove the DECON ABGR panel conversion (that
#   needs the glass; see docs/beta-finalization/boot/COLOUR-CONVERSION.md), and a
#   PASS here is never promoted to VERIFIED_ON_S10PLUS.
#
# Usage (guest, inside the graphical session):
#   XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 \
#   python3 guest-launcher-parity.py --outdir ~/vm-parity-out
#
# Env/timeout: the whole run is bounded; the exit code is 0 when the harness
# completed (per-check PASS/FAIL/NOT-VERIFIED counts are in the JSON), 2 when it
# could not run at all (e.g. no Wayland session, WebKit missing).
# =============================================================================
import argparse
import json
import os
import subprocess
import sys
import time

try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('WebKit2', '4.1')
    from gi.repository import Gtk, WebKit2, GLib
except Exception as exc:                                   # pragma: no cover
    sys.stderr.write('HARNESS-CANNOT-RUN: WebKit2GTK/GTK3 unavailable: %r\n' % (exc,))
    sys.exit(2)

# Injected at DOCUMENT_START into the page's own world so that the console-error
# record is what the page itself produced (no synthetic errors are added).
PRELUDE = r"""
(function () {
  if (window.__nuxelErrors) return;
  window.__nuxelErrors = [];
  function rec(level, args) {
    try {
      window.__nuxelErrors.push({
        level: level,
        text: Array.prototype.map.call(args, function (a) {
          try { return (typeof a === 'string') ? a : JSON.stringify(a); }
          catch (e) { return String(a); }
        }).join(' '),
        at: Date.now()
      });
    } catch (e) {}
  }
  var ce = console.error, cw = console.warn;
  console.error = function () { rec('error', arguments); ce.apply(console, arguments); };
  console.warn  = function () { rec('warn', arguments);  cw.apply(console, arguments); };
  window.addEventListener('error', function (e) {
    var t = e.target;
    if (t && t !== window && (t.src || t.href)) {
      rec('error', ['RESOURCE ' + (t.tagName || '?') + ' ' + (t.src || t.href)]);
    } else {
      rec('error', ['JS ' + (e.message || 'error') + ' @' + (e.filename || '?') + ':' + (e.lineno || 0)]);
    }
  }, true);
  window.addEventListener('unhandledrejection', function (e) {
    var r = e.reason;
    rec('error', ['UNHANDLED-REJECTION ' + ((r && (r.message || r.name)) || String(r))]);
  });
})();
"""

# ---------------------------------------------------------------------------
# In-page probe: everything is read from the LIVE page and returned as JSON.
# ---------------------------------------------------------------------------
PROBE_LAUNCHER = r"""
(function () {
  function rect(el) {
    if (!el) return null;
    var r = el.getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height, right: r.right, bottom: r.bottom };
  }
  function css(el, prop) { return el ? getComputedStyle(el)[prop] : null; }
  function txt(id) { var e = document.getElementById(id); return e ? e.textContent : null; }

  var sb = document.getElementById('status-bar');
  var sz = window.NuxelSafeZones || null;
  var barW = sb ? sb.getBoundingClientRect().width : window.innerWidth;

  var out = {
    url: location.href,
    title: document.title,
    readyState: document.readyState,
    bodyReady: document.body.classList.contains('ready'),
    viewport: { w: window.innerWidth, h: window.innerHeight, dpr: window.devicePixelRatio },
    userAgent: navigator.userAgent
  };

  // ---- status-bar.js: the single source of truth -------------------------
  out.statusBar = {
    classPresent: (typeof StatusBar !== 'undefined'),
    version: (typeof StatusBar !== 'undefined') ? StatusBar.VERSION : null,
    globalVersion: window.NUXEL_STATUS_BAR_VERSION || null,
    rect: rect(sb),
    background: css(sb, 'backgroundColor'),
    color: css(sb, 'color'),
    height: sb ? sb.getBoundingClientRect().height : null,
    timeText: txt('status-time'),
    timeRect: rect(document.getElementById('status-time')),
    signalRect: rect(document.getElementById('status-signal')),
    wifiRect: rect(document.getElementById('status-wifi')),
    batteryRect: rect(document.getElementById('status-battery')),
    batteryPctText: txt('status-battery-pct'),
    batteryPctRect: rect(document.getElementById('status-battery-pct')),
    leftCluster: rect(document.querySelector('#status-bar .status-left')),
    centerCluster: rect(document.querySelector('#status-bar .status-center')),
    rightCluster: rect(document.querySelector('#status-bar .status-right'))
  };

  // ---- registry / launcher grid ------------------------------------------
  var apps = (window.appRegistry && appRegistry.getAllApps) ? appRegistry.getAllApps() : [];
  out.registry = {
    version: window.NUXEL_REGISTRY_VERSION || null,
    count: apps.length,
    ids: apps.map(function (a) { return a.id; }),
    entries: apps.map(function (a) { return { id: a.id, name: a.name, type: a.type, url: a.url }; })
  };
  var tiles = Array.prototype.slice.call(document.querySelectorAll('#app-list .app-item'));
  out.grid = {
    tiles: tiles.length,
    icons: document.querySelectorAll('#app-list .app-icon').length,
    labels: Array.prototype.slice.call(document.querySelectorAll('#app-list .app-label')).map(function (e) { return e.textContent; }),
    labelsWithText: tiles.filter(function (t) { return (t.querySelector('.app-label') || {}).textContent; }).length,
    listRect: rect(document.getElementById('app-list')),
    listDisplay: css(document.getElementById('app-list'), 'display'),
    listColumns: css(document.getElementById('app-list'), 'gridTemplateColumns'),
    dockTiles: document.querySelectorAll('#dock-items .app-item').length,
    dockRect: rect(document.getElementById('dock')),
    pageDots: document.querySelectorAll('.app-grid-indicator .dot').length,
    firstTileRect: rect(tiles[0]),
    tilesInsideViewport: tiles.filter(function (t) {
      var r = t.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && r.top >= -1 && r.bottom <= window.innerHeight + 1;
    }).length
  };

  // ---- ten-zone safe-area engine ----------------------------------------
  out.safeZones = {
    present: !!sz,
    zones: sz ? sz.ZONES : null,
    presets: sz ? sz.presets() : null,
    state: sz ? JSON.parse(JSON.stringify(sz.state)) : null,
    activeZones: sz ? sz.activeZones() : null,
    blockedIntervals: sz ? sz.blockedIntervals(barW) : null
  };

  // ---- wallpaper + colour pipeline (bytes) ------------------------------
  out.wallpaper = {
    backgroundImage: css(document.body, 'backgroundImage'),
    backgroundColor: css(document.body, 'backgroundColor'),
    bodyRect: rect(document.body)
  };

  out.colour = (function () {
    // Canvas round-trip: what WebKit hands to the compositor as RGBA bytes for
    // known colours.  This is the WebKit side of the colour pipeline; the
    // XRGB8888 -> DECON ABGR8888 swap happens below WebKit (nuxel-wl-fb) and is
    // NOT observable from a web page.
    var cases = { red: '#ff0000', green: '#00ff00', blue: '#0000ff', white: '#ffffff', black: '#000000', grey: '#808080' };
    var res = {};
    try {
      var c = document.createElement('canvas');
      c.width = 2; c.height = 2;
      var g = c.getContext('2d');
      Object.keys(cases).forEach(function (k) {
        g.clearRect(0, 0, 2, 2);
        g.fillStyle = cases[k];
        g.fillRect(0, 0, 2, 2);
        var d = g.getImageData(0, 0, 1, 1).data;
        res[k] = { expect: cases[k], rgba: [d[0], d[1], d[2], d[3]] };
      });
    } catch (e) {
      res.error = String(e && e.message || e);
    }
    return res;
  })();

  // ---- boot splash (animation hand-off in the VM path) -------------------
  out.bootSplash = (function () {
    var s = document.getElementById('boot-splash');
    var v = document.getElementById('boot-splash-video');
    return {
      present: !!s,
      removed: !s,
      splashOpacity: s ? css(s, 'opacity') : null,
      video: v ? {
        readyState: v.readyState,
        networkState: v.networkState,
        currentTime: v.currentTime,
        duration: v.duration,
        paused: v.paused,
        videoWidth: v.videoWidth,
        videoHeight: v.videoHeight,
        error: v.error ? { code: v.error.code, message: v.error.message } : null
      } : null
    };
  })();

  // ---- quick settings / search ------------------------------------------
  var qs = document.getElementById('quick-settings');
  var so = document.getElementById('search-overlay');
  out.panels = {
    quickSettings: {
      present: !!qs,
      open: qs ? !qs.classList.contains('hidden') : null,
      items: Array.prototype.slice.call(document.querySelectorAll('#quick-settings .qs-item')).map(function (el) {
        return { id: el.id, label: (el.querySelector('.qs-label') || {}).textContent, enabled: el.dataset.enabled };
      })
    },
    searchOverlay: {
      present: !!so,
      open: so ? !so.classList.contains('hidden') : null,
      results: document.querySelectorAll('#search-results .search-result, #search-results .app-item').length
    },
    recents: { present: !!document.getElementById('recents-view') }
  };

  // ---- bridge (host/HTTP channel) ---------------------------------------
  out.bridge = {
    present: (typeof window.bridge !== 'undefined'),
    sharedModule: !!window.NuxelBridge,
    connected: (window.bridge ? !!window.bridge.connected : null),
    mockMode: (window.NuxelBridge ? !!window.NuxelBridge.mockMode : null),
    apiUrl: (window.bridge ? window.bridge.apiUrl : null)
  };

  out.errors = window.__nuxelErrors || [];
  return JSON.stringify(out);
})()
"""

PROBE_ZONE_MATRIX = r"""
(function () {
  // Invariant under test: with a blocked-zone set applied, no status item may be
  // laid out INSIDE a blocked interval - and where no placement exists at all,
  // the engine must REPORT the drop instead of silently overlapping the cutout.
  var sz = window.NuxelSafeZones;
  var sb = document.getElementById('status-bar');
  if (!sz || !sb) return JSON.stringify({ error: 'safe-zone engine or status bar missing' });
  var barW = sb.getBoundingClientRect().width;
  var ids = ['status-time', 'status-signal', 'status-wifi', 'status-battery', 'status-battery-pct'];
  var cases = [
    { name: 'none',        zones: [] },
    { name: 's10plus',     zones: [9, 10] },
    { name: 'center',      zones: [5, 6] },
    { name: 'left',        zones: [1, 2] },
    { name: 'zone-10-only', zones: [10] },
    { name: 'zone-1-only', zones: [1] },
    { name: 'gaps-2-3-7',  zones: [2, 3, 7] },
    { name: 'odd-zones',   zones: [1, 3, 5, 7, 9] },
    { name: 'all-ten',     zones: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] }
  ];
  function clusterOf(el) {
    var c = el.closest ? el.closest('.status-left,.status-center,.status-right') : null;
    return c ? (c.className || '').split(' ')[0] : null;
  }
  var results = [];
  var original = sz.activeZones().slice();
  var originalProfile = sz.state.profile;
  // natural (untransformed) cluster widths, measured with no zones blocked
  sz.previewZones([], 'portrait', 'custom');
  sz.applyLayout();
  var clusterNatural = {};
  ['.status-left', '.status-center', '.status-right'].forEach(function (sel) {
    var el = sb.querySelector(sel);
    if (!el) return;
    var r = el.getBoundingClientRect();
    clusterNatural[sel] = { left: r.left, right: r.right, width: r.width };
  });
  cases.forEach(function (c) {
    sz.previewZones(c.zones, 'portrait', 'custom');
    var report = sz.applyLayout();
    var intervals = sz.blockedIntervals(barW);
    var free = sz.freeIntervals(barW, intervals);
    var violations = [];
    var placed = [];
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      var r = el.getBoundingClientRect();
      if (r.width <= 0 && r.height <= 0) return;
      var cluster = clusterOf(el);
      placed.push({ id: id, cluster: cluster, x: Math.round(r.x * 100) / 100, w: Math.round(r.width * 100) / 100,
                    right: Math.round(r.right * 100) / 100 });
      intervals.forEach(function (iv) {
        var overlap = Math.min(r.right, iv.end) - Math.max(r.x, iv.start);
        if (overlap > 0.5) {
          violations.push({ id: id, cluster: cluster, zone: iv.zone,
                            overlapPx: Math.round(overlap * 100) / 100 });
        }
      });
    });
    var movedClusters = (report.moved || []).map(function (m) { return (m.cluster || '').split(' ')[0]; });
    var droppedClusters = (report.dropped || []).map(function (d) { return (d.cluster || '').split(' ')[0]; });
    results.push({
      case: c.name, zones: c.zones, blockedIntervals: intervals, freeIntervals: free,
      placed: placed, violations: violations, plannerReport: report,
      movedClusters: movedClusters, droppedClusters: droppedClusters,
      violationClusters: violations.map(function (v) { return v.cluster; }).filter(function (v, i, a) { return a.indexOf(v) === i; })
    });
  });
  sz.previewZones(original, 'portrait', originalProfile);
  sz.cancelPreview();
  return JSON.stringify({ barWidthPx: barW, clusterNatural: clusterNatural, cases: results });
})()
"""

PROBE_EDITOR_IFRAME = r"""
(function () {
  // The Settings app is a registry app opened inside the launcher; its ten-zone
  // editor re-uses the LAUNCHER's safe-zone engine through the same-origin
  // parent frame.  This probe embeds it exactly that way and drives the real
  // editor, then compares the editor's report with the launcher's own bar.
  var out = { started: true, engineInParent: !!window.NuxelSafeZones };
  var f = document.getElementById('__parity_editor_frame');
  if (f) f.parentNode.removeChild(f);
  f = document.createElement('iframe');
  f.id = '__parity_editor_frame';
  f.style.cssText = 'position:fixed;left:0;top:0;width:360px;height:720px;border:0;z-index:9';
  f.src = '/pwa/nuxel-apps/settings/index.html';
  document.body.appendChild(f);
  return JSON.stringify(out);
})()
"""

PROBE_EDITOR_DRIVE = r"""
(function () {
  var f = document.getElementById('__parity_editor_frame');
  if (!f || !f.contentDocument) return JSON.stringify({ error: 'editor iframe not available' });
  var d = f.contentDocument;
  var w = f.contentWindow;
  var zones = Array.prototype.slice.call(d.querySelectorAll('#zones .zone'));
  var out = { zoneBoxes: zones.length, engineVisibleToEditor: !!(w.NuxelSafeZones || (window.parent && window.NuxelSafeZones)) };
  // The editor renders the ten zones after its boot; build state safely if the
  // page is still loading.
  if (!zones.length) return JSON.stringify({ error: 'no zone boxes rendered yet', readyState: d.readyState });
  // Block the two right-most zones (the S10+ portrait cutout: 9, 10) and press
  // "Apply to real status bar (preview)" - the button that drives the REAL bar.
  [9, 10].forEach(function (z) {
    var b = d.querySelector('#zones .zone[data-zone="' + z + '"]');
    if (b && !b.classList.contains('blocked')) b.click();
  });
  var apply = d.getElementById('apply-zones');
  if (apply) apply.click();
  var report = d.getElementById('preview-report') ? d.getElementById('preview-report').textContent : null;
  var blockedBoxes = Array.prototype.slice.call(d.querySelectorAll('#zones .zone.blocked')).map(function (b) { return b.dataset.zone; });
  var previewStrip = d.getElementById('preview-zones');
  var previewBlocked = previewStrip ? Array.prototype.slice.call(previewStrip.children).map(function (c, i) { return c.classList.contains('blocked') ? (i + 1) : null; }).filter(function (x) { return x; }) : null;
  var previewBar = d.getElementById('preview-bar');
  var pvRects = previewBar ? Array.prototype.slice.call(previewBar.querySelectorAll('.pv')).map(function (el) {
    var r = el.getBoundingClientRect();
    return { cls: el.className, x: Math.round(r.x), w: Math.round(r.width) };
  }) : null;
  // Real launcher status bar, driven by the editor through the shared engine.
  var ids = ['status-time', 'status-signal', 'status-wifi', 'status-battery', 'status-battery-pct'];
  var bar = document.getElementById('status-bar');
  var barW = bar ? bar.getBoundingClientRect().width : 0;
  var intervals = window.NuxelSafeZones ? window.NuxelSafeZones.blockedIntervals(barW) : null;
  var realPlaced = ids.map(function (id) {
    var el = document.getElementById(id);
    if (!el) return null;
    var r = el.getBoundingClientRect();
    return { id: id, x: Math.round(r.x), w: Math.round(r.width), right: Math.round(r.right) };
  }).filter(Boolean);
  var realViolations = [];
  if (intervals) {
    realPlaced.forEach(function (p) {
      intervals.forEach(function (iv) {
        if (Math.min(p.right, iv.end) - Math.max(p.x, iv.start) > 0.5) realViolations.push({ id: p.id, zone: iv.zone });
      });
    });
  }
  out.blockedBoxes = blockedBoxes;
  out.previewBlockedZones = previewBlocked;
  out.previewReport = report;
  out.previewItemRects = pvRects;
  out.realBlockedIntervals = intervals;
  out.realPlaced = realPlaced;
  out.realViolations = realViolations;
  out.ok = (blockedBoxes.length === 2 && realViolations.length === 0);
  // Return the launcher to the unblocked state so the screenshot is the plain
  // launcher (the editor preview is not persisted without a host).
  if (window.NuxelSafeZones) { window.NuxelSafeZones.cancelPreview(); }
  return JSON.stringify(out);
})()
"""

WALLPAPER_JS = r"""
(function () {
  if (window.__nuxelWallpaper) return JSON.stringify(window.__nuxelWallpaper);
  window.__nuxelWallpaper = { state: 'pending' };
  (function () {
    var out = { state: 'running', samples: {} };
    function hex(buf) {
      return Array.prototype.slice.call(new Uint8Array(buf)).map(function (b) {
        return ('0' + b.toString(16)).slice(-2);
      }).join('');
    }
    // (a) fetch the exact bytes the served tree hands out and digest them
    fetch('assets/nuxel-background.png').then(function (r) {
      out.status = r.status;
      out.contentType = r.headers.get('content-type');
      return r.arrayBuffer();
    }).then(function (buf) {
      out.bytes = buf.byteLength;
      out.magic = hex(buf.slice(0, 8));
      if (window.crypto && crypto.subtle && crypto.subtle.digest) {
        return crypto.subtle.digest('SHA-256', buf).then(function (h) { out.sha256 = hex(h); });
      }
      out.sha256 = null;
      out.digestReason = 'crypto.subtle unavailable';
    }).catch(function (e) { out.fetchError = String((e && e.message) || e); })
    .then(function () {
      // (b) decode + draw it: proves the wallpaper the launcher paints is the
      //     repository asset and that WebKit renders the expected pixel bytes.
      return new Promise(function (resolve) {
        var img = new Image();
        img.onload = function () {
          out.naturalSize = [img.naturalWidth, img.naturalHeight];
          try {
            var c = document.createElement('canvas');
            c.width = 8; c.height = 16;
            var g = c.getContext('2d');
            g.drawImage(img, 0, 0, 8, 16);
            [['tl', 0, 0], ['tr', 7, 0], ['center', 4, 8], ['bl', 0, 15], ['br', 7, 15]].forEach(function (p) {
              var d = g.getImageData(p[1], p[2], 1, 1).data;
              out.samples[p[0]] = [d[0], d[1], d[2], d[3]];
            });
          } catch (e) { out.drawError = String((e && e.message) || e); }
          resolve();
        };
        img.onerror = function () { out.imageError = 'wallpaper image failed to decode'; resolve(); };
        img.src = 'assets/nuxel-background.png';
      });
    }).then(function () {
      out.state = 'done';
      window.__nuxelWallpaper = out;
    });
  })();
  return JSON.stringify({ state: 'pending' });
})()
"""


class Harness(object):
    """Sequential WebKit driver: every step is a callback-completed stage."""

    def __init__(self, args):
        self.a = args
        self.win = None
        self.view = None
        self.result = {
            'harness': 'docs/beta-finalization/vm/guest-launcher-parity.py',
            'briq': 'briq-11a-vm-launcher-parity',
            'access_tier': 'VM-only',
            'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'guest': {},
            'base_url': args.base_url,
            'launcher_url': args.base_url.rstrip('/') + '/pwa/nuxel-home/index.html',
            'checks': {},
            'artifacts': {},
            'errors': [],
            'steps': [],
        }
        self.steps = [
            ('boot', self.step_boot),
            ('wait_launcher_ready', self.step_wait_ready),
            ('probe_launcher', self.step_probe_launcher),
            ('probe_wallpaper', self.step_probe_wallpaper),
            ('probe_serviceworker', self.step_probe_serviceworker),
            ('zone_matrix', self.step_zone_matrix),
            ('editor_iframe', self.step_editor_iframe),
            ('interactions', self.step_interactions),
            ('launcher_artifacts', self.step_launcher_artifacts),
            ('colourtest', self.step_colourtest),
            ('apps', self.step_apps),
            ('finish', self.step_finish),
        ]

    # ---- logging ---------------------------------------------------------
    def log(self, msg):
        sys.stdout.write('[parity] %s\n' % (msg,))
        sys.stdout.flush()

    def record(self, name, value):
        self.result['checks'][name] = value

    # ---- guest identity --------------------------------------------------
    def guest_identity(self):
        g = {}
        for key, cmd in (
            ('hostname', ['hostname']),
            ('kernel', ['uname', '-r']),
            ('arch', ['uname', '-m']),
            ('fedora', ['bash', '-lc', 'cat /etc/fedora-release 2>/dev/null']),
            ('webkit2gtk', ['bash', '-lc', 'rpm -q --qf "%{VERSION}-%{RELEASE}\\n" webkit2gtk4.1 2>/dev/null']),
            ('phoc', ['bash', '-lc', 'rpm -q --qf "%{VERSION}-%{RELEASE}\\n" phoc 2>/dev/null']),
            ('phosh', ['bash', '-lc', 'rpm -q --qf "%{VERSION}-%{RELEASE}\\n" phosh 2>/dev/null']),
            ('gdk_scale', ['bash', '-lc', 'echo GDK_SCALE=${GDK_SCALE:-unset} GDK_DPI_SCALE=${GDK_DPI_SCALE:-unset}']),
            ('display_size', ['bash', '-lc', 'wlr-randr 2>/dev/null || swaymsg -t get_outputs 2>/dev/null || echo unknown']),
            ('wayland_display', ['bash', '-lc', 'echo ${WAYLAND_DISPLAY:-unset}']),
        ):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                g[key] = (r.stdout or r.stderr or '').strip()
            except Exception as exc:
                g[key] = 'unavailable: %r' % (exc,)
        self.result['guest'] = g

    # ---- WebKit helpers --------------------------------------------------
    def eval_js(self, script, cb):
        def done(view, result, data=None):
            val = None
            err = None
            try:
                val = view.evaluate_javascript_finish(result)
                if val is None:
                    err = 'no value'
            except Exception as exc:
                err = repr(exc)
            text = None
            if val is not None:
                try:
                    text = val.to_string()
                except Exception as exc:
                    err = 'to_string failed: %r' % (exc,)
            cb(text, err)
        try:
            self.view.evaluate_javascript(script, -1, None, None, None, done, None)
        except Exception as exc:
            cb(None, repr(exc))

    def eval_json(self, script, cb):
        def handle(text, err):
            if err or not text:
                cb(None, err or 'empty result')
                return
            try:
                cb(json.loads(text), None)
            except Exception as exc:
                cb(None, 'not JSON: %r :: %.200s' % (exc, text))
        self.eval_js(script, handle)

    def load(self, url, cb, settle_ms=900):
        box = {}

        def on_changed(view, event):
            if event != WebKit2.LoadEvent.FINISHED or box.get('done'):
                return
            box['done'] = True
            try:
                view.disconnect(box['id'])
            except Exception:
                pass
            GLib.timeout_add(settle_ms, cb)
        box['id'] = self.view.connect('load-changed', on_changed)
        self.view.load_uri(url)

    def wait_until(self, cond_js, cb, timeout=30.0, interval=0.3):
        state = {'t0': time.time()}

        def tick():
            if time.time() - state['t0'] > timeout:
                cb(False)
                return

            def handle(text, err):
                if text and text.strip() == 'true':
                    cb(True)
                else:
                    GLib.timeout_add(int(interval * 1000), tick)
            self.eval_js(cond_js, handle)
        tick()

    def snapshot(self, path, cb, full=False):
        region = WebKit2.SnapshotRegion.FULL_DOCUMENT if full else WebKit2.SnapshotRegion.VISIBLE

        def done(view, result, data=None):
            err = None
            try:
                surf = view.get_snapshot_finish(result)
                if hasattr(surf, 'get_surface'):
                    surf = surf.get_surface()
                surface = surf
                if surface is None:
                    err = 'no surface'
                else:
                    surface.write_to_png(path)
                    if not os.path.exists(path) or os.path.getsize(path) == 0:
                        err = 'png not written'
            except Exception as exc:
                err = repr(exc)
            cb(err)
        try:
            self.view.get_snapshot(region, WebKit2.SnapshotOptions.NONE, None, done, None)
        except Exception as exc:
            cb(repr(exc))

    def grim(self, path):
        try:
            r = subprocess.run(['grim', path], capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                return 'grim rc=%d %s' % (r.returncode, (r.stderr or '').strip())
            return None
        except Exception as exc:
            return 'grim unavailable: %r' % (exc,)

    def dump_dom(self, name, cb):
        def handle(text, err):
            if err or text is None:
                cb(None, err)
                return
            path = os.path.join(self.a.outdir, 'dom', name + '.html')
            try:
                with open(path, 'w') as fh:
                    fh.write(text)
                cb(path, None)
            except Exception as exc:
                cb(None, repr(exc))
        self.eval_js('document.documentElement.outerHTML', handle)

    def art(self, kind, name, path, err=None):
        entry = {'kind': kind, 'name': name, 'path': os.path.basename(path)}
        if os.path.exists(path):
            entry['bytes'] = os.path.getsize(path)
        entry['ok'] = os.path.exists(path) and not err
        if err:
            entry['error'] = err
        self.result['artifacts'].setdefault(kind, []).append(entry)
        self.log('%s %s -> %s%s' % ('OK  ' if entry['ok'] else 'FAIL', kind, os.path.basename(path),
                                    '' if not err else ' (%s)' % err))
        return entry

    def out(self, *parts):
        p = os.path.join(self.a.outdir, *parts)
        d = os.path.dirname(p)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        return p

    # ---- driver ----------------------------------------------------------
    def _start(self):
        self._run(0)

    def _run(self, i):
        if i >= len(self.steps):
            self.log('all steps complete')
            cb = getattr(self, 'on_complete', None)
            if cb:
                cb()
            return
        name, fn = self.steps[i]
        self.result['steps'].append(name)
        self.log('=== step %d/%d: %s ===' % (i + 1, len(self.steps), name))

        def cont(*_a):
            GLib.idle_add(self._run, i + 1)
        try:
            fn(cont)
        except Exception as exc:
            self.result['errors'].append('step %s raised %r' % (name, exc))
            self.log('step %s raised %r' % (name, exc))
            GLib.idle_add(self._run, i + 1)

PROBE_APP = r"""
(function () {
  var body = document.body;
  return JSON.stringify({
    url: location.href,
    title: document.title,
    readyState: document.readyState,
    elements: document.getElementsByTagName('*').length,
    bodyChildren: body ? body.children.length : 0,
    scripts: document.scripts.length,
    textLength: body ? ((body.innerText || '').length) : 0,
    hasManifest: !!document.querySelector('link[rel=manifest]'),
    visibleRoots: body ? Array.prototype.slice.call(body.children).map(function (e) {
      var r = e.getBoundingClientRect();
      return { tag: e.tagName, id: e.id || null, cls: (typeof e.className === 'string' ? e.className : null), w: Math.round(r.width), h: Math.round(r.height) };
    }).slice(0, 8) : [],
    errors: window.__nuxelErrors || []
  });
})()
"""

PROBE_COLOURTEST = r"""
(function () {
  function css(el, p) { return el ? getComputedStyle(el)[p] : null; }
  var sw = document.getElementById('swatch');
  var rep = document.getElementById('report');
  var thirds = document.getElementById('thirds');
  var btns = Array.prototype.slice.call(document.querySelectorAll('#controls button'));
  var out = {
    url: location.href,
    title: document.title,
    report: rep ? rep.textContent : null,
    swatchBackground: css(sw, 'backgroundColor'),
    swatchBgImage: css(sw, 'backgroundImage'),
    thirdsDisplay: css(thirds, 'display'),
    labelName: (document.getElementById('name') || {}).textContent,
    labelHex: (document.getElementById('hex') || {}).textContent,
    buttons: btns.map(function (b) { return b.getAttribute('data-c'); }),
    activeButton: (btns.filter(function (b) { return b.classList.contains('active'); })[0] || {}).getAttribute
      ? (btns.filter(function (b) { return b.classList.contains('active'); })[0]).getAttribute('data-c') : null,
    errors: window.__nuxelErrors || [],
    // cycle the swatch by tapping it (the one-finger path used on the phone)
    cycle: []
  };
  if (sw && sw.click) {
    for (var i = 0; i < 3; i++) {
      sw.click();
      out.cycle.push({ name: (document.getElementById('name') || {}).textContent,
                       bg: css(document.getElementById('swatch'), 'backgroundColor') });
    }
  }
  return JSON.stringify(out);
})()
"""


# ---------------------------------------------------------------------------
# Step bodies.  They are ordinary functions bound onto Harness below (the
# driver is a callback trampoline, so each step signals completion by calling
# its `nxt` continuation).
# ---------------------------------------------------------------------------
def each(self, fns, done):
    """Run callback-style stages strictly in order (each calls its own `nxt`)."""
    idx = {'n': 0}

    def step():
        if idx['n'] >= len(fns):
            done()
            return
        fn = fns[idx['n']]
        idx['n'] += 1
        fn(lambda *_: GLib.idle_add(step))
    step()


def step_boot(self, nxt):
    """Create the real WebKit view on the live Phosh session and load Nuxel Home."""
    self.guest_identity()
    self.win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    self.win.set_decorated(False)
    self.win.set_resizable(False)
    self.win.set_default_size(self.a.width, self.a.height)
    self.win.set_title('Nuxel Home (VM parity harness)')
    self.view = WebKit2.WebView()
    st = self.view.get_settings()
    for prop, val in (('enable-write-console-messages-to-stdout', True),
                      ('enable-javascript', True),
                      ('enable-developer-extras', True)):
        try:
            st.set_property(prop, val)
        except Exception as exc:
            self.log('setting %s failed: %r' % (prop, exc))
    try:
        frames = WebKit2.UserContentInjectedFrames.TOP_FRAME
        when = None
        for cand in ('START', 'DOCUMENT_START', 'AT_DOCUMENT_START'):
            when = getattr(WebKit2.UserScriptInjectionTime, cand, None)
            if when is not None:
                break
        if when is None:
            raise RuntimeError('no UserScriptInjectionTime.DOCUMENT_START variant found')
        script = WebKit2.UserScript.new(PRELUDE, frames, when, None, None)
        self.view.get_user_content_manager().add_script(script)
        self.log('console/error prelude injected at document start (enum=%r)' % (when,))
    except Exception as exc:
        self.log('user-script injection failed: %r' % (exc,))
    self.win.add(self.view)
    self.win.show_all()
    self.win.present()
    self.log('window %dx%d shown; loading %s' % (self.a.width, self.a.height, self.result['launcher_url']))
    self.load(self.result['launcher_url'], nxt, settle_ms=2000)


def step_wait_ready(self, nxt):
    """Wait for the launcher's own boot to finish (body.ready + tiles built)."""
    cond = ("(document.body && document.body.classList.contains('ready') && "
            "document.querySelectorAll('#app-list .app-item').length > 0 && "
            "document.readyState === 'complete') ? 'true' : 'false'")

    def waited(ok):
        self.record('launcher_ready_within_timeout', bool(ok))
        self.log('launcher ready: %s' % ok)
        GLib.timeout_add(1500, nxt)
    self.wait_until(cond, waited, timeout=self.a.ready_timeout)


def step_probe_launcher(self, nxt):
    def handle(data, err):
        if err:
            self.result['errors'].append('probe_launcher: %s' % err)
        self.result['launcher'] = data
        self.log('launcher probe: tiles=%s statusbar=%s safezones=%s' % (
            (data or {}).get('grid', {}).get('tiles'),
            (data or {}).get('statusBar', {}).get('version'),
            (data or {}).get('safeZones', {}).get('zones')))
        nxt()
    self.eval_json(PROBE_LAUNCHER, handle)


def step_probe_wallpaper(self, nxt):
    """Fetch + decode the wallpaper asset from the served tree and digest it."""
    state = {'t0': time.time(), 'done': False}

    def finish(payload):
        if state['done']:
            return
        state['done'] = True
        self.result['wallpaper'] = payload
        self.log('wallpaper: state=%s sha256=%s bytes=%s' % (
            payload.get('state'), payload.get('sha256'), payload.get('bytes')))
        nxt()

    def poll():
        if state['done']:
            return
        if time.time() - state['t0'] > 45:
            finish({'state': 'timeout'})
            return

        def handle(text, err):
            if err:
                finish({'state': 'error', 'error': err})
                return
            try:
                payload = json.loads(text)
            except Exception:
                GLib.timeout_add(400, poll)
                return
            if payload.get('state') == 'done':
                finish(payload)
            else:
                GLib.timeout_add(400, poll)
        self.eval_js("JSON.stringify(window.__nuxelWallpaper || {state:'pending'})", handle)
    self.eval_js(WALLPAPER_JS, lambda *_: GLib.timeout_add(400, poll))


SW_JS = r"""
(function () {
  if (window.__nuxelSW) return 'true';
  window.__nuxelSW = { state: 'pending' };
  var out = {
    state: 'running',
    supported: !!navigator.serviceWorker,
    controller: !!(navigator.serviceWorker && navigator.serviceWorker.controller),
    controllerScript: (navigator.serviceWorker && navigator.serviceWorker.controller)
      ? navigator.serviceWorker.controller.scriptURL : null
  };
  var jobs = [];
  if (navigator.serviceWorker && navigator.serviceWorker.getRegistrations) {
    jobs.push(navigator.serviceWorker.getRegistrations().then(function (rs) {
      out.registrations = rs.map(function (r) {
        return {
          scope: r.scope,
          active: r.active ? r.active.state : null,
          activeScript: r.active ? r.active.scriptURL : null,
          installing: r.installing ? r.installing.state : null,
          waiting: r.waiting ? r.waiting.state : null
        };
      });
    }).catch(function (e) { out.registrationError = String((e && e.message) || e); }));
  }
  if (window.caches && caches.keys) {
    jobs.push(caches.keys().then(function (k) { out.caches = k; })
      .catch(function (e) { out.cachesError = String((e && e.message) || e); }));
  }
  Promise.all(jobs).then(function () {
    out.state = 'done';
    window.__nuxelSW = out;
  }).catch(function (e) {
    out.state = 'done';
    out.error = String((e && e.message) || e);
    window.__nuxelSW = out;
  });
  return 'true';
})()
"""


def step_probe_serviceworker(self, nxt):
    """Service worker + cache namespace state of the running launcher."""
    state = {'t0': time.time(), 'done': False}

    def finish(payload):
        if state['done']:
            return
        state['done'] = True
        self.result['serviceWorker'] = payload
        self.log('service worker: controller=%s regs=%s caches=%s' % (
            payload.get('controller'),
            [r.get('active') for r in (payload.get('registrations') or [])], payload.get('caches')))
        nxt()

    def poll():
        if state['done']:
            return
        if time.time() - state['t0'] > 25:
            finish({'state': 'timeout'})
            return

        def handle(text, err):
            if err:
                finish({'state': 'error', 'error': err})
                return
            try:
                payload = json.loads(text)
            except Exception:
                GLib.timeout_add(400, poll)
                return
            if payload.get('state') == 'done':
                finish(payload)
            else:
                GLib.timeout_add(400, poll)
        self.eval_js("JSON.stringify(window.__nuxelSW || {state:'pending'})", handle)
    self.eval_js(SW_JS, lambda *_: GLib.timeout_add(400, poll))


def step_zone_matrix(self, nxt):
    """Blocked-zone -> exclusion invariant over a matrix of zone sets."""
    def handle(data, err):
        if err:
            self.result['errors'].append('zone_matrix: %s' % err)
        self.result['zone_matrix'] = data
        cases = (data or {}).get('cases', [])
        bad = [c['case'] for c in cases if c.get('violations')]
        self.log('zone matrix: %d cases, violations in: %s' % (len(cases), bad or 'none'))
        nxt()
    self.eval_json(PROBE_ZONE_MATRIX, handle)


def step_editor_iframe(self, nxt):
    """Drive the real ten-zone editor in the Settings app inside the launcher."""
    shot = self.out('screenshots', 'vm-gl-05-settings-safe-zone-editor.png')
    grim_png = self.out('screenshots', 'vm-grim-05-settings-safe-zone-editor.png')
    tries = {'n': 0}

    def attempt():
        tries['n'] += 1

        def handle(data, err):
            if err:
                self.result['errors'].append('editor: %s' % err)
            if isinstance(data, dict) and str(data.get('error', '')).startswith('no zone boxes') and tries['n'] < 5:
                GLib.timeout_add(2000, attempt)
                return
            self.result['editor'] = data
            self.log('editor probe (attempt %d): %s' % (tries['n'], json.dumps(data)[:400] if data else None))

            def after_shot(e1):
                self.art('screenshot', 'editor-in-launcher', shot, e1)
                gerr = self.grim(grim_png)
                self.art('screenshot', 'editor-in-launcher-grim', grim_png, gerr)
                self.eval_js("(function(){var f=document.getElementById('__parity_editor_frame');"
                             "if(f&&f.parentNode)f.parentNode.removeChild(f);return 'true';})()",
                             lambda *_: GLib.timeout_add(800, nxt))
            self.snapshot(shot, after_shot)
        self.eval_json(PROBE_EDITOR_DRIVE, handle)
    self.eval_json(PROBE_EDITOR_IFRAME, lambda *_: GLib.timeout_add(3500, attempt))


def step_interactions(self, nxt):
    """Quick settings + search: synthetic taps on the real DOM controls."""
    drive = r"""
(function () {
  var out = {};
  var qs = window.qs;
  if (qs && qs.toggle) qs.toggle();
  var panel = document.getElementById('quick-settings');
  out.qs_opened = panel ? !panel.classList.contains('hidden') : null;
  var wifi = document.getElementById('qs-wifi');
  out.wifi_before = wifi ? wifi.dataset.enabled : null;
  if (wifi) wifi.click();
  out.wifi_after = wifi ? wifi.dataset.enabled : null;
  var so = document.getElementById('search-overlay');
  if (window.search && window.search.open) window.search.open();
  out.search_opened = so ? !so.classList.contains('hidden') : null;
  var input = document.getElementById('search-input');
  out.search_results = {};
  if (input) {
    ['term', 'set', 'zzz'].forEach(function (q) {
      input.value = q;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      out.search_results[q] = document.querySelectorAll('#search-results .search-result-item').length;
    });
    input.value = '';
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }
  if (window.search && window.search.close) window.search.close();
  out.search_closed = so ? so.classList.contains('hidden') : null;
  if (qs && qs.toggle && panel && !panel.classList.contains('hidden')) qs.toggle();
  out.qs_closed = panel ? panel.classList.contains('hidden') : null;
  return JSON.stringify(out);
})()
"""

    def handle(data, err):
        if err:
            self.result['errors'].append('interactions: %s' % err)
        self.result['interactions'] = data
        self.log('interactions: %s' % (json.dumps(data)[:400] if data else None))
        GLib.timeout_add(800, nxt)
    self.eval_json(drive, handle)


def step_launcher_artifacts(self, nxt):
    """Screenshot + DOM evidence of the plain launcher (real render, real WM)."""
    visible = self.out('screenshots', 'vm-gl-01-launcher-visible.png')
    full = self.out('screenshots', 'vm-gl-02-launcher-fulldocument.png')
    grim_png = self.out('screenshots', 'vm-grim-01-launcher.png')

    def s1(n1):
        self.snapshot(visible, lambda e: (self.art('screenshot', 'launcher-visible', visible, e), n1()))
    def s2(n2):
        self.snapshot(full, lambda e: (self.art('screenshot', 'launcher-fulldocument', full, e), n2()), full=True)
    def s3(n3):
        err = self.grim(grim_png)
        self.art('screenshot', 'launcher-grim', grim_png, err)
        n3()
    def s4(n4):
        self.dump_dom('launcher', lambda path, derr: (self.art('dom', 'launcher', path or visible, derr), n4()))
    self.each([s1, s2, s3, s4], nxt)


def step_colourtest(self, nxt):
    """colour-test.html: the page the handset owner uses for the ABGR check."""
    url = self.result['base_url'].rstrip('/') + '/pwa/nuxel-home/colour-test.html'
    shot = self.out('screenshots', 'vm-gl-06-colour-test.png')
    grim_png = self.out('screenshots', 'vm-grim-06-colour-test.png')

    def loaded():
        def handle(data, err):
            if err:
                self.result['errors'].append('colourtest: %s' % err)
            self.result['colourtest'] = data
            self.log('colour-test: swatch=%s report=%s' % (
                (data or {}).get('swatchBackground'), (data or {}).get('report')))

            def s1(n1):
                self.snapshot(shot, lambda e: (self.art('screenshot', 'colour-test-visible', shot, e), n1()))
            def s2(n2):
                gerr = self.grim(grim_png)
                self.art('screenshot', 'colour-test-grim', grim_png, gerr)
                n2()
            def s3(n3):
                self.dump_dom('colour-test', lambda path, derr: (self.art('dom', 'colour-test', path or shot, derr), n3()))
            self.each([s1, s2, s3], lambda: GLib.timeout_add(200, nxt))
        self.eval_json(PROBE_COLOURTEST, handle)
    self.load(url, loaded, settle_ms=1200)


def step_apps(self, nxt):
    """Every PWA in the launcher registry: load, collect console errors, dump DOM."""
    launcher = self.result.get('launcher') or {}
    entries = [e for e in (launcher.get('registry', {}) or {}).get('entries', [])
               if e.get('type') == 'pwa' and (e.get('url') or '').endswith('.html')]
    if not entries:
        entries = [{'id': 'org.nuxel.Terminal', 'name': 'Terminal', 'url': '/pwa/nuxel-apps/terminal/index.html'}]
    self.result['apps'] = {}
    i = {'n': 0}

    def next_app():
        if i['n'] >= len(entries):
            GLib.timeout_add(200, nxt)
            return
        entry = entries[i['n']]
        i['n'] += 1
        url = self.result['base_url'].rstrip('/') + entry['url']
        slug = entry['id'].replace('.', '-')
        self.log('app %d/%d %s -> %s' % (i['n'], len(entries), entry['id'], url))

        def loaded():
            def handle(data, err):
                rec = data or {}
                rec['error'] = err
                rec['expected_id'] = entry['id']
                self.result['apps'][entry['id']] = rec
                errors = rec.get('errors') or []
                app_err = [e for e in errors if not _is_bridge_error(e)]
                bridge_err = [e for e in errors if _is_bridge_error(e)]
                self.log('  %s: elements=%s errors=%d (app=%d bridge=%d)' % (
                    entry['id'], rec.get('elements'), len(errors), len(app_err), len(bridge_err)))

                def after_dom(*_):
                    shot = self.out('screenshots', 'vm-gl-10-app-%s.png' % slug)

                    def after_shot(e2):
                        self.art('screenshot', 'app-%s' % entry['id'], shot, e2)
                        GLib.timeout_add(150, next_app)
                    self.snapshot(shot, after_shot)
                self.dump_dom('app-' + slug, after_dom)
            self.eval_json(PROBE_APP, handle)
        self.load(url, loaded, settle_ms=1400)
    next_app()


def step_finish(self, nxt):
    """Derive the honest check verdicts and write the JSON result."""
    self.result['finished'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    self.result['checks'] = derive_checks(self.result)
    verdicts = self.result['checks']
    passed = [k for k, v in verdicts.items() if v.get('verdict') == 'PASS']
    failed = [k for k, v in verdicts.items() if v.get('verdict') == 'FAIL']
    nver = [k for k, v in verdicts.items() if v.get('verdict') == 'NOT-VERIFIED-HERE']
    self.result['summary'] = {'pass': len(passed), 'fail': len(failed), 'not_verified_here': len(nver),
                              'failed_checks': failed, 'not_verified_checks': nver}
    with open(self.a.json, 'w') as fh:
        json.dump(self.result, fh, indent=2, sort_keys=True)
    self.log('RESULT pass=%d fail=%d not-verified=%d -> %s' % (len(passed), len(failed), len(nver), self.a.json))
    self.log('FAILED: %s' % (failed or 'none'))
    self.log('NOT VERIFIED HERE: %s' % (nver or 'none'))
    nxt()


def _is_bridge_error(entry):
    text = (entry.get('text') or '') + ' ' + str(entry.get('level') or '')
    return any(marker in text for marker in (
        'X-Nuxel-Bridge-Version', 'access control', 'Load failed', '[Bridge]', 'CORS'))


def _verdict(name, ok, detail):
    if ok is None:
        return {'verdict': 'NOT-VERIFIED-HERE', 'detail': detail}
    return {'verdict': 'PASS' if ok else 'FAIL', 'detail': detail}


def derive_checks(result):
    """Turn the raw observations into honest PASS / FAIL / NOT-VERIFIED-HERE.

    A PASS here means "observed in the UTM VM on the reference Phosh/WebKitGTK
    stack".  It is never evidence for the S10+ handset.
    """
    exp = result.get('expect') or {}
    checks = {}
    lb = result.get('launcher') or {}

    # 1. the launcher page really loads and its JavaScript builds the UI ------
    grid = lb.get('grid') or {}
    tiles = grid.get('tiles') or 0
    labels = grid.get('labels') or []
    checks['launcher_loads_and_js_builds_ui'] = _verdict(
        'launcher_loads_and_js_builds_ui',
        bool(tiles) and len(labels) == tiles and bool(lb.get('bodyReady')),
        'tiles=%s labelled=%s docked=%s dots=%s bodyReady=%s viewport=%s' % (
            tiles, len(labels), grid.get('dockTiles'), grid.get('pageDots'),
            lb.get('bodyReady'), lb.get('viewport')))

    # 2. status-bar revision: one source of truth ----------------------------
    sb = lb.get('statusBar') or {}
    ver, gver = sb.get('version'), sb.get('globalVersion')
    exp_ver = exp.get('status_bar_version') or exp.get('manifest_pwa_version')
    ok = bool(ver) and ver == gver and (not exp_ver or ver == exp_ver)
    checks['status_bar_single_source_of_truth'] = _verdict(
        'status_bar_single_source_of_truth', ok,
        'running=%s global=%s repo_status_bar=%s manifest.pwa_version=%s sw.cache_version=%s' % (
            ver, gver, exp.get('status_bar_version'), exp.get('manifest_pwa_version'),
            exp.get('sw_cache_version')))

    # 3. ten-zone engine -----------------------------------------------------
    sz = lb.get('safeZones') or {}
    checks['safe_zones_ten_zone_engine'] = _verdict(
        'safe_zones_ten_zone_engine', sz.get('zones') == 10,
        'zones=%s presets=%s active=%s' % (sz.get('zones'), sz.get('presets'), sz.get('activeZones')))

    # 4. blocked-zone exclusion invariant (matrix) ---------------------------
    zm = result.get('zone_matrix') or {}
    cases = zm.get('cases') or []
    clean, honest_drops, dishonest = [], [], []
    for c in cases:
        if not c.get('violations'):
            clean.append(c['case'])
            continue
        plan = c.get('plannerReport') or {}
        dropped = plan.get('dropped') or []
        reasons = sorted(set(d.get('reason') for d in dropped))
        dropped_clusters = set((d.get('cluster') or '').split(' ')[0] for d in dropped)
        viol_clusters = set(c.get('violationClusters') or [])
        documented = reasons and all(r in ('no_free_interval', 'free_interval_narrower_than_cluster') for r in reasons)
        covered = viol_clusters and viol_clusters.issubset(dropped_clusters)
        if documented and covered:
            honest_drops.append({'case': c['case'], 'zones': c['zones'], 'reasons': reasons})
        else:
            dishonest.append({'case': c['case'], 'violations': c.get('violations'),
                              'reasons': reasons, 'dropped_clusters': sorted(dropped_clusters)})
    checks['safe_zones_blocked_zone_exclusion_matrix'] = _verdict(
        'safe_zones_blocked_zone_exclusion_matrix',
        bool(cases) and not dishonest,
        'cases=%d clean=%s impossible_reported_as_drop=%s unexplained_violations=%s' % (
            len(cases), clean, honest_drops or 'none', dishonest or 'none'))

    # 4b. the narrow-gap case must be reported, not silently overlapping -----
    narrow_ok, narrow_detail = None, 'no narrow-gap case exercised'
    for c in cases:
        for d in ((c.get('plannerReport') or {}).get('dropped') or []):
            if d.get('reason') == 'free_interval_narrower_than_cluster':
                gap = d.get('free')
                w = d.get('width')
                narrow_ok = bool(gap and w is not None and (gap[1] - gap[0]) < w)
                narrow_detail = 'case=%s cluster=%s gap=%s clusterWidth=%s reported=%s' % (
                    c['case'], d.get('cluster'), gap, w, narrow_ok)
    checks['safe_zones_narrow_gap_reported_not_hidden'] = _verdict(
        'safe_zones_narrow_gap_reported_not_hidden', narrow_ok, narrow_detail)

    # 5. the editor in Settings excludes the blocked zones -------------------
    ed = result.get('editor') or {}
    ed_ok = bool(ed.get('ok')) and sorted(ed.get('blockedBoxes') or []) == ['10', '9'] \
        and not (ed.get('realViolations') or [])
    checks['safe_zone_editor_excludes_blocked_zones'] = _verdict(
        'safe_zone_editor_excludes_blocked_zones', ed_ok,
        'zone_boxes=%s blocked_pressed=%s editor_preview_blocked=%s real_bar_intervals=%s real_bar_violations=%s' % (
            ed.get('zoneBoxes'), sorted(ed.get('blockedBoxes') or []), ed.get('previewBlockedZones'),
            ed.get('realBlockedIntervals'), ed.get('realViolations')))

    # 6. wallpaper bytes -----------------------------------------------------
    wp = result.get('wallpaper') or {}
    exp_wp = exp.get('wallpaper_sha256')
    if not wp.get('sha256'):
        wp_ok = None
    else:
        wp_ok = (wp.get('sha256') == exp_wp) if exp_wp else None
    checks['wallpaper_bytes_match_repository'] = _verdict(
        'wallpaper_bytes_match_repository', wp_ok,
        'vm_sha256=%s repo_sha256=%s bytes=%s natural=%s samples=%s' % (
            wp.get('sha256'), exp_wp, wp.get('bytes'), wp.get('naturalSize'), wp.get('samples')))

    # 7. colour pipeline bytes (WebKit side) ---------------------------------
    col = lb.get('colour') or {}
    expect_rgba = {'red': [255, 0, 0, 255], 'green': [0, 255, 0, 255], 'blue': [0, 0, 255, 255],
                   'white': [255, 255, 255, 255], 'black': [0, 0, 0, 255], 'grey': [128, 128, 128, 255]}
    col_bad = {k: v.get('rgba') for k, v in col.items()
               if isinstance(v, dict) and v.get('rgba') != expect_rgba.get(k)}
    checks['colour_pipeline_bytes_webkit_side'] = _verdict(
        'colour_pipeline_bytes_webkit_side', bool(col) and not col_bad and 'error' not in col,
        'rgba=%s mismatches=%s' % ({k: v.get('rgba') for k, v in col.items() if isinstance(v, dict)},
                                   col_bad or 'none'))

    # 7b. the DECON ABGR panel conversion is NOT observable from a web page ---
    checks['decon_abgr_panel_conversion'] = _verdict(
        'decon_abgr_panel_conversion', None,
        'not observable in the VM: the panel byte order (XRGB8888 shm -> DECON ABGR_8888) is owned by '
        'nuxel-wl-fb on the handset; the VM has no framebuffer bridge. See docs/beta-finalization/boot/COLOUR-CONVERSION.md '
        'and area 3.4 of the manual proof checklist.')

    # 8. colour-test page (the page used on the handset) ---------------------
    ct = result.get('colourtest') or {}
    checks['colour_test_page_renders_expected_rgb'] = _verdict(
        'colour_test_page_renders_expected_rgb',
        str(ct.get('swatchBackground')) in ('rgb(255, 0, 0)', 'rgba(255, 0, 0, 1)') and bool(ct.get('report')),
        'initial_swatch=%s report=%.120s cycle=%s' % (ct.get('swatchBackground'), str(ct.get('report')), ct.get('cycle')))

    # 9. service worker: registered, active, cache namespaced ---------------
    sw = result.get('serviceWorker') or {}
    regs = sw.get('registrations') or []
    active = [r for r in regs if r.get('active') == 'activated']
    exp_cache = exp.get('sw_cache_version')
    cached = [c for c in (sw.get('caches') or []) if exp_cache and exp_cache in c]
    checks['service_worker_registered_and_cached'] = _verdict(
        'service_worker_registered_and_cached',
        bool(active) and bool(cached) if exp_cache else None,
        'supported=%s controller=%s registrations=%s caches=%s expected_cache_suffix=%s' % (
            sw.get('supported'), sw.get('controller'), regs, sw.get('caches'), exp_cache))

    # 10. interactions -------------------------------------------------------
    it = result.get('interactions') or {}
    sr = (it.get('search_results') or {}).get('term')
    inter_ok = bool(it.get('qs_opened')) and it.get('wifi_after') == 'true' and (sr or 0) > 0 \
        and bool(it.get('search_closed')) and bool(it.get('qs_closed'))
    checks['quick_settings_and_search_interact'] = _verdict(
        'quick_settings_and_search_interact', inter_ok,
        'qs_opened=%s wifi=%s->%s search_opened=%s results(term/set/zzz)=%s search_closed=%s qs_closed=%s' % (
            it.get('qs_opened'), it.get('wifi_before'), it.get('wifi_after'), it.get('search_opened'),
            it.get('search_results'), it.get('search_closed'), it.get('qs_closed')))

    # 11. refreshed PWAs load without application console errors -------------
    apps = result.get('apps') or {}
    bad_apps = {}
    for app_id, rec in apps.items():
        errs = rec.get('errors') or []
        app_errs = [e for e in errs if not _is_bridge_error(e)]
        wk_errs = rec.get('webkit_console_errors') or []
        if app_errs or wk_errs or not rec.get('elements'):
            bad_apps[app_id] = {'dom_errors': app_errs, 'webkit_console_errors': wk_errs,
                                'elements': rec.get('elements')}
    checks['refreshed_pwa_apps_load_without_app_errors'] = _verdict(
        'refreshed_pwa_apps_load_without_app_errors', bool(apps) and not bad_apps,
        'apps=%s bad=%s' % (sorted(apps.keys()), bad_apps or 'none'))

    # 12. bridge connection from the page origin ----------------------------
    br = lb.get('bridge') or {}
    br_ok = bool(br.get('connected')) if br.get('present') else None
    checks['bridge_connected_from_page'] = _verdict(
        'bridge_connected_from_page', br_ok,
        'present=%s shared_module=%s connected=%s mockMode=%s api=%s' % (
            br.get('present'), br.get('sharedModule'), br.get('connected'), br.get('mockMode'), br.get('apiUrl')))

    # 13. boot-animation splash hand-off ------------------------------------
    bs = lb.get('bootSplash') or {}
    vid = bs.get('video') or {}
    splash_ok = bool(lb.get('bodyReady')) and (bs.get('removed') or str(bs.get('splashOpacity')) in ('0', '0.0'))
    checks['boot_splash_handoff_completes'] = _verdict(
        'boot_splash_handoff_completes', splash_ok,
        'present=%s removed=%s opacity=%s video_error=%s' % (
            bs.get('present'), bs.get('removed'), bs.get('splashOpacity'),
            (vid.get('error') or {}).get('code')))
    if vid.get('error'):
        checks['boot_animation_decodes_in_vm'] = _verdict(
            'boot_animation_decodes_in_vm', None,
            'the VM WebKitGTK cannot decode assets/nuxel-boot-animation.mp4 (video error code %s, '
            'readyState=%s): the splash therefore hides through its error path. The animation itself is '
            'the handset path (initramfs player, area 2 of the manual proof checklist).' % (
                (vid.get('error') or {}).get('code'), vid.get('readyState')))
    else:
        checks['boot_animation_decodes_in_vm'] = _verdict(
            'boot_animation_decodes_in_vm', bool(vid.get('videoWidth')),
            'readyState=%s size=%sx%s duration=%s' % (vid.get('readyState'), vid.get('videoWidth'),
                                                      vid.get('videoHeight'), vid.get('duration')))

    # 14. registry matches the repository -----------------------------------
    reg = lb.get('registry') or {}
    exp_ids = exp.get('registry_ids')
    reg_ok = (set(reg.get('ids') or []) == set(exp_ids)) if exp_ids else None
    checks['registry_matches_repository'] = _verdict(
        'registry_matches_repository', reg_ok,
        'vm_ids=%s repo_ids=%s' % (sorted(reg.get('ids') or []), sorted(exp_ids or [])))

    return checks


def main(argv=None):
    ap = argparse.ArgumentParser(description='Nuxel Home VM launcher-parity harness (guest side)')
    ap.add_argument('--base-url', default='http://127.0.0.1:8000')
    ap.add_argument('--outdir', default=os.path.expanduser('~/vm-parity-out'))
    ap.add_argument('--json', default=None)
    ap.add_argument('--expect', default=None, help='JSON file with repository-side expectations')
    ap.add_argument('--width', type=int, default=360)
    ap.add_argument('--height', type=int, default=720)
    ap.add_argument('--ready-timeout', type=float, default=40.0)
    ap.add_argument('--total-timeout', type=float, default=420.0)
    args = ap.parse_args(argv)
    if not args.json:
        args.json = os.path.join(args.outdir, 'vm-parity-result.json')

    if not (os.environ.get('WAYLAND_DISPLAY') or os.environ.get('DISPLAY')):
        sys.stderr.write('HARNESS-CANNOT-RUN: no WAYLAND_DISPLAY/DISPLAY (no graphical session)\n')
        return 2
    wt = os.environ.get('XDG_RUNTIME_DIR', '')
    if os.environ.get('WAYLAND_DISPLAY') and wt and \
            not os.path.exists(os.path.join(wt, os.environ['WAYLAND_DISPLAY'])):
        sys.stderr.write('HARNESS-CANNOT-RUN: wayland socket %s missing\n'
                         % os.path.join(wt, os.environ['WAYLAND_DISPLAY']))
        return 2
    for sub in ('screenshots', 'dom', 'logs'):
        os.makedirs(os.path.join(args.outdir, sub), exist_ok=True)

    h = Harness(args)
    h.result['expect'] = {}
    if args.expect and os.path.exists(args.expect):
        try:
            with open(args.expect) as fh:
                h.result['expect'] = json.load(fh)
        except Exception as exc:
            h.log('expect file unreadable: %r' % (exc,))
    h.result['ok'] = False

    def write_json():
        h.result['ok'] = os.path.exists(args.json)
        if not h.result['ok']:
            with open(args.json, 'w') as fh:
                json.dump(h.result, fh, indent=2, sort_keys=True)

    def on_complete():
        write_json()
        Gtk.main_quit()

    def on_timeout():
        h.result['aborted'] = 'total-timeout (%ss)' % args.total_timeout
        h.log('ABORT: total timeout reached')
        write_json()
        Gtk.main_quit()
    h.on_complete = on_complete
    GLib.timeout_add(int(args.total_timeout * 1000), on_timeout)
    h._start()
    Gtk.main()
    h.log('harness finished, json=%s' % args.json)
    return 0 if os.path.exists(args.json) else 2


# Bind the step bodies onto the driver class (see the comment above them).
for _fn in (each, step_boot, step_wait_ready, step_probe_launcher, step_probe_wallpaper,
            step_probe_serviceworker, step_zone_matrix, step_editor_iframe, step_interactions,
            step_launcher_artifacts,
            step_colourtest, step_apps, step_finish):
    setattr(Harness, _fn.__name__, _fn)


if __name__ == '__main__':
    sys.exit(main())

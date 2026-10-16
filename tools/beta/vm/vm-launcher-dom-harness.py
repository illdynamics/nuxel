#!/usr/bin/env python3
# =============================================================================
# tools/beta/vm/vm-launcher-dom-harness.py   (build group bg-11-vm-parity)
#
# GUEST-SIDE half of the VM launcher/status-bar/safe-zones/app parity run
# (briq-11a).  Runs INSIDE the UTM ARM64 Fedora guest, as the `nuxel` user,
# on the live Phosh/phoc 0.54 Wayland session, and drives a REAL WebKitGTK 4.1
# engine (the same engine class the Nuxel PWA host uses) against the launcher
# served by nuxel-web on 127.0.0.1:8000.
#
# What it proves, all from inside the running page (not from static files):
#   [G1] LAUNCHER GRID RENDERS - #app-grid / #app-list exist, the app tiles are
#        built BY JAVASCRIPT (data-app-id present), the .app-list computed style
#        really is a 4-column grid, the dock is populated and the two grid
#        indicator dots exist.  Tile count is compared against the registry
#        length read from the page's own AppRegistry instance.
#   [G2] STATUS BAR IS THE SINGLE SOURCE OF TRUTH - the running page publishes
#        window.NUXEL_STATUS_BAR_VERSION (class static VERSION), which must be
#        the same v0.4.x the repo serves; the live time is rendered (not 00:00)
#        and the safe-zone engine reports itself present to the status bar.
#   [G3] TEN-ZONE SAFE-AREA ENGINE EXCLUDES BLOCKED ZONES - the harness calls the
#        real window.NuxelSafeZones engine and for EVERY preset x orientation:
#          * blockedIntervals() yields exactly the declared zones,
#          * freeIntervals() is the complement (blocked zones are holes),
#          * planCluster() reports hit=true + a target inside a free interval for
#            a cluster that genuinely overlaps a blocked zone,
#        plus a live previewZones() pass that drives applyLayout() and reads the
#        #status-bar data-safezone-* attributes and the __nuxelSafeZoneReport.
#   [G4] WALLPAPER + COLOUR PIPELINE BYTES - the launcher background image is
#        loaded through the real HTTP docroot; its natural size, a browser-side
#        luminance signature and the 1x1 / 4x4 canvas colour probes are read in
#        page, and the image bytes are then fetched and SHA-256 hashed in guest
#        so the VM and the repo can be compared byte-for-byte.  The colour-order
#        test page is rendered on the live display and captured with grim.
#   [G5] REFRESHED APPS LOAD WITHOUT CONSOLE ERRORS - each registered PWA is
#        loaded in a real same-origin iframe; the harness records per-app
#        load-finished / load-failed, the child document's <title> and a body
#        marker, and captures page console messages (level >= warning) and any
#        window.onerror from the child document.
#
#   [G5a] CONSOLE / ERROR CAPTURE - an in-page UserScript (ALL_FRAMES, at START)
#        wraps console.error/warn and window 'error' / 'unhandledrejection' so
#        G5's "no console errors" claim is backed by the engine's OWN records
#        (result['console'], result['js_errors'], result['colour_page_console']).
#   [G5b] DOM DUMPS - the launcher, the colour-order page and EVERY registered
#        PWA are dumped as-built (document.documentElement.outerHTML) into
#        SHOT_DIR/dom/{launcher.html,colour-test.html,app-<id>.html} with a
#        per-file byte count + SHA-256 (result['dom'], result['app_dom']).
#
# Artifacts written to SHOT_DIR (default /tmp/nuxel-vm-parity-shots):
#   vm-launcher-home.png, vm-colour-order.png, dom/*.html, result.json
#
# HONESTY: this harness runs in the VM only.  A PASS here is VM evidence, never
# VERIFIED_ON_S10PLUS.  A step that cannot run is emitted with ok=false and a
# reason; nothing is fabricated.  No image is written to any raw block device.
#
# Usage (in the guest):
#   PWA_URL=http://127.0.0.1:8000/pwa/nuxel-home/index.html \
#   python3 tools/beta/vm/vm-launcher-dom-harness.py > out.json
# Env: PWA_URL, COLOUR_URL, SHOT_DIR, HARNESS_TIMEOUT_SEC, NUXEL_APPS_URL
# =============================================================================
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

import gi  # type: ignore
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import GLib, Gtk, WebKit2  # type: ignore

BASE = os.environ.get('NUXEL_BASE_URL', 'http://127.0.0.1:8000')
PWA_URL = os.environ.get('PWA_URL', BASE + '/pwa/nuxel-home/index.html')
COLOUR_URL = os.environ.get('COLOUR_URL', BASE + '/pwa/nuxel-home/colour-test.html')
SHOT_DIR = os.environ.get('SHOT_DIR', '/tmp/nuxel-vm-parity-shots')
TIMEOUT = int(os.environ.get('HARNESS_TIMEOUT_SEC', '180'))
os.makedirs(SHOT_DIR, exist_ok=True)

result = {
    'pwa_url': PWA_URL,
    'colour_url': COLOUR_URL,
    'shot_dir': SHOT_DIR,
    'generated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'load': {},
    'g1_launcher_grid': {},
    'g2_status_bar': {},
    'g3_safe_zones': {},
    'g4_wallpaper_colour': {},
    'g5_apps': {},
    'console': [],
    'js_errors': [],
    'screenshots': {},
}

# --- JS probes (each is a self-contained expression; the runner wraps them in
#     an async IIFE that stores the JSON string in window.__probe_result). -----
JS_LAUNCHER = r"""
(async () => {
  const out = {};
  const grid = document.getElementById('app-grid');
  const list = document.getElementById('app-list');
  const dock = document.getElementById('dock-items');
  out.appGridPresent = !!grid;
  out.appListPresent = !!list;
  out.appGrid = grid ? {w: Math.round(grid.getBoundingClientRect().width),
                        h: Math.round(grid.getBoundingClientRect().height),
                        scrollH: grid.scrollHeight} : null;
  const tiles = list ? [...list.querySelectorAll('.app-item')] : [];
  out.tileCount = tiles.length;
  out.tileIds = tiles.map(t => t.dataset.appId).filter(Boolean);
  out.tileLabels = tiles.map(t => (t.querySelector('.app-label') || {}).textContent || '').filter(Boolean);
  out.tilesHaveIcons = tiles.filter(t => !!t.querySelector('.app-icon')).length;
  if (list) {
    const cs = getComputedStyle(list);
    out.appListDisplay = cs.display;
    out.appListColumns = cs.gridTemplateColumns ? cs.gridTemplateColumns.split(' ').filter(Boolean).length : 0;
    out.appListGap = cs.gap || cs.rowGap + ' ' + cs.columnGap;
  }
  const dockTiles = dock ? [...dock.querySelectorAll('.app-item')] : [];
  out.dockCount = dockTiles.length;
  out.dockIds = dockTiles.map(t => t.dataset.appId).filter(Boolean);
  out.gridIndicatorDots = document.querySelectorAll('#app-grid .app-grid-indicator .dot').length;
  out.gridTitle = (document.querySelector('.app-grid-title') || {}).textContent || '';
  // Registry length from the page's OWN registry object (single source of truth).
  out.registryNames = (typeof NUXEL_APPS === 'object') ? Object.keys(NUXEL_APPS) : [];
  out.registryVersion = (typeof NUXEL_REGISTRY_VERSION !== 'undefined') ? NUXEL_REGISTRY_VERSION : null;
  if (window.nuxel && window.nuxel.appRegistry && window.nuxel.appRegistry.getAllApps) {
    out.registryAllCount = window.nuxel.appRegistry.getAllApps().length;
  }
  out.bodyClass = document.body ? document.body.className : '';
  out.readyState = document.readyState;
  return JSON.stringify(out);
})()
"""

JS_STATUS = r"""
(async () => {
  const out = {};
  out.statusBarVersion = (typeof window.NUXEL_STATUS_BAR_VERSION !== 'undefined') ? window.NUXEL_STATUS_BAR_VERSION : null;
  out.statusBarClass = (typeof StatusBar !== 'undefined' && StatusBar.VERSION) ? StatusBar.VERSION : null;
  const t = document.getElementById('status-time');
  out.timeText = t ? t.textContent.trim() : null;
  out.timeIsLive = !!(t && /^\d{1,2}:\d{2}$/.test(t.textContent.trim()) && t.textContent.trim() !== '00:00');
  out.safeZonesGlobal = typeof window.NuxelSafeZones !== 'undefined';
  const bar = document.getElementById('status-bar');
  out.barPresent = !!bar;
  out.barWidth = bar ? bar.clientWidth : 0;
  out.barAttrs = bar ? {
    profile: bar.getAttribute('data-safezone-profile'),
    orientation: bar.getAttribute('data-safezone-orientation'),
    blocked: bar.getAttribute('data-safezone-blocked'),
    paddingDp: bar.getAttribute('data-safezone-padding-dp')
  } : null;
  out.clusters = bar ? {
    left: !!bar.querySelector('.status-left'),
    center: !!bar.querySelector('.status-center'),
    right: !!bar.querySelector('.status-right')
  } : null;
  return JSON.stringify(out);
})()
"""

JS_SAFEZONES = r"""
(async () => {
  const out = {ZONES: null, presets: {}, clusterPlan: null, preview: null, engine: typeof window.NuxelSafeZones !== 'undefined'};
  if (!window.NuxelSafeZones) return JSON.stringify(out);
  const SZ = window.NuxelSafeZones;
  out.ZONES = SZ.ZONES;
  const orients = ['portrait', 'landscape_left', 'landscape_right'];
  const W = 720;
  function inHole(v, ivals) {
    for (let i = 0; i < ivals.length; i++) if (v >= ivals[i].start && v < ivals[i].end) return true;
    return false;
  }
  const presets = ['none', 's10plus', 'pixel_center', 'left_camera', 'right_camera'];
  const savedProfile = SZ.state.profile, savedOrientation = SZ.state.orientation;
  presets.forEach(p => {
    out.presets[p] = {};
    orients.forEach(o => {
      SZ.state.profile = p;
      SZ.state.orientation = o;
      const zones = SZ.zonesFor(p, o);
      const iv = SZ.blockedIntervals(W);
      const free = SZ.freeIntervals(W, iv);
      const zw = W / SZ.ZONES;
      let centresExcluded = true, checked = 0;
      zones.forEach(z => {
        const mid = (z - 1) * zw + zw / 2;
        checked++;
        if (!inHole(mid, iv)) centresExcluded = false;
      });
      let freeClean = true, freeInside = true;
      free.forEach(f => {
        if (inHole(f.start + 0.5, iv) || inHole(f.end - 0.5, iv)) freeClean = false;
        if (f.start < 0 || f.end > W + 0.5) freeInside = false;
      });
      out.presets[p][o] = {
        zones: zones, blockedIntervals: iv.length, freeIntervals: free.length,
        blockedCentresExcluded: centresExcluded, blockedZonesChecked: checked,
        freeIntervalsClearOfBlocked: freeClean, freeIntervalsWithinBar: freeInside
      };
    });
  });
  SZ.state.profile = 's10plus';
  SZ.state.orientation = 'portrait';
  const s10zones = SZ.zonesFor('s10plus', 'portrait');
  const ivals = SZ.blockedIntervals(W);
  const rightNatural = {left: W - 200, right: W, top: 0, bottom: 24};
  const planRight = SZ.planCluster(rightNatural, 'end', ivals, W);
  const leftNatural = {left: 0, right: 90, top: 0, bottom: 24};
  const planLeft = SZ.planCluster(leftNatural, 'start', ivals, W);
  const firstBlockedStart = ivals.length ? ivals[0].start : W;
  out.clusterPlan = {
    s10plusZones: s10zones,
    rightNatural: [rightNatural.left, rightNatural.right],
    planRight: planRight,
    planLeft: planLeft,
    rightTargetInFreeInterval: !!(planRight.target && planRight.target.start >= firstBlockedStart - 1 &&
                                  planRight.target.end <= W + 1),
    rightEndBeforeFirstBlocked: !!(planRight.shift !== 0 ? (rightNatural.right + planRight.shift) <= firstBlockedStart + 1 : true),
    leftUnaffectedByRightEdgeBlock: (planLeft.hit === false) || (planLeft.shift === 0)
  };
  SZ.state.profile = savedProfile;
  SZ.state.orientation = savedOrientation;
  const bar = document.getElementById('status-bar');
  SZ.previewZones([3, 4], 'portrait', 'custom');
  out.preview = {
    barBlockedAttr: bar ? bar.getAttribute('data-safezone-blocked') : null,
    barProfileAttr: bar ? bar.getAttribute('data-safezone-profile') : null,
    report: window.__nuxelSafeZoneReport ? {
      blocked: window.__nuxelSafeZoneReport.blocked,
      width: window.__nuxelSafeZoneReport.width,
      moved: window.__nuxelSafeZoneReport.moved.length,
      dropped: window.__nuxelSafeZoneReport.dropped.length
    } : null,
    blockedApplied: !!(bar && bar.getAttribute('data-safezone-blocked') === '3,4'),
    editorAPIComplete: ['ZONES','zonesFor','blockedIntervals','freeIntervals','planCluster','applyLayout','previewZones','cancelPreview','commitPreview','setZone','padding']
      .every(k => typeof SZ[k] !== 'undefined')
  };
  SZ.cancelPreview();
  SZ.state.profile = savedProfile;
  SZ.state.orientation = savedOrientation;
  out.afterCancel = {barBlockedAttr: bar ? bar.getAttribute('data-safezone-blocked') : null};
  return JSON.stringify(out);
})()
"""

JS_WALLPAPER = r"""
(async () => {
  const out = {};
  const body = getComputedStyle(document.body);
  out.bodyBackgroundImage = body.backgroundImage;
  out.bodyBackgroundColor = body.backgroundColor;
  out.bodyBackgroundSize = body.backgroundSize;
  out.bodyBackgroundPosition = body.backgroundPosition;
  const m = /url\(["']?([^"')]+)["']?\)/.exec(body.backgroundImage || '');
  out.backgroundUrl = m ? m[1] : null;
  if (m) {
    try {
      const r = await fetch(m[1], {cache: 'no-store'});
      out.backgroundHttpStatus = r.status;
      const buf = new Uint8Array(await r.arrayBuffer());
      out.backgroundBytes = buf.length;
      let h = 0;
      // simple FNV-1a signature over the bytes (cheap, in-page, deterministic)
      for (let i = 0; i < buf.length; i++) { h ^= buf[i]; h = (h * 16777619) >>> 0; }
      out.backgroundFnv1a = h.toString(16);
      let sum = 0;
      for (let i = 0; i < buf.length; i += 97) sum = (sum + buf[i]) >>> 0;
      out.backgroundByteSample = sum;
    } catch (e) { out.backgroundFetchError = String(e); }
  }
  // Draw the wallpaper into a canvas and read the real decoded pixels (this is
  // the launcher's own colour pipeline; the panel byte order is verified
  // separately by the colour-order test page + a screenshot probe).
  const img = new Image();
  const loaded = await new Promise(res => {
    img.onload = () => res(true);
    img.onerror = () => res(false);
    img.src = (m ? m[1] : '') + (m && m[1].indexOf('?') < 0 ? '?probe=1' : '');
  });
  out.wallpaperDecoded = loaded;
  if (loaded) {
    out.wallpaperNaturalWidth = img.naturalWidth;
    out.wallpaperNaturalHeight = img.naturalHeight;
    try {
      const c = document.createElement('canvas');
      c.width = 16; c.height = 16;
      const cx = c.getContext('2d');
      cx.drawImage(img, 0, 0, 16, 16);
      const d = cx.getImageData(0, 0, 16, 16).data;
      let r = 0, g = 0, b = 0, n = 0;
      for (let i = 0; i < d.length; i += 4) { r += d[i]; g += d[i+1]; b += d[i+2]; n++; }
      out.wallpaperMeanRgb = [Math.round(r/n), Math.round(g/n), Math.round(b/n)];
      let H = 0;
      for (let i = 0; i < d.length; i++) { H = ((H << 5) - H + d[i]) | 0; }
      out.wallpaperCanvasHash = (H >>> 0).toString(16);
    } catch (e) { out.wallpaperCanvasError = String(e); }
  }
  return JSON.stringify(out);
})()
"""

JS_APPS = r"""
(async () => {
  const out = {apps: [], count: 0};
  const apps = (typeof NUXEL_APPS === 'object') ? Object.entries(NUXEL_APPS) : [];
  const pw = apps.filter(([id, a]) => a.type === 'pwa' && /^https?:|^\//.test(a.url || ''));
  var pending = pw.length;
  if (!pending) return JSON.stringify(out);
  return await new Promise(resolve => {
    function finish() { out.count = out.apps.length; resolve(JSON.stringify(out)); }
    pw.forEach(([id, a]) => {
      const f = document.createElement('iframe');
      f.style.cssText = 'position:fixed;left:-10000px;top:0;width:412px;height:820px;border:0';
      f.dataset.probeAppId = id;
      const rec = {id: id, url: a.url, loaded: false, error: null, title: null, bodyMarkers: null};
      const t = setTimeout(() => { rec.error = rec.error || 'timeout'; done(rec, f); }, 12000);
      function done(r, el) {
        clearTimeout(t);
        if (el.parentNode) el.parentNode.removeChild(el);
        out.apps.push(r);
        if (--pending === 0) finish();
      }
      f.addEventListener('load', () => {
        rec.loaded = true;
        try {
          const d = f.contentDocument;
          rec.title = d ? d.title : null;
          rec.bodyMarkers = d && d.body ? {
            nodes: d.body.querySelectorAll('*').length,
            hasText: (d.body.innerText || '').trim().length > 0,
            marker: (d.body.innerText || '').slice(0, 60)
          } : null;
        } catch (e) { rec.error = 'cross-origin: ' + String(e); }
        done(rec, f);
      });
      f.addEventListener('error', () => { rec.error = 'iframe error event'; done(rec, f); });
      f.src = a.url;
      document.body.appendChild(f);
    });
  });
})()
"""


def _harness_js(side_effects):
    return ("(async () => { try { window.__probe_result = await (function(){return %s;})(); "
            "window.__probe_err = null; } catch (e) { window.__probe_result = null; "
            "window.__probe_err = String(e); } window.__probe_done = true; })(); true;"
            % side_effects)


def run_js(view, script, timeout_ms=45000):
    """Run a JS snippet and return (value_string, error_string)."""
    holder = {}
    loop = GLib.MainLoop()

    def cb(v, res, _ud=None):
        try:
            jres = v.run_javascript_finish(res)
            val = jres.get_js_value()
            holder['val'] = val.to_string() if val else None
        except Exception as exc:  # noqa: BLE001
            holder['err'] = str(exc)
        loop.quit()

    view.run_javascript(script, None, cb)
    GLib.timeout_add(timeout_ms, lambda: (loop.quit(), False)[1])
    loop.run()
    return holder.get('val'), holder.get('err')


def eval_probe(view, js_expr, timeout_ms=60000):
    run_js(view, _harness_js(js_expr), 60000)
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        v, _ = run_js(view, 'window.__probe_done === true ? "DONE" : "PENDING"', 8000)
        if v == 'DONE':
            break
        time.sleep(0.2)
    raw, err = run_js(view, 'window.__probe_result || "null"', 8000)
    perr, _ = run_js(view, 'window.__probe_err || "null"', 8000)
    if err:
        return None, err
    if perr and perr != 'null':
        return None, 'page-side error: ' + perr
    if not raw or raw == 'null':
        return None, 'no probe result'
    try:
        return json.loads(json.loads(raw)), None
    except Exception:  # noqa: BLE001
        try:
            return json.loads(raw), None
        except Exception as exc:  # noqa: BLE001
            return None, 'unparseable probe result: %s' % exc


def grim(path):
    try:
        subprocess.run(['grim', path], timeout=15, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return os.path.exists(path) and os.path.getsize(path) > 0
    except Exception:  # noqa: BLE001
        return False


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


# --- console / error capture (in-page UserScript, ALL_FRAMES, at START) -----
CONSOLE_HOOK_JS = r"""
(function () {
  if (window.__nuxelConsoleHooked) { return; }
  window.__nuxelConsoleHooked = true;
  window.__nuxelConsole = [];
  window.__nuxelErrors = [];
  function str(a) {
    try { return (typeof a === 'string') ? a : JSON.stringify(a); } catch (e) { return String(a); }
  }
  function push(level, args) {
    try { window.__nuxelConsole.push({level: level, text: Array.prototype.map.call(args, str).join(' ')}); } catch (e) {}
  }
  var origError = console.error, origWarn = console.warn;
  console.error = function () { push('error', arguments); try { origError.apply(console, arguments); } catch (e) {} };
  console.warn = function () { push('warning', arguments); try { origWarn.apply(console, arguments); } catch (e) {} };
  window.addEventListener('error', function (ev) {
    try { window.__nuxelErrors.push({kind: 'error', message: String(ev.message || ''),
      source: String(ev.filename || ''), line: ev.lineno || 0, column: ev.colno || 0}); } catch (e) {}
  }, true);
  window.addEventListener('unhandledrejection', function (ev) {
    var r = ev.reason;
    try { window.__nuxelErrors.push({kind: 'unhandledrejection',
      message: String((r && (r.message || r)) || '')}); } catch (e) {}
  }, true);
})();
"""


def install_console_hook(view):
    """Record console.error/warn + window.onerror/unhandledrejection from EVERY
    frame (main world, injected before any page script runs)."""
    ucm = view.get_user_content_manager()
    script = WebKit2.UserScript.new(CONSOLE_HOOK_JS,
                                   WebKit2.UserContentInjectedFrames.ALL_FRAMES,
                                   WebKit2.UserScriptInjectionTime.START,
                                   None, None)
    ucm.add_script(script)
    return ucm


def _decode_list(raw):
    try:
        val = json.loads(raw) if raw else []
        return val if isinstance(val, list) else []
    except Exception:  # noqa: BLE001
        return []


def read_diag(view):
    """Read the console + error records from whichever document the view shows."""
    c_raw, _ = run_js(view, 'JSON.stringify(window.__nuxelConsole || [])', 8000)
    e_raw, _ = run_js(view, 'JSON.stringify(window.__nuxelErrors || [])', 8000)
    return _decode_list(c_raw), _decode_list(e_raw)


def dump_dom(view, path, timeout_ms=20000):
    """Write document.documentElement.outerHTML to `path`; return a manifest rec."""
    raw, err = run_js(view, 'document.documentElement.outerHTML', timeout_ms)
    if not raw:
        return {'path': None, 'error': err or 'empty DOM'}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', errors='replace') as fh:
        fh.write(raw)
    return {'path': path, 'bytes': os.path.getsize(path), 'sha256': sha256_file(path)}


APP_DOM_JS = r"""
(async () => {
  const url = %s;
  const f = document.createElement('iframe');
  f.style.cssText = 'position:fixed;left:-10000px;top:0;width:412px;height:820px;border:0';
  document.body.appendChild(f);
  const res = await new Promise(resolve => {
    const t = setTimeout(() => resolve({ok: false, reason: 'timeout'}), 6000);
    f.addEventListener('load', () => {
      clearTimeout(t);
      try {
        const d = f.contentDocument;
        const html = (d && d.documentElement) ? d.documentElement.outerHTML : null;
        resolve({ok: !!html, html: html, title: d ? d.title : null,
                 console: (f.contentWindow.__nuxelConsole || []),
                 errors: (f.contentWindow.__nuxelErrors || [])});
      } catch (err) { resolve({ok: false, reason: 'cross-origin: ' + String(err)}); }
    });
    f.addEventListener('error', () => { clearTimeout(t); resolve({ok: false, reason: 'iframe error event'}); });
    f.src = url;
  });
  if (f.parentNode) { f.parentNode.removeChild(f); }
  return JSON.stringify(res);
})()
"""


def dump_app_dom(view, app_id, url, dom_dir):
    """Load one app in a real iframe, dump its DOM + its own console records."""
    val, err = eval_probe(view, APP_DOM_JS % json.dumps(url), 30000)
    rec = {'id': app_id, 'url': url}
    if err or not isinstance(val, dict):
        rec.update({'ok': False, 'error': err or 'no probe result'})
        return rec
    rec['ok'] = bool(val.get('ok'))
    rec['title'] = val.get('title')
    rec['console'] = val.get('console') or []
    rec['errors'] = val.get('errors') or []
    if val.get('ok') and val.get('html'):
        path = os.path.join(dom_dir, 'app-%s.html' % re.sub(r'[^A-Za-z0-9._-]', '_', app_id))
        os.makedirs(dom_dir, exist_ok=True)
        with open(path, 'w', encoding='utf-8', errors='replace') as fh:
            fh.write(val['html'])
        rec['dom_path'] = path
        rec['dom_bytes'] = os.path.getsize(path)
        rec['dom_sha256'] = sha256_file(path)
    else:
        rec['error'] = val.get('reason') or 'no html'
    return rec


def main():
    win = Gtk.Window(title='nuxel-vm-launcher-parity')
    win.set_default_size(720, 1440)
    win.set_decorated(False)
    view = WebKit2.WebView()
    # Record console.error/warn + window.onerror/unhandledrejection from every
    # frame BEFORE any page script runs (requirement G5: "no console errors").
    install_console_hook(view)
    st = view.get_settings()
    st.set_enable_developer_extras(True)
    st.set_enable_write_console_messages_to_stdout(False)
    win.add(view)
    win.show_all()

    loaded = {'ok': False, 'err': None}
    view.connect('load-changed', lambda v, ev: loaded.__setitem__('ok', ev == WebKit2.LoadEvent.FINISHED))
    view.connect('load-failed', lambda v, ev, uri, err: loaded.__setitem__('err', '%s (%s)' % (err.message, uri)))

    view.load_uri(PWA_URL)
    end = time.time() + TIMEOUT
    while time.time() < end:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        if loaded['ok'] or loaded['err']:
            break
        time.sleep(0.25)
    time.sleep(3)  # let the launcher's JS build the DOM
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    result['load'] = dict(loaded)

    for key, expr in (('g1_launcher_grid', JS_LAUNCHER),
                      ('g2_status_bar', JS_STATUS),
                      ('g3_safe_zones', JS_SAFEZONES),
                      ('g4_wallpaper_colour', JS_WALLPAPER),
                      ('g5_apps', JS_APPS)):
        val, err = eval_probe(view, expr)
        if err:
            result[key] = {'probe_error': err}
        else:
            result[key] = val or {}

    # --- [G5a] console + JS errors recorded from the live launcher page ------
    result['console'], result['js_errors'] = read_diag(view)

    # --- DOM dump: the launcher exactly as the engine built it ---------------
    dom_dir = os.path.join(SHOT_DIR, 'dom')
    os.makedirs(dom_dir, exist_ok=True)
    result['dom'] = {'dir': dom_dir}
    result['dom']['launcher'] = dump_dom(view, os.path.join(dom_dir, 'launcher.html'))

    # --- [G5b] per-app DOM dumps + per-app console (same-origin iframes) -----
    apps = (result.get('g5_apps') or {}).get('apps') or []
    app_doms = []
    for a in apps:
        aid, aurl = a.get('id'), a.get('url')
        if not a.get('loaded') or not aurl:
            app_doms.append({'id': aid, 'url': aurl, 'ok': False,
                             'error': a.get('error') or 'app iframe did not load'})
            continue
        app_doms.append(dump_app_dom(view, aid, aurl, dom_dir))
    result['app_dom'] = app_doms

    # launcher screenshot on the live Phosh display (window still on-screen)
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    p = os.path.join(SHOT_DIR, 'vm-launcher-home.png')
    result['screenshots']['launcher_home'] = p if grim(p) else None

    # --- colour-order page: the SAME engine + pipeline, second URL -----------
    loaded['ok'] = False
    view.load_uri(COLOUR_URL)
    end = time.time() + 60
    while time.time() < end and not loaded['ok']:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(0.25)
    time.sleep(2)
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)
    p2 = os.path.join(SHOT_DIR, 'vm-colour-order.png')
    result['screenshots']['colour_order'] = p2 if grim(p2) else None
    cval, cerr = eval_probe(view, r"""
      (async () => {
        const out = {title: document.title, swatch: (getComputedStyle(document.getElementById('swatch')||document.body).backgroundColor)};
        const t = document.getElementById('thirds');
        out.thirds = t ? [...t.children].map(c => getComputedStyle(c).backgroundColor) : [];
        out.label = document.body ? (document.body.innerText || '').trim().slice(0, 200) : '';
        return JSON.stringify(out);
      })()""", 30000)
    result['g4_wallpaper_colour']['colour_page_selfreport'] = cval if not cerr else {'probe_error': cerr}
    result['colour_page_label'] = (cval or {}).get('label') if isinstance(cval, dict) else None
    result['dom']['colour_page'] = dump_dom(view, os.path.join(dom_dir, 'colour-test.html'))
    result['colour_page_console'], result['colour_page_js_errors'] = read_diag(view)

    # --- hash the guest-side wallpaper bytes so the host can compare ---------
    try:
        wurl = (result.get('g4_wallpaper_colour') or {}).get('backgroundUrl')
        if wurl:
            full = wurl if wurl.startswith('http') else BASE + (wurl if wurl.startswith('/') else '/' + wurl)
            tmp = '/tmp/nuxel-wallpaper-probe.bin'
            urllib.request.urlretrieve(full, tmp)
            result['g4_wallpaper_colour']['background_sha256_guest'] = sha256_file(tmp)
            result['g4_wallpaper_colour']['background_bytes_guest'] = os.path.getsize(tmp)
    except Exception as exc:  # noqa: BLE001
        result['g4_wallpaper_colour']['background_hash_error'] = str(exc)

    # --- screenshot manifest (separate loop: never mutate while iterating) ---
    shots = {}
    for k, path in list(result['screenshots'].items()):
        rec = {'path': path}
        if path and os.path.exists(path):
            rec['bytes'] = os.path.getsize(path)
            rec['sha256'] = sha256_file(path)
        shots[k] = rec
    result['screenshots'] = shots

    gates = {
        'page_loaded': bool(result.get('load', {}).get('ok')),
        'g1_launcher_grid': 'probe_error' not in (result.get('g1_launcher_grid') or {}),
        'g2_status_bar': 'probe_error' not in (result.get('g2_status_bar') or {}),
        'g3_safe_zones': 'probe_error' not in (result.get('g3_safe_zones') or {}),
        'g4_wallpaper_colour': 'probe_error' not in (result.get('g4_wallpaper_colour') or {}),
        'g5_apps': 'probe_error' not in (result.get('g5_apps') or {}),
    }
    result['gates'] = gates

    out_json = os.path.join(SHOT_DIR, 'result.json')
    with open(out_json, 'w', encoding='utf-8') as fh:
        json.dump(result, fh, indent=2, default=str)
    print(json.dumps(result, indent=2, default=str))
    Gtk.main_quit()
    sys.stdout.flush()
    sys.exit(0 if all(gates.values()) else 3)


if __name__ == '__main__':
    main()

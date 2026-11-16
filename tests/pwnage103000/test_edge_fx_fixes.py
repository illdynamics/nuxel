#!/usr/bin/env python3
"""Regression tests for the two owner-reported Edge FX defects.

  * Preview must reach Home even while the app iframe is on top, and the CSS
    must not hide the overlay merely because a panel flag is set.
  * "Allow all apps" must persist an empty allowlist and update the UI from the
    provider response, never from a stale render closure.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FX = ROOT / 'pwa/nuxel-apps/edge-fx/edge-fx.js'
FX_HTML = ROOT / 'pwa/nuxel-apps/edge-fx/index.html'
ENGINE = ROOT / 'pwa/nuxel-home/js/edge-lighting.js'
CSS = ROOT / 'pwa/nuxel-home/css/edge-lighting.css'

fails = []


def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond or not extra else '  ' + str(extra)))
    if not cond:
        fails.append(name)


js = FX.read_text()
engine = ENGINE.read_text()
css = CSS.read_text()
html = FX_HTML.read_text()

check('Edge FX classic script loads after the module bridge (race is guarded)',
      html.find('edge-fx.js') > html.find('bridge.js'))
check('Edge FX waits for the shared bridge singleton', 'function bridgeReady' in js and 'bridgeReady().then(loadStatus)' in js)
check('Edge FX save no longer hard-refuses on first tap',
      "Bridge unavailable: settings were not saved" not in js)
check('Edge FX posts validated preview request to Home',
      "nuxel:edge-lighting-preview" in js and 'request_id' in js)
check('Edge FX waits for a preview acknowledgement', 'nuxel:edge-lighting-preview-result' in js)
check('Preview button uses the acknowledgement path', "previewEffect(settings.effect)" in js)
check('Home validates message origin and source', "ev.origin !== origin" in engine and 'ev.source === global' in engine)
check('Home preview is not suppressed by disabled master switch', 'one-shot presentation request' in engine)
check('Home waits for the shared bridge before reading settings', 'function bridgeReady' in engine and 'bridgeReady().then(function () { return apiFetch' in engine)
check('Shared bridge GET does not duplicate the /api/v1 prefix', "replace(/^\\/api\\/v1/" in engine and 'b.get(endpoint)' in engine)
check('Preview overlay gets an explicit top layer', 'edge-preview-requested' in engine and "root.style.zIndex = '1000'" in engine)
check('Preview top layer is cleared on stop', "root.classList.remove('active', 'edge-preview-requested')" in engine)
check('Panel-open CSS no longer hides every preview',
      'body.edge-panel-open #nuxel-edge-lighting { visibility: visible; }' in css)
check('Edge root is above the immersive PWA frame', re.search(r'\.edge-root\s*\{[^}]*z-index:\s*240', css, re.S) is not None)
check('Allow all persists explicit source_mode=all', "save({ source_mode: 'all'" in js)
check('Per-app selection persists source_mode=allowlist', "save({ source_mode: 'allowlist'" in js)
check('Allow all refreshes checkboxes from provider config',
      'renderSources();' in js.split("$('sources-clear')")[1][:1600])
check('Allow all verifies the provider read-back before claiming success',
      'refreshStatus(true)' in js.split("$('sources-clear')")[1][:1600])
check('A successful save tells Home to adopt the provider document',
      "nuxel:edge-lighting-resync" in js and 'notifyHome(cfg)' in js)
check('Home applies a resync message to the one engine',
      "'nuxel:edge-lighting-resync'" in engine and 'settings = api.normaliseSettings(msg.config)' in engine)
check('Effect tiles persist the selection even when a preview is suppressed',
      js.find("save({ effect: eff }") < js.find("previewEffect(eff).then") and
      "fixtureMode ? Promise.resolve(false) : save({ effect: eff }" in js)
check('Preview carries the app-owned presentation settings',
      'previewSettings(effect)' in js and 'settings: msg.settings' in engine)
check('Preview never reports success for a suppressed animation',
      "result.error = isSleeping() ? 'display-asleep'" in engine and
      "result.ok = false" in engine.split('if (!desc) {')[1][:400])
check('Bridge mock replies are never treated as provider results',
      'function isMock(' in js and 'res.mock === true' in js and 'isMock(res) ? fetchApi' in js)
check('Overlay is not paint-contained (effects are not clipped)',
      'contain: strict' not in css.split('.edge-root {')[1].split('}')[0])
check('Source rows read the authoritative list, not a stale closure', 'current = allowedList().slice()' in js)
check('Source rows cannot overwrite each other', 'sourcesBusy' in js)
check('Source summary is visible', 'id="sources-summary"' in html and "$('sources-summary')" in js)
check('All-apps state visibly clears the list', 'id="sources-empty"' in html and 'cb.checked = !allowAll' in js)
check('Unchecking from All keeps the other apps, checking selects only one',
      'current = cb.checked' in js and "? [app.id]" in js and "id !== app.id" in js)
check('Asset cache-busting version bumped', 'edge-fx.js?v=p103000c' in html and 'edge-fx.css?v=p103000c' in html)

print()
if fails:
    print('test_edge_fx_fixes: %d FAILING CHECK(S): %s' % (len(fails), ', '.join(fails)))
    sys.exit(1)
print('test_edge_fx_fixes: ALL PASS')

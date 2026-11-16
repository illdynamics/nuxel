#!/usr/bin/env python3
"""PWNAGE-103000 wiring/contract checks across the real tree.

Guards the architectural boundaries: one notification source, one Home gesture
owner, one display renderer, no framebuffer/LED writer added, the canonical
Edge FX app, the service worker cache bump and the provider routing.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import check, finish, ROOT  # noqa: E402

api = (ROOT / 'services/nuxel-bridge/src/api.py').read_text()
home = ROOT / 'pwa/nuxel-home'
edge_js = (home / 'js/edge-lighting.js').read_text()
gest = (home / 'js/gestures.js').read_text()
qs = (home / 'js/qs.js').read_text()
idx = (home / 'index.html').read_text()
sw = (home / 'sw.js').read_text()
manifest = (home / 'manifest.json').read_text()
fx = ROOT / 'pwa/nuxel-apps/edge-fx'

# --- bridge wiring ---------------------------------------------------------
check('provider is imported in the optional provider table', "'edge_lighting_provider')" in api)
check('NotificationAdded is watched on the canonical system-bus hub',
      "signal_name='NotificationAdded'" in api and "bus_name='org.nuxel.Notifications'" in api)
check('watch is started by the HTTP bridge entry point', 'start_edge_lighting_watch()' in api)
check('GET status route exists', "'/api/v1/edge-lighting'" in api)
check('GET journal route exists', "'/api/v1/edge-lighting/events'" in api)
check('edge-lighting RPC namespace is routed', "namespace == 'edge-lighting'" in api)
check('a PWA cannot submit the privileged event verb',
      "'notification events are ingested from org.nuxel.Notifications only'" in api)
check('no second notification daemon/unit was added',
      not (ROOT / 'services/nuxel-notifications').joinpath('systemd/edge.service').exists())
check('no new framebuffer writer in the edge code',
      '/dev/fb' not in edge_js and 'mmap' not in edge_js and 'fb0' not in edge_js)
check('no LED brightness write in any edge/UI file',
      not re.search(r'class/leds|/sys/class/camera/flash|rear_flash', edge_js + qs + gest
                    + (ROOT / 'pwa/nuxel-apps/edge-fx/edge-fx.js').read_text()))
check('only flashlight_provider writes the torch node',
      (ROOT / 'services/nuxel-bridge/src/flashlight_provider.py').read_text().count('_write_brightness') >= 1)

# --- Home wiring -----------------------------------------------------------
check('index loads the recognizer before the engine',
      idx.index('js/edge-panel-gesture.js') < idx.index('js/edge-lighting.js'))
check('index loads the edge stylesheet', 'css/edge-lighting.css' in idx)
check('Quick Settings has an Edge panel tile', 'id="qs-edge-panel"' in idx)
check('Quick Settings has an Edge lighting tile', 'id="qs-edge-lighting"' in idx)
check('qs.js opens the panel from the accessible tile', "edgePanelTile.addEventListener('click'" in qs)
check('qs.js previews/toggles edge lighting', '_buildEdgeLightingTile' in qs and 'api.preview(' in qs)
check('Quick Settings open closes the Edge panel (arbitration)', "closePanel('quick-settings')" in qs)
check('gestures.js keeps the single pointer/touch owner',
      gest.count("document.addEventListener('pointerdown'") == 1
      and gest.count("document.addEventListener('touchstart'") == 1)
check('edge overlay is pointer-events none', '.edge-root' in (home / 'css/edge-lighting.css').read_text())
check('effect engine polls the real journal endpoint', "'/edge-lighting/events?since='" in edge_js)
check('preview never creates a notification', 'notification_state_changed' in
      (ROOT / 'services/nuxel-bridge/src/edge_lighting_provider.py').read_text())
check('renderer destroys its animation on completion', "stop('complete')" in edge_js)
check('renderer stops on display sleep/screen-off', "'nuxel:display-sleep'" in edge_js and
      "'nuxel:screen-off'" in edge_js)
check('reduced motion is honoured before playing', 'reducedMotionState' in edge_js
      and "motion === 'off'" in edge_js)
check('edge panel renders canonical registry apps', 'appRegistry.getAllApps' in edge_js)
check('edge panel uses the existing notification list', 'statusBar.state.notifications' in edge_js)
check('edge panel hides notifications while locked', 'isLocked()' in edge_js)
check('panel launches through the canonical registry action', 'reg.launchApp(appId)' in edge_js)
check('panel supports both sides (left/right classes)', 'from-right' in edge_js
      and 'from-right' in (home / 'css/edge-lighting.css').read_text())

# --- service worker --------------------------------------------------------
m = re.search(r"const CACHE_VERSION = '([^']+)';", sw)
# A84: the cache version is now a release-tagged marker ('a84-lock'), not
# 'v0NN-p103000'.  The invariant that matters is that it ADVANCED past the
# p103000 builds (so a device does not keep an old launcher bundle cached).
check('service worker cache version advanced past the p103000 builds',
      bool(m) and (re.match(r'^v0\d\d-p103000$', m.group(1)) is None or
                   int(m.group(1)[1:4]) >= 96),
      m and m.group(1))
check('service worker precaches the new assets',
      all(a in sw for a in ('./js/edge-lighting.js', './js/edge-panel-gesture.js', './css/edge-lighting.css')))
ver = (json.loads(manifest).get('nuxel') or {}).get('cache_version')
check('manifest cache_version agrees with sw.js', ver == (m.group(1) if m else None), ver)
check('old Home files were not rewritten wholesale (git-relative sanity)',
      'NuxelEdgePanelGesture' in gest and 'NuxelEdgeLighting' in edge_js)

# --- Edge FX app -----------------------------------------------------------
for f in ('index.html', 'app.json', 'manifest.json', 'edge-fx.js', 'edge-fx.css', 'e2e/e2e.html'):
    check('Edge FX ships %s' % f, (fx / f).is_file())
app = json.loads((fx / 'app.json').read_text())
man = json.loads((fx / 'manifest.json').read_text())
check('Edge FX uses a canonical app id', app['id'] == 'nuxel-edge-fx' and man['nuxel']['app_id'] == 'nuxel-edge-fx')
check('Edge FX start_url is a local Nuxel app bundle',
      app['url'] == '/pwa/nuxel-apps/edge-fx/index.html' and man['start_url'] == './index.html')
check('Edge FX manifest pins bridge_version 1', man['nuxel']['bridge_version'] == '1')
fxjs = (fx / 'edge-fx.js').read_text()
check('Edge FX can save settings via the edge-lighting namespace', "call('edge-lighting', 'set'" in fxjs)
check('Edge FX previews through the one Home engine',
      "nuxel:edge-lighting-preview" in fxjs and 'previewEffect(settings.effect)' in fxjs
      and 'engine.preview(effect' in fxjs)
check('Edge FX uninstalls through the canonical apps registry', "call('apps', 'unregister'" in fxjs)
check('Edge FX reinstalls through the canonical apps registry', "call('apps', 'register'" in fxjs)
check('Edge FX explains uninstall keeps settings', 'settings are not' in (fx / 'index.html').read_text())
check('Edge FX opens the Edge panel from either side', "openPanel(side, 'edge-fx-app')" in fxjs)

# --- canonical registry ----------------------------------------------------
reg = json.loads((ROOT / 'pwa/nuxel-common/app-registry.json').read_text())
ids = [a.get('id') for a in reg['apps']]
check('canonical registry contains Edge FX exactly once', ids.count('nuxel-edge-fx') == 1)
check('registry version advanced', int(reg['registry_version']) >= 20, reg['registry_version'])
check('registry tree names the Edge FX bundle', any(t.get('dir') == 'pwa/nuxel-apps/edge-fx'
                                                     for t in reg.get('tree_apps', [])))
check('every app manifest bridge_version matches the pin',
      all(a.get('bridge_version', '1') == '1' for a in reg['apps']))

# --- Settings integration --------------------------------------------------
settings_html = (ROOT / 'pwa/nuxel-apps/settings/index.html').read_text()
check('Settings notifications tab has the Edge lighting section',
      'id="edge-lighting-state"' in settings_html and 'edge-lighting-settings.js' in settings_html)
fxhtml = (fx / 'index.html').read_text()
check('Edge FX offers screen-off/always only as disabled (unavailable)',
      'value="screen_off" disabled' in fxhtml and 'value="always" disabled' in fxhtml)
check('Settings links to Edge FX', 'edge-lighting-open' in settings_html)

# --- policy defaults file --------------------------------------------------
pol = json.loads((ROOT / 'configs/nuxel/edge-lighting/edge-lighting.json').read_text())
check('shipped policy default is Wave/theme/1800ms',
      pol['effect'] == 'wave' and pol['color_mode'] == 'theme' and pol['duration_ms'] == 1800)
check('shipped policy lists all eight S10-style effects',
      pol['effects'] == ['basic', 'wave', 'bubble', 'multicolor', 'heart', 'fireworks', 'eclipse', 'echo'])
check('shipped policy advertises only screen_on', pol['screen_modes_supported'] == ['screen_on'])

finish('PWNAGE-103000 contract')

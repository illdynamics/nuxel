#!/usr/bin/env python3
"""A83: wake from the dark glass, the wake Edge FX and the boot-cue timing.

These checks are offline.  They pin the properties that make the handset
behaviour correct and that a later edit could silently break:

  * the button manager (the single owner of gpio_keys and of the panel toggle)
    queues the panel wake from a dark-glass contact, before the panel unblanks,
    and drops that contact's stale samples from the gesture machine;
  * nuxel-wl-fb runs at most one wake per toggle burst, so a queued touch-wake
    cannot re-blank the panel that a Power press just turned on;
  * the launcher dispatches display-on on a wake the host announced even when
    this document never sampled display=off;
  * the configured Edge FX (Wave, #4aa8ff, 1800 ms) is enabled for wake+unlock
    by the engine defaults and by the provider; the owner's stored document
    wins when it carries explicit booleans;
  * the boot cue is started - not after - the preloading video's lockscreen
    handoff, using the shipped clip and audio lengths.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FAILS = []


def check(cond, what):
    print(("PASS " if cond else "FAIL ") + what)
    if not cond:
        FAILS.append(what)


def text(rel):
    return (ROOT / rel).read_text()


def run_py(rel, *args, env=None):
    import os
    e = dict(os.environ)
    e.update(env or {})
    return subprocess.run([sys.executable, str(ROOT / rel), *args],
                          capture_output=True, text=True, env=e, timeout=60)


# ---------------------------------------------------------------- button manager
bm = text('tools/s10plus/a45/nuxel-button-manager.c')
check('static int touch_wake_discard' in bm and 'touch_wake_ms' in bm,
      "button manager owns touch-wake state")
check(re.search(r'if \(!display_on\) \{[^}]*strstr\(dstate, "display=off"\)', bm, re.S) is not None,
      "wake is requested only while the panel is really off")
wake = bm[bm.index('if (!display_on) {', bm.index('sel.touch_fd >= 0 && r > 0')):]
wake = wake[:wake.index('touch_wake_discard = 1;')]
check('fifo_send(WLFB_FIFO, "screen-on\\n")' in wake,
      "dark-glass contact queues screen-on on the display bridge FIFO")
check('touch_wake_ms = t;' in wake and 'last_activity_ms = t;' in wake,
      "wake resets the idle timer and is debounced")
check('touch_wake_discard = 1;' in bm[bm.index('if (!display_on) {', bm.index('sel.touch_fd >= 0 && r > 0')):],
      "the waking contact is dropped from the gesture machine")
check('touch_repaint_at_ms' in bm and 'TOUCH_WAKE_REPAINT_SENT' in bm,
      "a deferred repaint follows the wake once the panel can accept it")
check('if (!display_on) touch_wake_ms = 0;' in bm,
      "the debounce clears when the finger lifts")
check('touch_pending_down = 1;' in bm[bm.index('if (touch_wake_discard) {'):],
      "the gesture machine restarts on the next real contact")

# --------------------------------------------------------------- display bridge
wf = text('tools/s10plus/a67/nuxel-wl-fb.c')
check('if (!display_on) display_set(1, "control-fifo");' in wf,
      "a duplicate screen-on is a no-op (the panel is already on)")
check('display_set(!display_on, "control-fifo");' in wf,
      "a control-FIFO toggle reads the live panel state, not a stale latch")
check('we_control_display' not in wf, "no second panel-state latch can drift")
check('int bb = read_int_file(BACKLIGHT);' in wf,
      "a status request re-reads the real backlight for wake verification")
host = text('tools/s10plus/a45/nuxel-pwa-host.c')
check('strcmp(action, "screen-wake")' in host and
      'wlfb_command("screen-on");' in host.split('strcmp(action, "screen-wake")')[1][:400],
      "host exposes a non-toggling screen-wake action")

# -------------------------------------------------------------------- launcher
app = text('pwa/nuxel-home/js/app.js')
check('_wakeFromOff' in app and 'this._wakeFromOff = false;' in app,
      "launcher tracks a host-announced wake without an OFF sample")
check("(this._lastDisplayOff !== false && !off && this._wakeFromOff === true)" in app,
      "an ON sample after a host wake dispatches display-on")
edge = text('pwa/nuxel-home/js/edge-lighting.js')
check("lifecycle: { screen_on: true, screen_off: false, lock: false, unlock: true }" in edge,
      "engine defaults play the configured effect on wake and unlock")
check('ensureWakeLifecycle' in edge and 'api.ensureWakeLifecycle' in edge,
      "engine repairs a legacy document that left wake switches off")
check("b.classList.remove('screen-off', 'screen-sleep')" in edge,
      "the wake pulse is not suppressed by the launcher's lagging pre-wake class")
prov = text('services/nuxel-bridge/src/edge_lighting_provider.py')
prov_defaults = prov[prov.index('"lifecycle": {'):]
prov_defaults = prov_defaults[:prov_defaults.index('}')]
check('"screen_on": True' in prov_defaults and '"unlock": True' in prov_defaults and
      '"screen_off": False' in prov_defaults and '"lock": False' in prov_defaults,
      "provider defaults match the configured wake behaviour")
sw = text('pwa/nuxel-home/sw.js')
man = json.loads(text('pwa/nuxel-home/manifest.json'))
cv = re.search(r"const CACHE_VERSION = '([^']+)'", sw).group(1)
check(cv == man['nuxel']['cache_version'], "service-worker cache version matches the manifest")

# ------------------------------------------------------------------ boot cue
cue = text('tools/s10plus/a33/nuxel-sound-cue.py')
check('def _cue_wait_seconds' in cue and '_cinema_active' in cue,
      "boot cue knows the preloading overlay and the clip/audio lengths")
check("doc.get('state') in ('starting', 'covered')" in cue,
      "cue waits only while the preloading video is on the glass")
asset = json.loads(text('configs/nuxel/boot/preload-cinema.json'))
check(asset['_asset']['duration_ms'] == 6016, "preloading clip duration is the shipped 6016 ms")
check(asset['_asset']['bytes'] == (ROOT / 'assets/nuxel-preloading-screen.mp4').stat().st_size,
      "the preloading clip bytes match the shipped asset")
stored = json.loads(text('configs/nuxel/edge-lighting/edge-lighting.json'))
if stored.get('lifecycle'):
    check(stored['lifecycle'].get('screen_on') is True and stored['lifecycle'].get('unlock') is True,
          "shipped Edge FX document enables wake and unlock")

# duration maths must be honest for the shipped files
sys.path.insert(0, str(ROOT / 'tools/s10plus/a33'))
import importlib.util
spec = importlib.util.spec_from_file_location('cue_doc', ROOT / 'tools/s10plus/a33/nuxel-sound-cue.py')
cue_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cue_mod)
lead = cue_mod._cue_wait_seconds()
check(abs(lead - 0.0) < 0.05 or 0.0 <= lead <= 6.016,
      "cue lead is clamped inside the clip (+%.3fs)" % lead)
# the cue must start strictly before the clip ends, while the video plays on
check(cue_mod._cue_wait_seconds() < 6.016 and cue_mod._cue_wait_seconds() >= 0.0,
      "cue lead keeps the boot audio inside the preloading video window")

if FAILS:
    print("\nA83 TESTS: %d FAILURE(S)" % len(FAILS))
    sys.exit(1)
print("\nA83 TESTS: ALL PASS")

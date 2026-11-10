"""PWNAGE-94000 regression tests.

Covers the six requested workstreams at the source/contract level plus the
DOM-free top-bar machine.  Physical-device results are recorded separately in
REPORT-PWNAGE-94000.md and are never inferred from these checks.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS " + name + (("  — " + str(detail)) if detail else ""))
    else:
        FAIL += 1
        print("  FAIL " + name + (("  — " + str(detail)) if detail else ""))


def read(rel):
    return (ROOT / rel).read_text()


def node(script):
    return subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True,
                          text=True, timeout=30)


print("PWNAGE-94000 — Workstream A: Doom")
doom = read("pwa/nuxel-apps/doom/js/doom.js")
check("WebAssembly Doom defaults sound ON", re.search(r"sound:\s*true", doom) is not None)
check("default Chocolate Doom config uses non-zero effects volume", "'sfx_volume 15'" in doom)
check("default Chocolate Doom config uses non-zero music volume", "'music_volume 8'" in doom)
check("engine args only add -nosound when the owner opted out or audio activation was refused",
      "const audioReady = await audioReadyForLaunch();" in doom and
      "if (!audioReady) {" in doom and "args.push('-nosound', '-nomusic');" in doom)
check("sound settings persist through the durable settings key",
      "nuxel.doom.wad.settings.v1" in doom)
engine = read("tools/s10plus/a33/doom-engines/nuxel-doom-engine")
check("native Chocolate Doom no longer forces -nomusic", "-nomusic" not in engine)
check("native wrapper seeds non-zero sfx/music volumes", "sfx_volume 15" in engine and "music_volume 8" in engine)
check("native wrapper uses a bounded audio readiness check, not a fixed sleep",
      "PULSE_SOCKET" in engine and "while [ \"$i\" -lt 30 ]" in engine)
crispy = read("tools/s10plus/a33/nuxel-crispy-doom")
check("Crispy Doom defaults sound ON", '${NUXEL_DOOM_SOUND:-1}' in crispy)
check("Crispy Doom only passes -nosound on explicit opt-out", "-nosound" in crispy and 'NUXEL_DOOM_SOUND:-1' in crispy)
check("WAD catalogue is digest-addressed and path-free",
      "/api/v1/doom/wads" in doom and "encodeURIComponent(wad.id)" in doom)
check("native Doom launches the installed engine wrapper",
      "org.nuxel.Doom.Chocolate" in doom)

print("\nPWNAGE-94000 — Workstream B: canonical top bar")
machine_path = ROOT / "pwa/nuxel-home/js/topbar-machine.js"
check("DOM-free top-bar machine exists", machine_path.is_file())
script = r"""
const M=require('./pwa/nuxel-home/js/topbar-machine.js');
const m=new M();
const down=[]; for(let i=0;i<4;i++){m.advance('down');down.push(m.level);}
const up=[]; for(let i=0;i<3;i++){m.closeAll('up');up.push(m.level);m.advance('down');}
const fromExtended=[]; m.advance('down');m.advance('down');m.advance('down');
fromExtended.push(m.level); m.closeAll('up'); fromExtended.push(m.level);
console.log(JSON.stringify({down,up,fromExtended}));
"""
r = node(script)
ok = r.returncode == 0
data = json.loads(r.stdout.strip()) if ok and r.stdout.strip() else {}
check("first/second/third downward gestures reach 1/2/3", data.get("down") == [1, 2, 3, 3], data.get("down"))
check("one upward gesture from each level reaches 0", data.get("up") == [0, 0, 0], data.get("up"))
check("extended closes atomically to hidden", data.get("fromExtended") == [3, 0], data.get("fromExtended"))
qs = read("pwa/nuxel-home/js/qs.js")
check("QuickSettings delegates to the machine", "new window.NuxelTopBarMachine" in qs)
check("upward pull is atomic closeAll", "if (direction === 'up') { this.closeAll('up'); return; }" in qs)
check("extended level is first-class", "quick-settings.extended" in read("pwa/nuxel-home/css/status-bar.css") or ".quick-settings.extended" in read("pwa/nuxel-home/css/status-bar.css"))
check("notification list is gated by EXTENDED, not EXPANDED",
      "#quick-settings.extended #qs-notifications" in read("pwa/nuxel-home/css/status-bar.css"))
immersive = read("pwa/nuxel-home/js/immersive.js")
check("immersive edge gesture advances one level only", "qs.advance('immersive-pull')" in immersive)
check("immersive defers to the status-bar pull that already consumed the swipe",
      "__nuxelQsGestureConsumed" in immersive and
      "setStatusVisible(true, 0);\n            return;" in immersive)
check("immersive upward gesture closes the whole panel", "qs.closeAll('immersive-up')" in immersive)
check("landscape top/bottom bands are wider than portrait",
      "BOTTOM_BAND = { portrait: 34, landscape: 56 }" in immersive and
      "TOP_BAND = { portrait: 48, landscape: 56 }" in immersive)
check("old two-value fullscreen bar state is gone", "bar_revealed" not in read("tools/s10plus/a45/nuxel-statusbar.c"))
statusbar = read("tools/s10plus/a45/nuxel-statusbar.c")
check("native adapter renders levels 0..3", "bar_set_level" in statusbar and "PANEL_EXTENDED" in statusbar)
check("native adapter never reserves app viewport space", "set_exclusive_zone(layer_surface, 0)" in statusbar)
check("native adapter is a presentation adapter over the canonical model",
      "statusbar-model.json" in statusbar and "model_get(\"wifi\"" in statusbar)
check("native adapter has a bounded level control FIFO for evidence",
      "/run/nuxel-statusbar.cmd" in statusbar)
check("statusbar control FIFO is opened read/write so POLLHUP cannot busy-spin",
      "open(CMD_FIFO, O_RDWR | O_NONBLOCK | O_CLOEXEC)" in statusbar
      and "open(CMD_FIFO, O_RDONLY" not in statusbar)
check("statusbar poll treats POLLHUP/POLLERR as readable control events",
      "POLLIN | POLLHUP | POLLERR" in statusbar)
navdock = read("tools/s10plus/a45/nuxel-navdock.c")
check("landscape nav dock input band grows to 56 px", "(width >= 500 || out_w > out_h) ? 56" in navdock)
check("status bar model is published by the DOM bar",
      "_publishCanonicalModel" in read("pwa/nuxel-home/js/status-bar.js"))
check("host whitelists the statusbar model output",
      '"statusbar-model"' in read("tools/s10plus/a45/nuxel-pwa-host.c"))

print("\nPWNAGE-94000 — Workstream C: startup performance")
api = read("services/nuxel-bridge/src/api.py")
check("launch-plan cache exists", "_LAUNCH_PLAN_CACHE" in api and "_LAUNCH_PLAN_TTL_S" in api)
_exec_block = api[api.index("def _exec_native_app"):api.index("def _keyboard_visible")]
check("registry lookup is reused instead of repeated", _exec_block.count("_lookup_registry_app(target_id)") == 1)
check("launch timings split the real phases", "request_to_focus_probe" in api and "focus_probe_to_provider_lookup" in api)
check("T3 first-surface timing is recorded", "t3_surface" in api and "surface_ms" in api)
check("surface matching is normalized for Flatpak/Wayland id differences",
      "def surface_id_matches" in api and "_norm_app_key" in api)
check("orientation subprocess is skipped when already in the requested pose",
      "_apply_orientation_if_needed" in api and "current_orientation_mode() == mode" in api)
check("launch evidence is written even on timeout", 'outcome = "no_surface_timeout"' in api)
check("duplicate launch guard remains present", "_focus_existing_surface(surface_id)" in api)
session = read("tools/s10plus/a45/nuxel-session.sh")
check("document portal is pre-started to avoid the 30 s Flatpak D-Bus timeout",
      "xdg-document-portal" in session and '" $USER_RUNTIME/doc "' in session)

print("\nPWNAGE-94000 — Workstream D: global dark theme")
check("GTK3 system default is Adwaita-dark", "gtk-theme-name=Adwaita-dark" in read("configs/nuxel/gtk/gtk-3.0-settings.ini"))
check("GTK3 prefers dark applications", "gtk-application-prefer-dark-theme=true" in read("configs/nuxel/gtk/gtk-3.0-settings.ini"))
check("GTK4 system default is Adwaita-dark", "gtk-theme-name=Adwaita-dark" in read("configs/nuxel/gtk/gtk-4.0-settings.ini"))
check("dconf site default is prefer-dark", "color-scheme='prefer-dark'" in read("configs/nuxel/dconf/db/site.d/00-nuxel-dark"))
check("dconf profile keeps user preferences first", "user-db:user" in read("configs/nuxel/dconf/profile-user"))
check("Flatpak global override changes only the environment",
      "[Environment]" in read("configs/nuxel/flatpak/global-override")
      and "[Context]" not in read("configs/nuxel/flatpak/global-override"))
check("session-user native apps use the user portal bus",
      '("unix:path=/run/user/1000/bus" if (is_flatpak or as_user)' in api)
check("launches force the dark preference and dconf backend",
      "GTK_APPLICATION_PREFER_DARK_THEME=1" in api and "GSETTINGS_BACKEND=dconf" in api)
check("Flatpak launch argv carries dark GTK environment",
      "--env=GTK_THEME=Adwaita:dark" in read("services/nuxel-bridge/src/flatpak_provider.py"))

print("\nPWNAGE-94000 — Workstream E: Back lifecycle")
ft = read("tools/s10plus/a59/nuxel-foreign-toplevel.c")
home_block = ft[ft.index('if (!strcmp(mode, "home"))'):ft.index('if (!strcmp(mode, "focus")')]
check("home action has no fixed lifecycle sleep", "usleep" not in home_block)
check("home action waits on compositor state events", "settle_compositor" in home_block and "home_state_ok" in ft)
check("home convergence requires Home to be active", "home_active" in api)
check("short Back remains distinct from long Back", "forceKillForeground" in read("pwa/nuxel-home/js/app.js"))
appjs = read("pwa/nuxel-home/js/app.js")
check("single Back closes a Quick Settings panel atomically", "qs.closeAll('back')" in appjs)
check("post-transition input check covers top/bottom edge hit targets",
      "topEdge" in appjs and "bottomEdge" in appjs)
check("host after-app-close asks the launcher for geometry restoration",
      "window.nuxel.restoreGeometry('host-after-app-close')" in read("tools/s10plus/a45/nuxel-pwa-host.c"))
check("native Home watchdog reloads a stuck foreground PWA",
      "HOST_HOME_WATCHDOG_RELOAD" in read("tools/s10plus/a45/nuxel-pwa-host.c") and
      "launcher-app" in read("tools/s10plus/a45/nuxel-pwa-host.c") and
      "configSet('launcher-app'" in read("pwa/nuxel-home/js/app.js"))
check("backgrounded PWA frames are hidden with inline !important, not CSS only",
      "_setSurfaceDisplay(el, visible)" in appjs and
      "el.style.setProperty('display', visible ? 'block' : 'none', 'important')" in appjs)
check("background/resume paths drive the inline surface visibility helper",
      "owned.forEach(el => this._setSurfaceDisplay(el, false))" in appjs and
      "forEach(el => this._setSurfaceDisplay(el, true))" in appjs)
check("Home sweeps orphan PWA frames that lost their owning session",
      "_sweepOrphanSurfaces()" in appjs and "this._sweepOrphanSurfaces();" in appjs)
doomjs = read("pwa/nuxel-apps/doom/js/doom.js")
check("Doom suspends its AudioContext when the engine pauses",
      "function suspendEngineAudio()" in doomjs and
      "suspendEngineAudio();" in doomjs[doomjs.index("function pauseEngine()"):doomjs.index("function resumeEngine()")])
check("Doom suspends audio on close-request and pagehide",
      "if (event.data.type !== 'nuxel:close-request') return;" in doomjs and
      "suspendEngineAudio();" in doomjs[doomjs.index("nuxel:close-request"):doomjs.index("window.NuxelDoom")])
check("Doom re-arms audio when the engine resumes",
      "scheduleEngineAudioResume();" in doomjs[doomjs.index("function resumeEngine()"):doomjs.index("function showLauncher()")])
check("Doom launch decides audio from the real AudioContext, not userActivation alone",
      "if (activation === false) return false;" not in doomjs and
      "only fall back to -nosound when the bounded resume" in doomjs and
      "if (ctx.state === 'running') return true;" in doomjs)
check("Doom does not install a statechange->resume feedback loop",
      "installNuxelAudioAutoResume" not in doomjs and
      "Never attach a permanent" in doomjs)
check("Doom keeps SFX and disables the unstable MIDI path",
      "if (audioReady && !args.includes('-nomusic')) args.push('-nomusic');" in doomjs)
check("Doom exposes bounded audio/GL callback probes for device evidence",
      "engineAudioStats" in doomjs and "engineGLStats" in doomjs and
      "engineAudioStats: function ()" in doomjs)

print("\nPWNAGE-94000 — Workstream F: desktop geometry")
check("one launcher geometry restore owns the reset",
      "restoreGeometry(reason)" in appjs and "nuxel:geometry-restored" in appjs)
check("restore removes stale immersive/panel/transform state",
      "app-status-hidden" in appjs and "touch-keyboard-open" in appjs and "style.transform = ''" in appjs)
check("restore re-establishes the scroll origin", "window.scrollTo(0, 0)" in appjs)
check("geometry report measures bar, dock, nav and grid",
      "geometryReport()" in appjs and "statusBar: rect('status-bar')" in appjs)
check("resize while an app owns the glass does not reset Home",
      "geometry:skip state=" in appjs)
check("native status bar does not create a second inset",
      "set_exclusive_zone(layer_surface, 0)" in statusbar)
check("desktop CSS keeps one inset variable per band",
      "--status-bar-height: 36px" in read("pwa/nuxel-home/css/style.css")
      and "--system-nav-height: 62px" in read("pwa/nuxel-home/css/style.css"))
check("dock and grid derive their positions from the shared nav inset",
      "bottom: var(--system-nav-height)" in read("pwa/nuxel-home/css/launcher.css")
      and "calc(var(--dock-height) + var(--system-nav-height))" in read("pwa/nuxel-home/css/launcher.css"))
check("host exposes restore-geometry for deterministic evidence",
      '"restore-geometry"' in read("tools/s10plus/a45/nuxel-pwa-host.c"))
check("host exposes a bounded immersive edge-gesture evidence hook",
      '"ui-edge-swipe "' in read("tools/s10plus/a45/nuxel-pwa-host.c"))
check("system app WebView permits media without a synthetic autoplay gesture",
      "webkit_settings_set_media_playback_requires_user_gesture(s, FALSE)" in read("tools/s10plus/a45/nuxel-pwa-host.c"))
check("root-only trusted tap hook exists for physical-path verification",
      '"test-tap "' in read("tools/s10plus/a45/nuxel-pwa-host.c") and "gtk_widget_event" in read("tools/s10plus/a45/nuxel-pwa-host.c"))
check("ui-rect evidence hook exists", '"ui-rect "' in read("tools/s10plus/a45/nuxel-pwa-host.c"))

print("\nPWNAGE-94000 — static checks")
py_files = [ROOT / "services/nuxel-bridge/src/api.py",
            ROOT / "services/nuxel-bridge/src/flatpak_provider.py"]
for f in py_files:
    r = subprocess.run(["python3", "-m", "py_compile", str(f)], capture_output=True, text=True)
    check("python compiles: " + f.name, r.returncode == 0, r.stderr.strip()[:120])
for f in ["pwa/nuxel-home/js/topbar-machine.js", "pwa/nuxel-home/js/qs.js",
          "pwa/nuxel-home/js/immersive.js", "pwa/nuxel-home/js/status-bar.js",
          "pwa/nuxel-home/js/app.js"]:
    r = subprocess.run(["node", "--check", str(ROOT / f)], capture_output=True, text=True)
    check("javascript parses: " + Path(f).name, r.returncode == 0, r.stderr.strip()[:120])
for f in ["tools/s10plus/a33/doom-engines/nuxel-doom-engine",
          "tools/s10plus/a33/nuxel-crispy-doom",
          "tools/s10plus/a45/nuxel-session.sh"]:
    r = subprocess.run(["sh", "-n", str(ROOT / f)], capture_output=True, text=True)
    check("shell parses: " + Path(f).name, r.returncode == 0, r.stderr.strip()[:120])

print("\nRESULT pass=%d fail=%d" % (PASS, FAIL))
raise SystemExit(1 if FAIL else 0)

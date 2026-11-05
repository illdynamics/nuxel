#!/usr/bin/env python3
"""PWNAGE-80000 offline acceptance checks (no phone required).

These checks bind each owner requirement to the actual deployed source path:
the Home PWA, nuxel-pwa-host, nuxel-button-manager, nuxel-osd, the a59
foreign-toplevel used by the pwnage62000 deploy, and nuxel-wl-fb.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PASS = FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS " + name + ((" — " + detail) if detail else ""))
    else:
        FAIL += 1
        print("  FAIL " + name + ((" — " + detail) if detail else ""))


def read(rel: str) -> str:
    return (ROOT / rel).read_text(errors="replace")


def main() -> int:
    print("PWNAGE-80000 acceptance checks")

    print("\n[zoom]")
    zp = read("pwa/nuxel-common/zoom-policy.js")
    check("central zoom policy exists", "NuxelZoomPolicy" in zp)
    check("central policy defaults to deny", "defaultDeny: true" in zp and "return state.default === 'allow'" in zp)
    check("future Permission Manager integration point exists", "setPolicy" in zp)
    check("pinch gesture events are denied", "gesturestart" in zp and "gesturechange" in zp)
    check("Ctrl/Meta wheel zoom is denied", "ctrlKey" in zp and "wheel" in zp)
    check("Ctrl/Meta +/-/0 zoom is denied", "e.key === '+'" in zp and "e.key === '0'" in zp)
    check("only multi-touch is cancelled, not one-finger input", "touches.length > 1" in zp)
    zcfg = json.loads(read("configs/nuxel/policy/zoom.json"))
    check("zoom policy document is default-deny", zcfg.get("default") == "deny" and zcfg.get("apps") == {})
    host = read("tools/s10plus/a45/nuxel-pwa-host.c")
    check("host injects policy into every frame", "ZOOM_POLICY_JS" in host and "WEBKIT_USER_CONTENT_INJECT_ALL_FRAMES" in host)
    check("host pins WebKit magnification and page zoom", '"magnification", 1.0' in host and '"zoom-level", 1.0' in host)
    check("host denies GtkGestureZoom capture", "gtk_gesture_zoom_new" in host and "GTK_EVENT_SEQUENCE_DENIED" in host)
    check("host denies Ctrl+wheel", "on_ctrl_scroll" in host and "GDK_CONTROL_MASK" in host)
    bad = []
    for f in sorted((ROOT / "pwa/nuxel-apps").glob("*/index.html")):
        html = f.read_text(errors="replace")
        m = re.search(r'<meta\s+name="viewport"[^>]*content="([^"]+)"', html, re.I)
        if not m:
            continue
        c = m.group(1)
        if not ("maximum-scale=1" in c and "minimum-scale=1" in c and "user-scalable=no" in c):
            bad.append(str(f.relative_to(ROOT)))
    check("every app viewport denies scaling", not bad, ", ".join(bad[:4]))

    print("\n[back + lifecycle]")
    app = read("pwa/nuxel-home/js/app.js")
    check("keyboard is first in Back precedence", re.search(r"back\(\) \{[\s\S]{0,900}?_keyboardVisible\(\)", app) is not None)
    check("Back at PWA root requests graceful close", "back:pwa-at-root-graceful-close" in app and "gracefulCloseForeground('back-root')" in app)
    check("Back at native root requests graceful close", "back:native-at-root-graceful-close" in app)
    check("normal Back never calls force-kill", re.search(r"back\(\) \{[\s\S]*?gracefulCloseForeground[\s\S]*?\}\s*\n\s*home\(\)", app) is not None and "terminateForeground" not in app[app.index("back() {"):app.index("home() {")])
    check("PWA Back tracks real history depth", "_installPwaHistoryProbe" in app and "__nuxelNavDepth" in app and "__nuxelBackPending" in app)
    check("PWA Back honours explicit app navigation state", "window.NuxelBack" in app and "_pwaExplicitBack" in app and "canGoBack" in app)
    check("PWA Back ignores hidden app controls", "_visibleBackControl" in app and "closest('[hidden], [aria-hidden=\"true\"]')" in app and "getBoundingClientRect" in app)
    check("graceful close and force kill are separate APIs", "gracefulCloseApp" in app and "forceKillApp" in app and "forceKillForeground" in app)
    check("background PWAs are not misclassified as native", "app.type === 'native' || app.type === 'flatpak' || (isForeground && !frame)" in app and "const surface = this.appSurfaces.get(appId)" in app)
    check("force kill is the long-Back path", "terminateForeground() {\n        return this.forceKillForeground('long-back');" in app)
    check("close removes only orphaned app surfaces", "querySelectorAll('.pwa-frame,.pwa-app-status,.pwa-app-bar')" in app and "const live = new Set()" in app and "if (!live.has(el)) el.remove()" in app)
    check("close retires the exact session from Recents", "if (appId) this.sessions.close(appId)" in app)
    check("close dispatches after-app-close redraw", "host.action('after-app-close')" in app)
    check("app close re-focuses the Home WebView", "gtk_widget_grab_focus(GTK_WIDGET(g_main_view))" in host and 'focus=home' in host)
    check("focus restoration runs after the async WebKit blur", "refocus_home_after_blur" in host and "g_timeout_add(80, refocus_home_after_blur" in host)
    check("lockscreen transition requests a full redraw", "host.action('force-redraw')" in app[app.index("    _lock(reason) {"):app.index("    _unlock(reason) {")])
    rec = read("pwa/nuxel-home/js/recents.js")
    check("Recents swipe left is graceful", "dx < 0" in rec and "_graceful(appId" in rec)
    check("Recents swipe right is force-kill", "dx > 0" in rec and "_force(appId" in rec)
    check("Recents shows a closing state", "closing" in rec and ".closing" in read("pwa/nuxel-home/css/status-bar.css"))
    check("Recents cards expose stable ids for the live swipe harness", "recents-card-${app.id}" in rec)
    check("native shell has a bounded Recents swipe harness", "ui-swipe " in host and "PointerEvent" in host and "invalid_swipe_target" in host)

    print("\n[invisible overlay / keyboard]")
    check("host hide-keyboard does not raise Home", "host_hide_keyboard" in host and "focus_bounce=1 home_raise=0" in host)
    check("foreign-toplevel supports hide-keyboard", "hide-keyboard" in read("tools/s10plus/a59/nuxel-foreign-toplevel.c"))
    check("keyboard focus is published to the native shell", "nuxelKeyboard" in host and "/run/nuxel-keyboard.visible" in host)
    check("keyboard visibility is pushed to Home for Back precedence", "keyboard-visible" in host and "__nuxelHostEvent" in host)
    check("Home consumes native keyboard visibility", "_nativeKeyboardVisible" in app and "keyboard-visible" in app)
    bm = read("tools/s10plus/a45/nuxel-button-manager.c")
    check("swipe-down on the keyboard dismisses it", "KB_SWIPE_DOWN_DISMISS" in bm and "action hide-keyboard" in bm)
    check("keyboard visibility slurp buffer is not heap-freed", "free(kv)" not in bm and "slurp() returns its static buffer" in bm)
    _fk = app.index("    forceKillForeground(reason) {")
    _fk_end = app.index("    forceKillApp(appId", _fk)
    check("force kill dismisses keyboard before surface teardown", "this._dismissKeyboard();" in app[_fk:_fk_end])
    wlfb = read("tools/s10plus/a67/nuxel-wl-fb.c")
    check("framebuffer bridge supports one-shot full repaint", '"repaint"' in wlfb and "force_full_frames" in wlfb and "REPAINT_FULL" in wlfb)
    check("repaint is one-shot, not a timer", "force_full_frames = 2" in wlfb and "sleep" not in wlfb[wlfb.index('force_full_frames = 2')-200:wlfb.index('force_full_frames = 2')+200])

    print("\n[calendar]")
    cal = read("pwa/nuxel-apps/calendar/index.html")
    caljs = read("pwa/nuxel-apps/calendar/js/calendar.js")
    check("Calendar requests persistent triple navigation", "nuxel:nav-visible" in caljs and "setNavVisible(true)" in caljs)
    check("Calendar app respects Back in its editor", 'data-action="back"' in cal)
    check("Calendar exposes explicit Back navigation state", "window.NuxelBack" in caljs and "canAppGoBack" in caljs and "appGoBack" in caljs)
    elem_map = re.search(r"var ELEMENT_IDS = \{(.*?)\n  \};", caljs, re.S)
    mapped_ids = re.findall(r"\w+: '([^']+)'", elem_map.group(1)) if elem_map else []
    camel = set(re.findall(r"el\.([A-Za-z]\w*)", caljs)) - {"Calendar", "ids", "setNavVisible"}
    camel_keys = set(re.findall(r"(\w+): '[^']+'", elem_map.group(1))) if elem_map else set()
    check("Calendar element map covers every controller property", bool(elem_map) and not (camel - camel_keys))
    check("Calendar element ids all exist in the document", bool(mapped_ids) and all(('id="' + i + '"') in cal for i in mapped_ids))
    check("Calendar time fields use numeric input purpose", cal.count('inputmode="numeric"') >= 2 and 'data-input-purpose="time"' in cal)
    check("Calendar provides a time keypad with a colon key", 'id="time-keypad"' in cal and 'data-time-key=":"' in cal)
    check("Calendar keypad supports digits/backspace/clear/now/done", all(k in cal for k in ('data-time-key="0"', 'data-time-key="back"', 'data-time-key="clear"', 'data-time-key="now"', 'data-time-key="done"')))
    check("Calendar hides keypad on editor close", "closeTimeKeypad" in caljs)
    check("Calendar editor hidden class is actually hidden", ".event-editor.hidden" in read("pwa/nuxel-apps/calendar/css/calendar.css"))

    print("\n[app drawer]")
    launcher = read("pwa/nuxel-home/js/launcher.js")
    css = read("pwa/nuxel-home/css/launcher.css")
    check("drawer default is three columns", "drawerColumns: 3" in launcher and "--drawer-columns, 3" in css)
    check("drawer grid cannot overflow", "repeat(var(--drawer-columns, 3), minmax(0, 1fr))" in css and "max-width: 100%" in css)
    check("orientation reflow resets zoom and rebuilds drawer", "reset-zoom" in launcher and "_renderDrawerApps(true)" in launcher and "visualViewport" in launcher)

    print("\n[power menu + reboot]")
    check("power-menu FIFO accepts an explicit row index", "CTRL_MENU_SELECT" in bm and "menu-select 3" in bm)
    check("native OSD has a real input region for the menu", "osd_input_region" in read("tools/s10plus/a45/nuxel-osd.c"))
    osd_c = read("tools/s10plus/a45/nuxel-osd.c")
    check("native OSD maps touch to menu rows", "menu_row_at" in osd_c and "menu-select %d" in osd_c)
    check("native OSD also accepts pointer clicks", "wl_pointer_listener" in osd_c and "pointer_button_cb" in osd_c)
    osd = read("pwa/nuxel-home/js/osd.js")
    check("Home DOM does not duplicate the native power menu", "nativeOsdActive" in osd and "single power-menu instance" in osd)
    pm = json.loads(read("configs/nuxel/power/power-menu.json"))
    check("visible power options are not statically gated", all(e.get("trigger_allowed") is True for e in pm["entries"] if e.get("id") in ("restart", "power-off")))
    check("suspend is offered because logind supports it", any(e.get("id") == "suspend" for e in pm["entries"]))
    gate = json.loads(read("configs/nuxel/buttons/reboot-gate.json"))
    check("reboot gate no longer has a 30-minute lockout", gate.get("min_interval_s", 9999) <= 15 and gate.get("max_reboots_per_hour", 0) >= 2)
    check("host delegates restart/poweroff through the button-manager gate", "button-manager gate" in host and "HOST_ACTION %s -> button-manager gate" in host)
    check("button manager timestamps reboot spawn", "REBOOT_SPAWNED" in bm and '/run/nuxel/reboot-exec' in bm and '--no-block' in bm)
    check("button manager publishes backend verdict", 'power-action.result' in bm)
    check("button manager confirms systemd accepted the job", "REBOOT_ACCEPTED" in bm and "spawned-unconfirmed" in bm and "WEXITSTATUS(status) == 0" in bm)
    check("Settings reports the backend power verdict", "power-action-result" in read("pwa/nuxel-apps/settings/power-menu.js") and "accepted by systemd" in read("pwa/nuxel-apps/settings/power-menu.js"))
    check("systemd stop is bounded", (ROOT / "services/nuxel-s10/systemd/system.conf.d/50-nuxel-bounded-stop.conf").is_file() and "DefaultTimeoutStopSec=15s" in read("services/nuxel-s10/systemd/system.conf.d/50-nuxel-bounded-stop.conf"))
    cue_paths = [
        "services/nuxel-session/systemd/nuxel-boot-sound.service.d/99-p80000-fast-stop.conf",
        "services/nuxel-s10/systemd/p80000-boot-sound-fast-stop.conf",
    ]
    cue_stops = [read(p) for p in cue_paths]
    check("cosmetic boot sound cannot hold shutdown", all("TimeoutStopSec=5s" in t for t in cue_stops))
    check("boot cue stop attaches to the cue process, not the warm-up helper",
          all("KillMode=process" in t and "KillMode=control-group" not in t for t in cue_stops))

    print("\n[doom + nuxtore]")
    cat = json.loads(read("pwa/nuxel-apps/nuxtore/catalog/nuxtore-catalog.json"))
    ids = [p["id"] for p in cat.get("packages", [])]
    doom = next((p for p in cat.get("packages", []) if p.get("id") == "org.nuxel.Doom"), {})
    doomjs = read("pwa/nuxel-apps/doom/js/doom.js")
    check("Doom exposes explicit Back navigation state", "window.NuxelBack" in doomjs and "canAppGoBack" in doomjs and "appGoBack" in doomjs)
    check("Nuxel Doom is a single NuXtore package", ids.count("org.nuxel.Doom") == 1)
    check("standalone Chocolate Doom package is gone", "org.nuxel.Doom.Chocolate" not in ids)
    check("standalone Chocolate Doom app tree is gone", not (ROOT / "pwa/nuxel-apps/doom-chocolate").exists())
    check("Nuxel Doom declares a complete bundled engine", "WebAssembly" in (doom.get("runtime") or {}).get("engine", ""))
    check("Nuxel Doom declares Freedoom runtime and WAD roots", any("freedoom" in r.lower() for r in doom.get("requires", [])) and doom.get("runtime", {}).get("wad_roots"))
    check("Nuxel Doom reports default WADs", doom.get("runtime", {}).get("default_wads") == ["freedoom1.wad", "freedoom2.wad", "freedm.wad"])
    check("no commercial WAD is bundled", doom.get("wad_policy", {}).get("commercial_wads_bundled") is False and doom.get("runtime", {}).get("bundled_wads") == [])
    check("WAD licence document ships with Doom", (ROOT / "pwa/nuxel-apps/doom/WAD-LICENSES.md").is_file())
    check("Doom import flow exists in UI and bridge", "wad-import" in read("pwa/nuxel-apps/doom/index.html") and "import_bytes" in read("services/nuxel-bridge/src/doom_assets.py") and "missing_file_data" in read("services/nuxel-bridge/src/api.py"))
    bundle_path = ROOT / "pwa/nuxel-apps/nuxtore/catalog" / doom.get("bundle", "bundles/org.nuxel.Doom-2.0.0.bundle.json")
    check("Doom bundle includes the WAD licence doc", bundle_path.is_file() and any("WAD-LICENSES.md" in f.get("path", "") for f in json.loads(bundle_path.read_text())))
    verify = subprocess.run([sys.executable, "pwa/nuxel-apps/nuxtore/tools/nuxtore-verify.py", "--root", "."], cwd=ROOT, capture_output=True, text=True)
    check("NuXtore catalog signature and every bundle digest verify", verify.returncode == 0 and "all packages verified" in verify.stdout, (verify.stdout or verify.stderr).strip().splitlines()[-1] if (verify.stdout or verify.stderr).strip() else "")

    print("\n[syntax]")
    js_files = [
        "pwa/nuxel-home/js/app.js", "pwa/nuxel-home/js/recents.js", "pwa/nuxel-home/js/launcher.js",
        "pwa/nuxel-home/js/immersive.js", "pwa/nuxel-home/js/osd.js", "pwa/nuxel-common/zoom-policy.js",
        "pwa/nuxel-apps/calendar/js/calendar.js", "pwa/nuxel-apps/doom/js/doom.js",
        "pwa/nuxel-apps/nuxtore/js/nuxtore.js",
    ]
    for f in js_files:
        p = subprocess.run(["node", "--check", str(ROOT / f)], capture_output=True, text=True)
        check("JS syntax " + f, p.returncode == 0, (p.stderr or "").strip()[:120])
    for f in ["services/nuxel-bridge/src/api.py", "services/nuxel-bridge/src/doom_assets.py"]:
        p = subprocess.run([sys.executable, "-m", "py_compile", str(ROOT / f)], capture_output=True, text=True)
        check("Python syntax " + f, p.returncode == 0, (p.stderr or "").strip()[:120])

    print("\n%d passed, %d failed" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

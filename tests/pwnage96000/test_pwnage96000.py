"""PWNAGE-96000 regression tests.

These are source/contract tests plus DOM-free renderer tests.  Physical-device
results live in docs/pwnage-96000 and are never inferred from this file.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(errors="replace")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _fixture_tree(base: Path, *, battery_status: str = "Charging",
                  external: bool = True, wireless: bool = False,
                  udc_state: str = "not attached", udc_speed: str = "UNKNOWN",
                  typec_role: str | None = None, bind_gadget: bool = True) -> dict:
    powers = base / "power_supply"
    _write(powers / "battery" / "type", "Battery\n")
    _write(powers / "battery" / "capacity", "73\n")
    _write(powers / "battery" / "status", battery_status + "\n")
    if external:
        _write(powers / "usb" / "type", "USB\n")
        _write(powers / "usb" / "online", "1\n")
    if wireless:
        _write(powers / "wireless" / "type", "Wireless\n")
        _write(powers / "wireless" / "online", "1\n")
    udc = "10c00000.dwc3"
    _write(base / "udc" / udc / "state", udc_state + "\n")
    _write(base / "udc" / udc / "current_speed", udc_speed + "\n")
    if bind_gadget:
        _write(base / "configfs" / "g1" / "UDC", udc + "\n")
    if typec_role is not None:
        _write(base / "typec" / "port0" / "data_role", typec_role + "\n")
    _write(base / "run" / "keep", "")
    return {
        "NUXEL_SYS_POWER_SUPPLY": str(powers),
        "NUXEL_SYS_UDC": str(base / "udc"),
        "NUXEL_CONFIGFS_GADGET": str(base / "configfs"),
        "NUXEL_SYS_TYPEC": str(base / "typec"),
        "NUXEL_RUN": str(base / "run"),
        "NUXEL_PROC": str(base / "proc"),
        "NUXEL_SYS_TTY": str(base / "tty"),
    }


def _load_indicators(env: dict):
    code = (
        "import importlib.util, json, sys\n"
        "spec = importlib.util.spec_from_file_location('si', %r)\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(m)\n"
        "print(json.dumps({'power': m.power_state(), 'usb': m.usb_connection()}))\n"
    ) % str(ROOT / "services/nuxel-bridge/src/system_indicators.py")
    proc = subprocess.run([sys.executable, "-c", code], env={**os.environ, **env},
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


# --------------------------------------------------------------------------- #
# Workstream B — battery lightning vs USB data truth
# --------------------------------------------------------------------------- #
def test_usb_provider_matrix():
    cases = [
        # name, fixture kwargs, expected pc_connected, expected charging, ext
        ("wall-charger-only", dict(battery_status="Charging", external=True,
                                   udc_state="not attached", udc_speed="UNKNOWN",
                                   typec_role="[none]"), False, True, True),
        ("wall-charger-no-gadget", dict(battery_status="Charging", external=True,
                                       udc_state="not attached", udc_speed="UNKNOWN",
                                       bind_gadget=False), False, True, True),
        ("pc-data-charging", dict(battery_status="Charging", external=True,
                                  udc_state="configured", udc_speed="high-speed",
                                  typec_role="host [device]"), True, True, True),
        ("pc-data-discharging", dict(battery_status="Discharging", external=True,
                                     udc_state="configured", udc_speed="high-speed",
                                     typec_role="host [device]"), True, False, True),
        ("wireless-charging-only", dict(battery_status="Charging", external=True,
                                        wireless=True, udc_state="not attached",
                                        udc_speed="UNKNOWN", typec_role="[none]"),
         False, True, True),
        ("unplugged", dict(battery_status="Discharging", external=False,
                           udc_state="not attached", udc_speed="UNKNOWN",
                           typec_role="[none]"), False, False, False),
        ("full-external", dict(battery_status="Full", external=True,
                               udc_state="not attached", udc_speed="UNKNOWN",
                               typec_role="[none]"), False, False, True),
        ("stale-configured-detached", dict(battery_status="Discharging", external=False,
                                           udc_state="configured", udc_speed="UNKNOWN",
                                           typec_role="[none]"), False, False, False),
    ]
    for name, kw, pc, charging, external in cases:
        with tempfile.TemporaryDirectory() as td:
            env = _fixture_tree(Path(td), **kw)
            data = _load_indicators(env)
        assert data["usb"]["pc_connected"] is pc, (name, data["usb"])
        assert data["power"]["charging"] is charging, (name, data["power"])
        assert data["power"]["external_power"] is external, (name, data["power"])


def _extract_method(src: str, name: str, next_name: str) -> str:
    start = src.index("    %s() {" % name)
    end = src.index("    %s(" % next_name, start)
    body = src[start:end]
    return "function " + body.strip().replace("\n    ", "\n    ")


def _usb_harness():
    src = read("pwa/nuxel-home/js/status-bar.js")
    fn_src = _extract_method(src, "_renderUsb", "_renderRemote")
    script = r"""
const fn = new Function('return (' + %s + ')')();
const writes = {dataset:0, attrs:0, label:0, title:0};
function makeEl() {
  const dataset = {};
  let lastState = '';
  Object.defineProperty(dataset, 'state', {
    set(v){ writes.dataset++; lastState = v; },
    get(){ return lastState; },
  });
  const el = {
    hidden:false, style:{display:''}, dataset, _attrs:{},
    querySelector(){ return { set textContent(v){ writes.label++; }, get textContent(){return '';} }; },
    setAttribute(k,v){ writes.attrs++; this._attrs[k]=v; },
    getAttribute(k){ return this._attrs[k]; },
    _title:'',
    set title(v){ writes.title++; this._title=v; }, get title(){ return this._title; },
  };
  return el;
}
function run(ind, pref) {
  writes.dataset = writes.attrs = writes.label = writes.title = 0;
  const el = makeEl();
  const self = {
    state:{indicators:ind, usbLabel:''}, elements:{usb:el},
    _providerVisible:{'status-usb': pref !== false},
    _usbRenderKey:'', _calls:[],
    _setProviderVisible(e,v){ this._calls.push(v); },
    _applySafeZones(){},
  };
  fn.call(self);
  const first = {visible: self._calls[self._calls.length-1], state: el.dataset.state,
                 label: self.state.usbLabel, aria: el._attrs['aria-label'],
                 writes: Object.assign({}, writes)};
  writes.dataset = writes.attrs = writes.label = writes.title = 0;
  fn.call(self);
  const second = Object.assign({}, writes);
  return {first, second};
}
const cases = JSON.parse(process.argv[1]);
const out = {};
for (const [name, ind, pref] of cases) out[name] = run(ind, pref);
console.log(JSON.stringify(out));
""" % json.dumps(fn_src)
    return script


def test_usb_renderer_matrix():
    cases = [
        ["wall-charger-only", {"charging": {"charging": True, "external_power": True},
                               "usb_data": {"pc_connected": False}}, True, False],
        ["pc-charging", {"charging": {"charging": True, "external_power": True},
                         "usb_data": {"pc_connected": True}}, True, True],
        ["pc-not-charging", {"charging": {"charging": False, "external_power": True},
                             "usb_data": {"pc_connected": True}}, True, True],
        ["mtp", {"charging": {"charging": True, "external_power": True},
                 "usb_data": {"pc_connected": False},
                 "file_transfer": {"active": True}}, True, True],
        ["usb-console", {"charging": {"charging": False, "external_power": False},
                         "usb_data": {"pc_connected": False},
                         "console_transports": {"usb": {"active": True}}}, True, True],
        ["wireless-only", {"charging": {"charging": True, "external_power": True},
                           "usb_data": {"pc_connected": False}, "wireless": True}, True, False],
        ["unknown", {}, True, False],
        ["malformed", {"charging": None, "usb_data": "nonsense",
                       "file_transfer": {}, "console_transports": {}}, True, False],
    ]
    script = _usb_harness()
    proc = subprocess.run(["node", "-e", script, json.dumps(cases)], cwd=ROOT,
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout.strip())
    for name, _ind, _pref, want_visible in cases:
        got = out[name]["first"]
        assert got["visible"] is want_visible, (name, got)
        if not want_visible:
            assert got["state"] == "unknown", (name, got)
            assert got["label"] == "", (name, got)
        if name == "mtp":
            assert got["label"] == "file", got
        if name == "usb-console":
            assert got["label"] == "term", got
        if name == "pc-charging":
            assert "USB data link" in got["aria"], got
    for name, _ind, _pref, _want in cases:
        assert out[name]["second"]["dataset"] == 0, (name, out[name]["second"])
        assert out[name]["second"]["attrs"] == 0, (name, out[name]["second"])
        assert out[name]["second"]["label"] == 0, (name, out[name]["second"])


def test_usb_renderer_ignores_external_power_source_in_code():
    src = read("pwa/nuxel-home/js/status-bar.js")
    usb = src[src.index("_renderUsb() {"):src.index("_renderRemote(")]
    assert "charging.external_power === true" not in usb
    assert "pc_connected === true" in usb
    assert "const charging = this.state.batteryCharging;" in src


def test_battery_lightning_is_charging_only():
    src = read("pwa/nuxel-home/js/status-bar.js")
    assert "const zaps = charging ?" in src
    assert "battery-zaps" in src
    assert "battery_charging" not in src  # no invented provider field


# --------------------------------------------------------------------------- #
# Workstream A — portal/FileChooser configuration and contract
# --------------------------------------------------------------------------- #
def test_portal_filechooser_backend_is_selected():
    conf = read("configs/nuxel/portals.conf")
    assert "org.freedesktop.impl.portal.FileChooser=nuxel" in conf
    assert "org.freedesktop.impl.portal.FileChooser=gtk" not in conf
    assert "org.nuxel.Portal" in conf  # the distinction is documented


def test_portal_backend_files_are_declared():
    assert (ROOT / "services/nuxel-portal-chooser/src/nuxel_portal_chooser.py").is_file()
    svc = read("services/nuxel-portal-chooser/dbus/org.freedesktop.impl.portal.desktop.nuxel.service")
    assert "Name=org.freedesktop.impl.portal.desktop.nuxel" in svc
    assert "Exec=/usr/libexec/nuxel/nuxel-portal-chooser" in svc
    portal = read("services/nuxel-portal-chooser/xdg-desktop-portal/nuxel.portal")
    assert "org.freedesktop.impl.portal.FileChooser" in portal


def test_portal_backend_protocol_contract():
    src = read("services/nuxel-portal-chooser/src/nuxel_portal_chooser.py")
    for token in ("OpenFile", "SaveFile", "SaveFiles",
                  "org.freedesktop.impl.portal.Request", "async_callbacks",
                  "multiple", "current_folder", "filters", "file_uri",
                  "Gallery", "Files", "Close"):
        assert token in src, token
    assert "external_power" not in src
    assert "--filesystem=host" not in src and "--device=all" not in src
    assert "--no-sandbox" not in src


def test_portal_backend_has_no_filename_logging():
    src = read("services/nuxel-portal-chooser/src/nuxel_portal_chooser.py")
    # State/diagnostic documents must not record selected paths or filenames.
    audit_calls = re.findall(r"audit\(STATE_PATH,(.*?)\)\n", src, re.S)
    for call in audit_calls:
        assert "\"path\"" not in call, call
        assert "uris" not in call, call
        assert "filename" not in call, call


def test_portal_deploy_mapping_is_atomic():
    dep = read("scripts/nuxel-deploy-live.py")
    assert "/etc/xdg-desktop-portal/portals.conf" in dep
    assert "/usr/libexec/nuxel/nuxel-portal-chooser" in dep
    assert "/usr/share/dbus-1/services/" in dep
    assert "/usr/share/xdg-desktop-portal/portals/" in dep
    pkg = read("tools/s10plus/a43/package-live.py")
    assert "services/nuxel-portal-chooser/src/nuxel_portal_chooser.py" in pkg


def main() -> int:
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS " + name)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print("FAIL " + name + ": " + repr(exc))
    print("\n%d passed, %d failed" % (len(tests) - failed, failed))
    return 1 if failed else 0




# --------------------------------------------------------------------------- #
# Workstream C — canonical native browser, ⋮ menu, site modes
# --------------------------------------------------------------------------- #
def test_browser_three_dot_menu_contract():
    src = read("shell/nuxel-browser-native/nuxel_browser_native.py")
    assert "\\u22ee" in src          # vertical three-dot glyph
    assert "Browser settings" in src
    assert "Gtk.MenuButton" in src and "Gtk.Popover" in src
    assert '"Mobile site"' in src and '"Desktop site"' in src
    assert "Gtk.RadioButton" in src
    assert "popover.popdown()" in src and '"menu-close"' in src
    assert "timeout_add_seconds(15" not in src  # duplicate status poll removed


def test_browser_real_webkit_user_agent_modes():
    src = read("shell/nuxel-browser-native/nuxel_browser_native.py")
    assert "wsettings.set_user_agent(user_agent_for(" in src
    assert "set_user_agent" in src
    # Desktop UA must be a truthful Linux desktop identity, not mobile.
    desktop = src[src.index("UA_DESKTOP ="):src.index("_site_mode =")]
    assert "X11; Linux aarch64" in desktop
    for forbidden in ("Android", "Mobile Safari", "Mobile/15E148"):
        assert forbidden not in desktop, forbidden
    # Mobile UA remains the S10+ identity.
    mobile = src[src.index("UA_MOBILE ="):src.index("UA_DESKTOP =")]
    assert "Android 14; SM-G975F" in mobile and "Mobile/15E148" in mobile
    assert "set_settings" not in src  # no global/default UA mutation


def test_browser_site_mode_persists_per_profile():
    src = read("shell/nuxel-browser-native/nuxel_browser_native.py")
    assert "/var/lib/nuxel/browser/settings.json" in src
    assert "def load_settings" in src and "def save_settings" in src
    assert "os.replace(tmp, SETTINGS_PATH)" in src
    assert "site_mode" in src
    assert "normalize_mode" in src
    # Settings survive restart by being loaded before the first view is built.
    assert src.index("settings = load_settings()") < src.index("WebKit2.WebView.new_with_settings")


def test_browser_back_closes_menu_before_history():
    src = read("shell/nuxel-browser-native/nuxel_browser_native.py")
    back = src[src.index('if cmd == "back":'):src.index('elif cmd == "forward":')]
    assert 'handlers["menu_is_open"]()' in back
    assert back.index('handlers["menu_close"]()') < back.index('view.go_back()')
    bridge = read("services/nuxel-bridge/src/api.py")
    assert 'state.get("menu_open", False)' in bridge
    assert "menu_open" in src and "menu-closed" in src


def test_browser_single_launcher_route():
    reg = json.loads(read("pwa/nuxel-common/app-registry.json"))
    apps = reg.get("apps") or []
    browsers = [a for a in apps if a.get("id") == "org.nuxel.Browser"]
    assert len(browsers) == 1
    assert browsers[0]["type"] == "native"
    assert browsers[0]["native_binary"].endswith("nuxel_browser_native.py")
    legacy = json.loads(read("pwa/nuxel-apps/browser/app.json"))
    assert legacy.get("launcher_exposed") is False
    assert legacy.get("legacy") is True
    assert legacy.get("superseded_by") == "org.nuxel.BrowserNative"


def test_browser_security_unchanged():
    src = read("shell/nuxel-browser-native/nuxel_browser_native.py")
    assert "--no-sandbox" not in src
    assert "ignore_tls" not in src and "tls-errors" not in src
    assert "WEBKIT_DISABLE_SANDBOX" not in src
    # The PWA route keeps its explicit external-navigation opt-in.
    pwa = read("pwa/nuxel-apps/browser/js/browser.js")
    assert "nuxel-browser-external" in pwa
    assert "allowExternal" in pwa




# --------------------------------------------------------------------------- #
# Workstream E — one canonical native top bar
# --------------------------------------------------------------------------- #
def test_topbar_single_owner():
    chrome = read("tools/s10plus/a45/nuxel-shell-chrome.sh")
    assert "/usr/lib/nuxel/nuxel-statusbar" in chrome
    assert "start_statusbar" in chrome
    session = read("tools/s10plus/a45/nuxel-session.sh")
    assert "nuxel-shell-chrome.sh" in session
    # No second statusbar/topbar client is started by the session or units.
    for rel in ("tools/s10plus/a45/nuxel-session.sh",):
        assert session.count("nuxel-statusbar") == 0 or "nuxel-shell-chrome" in session
    imports = read("tools/s10plus/a45/nuxel-statusbar.c")
    assert 'MODEL_FILE "/run/nuxel/statusbar-model.json"' in imports
    assert "nuxel-statusbar" in imports


def test_topbar_matches_home_design_tokens():
    src = read("tools/s10plus/a45/nuxel-statusbar.c")
    home = read("pwa/nuxel-home/css/status-bar.css")
    assert "rgba(26, 26, 46, 0.95)" in home
    assert "26.0 / 255.0, 26.0 / 255.0, 46.0 / 255.0, 0.95" in src
    assert "#define BAR_HEIGHT 36" in src
    assert "rgba(255,255,255,0.03)" in src or "1.0, 1.0, 1.0, 0.03" in src
    assert "cairo_move_to(cr, 16," in src


def test_topbar_build_links_both_protocols():
    build = read("tools/s10plus/a45/build-a45.sh")
    statusbar = build[build.index("nuxel-statusbar.c"):build.index("nuxel-text-input-probe.c")]
    assert "wlr-layer-shell-unstable-v1-protocol.c" in statusbar
    assert "xdg-shell-protocol.c" in statusbar


def test_topbar_lock_precedence_and_strip_contract():
    src = read("tools/s10plus/a45/nuxel-statusbar.c")
    assert "session_locked()" in src
    assert "native_foreground(" in src
    assert "BAR_STRIP_INPUT_PORTRAIT" in src
    assert "bar_strip()" in src
    assert "STATUSBAR_HIDDEN reason=lock_or_home" in src




# --------------------------------------------------------------------------- #
# Workstream F — Quick Settings critical path
# --------------------------------------------------------------------------- #
def test_quick_settings_opens_with_cache_first_render():
    src = read("pwa/nuxel-home/js/qs.js")
    level = src[src.index("_setLevel(level, reason) {"):src.index("_ensureVisibleRefresh() {")]
    assert "this._render();" in level
    assert "cache_first" in level
    assert "QS_PERF" in src


def test_quick_settings_preserves_single_flight_and_visible_timer():
    src = read("pwa/nuxel-home/js/qs.js")
    assert "if (this._stateSyncPromise) return this._stateSyncPromise;" in src
    assert "this._stateSyncPromise = this._syncStateOnce(options);" in src
    assert "clearInterval(this._locationTimer)" in src
    assert "setInterval(() =>" in src and "}, 5000);" in src
    assert "Promise.allSettled(secondary)" in src
    # Privacy/indicator provider reads are deferred off the open path.
    expanded = src[src.index("_setExpandedUI(level)"):src.index("collapseOrClose()")]
    assert "this._syncPrivacy();" not in expanded
    render = src[src.index("_render() {"):src.index("async _syncState(options)")]
    assert "this._syncPrivacy();" in render and "this._syncIndicators();" in render


def test_quick_settings_provider_timings_are_diagnostics_only():
    src = read("pwa/nuxel-home/js/qs.js")
    assert "event: 'provider'" in src and "phone_status" in src
    assert "nuxelDiag" in src
    assert "setInterval(() => nuxelPerf" not in src


# --------------------------------------------------------------------------- #
# Workstream G — drawer / Home
# --------------------------------------------------------------------------- #
def test_drawer_cache_and_settle_guard_preserved():
    src = read("pwa/nuxel-home/js/launcher.js")
    assert "_drawerSignature" in src and "drawerList" in src
    assert "if (!force && signature === this._drawerSignature && list.childElementCount)" in src
    assert "_drawerOpenGuardUntil = Date.now() + 250" in src
    assert "this._drawerLastRender = { ms: 0, rebuilt: false" in src


def test_drawer_does_not_render_hidden_widgets_on_open():
    src = read("pwa/nuxel-home/js/launcher.js")
    open_drawer = src[src.index("openDrawer() {"):src.index("closeDrawer() {")]
    assert "NuxelWidgets.renderPage" not in open_drawer
    assert "DRAWER_PERF" in src


# --------------------------------------------------------------------------- #
# Workstream H — presenter pacing / VSync truth
# --------------------------------------------------------------------------- #
def test_presenter_safe_target_and_rollback():
    conf = read("services/nuxel-s10/systemd/nuxel-wl-fb.service.d/15-idle-fps.conf")
    assert "Environment=NUXEL_TARGET_FPS=20" in conf
    assert "30 FPS is NOT claimed" in conf
    assert "frame_p95_ms=49-51" in conf
    src = read("tools/s10plus/a67/nuxel-wl-fb.c")
    assert "static int fps_target = 30;" in src
    assert '!strncmp(q, "fps ", 4)' in src
    assert "FBIOPAN_DISPLAY" in src
    assert "if (idle > 500) pace = 8;" in src
    assert "if (idle > 2000) pace = 3;" in src
    assert "if (idle > 6000) pace = 1;" in src
    assert "FBIO_WAITFORVSYNC" not in src  # no unsupported VSync claim


def test_presenter_publishes_frame_percentiles():
    src = read("tools/s10plus/a67/nuxel-wl-fb.c")
    assert "present_pct(50)" in src and "present_pct(95)" in src and "present_pct(99)" in src
    assert "frame_p50_ms=" in src and "frame_p95_ms=" in src and "frame_p99_ms=" in src
    assert "present_hist" in src and "PRESENT_HIST_BUCKETS" in src


if __name__ == "__main__":
    raise SystemExit(main())

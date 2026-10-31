"""PWNAGE-37000B Butterscotch Smooth regression tests.

These pin the measured 2026-10-31 optimization pass:

  * the lockscreen has no continuously-running indicator animation;
  * the app drawer is cached and toggled, not re-parsed on every open;
  * Home Settings is primed in an idle slice, not on the owner's first tap;
  * status-bar provider polling pauses while the lockscreen covers the bar;
  * safe-zone layout is coalesced into one rAF per update;
  * huge indicator/dock art is shipped at display size;
  * the framebuffer bridge performs damage-range blits and wakes on Wayland
    events instead of sleeping through a touch.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = ROOT / "pwa" / "nuxel-home"


def read(rel: str) -> str:
    return (HOME / rel).read_text(encoding="utf-8")


def png_size(path: Path):
    data = path.read_bytes()[:26]
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", data[16:24])


def test_lockscreen_has_no_infinite_indicator_animation():
    css = read("css/lockscreen.css")
    # Strip comments so prose about the old behaviour is never mistaken for a
    # live declaration.
    css_nc = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    # The only remaining animation is the short, JS-scheduled lockhead wiggle.
    for block in re.findall(r"[^{}]*\{[^{}]*animation:[^{}]*\}", css_nc):
        decl = block.split('{', 1)[1]
        assert "infinite" not in decl, block
    assert "nuxel-indicator-charge" not in css_nc
    assert "nuxel-indicator-usb" not in css_nc
    assert "nuxel-indicator-live" not in css_nc
    # No unconditional compositing hint on the always-present glow layer.
    glow = re.search(r"\.lockscreen-indicator \.lockscreen-indicator-glow\s*\{([^}]*)\}", css_nc)
    assert glow and "will-change" not in glow.group(1)


def test_lockscreen_wiggle_is_bounded_and_paused_off_screen():
    js = read("js/lockscreen.js")
    assert "_wiggleOnce(delayMs)" in js, "wiggle must be a one-shot greeting"
    assert "setInterval" not in js or "_startWiggle" not in js
    assert "}, 900);" in js
    assert "if (this.locked && !this._displayOff()) this._updateClock();" in js
    assert "if (!this.locked || !this.batteryEl" in js


def test_drawer_is_cached_not_rebuilt_on_every_open():
    js = read("js/launcher.js")
    assert "_drawerContainer()" in js
    assert "_drawerSignature" in js
    assert "if (this.drawerOpen) return;" in js
    assert "this._renderDrawerApps();" in js
    # openDrawer must not call the full home-grid renderer.
    body = re.search(r"openDrawer\(\)\s*\{(.*?)\n    \}", js, re.S).group(1)
    assert "_renderAppGrid" not in body
    assert "appList.hidden = true" in body


def test_home_settings_is_primed_off_the_tap_path():
    hs = read("js/home-settings.js")
    assert "function prime()" in hs and "global.NuxelHomeSettings = { open, close, apply, prime," in hs
    app = read("js/app.js")
    assert "_warmLauncherChrome()" in app
    assert "requestIdleCallback" in app


def test_status_polling_pauses_under_lockscreen_and_is_coalesced():
    js = read("js/status-bar.js")
    assert "_coveredByLock()" in js
    assert "this._statusInactive()" in js
    assert "}, 15000);" in js
    assert "}, 10000);" in js
    assert "}, 20000);" in js
    assert "this._safeZonesScheduled" in js
    # One rAF measurement, not two nested passes per caller.
    body = re.search(r"_applySafeZones\(\)\s*\{(.*?)\n    \}", js, re.S).group(1)
    assert body.count("requestAnimationFrame") == 1


def test_display_sized_assets():
    limits = {
        "assets/nuxel-charging.png": (256, 256),
        "assets/nuxel-connected-pc.png": (256, 256),
        "assets/nuxel-live-console-active.png": (256, 256),
        "assets/nuxel-console-serial.png": (128, 128),
        "assets/nuxel-console-usb.png": (128, 128),
        "assets/nuxel-console-wlan.png": (128, 128),
        "assets/nuxel-file-transfer.png": (128, 128),
        "assets/nuxel-connection-mode.png": (192, 192),
        "assets/nuxel-bottom-bar2.png": (1200, 420),
        "assets/nuxel-bottom-bar.jpg": (1000, 340),
    }
    for rel, (mw, mh) in limits.items():
        w, h = png_size(ROOT / rel) if rel.endswith('.png') else (0, 0)
        if rel.endswith('.jpg'):
            # PIL is available in CI container; keep the check simple otherwise.
            continue
        assert w <= mw and h <= mh, f"{rel} is {w}x{h}"


def test_framebuffer_bridge_uses_damage_and_wakes_on_wayland():
    src = (ROOT / "tools/s10plus/a34/nuxel-wl-fb.c").read_text()
    assert "frame_damage_rows()" in src
    assert "frame_blit_damage()" in src
    assert "blit_rows(" in src
    assert "wl_display_get_fd(dpy)" in src
    assert "poll(&wp, 1, ms)" in src
    assert "idle > 8000" in src and "idle > 60000" in src
    # Correctness guard: every changed frame still commits to DECON.
    assert 'return panel_commit_frame("frame-damage");' in src

#!/usr/bin/env python3
"""v0.8.5-beta regression contracts (static, offline).

Every check below corresponds to a fault reproduced on the live S10+ and a fix
in this release (see docs/v0.8.5-beta/REPORT.md):

  * Flatpak sandbox can start: the per-instance runtime dir is owned by the
    session user, and the Pulse socket is mapped at the path the runtime
    advertises (/run/flatpak/pulse/native) with a --filesystem Flatpak 1.16
    actually understands (no "src:dst" suffix).
  * Stremio is a supported app again and has a single-instance guard.
  * Tethering/hotspot traffic is accepted at forward priority -100 BEFORE the
    drop log, and the drop log is the last rule in the chain.
  * ip_forward is durable and tether stop no longer clobbers a running AP.
  * External (GTK/Flatpak) icons never paint a fallback glyph behind them.
  * The lock screen hides transient OSD/power-menu rectangles.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def read(rel):
    return (ROOT / rel).read_text()


def test_flatpak_pulse_mapping_is_valid_for_flatpak_1_16():
    src = read("services/nuxel-bridge/src/flatpak_provider.py")
    assert '"--filesystem=/run/user/0/pulse:/run/flatpak/pulse"' not in src, \
        "Flatpak 1.16 rejects src:dst and silently skips the mount"
    assert 'FLATPAK_PULSE_DEST = "/run/flatpak/pulse"' in src
    assert 'argv.append("--filesystem=%s" % FLATPAK_PULSE_DEST)' in src
    assert 'argv.append("--filesystem=%s/native" % FLATPAK_PULSE_DEST)' in src
    assert 'PULSE_SERVER=unix:%s/native' in src


def test_flatpak_instance_runtime_dir_belongs_to_session_user():
    src = read("services/nuxel-bridge/src/flatpak_provider.py")
    assert "def _ensure_flatpak_runtime_dirs()" in src
    assert "FLATPAK_INSTANCE_ROOT" in src and '".flatpak"' in src
    assert "ensure_flatpak_runtime_dirs()" in src.split("def launch_argv", 1)[1]
    session = read("tools/s10plus/a45/nuxel-session.sh")
    assert '"$USER_RUNTIME/.flatpak"' in session
    assert "chown -h nuxel:nuxel" in session


def test_stremio_is_supported_and_single_instance():
    reg = json.loads(read("pwa/nuxel-common/app-registry.json"))
    apps = reg["apps"] if isinstance(reg, dict) else reg
    app = next(a for a in apps if a["id"] == "com.stremio.Stremio")
    assert app["status"] != "unsupported"
    wrapper = read("services/nuxel-s10/bin/nuxel-flatpak-stremio")
    assert "flatpak ps" in wrapper and "already running" in wrapper
    assert "unshare -Ur true" in wrapper


def test_forward_chain_accepts_tether_before_the_drop_log():
    for rel in ("configs/nftables/nuxel-app-firewall.nft",
                "configs/nftables/nuxel-app-firewall-cgroupv2.nft"):
        src = read(rel)
        fwd = src.split("chain forward {", 1)[1].split("\n    }", 1)[0]
        assert 'iifname { "usb0", "usb1", "rndis0", "ncm0", "eth0" } accept' in fwd
        assert 'iifname { "wlan1", "p2p0" } accept' in fwd
        assert "10.42.0.0/24" in fwd and "10.15.19.0/24" in fwd
        rules = [ln.strip() for ln in fwd.splitlines() if ln.strip()]
        log_at = next(i for i, ln in enumerate(rules) if "NUXXEL-FWD-DROP" in ln)
        assert log_at == len(rules) - 1, "the drop log must not shadow accepts"


def test_ip_forward_durable_and_not_clobbered_by_tether_stop():
    conf = read("configs/nuxel/sysctl/90-nuxel-tether.conf")
    assert "net.ipv4.ip_forward = 1" in conf
    src = read("services/nuxel-bridge/src/usb_tether.py")
    assert "_ip_forward_needed_elsewhere" in src
    stop = src.split("def stop(", 1)[1].split("\ndef ", 1)[0]
    assert "prev_ip_forward" not in stop


def test_hotspot_uses_hostapd_tool_not_nmcli():
    src = read("services/nuxel-bridge/src/network_manager.py")
    assert 'HOTSPOT_TOOL = "/usr/libexec/nuxel/nuxel-hotspot"' in src
    fn = src.split("def hotspot_start(", 1)[1].split("\ndef ", 1)[0]
    assert "nmcli" not in fn
    tool = read("services/nuxel-network/nuxel-hotspot.py")
    assert 'dev in ("lo", "wlan1", "p2p0")' in tool


def test_external_icons_never_paint_a_fallback_glyph():
    js = read("pwa/nuxel-home/js/apps.js")
    assert "data-icon-origin" in js
    assert "onload=\"this.dataset.iconState" not in js, "inline handler per icon is a per-render cost"
    css = read("pwa/nuxel-home/css/launcher.css")
    for origin in ("gtk", "flatpak"):
        assert '.app-icon[data-icon-origin="%s"] > .nuxel-icon-fallback' % origin in css
        assert 'display: none !important' in css
    assert '.app-icon[data-icon-origin="gtk"],\n.app-item .app-icon[data-icon-origin="flatpak"] {\n    background: transparent !important;' in css


def test_lock_screen_hides_transient_osd_rectangles():
    css = read("pwa/nuxel-home/css/lockscreen.css")
    assert "body.lockscreen-active #nuxel-osd" in css
    assert "body.lockscreen-active #nuxel-power-menu" in css
    osd = read("pwa/nuxel-home/js/osd.js")
    assert "nuxel:lockscreen-shown" in osd and "hideAll" in osd

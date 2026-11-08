#!/usr/bin/env python3
"""PWNAGE-90000 shell reliability regressions (offline/static + parser)."""
from __future__ import annotations

import importlib.util
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(errors="replace")


def load_collector():
    spec = importlib.util.spec_from_file_location(
        "nuxel_systemd_graph_p90000_%d" % time.time_ns(),
        ROOT / "tools/diagnostics/nuxel-systemd-graph.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# ---- P90-01 restart acknowledgement / clean next boot ---------------------
def test_power_menu_never_writes_restart_accepted():
    src = read("pwa/nuxel-apps/settings/power-menu.js")
    assert "accepted by systemd" not in src
    assert "clearPowerTransient" in src
    assert "pagehide" in src and "beforeunload" in src
    # The reboot branch must not append ' accepted' to the entry label.
    reboot_branch = src[src.index("if (rebooting) {"):src.index("if (out) {", src.index("if (rebooting) {"))]
    assert "e.label + ' accepted'" not in reboot_branch
    assert "accepted by systemd" not in reboot_branch


def test_reboot_overlay_is_neutral_and_transient():
    css = read("pwa/nuxel-apps/settings/power-menu.css")
    assert "background: #000;" in css
    assert "#04121f" not in css
    assert "PWNAGE-90000" in css


# ---- P90-06 reload launcher ------------------------------------------------
def test_reload_launcher_retires_old_layers():
    src = read("pwa/nuxel-home/js/app.js")
    start = src.index("reloadLauncher() {")
    body = src[start:start + 2400]
    assert "nuxel:launcher-reload" in body
    assert "nuxel-reboot-overlay" in body
    assert "preload-cover" in body
    assert "NuxelImmersive.reset" in body
    assert "location.reload" in body
    # The next document must not replay boot chrome.
    assert "launcherReload" in src and "this._preloadCoverDone = true" in src


# ---- P90-07 / P90-13 Back + Home transition -------------------------------
def test_back_is_typed_and_unknown_is_not_root():
    api = read("services/nuxel-bridge/src/api.py")
    assert "_back_result" in api
    assert '"status"' in api
    assert '"unsupported"' in api
    # No unconditional false-root fallback remains.
    assert 'return ({"success": True, "handled": False, "at_root": True,\n                     "foreground": app_id}, 200)' not in api
    assert "NATIVE_BACK_SHORTCUTS" in api
    assert '"org.mozilla.firefox"' in api and '"org.videolan.VLC"' in api


def test_pwa_back_protocol_and_helper():
    app = read("pwa/nuxel-home/js/app.js")
    assert "_pwaBackProtocol" in app
    assert "nuxel:back-request" in app and "nuxel:back-result" in app
    assert "_returnToHome" in app
    assert "gracefulCloseForeground('back-root')" not in app
    helper = read("pwa/nuxel-common/back.js")
    assert "NuxelBackProtocol" in helper
    assert "declareAtRoot" in helper
    assert "event.source !== global.parent" in helper


def test_short_back_preserves_native_process():
    app = read("pwa/nuxel-home/js/app.js")
    body = app[app.index("if (!frame && this.appSession.app && this.appSession.state === 'ACTIVE'"):]
    body = body[:body.index("this._returnToHome('back-home')")]
    assert "_returnToHome('back-native-root')" in body
    assert "gracefulClose" not in body
    assert "forceKill" not in body


# ---- P90-08/09/10 top gesture state machine --------------------------------
def test_qs_upward_dismiss_from_expanded():
    qs = read("pwa/nuxel-home/js/qs.js")
    assert "expanded     + up   -> closed" in qs
    assert "Upward swipe closes the shade from BOTH compact and expanded" in qs
    assert "if (direction === 'up')" in qs and "this.close();" in qs
    assert "no-op" not in qs[qs.index("pull(direction"):qs.index("pull(direction") + 900]


def test_top_edge_two_stage_contract():
    imm = read("pwa/nuxel-home/js/immersive.js")
    assert "COMPACT_BAR + down -> EXPANDED_QUICK_SETTINGS" in imm
    assert "qs.open(); qs.expand()" in imm
    assert "nuxel:top-state" in imm
    status = read("pwa/nuxel-home/js/status-bar.js")
    assert "revealed:" in status and "source: 'status-bar'" in status
    # Native statusbar's second pull goes through the single Home owner.
    native = read("tools/s10plus/a45/nuxel-statusbar.c")
    assert "send_host_action" in native and 'quick-settings' in native
    host = read("tools/s10plus/a45/nuxel-pwa-host.c")
    assert "quick-settings" in host


# ---- P90-11 OSK-safe bottom strip -----------------------------------------
def test_navdock_remaps_over_osk():
    nav = read("tools/s10plus/a45/nuxel-navdock.c")
    assert "NAV_DOCK_KEYBOARD_REMAP" in nav
    assert "keyboard_visible()" in nav


# ---- P90-03 icons ----------------------------------------------------------
def test_icons_are_eager_only_on_visible_surfaces():
    apps = read("pwa/nuxel-home/js/apps.js")
    assert "nuxel-icon-fallback" in apps and "data-icon-state" in apps
    assert "visible ? 'eager' : 'lazy'" in apps
    assert "visible ? 'high' : 'low'" in apps
    launcher = read("pwa/nuxel-home/js/launcher.js")
    assert "_createGridNode" in launcher and "_updateGridNode" in launcher
    assert "gridSignature" in launcher
    css = read("pwa/nuxel-home/css/launcher.css")
    assert "nuxel-icon-img" in css and "opacity: 0" in css


def test_immutable_icon_cache_first_and_version_lockstep():
    sw = read("pwa/nuxel-home/sw.js")
    assert "cacheFirst" in sw and "IMMUTABLE_ICON_DIRS" in sw and "CRITICAL_ICONS" in sw
    manifest = json.loads(read("pwa/nuxel-home/manifest.json"))
    cache = manifest["nuxel"]["cache_version"]
    assert f"const CACHE_VERSION = '{cache}'" in sw
    # PWNAGE-93000 advanced the service-worker namespace so the notification
    # and sound-icon bundle cannot be served stale from a v080 cache.
    assert cache.startswith("v") and "-p" in cache
    assert cache != "v080-p90000"


# ---- P90-02 preload ownership / instrumentation --------------------------
def test_preload_controller_instrumentation_and_single_owner():
    ctl = read("services/nuxel-preload-cinema/nuxel-preload-cinema")
    assert "P90_PRELOAD_TIMEPOS" in ctl
    assert "P90_PRELOAD_STALL" in ctl
    assert "clock_advances" in ctl and "stall_count" in ctl
    assert "acquire_lock" in ctl and "DUPLICATE" in ctl
    cfg = json.loads(read("configs/nuxel/boot/preload-cinema.json"))
    assert cfg["hard_timeout_ms"] <= 20000 and cfg["max_display_ms"] >= 6000
    assert cfg["audio"] == "never"


def test_preload_layout_does_not_repeat_default_timings_in_session():
    session = read("tools/s10plus/a45/nuxel-session.sh")
    start = session.index("NUXEL_PRELOAD_EARLY=1")
    block = session[start:start + 600]
    assert "/usr/lib/nuxel/nuxel-preload-cinema --early" in block
    assert "NUXEL_PRELOAD_MAX_DISPLAY_MS" not in block
    assert "NUXEL_PRELOAD_POLL_MS" not in block


# ---- P90-04 lock/unlock no repeated restack --------------------------------
def test_lock_watch_is_edge_triggered_and_preload_safe():
    src = read("tools/s10plus/a59/nuxel-foreign-toplevel.c")
    assert "g_state_dirty" in src
    assert "preload_active" in src
    assert "preload-overlay-active" in src
    # The old unconditional 1 s level trigger must be gone from the outer test.
    outer = src[src.index("if (locked != 0 && (locked != last_locked"):]
    outer = outer[:outer.index("} else if (locked != 0)")]
    assert "nonhome_active || g_state_dirty" in outer


# ---- P90-12 systemd collector ---------------------------------------------
def test_systemd_parser_time_and_blame():
    mod = load_collector()
    t = mod.parse_systemd_time(
        "Startup finished in 1.5s (firmware) + 0.400s (loader) + 3.486s (kernel) + "
        "0.100s (initrd) + 14.099s (userspace) = 19.585s\n")
    assert t["available"] and abs(t["total_s"] - 19.585) < 1e-6
    assert abs(t["phases_s"]["kernel"] - 3.486) < 1e-6
    assert abs(t["phases_s"]["userspace"] - 14.099) < 1e-6
    blame = mod.parse_blame("  1.234s nuxel-wayland.service\n  250ms foo.service\n")
    assert blame[0]["unit"] == "nuxel-wayland.service"
    assert abs(blame[0]["seconds"] - 1.234) < 1e-6
    assert abs(blame[1]["seconds"] - 0.25) < 1e-6


def test_systemd_parser_shutdown_ignores_boot_restarts_and_missing_boot():
    mod = load_collector()
    journal = "\n".join([
        "[   12.405403] fedora systemd[1]: Stopping geoclue.service - Location Lookup Service...",
        "[   20.186119] fedora systemd[1]: Stopping nuxel-audio-session.service - audio...",
        "[ 2374.873797] fedora systemd-logind[5416]: System is rebooting.",
        "[ 2374.945965] fedora systemd[1]: Stopping avahi-daemon.service - Avahi...",
        "[ 2375.000000] fedora systemd[1]: Reached target shutdown.target - Shutdown.",
        "[ 2376.296249] fedora systemd[1]: Stopping nuxel-http-bridge.service - Bridge...",
    ])
    out = mod.parse_journal_shutdown(journal)
    assert out["status"] == "CAPTURED"
    assert out["first_monotonic_s"] >= 2374.8
    assert all(e["monotonic_s"] is None or e["monotonic_s"] >= 2374.8 for e in out["events"])
    assert not any("geoclue" in e["line"] for e in out["events"])
    missing = mod.parse_journal_shutdown("")
    assert missing["status"] == "NOT_CAPTURED"
    assert missing["events"] == []
    # Reordered messages, a repeated handoff marker, and a stop timeout: only
    # the final handoff window is kept, and timestamps remain min/max ordered.
    reordered = "\n".join([
        "[  12.0] systemd[1]: Stopping early-boot.service - boot restart...",
        "[ 900.0] systemd-logind: System is rebooting.",
        "[ 900.2] systemd[1]: Timed out stopping slow.service.",
        "[ 902.0] systemd[1]: Stopping late.service.",
        "[ 901.0] systemd[1]: Stopped out-of-order.service.",
        "[1000.0] systemd-logind: System is rebooting.",
        "[1001.0] systemd[1]: Timed out starting broken.service.",
    ])
    out2 = mod.parse_journal_shutdown(reordered)
    assert out2["status"] == "CAPTURED"
    assert out2["first_monotonic_s"] >= 1000.0 - 60.0
    assert any("Timed out" in e["line"] for e in out2["events"])
    assert not any("early-boot" in e["line"] for e in out2["events"])
    assert out2["last_monotonic_s"] >= out2["first_monotonic_s"]


def test_systemd_report_and_evidence_exist():
    report = ROOT / "SYSTEMD-GRAPH.md"
    assert report.is_file() and report.stat().st_size > 2000
    text = report.read_text(errors="replace")
    assert "## 1. Device and collection context" in text
    assert "## 6. Shutdown timeline" in text
    assert ("CAPTURED" in text) or ("NOT CAPTURED" in text)
    for name in ("SYSTEMD-BOOT.svg", "boot-systemd-analyze.txt", "boot-blame.txt",
                 "boot-critical-chain.txt", "boot-units.tsv",
                 "shutdown-journal-summary.txt", "collector-metadata.json"):
        p = ROOT / "diagnostics/systemd" / name
        assert p.is_file() and p.stat().st_size > 0, name
    meta = json.loads((ROOT / "diagnostics/systemd/collector-metadata.json").read_text())
    assert meta["boot_id"]
    assert meta["assets"]
    if meta.get("shutdown_status") == "CAPTURED":
        svg = ROOT / "diagnostics/systemd/SYSTEMD-SHUTDOWN.svg"
        assert svg.is_file() and svg.stat().st_size > 1000
        assert "SYSTEMD-SHUTDOWN.svg" in text


def test_packaging_includes_back_helper_and_reliability_assets():
    pkg = read("tools/s10plus/a43/package-live.py")
    ver = read("tools/s10plus/a43/verify-live.py")
    img = read("tools/s10plus/verify-fedora-phone-rootfs.py")
    assert "'pwa/nuxel-common/back.js'" in pkg
    assert "'pwa/nuxel-common/back.js'" in ver
    assert "/usr/share/nuxel/pwa/nuxel-common/back.js" in img
    assert "pwa/nuxel-apps/settings/power-menu.js" in img


def test_deploy_and_rollback_scripts_exist():
    dep = ROOT / "tools/pwnage90000/deploy-pwnage90000.sh"
    rb = ROOT / "tools/pwnage90000/rollback-pwnage90000.sh"
    assert dep.is_file() and dep.stat().st_size > 1000
    assert rb.is_file() and rb.stat().st_size > 500
    assert "nuxel-rollback-p90-" in dep.read_text()
    assert "nuxel-rollback-p90-" in rb.read_text()


def test_systemd_report_has_real_phases_and_shutdown_or_limitation():
    text = (ROOT / "SYSTEMD-GRAPH.md").read_text(errors="replace")
    assert "| kernel |" in text and "| userspace |" in text
    assert "**total**" in text
    assert ("Status: **CAPTURED**" in text) or ("**NOT CAPTURED**" in text)
    meta = json.loads((ROOT / "diagnostics/systemd/collector-metadata.json").read_text())
    assert meta["boot"] == "current"
    assert meta["shutdown_status"] in ("CAPTURED", "NOT_CAPTURED")


def test_gtp_plus_discovery_is_documented_not_invented():
    # The live registry did not contain a GTP+/GPT+ app on 2026-11-08.
    # The launcher must not hardcode a guessed id.
    blob = "\n".join(read(p) for p in (
        "services/nuxel-bridge/src/api.py",
        "pwa/nuxel-home/js/apps.js",
    ))
    assert "GTP+" not in blob and "GPT+" not in blob

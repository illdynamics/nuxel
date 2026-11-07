#!/usr/bin/env python3
"""PWNAGE-82000 source and store contracts."""
from __future__ import annotations

import importlib.util
import os
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(errors="replace")


def load_store():
    path = ROOT / "services/nuxel-bridge/src/pwa_store.py"
    spec = importlib.util.spec_from_file_location("p82000_pwa_store", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_assets_layout_and_install_source():
    lib = ROOT / "assets/nuxel-sounds"
    assert lib.is_dir()
    for name in ("nuxel-pow.mp3", "nuxel-alarm.mp3", "nuxel-boot-audio.mp3"):
        assert (lib / name).is_file(), name
    assert not (ROOT / "assets/nuxel-pow.mp3").exists()
    install = read("services/nuxel-sound/install-sound-library.sh")
    assert "assets/nuxel-sounds" in install and "nuxel-sounds/library" not in install
    assert "for src in \"$SRC\"/*" in install
    assert "preserved existing" in install
    assert "[Mm][Pp]3" in install


def test_sound_manager_prewarm_backoff_and_latency():
    src = read("services/nuxel-sound/nuxel-soundd.py")
    assert "def prewarm" in src
    assert "_start_backoff" in src and "_last_write_restart" in src
    assert "last_cue_latency_ms" in src
    assert 'action") == "volume" and self.active' in src
    assert "prewarm_state" in src
    assert "fcntl.F_SETPIPE_SZ" in src and "os.write(fd, view)" in src
    assert "No sleep here" in src and "STREAM_LATENCY" in src
    assert "probe_cache" in src and "ThreadPoolExecutor" in src


def test_flatpak_transaction_states_and_cancel():
    src = read("services/nuxel-bridge/src/flatpak_provider.py")
    for state in ("idle", "queued", "resolving", "downloading", "installing",
                  "verifying", "completed", "removing", "removed", "failed", "cancelled"):
        assert '"%s"' % state in src or "'%s'" % state in src, state
    assert "def cancel(" in src and "systemctl" in src
    assert "verified_installed" in src
    assert "postcondition failed" in src


def test_notes_store_under_home(tmp_path):
    os.environ["NUXEL_APP_DATA_DIR"] = str(tmp_path)
    store = load_store().PwaStore()
    saved = store.notes_save({"id": "note-test", "title": "  Test note  ",
                              "body": "hello", "pinned": True})
    assert saved["success"] and saved["note"]["title"] == "Test note"
    notes_dir = tmp_path / "files" / "Notes"
    assert (notes_dir / "note-test.json").is_file()
    listed = store.notes_list()
    assert listed["success"] and listed["count"] == 1
    assert listed["notes"][0]["body"] == "hello"
    renamed = store.notes_rename("note-test", "Renamed")
    assert renamed["success"]
    deleted = store.notes_delete("note-test")
    assert deleted["success"] and store.notes_list()["count"] == 0


def test_gallery_indexes_recordings(tmp_path):
    os.environ["NUXEL_APP_DATA_DIR"] = str(tmp_path)
    store = load_store().PwaStore()
    rec = tmp_path / "files" / "Gallery" / "Recordings" / "voice.wav"
    rec.parent.mkdir(parents=True)
    with wave.open(str(rec), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(48000)
        fh.writeframes(struct.pack("<480h", *([1000] * 480)))
    listing = store.storage_media_list()
    assert listing["success"]
    row = next(x for x in listing["media"] if x["name"] == "voice.wav")
    assert row["kind"] == "audio"
    wf = store.storage_waveform("/Gallery/Recordings/voice.wav", 16)
    assert wf["success"] and wf["duration"] > 0


def test_calendar_uses_shared_numeric_keyboard_only():
    html = read("pwa/nuxel-apps/calendar/index.html")
    js = read("pwa/nuxel-apps/calendar/js/calendar.js")
    assert "time-keypad" not in html and "timeKeypad" not in js
    assert 'inputmode="numeric"' in html and 'data-input-purpose="time"' in html
    assert 'data-input-purpose="date"' in html
    assert "timeZone" in js and "normaliseDate" in js
    assert "window.NuxelBack" in js


def test_doom_twin_dpad_contract():
    html = read("pwa/nuxel-apps/doom/index.html")
    css = read("pwa/nuxel-apps/doom/css/doom.css")
    js = read("pwa/nuxel-apps/doom/js/doom.js")
    # PWNAGE-84000: two circular analog thumbsticks (not a four-button D-pad).
    for ident in ("move-stick", "aim-stick", "fire-left", "fire-right", "look-map"):
        assert 'id="%s"' % ident in html
    for stale in ("joy-zone", "look-zone", "look-left", "look-right", "look-menu",
                  "walk-pad", "aim-pad", "btn-fire", "btn-use", "btn-next", "btn-prev",
                  "btn-run", "btn-pause"):
        assert 'id="%s"' % stale not in html, stale
    assert html.count('class="thumbstick"') == 2
    assert html.count('class="fire-button"') == 2
    assert "--pad-size" in css and ".twin-side" in css and ".thumbstick" in css
    assert "fireHoldCount" in js and "bindHold('fire-left', fireDown, fireUp)" in js
    assert "bindHold('fire-right', fireDown, fireUp)" in js
    assert "tapKey('KeyM', 77" in js
    assert "key_lookup 73" in js
    assert "key_map_toggle 77" in js


def test_devmgmt_states_and_tabs():
    js = read("pwa/nuxel-apps/devmgmt/js/devmgmt.js")
    css = read("pwa/nuxel-apps/devmgmt/css/devmgmt.css")
    for state in ("FULL", "PARTIAL", "UNAVAILABLE", "DEGRADED", "NOT TESTED"):
        assert state in js
    assert "VGEM" in js and "GBM import" in js and "WebKit DMA-BUF transport" in js
    assert "flex-wrap:nowrap" in css and "min-width:max-content" in css


def test_home_widgets_context_menu_dock_and_vram_setting():
    widgets = read("pwa/nuxel-home/js/widgets.js")
    settings = read("pwa/nuxel-home/js/home-settings.js")
    launcher = read("pwa/nuxel-home/js/launcher.js")
    monitor = read("pwa/nuxel-home/js/system-monitor.js")
    assert "registry: registry" in widgets
    for widget in ("notes:", "clock:", "calendar:"):
        assert widget in widgets
    assert "openWidgetPicker" in settings and "openContextMenu" in settings
    assert "Home Settings" in settings and "Widgets" in settings
    assert "_dockSignature" in launcher and "node.__nuxelIcon" in launcher
    assert "edge-dwell-left" in launcher and "}, 1000)" in launcher
    assert "gpuMemoryDisplay" in monitor and "amount-percent" in monitor
    assert "duration" not in monitor  # no fabricated VRAM budget


def test_cookie_adapter_is_private_and_cleaned():
    src = read("services/nuxel-bridge/src/api.py")
    assert "_nuxel_cookie_db" in src and "_nuxel_export_cookies" in src
    assert "0o600" in src and "--cookies" in src
    assert "os.unlink(cookie_file)" in src
    assert "cookies-from-browser" in src
    assert "Early returns after that point used to leak" in src
    assert 'job.pop("cookie_file", None)' in src


def test_notes_convert_actions_present():
    js = read("pwa/nuxel-apps/notes/js/notes.js")
    html = read("pwa/nuxel-apps/notes/index.html")
    assert "convertToCalendar" in js and "convertToAlarm" in js
    assert "data-note-action=\"calendar\"" in html
    assert "~/Notes" in js or "notes', 'save'" in js


def test_build_stages_sound_stack_and_current_button_manager():
    build = read("images/s10plus/build-phone-rootfs-inside-fedora.sh")
    unit = read("services/nuxel-sound/nuxel-soundd.service")
    for target in ("nuxel-soundd.py", "nuxel-clockd.py",
                   "services/nuxel-sound/nuxel-soundctl.c",
                   "install-sound-library.sh"):
        assert target in build, target
    assert "tools/s10plus/a45/nuxel-button-manager.c" in build
    assert "tools/s10plus/a34/nuxel-button-manager.c" not in build
    assert "ExecStartPre=/usr/libexec/nuxel/install-sound-library" in unit


def test_lock_suspends_active_app_and_doom_pauses():
    app = read("pwa/nuxel-home/js/app.js")
    doom = read("pwa/nuxel-apps/doom/js/doom.js")
    assert "_notifyAppFrame('nuxel:suspend'" in app
    lock_body = app[app.index('    _lock(reason) {'):app.index('    _unlock(reason) {')]
    assert "_backgroundForegroundApp()" in lock_body
    assert "event.data.type === 'nuxel:suspend'" in doom
    assert "pauseEngine();" in doom[doom.index("event.data.type === 'nuxel:suspend'"):]


def test_vesktop_uses_visible_software_compositing_fallback():
    api = read("services/nuxel-bridge/src/api.py")
    marker = 'target_id == "dev.vencord.Vesktop"'
    assert marker in api
    block = api[api.index(marker):api.index('if as_user:', api.index(marker))]
    assert '"--disable-gpu"' in block
    assert 'does NOT relax the Flatpak sandbox' in block

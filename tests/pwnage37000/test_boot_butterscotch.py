"""PWNAGE-37000 boot-latency and preload-overlay regressions.

These guard the measured S10+ cold-boot fixes:
  * the ABOX firmware reload must not block multi-user.target,
  * nuxel-wayland gets a fast, deterministic stop so the ABOX reload can restart
    it without the ~46 s final-sigterm stall,
  * the ABOX resume write is bounded like the suspend write,
  * the preload controller republishes a terminal status when it hits the
    one-shot marker, and the PWA cover backs off instead of polling 100 ms
    forever on a missing status file.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_abox_unit_does_not_want_multi_user():
    unit = _read(ROOT / "services" / "nuxel-s10" / "systemd" / "nuxel-abox-firmware-reload.service")
    assert "WantedBy=nuxel-wayland.service" in unit
    assert "WantedBy=multi-user.target" not in unit


def test_wayland_fast_stop_drop_in():
    dropin = _read(ROOT / "services" / "nuxel-s10" / "systemd" / "nuxel-wayland.service.d" / "30-fast-stop.conf")
    assert "TimeoutStopSec=8" in dropin
    assert "SendSIGKILL=yes" in dropin
    assert "KillMode=control-group" in dropin


def test_abox_resume_write_is_bounded():
    script = _read(ROOT / "services" / "nuxel-s10" / "bin" / "nuxel-abox-firmware-reload.sh")
    assert "timeout -k 1 5 sh -c 'printf on > \"$1\"'" in script


def test_preload_already_ran_publishes_terminal_status():
    controller = _read(ROOT / "services" / "nuxel-preload-cinema" / "nuxel-preload-cinema")
    assert 'mark_overlay("done", reason="already-ran")' in controller


def test_preload_cover_backs_off():
    app = _read(ROOT / "pwa" / "nuxel-home" / "js" / "app.js")
    assert "backoffMs" in app
    assert "Math.min(1000, Math.max(100, backoffMs * 2))" in app


def test_audio_route_does_not_block_multi_user():
    unit = _read(ROOT / "services" / "nuxel-s10" / "systemd" / "nuxel-audio-route.service")
    assert "WantedBy=nuxel-wayland.service" in unit
    assert "WantedBy=multi-user.target" not in unit

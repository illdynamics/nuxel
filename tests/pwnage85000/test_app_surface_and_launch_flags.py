"""Regression tests for generic Flatpak app responsiveness fixes.

Covers the two shared root causes on the live S10+:

* launcher ids (reverse-DNS) differ from the Wayland app_id the client publishes
  (Caprine, ferdium, teams-for-linux, ...), so focus/close silently did nothing;
* Electron and QtWebEngine apps need Wayland + software + inner-sandbox flags
  that were previously applied only to Legcord/Vesktop/Signal by name.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "nuxel-bridge" / "src"))
import app_surface  # noqa: E402
import flatpak_provider as fp  # noqa: E402


LISTING = """WINDOWS=7
WIN title=Nuxel app_id=nuxel-pwa-host max=1 min=0 act=0 fs=0
WIN title=Signal app_id=org.signal.Signal max=1 min=0 act=0 fs=0
WIN title=Caprine app_id=Caprine max=1 min=0 act=0 fs=0
WIN title=Ferdium app_id=ferdium max=1 min=0 act=0 fs=0
WIN title=Telegram app_id=org.telegram.desktop max=1 min=0 act=0 fs=0
WIN title=ZapZap app_id=com.rtosta.zapzap max=1 min=0 act=0 fs=0
WIN title=Sign in app_id=com.github.IsmaelMartinez.teams_for_linux max=1 min=0 act=0 fs=0
"""


def test_surface_resolution_covers_short_product_ids():
    assert app_surface.resolve_from_listing(LISTING, "com.sindresorhus.Caprine") == "Caprine"
    assert app_surface.resolve_from_listing(LISTING, "org.ferdium.Ferdium") == "ferdium"
    assert app_surface.resolve_from_listing(LISTING, "com.rtosta.zapzap") == "com.rtosta.zapzap"
    assert app_surface.resolve_from_listing(
        LISTING, "com.github.IsmaelMartinez.teams_for_linux"
    ) == "com.github.IsmaelMartinez.teams_for_linux"
    assert app_surface.resolve_from_listing(LISTING, "org.signal.Signal") == "org.signal.Signal"


def test_surface_resolution_does_not_pick_home():
    assert app_surface.resolve_from_listing(LISTING, "org.example.Missing") is None
    assert app_surface.surface_matches("nuxel-software", "nuxel-pwa-host") is False
    assert app_surface.surface_matches("org.gnome.Software", "nuxel-software") is True


def test_qtwebengine_detection_uses_metadata(monkeypatch):
    p = fp.FlatpakProvider()
    monkeypatch.setattr(
        p, "_metadata",
        lambda aid: "[Environment]\nQTWEBENGINEPROCESS_PATH=/app/bin/QtWebEngineProcess\n",
    )
    assert p.is_qtwebengine("org.example.QtApp") is True
    monkeypatch.setattr(p, "_metadata", lambda aid: "[Application]\ncommand=gtk-app\n")
    assert p.is_qtwebengine("org.example.GtkApp") is False


def _fake_provider(monkeypatch, electron=False, qtwebengine=False):
    p = fp.FlatpakProvider()
    p.is_installed = lambda aid: True  # type: ignore[assignment]
    monkeypatch.setattr(p, "is_electron", lambda aid: electron)
    monkeypatch.setattr(p, "is_qtwebengine", lambda aid: qtwebengine)
    return p


def test_electron_launch_flags_are_generic(monkeypatch):
    p = _fake_provider(monkeypatch, electron=True)
    argv = p.launch_argv("com.sindresorhus.Caprine")
    assert argv is not None
    app_index = argv.index("com.sindresorhus.Caprine")
    assert "--env=ELECTRON_OZONE_PLATFORM_HINT=wayland" in argv
    assert "--env=ZYPAK_ZYGOTE_STRATEGY_SPAWN=0" in argv
    for flag in (
        "--ozone-platform=wayland",
        "--enable-features=UseOzonePlatform,WebRTCPipeWireCapturer",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ):
        assert flag in argv
        assert argv.index(flag) > app_index, "Chromium switches must follow the app id"


def test_qtwebengine_launch_env_is_generic(monkeypatch):
    p = _fake_provider(monkeypatch, electron=False, qtwebengine=True)
    argv = p.launch_argv("com.rtosta.zapzap")
    assert argv is not None
    assert "--env=QTWEBENGINE_DISABLE_SANDBOX=1" in argv
    assert any(a.startswith("--env=QTWEBENGINE_CHROMIUM_FLAGS=") for a in argv)
    assert "--disable-gpu" not in argv  # flags are carried inside the env value
    assert argv[-1] == "com.rtosta.zapzap"


def test_non_chromium_app_does_not_inherit_chromium_flags(monkeypatch):
    p = _fake_provider(monkeypatch, electron=False, qtwebengine=False)
    argv = p.launch_argv("org.gnome.TextEditor")
    assert argv is not None
    assert argv[-1] == "org.gnome.TextEditor"
    assert "--disable-gpu" not in argv
    assert "--no-sandbox" not in argv

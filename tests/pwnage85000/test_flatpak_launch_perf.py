"""PWNAGE-85000 Flatpak launch-path regression tests.

These tests pin the two root causes found on the live S10+:

  * an installed-app inventory scan on every launch (including a user-scope
    ``flatpak list`` wrapped in a transient unit), and
  * transient units that linger in ``stop-sigterm`` for the default 15 s on
    this vendor kernel even when their cgroup is empty.

They also pin the conservative per-app renderer policy so a future blanket
``GSK_RENDERER``/llvmpipe change cannot silently return.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "nuxel-bridge" / "src"))
import flatpak_provider as fp  # noqa: E402


APP = "org.gnome.TextEditor"


def _provider(monkeypatch, apps=None, present=True):
    fp.FlatpakProvider._installed_app_present = staticmethod(lambda aid: present)
    p = fp.FlatpakProvider()
    calls = {"system": 0, "user": 0}

    def fake_scope(scope):
        calls[scope] += 1
        rows = apps if apps is not None else [
            {"id": APP, "name": "Text Editor", "scope": scope}
        ]
        return {"success": True, "scope": scope, "apps": rows}

    monkeypatch.setattr(p, "_installed_scope", fake_scope)
    return p, calls


def test_launch_uses_installed_cache_not_full_scan(monkeypatch):
    apps = [{"id": APP, "name": "Text Editor", "scope": "system"}]
    p, calls = _provider(monkeypatch, apps)
    first = p.launch_argv(APP)
    second = p.launch_argv(APP)
    assert first == second
    assert calls == {"system": 1, "user": 1}, "launch re-ran the inventory"


def test_transaction_invalidates_installed_cache(monkeypatch):
    p, calls = _provider(monkeypatch)
    p.list_installed()
    assert calls == {"system": 1, "user": 1}
    p.invalidate_installed()
    p.list_installed()
    assert calls == {"system": 2, "user": 2}


def test_removed_app_is_not_launchable_from_warm_cache(monkeypatch):
    p, calls = _provider(monkeypatch)
    assert p.is_installed(APP) is True
    fp.FlatpakProvider._installed_app_present = staticmethod(lambda aid: False)
    assert p.is_installed(APP) is False
    assert calls["system"] >= 2, "missing deployment must force a fresh scan"


def test_unknown_app_is_rejected_without_launch_argv(monkeypatch):
    p, _calls = _provider(monkeypatch, apps=[])
    assert p.launch_argv("../../bin/sh") is None
    assert p.launch_argv("not.installed.App") is None


def test_transient_units_have_bounded_stop_timeout():
    for argv in (fp._user_argv(["/bin/true"]), fp._system_job_argv(["/bin/true"])):
        assert "--property=TimeoutStopSec=1s" in argv
        assert argv[0] == "/usr/bin/systemd-run"


def test_base_env_does_not_force_software_renderer():
    env = fp._base_env(scope="user", user_bus=True)
    assert "GSK_RENDERER" not in env
    assert "LIBGL_ALWAYS_SOFTWARE" not in env
    assert env["XDG_RUNTIME_DIR"] == "/run/user/1000"


def test_renderer_policy_is_explicit_and_conservative():
    fallback = fp.renderer_policy("org.example.Unknown")
    assert fallback["mode"] == "software-fallback"
    assert "LIBGL_ALWAYS_SOFTWARE=1" in fallback["env"]
    assert "GSK_RENDERER=cairo" in fallback["env"]

    auto = fp.renderer_policy(APP)
    assert auto["mode"] == "auto"
    assert auto["env"] == [], "auto must not inject a renderer override"

    assert fp.renderer_policy("app.legcord.Legcord")["mode"] == "software-fallback"
    assert fp.renderer_policy("dev.vencord.Vesktop")["mode"] == "software-fallback"


def test_launch_argv_uses_per_app_policy(monkeypatch):
    apps = [{"id": APP, "name": "Text Editor", "scope": "system"}]
    p, _calls = _provider(monkeypatch, apps)
    argv = p.launch_argv(APP)
    assert "--env=GSK_RENDERER=cairo" not in argv
    assert "--env=GDK_BACKEND=wayland" in argv
    assert argv[-1] == APP

    firefox = p.launch_argv("org.mozilla.firefox")
    assert p.is_installed("org.mozilla.firefox") is False  # not in fake inventory


def test_launch_reports_policy_without_extra_inventory(monkeypatch):
    apps = [{"id": APP, "name": "Text Editor", "scope": "system"}]
    p, calls = _provider(monkeypatch, apps)
    out = p.handle("launch", {"app_id": APP})
    assert out["success"] is True
    assert out["renderer"]["mode"] == "auto"
    assert calls == {"system": 1, "user": 1}

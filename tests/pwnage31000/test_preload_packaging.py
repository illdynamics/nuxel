#!/usr/bin/env python3
"""Offline packaging, manifest and preservation tests for PWNAGE-31000."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "services/nuxel-preload-cinema/nuxel-preload-cinema"
UNIT = ROOT / "services/nuxel-preload-cinema/nuxel-preload-cinema.service"
CONFIG = ROOT / "configs/nuxel/boot/preload-cinema.json"
MANIFEST = ROOT / "tools/beta/live/nuxel-31000-preload-cinema-manifest.json"
VERIFY = ROOT / "tools/pwnage31000/verify-preload-cinema.py"
ASSET = ROOT / "assets/nuxel-preloading-screen.mp4"
BOOT_ANIMATION = ROOT / "assets/nuxel-boot-animation.mp4"
BOOT_ANIMATION_SHA = "280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c"
ASSET_SHA = "b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1"
RUNTIME_ASSET = "/usr/share/nuxel/preload/nuxel-preloading-screen.mp4"
RUNTIME_PLAYER = "/usr/bin/mpv"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_controller_unit_and_config_exist():
    assert CONTROLLER.is_file() and CONTROLLER.stat().st_mode & 0o111
    assert UNIT.is_file()
    assert CONFIG.is_file()
    cfg = json.loads(CONFIG.read_text())
    assert cfg["asset"] == RUNTIME_ASSET
    assert cfg["asset_sha256"] == ASSET_SHA
    assert cfg["player"] == RUNTIME_PLAYER
    assert cfg["enabled"] is True
    assert cfg["audio"] == "never"
    assert cfg["require_boot_os"] is True
    assert cfg["start_timeout_ms"] >= 20000
    assert 0 < cfg["max_display_ms"] <= cfg["hard_timeout_ms"]
    # Worst-case overlay release stays inside nuxel-fallback's 60 s wait.
    assert cfg["start_timeout_ms"] + cfg["hard_timeout_ms"] < 60000


def test_unit_never_owns_framebuffer_and_is_bounded():
    text = UNIT.read_text()
    assert "After=nuxel-wayland.service nuxel-wl-fb.service" in text
    assert "Before=nuxel-fallback.service" in text
    assert "Wants=nuxel-wayland.service nuxel-wl-fb.service" in text
    assert "ReadWritePaths=-/run/nuxel -/var/log/nuxel -/var/lib/nuxel -/usr/share/nuxel/nuxel-home" in text
    assert "Restart=no" in text
    assert "StartLimitBurst=1" in text
    assert "KillMode=control-group" in text
    assert "ExecStart=/usr/lib/nuxel/nuxel-preload-cinema" in text
    executable_lines = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
    assert "/dev/fb0" not in executable_lines


def test_manifest_validates_and_plans_with_asset_hash():
    sys.path.insert(0, str(ROOT / "tools/beta/live"))
    import nuxel_live as nl
    man = json.loads(MANIFEST.read_text())
    assert nl.validate_manifest(man, str(ROOT)) == []
    plan = nl.build_deploy_plan(man, str(ROOT))
    assert plan["violations"] == []
    targets = {s["target"]: s["source"] for s in plan["steps"]}
    assert targets["/usr/lib/nuxel/nuxel-preload-cinema"] == \
        "services/nuxel-preload-cinema/nuxel-preload-cinema"
    assert targets["/etc/nuxel/boot/preload-cinema.json"] == \
        "configs/nuxel/boot/preload-cinema.json"
    assert targets["/etc/systemd/system/nuxel-preload-cinema.service"] == \
        "services/nuxel-preload-cinema/nuxel-preload-cinema.service"
    assert targets[RUNTIME_ASSET] == "assets/nuxel-preloading-screen.mp4"
    asset_step = next(s for s in plan["steps"] if s["source"] == "assets/nuxel-preloading-screen.mp4")
    assert asset_step["source_sha256"] == ASSET_SHA
    assert asset_step["mode"] == "0644"
    # A boot asset must not restart the live compositor during deployment.
    assert plan["activation_plan"]["daemon_reload"] is True
    assert plan["activation_plan"]["restarts"] == []


def test_manifest_packages_the_supplied_asset_not_a_placeholder():
    man = json.loads(MANIFEST.read_text())
    assert man.get("non_deployable") == []
    files = [f for g in man["groups"] for f in g.get("files", [])]
    entry = next(f for f in files if f["source"] == "assets/nuxel-preloading-screen.mp4")
    assert entry["target"] == RUNTIME_ASSET
    assert entry["mode"] == "0644"
    assert entry["sha256"] == ASSET_SHA
    assert ASSET_SHA in man["groups"][0]["health_check"]
    assert RUNTIME_PLAYER in man["groups"][0]["health_check"]


def test_verify_tool_passes_with_supplied_asset():
    out = subprocess.run([sys.executable, str(VERIFY)], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "VERDICT PASS" in out.stdout
    assert "checks=" in out.stdout
    assert "FAIL " not in out.stdout


def test_asset_metadata_matches_the_timing_and_audio_policy():
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader("npc_test", str(CONTROLLER))
    spec = importlib.util.spec_from_loader("npc_test", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["npc_test"] = module
    loader.exec_module(module)
    assert abs((module.mp4_duration_seconds(ASSET) or 0) - 6.016) < 0.05
    assert sha256(ASSET) == ASSET_SHA
    assert ASSET.stat().st_size == 7_630_092
    # The clip does contain AAC, but the controller's command line always
    # disables audio.  This asserts the policy, not that the track is missing.
    text = CONTROLLER.read_text()
    assert "--no-audio" in text and "--mute=yes" in text


def test_existing_boot_animation_and_warning_assets_are_preserved():
    assert BOOT_ANIMATION.is_file()
    assert sha256(BOOT_ANIMATION) == BOOT_ANIMATION_SHA
    assert (ROOT / "assets/nuxel-boot-screen-warn.jpg").is_file()
    init = (ROOT / "boot/initramfs/init.sh").read_text()
    for marker in ("nuxel-boot-splash.raw", "nuxel-boot-animation.mp4",
                   "WARNING", "nuxel_start_animation", "switch_root"):
        assert marker in init
    # The new feature is a rootfs userspace service; it must not edit the
    # initramfs, boot partition or warning-screen sequence.
    assert "nuxel-preload-cinema" not in init


def test_image_builders_package_controller_asset_and_player():
    phone = (ROOT / "images/s10plus/build-phone-rootfs-inside-fedora.sh").read_text()
    assert "nuxel-preload-cinema" in phone
    assert "assets/nuxel-preloading-screen.mp4" in phone
    assert RUNTIME_ASSET in phone
    assert "multi-user.target.wants/nuxel-preload-cinema.service" in phone
    assert "nuxel-wayland.service" in phone
    assert "asset_sha256" in phone
    assert " mpv " in phone or "\n    pipewire wireplumber alsa-lib mpg123 mpv" in phone
    assert "test -x \"$STAGE/usr/bin/mpv\"" in phone

    vm = (ROOT / "images/mkrootfs.sh").read_text()
    assert "nuxel-preload-cinema" in vm
    assert "nuxel-preloading-screen.mp4" in vm
    assert "asset_sha256" in vm


def test_phone_rootfs_verifier_tracks_runtime_files_and_player():
    text = (ROOT / "tools/s10plus/verify-fedora-phone-rootfs.py").read_text()
    assert "/usr/lib/nuxel/nuxel-preload-cinema" in text
    assert "/etc/nuxel/boot/preload-cinema.json" in text
    assert "/etc/systemd/system/nuxel-preload-cinema.service" in text
    assert "services/nuxel-preload-cinema/nuxel-preload-cinema" in text
    assert RUNTIME_ASSET in text
    assert "'/usr/bin/mpv'" in text


def test_image_package_manifest_records_mpv():
    doc = json.loads((ROOT / "images/s10plus/packages-manifest.json").read_text())
    names = [p["name"] for g in doc["groups"] for p in g["packages"]]
    assert "mpv" in names
    assert doc["verdict"] == "resolved"
    assert doc["resolved_count"] == sum(len(g["packages"]) for g in doc["groups"])


def test_release_test_registry_runs_this_suite_without_partial_asset_mode():
    registry = (ROOT / "tools/beta/run-all-tests.sh").read_text()
    assert "U-pwnage31000-preload-cinema" in registry
    assert "tests/pwnage31000" in registry
    assert "verify-preload-cinema.py --allow-missing" not in registry


def test_preload_asset_is_not_fabricated_or_substituted():
    assert ASSET.is_file()
    assert sha256(ASSET) == ASSET_SHA
    assert sha256(ASSET) != BOOT_ANIMATION_SHA, \
        "assets/nuxel-preloading-screen.mp4 must be the supplied asset, not a renamed boot animation"

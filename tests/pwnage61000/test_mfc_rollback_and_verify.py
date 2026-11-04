import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_rollback_removes_only_mfc_firmware(tmp_path):
    root = tmp_path / "rootfs"
    (root / "lib/firmware").mkdir(parents=True)
    (root / "lib/firmware/mfc_fw.bin").write_bytes(b"mfc")
    (root / "lib/firmware/AP_AUDIO_SLSI.bin").write_bytes(b"audio")
    p = subprocess.run(["bash", str(ROOT / "tools/s10plus/a61/rollback-pwnage61000.sh"),
                        "--rootfs", str(root), "--firmware"], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert not (root / "lib/firmware/mfc_fw.bin").exists()
    assert (root / "lib/firmware/AP_AUDIO_SLSI.bin").exists()


def test_rollback_dry_run_changes_nothing(tmp_path):
    root = tmp_path / "rootfs"
    (root / "lib/firmware").mkdir(parents=True)
    (root / "lib/firmware/mfc_fw.bin").write_bytes(b"mfc")
    p = subprocess.run(["bash", str(ROOT / "tools/s10plus/a61/rollback-pwnage61000.sh"),
                        "--rootfs", str(root), "--all", "--dry-run"], capture_output=True, text=True)
    assert p.returncode == 0
    assert (root / "lib/firmware/mfc_fw.bin").exists()


def test_image_verify_software_profile(tmp_path):
    root = tmp_path / "rootfs"
    (root / "usr/lib/nuxel").mkdir(parents=True)
    (root / "usr/bin").mkdir(parents=True)
    (root / "usr/bin/mpv").write_text("")
    guard = root / "usr/lib/nuxel/nuxel-gstreamer-guard.sh"
    guard.write_text("#!/bin/sh\n")
    diag = root / "usr/lib/nuxel/nuxel-mfc-diag"
    diag.write_text("#!/usr/bin/env python3\n# Default mode is INVENTORY and it never opens /dev/video*.\n")
    diag.chmod(0o755)
    (root / "usr/lib64/gstreamer-1.0").mkdir(parents=True)
    for p in ("libgstvideo4linux2.so", "libgstv4l2codecs.so", "libgstkms.so", "libgstopengl.so"):
        (root / "usr/lib64/gstreamer-1.0" / (p + ".nuxel-disabled")).write_text("")
    wp = root / "etc/wireplumber/wireplumber.conf.d"
    wp.mkdir(parents=True)
    (wp / "99-nuxel-no-v4l2.conf").write_text(
        "wireplumber.profiles = { main = { hardware.audio = required\n"
        "hardware.bluetooth = required\nhardware.video-capture = disabled } }\n")
    (root / "usr/lib/nuxel/nuxel-preload-cinema").write_text("mpv --hwdec=no\n")
    p = subprocess.run(["bash", str(ROOT / "tools/s10plus/a61/nuxel-mfc-image-verify.sh"),
                        "--rootfs", str(root), "--profile", "software"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr


def test_image_verify_mfc_profile_fails_without_firmware(tmp_path):
    root = tmp_path / "rootfs"
    (root / "usr/lib/nuxel").mkdir(parents=True)
    (root / "usr/bin").mkdir(parents=True)
    (root / "usr/bin/mpv").write_text("")
    (root / "usr/lib/nuxel/nuxel-gstreamer-guard.sh").write_text("")
    (root / "usr/lib/nuxel/nuxel-mfc-diag").write_text("# Default mode is INVENTORY\n")
    (root / "usr/lib/nuxel/nuxel-mfc-diag").chmod(0o755)
    (root / "usr/lib/nuxel/nuxel-mfc-decode").write_text("")
    (root / "usr/lib/nuxel/nuxel-mfc-decode").chmod(0o755)
    (root / "usr/lib64/gstreamer-1.0").mkdir(parents=True)
    for p in ("libgstvideo4linux2.so", "libgstv4l2codecs.so", "libgstkms.so", "libgstopengl.so"):
        (root / "usr/lib64/gstreamer-1.0" / (p + ".nuxel-disabled")).write_text("")
    wp = root / "etc/wireplumber/wireplumber.conf.d"
    wp.mkdir(parents=True)
    (wp / "99-nuxel-no-v4l2.conf").write_text(
        "wireplumber.profiles = { main = { hardware.audio = required\n"
        "hardware.bluetooth = required\nhardware.video-capture = disabled } }\n")
    p = subprocess.run(["bash", str(ROOT / "tools/s10plus/a61/nuxel-mfc-image-verify.sh"),
                        "--rootfs", str(root), "--profile", "mfc"],
                       capture_output=True, text=True)
    assert p.returncode == 1
    assert "mfc_fw.bin missing" in p.stdout

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_guard_still_disables_all_four_plugins():
    text = (ROOT / "tools/s10plus/a29/nuxel-gstreamer-guard.sh").read_text()
    for p in ("libgstvideo4linux2.so", "libgstv4l2codecs.so",
              "libgstkms.so", "libgstopengl.so"):
        assert p in text
    assert "nuxel-disabled" in text
    assert "registry." in text


def test_both_sessions_invoke_guard():
    for rel in ("tools/s10plus/a29/nuxel-session.sh", "tools/s10plus/a45/nuxel-session.sh"):
        text = (ROOT / rel).read_text()
        assert "/usr/lib/nuxel/nuxel-gstreamer-guard.sh" in text


def test_wireplumber_keeps_audio_bt_and_disables_capture():
    text = (ROOT / "configs/s10plus/wireplumber/99-nuxel-no-v4l2.conf").read_text()
    assert "hardware.video-capture = disabled" in text
    assert "hardware.audio = required" in text
    assert "hardware.bluetooth = required" in text


def test_preload_stays_software_safe():
    text = (ROOT / "services/nuxel-preload-cinema/nuxel-preload-cinema").read_text()
    assert "--hwdec=no" in text
    assert "v4l2" not in text.lower()
    assert "mfc" not in text.lower()


def test_no_boot_or_install_mfc_hardware_test():
    # Only user-invoked helper paths may mention the hardware-open flag.
    offenders = []
    for base in ("services", "configs", "boot"):
        for p in (ROOT / base).rglob("*"):
            if not p.is_file():
                continue
            try:
                t = p.read_text(errors="replace")
            except OSError:
                continue
            if "--allow-hardware-open" in t or "nuxel-mfc-decode" in t:
                offenders.append(str(p.relative_to(ROOT)))
    assert offenders == []


def test_rootfs_build_installs_diag_and_keeps_guard():
    text = (ROOT / "images/s10plus/build-phone-rootfs-inside-fedora.sh").read_text()
    assert "nuxel-mfc-diag" in text
    assert "nuxel-mfc-decode" in text
    assert "99-nuxel-no-v4l2.conf" in text
    assert "nuxel-gstreamer-guard.sh" in text

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel):
    return (ROOT / rel).read_text()


def test_mic_pipewire_source_is_real_capture_not_monitor():
    conf = read("configs/s10plus/pipewire/51-nuxel-s10-mic.conf")
    assert "api.alsa.pcm.source" in conf
    assert 'api.alsa.path    = "hw:0,13"' in conf
    assert 'media.class      = "Audio/Source"' in conf
    assert "alsa_input.hw_0_13" in conf


def test_mic_route_uses_vendor_controls_and_waits_for_abox():
    script = read("services/nuxel-s10/bin/nuxel-mic-route.sh")
    for needle in (
        "ABOX NSRC0", "ABOX SIFM0", "ABOX WDMA1_EN",
        "LHPF1 Input 1", "ASRC1IN1L Input 1", "ISRC1INT1 Input 1",
        "AIF1TX1 Input 1", "AIF1TX2 Input 1", "DMIC1 Switch",
        "--wait", "nuxel-audio-route.state",
    ):
        assert needle in script
    unit = read("services/nuxel-s10/systemd/nuxel-mic-route.service")
    assert "--wait 180" in unit
    assert "Restart=on-failure" in unit
    assert "nuxel-audio-route.service" in unit


def test_rootfs_builder_stages_mic_and_bwrap_shim():
    builder = read("images/s10plus/build-phone-rootfs-inside-fedora.sh")
    assert "51-nuxel-s10-mic.conf" in builder
    assert "nuxel-mic-route.sh" in builder
    assert "nuxel-mic-route.service" in builder
    assert "nuxel-bwrap-compat.py" in builder
    assert "bwrap.real" in builder


def test_bwrap_shim_rewrites_fd_binds_to_real_paths():
    shim = read("tools/s10plus/nuxel-bwrap-compat.py")
    assert b"--ro-bind-fd" in shim.encode()
    assert b"--bind-fd" in shim.encode()
    assert "os.readlink" in shim
    assert "/usr/libexec/bwrap.real" in shim


def test_kernel_patches_present():
    for name in (
        "0006-sec-ts-lpm-bind.patch",
        "0007-sec-nfc-class-name.patch",
        "0008-nuxel-userns-flatpak.patch",
        "0009-nuxel-statx-mnt-id.patch",
    ):
        path = ROOT / "kernel/s10plus/patches" / name
        assert path.exists() and path.read_text().strip()
        assert (ROOT / "kernel/s10plus/patches" / (name + ".required")).exists()

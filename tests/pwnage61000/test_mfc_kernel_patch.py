import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATCH = ROOT / "kernel/s10plus/patches/0008-mfc-firmware-fail-closed.patch"
SRC = ROOT / "kernel/s10plus/.build/src"


def test_patch_and_required_sidecar_exist():
    assert PATCH.is_file()
    assert (PATCH.parent / (PATCH.name + ".required")).is_file()


def test_patch_switches_to_direct_loader_and_ip_gate():
    text = PATCH.read_text()
    assert "request_firmware_direct" in text
    assert "MFC_SUPPORTED_IP_VER" in text
    assert "-ENODEV" in text
    assert "unavailable" in text
    # No added legacy request_firmware call.
    added = [ln for ln in text.splitlines()
             if ln.startswith("+") and "request_firmware(" in ln
             and not ln.lstrip("+").lstrip().startswith("*")]
    assert added == []


def test_patch_applies_to_pinned_source():
    if not (SRC / ".git").exists():
        import pytest
        pytest.skip("pinned kernel source cache absent")
    fwd = subprocess.run(["git", "-C", str(SRC), "apply", "--check", str(PATCH)],
                         capture_output=True, text=True)
    if fwd.returncode == 0:
        return
    # A build cache may already have applied the required patch.  Accept that
    # only when the reverse check proves the exact patch is present.
    rev = subprocess.run(["git", "-C", str(SRC), "apply", "--reverse", "--check", str(PATCH)],
                         capture_output=True, text=True)
    assert rev.returncode == 0, fwd.stderr + rev.stderr


def test_mfc_config_is_required_in_both_fragments():
    for rel in ("kernel/s10plus/configs/nuxel-drm-kbase.fragment",
                "kernel/s10plus/configs/live-required.config"):
        text = (ROOT / rel).read_text()
        assert "CONFIG_VIDEO_EXYNOS_MFC=y" in text
        assert "CONFIG_VIDEOBUF2_DMA_SG=y" in text
        assert "CONFIG_EXYNOS_IOMMU=y" in text


def test_live_config_evidence_matches_required_set():
    live = ROOT / "docs/beta-finalization/live/evidence/pwnage-61000/live-config.txt"
    assert live.is_file()
    p = subprocess.run(["python3", str(ROOT / "tools/s10plus/verify-kernel-config.py"),
                        "--config", str(live), "--quiet"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr

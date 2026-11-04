import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

from conftest import make_video_node


def fake_tree(tmp_path):
    sysfs = tmp_path / "sys"
    make_video_node(sysfs, "video6", "s5p-mfc-dec0", "188d0000.mfc",
                    "s5p-mfc", "samsung,exynos-mfc", 0x1300)
    make_video_node(sysfs, "video111", "exynos-fimc-is-30c", "170e0000.fimc_is",
                    "exynos-fimc-is", "samsung,exynos5-fimc-is", None)
    cfg = tmp_path / "config"
    cfg.write_text("CONFIG_VIDEO_EXYNOS_MFC=y\nCONFIG_VIDEOBUF2_DMA_SG=y\n"
                   "CONFIG_EXYNOS_IOMMU=y\nCONFIG_V4L2_MEM2MEM_DEV=y\n")
    fwdir = tmp_path / "fw"
    fwdir.mkdir()
    return sysfs, cfg, fwdir


def test_allowlist_rejects_by_number_and_wrong_identity(diag):
    good = {"name": "s5p-mfc-dec0", "driver": "s5p-mfc",
            "compatible": "samsung,exynos-mfc", "ip_ver": "0x1300",
            "platform_device": "188d0000.mfc"}
    assert diag.classify_node(good) == "MFC_DECODER"
    for key, val in (("name", "exynos-fimc-is-30c"),
                     ("driver", "exynos-fimc-is"),
                     ("compatible", "samsung,exynos5-fimc-is"),
                     ("ip_ver", "0x1200"),
                     ("platform_device", "170e0000.fimc_is")):
        bad = dict(good)
        bad[key] = val
        assert diag.classify_node(bad) != "MFC_DECODER", key


def test_scan_is_read_only_and_finds_exact_decoder(diag, tmp_path):
    sysfs, _, _ = fake_tree(tmp_path)
    nodes = diag.scan_video_nodes(str(sysfs))
    dec, err = diag.find_decoder(nodes)
    assert dec is not None and not err
    assert dec["name"] == "s5p-mfc-dec0"
    assert not (tmp_path / "dev").exists()


def test_missing_firmware_is_blocked(diag, tmp_path):
    sysfs, cfg, fwdir = fake_tree(tmp_path)
    st = diag.build_status(sysfs_root=str(sysfs), dev_root=str(tmp_path / "dev"),
                           firmware_dirs=[str(fwdir)], config_path=str(cfg),
                           receipt_path=str(tmp_path / "none.json"), root=str(tmp_path))
    assert st["state"] == "BLOCKED_FIRMWARE_MISSING"
    assert st["safe_open_allowed"] is False
    assert st["decoder_node"].endswith("/video6")


def test_wrong_firmware_hash_is_blocked(diag, tmp_path):
    sysfs, cfg, fwdir = fake_tree(tmp_path)
    (fwdir / diag.FIRMWARE_NAME).write_bytes(b"wrong")
    st = diag.build_status(sysfs_root=str(sysfs), dev_root=str(tmp_path / "dev"),
                           firmware_dirs=[str(fwdir)], config_path=str(cfg),
                           receipt_path=str(tmp_path / "none.json"), root=str(tmp_path))
    assert st["state"] == "BLOCKED_FIRMWARE_HASH"


def test_matching_firmware_but_no_receipt_is_blocked(diag, tmp_path, monkeypatch):
    sysfs, cfg, fwdir = fake_tree(tmp_path)
    data = b"fake-but-consistent-firmware-for-unit-test"
    (fwdir / diag.FIRMWARE_NAME).write_bytes(data)
    monkeypatch.setattr(diag, "FIRMWARE_SHA256", hashlib.sha256(data).hexdigest())
    monkeypatch.setattr(diag, "FIRMWARE_SIZE", len(data))
    st = diag.build_status(sysfs_root=str(sysfs), dev_root=str(tmp_path / "dev"),
                           firmware_dirs=[str(fwdir)], config_path=str(cfg),
                           receipt_path=str(tmp_path / "none.json"), root=str(tmp_path))
    assert st["state"] == "BLOCKED_DRIVER_UNSAFE"
    assert "receipt" in st["reason"].lower()
    assert st["safe_open_allowed"] is False


def test_receipt_and_gate(diag, tmp_path):
    receipt = {
        "schema": diag.RECEIPT_SCHEMA, "owner_approved": True,
        "source_commit": diag.SOURCE_COMMIT, "device": diag.DEVICE,
        "decoder_node": "/dev/video6", "platform_device": diag.EXPECTED_PLATFORM,
        "driver": diag.EXPECTED_DRIVER, "compatible": diag.EXPECTED_COMPATIBLE,
        "ip_ver": diag.EXPECTED_IP_VER, "firmware_name": diag.FIRMWARE_NAME,
        "firmware_sha256": diag.FIRMWARE_SHA256, "kernel_patch": diag.KERNEL_PATCH,
        "kernel_patch_applied": True, "missing_firmware_test": "SOURCE_PASS",
    }
    rp = tmp_path / "receipt.json"
    rp.write_text(json.dumps(receipt))
    loaded, err = diag.load_receipt(str(rp))
    assert loaded is not None and not err
    st = {"decoder_node": "/dev/video6", "safe_open_allowed": True,
          "state": "AVAILABLE_PROBE_ONLY", "reason": ""}
    _, gerr = diag.require_active_gate(st, "/dev/video111", loaded)
    assert gerr
    _, gerr = diag.require_active_gate(st, "/dev/video6", loaded)
    assert not gerr
    bad = dict(receipt, kernel_patch_applied=False)
    rp.write_text(json.dumps(bad))
    loaded, err = diag.load_receipt(str(rp))
    assert loaded is None and "NOT applied" in err


def test_inventory_cli_never_opens_and_default_is_inventory(tmp_path):
    # No args: default inventory, never an active open.
    p = subprocess.run([sys.executable,
                        str(pathlib.Path(__file__).resolve().parents[2] / "tools/s10plus/a61/nuxel-mfc-diag")],
                       capture_output=True, text=True, timeout=20)
    assert p.returncode == 0
    assert "no device node opened" in p.stdout
    # Active mode without the explicit flag must refuse before any open.
    p = subprocess.run([sys.executable,
                        str(pathlib.Path(__file__).resolve().parents[2] / "tools/s10plus/a61/nuxel-mfc-diag"),
                        "--query-only", "--device", "/dev/video6"],
                       capture_output=True, text=True, timeout=20)
    assert p.returncode == 2
    assert "REFUSED" in (p.stderr + p.stdout)

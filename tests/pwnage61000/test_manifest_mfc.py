import hashlib
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "firmware/s10plus/manifest.yml"
FW_SHA = "f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f"


def video_entry():
    doc = yaml.safe_load(MANIFEST.read_text())
    entries = doc["firmware_files"]["video"]
    return [e for e in entries if e["source_path"] == "vendor/firmware/mfc_fw.bin"][0]


def test_mfc_manifest_contract():
    e = video_entry()
    assert e["dest"] == "/lib/firmware/mfc_fw.bin"
    assert e["required"] is False          # software-only images stay buildable
    assert e["checksum"] == FW_SHA
    assert e["size"] == 685832
    assert e["driver_request_name"] == "mfc_fw.bin"
    assert e["expected_ip_ver"] == "0x1300"
    assert e["source_repo"] == "Linux4/proprietary_vendor_samsung"
    assert e["source_commit"] == "05c9ef8f16e0ad5ab274e408c120dfd99fd5c628"
    assert e["source_path_full"].startswith("exynos9820-common/")
    assert "not redistributed" in e["redistribution"]


def test_fetcher_covers_exynos9820_common_mfc():
    text = (ROOT / "firmware/s10plus/fetch-vendor-blobs.sh").read_text()
    assert "exynos9820-common/proprietary/vendor/firmware/" in text
    assert "05c9ef8f16e0ad5ab274e408c120dfd99fd5c628" in text


def test_installer_has_verify_mfc_and_no_fabrication():
    text = (ROOT / "firmware/s10plus/install-firmware.sh").read_text()
    assert "--verify-mfc" in text
    assert "MFC_BLOB_HASH" in text
    assert "MFC_BLOB_SIZE" in text
    assert "MFC_BLOB_HEADER" in text
    assert "ea000077" in text
    # No padding/fake fallback path.
    assert "dd if=/dev/zero" not in text
    assert "truncate" not in text


def test_local_blob_hash_if_present():
    p = ROOT / "firmware/s10plus/blobs/vendor-firmware/mfc_fw.bin"
    if not p.is_file():
        import pytest
        pytest.skip("local blob not staged (gitignored)")
    data = p.read_bytes()
    assert len(data) == 685832
    assert hashlib.sha256(data).hexdigest() == FW_SHA
    assert data[:4] == bytes.fromhex("770000ea")


def test_mfc_test_media_manifest_is_honest():
    import json
    doc = json.loads((ROOT / "tools/s10plus/a61/mfc-test-media.json").read_text())
    assert doc["schema"] == "nuxel.mfc.test-media/1"
    ref = doc["software_reference"]
    assert ref["codec"] == "H.264 High"
    assert ref["sha256"] == "b059f121e62b167fde8664e24c879ca443df8740d95441e7948abdbcc6cdbbf1"
    assert ref["status"] == "PRESENT_SOFTWARE_REFERENCE"
    ids = {f["id"] for f in doc["fixtures"]}
    assert {"h264-720p30", "h264-1080p30", "h264-1080p60", "hevc-main-1080p30", "4k30"} <= ids
    assert all(f["status"] == "NOT_PRESENT" for f in doc["fixtures"])
    assert all(f["sha256"] is None for f in doc["fixtures"])

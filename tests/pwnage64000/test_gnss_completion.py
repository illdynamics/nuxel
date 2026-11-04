#!/usr/bin/env python3
"""PWNAGE-64000 completion tests: canonical BCM4773 inventory + diagnostics.

These are offline/host tests.  A real satellite fix remains an owner outdoor
test; nothing here creates a coordinate, enables the GPS rail or opens a BBD
device node.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "services", "nuxel-bridge", "src"))

import gnss_inventory as gi  # noqa: E402

POLICY = os.path.join(ROOT, "configs", "nuxel", "gnss", "gnss.json")
DIAG = os.path.join(ROOT, "tools", "s10plus", "a33", "nuxel-gnss-diag.sh")
FIX = os.path.join(ROOT, "tools", "s10plus", "a33", "tests", "hw-subsystems", "fixtures")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def touch(root, rel, data=b"x"):
    p = os.path.join(root, rel.lstrip("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write(data)
    return p


def test_strict_firmware_rejects_generic_and_wrong_bcm(tmp_path):
    root = str(tmp_path)
    touch(root, "lib/firmware/gnss/bcm4773_sensorhub.patch")
    touch(root, "vendor/firmware/bcm_sensorhub_a1.patch")
    touch(root, "lib/firmware/gps.bin")
    touch(root, "lib/firmware/gnss/gnss.bin")
    touch(root, "lib/firmware/bcm47755_sensorhub.patch")
    found = gi.firmware(root)
    names = sorted(f["basename"] for f in found)
    assert names == ["bcm4773_sensorhub.patch", "bcm_sensorhub_a1.patch"]
    assert all(f["status"] == gi.PRESENT_UNVERIFIED for f in found)
    assert gi.firmware_identity_verified(found) is False


def test_verified_hash_promotes_identity_but_not_load(tmp_path):
    root = str(tmp_path)
    p = touch(root, "lib/firmware/gnss/bcm4773_sensorhub.patch", b"payload")
    import hashlib
    digest = hashlib.sha256(b"payload").hexdigest()
    found = gi.firmware(root, hashes={digest})
    assert found[0]["status"] == gi.IDENTITY_VERIFIED
    assert gi.firmware_identity_verified(found) is True
    # identity != loaded: the canonical inventory never claims a load.
    inv = gi.provider_inventory(root)
    assert inv["firmware_loaded"] is False
    assert inv["fix_supported"] is False


def test_loader_node_is_never_firmware(tmp_path):
    root = str(tmp_path)
    touch(root, "dev/bbd_patch")
    assert gi.loader_nodes(root) == [os.path.join(root, "dev/bbd_patch")]
    assert gi.firmware(root) == []
    assert gi.firmware_present(gi.firmware(root)) is False


def test_bridge_inventory_full_path_does_not_raise(tmp_path):
    root = str(tmp_path)
    touch(root, "dev/ttyBCM")
    touch(root, "dev/bbd_patch")
    touch(root, "sys/bus/spi/drivers/brcm gps spi/spi17.0/driver", b"brcm gps spi\n")
    inv = gi.bridge_inventory(root)  # must not raise UnboundLocalError
    assert inv["present"] is True
    assert inv["driver_bound"] is True
    assert inv["firmware_present"] is False
    assert "sensor-hub patch" in inv["blocker"]
    assert inv["vendor_runtime"]["complete"] is False
    assert "complete" not in inv["blocker"]
    assert len(inv["bbd_nodes"]) == len(set(inv["bbd_nodes"]))


def test_provider_inventory_has_no_fix_or_nmea_claim(tmp_path):
    inv = gi.provider_inventory(str(tmp_path))
    assert inv["protocol"] == "broadcom-bbd-lhd-rpc"
    assert inv["nmea"] is False
    assert inv["fix_supported"] is False
    assert inv["firmware_loaded"] is False
    assert "power_rail" in inv


def test_policy_artefact_is_loader_aware():
    pol = json.load(open(POLICY, encoding="utf-8"))
    assert pol["evidence_sources"]["stream"]["protocol"] == "broadcom-bbd-lhd-rpc"
    assert pol["evidence_sources"]["stream"]["sentence_hints"] == []
    arts = pol["expected_artefacts"]
    assert arts, "expected_artefacts must be populated"
    art = arts[0]
    assert art["status"] == "absent"
    assert art["kind"] == "character-device payload"
    assert art["loader_node"] == "/dev/bbd_patch"
    assert art["required_for_fix"] is True
    assert art["sha256"] is None and art["size_bytes"] is None
    assert "/system/bin/bcm_sensorhub_a1.patch" in art["expected_paths"]
    # A loader character device is not a firmware artefact path.
    assert art["loader_node"] not in art["expected_paths"]


def test_diagnostic_selftest_is_bounded_and_never_hangs():
    p = subprocess.run(["bash", DIAG, "selftest"], capture_output=True,
                       text=True, timeout=45)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "FAIL" not in p.stdout
    assert "fixtures checked" in p.stdout or "SKIP" in p.stdout


def test_diagnostic_fixture_never_prints_a_fix_or_nmea():
    fixture = os.path.join(FIX, "gnss-bcm-nofw")
    p = subprocess.run(["bash", DIAG, "--root", fixture, "status", "--json"],
                       capture_output=True, text=True, timeout=30)
    doc = json.loads([l for l in p.stdout.splitlines() if l.startswith("{")][0])
    assert doc["state"] == "BLOCKED_FIRMWARE"
    assert doc["fix_verified"] is False
    assert doc["nmea_stream"] is False
    assert "latitude" not in doc and "longitude" not in doc
    assert "ttyBCM" in doc["stages"]["device_node"]


def test_bridge_consumes_the_canonical_inventory():
    src = read(os.path.join(ROOT, "services", "nuxel-bridge", "src", "bridge.py"))
    assert "_gi.bridge_inventory(root='/')" in src
    # The old broad heuristic must not come back.
    assert "'gps', 'gnss', 'ssp'" not in src
    assert "low.startswith(('gps'" not in src


def test_deploy_and_rollback_are_userspace_only():
    dep = os.path.join(ROOT, "tools", "s10plus", "a64", "deploy-pwnage64000.sh")
    rb = os.path.join(ROOT, "tools", "s10plus", "a64", "rollback-pwnage64000.sh")
    for path in (dep, rb):
        assert os.path.isfile(path), path
        text = read(path)
        for forbidden in ("mkfs", "parted", "dd if=", "dd of=", "/dev/bbd_patch",
                          "systemctl reboot", "reboot -f", "flash-image"):
            assert forbidden not in text, (path, forbidden)
    assert "gnss.json" in read(dep) and "gnss_inventory.py" in read(dep)

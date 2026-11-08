#!/usr/bin/env python3
"""PWNAGE-91000 static contracts for boot, NFC policy and deliverables."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(errors="replace")


def test_avahi_is_off_the_network_online_critical_path():
    text = read("services/nuxel-s10/systemd/avahi-daemon.service.d/10-nuxel-boot-order.conf")
    active = [line.strip() for line in text.splitlines()
              if line.strip() and not line.lstrip().startswith("#")]
    joined = "\n".join(active)
    assert "After=NetworkManager.service wpa_supplicant.service" in joined
    assert "Wants=network-online.target" not in joined
    assert "After=network-online.target" not in joined
    assert "Restart=on-failure" in joined
    assert "RestartSec=3" in joined


def test_build_installs_avahi_dropin_and_spoof_state_dir():
    build = read("images/s10plus/build-phone-rootfs-inside-fedora.sh")
    assert "avahi-daemon.service.d/10-nuxel-boot-order.conf" in build
    assert "var/lib/nuxel/spoof" in build
    prov = read("tools/s10plus/a33/nuxel-provision-services.sh")
    assert "/var/lib/nuxel/spoof" in prov
    assert "nuxel-bridge:nuxel-bridge" in prov


def test_nfc_policy_pins_s3nrn82_firmware_and_hash():
    doc = json.loads(read("configs/nuxel/nfc/nfc.json"))
    expected = doc["evidence_sources"]["firmware_expected"]
    assert expected["path"].endswith("sec_s3nrn82_firmware.bin")
    assert expected["size"] == 151852
    assert expected["sha256"] == "d315cd8bf47d90b7537aa978cb52299b7f2a56e8748588fb980b83ee823c0bfb"
    assert doc["evidence_sources"]["service"]["socket"] == "/run/nuxel/nfc/nfc.sock"


def test_required_reports_exist():
    for name in ("SYSTEMD-GRAPH.md", "GPU-ACCEL-REPORT.md", "REPORT-CAMERA.md",
                 "REPORT-GPS.md", "REPORT-NFC.md", "REPORT-ROTATION.md",
                 "REPORT-FINGERPRINT.md", "REPORT-MOBILE-NETWORKING.md",
                 "REPORT-LEDS.md", "PWNAGE-91000-REPORT.md"):
        p = ROOT / name
        assert p.is_file() and p.stat().st_size > 1000, name

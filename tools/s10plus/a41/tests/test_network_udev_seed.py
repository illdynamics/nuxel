#!/usr/bin/env python3
"""Offline safety tests for the no-udevd Wi-Fi compatibility seed."""
from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "tools/s10plus/a41/nuxel-network-udev-seed.sh"
UNIT = ROOT / "tools/s10plus/a41/nuxel-network-udev-seed.service"


class NetworkUdevSeedTests(unittest.TestCase):
    def run_seed(self, sysnet: pathlib.Path, udev: pathlib.Path):
        env = os.environ | {
            "NUXEL_SYS_CLASS_NET": str(sysnet),
            "NUXEL_UDEV_DATA_DIR": str(udev),
        }
        return subprocess.run(["sh", str(SCRIPT)], env=env, text=True,
                              capture_output=True, check=False)

    def test_creates_only_real_wireless_interfaces(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            sysnet, udev = root / "net", root / "udev"
            wlan0 = sysnet / "wlan0"
            wlan0.mkdir(parents=True)
            (wlan0 / "ifindex").write_text("17\n")
            (wlan0 / "phy80211").touch()
            eth0 = sysnet / "eth0"
            eth0.mkdir()
            (eth0 / "ifindex").write_text("2\n")
            self.assertEqual(self.run_seed(sysnet, udev).returncode, 0)
            record = (udev / "n17").read_text()
            self.assertIn("E:ID_NET_DRIVER=wl\n", record)
            self.assertIn("E:ID_NET_NAME=wlan0\n", record)
            self.assertIn("E:NM_UNMANAGED=0\n", record)
            self.assertRegex(record, r"I:\d{10}000000\n")
            self.assertFalse((udev / "n2").exists())

    def test_preserves_an_existing_udev_record(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            sysnet, udev = root / "net", root / "udev"
            wlan1 = sysnet / "wlan1"
            wlan1.mkdir(parents=True)
            (wlan1 / "ifindex").write_text("18\n")
            (wlan1 / "phy80211").touch()
            udev.mkdir()
            existing = udev / "n18"
            existing.write_text("E:OWNER=udevd\n")
            self.assertEqual(self.run_seed(sysnet, udev).returncode, 0)
            self.assertEqual(existing.read_text(), "E:OWNER=udevd\n")

    def test_unit_is_ordered_before_networkmanager(self):
        text = UNIT.read_text()
        self.assertIn("Before=NetworkManager.service", text)
        self.assertIn("RequiredBy=NetworkManager.service", text)
        self.assertIn("ExecStart=/usr/libexec/nuxel/nuxel-network-udev-seed", text)
        # systemd-udevd is masked on this kernel, so the device unit never
        # appears; depending on it used to cost the full 50 s device timeout
        # before Wi-Fi could start.
        self.assertNotIn("Wants=sys-subsystem-net-devices-wlan0.device", text)
        self.assertNotIn("After=local-fs.target sys-subsystem-net-devices-wlan0.device", text)


if __name__ == "__main__":
    unittest.main()

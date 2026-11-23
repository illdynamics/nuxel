#!/usr/bin/env python3
"""Offline-only, synthetic and negative tests for separate-DT SSP BOOT packer."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

PACKER = Path(__file__).resolve().parents[1] / 'pack-ssp-boot.py'
spec = importlib.util.spec_from_file_location('ssp_boot_packer', PACKER)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
CAP = 110 * mod.PAGE


def raw_kernel(size=65536):
    body = bytearray(size)
    body[:4] = b'\x00\x00\x6c\x14'
    body[0x38:0x3c] = mod.ARM64_MAGIC
    struct.pack_into('<QQQ', body, 8, 0x80000, size, 0)
    return bytes(body)


def donor(size=65536, ramdisk=b'\x5d\x00\x00\x80\x00' + b'\xff'*8 + b'payload'):
    hdr = bytearray(mod.PAGE)
    hdr[:8] = mod.MAGIC
    for off, value in ((8, size), (12, 0x10008000), (16, len(ramdisk)),
                       (20, 0x11000000), (24, 0), (28, 0), (32, 0x10000100),
                       (36, mod.PAGE), (40, 1), (44, 0x18000171),
                       (1632, 0), (1644, 1648)):
        struct.pack_into('<I', hdr, off, value)
    hdr[48:64] = b'nuxel-s10plus\x00\x00\x00'
    hdr[64:64+len(b'nuxel.device=s10plus')] = b'nuxel.device=s10plus'
    payload = bytes(hdr) + raw_kernel(size)
    payload += bytes(mod.aligned(size)-size) + ramdisk
    return payload + bytes(CAP-len(payload))


class TestPack(unittest.TestCase):
    def test_exact_layout_kernel_only(self):
        d = donor(); img = raw_kernel(68865)
        got, receipt = mod.make_candidate(d, img, capacity=CAP,
                                           expect_donor_sha256=mod.sha256(d))
        a = mod.section_layout(got, CAP)
        b = mod.section_layout(d, CAP)
        self.assertEqual(got[12:mod.PAGE], d[12:mod.PAGE])
        self.assertEqual(a['ramdisk'], b['ramdisk'])
        self.assertEqual(got[mod.PAGE:mod.PAGE+len(img)], img)
        self.assertEqual(struct.unpack_from('<I', got, 8)[0], len(img))
        self.assertEqual(a['ramdisk_offset'], mod.PAGE + mod.aligned(len(img)))
        self.assertEqual(len(got), CAP)
        self.assertEqual(got[a['payload_end_aligned']:], bytes(CAP-a['payload_end_aligned']))
        self.assertEqual(receipt['appended_dtb_count'], 0)
        self.assertFalse(receipt['flash_authorized'])

    def test_no_appended_dtb_is_allowed(self):
        self.assertEqual(mod.section_layout(donor(), CAP)['payload_end_aligned'],
                         mod.PAGE + 65536 + mod.aligned(20))

    def test_added_fdt_tail_is_rejected(self):
        d = bytearray(donor())
        d[mod.PAGE + 65536 + mod.PAGE:mod.PAGE + 65536 + mod.PAGE+4] = b'\xd0\x0d\xfe\xed'
        with self.assertRaisesRegex(ValueError, 'nonzero data'):
            mod.section_layout(bytes(d), CAP)

    def test_nonzero_partition_slack_rejected(self):
        d = bytearray(donor()); d[-5] = 1
        with self.assertRaisesRegex(ValueError, 'nonzero data'):
            mod.section_layout(bytes(d), CAP)

    def test_wrong_sha256_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            mod.make_candidate(donor(), raw_kernel(), capacity=CAP,
                               expect_donor_sha256='0'*64)

    def test_wrong_header_version_and_addresses_rejected(self):
        for off, value in ((40, 0), (1644, 123), (12, 0x4), (36, 4096), (24, 19)):
            with self.subTest(off=off):
                d = bytearray(donor()); struct.pack_into('<I', d, off, value)
                with self.assertRaises(ValueError):
                    mod.section_layout(bytes(d), CAP)

    def test_nonarm64_image_rejected(self):
        bad = b'\x1f\x8b' + bytes(65534)
        with self.assertRaisesRegex(ValueError, 'raw, uncompressed'):
            mod.make_candidate(donor(), bad, capacity=CAP,
                               expect_donor_sha256=mod.sha256(donor()))

    def test_oversize_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exceed'):
            mod.make_candidate(donor(), raw_kernel(CAP), capacity=CAP,
                               expect_donor_sha256=mod.sha256(donor()))

    def test_no_output_after_failed_pack_and_cli_json(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t); d = t/'donor.img'; k = t/'Image'; o=t/'out.img'; m=t/'manifest.json'
            d.write_bytes(donor()); k.write_bytes(raw_kernel(72000))
            cmd = [sys.executable, str(PACKER), '--donor', str(d), '--kernel', str(k),
                   '--out', str(o), '--partition-bytes', str(CAP),
                   '--expect-donor-sha256', hashlib.sha256(d.read_bytes()).hexdigest(),
                   '--manifest', str(m)]
            bad = subprocess.run(cmd + ['--ramdisk-raw', str(d)],capture_output=True,text=True)
            self.assertNotEqual(bad.returncode, 0); self.assertFalse(o.exists())
            good = subprocess.run(cmd, capture_output=True,text=True)
            self.assertEqual(good.returncode,0, good.stderr)
            self.assertTrue(m.exists()); self.assertEqual(o.stat().st_size,CAP)
            self.assertEqual(json.loads(m.read_text())['candidate_sha256'],mod.sha256(o.read_bytes()))


if __name__ == '__main__':
    unittest.main()

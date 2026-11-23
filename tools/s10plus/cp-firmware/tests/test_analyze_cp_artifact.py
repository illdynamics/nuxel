#!/usr/bin/env python3
"""Offline tests for the CP artifact analyzer.

ALL fixtures are synthetic, generated in a temp dir, deleted at exit.
No real firmware is ever read or produced by this test.
Run:  python3 tools/s10plus/cp-firmware/tests/test_analyze_cp_artifact.py
"""
import hashlib
import io
import json
import os
import struct
import sys
import tarfile
import tempfile
import zlib
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import analyze_cp_artifact as A  # noqa: E402

try:
    import lz4.frame  # type: ignore
    HAVE_LZ4 = True
except ImportError:  # pragma: no cover
    HAVE_LZ4 = False

BLK = 512


def itoc_image(n_parts=5):
    """Build a tiny synthetic ITOC image whose parts fit the buffer."""
    names = [b"TOC\x00", b"BOOT", b"MAIN", b"VSS", b"NV"]
    hdr = bytearray(0x1000)  # S5000AP header area is 4 KiB (modem.bin: first part at 0x420)
    payload_off = len(hdr)  # parts begin after the 4 KiB header
    payload = bytearray()
    for i in range(n_parts):
        size = 1024
        off = payload_off + len(payload)
        body = bytes((i + 1,)) * size
        name = names[i].ljust(4, b"\x00")[:4]
        words = list(struct.unpack("<I", name)) + [0, 0, off,
                                                     0x40000000 + i * 0x10000,
                                                     size, zlib.crc32(body) & 0xFFFFFFFF, i]
        hdr[i * 32:(i + 1) * 32] = struct.pack("<8I", *words)
        payload.extend(body)
    return bytes(hdr) + bytes(payload)


def lz4_compress(b):
    if not HAVE_LZ4:
        raise unittest.SkipTest("python-lz4 not available")
    return lz4.frame.compress(b, compression_level=0, block_linked=False,
                              content_checksum=True)


def make_tar(members, bonus=b"", pad_end=True):
    """Hand-roll a ustar-ish TAR from (name, bytes[, typeflag]) triples."""
    out = bytearray()
    for m in members:
        name, data = m[0], m[1]
        tf = (m[2] if len(m) > 2 else b"0")
        hdr = bytearray(BLK)
        hdr[0:len(name)] = name
        hdr[100:108] = b"0000644\x00"
        hdr[108:116] = b"0000000\x00"
        hdr[116:124] = b"0000000\x00"
        hdr[124:136] = ("%011o\x00" % len(data)).encode()
        hdr[136:148] = b"00000000000\x00"
        hdr[148:156] = b" " * 8
        hdr[156:157] = tf
        hdr[257:263] = b"ustar\x00"
        hdr[263:265] = b"00"
        # checksum
        hdr[148:156] = b" " * 8
        cs = sum(hdr)
        hdr[148:156] = ("%06o\x00 " % cs).encode()
        out += hdr
        out += data
        if len(data) % BLK:
            out += b"\x00" * (BLK - len(data) % BLK)
    out += bonus
    if pad_end:
        out += b"\x00" * BLK * 2
    return bytes(out)


def with_md5(body):
    return body + hashlib.md5(body).hexdigest().encode()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data):
        p = os.path.join(self.d, name)
        with open(p, "wb") as f:
            f.write(data)
        return p

    def analyze(self, path):
        return A.analyze(path, self.d)


class TestGoodArchive(Base):
    @unittest.skipUnless(HAVE_LZ4, "python-lz4 required")
    def test_valid_archive_two_members(self):
        img = itoc_image()
        z = lz4_compress(img)
        dbg = b"PK\x03\x04" + b"fakezip" * 100
        zd = lz4_compress(dbg)
        tar = make_tar([(b"modem.bin.lz4", z), (b"modem_debug.bin.lz4", zd)])
        p = self.write("CP_test.tar.md5", with_md5(tar))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED", json.dumps(r, indent=2))
        names = [m["name"] for m in r["members"]]
        self.assertEqual(names, ["modem.bin.lz4", "modem_debug.bin.lz4"])
        m0 = r["members"][0]
        self.assertEqual(m0["lz4"]["decompressed_sha256"], hashlib.sha256(img).hexdigest())
        self.assertEqual(m0["lz4"]["decompressed_size"], len(img))
        self.assertEqual(m0["lz4"]["container"], "ITOC")
        self.assertTrue(m0["lz4"]["itoc_bounds_ok"])
        self.assertEqual(r["members"][1]["lz4"]["container"], "ZIP")

    @unittest.skipUnless(HAVE_LZ4, "python-lz4 required")
    def test_zero_tar_trailer_padding_tolerated(self):
        img = itoc_image()
        z = lz4_compress(img)
        tar = make_tar([(b"modem.bin.lz4", z)])
        # add extra zero blocks before the md5 trailer
        p = self.write("CP_pad.tar.md5", with_md5(tar + b"\x00" * BLK * 4))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED", json.dumps(r, indent=2))


class TestNegatives(Base):
    def test_missing(self):
        r = self.analyze(os.path.join(self.d, "does-not-exist.tar.md5"))
        self.assertEqual(r["decision"], "ARCHIVE_MISSING")
        self.assertIn("does-not-exist", r["missing_path"])

    @unittest.skipUnless(HAVE_LZ4, "python-lz4 required")
    def test_md5_mismatch(self):
        z = lz4_compress(itoc_image())
        tar = make_tar([(b"modem.bin.lz4", z)])
        good = with_md5(tar)
        bad = good[:-1] + (b"0" if good[-1:] != b"0" else b"1")
        p = self.write("CP_badmd5.tar.md5", bad)
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")
        c = [x for x in r["checks"] if x["name"] == "samsung_md5_trailer"][0]
        self.assertFalse(c["ok"])

    @unittest.skipUnless(HAVE_LZ4, "python-lz4 required")
    def test_truncated_archive(self):
        z = lz4_compress(itoc_image())
        tar = make_tar([(b"modem.bin.lz4", z)])
        full = with_md5(tar)
        p = self.write("CP_trunc.tar.md5", full[:len(full) // 2])
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")

    @unittest.skipUnless(HAVE_LZ4, "python-lz4 required")
    def test_corrupted_lz4_payload(self):
        img = itoc_image()
        z = bytearray(lz4_compress(img))
        # Flip bytes in the middle of the compressed payload (post-header).
        for i in range(60, 80):
            z[i] ^= 0xFF
        tar = make_tar([(b"modem.bin.lz4", bytes(z))])
        p = self.write("CP_corrupt.tar.md5", with_md5(tar))
        r = self.analyze(p)
        # MD5 trailer still matches (file not altered post-md5), but LZ4 must fail.
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED", json.dumps(r, indent=2))
        self.assertTrue(any(c["name"] == "lz4_decompress" and not c["ok"] for c in r["checks"]))

    @unittest.skipUnless(HAVE_LZ4, "python-lz4 required")
    def test_wrong_variant_names_still_analyzed(self):
        # The analyzer must NOT assert DTK9 identity; it records what it sees.
        z = lz4_compress(itoc_image())
        tar = make_tar([(b"modem.bin.lz4", z)])
        p = self.write("CP_OTHERBUILD.tar.md5", with_md5(tar))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED")
        self.assertNotIn("dtk9", json.dumps(r).lower())

    def test_path_traversal_member_rejected(self):
        z = b"notlz4"
        tar = make_tar([(b"../evil.bin.lz4", z)])
        p = self.write("CP_trav.tar.md5", with_md5(tar))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")
        c = [x for x in r["checks"] if x["name"] == "tar_structure"][0]
        self.assertIn("traversal", c["reason"])

    def test_absolute_member_rejected(self):
        tar = make_tar([(b"/etc/passwd", b"x")])
        p = self.write("CP_abs.tar.md5", with_md5(tar))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")
        self.assertIn("absolute", [x for x in r["checks"] if x["name"] == "tar_structure"][0]["reason"])

    def test_symlink_member_rejected(self):
        tar = make_tar([(b"modem.bin.lz4", b"x", b"2")])
        p = self.write("CP_sym.tar.md5", with_md5(tar))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")
        self.assertIn("symlink", [x for x in r["checks"] if x["name"] == "tar_structure"][0]["reason"])

    def test_device_member_rejected(self):
        tar = make_tar([(b"modem.bin.lz4", b"x", b"3")])
        p = self.write("CP_dev.tar.md5", with_md5(tar))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")
        self.assertIn("device", [x for x in r["checks"] if x["name"] == "tar_structure"][0]["reason"])

    def test_duplicate_member_rejected(self):
        tar = make_tar([(b"modem.bin.lz4", b"a"), (b"modem.bin.lz4", b"b")])
        p = self.write("CP_dup.tar.md5", with_md5(tar))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")
        self.assertIn("duplicate", [x for x in r["checks"] if x["name"] == "tar_structure"][0]["reason"])

    def test_oversized_member_rejected(self):
        # Claim a 1 GiB member with too little data => rejected before buffering.
        hdr = bytearray(BLK)
        hdr[0:12] = b"modem.bin.lz"
        hdr[124:136] = ("%011o\x00" % (1 << 30)).encode()
        hdr[156:157] = b"0"
        cs = sum(hdr)
        hdr[148:156] = ("%06o\x00 " % cs).encode()
        tar = bytes(hdr) + b"\x00" * BLK
        p = self.write("CP_big.tar.md5", with_md5(tar))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")
        c = [x for x in r["checks"] if x["name"] == "tar_structure"][0]
        self.assertTrue("truncated" in c["reason"] or "exceed" in c["reason"], c["reason"])

    def test_no_members_rejected(self):
        p = self.write("CP_empty.tar.md5", with_md5(b"\x00" * BLK * 2))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")

    @unittest.skipUnless(HAVE_LZ4, "python-lz4 required")
    def test_member_size_mismatch_with_lz4_frame(self):
        z = lz4_compress(itoc_image())
        z2 = z + b"\x00" * 16  # extra bytes after a complete frame
        tar = make_tar([(b"modem.bin.lz4", z2)])
        p = self.write("CP_extra.tar.md5", with_md5(tar))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")


class TestItocParser(Base):
    @unittest.skipUnless(HAVE_LZ4, "python-lz4 required")
    def test_itoc_part_crc_mismatch_rejected(self):
        img = bytearray(itoc_image())
        # Flip one byte inside MAIN's payload; ITOC CRC32 for MAIN must fail.
        main = [p for p in A.parse_itoc(bytes(img)) if p["magic"] == "MAIN"][0]
        img[main["offset"] + 7] ^= 0xFF
        z = lz4_compress(bytes(img))
        tar = make_tar([(b"modem.bin.lz4", z)])
        p = self.write("CP_itoccrc.tar.md5", with_md5(tar))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")
        self.assertTrue(any(c["name"] == "itoc_part_crc32" and not c["ok"] for c in r["checks"]))

    def test_itoc_bounds_bad(self):
        img = bytearray(itoc_image())
        # make MAIN claim more bytes than exist
        struct.pack_into("<I", img, 2 * 32 + 20, 0x7FFFFFFF)
        parts = A.parse_itoc(bytes(img))
        self.assertTrue(any(p["offset"] + p["size"] > len(img) for p in parts))


class TestDeterminism(Base):
    @unittest.skipUnless(HAVE_LZ4, "python-lz4 required")
    def test_repeat_analysis_identical(self):
        z = lz4_compress(itoc_image())
        tar = make_tar([(b"modem.bin.lz4", z)])
        p = self.write("CP_det.tar.md5", with_md5(tar))
        a = self.analyze(p)
        b = self.analyze(p)
        # Remove volatile file metadata keys before comparing.
        for r in (a, b):
            r.pop("archive")
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))


class TestExtraHardening(Base):
    @unittest.skipUnless(HAVE_LZ4, "python-lz4 required")
    def test_extra_trailing_garbage_after_md5_rejected(self):
        z = lz4_compress(itoc_image())
        tar = make_tar([(b"modem.bin.lz4", z)])
        full = with_md5(tar) + b"EXTRA"  # shifts the MD5 trailer out of final 32 bytes
        p = self.write("CP_garbage.tar.md5", full)
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")

    def test_not_a_tar_rejected(self):
        p = self.write("CP_junk.tar.md5", b"Z" * 4096 + hashlib.md5(b"Z" * 4096).hexdigest().encode())
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED_FAILED")

    @unittest.skipUnless(HAVE_LZ4, "python-lz4 required")
    def test_wrong_member_name_still_listed_not_guessed(self):
        z = lz4_compress(itoc_image())
        tar = make_tar([(b"notthemodem.bin.lz4", z)])
        p = self.write("CP_wrongname.tar.md5", with_md5(tar))
        r = self.analyze(p)
        self.assertEqual(r["decision"], "ARCHIVE_VALIDATED")
        self.assertEqual([m["name"] for m in r["members"]], ["notthemodem.bin.lz4"])

    def test_analyzer_is_read_only_on_source(self):
        z = lz4_compress(itoc_image())
        tar = make_tar([(b"modem.bin.lz4", z)])
        data = with_md5(tar)
        p = self.write("CP_ro.tar.md5", data)
        before = hashlib.sha256(open(p, "rb").read()).hexdigest()
        self.analyze(p)
        after = hashlib.sha256(open(p, "rb").read()).hexdigest()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)

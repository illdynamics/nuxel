#!/usr/bin/env python3
"""End-to-end offline mock-boot transcript tests for nuxel-cpbootd.

These prove the complete, source-faithful CP boot transaction runs against the
deterministic mock backend and reaches 'online', AND that every negative input
fails closed with a nonzero exit + machine-readable first_failed_stage.

IMPORTANT: the mock 'online' verdict is tagged `"backend":"mock"` and is NEVER
physical ONLINE. No /dev/umts_*, no block device, no RF, no ioctl are touched
here — the mock backend is pure in-memory state.
"""
import json
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
UAPI_DIR = os.path.join(HERE, "..")
BIN = os.path.join(UAPI_DIR, "nuxel-cpbootd.host")

NAME = 12
MAX_TOC = 16


def _entry(name, b_off, m_off, size, crc=0, cnt=0):
    n = name.encode()[:NAME].ljust(NAME, b"\x00")
    return n + struct.pack("<5I", b_off, m_off, size, crc, cnt)


def build_fixture(tmp, main_size=128, vss_size=64, nv_size=64):
    """Build a structurally-valid synthetic S5000AP ITOC (NOT real firmware)."""
    boot_size = 7744
    hdr = 6 * 32
    entries = [_entry("TOC", 0, 0, 0, 0, 6)]
    entries.append(_entry("BOOT", hdr, 0, boot_size))
    entries.append(_entry("MAIN", hdr + boot_size, boot_size, main_size))
    entries.append(_entry("VSS", hdr + boot_size + main_size, boot_size + main_size, vss_size))
    entries.append(_entry("NV", hdr + boot_size + main_size + vss_size, boot_size + main_size + vss_size, nv_size))
    entries.append(_entry("OFFSET", 0, 0, 0))
    blob = b"".join(entries)
    assert len(blob) == hdr
    blob += b"\xAB" * boot_size + b"\xCD" * main_size + b"\xEF" * vss_size + b"\x01" * nv_size
    path = os.path.join(tmp, "efuj2_fixture.itoc")
    with open(path, "wb") as f:
        f.write(blob)
    return path


def run(args):
    return subprocess.run([BIN] + args, capture_output=True, text=True)


def test_full_mock_boot_reaches_online():
    with tempfile.TemporaryDirectory() as td:
        fx = build_fixture(td)
        p = run(["--really-boot", "--mock", "--firmware", fx])
        assert p.returncode == 0, f"rc={p.returncode}\nstdout={p.stdout}\nstderr={p.stderr}"
        lines = [l for l in p.stdout.splitlines() if l]
        # each stage must appear in canonical order
        canonical = [
            "status-probe", "security-reinit", "xmit-boot", "security-toc",
            "security-vss", "security-main", "power-on", "boot-on", "dl-start",
            "handshake", "boot-off", "online-verify",
        ]
        seen = []
        for l in lines:
            try:
                o = json.loads(l)
            except json.JSONDecodeError:
                continue
            if "stage" in o:
                seen.append(o["stage"])
        for st in canonical:
            assert st in seen, f"missing stage {st}; seen={seen}"
        # final verdict must be 'online' AND backend 'mock' (never physical)
        final = json.loads(lines[-1])
        assert final["verdict"] == "online"
        assert final["backend"] == "mock"


def test_mock_online_is_never_mislabeled_physical():
    with tempfile.TemporaryDirectory() as td:
        fx = build_fixture(td)
        p = run(["--really-boot", "--mock", "--firmware", fx])
        tail = json.loads(p.stdout.strip().splitlines()[-1])
        assert tail["backend"] == "mock"
        assert tail.get("mode") == "really-boot"


def test_invalid_itoc_magic_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "bad.itoc")
        with open(p, "wb") as f:
            f.write(b"NOT_AN_ITOC_HDR_1234" + b"\x00" * 4000)
        r = run(["--really-boot", "--mock", "--firmware", p])
        assert r.returncode != 0
        assert "itoc-parse" in r.stdout


def test_missing_firmware_fails_closed():
    r = run(["--really-boot", "--mock", "--firmware", "/nonexistent/x.itoc"])
    assert r.returncode != 0
    assert "itoc-parse" in r.stdout


def test_bounds_overflow_part_rejected():
    with tempfile.TemporaryDirectory() as td:
        # entry with b_offset+size exceeding file size must be rejected at parse
        p = os.path.join(td, "overflow.itoc")
        # TOC count 2; second entry 'BOOT' with size huge past EOF
        e0 = _entry("TOC", 0, 0, 0, 0, 2)
        e1 = _entry("BOOT", 0x1000, 0, 0x7FFFFFFF)  # b_offset+size overflows file
        blob = e0 + e1
        # pad to at least 2*32
        blob = blob.ljust(64, b"\x00")
        with open(p, "wb") as f:
            f.write(blob)
        r = run(["--really-boot", "--mock", "--firmware", p])
        assert r.returncode != 0
        # parse must fail (either bounds or missing MAIN)
        assert "itoc-parse" in r.stdout or "out of bounds" in r.stderr or "missing" in r.stderr


def test_invalid_deadline_rejected():
    for d in ["abc", "-5", "0", "999999999"]:
        r = run(["--deadline-ms", d])
        assert r.returncode == 2, f"deadline {d} not rejected (rc={r.returncode})"


def test_physical_really_boot_rejected_on_no_hw_build():
    with tempfile.TemporaryDirectory() as td:
        fx = build_fixture(td)
        r = run(["--really-boot", "--firmware", fx, "--manifest-sha256", "deadbeef"])
        # no-HW default build must refuse physical really-boot (exit 2)
        assert r.returncode == 2
        assert "NUXEL_CPBOOTD_ENABLE_HW=1" in r.stderr


def test_dry_run_status_only_no_mutation():
    r = run(["--mock"])
    assert r.returncode == 0
    j = json.loads(r.stdout.strip())
    assert j["mode"] == "dry-run"
    assert j["backend"] == "mock"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))

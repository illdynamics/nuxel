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
import hashlib
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
# BootDumpModap.cpp: CP_MEMORY_MASK strips the top 2 bits of the absolute load
# address to yield the XMIT_BOOT relative offset.
CP_MEMORY_MASK = (0x40000000 - 1)


def _entry(name, b_off, m_off, size, crc=0, cnt=0):
    n = name.encode()[:NAME].ljust(NAME, b"\x00")
    return n + struct.pack("<5I", b_off, m_off, size, crc, cnt)


def build_fixture(tmp, main_size=128, vss_size=64, nv_size=64):
    """Build a structurally-valid synthetic S5000AP ITOC matching the REAL
    verified layout (load addresses == CP DRAM base-relative offsets), NOT a
    fabricated sequentially-accumulated layout."""
    boot_size = 7744
    # Absolute load addresses mirroring the verified DTK9/EFUJ2 modem.bin ITOC:
    #   TOC 0x40008000, BOOT 0x40000000, MAIN 0x40010000,
    #   VSS 0x47800000,  NV 0x45600000, OFFSET 0x00000000
    LOAD_TOC  = 0x40008000
    LOAD_BOOT = 0x40000000
    LOAD_MAIN = 0x40010000
    LOAD_VSS  = 0x47800000
    LOAD_NV   = 0x45600000

    hdr = MAX_TOC * 32
    entries = []
    # TOC: size=1040 (like the real TOC part), nonzero m_offset, stage count = 5
    entries.append(_entry("TOC", 0, LOAD_TOC, 1040, 0, 5))
    entries.append(_entry("BOOT", hdr, LOAD_BOOT, boot_size))
    entries.append(_entry("MAIN", hdr + boot_size, LOAD_MAIN, main_size))
    entries.append(_entry("VSS", hdr + boot_size + main_size, LOAD_VSS, vss_size))
    entries.append(_entry("NV", hdr + boot_size + main_size + vss_size, LOAD_NV, nv_size))
    entries.append(_entry("OFFSET", 0, 0, 0))
    # Pad remaining slots to a full 16 x 32-byte TOC table (zero-filled).
    while len(entries) < MAX_TOC:
        entries.append(_entry("", 0, 0, 0, 0, 0))
    blob = b"".join(entries)
    assert len(blob) == hdr
    blob += b"\xAB" * boot_size + b"\xCD" * main_size + b"\xEF" * vss_size + b"\x01" * nv_size
    path = os.path.join(tmp, "efuj2_fixture.itoc")
    with open(path, "wb") as f:
        f.write(blob)
    return path


def run(args):
    return subprocess.run([BIN] + args, capture_output=True, text=True,
                          errors="replace")


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


def test_itoc_parse_reports_stage_count_and_toc_m_offset():
    """Regression: parse_itoc must report the stage count (toc[0].toc_count)
    and the TOC's own masked m_offset, mirroring the real EFUJ2/DTK9 layout."""
    with tempfile.TemporaryDirectory() as td:
        fx = build_fixture(td)
        p = run(["--really-boot", "--mock", "--firmware", fx])
        assert p.returncode == 0, f"rc={p.returncode}\nstderr={p.stderr}"
        assert "stages=5" in p.stderr
        assert "BOOT@1 MAIN@2 VSS@3 NV@4 OFFSET@5" in p.stderr
        assert "TOC(m_off=0x40008000 size=1040)" in p.stderr

def test_toc_missing_moffset_fails_closed():
    """Regression: secure verify requires TOC m_offset != 0 (cbd rejects a TOC
    with no m_offset under CONFIG_SEC_CP_VERIFYING_ALL)."""
    with tempfile.TemporaryDirectory() as td:
        p_path = os.path.join(td, "no_toc_moff.itoc")
        boot_size = 7744
        hdr = MAX_TOC * 32
        entries = [_entry("TOC", 0, 0, 1040, 0, 5),  # m_offset == 0 -> reject
                   _entry("BOOT", hdr, 0x40000000, boot_size),
                   _entry("MAIN", hdr + boot_size, 0x40010000, 128),
                   _entry("VSS", hdr + boot_size + 128, 0x47800000, 64),
                   _entry("NV", hdr + boot_size + 128 + 64, 0x45600000, 64),
                   _entry("OFFSET", 0, 0, 0)]
        while len(entries) < MAX_TOC:
            entries.append(_entry("", 0, 0, 0, 0, 0))
        blob = b"".join(entries)
        blob += b"\xAB" * (boot_size + 128 + 64 + 64)
        with open(p_path, "wb") as f:
            f.write(blob)
        r = run(["--really-boot", "--mock", "--firmware", p_path])
        assert r.returncode != 0
        assert "no m_offset for TOC verification" in r.stderr


def nv_fixture(td, data=b"\xcc" * 64):
    fx = build_fixture(td)
    # NV b_offset is zero in the real TOC: it names a separate EFS input.
    with open(fx, "r+b") as f:
        f.seek(4 * 32 + 12)
        f.write(struct.pack("<I", 0))
    nv = os.path.join(td, "nv.bin")
    md5 = nv + ".md5"
    with open(nv, "wb") as f:
        f.write(data)
    with open(md5, "w") as f:
        f.write(hashlib.md5(data + b"Samsung_Android_RIL").hexdigest())
    return ["--really-boot", "--mock", "--firmware", fx, "--nv-image", nv, "--nv-md5", md5]


def test_nv_snapshot_is_verified_and_downloaded_to_toc_address():
    with tempfile.TemporaryDirectory() as td:
        p = run(nv_fixture(td))
        assert p.returncode == 0, p.stdout + p.stderr
        events = [json.loads(line) for line in p.stdout.splitlines()]
        nv = next(e for e in events if "nv_download" in e)
        assert nv == {"nv_download": "complete", "bytes": 64, "m_offset": 0x5600000}
        assert events[0]["nv_preflight"] == "verified"
        assert events[-1]["verdict"] == "online"


def test_nv_corruption_rejected_before_cp_reset_or_download():
    with tempfile.TemporaryDirectory() as td:
        args = nv_fixture(td)
        with open(os.path.join(td, "nv.bin"), "r+b") as f:
            f.write(b"\0")
        p = run(args)
        assert p.returncode != 0 and "nv-preflight" in p.stdout
        assert '"stage"' not in p.stdout


def test_nv_length_mismatch_and_plain_md5_fail_closed():
    with tempfile.TemporaryDirectory() as td:
        p = run(nv_fixture(td, b"\xcc" * 63))
        assert p.returncode != 0 and '"stage"' not in p.stdout
        args = nv_fixture(td)
        with open(os.path.join(td, "nv.bin.md5"), "w") as f:
            f.write(hashlib.md5(b"\xcc" * 64).hexdigest())
        p = run(args)
        assert p.returncode != 0 and '"stage"' not in p.stdout

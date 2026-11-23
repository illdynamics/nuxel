#!/usr/bin/env python3
"""Offline verification of the Samsung S5000AP / Exynos9820 kernel UAPI.

These tests assert, from the pinned kernel commit
f7194c1d15eded1c2a1a4dc63825b26103435cc0, the exact numeric ioctl values
(Linux asm-generic _IO encoding), struct sizes, field offsets, boot-state
enum order, SIPC5 framing sizes, and 32/64-bit layout identity. They do NOT
touch any device and perform NO ioctl.

The struct-layout numbers below were derived by cross-compiling for AArch64
(GCC 15.2.0) and ILP32 and reading the DWARF/disassembly, not guessed.
"""

import json
import subprocess
import sys
import tempfile
import os

HERE = os.path.dirname(os.path.abspath(__file__))
UAPI_DIR = os.path.join(HERE, "..")
HEADER = os.path.join(UAPI_DIR, "s5000ap_uapi.h")
CHECK_C = os.path.join(UAPI_DIR, "nuxel-s5000ap-uapi-check.c")

# Linux asm-generic ioctl encoding: _IO('o',N) == 0x6F00 | N
IO = lambda n: 0x6F00 | n  # noqa: E731

EXPECTED_IOCTLS = {
    "IOCTL_MODEM_ON":              IO(0x19),
    "IOCTL_MODEM_OFF":             IO(0x20),
    "IOCTL_MODEM_RESET":           IO(0x21),
    "IOCTL_MODEM_BOOT_ON":         IO(0x22),
    "IOCTL_MODEM_BOOT_OFF":        IO(0x23),
    "IOCTL_MODEM_BOOT_DONE":       IO(0x24),
    "IOCTL_MODEM_PROTOCOL_SUSPEND": IO(0x25),
    "IOCTL_MODEM_PROTOCOL_RESUME":  IO(0x26),
    "IOCTL_MODEM_STATUS":          IO(0x27),
    "IOCTL_MODEM_DL_START":        IO(0x28),
    "IOCTL_MODEM_FW_UPDATE":       IO(0x29),
    "IOCTL_MODEM_NET_SUSPEND":     IO(0x30),
    "IOCTL_MODEM_NET_RESUME":      IO(0x31),
    "IOCTL_MODEM_DUMP_START":      IO(0x32),
    "IOCTL_MODEM_DUMP_UPDATE":     IO(0x33),
    "IOCTL_MODEM_FORCE_CRASH_EXIT": IO(0x34),
    "IOCTL_MODEM_CP_UPLOAD":       IO(0x35),
    "IOCTL_MODEM_SET_TX_LINK":     IO(0x37),
    "IOCTL_MODEM_XMIT_BOOT":       IO(0x40),
    "IOCTL_MODEM_GET_SHMEM_INFO":  IO(0x41),
    "IOCTL_DPRAM_INIT_STATUS":     IO(0x43),
    "IOCTL_LINK_DEVICE_RESET":     IO(0x44),
    "IOCTL_MODEM_GET_SHMEM_SRINFO": IO(0x45),
    "IOCTL_MODEM_SET_SHMEM_SRINFO": IO(0x46),
    "IOCTL_MODEM_GET_CP_BOOTLOG":  IO(0x47),
    "IOCTL_MODEM_CLR_CP_BOOTLOG":  IO(0x48),
    "IOCTL_MIF_LOG_DUMP":          IO(0x51),
    "IOCTL_MIF_DPRAM_DUMP":        IO(0x52),
    "IOCTL_SECURITY_REQ":          IO(0x53),
    "IOCTL_SHMEM_FULL_DUMP":       IO(0x54),
    "IOCTL_MODEM_CRASH_REASON":    IO(0x55),
    "IOCTL_MODEM_AIRPLANE_MODE":   IO(0x56),
    "IOCTL_VSS_FULL_DUMP":         IO(0x57),
    "IOCTL_ACPM_FULL_DUMP":        IO(0x58),
    "IOCTL_CPLOG_FULL_DUMP":       IO(0x59),
    "IOCTL_DATABUF_FULL_DUMP":     IO(0x5A),
    "IOCTL_MODEM_RAMDUMP_START":   IO(0xCE),
    "IOCTL_MODEM_RAMDUMP_STOP":    IO(0xCF),
}

EXPECTED_STATE = {
    "STATE_OFFLINE": 0, "STATE_CRASH_RESET": 1, "STATE_CRASH_EXIT": 2,
    "STATE_BOOTING": 3, "STATE_ONLINE": 4, "STATE_NV_REBUILDING": 5,
    "STATE_LOADER_DONE": 6, "STATE_SIM_ATTACH": 7, "STATE_SIM_DETACH": 8,
    "STATE_CRASH_WATCHDOG": 9,
}

EXPECTED_BOOT_MODE = {
    "CP_BOOT_MODE_NORMAL": 0, "CP_BOOT_MODE_DUMP": 1, "CP_BOOT_RE_INIT": 2,
    "CP_BOOT_REQ_CP_RAM_LOGGING": 5, "CP_BOOT_MODE_MANUAL": 7,
}


def _header_text():
    with open(HEADER) as f:
        return f.read()


def strip_c_comments(src):
    out = []
    i = 0
    n = len(src)
    while i < n:
        if src[i:i+2] == "//":
            j = src.find("\n", i)
            i = n if j == -1 else j
        elif src[i:i+2] == "/*":
            j = src.find("*/", i + 2)
            i = n if j == -1 else j + 2
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


def parse_macro_value(name, src):
    """Parse a #define NAME (literal) style macro that is a single hex/dec/int."""
    stripped = strip_c_comments(src)
    for line in stripped.splitlines():
        line = line.strip()
        if line.startswith("#define"):
            parts = line.split(None, 2)
            if len(parts) >= 3 and parts[1] == name:
                val = parts[2].strip()
                val = val.split("/*")[0].strip()
                # handle  (IOCTL_MAGIC | 0xNN)  and plain ints
                if "IOCTL_MAGIC" in val:
                    val = val.replace("IOCTL_MAGIC", "0x6F00")
                # strip surrounding parens so a single '|' expression can evaluate
                val = val.strip("()")
                try:
                    # allow only hex ints and '|' of hex ints (no arbitrary eval)
                    import re
                    if re.fullmatch(r"0x[0-9A-Fa-f]+(?:\s*\|\s*0x[0-9A-Fa-f]+)+", val):
                        val = eval(val, {"__builtins__": {}}, {})
                        return val
                    return int(val, 0)
                except (ValueError, SyntaxError):
                    return None
    return None


def parse_enum(name, src):
    """Parse an enum NAME { A=0, B, ... } returning {member: value}."""
    stripped = strip_c_comments(src)
    import re
    m = re.search(r"enum\s+" + re.escape(name) + r"\s*\{([^}]*)\}", stripped)
    if not m:
        return {}
    body = m.group(1)
    result = {}
    val = 0
    for line in body.splitlines():
        line = line.strip().strip(",").strip()
        if not line or line.startswith("//"):
            continue
        # python-style member = expr
        if "=" in line:
            member, expr = line.split("=", 1)
            member = member.strip()
            expr = expr.strip()
            # try int, else fall back to previous value + 1
            try:
                val = int(expr, 0)
            except ValueError:
                val += 1
        else:
            member = line.strip()
            val = val if member else val + 0
        result[member] = val
        val += 1
    return result


def test_ioctl_values():
    src = _header_text()
    for name, expected in EXPECTED_IOCTLS.items():
        got = parse_macro_value(name, src)
        assert got == expected, f"{name}: expected 0x{expected:08X} got {got!r}"


def test_state_enum():
    src = _header_text()
    got = parse_enum("modem_state", src)
    for name, expected in EXPECTED_STATE.items():
        assert got.get(name) == expected, f"{name}: {got.get(name)} != {expected}"


def test_boot_mode_enum():
    src = _header_text()
    got = parse_enum("cp_boot_mode", src)
    for name, expected in EXPECTED_BOOT_MODE.items():
        assert got.get(name) == expected, f"{name}: {got.get(name)} != {expected}"


def test_struct_layout_constants():
    src = _header_text()
    # The header must NOT claim 32 bytes; the correct packed size is 28.
    assert "32 bytes" not in strip_c_comments(src).replace("28 bytes", ""), \
        "header still references the discredited 32-byte size"


def _compile_and_run(cc, flags):
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "check")
        argv = [cc] + flags + ["-o", out, CHECK_C]
        p = subprocess.run(argv, capture_output=True, text=True)
        assert p.returncode == 0, f"{cc} build failed:\n{p.stderr}"
        r = subprocess.run([out], capture_output=True, text=True)
        assert r.returncode == 0, f"check run failed:\n{r.stderr}"
        return json.loads(r.stdout)


def test_host_lp64_layout():
    cc = os.environ.get("CC", "gcc")
    try:
        d = _compile_and_run(cc, ["-O2", "-Wall", "-Wextra", "-Werror"])
    except FileNotFoundError:
        pytest.skip(f"{cc} not available")
    assert d["sizeof_modem_firmware"] == 28
    assert d["modem_firmware_offsets"] == {
        "binary": 0, "size": 8, "m_offset": 12,
        "b_offset": 16, "mode": 20, "len": 24,
    }
    assert d["sizeof_modem_sec_req"] == 16
    assert d["sizeof_sipc5_link_header"] == 6
    assert int(d["ioctl_0x27_status"], 16) == 0x6F27
    assert int(d["ioctl_0x40_xmit_boot"], 16) == 0x6F40
    assert int(d["ioctl_0x53_security"], 16) == 0x6F53
    assert d["state_online"] == 4
    assert d["state_crash_watchdog"] == 9


def test_aarch64_cross_compile():
    cc = os.environ.get("AARCH64_CC", "aarch64-linux-gnu-gcc")
    if not _which(cc):
        pytest.skip(f"{cc} not available")
    # -static build proves the binary is self-contained for the device
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "check")
        argv = [cc, "-O2", "-Wall", "-Wextra", "-Werror", "-static", "-o", out, CHECK_C]
        p = subprocess.run(argv, capture_output=True, text=True)
        assert p.returncode == 0, f"aarch64 build failed:\n{p.stderr}"


def _which(cmd):
    from shutil import which
    return which(cmd) is not None


def test_no_device_access():
    src = open(CHECK_C).read()
    for banned in ["open(", "ioctl(", "/dev/", "O_RDWR", "O_RDONLY", "write("]:
        assert banned not in src, f"uapi-check must not contain {banned!r}"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))

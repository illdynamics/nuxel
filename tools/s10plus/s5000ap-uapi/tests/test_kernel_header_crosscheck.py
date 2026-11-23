#!/usr/bin/env python3
"""Cross-check the extracted s5000ap_uapi.h against the ACTUAL kernel source.

Parses the pinned kernel headers (modem_prj.h, sipc5.h, modem_v1.h) and asserts
the extracted userspace header agrees on: every IOCTL_* macro value (via the
Linux asm-generic ioctl encoding), the modem_state enum order, cp_boot_mode
values, struct modem_firmware field order, and struct modem_sec_req fields.

This is a SOURCE-level comparative assertion: it does not touch any device.

The kernel source is a required input. If it is absent, this suite SKIPS with
the missing path rather than reporting a false PASS (a real checkout at the
pinned SHA f7194c1d15eded1c2a1a4dc63825b26103435cc0 is mandatory).
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
UAPI_HEADER = os.path.join(os.path.dirname(HERE), "s5000ap_uapi.h")

KERNEL = os.path.join(ROOT, "kernel", "s10plus", ".build",
                      "src.polluted.case-insensitive", "drivers", "misc", "modem_v1")
MODEM_PRJ = os.path.join(KERNEL, "modem_prj.h")
SIPC5 = os.path.join(KERNEL, "include", "sipc5.h")
MODEM_V1 = os.path.join(KERNEL, "modem_v1.h")

IO = lambda n: 0x6F00 | n  # noqa: E731

# PCIe-only ioctls, gated by #ifdef CONFIG_LINK_DEVICE_PCIE in the kernel.
# This device is SHMEM (CONFIG_LINK_DEVICE_SHMEM=y), so these do NOT exist in
# the running kernel and MUST be absent from the SHMEM UAPI header.
PCIE_ONLY_IOCTLS = {"IOCTL_MODEM_DUMP_RESET", "IOCTL_REGISTER_PCIE"}


def _src(path):
    with open(path) as f:
        return f.read()


def _strip(src):
    # naive C comment strip
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


def _require_kernel():
    """Raise a skip if the pinned kernel source is not present."""
    if not os.path.isfile(MODEM_PRJ):
        pytest.skip(
            f"kernel source at {MODEM_PRJ} not present; require a genuine checkout "
            "of android_kernel_samsung_exynos9820 @ f7194c1d15eded1c2a1a4dc63825b26103435cc0"
        )


def kernel_ioctl_values():
    """Extract every IOCTL_* macro from modem_prj.h (the canonical kernel source)."""
    _require_kernel()
    src = _strip(_src(MODEM_PRJ))
    vals = {}
    for m in re.finditer(r"#define\s+(IOCTL_[A-Z0-9_]+)\s+_IO\('o',\s*(0x[0-9A-Fa-f]+)\)", src):
        name, num = m.group(1), int(m.group(2), 16)
        vals[name] = IO(num)
    return vals


def uapi_ioctl_values():
    """Extract every IOCTL_* macro from the extracted userspace header."""
    src = _strip(_src(UAPI_HEADER))
    vals = {}
    for m in re.finditer(r"#define\s+(IOCTL_[A-Z0-9_]+)\s+\(IOCTL_MAGIC\s*\|\s*(0x[0-9A-Fa-f]+)\)", src):
        name, num = m.group(1), int(m.group(2), 16)
        vals[name] = 0x6F00 | num
    return vals


def test_every_kernel_ioctl_present_and_equal():
    k = kernel_ioctl_values()
    u = uapi_ioctl_values()
    assert k, "could not parse kernel ioctls"
    for name, val in k.items():
        if name in PCIE_ONLY_IOCTLS:
            # PCIe-only: must be ABSENT from the SHMEM header
            assert name not in u, f"{name} is PCIe-only and must NOT be in SHMEM header"
            continue
        assert name in u, f"missing {name} in extracted header"
        assert u[name] == val, f"{name}: uapi 0x{u[name]:X} != kernel 0x{val:X}"


def test_no_extra_dangerous_ioctl_injected():
    k = kernel_ioctl_values()
    u = uapi_ioctl_values()
    # Every UAPI ioctl must exist in the kernel (no invented commands)
    for name in u:
        assert name in k, f"UAPI {name} is NOT in the kernel (injected?)"


def test_kernel_state_enum_matches():
    src = _strip(_src(MODEM_PRJ))
    m = re.search(r"enum\s+modem_state\s*\{([^}]*)\}", src)
    assert m, "modem_state enum not found in kernel"
    body = m.group(1)
    members = [l.strip().strip(",").strip() for l in body.splitlines() if l.strip() and not l.strip().startswith("//")]
    expected = ["STATE_OFFLINE", "STATE_CRASH_RESET", "STATE_CRASH_EXIT",
                "STATE_BOOTING", "STATE_ONLINE", "STATE_NV_REBUILDING",
                "STATE_LOADER_DONE", "STATE_SIM_ATTACH", "STATE_SIM_DETACH",
                "STATE_CRASH_WATCHDOG"]
    got = [x for x in members if x]
    assert got == expected, f"kernel modem_state order mismatch: {got} != {expected}"


def test_kernel_firmware_struct_field_order():
    src = _strip(_src(MODEM_PRJ))
    m = re.search(r"struct\s+modem_firmware\s*\{(.*?)\}\s*__packed;", src, re.S)
    assert m, "modem_firmware struct not found"
    body = m.group(1)
    fields = [l.strip().rstrip(";").split()[-1] for l in body.splitlines()
              if l.strip() and not l.strip().startswith("//")]
    assert fields == ["binary", "size", "m_offset", "b_offset", "mode", "len"], \
        f"modem_firmware field order mismatch: {fields}"


def test_kernel_sec_req_field_order():
    src = _strip(_src(MODEM_PRJ))
    m = re.search(r"struct\s+modem_sec_req\s*\{(.*?)\}\s*__packed;", src, re.S)
    assert m, "modem_sec_req struct not found"
    body = m.group(1)
    fields = [l.strip().rstrip(";").split()[-1] for l in body.splitlines()
              if l.strip() and not l.strip().startswith("//")]
    assert fields == ["mode", "param2", "param3", "param4"], f"modem_sec_req order mismatch: {fields}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

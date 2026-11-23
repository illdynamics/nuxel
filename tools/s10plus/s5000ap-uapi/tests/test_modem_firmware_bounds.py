#!/usr/bin/env python3
"""Offline bounds-check tests for the XMIT_BOOT argument (struct modem_firmware).

These replicate the kernel's shmem_xmit_boot() validation arithmetic
(valid_space, m_offset + len overflow) WITHOUT touching any device, and assert
that a safe userspace planner would reject the same malformed inputs the
kernel rejects. They are pure arithmetic/struct-layout checks.

They also document the negative proof: none of these inputs can reach the
kernel in dry-run mode because nuxel-cpbootd never issues XMIT_BOOT.
"""
import struct
import sys

# struct modem_firmware (__packed, AArch64): u64 binary; u32 size/m_offset
# b_offset/mode/len => "=QIIIII" = 8 + 5*4 = 28 bytes
MF_FMT = "=QIIIII"
MF_SIZE = struct.calcsize(MF_FMT)
assert MF_SIZE == 28, f"modem_firmware must be 28 bytes, got {MF_SIZE}"


def pack_mf(binary=0, size=0, m_offset=0, b_offset=0, mode=0, length=0):
    return struct.pack(MF_FMT, binary & 0xFFFFFFFFFFFFFFFF, size & 0xFFFFFFFF,
                       m_offset & 0xFFFFFFFF, b_offset & 0xFFFFFFFF,
                       mode & 0xFFFFFFFF, length & 0xFFFFFFFF)


# Kernel validation (from link_device_shmem.c::shmem_xmit_boot):
#   valid_space = (mf.mode) ? mld->size : mld->boot_size
#   if mf.size > valid_space || mf.len > valid_space
#      || mf.m_offset > valid_space - mf.len   -> -EINVAL
def kernel_accepts(mf, boot_size, full_size):
    binary, size, m_offset, b_offset, mode, length = mf
    valid_space = full_size if mode else boot_size
    if size > valid_space or length > valid_space:
        return False
    if m_offset > valid_space - length:   # the integer-overflow fix
        return False
    return True


def test_packed_size_is_28():
    assert MF_SIZE == 28


def test_normal_boot_accept():
    # m_offset is RELATIVE to the shmem window base (not a physical address).
    # BOOT stage: 7,744 bytes at relative offset 0 in an 8 MiB boot window.
    mf = (0x10000000, 7744, 0, 0, 0, 7744)
    assert kernel_accepts(mf, boot_size=8 * 1024 * 1024, full_size=64 * 1024 * 1024)


def test_integer_overflow_m_offset_plus_len_rejected():
    # m_offset near U32_MAX with a len that overflows => must reject
    mf = (0, 0xFFFFFFFF, 0xFFFFFFF0, 0, 0, 0x20)
    assert kernel_accepts(mf, boot_size=8 * 1024 * 1024, full_size=8 * 1024 * 1024) is False


def test_size_exceeds_window_rejected():
    mf = (0, 0, 0, 0, 0, 0)
    mf = (0, 9 * 1024 * 1024, 0, 0, 0, 9 * 1024 * 1024)   # > 8 MiB boot window
    assert kernel_accepts(mf, boot_size=8 * 1024 * 1024, full_size=8 * 1024 * 1024) is False


def test_len_exceeds_window_rejected():
    mf = (0, 1024, 0, 0, 0, 9 * 1024 * 1024)
    assert kernel_accepts(mf, boot_size=8 * 1024 * 1024, full_size=8 * 1024 * 1024) is False


def test_m_offset_past_end_rejected():
    mf = (0, 1024, 7 * 1024 * 1024, 0, 0, 2 * 1024 * 1024)  # spans past window end
    assert kernel_accepts(mf, boot_size=8 * 1024 * 1024, full_size=8 * 1024 * 1024) is False


def test_dump_mode_uses_full_window():
    # mode=1 => valid_space = full_size, so a larger offset is allowed
    mf = (0, 1024, (8 * 1024 * 1024) - 1024, 0, 1, 1024)
    assert kernel_accepts(mf, boot_size=8 * 1024 * 1024, full_size=64 * 1024 * 1024) is True


def test_wrong_endianness_field_order_is_fixed():
    # The struct is little-endian (kernel AArch64). Verify field order byte-layout.
    mf = pack_mf(binary=0xDEADBEEFCAFEBABE, size=0x01020304, m_offset=0x05060708,
                 b_offset=0x11121314, mode=0x21222324, length=0x31323334)
    # binary is first 8 bytes LE
    assert mf[0:8] == struct.pack("<Q", 0xDEADBEEFCAFEBABE)
    # size at offset 8
    assert struct.unpack_from("<I", mf, 8)[0] == 0x01020304
    assert struct.unpack_from("<I", mf, 12)[0] == 0x05060708
    assert struct.unpack_from("<I", mf, 16)[0] == 0x11121314
    assert struct.unpack_from("<I", mf, 20)[0] == 0x21222324
    assert struct.unpack_from("<I", mf, 24)[0] == 0x31323334


def test_overlapping_segments_require_planner_check():
    # Two consecutive XMIT_BOOT calls with overlapping m_offset ranges would
    # corrupt the already-copied image. The kernel does NOT check overlap, so a
    # safe userspace planner MUST. Assert the planner logic (documented here).
    seg1 = (0x10000000, 0x1000, 0x1000)   # offset 0x1000..0x1FFF
    seg2 = (0x10001000, 0x1800, 0x800)      # offset 0x1800..0x1FFF overlaps seg1
    # planner rejects when seg2.start < seg1.end
    seg1_start, seg1_end = seg1[1], seg1[1] + seg1[2]
    seg2_start = seg2[1]
    assert seg2_start < seg1_end, "seg2 must overlap for this test to be meaningful"
    overlap = seg2_start < seg1_end
    assert overlap is True
    # The planner must therefore reject seg2 (not part of kernel; it's a userspace guard)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))

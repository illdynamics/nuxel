#!/usr/bin/env python3
"""Fail-closed, *offline* SSP BOOT-v1 kernel-only repacker for SM-G975F.

This particular donor is a full-size 57,671,680-byte BOOT partition image
with a 2048-byte header page, an arm64 Image, LZMA-alone ramdisk and **no**
appended DTB. Device-tree material lives in SEPARATE partitions. An arbitrary
FDT search is never a legitimate way to determine where the kernel starts.

This script cannot flash anything. Its successful exit proves only that its
byte-level packaging invariants hold. See SSP Stage 04/05 gates for required
*independent* BOOT and DT evidence and verified TWRP rollback copies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

PAGE = 2048
PARTITION_BYTES = 57_671_680
MAGIC = b"ANDROID!"
ARM64_MAGIC = b"ARM\x64"
HEADER_VERSION = 1
HEADER_SIZE = 1648


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def aligned(length: int, page: int = PAGE) -> int:
    return ((length + page - 1) // page) * page


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def section_layout(buf: bytes, capacity: int) -> dict:
    require(len(buf) == capacity, f"donor must be full partition ({capacity} bytes), got {len(buf)}")
    require(buf[:8] == MAGIC, "invalid Android BOOT magic")
    klen, kaddr, rlen, raddr = struct.unpack_from("<IIII", buf, 8)
    second, second_addr, tags, page, version = struct.unpack_from("<IIIII", buf, 24)
    hdrsize = struct.unpack_from("<I", buf, 1644)[0]
    require(page == PAGE, f"unapproved BOOT page size {page}")
    require(version == HEADER_VERSION and hdrsize == HEADER_SIZE,
            f"requires BOOT-v1 header size {HEADER_SIZE}, found {version}/{hdrsize}")
    require(second == 0 and second_addr == 0, "unexpected second-stage payload")
    require(struct.unpack_from("<I", buf, 1632)[0] == 0 and
            struct.unpack_from("<Q", buf, 1636)[0] == 0,
            "unexpected recovery DTBO payload in BOOT header")
    require(kaddr == 0x10008000 and raddr == 0x11000000 and tags == 0x10000100,
            "unexpected S10+ kernel/ramdisk/tags load addresses")
    require(b"nuxel.device=s10plus" in buf[64:576], "not a Nuxel S10+ donor")
    require(klen >= 65536 and rlen > 0, "empty/tiny BOOT component")
    koff = PAGE
    roff = koff + aligned(klen)
    end = roff + aligned(rlen)
    require(end <= capacity, "kernel+ramdisk overflows donor")
    require(buf[koff + 0x38:koff + 0x3c] == ARM64_MAGIC,
            "donor is missing raw ARM64 Image header")
    require(buf[roff:roff + 3] == b"\x5d\x00\x00", "unexpected donor ramdisk compression")
    require(not any(buf[koff + klen:roff]), "nonzero donor kernel alignment bytes")
    require(not any(buf[roff + rlen:end]), "nonzero donor ramdisk alignment bytes")
    require(not any(buf[end:]),
            "nonzero data after donor ramdisk: possible appended DTB or other trailer; REFUSE")
    return {"kernel_offset": koff, "kernel_size": klen, "ramdisk_offset": roff,
            "ramdisk_size": rlen, "payload_end_aligned": end,
            "header": buf[:PAGE], "ramdisk": buf[roff:roff + rlen],
            "kernel_addr": kaddr, "ramdisk_addr": raddr, "tags_addr": tags}


def make_candidate(donor: bytes, kernel: bytes, *, capacity: int,
                   expect_donor_sha256: str) -> tuple[bytes, dict]:
    require(len(expect_donor_sha256) == 64 and
            all(c in "0123456789abcdef" for c in expect_donor_sha256.lower()),
            "--expect-donor-sha256 must contain the complete SHA-256")
    actual_donor_sha = sha256(donor)
    require(actual_donor_sha == expect_donor_sha256.lower(),
            f"donor SHA-256 mismatch (actual {actual_donor_sha})")
    parts = section_layout(donor, capacity)
    require(len(kernel) >= 65536 and kernel[0x38:0x3c] == ARM64_MAGIC,
            "candidate must be raw, uncompressed AArch64 Image")
    k_aligned = aligned(len(kernel))
    rlen = parts["ramdisk_size"]
    end = PAGE + k_aligned + aligned(rlen)
    require(end <= capacity, f"candidate components {end} exceed partition {capacity}")
    header = bytearray(parts["header"])
    struct.pack_into("<I", header, 8, len(kernel))  # kernel_size is the *only* changed header field
    candidate = bytes(header) + kernel + bytes(k_aligned - len(kernel))
    candidate += parts["ramdisk"] + bytes(aligned(rlen) - rlen)
    candidate += bytes(capacity - len(candidate))
    require(len(candidate) == capacity, "candidate not partition sized")
    check = section_layout(candidate, capacity)
    require(check["ramdisk"] == parts["ramdisk"], "candidate ramdisk was modified")
    require(candidate[0:8] == donor[0:8] and
            candidate[12:PAGE] == donor[12:PAGE], "donor header unexpectedly changed")
    require(candidate[PAGE:PAGE + len(kernel)] == kernel, "candidate kernel differs")
    manifest = {
        "format": "nuxel-ssp-separate-dt-boot-v1", "offline_only": True,
        "flash_authorized": False,
        "donor_sha256": actual_donor_sha, "donor_bytes": len(donor),
        "candidate_sha256": sha256(candidate), "candidate_bytes": len(candidate),
        "kernel_sha256": sha256(kernel), "kernel_size": len(kernel),
        "kernel_offset": PAGE, "kernel_addr": hex(parts["kernel_addr"]),
        "ramdisk_sha256": sha256(check["ramdisk"]), "ramdisk_size": rlen,
        "ramdisk_offset": check["ramdisk_offset"],
        "ramdisk_addr": hex(parts["ramdisk_addr"]),
        "header_change_only": "kernel_size@0x08", "appended_dtb_count": 0,
        "dtb_dtbo_external_partitions": True, "trailing_partition_slack_zero": True,
        "requires_independent_boot_verifier": True,
        "requires_two_verified_rollback_copies": True,
        "requires_live_dt_readback": True,
    }
    return candidate, manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--donor", required=True, help="full-size known-good BOOT partition backup")
    p.add_argument("--kernel", required=True, help="verified uncompressed ARM64 kernel Image")
    p.add_argument("--out", required=True)
    p.add_argument("--expect-donor-sha256", required=True, help="trusted independently acquired SHA-256")
    p.add_argument("--partition-bytes", type=int, default=PARTITION_BYTES)
    p.add_argument("--manifest", help="write JSON packaging evidence (not flash approval)")
    p.add_argument("--pad-to-partition", action="store_true", help="retained compatibility; padding is always mandatory")
    # Explicitly reject former ramdisk-changing options rather than silently ignoring them.
    p.add_argument("--ramdisk-raw", default="")
    p.add_argument("--initramfs-cpio", default="")
    p.add_argument("--ramdisk-align", type=int, default=PAGE)
    args = p.parse_args(argv)
    try:
        require(not args.ramdisk_raw and not args.initramfs_cpio,
                "SSP candidate must be kernel-only; ramdisk replacement is forbidden")
        require(args.ramdisk_align == PAGE, "SSP uses canonical 2048-byte alignment")
        require(args.partition_bytes > PAGE * 2 and args.partition_bytes % PAGE == 0,
                "invalid BOOT partition byte count")
        require(Path(args.donor).resolve() != Path(args.out).resolve(),
                "refusing to overwrite donor BOOT image")
        require(Path(args.kernel).resolve() != Path(args.out).resolve(),
                "refusing to overwrite kernel Image")
        candidate, facts = make_candidate(Path(args.donor).read_bytes(),
                                          Path(args.kernel).read_bytes(),
                                          capacity=args.partition_bytes,
                                          expect_donor_sha256=args.expect_donor_sha256)
        # Atomic replacement prevents incomplete output after an interrupted write.
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(out.name + ".ssp-incomplete")
        try:
            with tmp.open("wb") as fh:
                fh.write(candidate)
                fh.flush()
                os.fsync(fh.fileno())
            tmp.replace(out)
        finally:
            tmp.unlink(missing_ok=True)
        if args.manifest:
            Path(args.manifest).write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n")
        print(json.dumps(facts, indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError, struct.error) as exc:
        print(f"SSP BOOT pack REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

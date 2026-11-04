#!/usr/bin/env python3
"""Generate an owner-approved MFC safety receipt (PWNAGE-61000).

This is deliberately conservative.  It never sets owner_approved or
kernel_patch_applied by itself; the operator must pass the explicit flags after
verifying the live state.  The physical first open is still a separate action.

Usage:
  nuxel-mfc-safety-receipt.py --print-template
  nuxel-mfc-safety-receipt.py --out /etc/nuxel/mfc/safety-receipt.json \
      --decoder-node /dev/video6 --firmware /lib/firmware/mfc_fw.bin \
      --owner-approve --kernel-patch-applied --firmware-installed \
      --missing-firmware-test PASS
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

SOURCE_COMMIT = "f7194c1d15eded1c2a1a4dc63825b26103435cc0"
FW_SHA = "f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f"
FW_SIZE = 685832


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="nuxel-mfc-safety-receipt.py")
    ap.add_argument("--print-template", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--decoder-node", default="/dev/video6")
    ap.add_argument("--firmware", default="/lib/firmware/mfc_fw.bin")
    ap.add_argument("--owner-approve", action="store_true")
    ap.add_argument("--approved-by")
    ap.add_argument("--kernel-patch-applied", action="store_true")
    ap.add_argument("--firmware-installed", action="store_true")
    ap.add_argument("--missing-firmware-test", choices=["NOT_RUN", "PASS", "SOURCE_PASS"], default="NOT_RUN")
    ap.add_argument("--decode-verified", action="store_true")
    ap.add_argument("--decode-evidence")
    args = ap.parse_args(argv)

    if args.print_template:
        print(json.dumps({
            "schema": "nuxel.mfc.safety-receipt/1",
            "owner_approved": False,
            "source_commit": SOURCE_COMMIT,
            "device": "beyond2lte",
            "decoder_node": "/dev/video6",
            "platform_device": "188d0000.mfc",
            "driver": "s5p-mfc",
            "compatible": "samsung,exynos-mfc",
            "ip_ver": "0x1300",
            "firmware_name": "mfc_fw.bin",
            "firmware_sha256": FW_SHA,
            "kernel_patch": "0008-mfc-firmware-fail-closed.patch",
            "kernel_patch_applied": False,
            "firmware_installed": False,
            "missing_firmware_test": "NOT_RUN",
            "decode_verified": False,
        }, indent=2, sort_keys=True))
        return 0

    if not args.out:
        print("error: --out is required (or use --print-template)", file=sys.stderr)
        return 2
    if not args.owner_approve:
        print("error: refusing to write a receipt without --owner-approve", file=sys.stderr)
        return 2
    if not args.kernel_patch_applied:
        print("error: refusing to write a receipt without --kernel-patch-applied", file=sys.stderr)
        return 2
    if not os.path.isfile(args.firmware):
        print("error: firmware missing: %s" % args.firmware, file=sys.stderr)
        return 2
    actual = sha256(args.firmware)
    if actual != FW_SHA or os.path.getsize(args.firmware) != FW_SIZE:
        print("error: firmware hash/size mismatch: %s size=%d" % (actual, os.path.getsize(args.firmware)),
              file=sys.stderr)
        return 2
    evidence = None
    if args.decode_verified:
        if not args.decode_evidence or not os.path.isfile(args.decode_evidence):
            print("error: --decode-verified requires an existing --decode-evidence file", file=sys.stderr)
            return 2
        evidence = {
            "path": os.path.abspath(args.decode_evidence),
            "sha256": sha256(args.decode_evidence),
            "firmware_sha256": FW_SHA,
        }
    doc = {
        "schema": "nuxel.mfc.safety-receipt/1",
        "owner_approved": True,
        "approved_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "approved_by": args.approved_by,
        "source_commit": SOURCE_COMMIT,
        "device": "beyond2lte",
        "decoder_node": args.decoder_node,
        "platform_device": "188d0000.mfc",
        "driver": "s5p-mfc",
        "compatible": "samsung,exynos-mfc",
        "ip_ver": "0x1300",
        "firmware_name": "mfc_fw.bin",
        "firmware_sha256": FW_SHA,
        "firmware_installed": bool(args.firmware_installed),
        "kernel_patch": "0008-mfc-firmware-fail-closed.patch",
        "kernel_patch_applied": True,
        "missing_firmware_test": args.missing_firmware_test,
        "decode_verified": bool(args.decode_verified),
        "decode_verified_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
            if args.decode_verified else None,
        "decode_evidence": evidence,
        "capabilities": [],
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    tmp = args.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, sort_keys=True)
        f.write("\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, args.out)
    print("wrote %s (owner_approved=true, decode_verified=%s)" % (args.out, doc["decode_verified"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

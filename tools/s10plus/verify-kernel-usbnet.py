#!/usr/bin/env python3
"""Fail-closed USBNET preservation gate for the combined S10+ kernel.

The NFC rebuild must not silently regress PWNAGE-107000:
  * ECM / ECM-subset / EEM gadget functions and their configfs options are y;
  * NAT / masquerade for USB tethering is y;
  * the NCM idempotent-misc_deregister patch is still in the built source;
  * the linked objects exist, so a compile race cannot drop a function.

Usage: verify-kernel-usbnet.py --build kernel/s10plus/.build/out [--json]
       verify-kernel-usbnet.py --config FILE --build DIR
Exit: 0 pass, 1 gate failure, 2 unusable inputs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC = os.path.join(ROOT, "kernel", "s10plus", ".build", "src")
GADGET = os.path.join(SRC, "drivers", "usb", "gadget", "function")

REQUIRED = (
    "CONFIG_USB_CONFIGFS",
    "CONFIG_USB_CONFIGFS_ECM",
    "CONFIG_USB_CONFIGFS_ECM_SUBSET",
    "CONFIG_USB_CONFIGFS_EEM",
    "CONFIG_USB_F_ECM",
    "CONFIG_USB_F_EEM",
    "CONFIG_USB_F_SUBSET",
    "CONFIG_NF_CONNTRACK",
    "CONFIG_NF_NAT",
    "CONFIG_NF_NAT_MASQUERADE_IPV4",
    "CONFIG_IP_NF_NAT",
    "CONFIG_IP_NF_TARGET_MASQUERADE",
)


def parse_config(path):
    out = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            m = re.match(r"^#\s*(CONFIG_[A-Za-z0-9_]+)\s+is not set$", line)
            if m:
                out[m.group(1)] = "n"
                continue
            m = re.match(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$", line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def check_ncm_patch():
    path = os.path.join(GADGET, "f_ncm.c")
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError as exc:
        return False, "f_ncm.c unreadable: %s" % exc
    # Two accepted shapes for the idempotent NCM teardown guard:
    #
    #  (a) the historical single flag `mirrorlink_registered`, set only on a
    #      successful misc_register() and tested in ncm_function_cleanup();
    #  (b) the later reference-counted singleton (`mirrorlink_active` +
    #      `mirrorlink_users` under mirrorlink_lock/mirrorlink_txn), which
    #      clears mirrorlink_active before the single misc_deregister() and so
    #      can never deregister a device that was not registered.  This is the
    #      shape in the current patch 0011 and is strictly safer for multiple
    #      concurrently-torn-down configfs instances.
    shapes = {
        "mirrorlink_registered": [
            "static bool mirrorlink_registered",
            "if (mirrorlink_registered)",
            "mirrorlink_registered = true",
            "mirrorlink_registered = false",
        ],
        "mirrorlink_active": [
            "static bool mirrorlink_active",
            "mirrorlink_active = true",
            "mirrorlink_active = false",
            "if (dev && mirrorlink_device.this_device)",
        ],
    }
    results = {}
    for name, guards in shapes.items():
        results[name] = all(g in text for g in guards)
    if any(results.values()):
        return True, ("NCM teardown guard present (%s)" % ", ".join(
            sorted(k for k, v in results.items() if v)))
    missing = [g for guards in shapes.values() for g in guards if g not in text]
    return False, "NCM teardown guard missing: " + ", ".join(sorted(set(missing)))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="verify-kernel-usbnet.py")
    ap.add_argument("--build", default=os.path.join(ROOT, "kernel", "s10plus", ".build", "out"))
    ap.add_argument("--config")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    build = os.path.abspath(args.build)
    cfg_path = args.config or os.path.join(build, ".config")
    if not os.path.isfile(cfg_path):
        print("missing config: %s" % cfg_path, file=sys.stderr)
        return 2
    cfg = parse_config(cfg_path)
    failures = []
    for sym in REQUIRED:
        if cfg.get(sym) != "y":
            failures.append("%s is %r (required =y)" % (sym, cfg.get(sym)))

    objects = [
        os.path.join(build, "drivers", "usb", "gadget", "function", name)
        for name in ("f_ecm.o", "f_eem.o", "f_subset.o", "f_ncm.o")
    ]
    for obj in objects:
        if not os.path.isfile(obj):
            failures.append("missing built gadget object: %s" % obj)
    ncm_ok, ncm_detail = check_ncm_patch()
    if not ncm_ok:
        failures.append(ncm_detail)
    netfilter = os.path.join(build, "net", "netfilter")
    if not os.path.isdir(netfilter):
        failures.append("missing built netfilter tree: %s" % netfilter)

    result = {"verdict": "PASS" if not failures else "FAIL",
              "config": cfg_path, "ncm_patch": ncm_ok, "failures": failures}
    if args.json:
        print(json.dumps(result, indent=2))
    elif not args.quiet:
        for sym in REQUIRED:
            print("[%s] %s=%s" % ("ok" if cfg.get(sym) == "y" else "FAIL", sym, cfg.get(sym)))
        print("[%s] %s" % ("ok" if ncm_ok else "FAIL", ncm_detail))
    if failures:
        for f in failures:
            print("::error::usbnet gate: %s" % f, file=sys.stderr)
        return 1
    if not args.quiet:
        print("kernel USBNET: PASS — ECM/ECM-subset/EEM/NAT and NCM fix present")
    return 0


if __name__ == "__main__":
    sys.exit(main())

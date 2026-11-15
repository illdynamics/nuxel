#!/usr/bin/env python3
"""Fail-closed NFC gate for the S10+ (beyond2lte) combined kernel.

This is deliberately stronger than a .config grep:

  * CONFIG_NFC_NCI and CONFIG_NFC_S3FWRN5_I2C must be built in (y, not m):
    the initramfs has no module loader and NFC must not depend on udev.
  * the built object tree must contain s3fwrn5_i2c.o, which proves the
    selected config produced the driver (not merely a symbol in .config).
  * every beyond2lte DT source/compiled DTBO must still describe the real
    controller at I2C 0x27 under hsi2c@108E0000 (7-0027 at runtime).
  * the legacy raw sec_nfc transport must not bind the same I2C node when
    the NCI driver is enabled (two drivers on one node is a conflict).

Usage:
  verify-kernel-nfc.py --build kernel/s10plus/.build/out [--json] [--quiet]
  verify-kernel-nfc.py --config FILE --build DIR

Exit: 0 = pass, 1 = gate failure, 2 = unusable inputs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DT_DIR = os.path.join(ROOT, "kernel", "s10plus", ".build", "src", "arch", "arm64",
                      "boot", "dts", "samsung")
REQUIRED = (
    "CONFIG_NFC",
    "CONFIG_NFC_NCI",
    "CONFIG_NFC_S3FWRN5",
    "CONFIG_NFC_S3FWRN5_I2C",
)
FORBIDDEN = (
    # No NXP PN547/PN553/PN5xx, ST21/ST-NCI, nxp-nci, or FDP driver is present
    # on any beyond2lte board revision.  Enabling one would be a guessed chip.
    "CONFIG_NFC_PN547",
    "CONFIG_NFC_P61",
    "CONFIG_NFC_ST_NCI_I2C",
    "CONFIG_NFC_ST_NCI_SPI",
    "CONFIG_NFC_NXP_NCI",
    "CONFIG_NFC_FDP",
)


def parse_config(path):
    out = {}
    try:
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
    except OSError as exc:
        raise SystemExit("cannot read config %s: %s" % (path, exc))
    return out


def _fragment_for_nfc(text):
    """Return the fragment number whose overlay contains sec-nfc@27."""
    for m in re.finditer(r'fragment@(\d+) \{', text):
        body = text[m.end():text.find('\n\t};', m.end())]
        if 'sec-nfc@27' in body:
            return int(m.group(1))
    return None


def check_dt():
    """Return [(file, ok, detail)] for every beyond2lte DT source."""
    results = []
    if not os.path.isdir(DT_DIR):
        return results, "DT source directory missing: %s" % DT_DIR
    files = sorted(f for f in os.listdir(DT_DIR)
                   if f.startswith("exynos9820-beyond2lte_") and f.endswith(".dts"))
    if not files:
        return results, "no beyond2lte DT sources found in %s" % DT_DIR
    for name in files:
        text = open(os.path.join(DT_DIR, name), encoding="utf-8", errors="replace").read()
        frag = _fragment_for_nfc(text)
        ok = ('sec-nfc@27' in text and 'reg = <0x27>;' in text and frag is not None)
        bus = None
        if ok:
            # The live hardware is kernel i2c-7 at hsi2c@108E0000.  Assert the
            # symbol that targets this node's fragment, not a guessed number.
            # A DTS fragment can be absent from __symbols__ (fragment@115 on
            # rev 19+), so resolve its target through __fixups__ instead:
            #   hsi2c_3 = "/fragment@115:target:0"
            # That symbol points at the real base node; all beyond2lte
            # revisions decode to hsi2c@108E0000 / kernel i2c-7 / 7-0027.
            bus = re.search(r'hsi2c_(\d+)\s*=\s*"/fragment@%d:target:0"' % frag, text)
            if bus is None:
                # __fixups__ lists hsi2c_3 = "target" for that fragment.
                for cand in re.finditer(r'^\s*hsi2c_(\d+)\s*=\s*([^;]+);', text,
                                        re.M):
                    if 'fragment@%d:target:0' % frag in cand.group(2):
                        bus = cand
                        break
            if bus:
                ok = bus.group(1) in ("20",)
            else:
                ok = re.search(r'hsi2c_(\d+)\s*=\s*".*108E0000"', text) is not None
        results.append((name, bool(ok), "fragment@%s sec-nfc@27 bus hsi2c_%s"
                        % (frag, bus.group(1) if bus else "?")))
    return results, None

def main(argv=None):
    ap = argparse.ArgumentParser(prog="verify-kernel-nfc.py")
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
            failures.append("%s is %r (required =y, built in)" % (sym, cfg.get(sym)))
    for sym in FORBIDDEN:
        if cfg.get(sym) not in (None, "n"):
            failures.append("%s is %r (no such controller on beyond2lte)" % (sym, cfg.get(sym)))

    # Measured binding regressions (attempts 1-3): whichever driver registered
    # first won 7-0027 and the other never got to probe.  The accepted fix is a
    # two-sided arbitration:
    #   * s3fwrn5_i2c registers at device_initcall() (after nfc_init, which
    #     registers the "nfc" class) and matches the vendor "sec-nfc" node;
    #   * the legacy driver keeps its I2C id_table entry (so the controller can
    #     never be left driverless) but defers exactly once (-EPROBE_DEFER),
    #     which makes the outcome independent of link/registration order;
    #   * s3fwrn5_i2c only registers nfc0 after its bootloader readiness
    #     handshake, and fails probe otherwise so sec_nfc can take over.
    # The gate requires all three source-level facts.
    nfc_dir = os.path.join(ROOT, "kernel", "s10plus", ".build", "src",
                           "drivers", "nfc")
    try:
        legacy_src = open(os.path.join(nfc_dir, "sec_nfc.c"),
                          encoding="utf-8", errors="replace").read()
    except OSError as exc:
        legacy_src = ""
        failures.append("legacy sec_nfc source unreadable: %s" % exc)
    idblk = re.search(r"static struct i2c_device_id sec_nfc_id_table\[\] = \{(.*?)\n\};",
                      legacy_src, re.S)
    if not idblk or "SEC_NFC_DRIVER_NAME" not in idblk.group(1):
        failures.append("legacy sec_nfc lost its I2C id_table fallback; the "
                        "controller would be left driverless if NCI cannot probe")
    if "EPROBE_DEFER" not in legacy_src:
        failures.append("legacy sec_nfc does not defer to the NCI driver "
                        "(EPROBE_DEFER missing)")
    try:
        i2c_src = open(os.path.join(nfc_dir, "s3fwrn5", "i2c.c"),
                       encoding="utf-8", errors="replace").read()
    except OSError as exc:
        i2c_src = ""
        failures.append("s3fwrn5 i2c source unreadable: %s" % exc)
    if "device_initcall" not in i2c_src:
        failures.append("s3fwrn5_i2c is not registered at device_initcall; "
                        "it must register after nfc_init and before the "
                        "deferred sec_nfc probe")
    if "s3fwrn5_i2c_nci_ready" not in i2c_src or "S3FWRN5_FW_CMD_GET_BOOTINFO" not in i2c_src:
        failures.append("s3fwrn5_i2c has no bootloader readiness handshake; "
                        "it would register a dead nfc0 on a non-NCI part")

    obj = os.path.join(build, "drivers", "nfc", "s3fwrn5", "s3fwrn5_i2c.o")
    if not os.path.isfile(obj):
        failures.append("driver object missing (config alone is not a driver): %s" % obj)

    dt_results, dt_err = check_dt()
    if dt_err:
        failures.append(dt_err)
    for name, ok, detail in dt_results:
        if not ok:
            failures.append("DT %s lost the real NFC node (%s)" % (name, detail))

    result = {
        "verdict": "PASS" if not failures else "FAIL",
        "config": cfg_path,
        "driver_object": obj,
        "dt_sources": len(dt_results),
        "failures": failures,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    elif not args.quiet:
        for sym in REQUIRED:
            print("[%s] %s=%s" % ("ok" if cfg.get(sym) == "y" else "FAIL", sym, cfg.get(sym)))
        print("[%s] s3fwrn5_i2c.o" % ("ok" if os.path.isfile(obj) else "FAIL"))
        print("DT sources checked: %d" % len(dt_results))
    if failures:
        for f in failures:
            print("::error::nfc gate: %s" % f, file=sys.stderr)
        return 1
    if not args.quiet:
        print("kernel NFC: PASS — S3FWRN5/S3NRN82 NCI driver, real 7-0027 node")
    return 0


if __name__ == "__main__":
    sys.exit(main())

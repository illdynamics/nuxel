#!/usr/bin/env python3
"""Fail-closed parity gate: does the built kernel config match the live phone?

PWNAGE-48000..54000 depend on kernel capabilities that the stock
exynos9820-beyond2lte defconfig does not enable (DRM core, UDMABUF, kbase
Bifrost, user namespaces, NFC, SECCOMP filtering).  A release built without the
`nuxel-drm-kbase.fragment` therefore compiles and packages fine but is NOT the
kernel running on the owner's handset.

This tool compares a built `.config` against
`kernel/s10plus/configs/live-required.config` and exits non-zero on any
mismatch or missing symbol.  It is used by the release workflow as a hard gate.

Usage:
  python3 tools/s10plus/verify-kernel-config.py --config kernel/s10plus/.build/out/.config
  python3 tools/s10plus/verify-kernel-config.py --config /tmp/live.config --json

Exit: 0 = every required capability present, 1 = mismatch, 2 = bad input.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DEFAULT_REQUIRED = os.path.join(ROOT, "kernel", "s10plus", "configs", "live-required.config")


def parse_config(path):
    """Return {symbol: value} where value is the string after '=' or 'n'."""
    out = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                m = re.match(r"^#\s*(CONFIG_[A-Za-z0-9_]+)\s+is not set$", line)
                if m:
                    out[m.group(1)] = "n"
                continue
            m = re.match(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$", line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def parse_required(path):
    """Return [(symbol, expected)] from the required-capability file."""
    req = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$", line)
            if not m:
                raise SystemExit("bad line in %s: %r" % (path, raw.rstrip()))
            req.append((m.group(1), m.group(2)))
    return req


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="verify-kernel-config.py")
    ap.add_argument("--config", required=True, help="built kernel .config")
    ap.add_argument("--required", default=DEFAULT_REQUIRED)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.config):
        print("missing config: %s" % args.config, file=sys.stderr)
        return 2
    if not os.path.isfile(args.required):
        print("missing requirements: %s" % args.required, file=sys.stderr)
        return 2

    built = parse_config(args.config)
    req = parse_required(args.required)

    checks, failures = [], []
    for symbol, expected in req:
        actual = built.get(symbol)
        ok = actual == expected
        checks.append({"symbol": symbol, "expected": expected, "actual": actual, "ok": ok})
        if not ok:
            failures.append((symbol, expected, actual))

    if args.json:
        print(json.dumps({
            "verdict": "PASS" if not failures else "FAIL",
            "config": args.config,
            "required": len(req),
            "failures": [{"symbol": s, "expected": e, "actual": a} for s, e, a in failures],
        }, indent=2))
    elif not args.quiet:
        for c in checks:
            status = "ok  " if c["ok"] else "FAIL"
            print("  [%s] %s = %s%s" % (status, c["symbol"], c["actual"],
                                        "" if c["ok"] else "  (required %s)" % c["expected"]))
        print("kernel config: %d/%d required capabilities present"
              % (len(req) - len(failures), len(req)))

    if failures:
        for symbol, expected, actual in failures:
            print("::error::kernel config %s is %s, required %s (not the live handset kernel)"
                  % (symbol, actual if actual is not None else "absent", expected),
                  file=sys.stderr)
        return 1
    print("kernel config: PASS — matches the live S10+ capability set")
    return 0


if __name__ == "__main__":
    sys.exit(main())

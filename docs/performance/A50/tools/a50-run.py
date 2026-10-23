#!/usr/bin/env python3
"""A50 read-only console runner.

Reuses tools/beta/live/nuxel_live.py (capability discovery + framed, SHA-256
verified commands + single-owner port lock). Runs a sequence of short, bounded,
read-only commands against the live Nuxel S10+ and prints verified results.

Usage:
  python3 a50-run.py 'uname -a' 'cat /proc/cmdline'
  python3 a50-run.py --file probes.txt            # name<TAB>command per line
  python3 a50-run.py --dev /dev/cu.usbmodem201 -- 'systemctl --failed'

Never writes to the device, a partition, kernel/bootloader, or flash tooling.
"""
from __future__ import annotations
import argparse, os, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(REPO, "tools", "beta", "live"))
import nuxel_live as nl  # noqa: E402


def load_probes(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if "\t" in line:
                name, _, cmd = line.partition("\t")
                out.append((name.strip(), cmd.strip()))
            else:
                out.append((line.strip(), line.strip()))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("commands", nargs="*")
    ap.add_argument("--file", default=None)
    ap.add_argument("--dev", default=None)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.file:
        probes = load_probes(args.file)
    else:
        probes = [(c, c) for c in args.commands]
    if not probes:
        ap.error("no commands supplied")

    con, node, notes = nl.open_console(dev=args.dev, timeout=args.timeout)
    results = []
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with con:
        for name, cmd in probes:
            r = con.run(cmd, timeout=args.timeout)
            results.append({"name": name, "command": cmd, "result": r.as_dict(),
                            "output": r.output})
            if args.json:
                continue
            print("=" * 72)
            print("### %s  [rc=%s framed=%s sha_ok=%s elapsed=%.3fs]" %
                  (name, r.rc, r.framed, r.sha_ok, r.elapsed))
            print(r.output.rstrip("\n"))
    if args.json:
        import json
        print(json.dumps({"at": started, "node": node, "results": results},
                         indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

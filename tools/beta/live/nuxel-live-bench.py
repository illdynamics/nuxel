#!/usr/bin/env python3
"""nuxel-live-bench — measure the live-console transfer path safely.

This tool NEVER installs or activates anything.  It writes a benchmark artifact
under /var/tmp on the device, verifies its SHA-256, records acknowledged-block
metrics, and removes its temporary files.  It holds the same shared flock as the
deploy/console tools for the duration of the measurement, so it is the only
writer on the physical serial stream.

Examples:
  python3 tools/beta/live/nuxel-live-bench.py --mode block
  python3 tools/beta/live/nuxel-live-bench.py --mode frame --source /path/to/file
  python3 tools/beta/live/nuxel-live-bench.py --mode both --block-lines 4
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nuxel_live as nl  # noqa: E402


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _bench_one(con, data, source, mode, args, op_id):
    name = os.path.basename(source).replace("/", "_")
    target = "/var/tmp/nxl-bench/%s.%s.%d" % (name, mode, os.getpid())
    progress_events = []

    def progress(ev):
        progress_events.append(dict(ev))

    t0 = time.monotonic()
    if mode == "block":
        res = nl.block_push_bytes(
            con, data, target, mode="0644", chunk=args.chunk,
            block=args.block_lines, max_block_bytes=args.block_bytes,
            resume=not args.no_resume, progress=progress,
            cancel_check=lambda: False)
    else:
        res = nl.push_bytes(con, data, target, chunk=args.chunk,
                            mode="0644", progress=progress,
                            cancel_check=lambda: False)
    elapsed = time.monotonic() - t0
    check = con.run("sha256sum %s 2>/dev/null | cut -d' ' -f1" % target,
                    timeout=con.timeout)
    got = check.output.strip().split()[0] if check.ok and check.output.strip() else None
    want = _sha(data)
    ok = bool(got == want)
    try:
        con.run("rm -f %s %s.*" % (target, target), timeout=con.timeout)
    except nl.ConsoleLost:
        pass
    acked = int(res.get("acked_bytes", 0))
    return {
        "mode": mode,
        "source": source,
        "bytes": len(data),
        "sha256": want,
        "device_sha256": got,
        "hash_ok": ok,
        "elapsed_s": round(elapsed, 3),
        "transport_elapsed_s": res.get("elapsed_s"),
        "throughput_bytes_s": round(len(data) / elapsed, 1) if elapsed else None,
        "acked_bytes": acked,
        "parts": res.get("parts"),
        "frames": res.get("frames"),
        "blocks": res.get("blocks"),
        "raw_writes": res.get("raw_writes"),
        "ack_writes": res.get("ack_writes"),
        "write_bytes": res.get("write_bytes"),
        "retries": res.get("retries"),
        "resume_used": res.get("resume_used", False),
        "resumed_b64_chars": res.get("resumed_b64_chars", 0),
        "fallback": res.get("fallback", False),
        "block_error": res.get("block_error"),
        "progress_events": len(progress_events),
        "last_progress": progress_events[-1] if progress_events else None,
        "target": target,
        "op": op_id,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="measure, never install, live-console transfer")
    ap.add_argument("--source", default="services/nuxel-bridge/src/bridge.py")
    ap.add_argument("--mode", choices=("block", "frame", "both"), default="block")
    ap.add_argument("--dev", default=None)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--lock-wait", type=float, default=30.0)
    ap.add_argument("--block-lines", type=int, default=8)
    ap.add_argument("--block-bytes", type=int, default=3072)
    ap.add_argument("--chunk", type=int, default=None,
                    help="base64 chars per line (default: measured 380)")
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    repo = nl.repo_root_from_here()
    source = args.source if os.path.isabs(args.source) else os.path.join(repo, args.source)
    with open(source, "rb") as fh:
        data = fh.read()
    op_id = "bench-%s-%d" % (time.strftime("%Y%m%dT%H%M%S"), os.getpid())
    try:
        node = ({"callout": args.dev, "match_stage": "explicit"} if args.dev
                else nl.select_console_node(nl.enumerate_console_nodes()))
    except nl.SelectionError as e:
        print("# benchmark: %s" % e, file=sys.stderr)
        return 3

    results = []
    try:
        with nl.Console(node["callout"], timeout=args.timeout,
                        lock_wait=args.lock_wait, op_id=op_id) as con:
            probe = con.probe(6.0)
            if not probe.reachable:
                print("# benchmark: console is byte-silent", file=sys.stderr)
                return 3
            boot = con.run("cat /proc/sys/kernel/random/boot_id 2>/dev/null")
            modes = ("block", "frame") if args.mode == "both" else (args.mode,)
            for mode in modes:
                try:
                    results.append(_bench_one(con, data, source, mode, args, op_id))
                except nl.ConsoleLost as e:
                    results.append({"mode": mode, "source": source,
                                    "bytes": len(data), "error": str(e),
                                    "hash_ok": False})
    except nl.ConsoleLost as e:
        print("# benchmark: cannot use console: %s" % e, file=sys.stderr)
        return 3

    doc = {"operation_id": op_id, "device": node["callout"],
           "boot_id": boot.output.strip() if boot.ok else None,
           "probe": probe.as_dict(), "source": source,
           "source_sha256": _sha(data), "bytes": len(data),
           "results": results}
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
    else:
        print("# nuxel-live-bench %s (%d bytes)" % (os.path.basename(source), len(data)))
        for r in results:
            if r.get("error"):
                print("# %s: ERROR %s" % (r["mode"], r["error"]))
                continue
            print("# %s: %s bytes in %.3fs = %.1f B/s; parts=%s blocks=%s "
                  "raw_writes=%s acks=%s retries=%s hash=%s"
                  % (r["mode"], r["bytes"], r["elapsed_s"],
                     r["throughput_bytes_s"], r["parts"], r["blocks"],
                     r["raw_writes"], r["ack_writes"], r["retries"],
                     "OK" if r["hash_ok"] else "MISMATCH"))
    return 0 if all(r.get("hash_ok") for r in results) else 5


if __name__ == "__main__":
    raise SystemExit(main())

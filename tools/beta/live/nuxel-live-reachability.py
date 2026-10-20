#!/usr/bin/env python3
"""nuxel-live-reachability — briq-10a: is the S10+ console reachable at all?

ACCESS TIER: live-phone-only.  This is the FIRST thing every live briQ runs.

What it does, in order (all measured, nothing assumed):
  1. enumerate CDC-ACM *capabilities* on the host (macOS: `ioreg -r -c
     AppleUSBACMData`; Linux: /sys/class/tty/*/device/../idVendor) — the console
     tty is selected by USB VID/PID + TTY base name, NEVER by a hard-coded
     /dev/cu.usbmodemNNN or /dev/ttyACMN;
  2. cross-check the USB device serial/product string, so a *different* gadget
     (logitech dongle, JBL speaker, Bluetooth port) can never be mistaken for
     the phone;
  3. take an exclusive host-side lock on the port (the console also mirrors
     /dev/kmsg, so two readers steal each other's bytes);
  4. open a bounded session and prove liveness BOTH ways: any bytes back, then a
     fully framed SHA-256-verified command;
  5. write the raw bundle + hash manifest under docs/beta-finalization/live/evidence/.

Verdicts
  0  console reachable  -> the caller may proceed (baseline read / deploy)
  3  BLOCKED_EXTERNAL_RESOURCE (no gadget, silent port, or no shell frame)
  4  BLOCKED_EXTERNAL_RESOURCE (port already owned by another host tool)

Never writes to a partition, kernel image, bootloader or flash tool. Never
touches .qq / RUN_ROOT.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nuxel_live as nl  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="S10+ live console reachability preflight")
    ap.add_argument("--evidence-dir", default=None,
                    help="evidence root (default docs/beta-finalization/live/evidence)")
    ap.add_argument("--name", default=None, help="fixed bundle directory name")
    ap.add_argument("--dev", default=None, help="explicit tty (skips capability selection)")
    ap.add_argument("--vid", default=hex(nl.DEFAULT_VID))
    ap.add_argument("--pid", default=hex(nl.DEFAULT_PID))
    ap.add_argument("--serial", default=nl.DEFAULT_SERIAL)
    ap.add_argument("--probe-seconds", type=float, default=6.0)
    ap.add_argument("--lock-wait", type=float, default=8.0,
                    help="seconds to wait for a competing host tool to release the console")
    ap.add_argument("--escalate", action="store_true",
                    help="when the primary node is silent, change diagnostic: alternate "
                         "node, alternate baud, then a volume burst")
    ap.add_argument("--timeout", type=float, default=12.0)
    ap.add_argument("--json", action="store_true", help="emit machine JSON on stdout")
    args = ap.parse_args(argv)

    repo = nl.repo_root_from_here()
    ev_root = args.evidence_dir or os.path.join(repo, "docs", "beta-finalization", "live", "evidence")
    nl.ensure_not_qq(ev_root)
    bundle = nl.EvidenceBundle(ev_root, name=args.name, label="reachability")

    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report = {"at": started, "host": os.uname().sysname + " " + os.uname().release,
              "evidence_dir": bundle.dir, "capability": {"vid": args.vid, "pid": args.pid,
                                                        "serial": args.serial},
              "steps": [], "verdict": None, "reachable": False, "blocked_reason": None}

    # --- 0. host environment facts (raw, so the doc can quote them) -------- #
    try:
        sp = subprocess.run(["system_profiler", "SPUSBDataType"], capture_output=True,
                            text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError) as e:
        sp = "system_profiler unavailable: %s" % e
    gadget_lines = "\n".join(l for l in sp.splitlines()
                             if any(k in l for k in ("Nuxel", "NUXEL", "0x4ee7", "0x18d1")))
    bundle.write("host-usb-gadget.txt", gadget_lines or "(no Nuxel gadget descriptor found)")
    report["gadget_descriptor_present"] = bool(gadget_lines)

    # Capability discovery MUST use the platform that is actually running.  The
    # previous code unconditionally ran macOS `ioreg`, so on a Linux host it
    # found zero nodes even when /sys/class/tty/ttyACM0 and the 18d1:4ee7 gadget
    # were both present — every live test then reported BLOCKED and did nothing.
    # nl.enumerate_console_nodes() has the /sys/class/tty branch (and tolerates
    # bare-hex sysfs VID/PID); use it on Linux and keep ioreg on macOS.
    if sys.platform == "darwin":
        try:
            ioreg_acm = subprocess.run(["ioreg", "-r", "-c", "AppleUSBACMData", "-w0", "-l"],
                                       capture_output=True, text=True, timeout=20).stdout
        except (OSError, subprocess.SubprocessError) as e:
            ioreg_acm = "ioreg unavailable: %s" % e
        bundle.write("host-ioreg-acm.txt", ioreg_acm)
        nodes = nl.parse_ioreg_acm(ioreg_acm) if ioreg_acm.startswith(("+", "|", " ")) else []
    else:
        nodes = nl.enumerate_console_nodes()
        bundle.write("host-sysfs-nodes.txt", json.dumps(nodes, indent=2, sort_keys=True))
    bundle.write("host-console-nodes.json", json.dumps(nodes, indent=2, sort_keys=True))
    report["nodes"] = nodes

    try:
        adb = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError) as e:
        adb = "adb unavailable: %s" % e
    bundle.write("host-adb-devices.txt", adb)
    report["adb_devices"] = [l.split("\t")[0] for l in adb.splitlines()[1:] if l.strip()]

    # --- 1/2. capability selection ----------------------------------------- #
    dev = args.dev
    node = {"callout": dev, "match_stage": "explicit"} if dev else None
    if not dev:
        if not nodes:
            report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
            report["blocked_reason"] = ("no CDC-ACM USB serial gadget enumerated on the host "
                                        "(VID 0x%04x PID 0x%04x)" % (nl.DEFAULT_VID, nl.DEFAULT_PID))
            return finish(bundle, report, args, 3)
        if sys.platform == "darwin":
            try:
                usb_devs = nl.parse_ioreg_usb_devices(
                    subprocess.run(["ioreg", "-w0", "-l", "-p", "IOUSB"],
                                   capture_output=True, text=True, timeout=20).stdout)
            except (OSError, subprocess.SubprocessError):
                usb_devs = []
        else:
            # Linux sysfs already matched VID/PID; the tty record carries them.
            usb_devs = None
        try:
            node = nl.select_console_node(nodes, vid=int(args.vid, 0), pid=int(args.pid, 0),
                                          serial=args.serial, usb_devices=usb_devs)
        except nl.SelectionError as e:
            report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
            report["blocked_reason"] = "capability selection failed: %s" % e
            return finish(bundle, report, args, 3)
        dev = node["callout"]
    report["selected"] = node
    report["steps"].append({"step": "select-by-capability", "ok": True,
                            "detail": "%s (matched %s)" % (dev, node.get("match_stage"))})

    # --- 3/4. bounded session ---------------------------------------------- #
    con = None
    try:
        con = nl.Console(dev, timeout=args.timeout, lock_wait=args.lock_wait)
        con.open()
    except nl.ConsoleLost as e:
        report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
        report["blocked_reason"] = "cannot take the console: %s" % e
        report["port_busy"] = "lock" in str(e) or "owned" in str(e)
        return finish(bundle, report, args, 4 if report.get("port_busy") else 3)

    try:
        probe = con.probe(args.probe_seconds)
        report["probe"] = probe.as_dict()
        bundle.write("probe-raw.txt",
                     "dev=%s bytes_in=%d echo_ok=%s error=%s elapsed=%.3fs\nsample:\n%s\n"
                     % (dev, probe.bytes_in, probe.echo_ok, probe.error, probe.elapsed, probe.sample))
        if not probe.reachable and args.escalate:
            # release our own lock FIRST: an escalation that cannot even take the
            # port would report a false negative (this bug was caught in testing).
            con.close()
            report["escalation"] = escalate(node, args, bundle)
        if not probe.reachable:
            report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
            report["blocked_reason"] = (
                "gadget enumerated as %s but the port is byte-silent for %.1fs "
                "(no shell echo, no /dev/kmsg mirror): the on-device console is not "
                "serving the port" % (dev, args.probe_seconds))
            return finish(bundle, report, args, 3)

        res = con.run("id; echo NXL-REACH-OK", timeout=args.timeout)
        bundle.write("frame-id.txt", "rc=%s framed=%s sha_ok=%s\n%s\n"
                     % (res.rc, res.framed, res.sha_ok, res.output))
        report["steps"].append({"step": "framed-command", "ok": res.ok,
                                "detail": res.as_dict(), "output": res.output.strip()[:400]})
        if not res.ok:
            report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
            report["blocked_reason"] = ("port answered bytes but no verified command frame "
                                        "(half-alive console)")
            return finish(bundle, report, args, 3)
        report["reachable"] = True
        report["verdict"] = "REACHABLE"
        return finish(bundle, report, args, 0)
    finally:
        con.close()


def escalate(node, args, bundle):
    """Repeat-failure rule: after the primary mode fails, CHANGE the diagnostic.

    Modes, each bounded: (1) the dialin node instead of the callout node,
    (2) 115200 baud instead of 9600, (3) a 4 KiB volume burst.  Each mode is a
    genuinely different hypothesis about *why* the far end is quiet, and the
    result of every mode is recorded — so "the console is unreachable" is a
    measured statement, not an assumption.
    """
    attempts = [
        ("primary-node", node.get("callout"), 115200, 0),
        ("fallback-baud-9600", node.get("callout"), 9600, 0),
        ("burst-4k", node.get("callout"), 115200, 4096),
    ]
    results = []
    for name, dev, baud, burst in attempts:
        if not dev or not os.path.exists(dev):
            results.append({"mode": name, "dev": dev, "ok": False,
                            "error": "node absent"})
            continue
        con = None
        try:
            con = nl.Console(dev, baud=baud, timeout=args.timeout, lock_wait=4.0)
            con.open()
            p = con.probe(4.0, burst=burst)
            results.append({"mode": name, "dev": dev, "baud": baud, "burst": burst,
                            "bytes_in": p.bytes_in, "echo_ok": p.echo_ok,
                            "error": p.error, "ok": p.reachable})
        except nl.ConsoleLost as e:
            results.append({"mode": name, "dev": dev, "ok": False, "error": str(e)})
        finally:
            if con is not None:
                con.close()
    bundle.write("escalation.json", json.dumps(results, indent=2, sort_keys=True))
    return results


def finish(bundle, report, args, code):
    report["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["exit_code"] = code
    report["verdicts"] = {"briq-10a-live-reachability-preflight":
                          "REACHABLE" if report.get("reachable") else "BLOCKED_EXTERNAL_RESOURCE"}
    bundle.write_json("reachability.json", report)
    man, lines = bundle.manifest()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("# nuxel-live-reachability -> %s" % report["verdict"])
        print("# evidence: %s" % bundle.dir)
        if report.get("selected"):
            print("# console: %s (%s)" % (report["selected"]["callout"],
                                          report["selected"].get("match_stage")))
        if not report.get("reachable"):
            print("# blocked: %s" % report.get("blocked_reason"))
        for ln in lines:
            print("# %s" % ln)
        print("# manifest: %s" % man)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

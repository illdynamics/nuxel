#!/usr/bin/env python3
"""nuxel-live-baseline — briq-10a: A32 baseline capture from the running phone.

ACCESS TIER: live-phone-only (safe against the offline fake console too).

What it does, in order, and *only* this:
  1. capability-based reachability preflight (never a hard-coded tty node);
  2. if the console answers: read the A32 baseline through verified frames —
     uptime, /proc/cmdline + androidboot.mode, systemctl is-active for
     nuxel-wayland / nuxel-wl-fb / nuxel-button-manager / nuxel-touch-arm /
     seatd, systemctl --failed, /var/lib/nuxel/fb-owner,
     /var/lib/nuxel/animation, /run/nuxel-wl-fb.state, the sec_touchscreen entry
     in /proc/bus/input/devices, the ALSA card list (must show beyond-madera),
     sec_ts IRQ counts and the PWA file hashes;
  3. write the RAW bundle plus a SHA-256 manifest under
     docs/beta-finalization/live/evidence/<bundle>/;
  4. diff the snapshot against the recorded A32 baseline expectations and record
     every delta — a delta is a regression *signal*, never a silent pass.
  5. if the console is unreachable, write the exact measured failure and report
     BLOCKED_EXTERNAL_RESOURCE.  Nothing is invented.

Verdicts
  0  baseline read            -> DEPLOYED_UNVERIFIED (read-only, no hardware claim)
  3  console unreachable      -> BLOCKED_EXTERNAL_RESOURCE
Never writes to a partition, kernel image, bootloader or flash tool; never
touches .qq / RUN_ROOT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nuxel_live as nl  # noqa: E402

#: The A32 baseline floor.  Anything that differs is reported as a delta.
EXPECTED_BASELINE = {
    "units_active": ["nuxel-wayland", "nuxel-wl-fb", "nuxel-button-manager",
                     "nuxel-touch-arm", "seatd"],
    "fb_owner": "nuxel-wl-fb",
    "animation_receipt_required": True,
    "alsa_contains": "beyond-madera",
    "touch_device": "sec_touchscreen",
    "registry_http": "200",
    "failed_units_max": 0,
}

DEFAULT_PWA = ["pwa/nuxel-home/index.html", "pwa/nuxel-home/js/apps.js",
               "pwa/nuxel-home/js/qs.js", "pwa/nuxel-home/js/status-bar.js",
               "pwa/nuxel-home/js/safe-zones.js", "pwa/nuxel-home/manifest.json",
               "pwa/nuxel-home/sw.js"]


def pwa_list_from_manifest(repo):
    p = os.path.join(repo, "tools", "beta", "live", "deploy-manifest.json")
    try:
        man = json.load(open(p))
    except (OSError, ValueError):
        return list(DEFAULT_PWA)
    rel = []
    for g in man.get("groups", []):
        if g.get("id") == "launcher-pwa":
            for f in g.get("files", []):
                if f["source"].startswith("pwa/nuxel-home/"):
                    rel.append(f["source"])
    return rel or list(DEFAULT_PWA)


def host_pwa_hashes(repo, rels):
    out = {}
    for rel in rels:
        p = os.path.join(repo, rel)
        if os.path.isfile(p):
            out[rel] = nl.sha256_file(p)
    return out


def parse_units(text):
    d = {}
    for line in nl.clean_lines(text):
        if "=" in line:
            k, _, v = line.partition("=")
            d[k.strip()] = v.strip()
    return d


def parse_cmdline(text):
    d = {}
    for line in nl.clean_lines(text):
        for tok in line.split():
            if "=" in tok:
                k, _, v = tok.partition("=")
                d.setdefault(k, v)
    return d


def parse_irq(text):
    for line in nl.clean_lines(text):
        parts = line.split()
        if len(parts) >= 3 and "sec_ts" in line:
            try:
                return sum(int(x) for x in parts[1:3] if x.isdigit())
            except ValueError:
                return None
    return None


def snapshot(con, bundle, repo, rels):
    """Read the baseline through verified frames; return the structured dict."""
    # baseline_probes() prefixes every entry with the on-device docroot.  On the
    # handset that is /usr/share/nuxel (measured: /home/nuxel/nuxel does not
    # exist), so detect it once here and hash the bytes the phone actually serves.
    docroot = "/usr/share/nuxel"
    for cand in ("/usr/share/nuxel", "/home/nuxel/nuxel"):
        r = con.run("test -f %s/pwa/nuxel-home/index.html && echo YES || echo NO" % cand)
        if r.ok and "YES" in r.output:
            docroot = cand
            break
    probes = nl.baseline_probes(list(rels), docroot=docroot)
    raw, frames, pwa_dev = {}, [], {}
    for key, cmd in probes:
        res = con.run(cmd)
        raw[key] = {"rc": res.rc, "framed": res.framed, "sha_ok": res.sha_ok,
                    "output": res.output}
        frames.append({"key": key, "ok": res.ok, "rc": res.rc,
                       "elapsed_s": round(res.elapsed, 3)})
        body = res.output if res.ok else ""
        bundle.write("raw/%s.txt" % key.replace("/", "_").replace(":", "_"),
                     "cmd: %s\nok: %s rc: %s framed: %s sha_ok: %s\n---\n%s"
                     % (cmd, res.ok, res.rc, res.framed, res.sha_ok, body))
        if key.startswith("pwa_sha256:"):
            rel = key.split(":", 1)[1]
            dev = "pwa/nuxel-home/" + rel.split("pwa/nuxel-home/", 1)[-1]
            pwa_dev[dev] = body.split()[0] if body.split() else None

    # fb-owner is a durable key/value receipt, not a one-line sentinel.  The
    # schema header is deliberately first, so reading line zero produced a
    # permanent false regression even while the single owner was healthy.
    # Prefer the explicit owner= field and retain the legacy one-line format
    # used by the fake-console test fixture.
    fb_owner_lines = nl.clean_lines(raw["fb_owner"]["output"])
    fb_owner = next((line.split("=", 1)[1].strip() for line in fb_owner_lines
                     if line.startswith("owner=")),
                    fb_owner_lines[0] if fb_owner_lines else "")

    snap = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": "live console (verified frames)",
        "uptime_s": (nl.clean_lines(raw["uptime"]["output"]) or [""])[0],
        "kernel": (nl.clean_lines(raw["uname"]["output"]) or [""])[0],
        "hostname": (nl.clean_lines(raw["hostname"]["output"]) or [""])[0],
        "cmdline": (nl.clean_lines(raw["cmdline"]["output"]) or [""])[0],
        "cmdline_vars": parse_cmdline(raw["cmdline"]["output"]),
        "boot_mode": (nl.clean_lines(raw["boot_mode"]["output"]) or [""])[0],
        "units": parse_units(raw["units"]["output"]),
        "failed_units": [l for l in nl.clean_lines(raw["failed_units"]["output"])
                         if "loaded units listed" not in l],
        "fb_owner": fb_owner,
        "animation_receipt": (nl.clean_lines(raw["animation"]["output"]) or [""])[0],
        "wl_fb_state": (nl.clean_lines(raw["wl_fb_state"]["output"]) or [""])[0],
        "touch_devices": "\n".join(nl.clean_lines(raw["touch_devices"]["output"])),
        "alsa_cards": "\n".join(nl.clean_lines(raw["alsa_cards"]["output"])),
        "alsa_beyond_madera": (nl.clean_lines(raw["alsa_beyond_madera"]["output"]) or [""])[0],
        "irq_sec_ts_count": parse_irq(raw["irq_sec_ts"]["output"]),
        "registry_http_code": (nl.clean_lines(raw["http_registry"]["output"]) or [""])[0],
        "pwa_sha256_device": pwa_dev,
        "frames_ok": sum(1 for f in frames if f["ok"]),
        "frames_total": len(frames),
    }
    bundle.write_json("frames.json", frames)
    return snap


def deltas(snap, expected=EXPECTED_BASELINE):
    """Compare the read snapshot with the A32 floor; never auto-promote."""
    out = []
    for u in expected["units_active"]:
        state = snap["units"].get(u)
        if state != "active":
            out.append({"item": "unit:%s" % u, "expected": "active",
                        "observed": state, "severity": "regression-signal"})
    if snap["fb_owner"] != expected["fb_owner"]:
        out.append({"item": "fb-owner", "expected": expected["fb_owner"],
                    "observed": snap["fb_owner"], "severity": "regression-signal"})
    if expected["animation_receipt_required"] and not snap["animation_receipt"]:
        out.append({"item": "animation-receipt", "expected": "present",
                    "observed": snap["animation_receipt"], "severity": "regression-signal"})
    if expected["alsa_contains"] not in (snap["alsa_cards"] + snap["alsa_beyond_madera"]):
        out.append({"item": "alsa-card", "expected": "contains %s" % expected["alsa_contains"],
                    "observed": snap["alsa_cards"], "severity": "regression-signal"})
    if expected["touch_device"] not in snap["touch_devices"]:
        out.append({"item": "touch-device", "expected": "contains sec_touchscreen",
                    "observed": snap["touch_devices"][:120], "severity": "regression-signal"})
    if snap["registry_http_code"] != expected["registry_http"]:
        out.append({"item": "pwa-registry", "expected": "HTTP %s" % expected["registry_http"],
                    "observed": snap["registry_http_code"], "severity": "regression-signal"})
    if len(snap["failed_units"]) > expected["failed_units_max"]:
        out.append({"item": "failed-units", "expected": "0",
                    "observed": snap["failed_units"], "severity": "regression-signal"})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="S10+ A32 baseline capture (briq-10a)")
    ap.add_argument("--evidence-dir", default=None)
    ap.add_argument("--name", default=None)
    ap.add_argument("--dev", default=None, help="explicit tty (fake console / known node)")
    ap.add_argument("--probe-seconds", type=float, default=8.0)
    ap.add_argument("--lock-wait", type=float, default=30.0)
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--pwa-list", default=None, help="comma-separated repo-relative PWA paths")
    ap.add_argument("--escalate", action="store_true")
    ap.add_argument("--fake-console", action="store_true",
                    help="mark the bundle as an OFFLINE self-test, never device evidence")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    repo = nl.repo_root_from_here()
    ev_root = args.evidence_dir or os.path.join(repo, "docs", "beta-finalization",
                                                "live", "evidence")
    nl.ensure_not_qq(ev_root)
    bundle = nl.EvidenceBundle(ev_root, name=args.name, label="baseline")
    rels = (args.pwa_list.split(",") if args.pwa_list
            else pwa_list_from_manifest(repo))
    report = {"briq": "briq-10a-live-reachability-preflight",
              "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "evidence_dir": bundle.dir,
              "fake_console": bool(args.fake_console), "pwa_files": rels,
              "reachable": False, "verdict": None, "blocked_reason": None}

    # --- 1. reachability ---------------------------------------------------- #
    node = None
    if args.dev:
        node = {"callout": args.dev, "match_stage": "explicit"}
    else:
        try:
            nodes = nl.enumerate_console_nodes()
            usb = []
            if sys.platform == "darwin":
                try:
                    usb = nl.parse_ioreg_usb_devices(
                        subprocess.run(["ioreg", "-w0", "-l", "-p", "IOUSB"],
                                       capture_output=True, text=True, timeout=20).stdout)
                except (OSError, subprocess.SubprocessError):
                    usb = []
            node = nl.select_console_node(nodes, usb_devices=usb)
        except (nl.SelectionError, subprocess.SubprocessError) as e:
            report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
            report["blocked_reason"] = "capability selection failed: %s" % e
            return finish(bundle, report, args, 3)
    report["console"] = node

    con = None
    try:
        con = nl.Console(node["callout"], timeout=args.timeout, lock_wait=args.lock_wait)
        con.open()
        probe = con.probe(args.probe_seconds)
        report["probe"] = probe.as_dict()
        bundle.write("probe-raw.txt", json.dumps(probe.as_dict(), indent=2, sort_keys=True))
        if not probe.reachable:
            report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
            report["blocked_reason"] = (
                "console %s enumerated but byte-silent for %.1fs: the on-device "
                "console is not serving the port; no baseline could be read"
                % (node["callout"], args.probe_seconds))
            return finish(bundle, report, args, 3)

        # --- 2/3. read the baseline ---------------------------------------- #
        snap = snapshot(con, bundle, repo, rels)
        if snap["frames_ok"] < snap["frames_total"]:
            report["incomplete_frames"] = snap["frames_total"] - snap["frames_ok"]
        bundle.write_json("a32-baseline.json", snap)
        host = host_pwa_hashes(repo, rels)
        bundle.write_json("host-pwa-hashes.json", host)
        drift = []
        for rel, host_hash in host.items():
            dev_key = "pwa/nuxel-home/" + rel.split("pwa/nuxel-home/", 1)[-1]
            dev_hash = snap["pwa_sha256_device"].get(dev_key)
            if dev_hash and dev_hash != host_hash:
                drift.append({"file": rel, "device": dev_hash, "repo": host_hash})
        report["pwa_drift"] = drift
        d = deltas(snap)
        report["baseline_deltas"] = d
        bundle.write_json("baseline-deltas.json", d)
        report["reachable"] = True
        report["verdict"] = "DEPLOYED_UNVERIFIED"
        report["verdict_note"] = (
            "baseline read from the running device; this is a read-only observation "
            "and proves nothing about hardware that reports no evidence (e.g. a "
            "registered sec_ts driver is not proof of a working touchscreen)")
        return finish(bundle, report, args, 0)
    except nl.ConsoleLost as e:
        report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
        report["blocked_reason"] = "cannot take the console: %s" % e
        return finish(bundle, report, args, 3)
    finally:
        if con is not None:
            con.close()


def finish(bundle, report, args, code):
    report["exit_code"] = code
    report["verdicts"] = {"briq-10a-live-reachability-preflight":
                          report["verdict"] or "BLOCKED_EXTERNAL_RESOURCE"}
    bundle.write_json("baseline-capture.json", report)
    man, lines = bundle.manifest()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("# nuxel-live-baseline -> %s" % report.get("verdict"))
        print("# evidence: %s" % bundle.dir)
        if report.get("blocked_reason"):
            print("# blocked: %s" % report["blocked_reason"])
        if report.get("baseline_deltas"):
            for d in report["baseline_deltas"]:
                print("# delta: %s expected=%s observed=%s" % (d["item"], d["expected"],
                                                               d["observed"]))
        print("# manifest: %s" % man)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

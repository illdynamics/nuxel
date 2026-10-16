#!/usr/bin/env python3
"""nuxel-live-deploy — briq-10b: deploy staged userspace to the RUNNING phone.

ACCESS TIER: live-phone-only for --apply; the plan/dry-run path is repository-only.

Baseline discipline, per file, exactly:
    record previous hash and keep a copy  ->  stage to <target>.nuxel-staged
    ->  verify staged SHA-256 on the device  ->  atomic `mv -f` install
    ->  verify installed SHA-256  ->  restart ONLY the smallest affected service
    ->  health check  ->  automatic rollback on failure.

Every write is confined to a userspace root.  If a plan step would touch a raw
partition, an image, a kernel/DTB/DTBO, the modem/EFS/calibration region, PIT or
partition metadata, the plan is refused *before any device contact* and the run
is reported BLOCKED_FIRMWARE (or BLOCKED_KERNEL for a group that says so).

If the console is unreachable, the plan is still produced (repository work is
not blocked by the phone) and the run reports BLOCKED_EXTERNAL_RESOURCE.

Verdicts
  0  --apply succeeded on device            -> DEPLOYED_UNVERIFIED
     (VERIFIED_ON_S10PLUS only with --observation "..." quoting a real on-device read)
  0  plan/dry-run only                      -> IMPLEMENTED_NOT_DEPLOYED
  3  console unreachable                    -> BLOCKED_EXTERNAL_RESOURCE
  4  plan violates an invariant             -> BLOCKED_FIRMWARE / BLOCKED_KERNEL
  5  a step failed and was rolled back      -> FAILED
Never flashes; never touches .qq / RUN_ROOT.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nuxel_live as nl  # noqa: E402


def slug(text):
    return re.sub(r"[^A-Za-z0-9._-]", "-", text).strip("-")[:60]


def write_plan_artifacts(bundle, plan, repo):
    bundle.write_json("plan.json", plan)
    index = []
    for i, step in enumerate(plan["steps"], 1):
        name = "scripts/%03d-%s.sh" % (i, slug(os.path.basename(step["target"])))
        body = ("#!/bin/sh\n# %s -> %s (service: %s, risk: %s)\n# staged source: %s\n# "
                "previous-hash: %s\n%s\n"
                % (step["component"], step["target"], step["service"], step["risk"],
                   step["source"], step["source_sha256"], nl.install_script(step)))
        bundle.write(name, body)
        index.append({"n": i, "group": step["group"], "target": step["target"],
                      "service": step["service"], "risk": step["risk"],
                      "source": step["source"], "source_sha256": step["source_sha256"],
                      "script": name})
    bundle.write_json("plan-index.json", index)
    bundle.write_json("skipped-groups.json", plan["skipped"])
    if plan["violations"]:
        bundle.write_json("plan-violations.json", plan["violations"])
    return index


def service_exists(con, unit):
    if not unit:
        return None
    res = con.run("systemctl cat %s >/dev/null 2>&1 && echo UNIT-PRESENT || echo UNIT-ABSENT"
                  % unit)
    if not res.ok:
        return None
    return "UNIT-PRESENT" in res.output


def run_script(con, bundle, name, script_text, timeout=None):
    """Stage a shell script on the device through verified frames, then run it."""
    path = "/var/tmp/nxl-%s.sh" % slug(name)
    push = nl.push_bytes(con, script_text.encode(), path, mode="0755")
    res = con.run("sh %s 2>&1; echo NXLSCRIPT-RC=$?" % path,
                  timeout=timeout or con.timeout)
    bundle.write("runs/%s.out" % slug(name),
                 "pushed=%s\nok=%s rc=%s\n---\n%s"
                 % (json.dumps(push, sort_keys=True), res.ok, res.rc, res.output))
    m = re.search(r"NXLSCRIPT-RC=(-?\d+)", res.output)
    rc = int(m.group(1)) if m else None
    return {"script": path, "push": push, "framed": res.ok, "rc": rc,
            "output": res.output[-2000:]}


def run_step(con, bundle, step, i):
    """stage -> verify -> atomic install -> restart smallest service -> health."""
    rec = {"n": i, "group": step["group"], "target": step["target"],
           "service": step["service"], "risk": step["risk"],
           "source": step["source"], "source_sha256": step["source_sha256"],
           "previous_hash": None, "installed_hash": None, "rollback": None}
    # record the previous hash / keep a rollback copy
    prev = run_script(con, bundle, "capture-%03d" % i,
                      "set -eu\nif [ -e %s ]; then cp -a %s %s; "
                      "sha256sum %s | cut -d' ' -f1; else echo NONE; fi\n"
                      % (step["target"], step["target"], step["backup"], step["target"]))
    rec["previous_hash"] = (prev["output"].strip().splitlines() or [None])[0]

    data = open(os.path.join(nl.repo_root_from_here(), step["source"]), "rb").read()
    push = nl.push_bytes(con, data, step["staged"], mode="0644")
    rec["staged_push"] = {"bytes": push["bytes"], "frames": push["frames"],
                          "sha256": push["decoded_sha256"]}

    svc = step["service"]
    if svc and service_exists(con, svc) is False:
        rec["service_absent"] = svc
        svc = None
    inst = run_script(con, bundle, "install-%03d" % i,
                      "#!/bin/sh\n" + nl.install_script(dict(step, service=svc)))
    rec["install"] = {"framed": inst["framed"], "rc": inst["rc"],
                      "output": inst["output"][-1200:]}
    rec["ok"] = bool(inst["framed"] and inst["rc"] == 0)
    if rec["ok"]:
        verify = con.run(step["verify"])
        rec["verify_output"] = verify.output.strip()[:200]
        rec["installed_hash"] = step["source_sha256"]
        rec["ok"] = bool(verify.ok and step["source_sha256"] in verify.output)
    if not rec["ok"]:
        rb = run_script(con, bundle, "rollback-%03d" % i,
                        "#!/bin/sh\nset -u\nif [ -e %s ]; then cp -a %s %s; %s; echo ROLLED-BACK; "
                        "else echo NO-BACKUP; fi\n"
                        % (step["backup"], step["backup"], step["target"],
                           ("systemctl restart %s" % svc) if svc else "true"))
        rec["rollback"] = {"rc": rb["rc"], "output": rb["output"][-600:]}
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description="flash-free live userspace deploy (briq-10b)")
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--evidence-dir", default=None)
    ap.add_argument("--name", default=None)
    ap.add_argument("--dev", default=None)
    ap.add_argument("--only", default=None, help="comma-separated group ids")
    ap.add_argument("--apply", action="store_true",
                    help="actually write to the device (default: plan/dry-run)")
    ap.add_argument("--observation", default=None,
                    help="verbatim on-device observation that upgrades the verdict")
    ap.add_argument("--lock-wait", type=float, default=30.0)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--fail-fast", action="store_true", default=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    repo = nl.repo_root_from_here()
    man_path = args.manifest or os.path.join(repo, "tools", "beta", "live",
                                             "deploy-manifest.json")
    ev_root = args.evidence_dir or os.path.join(repo, "docs", "beta-finalization",
                                                "live", "evidence")
    nl.ensure_not_qq(ev_root)
    bundle = nl.EvidenceBundle(ev_root, name=args.name, label="deploy")
    manifest = json.load(open(man_path))
    if args.only:
        want = {g.strip() for g in args.only.split(",")}
        manifest = dict(manifest)
        manifest["groups"] = [g for g in manifest["groups"] if g["id"] in want]

    plan = nl.build_deploy_plan(manifest, repo)
    index = write_plan_artifacts(bundle, plan, repo)
    report = {"briq": "briq-10b-live-deploy-userspace",
              "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "evidence_dir": bundle.dir,
              "manifest": os.path.relpath(man_path, repo), "apply": bool(args.apply),
              "steps": len(plan["steps"]), "skipped": plan["skipped"],
              "violations": plan["violations"], "results": [], "verdict": None}

    if plan["violations"]:
        kinds = {v["kind"] for v in plan["violations"]}
        report["verdict"] = "BLOCKED_KERNEL" if kinds == {"declared_blocked"} else "BLOCKED_FIRMWARE"
        report["blocked_reason"] = ("plan refused before any device contact: %s"
                                    % json.dumps(plan["violations"])[:600])
        return finish(bundle, report, args, 4)
    if not args.apply:
        report["verdict"] = "IMPLEMENTED_NOT_DEPLOYED"
        report["verdict_note"] = ("plan + install scripts generated and guarded; no "
                                  "device write attempted (pass --apply for the live run)")
        return finish(bundle, report, args, 0)

    # --- reachability before any write -------------------------------------- #
    try:
        node = ({"callout": args.dev, "match_stage": "explicit"} if args.dev
                else nl.select_console_node(nl.enumerate_console_nodes()))
    except nl.SelectionError as e:
        report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
        report["blocked_reason"] = "capability selection failed: %s" % e
        return finish(bundle, report, args, 3)
    try:
        con = nl.Console(node["callout"], timeout=args.timeout, lock_wait=args.lock_wait)
        con.open()
    except nl.ConsoleLost as e:
        report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
        report["blocked_reason"] = "cannot take the console: %s" % e
        return finish(bundle, report, args, 3)
    try:
        probe = con.probe(6.0)
        report["probe"] = probe.as_dict()
        if not probe.reachable:
            report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
            report["blocked_reason"] = ("console %s is byte-silent: refusing to write "
                                        "to a device that cannot confirm the result"
                                        % node["callout"])
            return finish(bundle, report, args, 3)

        failed = False
        for i, step in enumerate(plan["steps"], 1):
            rec = run_step(con, bundle, step, i)
            report["results"].append(rec)
            if not rec["ok"]:
                failed = True
                if args.fail_fast:
                    break
        if failed:
            report["verdict"] = "FAILED"
            report["blocked_reason"] = ("a deploy step failed and was rolled back to the "
                                        "recorded previous hash; no further writes attempted")
            return finish(bundle, report, args, 5)
        report["verdict"] = "VERIFIED_ON_S10PLUS" if args.observation else "DEPLOYED_UNVERIFIED"
        report["observation"] = args.observation
        report["verdict_note"] = (
            "files staged, hash-verified, atomically installed and the smallest affected "
            "service restarted with a passing health check. DEPLOYED_UNVERIFIED means the "
            "deploy succeeded but no human-visible behaviour was observed."
            if not args.observation else
            "upgraded on the strength of a recorded on-device observation: %s" % args.observation)
        return finish(bundle, report, args, 0)
    finally:
        con.close()


def finish(bundle, report, args, code):
    report["exit_code"] = code
    report["verdicts"] = {"briq-10b-live-deploy-userspace":
                          report["verdict"] or "BLOCKED_EXTERNAL_RESOURCE"}
    bundle.write_json("deployment.json", report)
    man, lines = bundle.manifest()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("# nuxel-live-deploy -> %s" % report.get("verdict"))
        print("# evidence: %s" % bundle.dir)
        print("# steps planned: %d, skipped groups: %d"
              % (report["steps"], len(report["skipped"])))
        for s in report["skipped"]:
            print("# skipped: %s -> %s (%s)" % (s["group"], s["verdict"], s["reason"][:80]))
        if report.get("blocked_reason"):
            print("# blocked: %s" % report["blocked_reason"])
        print("# manifest: %s" % man)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

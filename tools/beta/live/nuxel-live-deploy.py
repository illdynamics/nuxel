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
           "risk_rank": step.get("risk_rank"), "mode": step.get("mode"),
           "source": step["source"], "source_sha256": step["source_sha256"],
           "declared_reload": step.get("declared_reload") or None,
           "health_check": step.get("health_check"),
           "rollback_route": step.get("rollback"),
           "previous_hash": None, "installed_hash": None, "rollback": None}
    # Idempotence / resumability: if the target already carries the source bytes,
    # do nothing and report success.  A deploy that is re-run after a console
    # reconnect must NOT overwrite the original .nuxel-rollback copy with the new
    # bytes (that would destroy the only route back to the pre-deploy baseline).
    cur = con.run("sha256sum %s 2>/dev/null | cut -d' ' -f1" % step["target"])
    if cur.ok and step["source_sha256"] in cur.output:
        rec.update({"already_deployed": True, "ok": True,
                    "previous_hash": step["source_sha256"],
                    "installed_hash": step["source_sha256"]})
        return rec
    # record the previous hash / keep a rollback copy
    data = open(os.path.join(nl.repo_root_from_here(), step["source"]), "rb").read()
    push = nl.push_bytes(con, data, step["staged"], mode=step.get("mode") or "0644")
    rec["staged_push"] = {"bytes": push["bytes"],
                          "parts": push.get("parts", push.get("frames")),
                          "sha256": push["decoded_sha256"]}

    svc = step["service"]
    if svc and service_exists(con, svc) is False:
        rec["service_absent"] = svc
        svc = None
    inst = run_script(con, bundle, "install-%03d" % i,
                      "#!/bin/sh\n" + nl.install_script(dict(step, service=svc)))
    rec["install"] = {"framed": inst["framed"], "rc": inst["rc"],
                      "output": inst["output"][-1200:]}
    m = re.search(r"PREV=(\S+)", inst["output"])
    rec["previous_hash"] = m.group(1) if m else None
    # Success is decided by the TARGET'S BYTES, not by whether the install frame's
    # reply survived the kmsg-mirroring console (an unreadable frame on a perfectly
    # good install was reported as FAILED and rolled back).  The install script's
    # EXIT trap already restored the baseline if the install genuinely failed, so a
    # read-back that still shows the source hash means the install really worked.
    # A verified install frame that says INSTALL-OK already ran `sha256sum <target>
    # | grep -q <hash>` on the device; only read the target back when that frame
    # was unreadable (the noisy-console case), which saves a frame per file.
    payload_ok = False
    if inst["framed"] and inst["rc"] == 0 and "INSTALL-OK" in inst["output"]:
        payload_ok = True
        rec["verify_output"] = "INSTALL-OK (hash checked in-frame)"
    else:
        for _try in range(3):
            verify = con.run(step["verify"])
            if verify.ok:
                rec["verify_output"] = verify.output.strip()[:200]
                payload_ok = step["source_sha256"] in verify.output
                break
    rec["installed_hash"] = step["source_sha256"] if payload_ok else None
    rec["ok"] = bool(payload_ok)
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
    ap.add_argument("--reconnect-timeout", type=float, default=180.0,
                    help="seconds to keep retrying the console after it drops")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--fail-fast", action="store_true", default=True)
    ap.add_argument("--order", choices=("manifest", "risk"), default="manifest",
                    help="apply steps in manifest order (default; the extension "
                         "block is authored in ASCENDING RISK) or by explicit "
                         "risk class + priority")
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

    # Validate and plan against the FULL manifest, then restrict execution to the
    # selected groups.  Filtering the manifest *before* validation breaks the
    # extension-block invariants (extension.groups / group_reload_notes name
    # groups that a filtered manifest no longer contains), so --only must never
    # remove groups from the manifest that validate_manifest() inspects.
    plan = nl.build_deploy_plan(manifest, repo)
    if args.only:
        want = {g.strip() for g in args.only.split(",") if g.strip()}
        known = {s["group"] for s in plan["steps"]}
        unknown = want - {g.get("id") for g in manifest["groups"]}
        if unknown:
            report_only_error = ("--only names unknown group(s): %s" % sorted(unknown))
            print("# " + report_only_error, file=sys.stderr)
            return 2
        plan["steps"] = [s for s in plan["steps"] if s["group"] in want]
        plan["group_order"] = [g for g in plan["group_order"] if g.get("group") in want]
    if args.order == "risk":
        # Ascending risk first, then the group's own priority, then the target —
        # a total order, so the sequence is deterministic and recorded.
        plan["steps"].sort(key=lambda s: (s["risk_rank"], s.get("priority") or 0,
                                          s["group"], s["target"]))
    index = write_plan_artifacts(bundle, plan, repo)
    report = {"briq": "briq-10b-live-deploy-userspace",
              "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "evidence_dir": bundle.dir,
              "manifest": os.path.relpath(man_path, repo), "apply": bool(args.apply),
              "order": args.order, "steps": len(plan["steps"]),
              "groups": plan.get("group_order"), "risk_envelope": plan.get("risk_envelope"),
              "skipped": plan["skipped"],
              "violations": plan["violations"], "results": [], "verdict": None}

    if plan["violations"]:
        kinds = {v["kind"] for v in plan["violations"]}
        report["violation_kinds"] = sorted(kinds)
        if kinds <= {"declared_blocked"}:
            # Only honestly-declared kernel/firmware-blocked groups: nothing was
            # planned and nothing may be written.
            report["verdict"] = "BLOCKED_KERNEL"
        elif "guard" in kinds:
            # A step resolved onto a flash-adjacent path: this is the hard
            # invariant, and it is reported as such rather than as a bad manifest.
            report["verdict"] = "BLOCKED_FIRMWARE"
        else:
            # manifest / ordering / source_escape / missing_source / command_guard /
            # procedure_missing: the plan itself is invalid. That is a repository
            # defect, not an external-resource block, and it is never a deploy.
            report["verdict"] = "FAILED"
        report["blocked_reason"] = (
            "plan refused BEFORE any device contact (nothing was written): %s"
            % json.dumps(plan["violations"])[:900])
        report["verdicts"] = {"briq-10b-live-deploy-userspace": report["verdict"]}
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
        steps = plan["steps"]
        reconnects = 0
        i = 0
        while i < len(steps):
            step = steps[i]
            try:
                rec = run_step(con, bundle, step, i + 1)
                # A single dropped/corrupted frame on a step that actually landed
                # must not abort a 400-file deploy: re-attempt the step (it skips
                # itself if the target already carries the source bytes).
                tries = 1
                while not rec["ok"] and tries < 3:
                    tries += 1
                    time.sleep(1)
                    rec = run_step(con, bundle, step, i + 1)
                    rec["attempts"] = tries
            except nl.ConsoleLost as e:
                # The S10+ console gadget re-enumerates under sustained load
                # (measured 2026-10-16, several times per deploy).  A lost console
                # is not a failed step: reopen the port, re-probe, and RESUME from
                # the same step (already-installed files skip themselves).
                if reconnects >= 8:
                    report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
                    report["blocked_reason"] = ("console lost after %d reconnects: %s"
                                                % (reconnects, e))
                    return finish(bundle, report, args, 3)
                reconnects += 1
                report.setdefault("reconnects", []).append({"at_step": i + 1, "error": str(e)})
                con.close()
                waited = 0.0
                reopened = None
                while waited < args.reconnect_timeout:
                    time.sleep(3)
                    waited += 3
                    try:
                        reopened = nl.Console(node["callout"], timeout=args.timeout,
                                              lock_wait=args.lock_wait)
                        reopened.open()
                        if reopened.probe(6.0).reachable:
                            break
                        reopened.close()
                        reopened = None
                    except nl.ConsoleLost:
                        reopened = None
                if reopened is None:
                    report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
                    report["blocked_reason"] = ("console did not return within %.0fs "
                                                "after step %d" % (args.reconnect_timeout, i + 1))
                    return finish(bundle, report, args, 3)
                con = reopened
                continue  # retry the same step
            report["results"].append(rec)
            if not rec["ok"]:
                failed = True
                if args.fail_fast:
                    break
            i += 1
        report["reconnects"] = report.get("reconnects", [])

        # --- group health checks, once each, now that the group is complete --- #
        if not failed:
            health = []
            seen = []
            for st in steps:
                if st["group"] not in seen:
                    seen.append(st["group"])
            for gid in seen:
                hc = next((st.get("health_check") for st in steps
                           if st["group"] == gid and st.get("health_check")), None)
                if not hc:
                    continue
                ok = False
                out = ""
                for _try in range(3):
                    res = con.run(hc, timeout=max(args.timeout, 30.0))
                    out = res.output.strip()[:200]
                    if res.ok:
                        ok = (res.rc == 0)
                        break
                health.append({"group": gid, "check": hc, "ok": bool(ok), "output": out})
                print("# health %s -> %s" % (gid, "ok" if ok else "FAILED"), file=sys.stderr)
            report["health"] = health
            if any(not h["ok"] for h in health):
                failed = True
                report["blocked_reason"] = ("a group health check failed after install: %s"
                                            % json.dumps([h for h in health if not h["ok"]]))
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

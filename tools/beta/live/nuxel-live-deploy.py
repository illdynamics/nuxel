#!/usr/bin/env python3
"""nuxel-live-deploy — briq-10b: deploy staged userspace to the RUNNING phone.

ACCESS TIER: live-phone-only for --apply; the plan/dry-run path is repository-only.

Discipline:
    validate/guard the whole manifest -> acquire the shared flock -> record
    boot id and a JSONL journal -> stage, hash-verify and atomically install
    EVERY selected file -> build ONE coalesced activation plan (daemon-reload /
    declared reloads / service restarts) -> run group health checks -> commit,
    or restore every changed target and coalesce the rollback actions.

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
  6  rollback could not be verified         -> NEEDS_RECOVERY
 130 operator cancellation                 -> CANCELLED
Never flashes; never touches .qq / RUN_ROOT.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nuxel_live as nl  # noqa: E402


def slug(text):
    return re.sub(r"[^A-Za-z0-9._-]", "-", text).strip("-")[:60]


def make_operation_id():
    return "deploy-%s-%d" % (time.strftime("%Y%m%dT%H%M%S"), os.getpid())


class DeployReporter:
    """Operator-facing state/progress/log line, with a JSONL transaction journal.

    State transitions are validated against ``nl.CONSOLE_TRANSITIONS`` so a
    failed reconnect can never be reported as CONNECTED and a failed health
    check can never be reported as SUCCEEDED.  Progress lines reflect work the
    device acknowledged, never merely bytes queued on the host.
    """

    def __init__(self, bundle, op_id, target, out=sys.stderr, started_at=None):
        self.bundle = bundle
        self.op_id = op_id
        self.target = target
        self.out = out
        self.started_at = started_at or time.strftime("%Y-%m-%dT%H:%M:%S%z")
        self.t0 = time.monotonic()
        self.state = "DISCONNECTED"
        self.last_progress = None
        self.last_progress_line = 0.0
        self.last_event = None
        self.state_change("starting", force="CONNECTING")

    def state_change(self, note, force=None):
        new = force or self._state_for(note)
        self.state = nl.transition_state(self.state, new)
        self.last_event = note
        self.log({"event": "state", "state": self.state, "note": note})
        self._line("# [%s] %s (%.1fs)" % (self.state, note, self.elapsed()))
        self.snapshot()
        return self.state

    @staticmethod
    def _state_for(note):
        key = str(note).lower()
        for state in nl.CONSOLE_STATES:
            if state.lower() in key or state.lower() == key:
                return state
        mapping = {
            "reconnecting": "RECONNECTING", "health check": "HEALTH_CHECK",
            "rolling back": "ROLLING_BACK", "staging": "DEPLOY_STAGING",
            "activating": "DEPLOY_ACTIVATING", "restarting": "SERVICE_RESTARTING",
            "verifying": "TRANSFER_VERIFYING", "transferring": "TRANSFER_RUNNING",
        }
        for word, state in mapping.items():
            if word in key:
                return state
        return "COMMAND_RUNNING"

    def elapsed(self):
        return time.monotonic() - self.t0

    def log(self, event):
        """Append one journal event without clobbering a per-file target field."""
        if self.bundle is not None:
            doc = dict(event)
            doc.setdefault("target", self.target)
            doc.update({"op": self.op_id, "console": self.target,
                        "elapsed_s": round(self.elapsed(), 3)})
            self.bundle.journal(doc)

    def snapshot(self, **extra):
        """Write a small status.json that a local operator can read without the port."""
        if self.bundle is None:
            return
        doc = {"operation_id": self.op_id, "target": self.target,
               "state": self.state, "pid": os.getpid(),
               "pid_start": nl._proc_start_ticks(os.getpid()),
               "host": __import__("socket").gethostname(),
               "started_at": self.started_at,
               "elapsed_s": round(self.elapsed(), 3),
               "last_event": self.last_event,
               "last_progress": self.last_progress}
        doc.update(extra)
        try:
            self.bundle.write_json("status.json", doc)
        except OSError:
            pass

    def progress(self, event):
        acked = int(event.get("acked_bytes", 0))
        total = int(event.get("total_bytes", 0))
        blocks = int(event.get("block_count", 0))
        idx = int(event.get("block_index", 0))
        retries = int(event.get("retries", 0))
        mode = event.get("mode", "block")
        resumed = int(event.get("resumed_b64_chars", 0))
        elapsed = float(event.get("elapsed_s") or max(0.001, self.elapsed()))
        elapsed = max(0.001, elapsed)
        pct = (100.0 * acked / total) if total else 100.0
        rate = float(event.get("throughput_bytes_s") or (acked / elapsed))
        self.last_progress = {"acked_bytes": acked, "total_bytes": total,
                              "block_index": idx, "block_count": blocks,
                              "retries": retries, "mode": mode,
                              "resumed_b64_chars": resumed,
                              "throughput_bytes_s": round(rate, 1),
                              "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        text = ("%s: %d/%d bytes acknowledged (%.1f%%), %s %d/%d, "
                "retries %d, %.1f B/s, elapsed %.1fs"
                % (self.target, acked, total, pct, mode, idx, blocks,
                   retries, rate, elapsed))
        now = time.monotonic()
        interactive = bool(getattr(self.out, "isatty", lambda: False)())
        if interactive:
            self._line("\r# [TRANSFER_RUNNING] " + text, end="")
        elif now - self.last_progress_line >= 5.0 or acked >= total:
            self.last_progress_line = now
            self._line("# [TRANSFER_RUNNING] " + text)
        # A status snapshot is cheap and lets a second terminal see progress
        # without touching the serial stream.
        if now - getattr(self, "_last_snapshot", 0.0) >= 2.0:
            self._last_snapshot = now
            self.snapshot(transfer=self.last_progress)

    def summary(self, text):
        self.log({"event": "summary", "message": text})
        self._line("# %s" % text)

    def _line(self, text, end="\n"):
        try:
            self.out.write(text + end)
            self.out.flush()
        except (OSError, ValueError):
            pass


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
    activation = (plan.get("activation_plan")
                  or nl.transaction_activation_plan(plan["steps"]))
    bundle.write_json("activation-plan.json", activation)
    act_body = ["#!/bin/sh", "# coalesced transaction-level activation plan",
                "# daemon-reload: %d, reloads: %d, restarts: %d"
                % (1 if activation.get("daemon_reload") else 0,
                   len(activation.get("reloads") or []),
                   len(activation.get("restarts") or []))]
    da = activation.get("daemon_reload_action")
    if da:
        act_body.append("( %s )" % da["action"].replace("\n", "; "))
    for r in activation["reloads"]:
        act_body.append("( %s )" % r["action"].replace("\n", "; "))
    for r in activation["restarts"]:
        act_body.append("systemctl restart %s && systemctl is-active %s"
                        % (r["service"], r["service"]))
    bundle.write("scripts/000-activate.sh", "\n".join(act_body) + "\n")
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


def run_step(con, bundle, step, i, progress=None, cancel_check=None,
             block_lines=None, block_bytes=None, resume=True):
    """Stage -> verify -> atomically install one file.

    Service restarts/reloads are deliberately NOT run here; they happen once at
    the transaction boundary after every selected file is staged and verified.
    A failed install is left for the transaction-level rollback, which restores
    and verifies the recorded previous hash for every changed target.
    """
    t0 = time.time()
    rec = {"n": i, "group": step["group"], "target": step["target"],
           "service": step["service"], "risk": step["risk"],
           "risk_rank": step.get("risk_rank"), "mode": step.get("mode"),
           "source": step["source"], "source_sha256": step["source_sha256"],
           "declared_reload": step.get("declared_reload") or None,
           "health_check": step.get("health_check"),
           "rollback_route": step.get("rollback"),
           "txn_backup": step.get("txn_backup"),
           "previous_hash": None, "installed_hash": None, "rollback": None,
           "changed": False}
    # Idempotence / resumability: if the target already carries the source bytes,
    # do nothing and report success.  A deploy that is re-run after a console
    # reconnect must NOT overwrite the original .nuxel-rollback copy with the new
    # bytes (that would destroy the only route back to the pre-deploy baseline).
    cur = con.run("if [ -e %s ]; then sha256sum %s 2>/dev/null | cut -d' ' -f1; "
                  "else echo NUXEL-ABSENT; fi"
                  % (step["target"], step["target"]))
    if "NUXEL-ABSENT" in (cur.output if cur.ok else ""):
        observed_previous = "NONE"
    else:
        m_prev = re.search(r"\b([0-9a-f]{64})\b", cur.output if cur.ok else "")
        observed_previous = m_prev.group(1) if m_prev else None
    if cur.ok and step["source_sha256"] in cur.output:
        rec.update({"already_deployed": True, "ok": True,
                    "previous_hash": step["source_sha256"],
                    "installed_hash": step["source_sha256"],
                    "elapsed_s": round(time.time() - t0, 3)})
        return rec
    rec["changed"] = True
    # Record the pre-change hash even if the install frame is later lost; this
    # is the recovery contract for a host crash or a truncated device reply.
    rec["previous_hash"] = observed_previous
    with open(os.path.join(nl.repo_root_from_here(), step["source"]), "rb") as fh:
        data = fh.read()
    mode = step.get("mode") or "0644"
    t_push = time.time()
    push = None
    blocked_error = None
    if len(data) >= 8192:
        try:
            push = nl.block_push_bytes(
                con, data, step["staged"], mode=mode, progress=progress,
                cancel_check=cancel_check, block=block_lines,
                max_block_bytes=block_bytes or 3072, resume=resume)
        except nl.OperationCancelled:
            raise
        except nl.ConsoleLost as e:
            # Fallback to the proven frame-per-chunk protocol if block streaming
            # is unsupported by the far end; never leave echo disabled behind.
            blocked_error = str(e)
            try:
                con.run("stty echo 2>/dev/null", timeout=con.timeout)
            except nl.ConsoleLost:
                pass
            try:  # a failed block attempt may have left a transaction part
                con.run("rm -f %s.*.b64" % step["staged"], timeout=con.timeout)
            except nl.ConsoleLost:
                pass
            push = nl.push_bytes(con, data, step["staged"], mode=mode,
                                 cancel_check=cancel_check, progress=progress)
            push["fallback"] = True
            push["block_error"] = blocked_error
    else:
        push = nl.push_bytes(con, data, step["staged"], mode=mode,
                             cancel_check=cancel_check, progress=progress)
    push["elapsed_s"] = round(time.time() - t_push, 3)
    push["throughput_bytes_s"] = round(len(data) / push["elapsed_s"], 1) \
        if push["elapsed_s"] > 0 else None
    rec["staged_push"] = {
        "bytes": int(push["bytes"]),
        "acked_bytes": int(push.get("acked_bytes", push["bytes"])),
        "parts": int(push.get("parts", push.get("frames", 0)) or 0),
        "blocks": int(push.get("blocks") or 0),
        "raw_writes": int(push.get("raw_writes") or 0),
        "ack_writes": int(push.get("ack_writes") or 0),
        "write_bytes": int(push.get("write_bytes") or 0),
        "resume_used": bool(push.get("resume_used", False)),
        "resumed_b64_chars": int(push.get("resumed_b64_chars") or 0),
        "mode": push.get("mode") or step.get("mode") or "0644",
        "sha256": push["decoded_sha256"],
        "elapsed_s": push.get("elapsed_s"),
        "throughput_bytes_s": push.get("throughput_bytes_s"),
        "retries": int(push.get("retries") or 0),
        "fallback": bool(push.get("fallback", False)),
    }
    if blocked_error:
        rec["staged_push"]["block_error"] = blocked_error

    svc = step["service"]
    if svc and service_exists(con, svc) is False:
        rec["service_absent"] = svc
        svc = None
    inst = run_script(con, bundle, "install-%03d" % i,
                      "#!/bin/sh\n" + nl.install_script(dict(step, service=svc)))
    rec["install"] = {"framed": inst["framed"], "rc": inst["rc"],
                      "output": inst["output"][-1200:]}
    m = re.search(r"PREV=(\S+)", inst["output"])
    if m:
        rec["previous_hash"] = "NONE" if m.group(1) == "NONE" else m.group(1)
    # Success is decided by the TARGET'S BYTES, not by whether the install frame's
    # reply survived the kmsg-mirroring console (an unreadable frame on a perfectly
    # good install was reported as FAILED and rolled back).  The install script's
    # EXIT trap already restored the baseline if the install genuinely failed, so a
    # read-back that still shows the source hash means the install really worked.
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
    rec["elapsed_s"] = round(time.time() - t0, 3)
    return rec


def run_reload_action(con, bundle, name, action, timeout=None):
    """Run one coalesced `declared_reload` action on the device, recorded.

    The action runs in a subshell so a stray `exit 0`/`exit 1` inside a declared
    command cannot terminate the frame wrapper before its result marker is sent.
    """
    script = ("#!/bin/sh\nset -u\n( %s )\nrc=$?\necho NXLRELOAD-RC=$rc\n"
              % action.replace("\n", "; "))
    inst = run_script(con, bundle, name, script, timeout=timeout)
    m = re.search(r"NXLRELOAD-RC=(-?\d+)", inst["output"])
    rc = int(m.group(1)) if m else None
    return {"action": action, "framed": inst["framed"], "rc": rc,
            "output": inst["output"][-600:]}


def _restart_record(con, bundle, service, name, kind):
    out = run_script(con, bundle, name,
                     "#!/bin/sh\nset -e\nsystemctl restart %s\n"
                     "systemctl is-active %s\necho ACTIVATE-OK\n"
                     % (service, service))
    return {"kind": kind, "service": service, "framed": out["framed"],
            "rc": out["rc"], "output": out["output"][-300:]}


def _group_health_checks(steps):
    out, seen = [], set()
    for step in steps:
        gid = step.get("group")
        if gid in seen:
            continue
        seen.add(gid)
        hc = step.get("health_check")
        if hc:
            out.append((gid, hc))
    return out


def _execute_activation(con, bundle, activation, i, health_groups=None,
                        phase="activate"):
    """Execute one coalesced daemon-reload/reload/restart/health plan.

    Order is deterministic: one daemon-reload (if requested), declared reload
    actions in first-seen order, then each independently-affected service once.
    Health checks run last.  No action is ever planned once per file.
    """
    records = []
    prefix = "rollback-" if phase == "rollback" else ""
    da = activation.get("daemon_reload_action")
    if da:
        out = run_reload_action(con, bundle, prefix + "daemon-reload-%03d" % i,
                                da["action"])
        records.append({"kind": prefix + "daemon-reload",
                        "group": da.get("group"), "action": da["action"],
                        "framed": out["framed"], "rc": out["rc"],
                        "output": out["output"][-300:]})
        if not out["framed"] or out["rc"] != 0:
            return records, False
    for n, entry in enumerate(activation.get("reloads") or [], 1):
        out = run_reload_action(con, bundle,
                                "%sreload-%03d-%d" % (prefix, i, n),
                                entry["action"])
        records.append({"kind": prefix + "reload", "group": entry.get("group"),
                        "action": entry["action"], "framed": out["framed"],
                        "rc": out["rc"], "output": out["output"][-300:],
                        "restart_services": entry.get("restart_services") or []})
        if not out["framed"] or out["rc"] != 0:
            return records, False
    for n, entry in enumerate(activation.get("restarts") or [], 1):
        rec = _restart_record(con, bundle, entry["service"],
                              "%srestart-%03d-%d" % (prefix, i, n),
                              prefix + "restart")
        rec["group"] = entry.get("group")
        records.append(rec)
        if not rec["framed"] or rec["rc"] != 0:
            return records, False
    for gid, hc in (health_groups or []):
        ok = False
        out = ""
        for _try in range(3):
            res = con.run("( %s )" % hc, timeout=max(con.timeout, 30.0))
            out = res.output.strip()[:300]
            if res.ok:
                ok = (res.rc == 0)
                if ok:
                    break
        records.append({"kind": prefix + "health", "group": gid, "check": hc,
                        "ok": bool(ok), "output": out})
        if not ok:
            return records, False
    return records, True


def run_group_activation(con, bundle, group, steps, i):
    """Run one group's coalesced plan and health check (legacy-compatible)."""
    plan = nl.group_reload_plan(steps)
    return _execute_activation(con, bundle, plan, i,
                               health_groups=_group_health_checks(steps))


def run_transaction_activation(con, bundle, changed_steps, all_steps, i):
    """Run the WHOLE transaction's coalesced activation once.

    `changed_steps` drives reload/restart dedupe (unchanged targets must not
    cause needless restarts).  `all_steps` supplies health checks, which are
    non-mutating and therefore still run for an idempotent no-op deploy.
    """
    plan = nl.transaction_activation_plan(changed_steps)
    return _execute_activation(con, bundle, plan, i,
                               health_groups=_group_health_checks(all_steps))


def _restore_script(step, previous_hash, strict=True):
    prev = str(previous_hash) if previous_hash is not None else ""
    tail = "exit 1" if strict else "exit 0"
    # A transaction backup is authoritative for this run.  Only legacy callers
    # without one may fall back to the long-lived `.nuxel-rollback` baseline.
    backup = step.get("txn_backup") or step["backup"]
    return (
        "#!/bin/sh\nset -u\n"
        "if [ -e %(backup)s ]; then cp -a %(backup)s %(target)s; echo RESTORED; "
        "elif [ \"%(prev)s\" = NONE ]; then rm -f %(target)s; echo REMOVED-NEW; "
        "elif [ -e %(target)s ] && [ \"$(sha256sum %(target)s | cut -d' ' -f1)\" "
        "= \"%(prev)s\" ]; then echo ALREADY-RESTORED; "
        "else echo NO-BACKUP; %(tail)s; fi\n"
        % {"backup": backup, "target": step["target"], "prev": prev,
           "tail": tail})


def _verify_restored(con, step, previous_hash):
    """Return (verified, observed_output) for the recorded pre-transaction state."""
    if previous_hash == "NONE":
        got = con.run("test ! -e %s && echo NUXEL-ABSENT" % step["target"])
        return (bool(got.ok and got.rc == 0 and "NUXEL-ABSENT" in got.output),
                got.output.strip()[:200])
    if not previous_hash:
        return False, "no recorded previous hash"
    got = con.run("sha256sum %s 2>/dev/null | cut -d' ' -f1" % step["target"])
    return (bool(got.ok and got.rc == 0 and previous_hash in got.output),
            got.output.strip()[:200])


def run_transaction_rollback(con, bundle, steps, previous_hashes, i,
                             health_groups=None, strict=True):
    """Restore changed files, verify every restore, then coalesce rollback actions.

    Returns ``(records, ok)``.  ``ok`` is True only when every file could be
    restored to its recorded previous hash (or proven absent for a newly-created
    file), every coalesced rollback action succeeded and every requested health
    check passed.
    """
    records = []
    ok = True
    for step in reversed(steps):
        prev = previous_hashes.get(step["target"])
        rb = run_script(con, bundle, "rollback-%03d" % i,
                       _restore_script(step, prev, strict=strict))
        if prev is not None:
            verified, verify_output = _verify_restored(con, step, prev)
        else:
            verified, verify_output = None, "no recorded previous hash"
        rec = {"kind": "file-rollback", "group": step.get("group"),
               "target": step["target"], "previous_hash": prev,
               "backup_used": step.get("txn_backup") or step.get("backup"),
               "rc": rb["rc"], "output": rb["output"][-400:],
               "verified": verified, "verify_output": verify_output}
        records.append(rec)
        if rb["rc"] != 0 or (strict and verified is not True):
            ok = False
    if strict and not ok:
        # Do not restart services on top of a partially-restored file set.
        return records, False
    plan = nl.transaction_activation_plan(steps)
    acts, aok = _execute_activation(con, bundle, plan, i,
                                    health_groups=health_groups,
                                    phase="rollback")
    records.extend(acts)
    return records, bool(ok and aok)


def run_group_rollback(con, bundle, group, steps, i, previous_hashes=None,
                       verify=False):
    """Restore one group and coalesce its restart/reload plan.

    With `previous_hashes` supplied this is strict (the deploy tool's recovery
    path).  The legacy call shape remains available for unit tests and manual
    helper use: a missing backup is recorded, not treated as a hard failure.
    """
    ph = previous_hashes or {}
    health = _group_health_checks(steps) if verify else []
    return run_transaction_rollback(con, bundle, steps, ph, i,
                                    health_groups=health, strict=bool(verify))


def transaction_status(path):
    """Read a transaction journal/status WITHOUT touching the serial port.

    Returns a dict with ``state`` in COMPLETE / ACTIVE / INCOMPLETE, the last
    journal event, changed targets and a concrete recommended next action.
    """
    path = os.path.abspath(path)
    evdir = path if os.path.isdir(path) else os.path.dirname(path)
    status_path = os.path.join(evdir, "status.json")
    journal_path = (path if os.path.isfile(path) and path.endswith(".jsonl")
                    else os.path.join(evdir, "transaction.jsonl"))
    deployment_path = os.path.join(evdir, "deployment.json")
    status = {}
    try:
        with open(status_path) as fh:
            status = json.load(fh)
    except (OSError, ValueError):
        pass
    events = []
    try:
        with open(journal_path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    finished = next((e for e in reversed(events)
                     if e.get("event") == "finished"), None)
    deployment = None
    try:
        with open(deployment_path) as fh:
            deployment = json.load(fh)
    except (OSError, ValueError):
        pass

    pid = status.get("pid")
    pid_alive = bool(pid) and status.get("host") == __import__("socket").gethostname() \
        and nl._pid_alive(pid, status.get("pid_start"))
    if finished and deployment is not None:
        state = ("NEEDS_RECOVERY"
                 if (deployment or {}).get("verdict") == "NEEDS_RECOVERY"
                 else "COMPLETE")
    elif pid_alive:
        state = "ACTIVE"
    else:
        state = "INCOMPLETE"

    changed = []
    for r in (deployment or {}).get("results", []) or []:
        if r.get("changed") and r.get("target"):
            t = r["target"]
            if t not in changed:
                changed.append(t)
    for e in events:
        if e.get("event") == "verified" and e.get("changed"):
            t = e.get("target")
            if t and t not in changed and str(t).startswith("/dev/") is False:
                changed.append(t)
    last = events[-1] if events else {}
    if state == "COMPLETE":
        action = "none — transaction recorded as finished"
    elif state == "NEEDS_RECOVERY":
        action = ("rollback did not verify; keep the console available and inspect each "
                  "changed target's recorded .nuxel-rollback.pre-<op-id> backup "
                  "before retrying")
    elif state == "ACTIVE":
        action = "wait for the recorded owner; do not start another deploy or remove its lock"
    elif changed:
        action = ("inspect changed targets; if the process is gone and its flock is free, "
                  "restore each recorded .nuxel-rollback before retrying")
    else:
        action = "no target was verified changed; re-run a dry-run/preflight before any deploy"
    return {"evidence_dir": evdir, "journal": journal_path,
            "state": state, "pid": pid, "pid_alive": pid_alive,
            "operation_id": status.get("operation_id") or
            (deployment or {}).get("operation_id"),
            "verdict": (deployment or {}).get("verdict") or
            (finished or {}).get("verdict"),
            "last_event": last, "changed_targets": changed,
            "lock": (nl.lock_status_text(status["target"])
                     if status.get("target") else None),
            "recommended_action": action}


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
    ap.add_argument("--operation-id", default=None,
                    help="stable id recorded in the lock owner sidecar + journal")
    ap.add_argument("--lock-status", action="store_true",
                    help="print advisory lock ownership for --dev and exit "
                         "(never opens the serial port)")
    ap.add_argument("--transaction-status", default=None, metavar="DIR",
                    help="read an evidence dir/journal and report COMPLETE/ACTIVE/"
                         "INCOMPLETE without opening the serial port")
    ap.add_argument("--block-lines", type=int, default=8,
                    help="base64 lines per acknowledged block (default 4)")
    ap.add_argument("--block-bytes", type=int, default=3072,
                    help="max bytes in one raw block write (default 2048)")
    ap.add_argument("--no-resume", action="store_true",
                    help="discard an existing verified part prefix instead of resuming")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    op_id = args.operation_id or make_operation_id()

    if args.transaction_status:
        doc = transaction_status(args.transaction_status)
        if args.json:
            print(json.dumps(doc, indent=2, sort_keys=True))
        else:
            print("# transaction: %s (%s)" % (doc["state"], doc["operation_id"]))
            print("# evidence: %s" % doc["evidence_dir"])
            print("# verdict: %s; last event: %s"
                  % (doc["verdict"], doc["last_event"].get("event")))
            if doc["changed_targets"]:
                print("# changed targets: %s" % ", ".join(doc["changed_targets"]))
            print("# next: %s" % doc["recommended_action"])
        return 0

    if args.lock_status:
        dev = args.dev
        if not dev:
            try:
                dev = nl.select_console_node(nl.enumerate_console_nodes())["callout"]
            except nl.SelectionError as e:
                print("# lock-status: %s" % e, file=sys.stderr)
                return 2
        print("# %s" % nl.lock_status_text(dev))
        return 0

    repo = nl.repo_root_from_here()
    man_path = args.manifest or os.path.join(repo, "tools", "beta", "live",
                                             "deploy-manifest.json")
    ev_root = args.evidence_dir or os.path.join(repo, "docs", "beta-finalization",
                                                "live", "evidence")
    nl.ensure_not_qq(ev_root)
    bundle = nl.EvidenceBundle(ev_root, name=args.name, label="deploy")
    bundle.op_id = op_id
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
    # A per-transaction backup captures the bytes actually present immediately
    # before this run.  The long-lived `.nuxel-rollback` baseline is preserved
    # separately (created only when absent).
    for step in plan["steps"]:
        step["txn_backup"] = step["backup"] + ".pre-" + slug(op_id)
    index = write_plan_artifacts(bundle, plan, repo)
    bundle.journal({"event": "planned", "steps": len(plan["steps"]),
                    "groups": [g.get("group") for g in plan.get("group_order", [])],
                    "activation_plan": plan.get("activation_plan")})
    report = {"briq": "briq-10b-live-deploy-userspace",
              "operation_id": op_id,
              "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "evidence_dir": bundle.dir,
              "manifest": os.path.relpath(man_path, repo), "apply": bool(args.apply),
              "order": args.order, "steps": len(plan["steps"]),
              "groups": plan.get("group_order"), "risk_envelope": plan.get("risk_envelope"),
              "skipped": plan["skipped"],
              "violations": plan["violations"], "results": [], "verdict": None,
              "boot_id_before": None, "boot_id_after": None,
              "boot_id_changed": None, "cancelled": False,
              "transfer": {}, "journal": os.path.join(bundle.dir, "transaction.jsonl")}

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
    reporter = DeployReporter(bundle, op_id, node["callout"])
    cancelled = {"flag": False}

    def _sigint(signum, frame):
        # Cooperative cancellation: stop at the next safe boundary.  A remote
        # command already handed to the device may still finish; this handler
        # never claims otherwise and never releases the port lock mid-frame.
        cancelled["flag"] = True
        try:
            reporter.log({"event": "signal", "signal": int(signum)})
            reporter.state_change("cancellation requested at next safe boundary",
                                  force="CANCELLED")
        except (ValueError, OSError):
            pass

    old_handler = signal.signal(signal.SIGINT, _sigint)
    con = None
    all_results, activations, rollbacks = [], [], []
    changed_steps, previous_hashes = [], {}
    transfer_totals = {"bytes": 0, "elapsed_s": 0.0, "retries": 0,
                       "raw_writes": 0, "blocks": 0, "parts": 0,
                       "ack_writes": 0, "write_bytes": 0, "resumes": 0}
    try:
        try:
            con = nl.Console(node["callout"], timeout=args.timeout,
                             lock_wait=args.lock_wait, op_id=op_id)
            con.open()
        except nl.ConsoleLost as e:
            report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
            report["blocked_reason"] = "cannot take the console: %s" % e
            reporter.log({"event": "connect_failed", "error": str(e)})
            return finish(bundle, report, args, 3)
        reporter.state_change("connected", force="CONNECTED_IDLE")
        try:
            probe = con.probe(6.0)
            report["probe"] = probe.as_dict()
            if not probe.reachable:
                report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
                report["blocked_reason"] = ("console %s is byte-silent: refusing to write "
                                            "to a device that cannot confirm the result"
                                            % node["callout"])
                reporter.state_change("console byte-silent", force="FAILED")
                return finish(bundle, report, args, 3)

            # Record the device identity before mutating anything.  A bridge
            # restart is NOT a phone reboot; boot_id is how we prove that.
            boot_before = con.run("cat /proc/sys/kernel/random/boot_id 2>/dev/null")
            report["boot_id_before"] = boot_before.output.strip()[:64] if boot_before.ok else None
            reporter.log({"event": "boot_id_before",
                          "boot_id": report["boot_id_before"]})
            report["pid"] = os.getpid()
            report["pid_start"] = nl._proc_start_ticks(os.getpid())
            report["host"] = __import__("socket").gethostname()

            steps = plan["steps"]
            reconnects = 0
            report["reconnects"] = []

            def reopen_console(where, error):
                nonlocal con, reconnects
                if reconnects >= 8:
                    return False
                reconnects += 1
                report["reconnects"].append({"at": where, "error": str(error)})
                reporter.state_change("reconnecting (attempt %d): %s"
                                      % (reconnects, error), force="RECONNECTING")
                con.close()
                waited = 0.0
                while waited < args.reconnect_timeout:
                    time.sleep(3)
                    waited += 3
                    try:
                        reopened = nl.Console(node["callout"], timeout=args.timeout,
                                              lock_wait=args.lock_wait, op_id=op_id)
                        reopened.open()
                        if reopened.probe(6.0).reachable:
                            con = reopened
                            reporter.state_change("reconnected", force="CONNECTED_IDLE")
                            reporter.log({"event": "reconnected", "attempt": reconnects,
                                          "waited_s": waited})
                            return True
                        reopened.close()
                    except nl.ConsoleLost:
                        pass
                reporter.log({"event": "reconnect_failed", "attempts": reconnects,
                              "error": str(error)})
                return False

            groups, by_group = [], {}
            for step in steps:
                g = by_group.get(step["group"])
                if g is None:
                    g = {"id": step["group"], "steps": []}
                    by_group[step["group"]] = g
                    groups.append(g)
                g["steps"].append(step)

            def add_transfer(rec):
                sp = rec.get("staged_push") or {}
                transfer_totals["bytes"] += int(sp.get("bytes") or 0)
                transfer_totals["elapsed_s"] += float(sp.get("elapsed_s") or 0.0)
                transfer_totals["retries"] += int(sp.get("retries") or 0)
                transfer_totals["raw_writes"] += int(sp.get("raw_writes") or 0)
                transfer_totals["blocks"] += int(sp.get("blocks") or 0)
                transfer_totals["parts"] += int(sp.get("parts") or 0)
                transfer_totals["ack_writes"] += int(sp.get("ack_writes") or 0)
                transfer_totals["write_bytes"] += int(sp.get("write_bytes") or 0)
                transfer_totals["resumes"] += 1 if sp.get("resume_used") else 0

            def transfer_report():
                return {
                    "bytes": transfer_totals["bytes"],
                    "elapsed_s": round(transfer_totals["elapsed_s"], 3),
                    "throughput_bytes_s": round(
                        transfer_totals["bytes"] / transfer_totals["elapsed_s"], 1)
                    if transfer_totals["elapsed_s"] > 0 else None,
                    "retries": transfer_totals["retries"],
                    "raw_writes": transfer_totals["raw_writes"],
                    "ack_writes": transfer_totals["ack_writes"],
                    "write_bytes": transfer_totals["write_bytes"],
                    "blocks": transfer_totals["blocks"],
                    "parts": transfer_totals["parts"],
                    "resumes": transfer_totals["resumes"],
                }

            def capture_boot_after():
                try:
                    boot_after = con.run(
                        "cat /proc/sys/kernel/random/boot_id 2>/dev/null")
                    report["boot_id_after"] = (boot_after.output.strip()[:64]
                                               if boot_after.ok else None)
                except nl.ConsoleLost:
                    report["boot_id_after"] = None
                report["boot_id_changed"] = bool(
                    report["boot_id_before"] and report["boot_id_after"] and
                    report["boot_id_before"] != report["boot_id_after"])
                reporter.log({"event": "boot_id_after",
                              "boot_id": report["boot_id_after"],
                              "boot_id_changed": report["boot_id_changed"]})

            rollback_health = []

            def do_rollback(reason):
                nonlocal rollback_health
                if not changed_steps:
                    reporter.log({"event": "rolled_back", "reason": reason,
                                  "records": [], "nothing_changed": True})
                    return True
                reporter.state_change("rolling back transaction: %s" % reason,
                                      force="ROLLING_BACK")
                reporter.log({"event": "rolling_back", "reason": reason,
                              "targets": [s["target"] for s in changed_steps]})
                changed_ids = {s["group"] for s in changed_steps}
                rollback_health = _group_health_checks(
                    [s for s in steps if s["group"] in changed_ids])
                try:
                    rb, ok = run_transaction_rollback(
                        con, bundle, changed_steps, previous_hashes, 1,
                        health_groups=rollback_health)
                except nl.ConsoleLost as e:
                    reporter.log({"event": "rollback_console_lost", "error": str(e)})
                    if reopen_console("rollback", e):
                        try:
                            rb, ok = run_transaction_rollback(
                                con, bundle, changed_steps, previous_hashes, 1,
                                health_groups=rollback_health)
                        except Exception as exc:  # noqa: BLE001
                            rb, ok = [], False
                            reporter.log({"event": "rollback_error",
                                          "error": str(exc)})
                    else:
                        rb, ok = [], False
                except Exception as exc:  # noqa: BLE001 - report, never mask
                    rb, ok = [], False
                    reporter.log({"event": "rollback_error", "error": str(exc)})
                rollbacks.append({"group": "transaction", "ok": bool(ok),
                                  "reason": reason, "records": rb})
                reporter.log({"event": "rolled_back" if ok else "recovery_required",
                              "reason": reason, "ok": bool(ok)})
                try:
                    reporter.state_change("rolled back" if ok else "recovery required",
                                          force="ROLLED_BACK" if ok else "NEEDS_RECOVERY")
                except ValueError:
                    pass
                return bool(ok)

            def fail_after_rollback(reason, exit_if_recovered=5):
                rb_ok = do_rollback(reason)
                capture_boot_after()
                report["transfer"] = transfer_report()
                report["results"] = all_results
                report["activation"] = activations
                report["rollbacks"] = rollbacks
                report["health"] = [a for a in activations
                                    if a.get("kind") in ("health", "rollback-health")]
                report["rollback_ok"] = bool(rb_ok)
                if rb_ok:
                    report["verdict"] = "FAILED"
                    report["blocked_reason"] = reason
                    try:
                        reporter.state_change("failed", force="FAILED")
                    except ValueError:
                        pass
                    return finish(bundle, report, args, exit_if_recovered)
                report["verdict"] = "NEEDS_RECOVERY"
                report["blocked_reason"] = (reason + "; rollback did not verify — "
                                            "operator recovery is required")
                reporter.state_change("recovery required", force="NEEDS_RECOVERY")
                return finish(bundle, report, args, 6)

            # --- stage every selected file before any service is touched ----
            reporter.state_change("staging %d files in %d groups"
                                  % (len(steps), len(groups)), force="DEPLOY_STAGING")
            reporter.log({"event": "staging", "steps": len(steps),
                          "groups": [g["id"] for g in groups]})
            stage_failed = False
            offset = 0
            for g in groups:
                gid = g["id"]
                gsteps = g["steps"]
                reporter.log({"event": "group_staging", "group": gid,
                              "files": len(gsteps)})
                for j, step in enumerate(gsteps):
                    n = offset + j + 1
                    if cancelled["flag"]:
                        raise nl.OperationCancelled(
                            "operator cancelled before step %d (%s)"
                            % (n, step["target"]))
                    reporter.log({"event": "staging", "step": n, "group": gid,
                                  "target": step["target"],
                                  "source_sha256": step["source_sha256"]})
                    tries = 0
                    while True:
                        try:
                            rec = run_step(
                                con, bundle, step, n, progress=reporter.progress,
                                cancel_check=lambda: cancelled["flag"],
                                block_lines=args.block_lines,
                                block_bytes=args.block_bytes,
                                resume=not args.no_resume)
                            tries += 1
                            if rec["ok"] or tries >= 3:
                                break
                            time.sleep(1)
                        except nl.OperationCancelled:
                            raise
                        except nl.ConsoleLost as e:
                            if not reopen_console("step %d" % n, e):
                                report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
                                report["blocked_reason"] = (
                                    "console lost after %d reconnects during "
                                    "staging step %d: %s" % (reconnects, n, e))
                                return finish(bundle, report, args, 3)
                            continue
                    rec["attempts"] = tries
                    all_results.append(rec)
                    add_transfer(rec)
                    reporter.log({"event": "staged" if rec["ok"] else "stage_failed",
                                  "step": n, "group": gid,
                                  "target": step["target"],
                                  "changed": bool(rec.get("changed")),
                                  "previous_hash": rec.get("previous_hash"),
                                  "installed_hash": rec.get("installed_hash"),
                                  "bytes": (rec.get("staged_push") or {}).get("bytes"),
                                  "elapsed_s": rec.get("elapsed_s"),
                                  "throughput_bytes_s":
                                      (rec.get("staged_push") or {}).get(
                                          "throughput_bytes_s"),
                                  "retries": (rec.get("staged_push") or {}).get("retries"),
                                  "transport_mode":
                                      (rec.get("staged_push") or {}).get("mode"),
                                  "fallback":
                                      (rec.get("staged_push") or {}).get("fallback", False)})
                    if rec["ok"]:
                        if rec.get("changed"):
                            changed_steps.append(step)
                            previous_hashes[step["target"]] = rec.get("previous_hash")
                        reporter.log({"event": "verified", "step": n, "group": gid,
                                      "target": step["target"],
                                      "changed": bool(rec.get("changed")),
                                      "installed_hash": rec.get("installed_hash")})
                    else:
                        if rec.get("changed"):
                            changed_steps.append(step)
                            previous_hashes[step["target"]] = rec.get("previous_hash")
                        stage_failed = True
                        break
                offset += len(gsteps)
                if stage_failed:
                    break

            report["transfer"] = transfer_report()
            if stage_failed:
                return fail_after_rollback(
                    "staging failed; the transaction was rolled back before any "
                    "service reload/restart")

            if cancelled["flag"]:
                raise nl.OperationCancelled(
                    "operator cancelled before activation; staged files are being restored")

            # --- one coalesced activation for the WHOLE transaction ---------
            activation = nl.transaction_activation_plan(changed_steps)
            report["planned_activation_plan"] = plan.get("activation_plan")
            report["executed_activation_plan"] = activation
            report["changed_steps"] = len(changed_steps)
            report["no_op"] = not bool(changed_steps)
            reporter.state_change("activating transaction (%d changed files, "
                                  "%d reloads, %d restarts)"
                                  % (len(changed_steps),
                                     len(activation.get("reloads") or []) +
                                     (1 if activation.get("daemon_reload_action") else 0),
                                     len(activation.get("restarts") or [])),
                                  force="DEPLOY_ACTIVATING")
            reporter.log({"event": "activating", "plan": activation,
                          "changed_steps": len(changed_steps)})
            try:
                acts, ok = run_transaction_activation(con, bundle, changed_steps,
                                                      steps, 1)
            except nl.ConsoleLost as e:
                reporter.log({"event": "activation_console_lost", "error": str(e)})
                if not reopen_console("activation", e):
                    return fail_after_rollback(
                        "console lost during activation and did not reconnect: %s" % e)
                try:
                    acts, ok = run_transaction_activation(con, bundle, changed_steps,
                                                          steps, 1)
                    report["activation_retried_after_reconnect"] = True
                except nl.ConsoleLost as e2:
                    return fail_after_rollback(
                        "console lost again during retried activation: %s" % e2)
            activations.extend(acts)
            for a in acts:
                reporter.log({"event": "activation_record", "record": a})
            if cancelled["flag"]:
                raise nl.OperationCancelled(
                    "operator cancelled after activation; rolling back the transaction")
            reporter.log({"event": "activated", "ok": bool(ok),
                          "counts": {
                              "daemon_reloads": sum(
                                  1 for a in acts if a.get("kind") == "daemon-reload"),
                              "reloads": sum(1 for a in acts if a.get("kind") == "reload"),
                              "restarts": sum(
                                  1 for a in acts if a.get("kind") == "restart") +
                                  sum(len(a.get("restart_services") or [])
                                      for a in acts if a.get("kind") == "reload"),
                              "health_checks": sum(1 for a in acts if a.get("kind") == "health"),
                          }})
            if not ok:
                return fail_after_rollback(
                    "activation/health check failed; every changed file was restored "
                    "to its recorded previous hash")
            reporter.state_change("health checks passed; committing",
                                  force="HEALTH_CHECK")
            capture_boot_after()
            report["transfer"] = transfer_report()
            report["results"] = all_results
            report["activation"] = activations
            report["rollbacks"] = rollbacks
            report["health"] = [a for a in activations if a.get("kind") == "health"]
            report["activation_counts"] = {
                "daemon_reloads": sum(1 for a in activations
                                      if a.get("kind") == "daemon-reload"),
                "reloads": sum(1 for a in activations if a.get("kind") == "reload"),
                "restarts": sum(1 for a in activations
                                if a.get("kind") == "restart") +
                            sum(len(a.get("restart_services") or [])
                                for a in activations if a.get("kind") == "reload"),
                "health_checks": sum(1 for a in activations if a.get("kind") == "health"),
            }
            report["verdict"] = ("VERIFIED_ON_S10PLUS" if args.observation
                                 else "DEPLOYED_UNVERIFIED")
            report["observation"] = args.observation
            report["verdict_note"] = (
                ("no-op: every selected target already matched its source hash; "
                 "no reload/restart was performed. " if report["no_op"] else
                 "files staged, hash-verified, atomically installed and the "
                 "transaction's coalesced reload/restart actions run once. ") +
                ("DEPLOYED_UNVERIFIED means the deploy succeeded but no "
                 "human-visible behaviour was observed."
                 if not args.observation else
                 "upgraded on the strength of a recorded on-device observation: %s"
                 % args.observation))
            reporter.log({"event": "committed", "verdict": report["verdict"],
                          "no_op": report["no_op"],
                          "activation_counts": report["activation_counts"]})
            reporter.state_change("committed", force="SUCCEEDED")
            return finish(bundle, report, args, 0)
        except nl.OperationCancelled as e:
            report["cancelled"] = True
            report["verdict"] = "CANCELLED"
            report["blocked_reason"] = str(e)
            reporter.log({"event": "cancelled", "reason": str(e),
                          "changed_steps": len(changed_steps)})
            rb_ok = do_rollback("operator cancelled: %s" % e)
            capture_boot_after()
            report["transfer"] = transfer_report()
            report["results"] = all_results
            report["activation"] = activations
            report["rollbacks"] = rollbacks
            report["rollback_ok"] = bool(rb_ok)
            if not rb_ok:
                report["verdict"] = "NEEDS_RECOVERY"
                reporter.state_change("cancelled; recovery required",
                                      force="NEEDS_RECOVERY")
                return finish(bundle, report, args, 6)
            try:
                reporter.state_change("cancelled and rolled back",
                                      force="CANCELLED")
            except ValueError:
                pass
            return finish(bundle, report, args, 130)
        finally:
            if con is not None:
                con.close()
                con = None
    finally:
        signal.signal(signal.SIGINT, old_handler)


def finish(bundle, report, args, code):
    report["exit_code"] = code
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["verdicts"] = {"briq-10b-live-deploy-userspace":
                          report["verdict"] or "BLOCKED_EXTERNAL_RESOURCE"}
    bundle.journal({"event": "finished", "verdict": report["verdict"],
                    "exit_code": code, "pid": os.getpid(),
                    "no_op": report.get("no_op"),
                    "rollback_ok": report.get("rollback_ok")})
    bundle.write_json("status.json", {
        "operation_id": report.get("operation_id"),
        "state": ("NEEDS_RECOVERY" if report.get("verdict") == "NEEDS_RECOVERY"
                  else ("COMPLETE" if code in (0, 3, 4, 5, 130) else "INCOMPLETE")),
        "verdict": report.get("verdict"), "exit_code": code,
        "pid": os.getpid(), "pid_start": nl._proc_start_ticks(os.getpid()),
        "host": __import__("socket").gethostname(),
        "finished_at": report["finished_at"],
        "no_op": report.get("no_op"),
        "changed_steps": report.get("changed_steps"),
        "rollback_ok": report.get("rollback_ok"),
        "blocked_reason": report.get("blocked_reason"),
    })
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
        if report.get("transfer"):
            t = report["transfer"]
            print("# transfer: %s bytes, %s s, %s B/s, retries %s, "
                  "raw writes %s, blocks %s, parts %s"
                  % (t.get("bytes"), t.get("elapsed_s"),
                     t.get("throughput_bytes_s"), t.get("retries"),
                     t.get("raw_writes"), t.get("blocks"), t.get("parts")))
        if report.get("activation_counts") is not None:
            c = report["activation_counts"]
            print("# activation: daemon-reload %s, reloads %s, restarts %s, "
                  "health %s, no-op %s"
                  % (c.get("daemon_reloads"), c.get("reloads"),
                     c.get("restarts"), c.get("health_checks"),
                     bool(report.get("no_op"))))
        print("# manifest: %s" % man)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

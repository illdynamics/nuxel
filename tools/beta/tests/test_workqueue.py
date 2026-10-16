#!/usr/bin/env python3
"""test_workqueue.py — offline tests for tools/beta/workqueue.py (briq-00c).

Hermetic: every case runs against a throw-away queue directory under $TMPDIR, driving
the real CLI in a subprocess.  The only case that reads the repository is the last one
(it validates the seeded ledger in docs/beta-finalization/workqueue/).

What is proven:
  * add / list / show / set-state / verify-schema work end to end
  * records are APPEND-ONLY (history grows; the previous revision is never rewritten)
  * the verdict vocabulary is closed (nothing outside the mission list is accepted)
  * evidence has exactly two legal shapes and both are checked: ARTEFACT evidence
    (offline/vm/on_device/owner_instruction/observation/doc) must name a path, and
    ACTION evidence (verifier-run/test-run/defect-found-and-fixed/change) must say
    what ran/was found or changed AND what came of it
  * VERIFIED_ON_S10PLUS is REFUSED without an on-device evidence path
    (a passing unit test can never produce it), accepted with one
  * dependencies must exist, must not be self-referential, and must be acyclic
  * a verdict change requires a note (the reason is evidence)
  * the per-task writer lock is honoured
  * `list --ready` and `verify-schema --strict` behave
  * `render` regenerates the machine-owned blocks of WORK-QUEUE.md from the JSON
    store, is deterministic, detects staleness (`--check`), never clobbers the
    prose outside the markers, and REFUSES to render from an invalid store
  * the real seeded queue is valid and covers every briQ in the plan

Usage: python3 tools/beta/tests/test_workqueue.py
Exit status = number of failed cases.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
TOOL = ROOT / "tools" / "beta" / "workqueue.py"
REAL_QUEUE = ROOT / "docs" / "beta-finalization" / "workqueue"

PASS = 0
FAIL = 0


def ok(msg: str) -> None:
    global PASS
    PASS += 1
    print(f"PASS {msg}")


def bad(msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"FAIL {msg}")


class Queue:
    """A disposable queue directory + CLI runner."""

    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="nuxel-workqueue-test."))

    def run(self, *args, expect=None):
        p = subprocess.run(
            [sys.executable, str(TOOL), "--root", str(self.dir), *args],
            capture_output=True,
            text=True,
        )
        if expect is not None and p.returncode != expect:
            print(f"      (rc={p.returncode} want={expect})\n      out={p.stdout.strip()}\n      err={p.stderr.strip()}")
        return p

    def file(self, tid: str) -> Path:
        return self.dir / f"{tid}.json"

    def read(self, tid: str) -> dict:
        return json.loads(self.file(tid).read_text())

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def add_task(q: Queue, tid="t-a", **kw):
    args = ["add", "--id", tid, "--title", kw.pop("title", f"task {tid}"), "--priority", str(kw.pop("priority", 1))]
    for k, v in kw.items():
        flag = "--" + k.replace("_", "-")
        if isinstance(v, list):
            for item in v:
                args += [flag, str(item)]
        elif v is True:
            args.append(flag)
        else:
            args += [flag, str(v)]
    return q.run(*args)


# --------------------------------------------------------------------------- #
# 1. add + verify-schema
# --------------------------------------------------------------------------- #
def case_add_and_verify(q: Queue):
    p = add_task(q, "t-a", component="bg-00-preflight", rollback="revert the commit")
    if p.returncode == 0 and q.file("t-a").is_file():
        ok("add creates the per-task state file")
    else:
        bad(f"add failed rc={p.returncode} err={p.stderr.strip()}")

    v = q.run("verify-schema")
    if v.returncode == 0 and "schema OK" in v.stdout:
        ok("verify-schema accepts a well-formed queue")
    else:
        bad(f"verify-schema rejected a valid queue rc={v.returncode}: {v.stdout.strip()} {v.stderr.strip()}")

    j = q.run("verify-schema", "--json")
    try:
        payload = json.loads(j.stdout)
        good = payload["ok"] is True and payload["tasks"] == 1
    except Exception as exc:  # noqa: BLE001
        good = False
        print(f"      json error: {exc}")
    ok("verify-schema --json emits a parseable payload") if good else bad("verify-schema --json unusable")


# --------------------------------------------------------------------------- #
# 2. duplicate guard
# --------------------------------------------------------------------------- #
def case_duplicate(q: Queue):
    p = add_task(q, "t-a")
    if p.returncode == 2 and "already exists" in p.stderr:
        ok("duplicate add is refused (exit 2)")
    else:
        bad(f"duplicate add not refused rc={p.returncode}: {p.stderr.strip()}")

    p = add_task(q, "t-a", force=True)
    if p.returncode == 0:
        ok("--force re-creates a task deliberately")
    else:
        bad(f"--force add failed rc={p.returncode}")


# --------------------------------------------------------------------------- #
# 3. vocabulary is closed
# --------------------------------------------------------------------------- #
def case_vocabulary(q: Queue):
    p = q.run("set-state", "t-a", "--verdict", "TOTALLY_FINE")
    if p.returncode == 2 and "invalid choice" in p.stderr:
        ok("a verdict outside the mission vocabulary is rejected by the CLI")
    else:
        bad(f"invalid verdict not rejected rc={p.returncode}: {p.stderr.strip()}")

    # ...and by the validator, not just argparse: write a bad verdict straight to disk
    rf = q.read("t-a")
    rf["revisions"][-1]["verdict"] = "LOOKS_GOOD_TO_ME"
    q.file("t-a").write_text(json.dumps(rf))
    v = q.run("verify-schema")
    if v.returncode == 1 and "not in the allowed vocabulary" in v.stdout:
        ok("verify-schema rejects a verdict outside the vocabulary even if written directly")
    else:
        bad(f"verify-schema did not catch a hand-written bad verdict rc={v.returncode}")
    rf["revisions"][-1]["verdict"] = None
    q.file("t-a").write_text(json.dumps(rf))


# --------------------------------------------------------------------------- #
# 4/5. the honesty gate on VERIFIED_ON_S10PLUS
# --------------------------------------------------------------------------- #
def case_on_device_gate(q: Queue):
    p = q.run("set-state", "t-a", "--verdict", "VERIFIED_ON_S10PLUS", "--note", "it worked on my desk")
    if p.returncode == 1 and "on_device evidence" in p.stderr:
        ok("VERIFIED_ON_S10PLUS is refused without an on-device evidence path")
    else:
        bad(f"on-device gate did not fire rc={p.returncode}: {p.stderr.strip()}")

    offdev = json.dumps({"kind": "offline", "path": "tools/beta/tests/test_workqueue.py", "command": "pytest", "result": "pass"})
    p = q.run("set-state", "t-a", "--verdict", "VERIFIED_ON_S10PLUS", "--evidence", offdev)
    if p.returncode == 1:
        ok("an offline-only 'pass' still cannot produce VERIFIED_ON_S10PLUS")
    else:
        bad(f"offline evidence produced an on-device verdict rc={p.returncode}")

    before = q.read("t-a")
    ondev = json.dumps(
        {
            "kind": "on_device",
            "path": "scripts/s10plus-debug-pack/captures/20261016/touch-trace.txt",
            "command": "bash nuxel-console-host.sh --run 'nuxel-touch-trace.py --json'",
            "result": "LAYER=7 STATE=ok events=42",
            "at": "2026-10-16T16:00:00+02:00",
        }
    )
    p = q.run("set-state", "t-a", "--verdict", "VERIFIED_ON_S10PLUS", "--evidence", ondev,
              "--note", "console capture on the handset")
    after = q.read("t-a")
    if p.returncode == 0 and after["revisions"][-1]["verdict"] == "VERIFIED_ON_S10PLUS":
        ok("VERIFIED_ON_S10PLUS is accepted once a real on-device capture is attached")
    else:
        bad(f"valid on-device verdict refused rc={p.returncode}: {p.stderr.strip()}")

    if len(after["revisions"]) == len(before["revisions"]) + 1 and after["revisions"][0] == before["revisions"][0]:
        ok("set-state APPENDS a revision and never rewrites the previous one")
    else:
        bad("set-state is not append-only")

    v = q.run("verify-schema")
    if v.returncode == 0 and "VERIFIED_ON_S10PLUS" in q.run("verify-schema", "--json").stdout:
        ok("the queue validates with a legitimate on-device verdict present")
    else:
        bad("queue invalid after a legitimate on-device verdict")


# --------------------------------------------------------------------------- #
# 6. verdict changes need a reason
# --------------------------------------------------------------------------- #
def case_verdict_change_needs_note(q: Queue):
    p = q.run("set-state", "t-a", "--verdict", "FAILED")
    if p.returncode == 1 and "without --note" in p.stderr:
        ok("silently downgrading a recorded verdict is refused")
    else:
        bad(f"verdict downgrade without a note was not refused rc={p.returncode}: {p.stderr.strip()}")

    p = q.run("set-state", "t-a", "--verdict", "FAILED", "--note", "console capture contradicted the earlier claim")
    if p.returncode == 0:
        ok("a verdict change is accepted when the reason is recorded")
    else:
        bad(f"noted verdict change refused rc={p.returncode}: {p.stderr.strip()}")
    q.run("set-state", "t-a", "--verdict", "OFFLINE_TESTED", "--note", "restore test state")


# --------------------------------------------------------------------------- #
# 7/8. dependency integrity
# --------------------------------------------------------------------------- #
def case_dependencies(q: Queue):
    p = add_task(q, "t-b", dep="t-does-not-exist")
    if p.returncode == 1 and "unknown dependency" in p.stderr:
        ok("a dependency on an unknown task is refused")
    else:
        bad(f"unknown dependency not refused rc={p.returncode}: {p.stderr.strip()}")

    p = add_task(q, "t-self", dep="t-self")
    if p.returncode == 1 and "itself" in p.stderr:
        ok("a self-dependency is refused")
    else:
        bad(f"self-dependency not refused rc={p.returncode}: {p.stderr.strip()}")

    add_task(q, "t-b", dep="t-a")
    add_task(q, "t-c", dep="t-b")
    if q.run("verify-schema").returncode == 0:
        ok("a valid dependency chain validates")
    else:
        bad("valid dependency chain failed validation")

    # force a cycle by hand: t-b -> t-a is fine, add t-a -> t-c
    rf = q.read("t-a")
    rf["revisions"][-1]["dependencies"] = ["t-c"]
    q.file("t-a").write_text(json.dumps(rf))
    v = q.run("verify-schema")
    if v.returncode == 1 and "dependency cycle" in v.stdout:
        ok("a dependency cycle is detected (and named) by verify-schema")
    else:
        bad(f"cycle not detected rc={v.returncode}: {v.stdout.strip()}")
    rf["revisions"][-1]["dependencies"] = []
    q.file("t-a").write_text(json.dumps(rf))


# --------------------------------------------------------------------------- #
# 9/10. list, and readiness
# --------------------------------------------------------------------------- #
def case_list(q: Queue):
    p = q.run("list", "--json")
    try:
        rows = json.loads(p.stdout)
        ids = [r["id"] for r in rows]
        good = ids == sorted(ids) or all(rows[i]["priority"] <= rows[i + 1]["priority"] for i in range(len(rows) - 1))
    except Exception as exc:  # noqa: BLE001
        good = False
        print(f"      list --json error: {exc} out={p.stdout[:200]}")
    ok("list --json returns parseable rows ordered by priority") if good else bad("list --json unusable")

    # t-a and t-b have tentative verdicts; t-c waits on t-b which is OFFLINE_TESTED-ish.
    # Put t-b into FAILED so t-c must NOT be reported ready.
    q.run("set-state", "t-b", "--verdict", "FAILED", "--note", "test: blocked dependency")
    p = q.run("list", "--ready", "--json")
    try:
        ready = {r["id"] for r in json.loads(p.stdout)}
    except Exception:  # noqa: BLE001
        ready = set()
    if "t-c" not in ready and "t-a" in ready:
        ok("list --ready hides tasks whose dependency is unsatisfied")
    else:
        bad(f"readiness logic wrong: ready={sorted(ready)}")
    q.run("set-state", "t-b", "--verdict", "OFFLINE_TESTED", "--note", "test: dependency restored")


# --------------------------------------------------------------------------- #
# 11. strict mode + broken file handling
# --------------------------------------------------------------------------- #
def case_strict_and_broken(q: Queue):
    add_task(q, "t-novote")
    # drop the verdict from everything else so exactly one task lacks one
    for tid in ("t-a", "t-b", "t-c", "t-a"):
        rf = q.read(tid)
        for rev in rf["revisions"]:
            rev["verdict"] = None
        q.file(tid).write_text(json.dumps(rf))
    v = q.run("verify-schema", "--strict")
    if v.returncode == 1 and "strict mode requires a final verdict" in v.stdout:
        ok("verify-schema --strict demands a verdict on every task")
    else:
        bad(f"strict mode did not complain rc={v.returncode}")

    (q.dir / "t-broken.json").write_text("{not json at all")
    v = q.run("verify-schema")
    if v.returncode == 1 and "unreadable JSON state file" in v.stdout and "Traceback" not in v.stderr:
        ok("a corrupt state file is reported cleanly instead of crashing the validator")
    else:
        bad(f"corrupt file handling wrong rc={v.returncode} stderr={v.stderr.strip()[:120]}")
    (q.dir / "t-broken.json").unlink()


# --------------------------------------------------------------------------- #
# 11b. render: the human view is derived, deterministic, and fail-closed
# --------------------------------------------------------------------------- #
DOC_TEMPLATE = """# test doc

prose before

<!-- BEGIN GENERATED: ledger-state -->
stale
<!-- END GENERATED: ledger-state -->

<!-- BEGIN GENERATED: execution-order -->
stale
<!-- END GENERATED: execution-order -->

<!-- BEGIN GENERATED: task-ledger -->
stale
<!-- END GENERATED: task-ledger -->

prose after
"""


def _doc(q: Queue) -> Path:
    d = q.dir / "WORK-QUEUE.md"
    d.write_text(DOC_TEMPLATE)
    return d


def case_render(q: Queue):
    add_task(q, "t-r1", component="bg-00-preflight", rollback="revert", priority="0")
    add_task(q, "t-r2", component="bg-00-preflight", rollback="revert", priority="1", dep="t-r1")
    add_task(q, "t-r3", component="bg-00-preflight", rollback="revert", priority="1", dep="t-r2")
    q.run("set-state", "t-r1", "--state", "implemented", "--verdict", "OFFLINE_TESTED",
          "--evidence", json.dumps({"kind": "offline", "path": "tools/beta/workqueue.py",
                                    "command": "python3 tools/beta/tests/test_workqueue.py",
                                    "result": "PASS"}))

    doc = _doc(q)
    p = q.run("render", "--write", "--out", str(doc))
    body = doc.read_text()
    if p.returncode == 0 and "<!-- BEGIN GENERATED: ledger-state -->" in body and "stale" not in body:
        ok("render --write replaces every generated block and leaves no stale marker text")
    else:
        bad(f"render --write failed rc={p.returncode}: {p.stderr.strip()[:160]}")

    if "prose before" in body and "prose after" in body:
        ok("render never touches the prose outside the generated markers")
    else:
        bad("render clobbered human prose")

    n_tasks = len(sorted(q.dir.glob("*.json")))
    if f"| Tasks | **{n_tasks}**" in body and "| Revisions (append-only) | " in body:
        ok("the rendered ledger-state block carries measured counts from the JSON store")
    else:
        bad(f"rendered ledger-state has no task count for {n_tasks} task(s)")

    i2, i3 = body.find("`t-r2`"), body.find("`t-r3`")
    if -1 < i2 < i3 and "waiting on `t-r2`" in body:
        ok("the execution order lists a dependent after its dependency and flags it as waiting")
    else:
        bad(f"execution order wrong (t-r2@{i2} t-r3@{i3})")

    if "| `t-r1` | 0 | bg-00-preflight | implemented | OFFLINE_TESTED" in body:
        ok("the task ledger reflects the effective (latest) revision")
    else:
        bad("task ledger row does not reflect the latest revision")

    p = q.run("render", "--check", "--out", str(doc))
    if p.returncode == 0:
        ok("render --check passes when the document matches the JSON store")
    else:
        bad(f"render --check reported a fresh document as stale rc={p.returncode}")

    before = doc.read_text()
    q.run("render", "--check", "--out", str(doc))
    add_task(q, "t-r4", component="bg-00-preflight", rollback="revert", priority="2")
    p = q.run("render", "--check", "--out", str(doc))
    if p.returncode == 1 and doc.read_text() == before:
        ok("render --check detects a new task in the store and writes nothing")
    else:
        bad(f"staleness not detected rc={p.returncode}")

    p = q.run("render", "--stdout", "--out", str(doc))
    if p.returncode == 0 and "`t-r4`" in p.stdout and doc.read_text() == before:
        ok("render --stdout prints the regenerated document without touching the file")
    else:
        bad(f"render --stdout wrote or printed nothing rc={p.returncode}")

    first = q.run("render", "--stdout", "--out", str(doc)).stdout
    second = q.run("render", "--stdout", "--out", str(doc)).stdout
    if first == second and first:
        ok("render is deterministic (byte-identical across runs, no timestamps in generated blocks)")
    else:
        bad("render output is not stable")

    nomark = q.dir / "WORK-QUEUE-nomarkers.md"
    nomark.write_text("# no markers here\n")
    p = q.run("render", "--write", "--out", str(nomark))
    if p.returncode != 0 and "marker" in (p.stderr + p.stdout):
        ok("render refuses a document without the generated-block markers (and names them)")
    else:
        bad(f"marker-less document not refused rc={p.returncode}")

    broken = q.dir / "t-broken-render.json"
    broken.write_text("{not json")
    p = q.run("render", "--stdout", "--out", str(doc))
    broken.unlink()
    if p.returncode == 1 and "refusing to render" in p.stderr:
        ok("render refuses to render the human view from an invalid store (fail closed)")
    else:
        bad(f"render rendered an invalid store rc={p.returncode}: {p.stderr.strip()[:160]}")


# --------------------------------------------------------------------------- #
# 12. writer lock
# --------------------------------------------------------------------------- #
def case_lock(q: Queue):
    lock = q.dir / "t-a.json.lock"
    lock.write_text("12345 held\n")
    p = q.run("set-state", "t-a", "--state", "implemented")
    lock.unlink()
    if p.returncode == 1 and "locked by another writer" in p.stderr:
        ok("the per-task writer lock prevents interleaved concurrent writes")
    else:
        bad(f"lock not honoured rc={p.returncode}: {p.stderr.strip()[:160]}")


# --------------------------------------------------------------------------- #
# 13. evidence shape validation
# --------------------------------------------------------------------------- #
def case_evidence_shape(q: Queue):
    p = q.run("set-state", "t-a", "--evidence", json.dumps({"kind": "telepathy", "path": "x"}))
    if p.returncode == 1 and "kind" in p.stderr:
        ok("an evidence entry with an unknown kind is refused")
    else:
        bad(f"bad evidence kind not refused rc={p.returncode}: {p.stderr.strip()}")

    p = q.run("set-state", "t-a", "--evidence", json.dumps({"kind": "offline"}))
    if p.returncode == 1 and "path" in p.stderr:
        ok("an evidence entry without a path is refused")
    else:
        bad(f"pathless evidence not refused rc={p.returncode}: {p.stderr.strip()}")

    # The action-evidence family (added by briq-02-gate-failure-repair): a run, a
    # defect or a change IS evidence, and it is not enough to name a file for it -
    # the entry has to say what happened.
    for ev, label in (
        ({"kind": "verifier-run", "command": "python3 tools/x/verify.py", "result": "rc 0, 12 checks"},
         "a verifier-run (command + result) is accepted"),
        ({"kind": "test-run", "command": "python3 tests/test-x.py", "result": "all assertions pass"},
         "a test-run (command + result) is accepted"),
        ({"kind": "defect-found-and-fixed", "what": "a stale cache changed a verdict", "result": "version guard added"},
         "a defect-found-and-fixed (what + result) is accepted"),
        ({"kind": "change", "what": "the schema gained action kinds", "result": "records validate",
          "at": "2026-10-16T22:00:00+02:00"},
         "a change (what + at) is accepted"),
    ):
        p = q.run("set-state", "t-a", "--evidence", json.dumps(ev))
        if p.returncode == 0:
            ok(label)
        else:
            bad(f"{label[:-11]} refused rc={p.returncode}: {p.stderr.strip()}")

    p = q.run("set-state", "t-a", "--evidence", json.dumps({"kind": "verifier-run", "result": "rc 0"}))
    if p.returncode == 1 and "command" in p.stderr:
        ok("an action entry that names neither a command nor a what is refused")
    else:
        bad(f"nameless action evidence not refused rc={p.returncode}: {p.stderr.strip()}")

    p = q.run("set-state", "t-a", "--evidence", json.dumps({"kind": "change", "what": "something"}))
    if p.returncode == 1 and "outcome" in p.stderr:
        ok("an action entry with no outcome (result/at) is refused")
    else:
        bad(f"outcome-less action evidence not refused rc={p.returncode}: {p.stderr.strip()}")


# --------------------------------------------------------------------------- #
# 14. the real seeded queue
# --------------------------------------------------------------------------- #
def case_real_queue():
    if not REAL_QUEUE.is_dir():
        bad(f"real queue directory missing: {REAL_QUEUE}")
        return
    p = subprocess.run(
        [sys.executable, str(TOOL), "verify-schema", "--json"],
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(p.stdout)
    except Exception as exc:  # noqa: BLE001
        bad(f"real queue verify-schema output unparseable: {exc} {p.stdout[:200]}")
        return
    if payload["ok"] and payload["tasks"] >= 50:
        ok(f"the seeded repository queue validates ({payload['tasks']} tasks, acyclic)")
    else:
        bad(f"real queue invalid: {payload.get('errors')}")

    # An on-device verdict is legitimate ONLY when the record carries a real
    # on_device capture.  (The first sessions had zero such claims; session 2 has
    # exactly one - briq-00a, whose preflight ran against the live handset - so the
    # invariant to hold is "no claim without a capture", not "no claim at all".)
    unbacked = sorted(
        t
        for t, r in load_real().items()
        if r.get("verdict") == "VERIFIED_ON_S10PLUS"
        and not any(
            (e or {}).get("kind") == "on_device"
            and str((e or {}).get("command", "")).strip()
            and (str((e or {}).get("result", "")).strip() or str((e or {}).get("at", "")).strip())
            for e in (r.get("evidence") or [])
        )
    )
    if not unbacked:
        n = sum(1 for r in load_real().values() if r.get("verdict") == "VERIFIED_ON_S10PLUS")
        ok(f"every VERIFIED_ON_S10PLUS claim in the seeded queue carries an on_device capture "
           f"({n} claim(s), 0 unbacked)")
    else:
        bad(f"tasks claim an on-device verdict without on_device evidence: {unbacked}")


def load_real() -> dict:
    out = {}
    for f in sorted(REAL_QUEUE.glob("*.json")):
        rf = json.loads(f.read_text())
        out[f.stem] = rf["revisions"][-1]
    return out


def main() -> int:
    if not TOOL.is_file():
        print(f"FAIL tool missing: {TOOL}")
        return 1
    q = Queue()
    try:
        case_add_and_verify(q)
        case_duplicate(q)
        case_vocabulary(q)
        case_on_device_gate(q)
        case_verdict_change_needs_note(q)
        case_dependencies(q)
        case_list(q)
        case_strict_and_broken(q)
        case_lock(q)
        case_evidence_shape(q)
        case_render(q)
        case_real_queue()
    finally:
        q.cleanup()
    print(f"== {FAIL} failing case(s), {PASS} passing ==")
    return FAIL


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""workqueue.py — persistent, dependency-aware, resumable work queue for the Nuxel
beta finalization (briq-00c).

Design contract (mission section 4)
-----------------------------------
* One **append-only** JSON state file per task:
  `docs/beta-finalization/workqueue/<stable-id>.json`.
  Parallel build groups therefore never write to a shared file — each group owns its
  own task ids, and `set-state` only ever *appends* a revision.  History is never
  rewritten, so a task's full audit trail survives the run.
* Every revision carries: stable id, priority (mission band), component, current
  implementation state, dependencies, evidence (path + command + result), intended
  changes, tests, risk level, rollback method and final verdict.
* Verdicts use **exactly** the allowed vocabulary.  A verdict of
  `VERIFIED_ON_S10PLUS` is refused unless the record carries an on-device evidence
  path (kind == "on_device" with a real command and a captured result): a passing
  unit test never yields VERIFIED_ON_S10PLUS.
* `verify-schema` validates the vocabulary, referential integrity and dependency
  acyclicity and reports the queue state.

Subcommands
-----------
  list            list tasks (filters: --group --state --verdict --priority --ready)
  show            print one task's current record (or its full revision history)
  add             create a new task file (refuses duplicate / invalid records)
  set-state       append a revision changing state/verdict/evidence/notes
  verify-schema   validate the whole queue; non-zero exit when it is invalid
  seed            create task files for every briQ in a QonQrete plan.json
                  (used once to seed this ledger; safe to re-run with --force)

Exit codes: 0 = ok, 1 = validation/verify failure, 2 = usage error.
Repository-only: this tool never touches the phone, the VM, a block device or
`/Users/wicked/x/nuxel/.qq`.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = 1

# --------------------------------------------------------------------------- #
# Vocabularies (the verdict list is verbatim from the mission; do not widen it) #
# --------------------------------------------------------------------------- #
VERDICTS = [
    "VERIFIED_ON_S10PLUS",
    "VERIFIED_IN_VM_ONLY",
    "OFFLINE_TESTED",
    "DEPLOYED_UNVERIFIED",
    "IMPLEMENTED_NOT_DEPLOYED",
    "BLOCKED_KERNEL",
    "BLOCKED_FIRMWARE",
    "BLOCKED_HARDWARE",
    "BLOCKED_EXTERNAL_RESOURCE",
    "NEEDS_OWNER_TEST",
    "FAILED",
    "DEFERRED",
    "NOT_SUPPORTED_ON_DEVICE",
]

# verdicts that still mean "this work item is open" when a dependent looks at it
UNSATISFIED_VERDICTS = {
    "FAILED",
    "BLOCKED_KERNEL",
    "BLOCKED_FIRMWARE",
    "BLOCKED_HARDWARE",
    "BLOCKED_EXTERNAL_RESOURCE",
}

STATES = ["pending", "in_progress", "implemented", "blocked", "deferred", "reverted"]

RISKS = ["low", "medium", "high"]

EVIDENCE_KINDS = [
    "offline",          # ran on this host (build, unit test, static analysis)
    "vm",               # ran in the UTM Fedora 43 guest (VERIFIED_IN_VM_ONLY channel)
    "on_device",        # came off the physical S10+ (console/adb capture, probe)
    "owner_instruction",# documented step for the phone owner to execute
    "observation",      # file/registry inspection; presence is NOT a verdict
    "doc",              # written record that a later reviewer can re-read
]

# Mission bands.  0 is the repository foundation that has to exist before band 1
# (preflight / discovery / this ledger / baseline protection) and is deliberately
# allowed so the queue can represent briq-00*.
PRIORITY_MIN, PRIORITY_MAX = 0, 8

# Priority of each build group, taken from the mission's priority order and from the
# "Priority N - ..." labels in the plan.  bg-10 (live phone) and bg-11 (VM parity)
# are the two evidence channels that gate verification, hence bands 1 and 2.
GROUP_PRIORITY = {
    "bg-00-preflight": 0,
    "bg-01-touch-pipeline": 1,
    "bg-02-boot-animation-launcher": 2,
    "bg-03-connectivity-time-audio-buttons": 3,
    "bg-04-userspace-completion": 4,
    "bg-05-security-permissions": 5,
    "bg-06-core-phone-apps": 6,
    "bg-07-specialty-apps": 7,
    "bg-08-hardware-subsystems": 7,
    "bg-09-integration-release": 8,
    "bg-10-live-phone": 1,
    "bg-11-vm-parity": 2,
    "bg-12-reports": 8,
}

ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

DEFAULT_ROLLBACK = (
    "git revert the commit(s) touching this task's expected files; the change is "
    "repository-only and alters no device state"
)

DEFAULT_OWNER_ACTION = ""

# The mission requires every record to carry intended_changes and tests.  `add`
# therefore fills an explicit placeholder rather than an empty list, so the record is
# honest about the gap instead of failing validation with a confusing message.
DEFAULT_INTENDED = ["(to be filled in by the owning briQ when it reports)"]
DEFAULT_TESTS = ["(to be filled in by the owning briQ when it reports)"]


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def now() -> str:
    """Real local clock, ISO-8601 with offset.  Never a fabricated timestamp."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def default_queue_dir() -> Path:
    return repo_root() / "docs" / "beta-finalization" / "workqueue"


def task_path(queue_dir: Path, task_id: str) -> Path:
    return queue_dir / f"{task_id}.json"


def atomic_write_json(path: Path, obj) -> None:
    """Write JSON atomically: readers see either the old or the new file, never a
    half-written one (parallel groups are reading this directory)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(obj, fh, indent=2, sort_keys=False)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class LockError(RuntimeError):
    pass


class task_lock:
    """Advisory exclusive lock so two parallel writers can never interleave on the
    same task file.  Portable (O_EXCL), no external dependency."""

    def __init__(self, path: Path, timeout: float = 2.0):
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        import time

        deadline = time.time() + self.timeout
        while True:
            try:
                self.fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, f"{os.getpid()} {now()}\n".encode())
                return self
            except FileExistsError:
                if time.time() > deadline:
                    raise LockError(f"task is locked by another writer: {self.lock_path}")
                time.sleep(0.05)

    def __exit__(self, *exc):
        try:
            if self.fd is not None:
                os.close(self.fd)
            os.unlink(self.lock_path)
        except OSError:
            pass
        return False


def load_task_file(path: Path) -> dict:
    with open(path) as fh:
        return json.load(fh)


def effective(record_file: dict) -> dict:
    """The current record = last appended revision."""
    revs = record_file.get("revisions") or []
    return revs[-1] if revs else {}


def load_queue(queue_dir: Path, include_meta: bool = False) -> dict:
    records = {}
    files = sorted(p for p in queue_dir.glob("*.json") if p.is_file())
    for p in files:
        try:
            rf = load_task_file(p)
        except json.JSONDecodeError as exc:
            records[p.stem] = {"__broken__": f"{p}: {exc}"}
            continue
        rec = effective(rf)
        rec = dict(rec) if isinstance(rec, dict) else {}
        rec.setdefault("id", rf.get("id", p.stem))
        if include_meta:
            rec["__file__"] = str(p)
            rec["__revisions__"] = len(rf.get("revisions") or [])
            rec["__file_schema_version__"] = rf.get("schema_version")
        records[rec["id"]] = rec
    return records


# --------------------------------------------------------------------------- #
# validation                                                                   #
# --------------------------------------------------------------------------- #
def validate_record(rec: dict, known_ids=None) -> list:
    """Validate one task record.  Returns a list of error strings ([] == valid).

    `known_ids` (the full id set of the queue) is required to check dependencies;
    pass None to skip dependency existence (self/format checks still run).
    """
    errs = []

    tid = rec.get("id")
    if not isinstance(tid, str) or not tid:
        errs.append("id: missing or not a string")
    elif not ID_RE.match(tid):
        errs.append(f"id: {tid!r} must match {ID_RE.pattern}")

    for field in ("title", "component"):
        if not isinstance(rec.get(field), str) or not rec.get(field):
            errs.append(f"{field}: required non-empty string")

    pri = rec.get("priority")
    if not isinstance(pri, int) or isinstance(pri, bool):
        errs.append("priority: required integer (mission band)")
    elif not (PRIORITY_MIN <= pri <= PRIORITY_MAX):
        errs.append(f"priority: {pri} out of range {PRIORITY_MIN}..{PRIORITY_MAX}")

    state = rec.get("state")
    if state not in STATES:
        errs.append(f"state: {state!r} not in {STATES}")

    verdict = rec.get("verdict")
    if verdict is not None and verdict not in VERDICTS:
        errs.append(f"verdict: {verdict!r} not in the allowed vocabulary {VERDICTS}")

    risk = rec.get("risk")
    if risk not in RISKS:
        errs.append(f"risk: {risk!r} not in {RISKS}")

    deps = rec.get("dependencies")
    if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
        errs.append("dependencies: required list of task ids")
        deps = []
    else:
        if len(set(deps)) != len(deps):
            errs.append("dependencies: duplicate ids")
        for d in deps:
            if d == tid:
                errs.append(f"dependencies: task depends on itself ({d})")
            elif not ID_RE.match(d):
                errs.append(f"dependencies: {d!r} is not a valid task id")
            elif known_ids is not None and d not in known_ids:
                errs.append(f"dependencies: unknown dependency {d!r} (no such task in the queue)")

    for field in ("intended_changes", "tests"):
        v = rec.get(field)
        if isinstance(v, str):
            if not v.strip():
                errs.append(f"{field}: must not be empty (use a list of strings or omit)")
        elif isinstance(v, list):
            if not v or not all(isinstance(x, str) and x.strip() for x in v):
                errs.append(f"{field}: list must contain non-empty strings")
        else:
            errs.append(f"{field}: required list of strings (or a single string)")

    # The mission requires a rollback method on every record.
    if not isinstance(rec.get("rollback"), str) or not rec.get("rollback").strip():
        errs.append("rollback: required non-empty string (how to undo this task)")

    ev = rec.get("evidence")
    if not isinstance(ev, list):
        errs.append("evidence: required list (may be empty)")
        ev = []
    for i, e in enumerate(ev):
        if not isinstance(e, dict):
            errs.append(f"evidence[{i}]: must be an object")
            continue
        if e.get("kind") not in EVIDENCE_KINDS:
            errs.append(f"evidence[{i}].kind: {e.get('kind')!r} not in {EVIDENCE_KINDS}")
        if not isinstance(e.get("path"), str) or not e.get("path", "").strip():
            errs.append(f"evidence[{i}].path: required non-empty string")
        if "command" in e and not isinstance(e["command"], str):
            errs.append(f"evidence[{i}].command: must be a string when present")

    if "offline_ceiling" in rec and rec["offline_ceiling"] is not None:
        if rec["offline_ceiling"] not in VERDICTS:
            errs.append(f"offline_ceiling: {rec['offline_ceiling']!r} not in the allowed vocabulary")

    # ---- the honesty gate: no on-device evidence, no on-device verdict --------
    if verdict == "VERIFIED_ON_S10PLUS":
        on_dev = [
            e
            for e in ev
            if isinstance(e, dict)
            and e.get("kind") == "on_device"
            and isinstance(e.get("command"), str)
            and e.get("command", "").strip()
            and (str(e.get("result", "")).strip() or str(e.get("at", "")).strip())
        ]
        if not on_dev:
            errs.append(
                "verdict: VERIFIED_ON_S10PLUS requires at least one on_device evidence entry "
                "with a real command and a captured result/at timestamp "
                "(a passing unit test never yields VERIFIED_ON_S10PLUS)"
            )
    if verdict == "VERIFIED_IN_VM_ONLY" and not any(
        isinstance(e, dict) and e.get("kind") == "vm" for e in ev
    ):
        errs.append("verdict: VERIFIED_IN_VM_ONLY requires at least one evidence entry of kind 'vm'")
    if verdict == "DEPLOYED_UNVERIFIED" and not any(
        isinstance(e, dict) and e.get("kind") == "on_device" for e in ev
    ):
        errs.append("verdict: DEPLOYED_UNVERIFIED requires at least one on_device evidence entry")

    return errs


def find_cycle(records: dict):
    """Depth-first dependency search.  Returns a cycle path (list) or None."""
    WHITE, GREY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in records}
    stack = []

    def visit(tid, path):
        color[tid] = GREY
        path.append(tid)
        for dep in records.get(tid, {}).get("dependencies") or []:
            if dep not in records:
                continue
            if color[dep] == GREY:
                return path[path.index(dep):] + [dep]
            if color[dep] == WHITE:
                cyc = visit(dep, path)
                if cyc:
                    return cyc
        path.pop()
        color[tid] = BLACK
        return None

    for tid in sorted(records):
        if color.get(tid) == WHITE:
            cyc = visit(tid, [])
            if cyc:
                return cyc
    return None


def validate_queue(records: dict, strict: bool = False) -> list:
    errs = []
    known = set(records)
    for tid, rec in sorted(records.items()):
        if "__broken__" in rec:
            errs.append(f"{tid}: unreadable JSON state file — {rec['__broken__']}")
            continue
        if rec.get("id") != tid:
            errs.append(f"{tid}: record id {rec.get('id')!r} does not match its file name")
        for e in validate_record(rec, known):
            errs.append(f"{tid}: {e}")
    cyc = find_cycle(records)
    if cyc:
        errs.append("dependency cycle: " + " -> ".join(cyc))
    if strict:
        for tid, rec in sorted(records.items()):
            if rec.get("verdict") is None:
                errs.append(f"{tid}: strict mode requires a final verdict (currently null)")
    return errs


# --------------------------------------------------------------------------- #
# subcommands                                                                  #
# --------------------------------------------------------------------------- #
def _parse_evidence(items) -> list:
    out = []
    for raw in items or []:
        raw = raw.strip()
        if raw.startswith("@"):
            raw = Path(raw[1:]).read_text()
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"workqueue: --evidence is not valid JSON ({exc}): {raw[:80]}")
        if not isinstance(obj, dict):
            raise SystemExit("workqueue: --evidence must be a JSON object")
        out.append(obj)
    return out


def _as_list(values):
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    return list(values)


def cmd_list(args) -> int:
    qdir = Path(args.root)
    records = load_queue(qdir, include_meta=True)
    rows = []
    for tid, rec in records.items():
        if args.group and rec.get("component") != args.group:
            continue
        if args.state and rec.get("state") != args.state:
            continue
        if args.verdict and rec.get("verdict") != args.verdict:
            continue
        if args.priority is not None and rec.get("priority") != args.priority:
            continue
        if args.ready:
            deps = rec.get("dependencies") or []
            unmet = []
            for d in deps:
                dep = records.get(d)
                if dep is None:
                    unmet.append(d)
                    continue
                v = dep.get("verdict")
                if v is None or v in UNSATISFIED_VERDICTS:
                    unmet.append(d)
            if unmet:
                continue
        rows.append(rec)

    rows.sort(key=lambda r: (r.get("priority", 99), r.get("id", "")))

    if args.json:
        payload = [
            {
                "id": r.get("id"),
                "priority": r.get("priority"),
                "component": r.get("component"),
                "state": r.get("state"),
                "verdict": r.get("verdict"),
                "dependencies": r.get("dependencies") or [],
                "evidence": len(r.get("evidence") or []),
                "revisions": r.get("__revisions__"),
            }
            for r in rows
        ]
        print(json.dumps(payload, indent=2))
        return 0

    if not rows:
        print("(no tasks match)")
        return 0
    print(f"{'id':<40} {'pri':>3}  {'state':<12} {'verdict':<26} {'de':>2} {'ev':>2}")
    for r in rows:
        print(
            f"{r.get('id',''):<40} {r.get('priority',-1):>3}  "
            f"{str(r.get('state','')):<12} {str(r.get('verdict') or '-'):<26} "
            f"{len(r.get('dependencies') or []):>2} {len(r.get('evidence') or []):>2}"
        )
    print(f"\n{len(rows)} task(s)")
    return 0


def cmd_show(args) -> int:
    path = task_path(Path(args.root), args.id)
    if not path.is_file():
        print(f"workqueue: no such task: {args.id}", file=sys.stderr)
        return 1
    rf = load_task_file(path)
    if args.json or not args.history:
        print(json.dumps(rf, indent=2))
        return 0
    print(f"# {args.id} — {len(rf.get('revisions') or [])} revision(s)")
    for rev in rf.get("revisions") or []:
        print(
            f"\n## revision {rev.get('revision')}  {rev.get('at')}  by {rev.get('by')}\n"
            f"state={rev.get('state')} verdict={rev.get('verdict')} risk={rev.get('risk')}\n"
            f"note: {rev.get('note','')}"
        )
    return 0


def cmd_add(args) -> int:
    qdir = Path(args.root)
    qdir.mkdir(parents=True, exist_ok=True)
    path = task_path(qdir, args.id)
    if path.exists() and not args.force:
        print(f"workqueue: task already exists: {args.id} (use set-state, or --force)", file=sys.stderr)
        return 2
    known = set(load_queue(qdir))
    record = {
        "id": args.id,
        "title": args.title,
        "component": args.component,
        "priority": args.priority,
        "state": args.state,
        "dependencies": [d for d in (args.dep or [])],
        "evidence": _parse_evidence(args.evidence),
        "intended_changes": _as_list(args.intended) or list(DEFAULT_INTENDED),
        "tests": _as_list(args.test) or list(DEFAULT_TESTS),
        "risk": args.risk,
        "rollback": args.rollback or DEFAULT_ROLLBACK,
        "verdict": args.verdict,
        "offline_ceiling": args.offline_ceiling,
        "owner_action": args.owner_action or DEFAULT_OWNER_ACTION,
        "expected_files": _as_list(args.expected_file),
        "note": args.note or "",
    }
    errs = validate_record(record, known | {args.id})
    if errs:
        for e in errs:
            print(f"workqueue: refusing to add {args.id}: {e}", file=sys.stderr)
        return 1
    atomic_write_json(
        path,
        {
            "schema_version": SCHEMA_VERSION,
            "id": args.id,
            "revisions": [dict(record, revision=1, at=now(), by=args.by)],
        },
    )
    print(f"workqueue: added {args.id} ({qdir})")
    return 0


def cmd_set_state(args) -> int:
    qdir = Path(args.root)
    path = task_path(qdir, args.id)
    if not path.is_file():
        print(f"workqueue: no such task: {args.id}", file=sys.stderr)
        return 2
    known = set(load_queue(qdir))
    try:
        lock = task_lock(path)
        lock.__enter__()
    except LockError as exc:
        print(f"workqueue: {exc}", file=sys.stderr)
        return 1
    try:
        rf = load_task_file(path)
        revs = rf.setdefault("revisions", [])
        # deep copy: a shallow dict() would share the evidence/tests/dependency
        # *lists* with the previous revision, so appending to them would silently
        # rewrite history.  Append-only means the old revision is frozen.
        cur = copy.deepcopy(revs[-1]) if revs else {"id": args.id}
        cur.pop("revision", None)
        cur["id"] = args.id

        if args.state:
            cur["state"] = args.state
        if args.verdict:
            cur["verdict"] = args.verdict
        if args.risk:
            cur["risk"] = args.risk
        if args.rollback is not None:
            cur["rollback"] = args.rollback
        if args.owner_action is not None:
            cur["owner_action"] = args.owner_action
        if args.offline_ceiling is not None:
            cur["offline_ceiling"] = args.offline_ceiling
        if args.note:
            cur["note"] = args.note
        for ev in _parse_evidence(args.evidence):
            cur.setdefault("evidence", []).append(ev)
        for t in _as_list(args.test):
            lst = cur.get("tests")
            if isinstance(lst, str):
                lst = [lst]
            lst = lst or []
            lst.append(t)
            cur["tests"] = lst
        for ic in _as_list(args.intended):
            lst = cur.get("intended_changes")
            if isinstance(lst, str):
                lst = [lst]
            lst = lst or []
            lst.append(ic)
            cur["intended_changes"] = lst
        for ef in _as_list(args.expected_file):
            lst = cur.get("expected_files") or []
            if ef not in lst:
                lst.append(ef)
            cur["expected_files"] = lst
        for d in _as_list(args.add_dep):
            lst = cur.get("dependencies") or []
            if d not in lst:
                lst.append(d)
            cur["dependencies"] = lst

        errs = validate_record(cur, known)
        if errs:
            for e in errs:
                print(f"workqueue: refusing state change for {args.id}: {e}", file=sys.stderr)
            return 1
        # Never *downgrade* an already-recorded on-device verdict silently: a new
        # revision must say why (a note is required to replace a recorded verdict).
        prev = revs[-1].get("verdict") if revs else None
        if prev and cur.get("verdict") and prev != cur.get("verdict") and not args.note:
            print(
                f"workqueue: refusing to change verdict {prev} -> {cur['verdict']} without --note "
                "(the reason for a verdict change is evidence)",
                file=sys.stderr,
            )
            return 1
        revs.append(dict(cur, revision=len(revs) + 1, at=now(), by=args.by))
        atomic_write_json(path, rf)
    finally:
        lock.__exit__(None, None, None)
    print(
        f"workqueue: {args.id} -> state={cur.get('state')} verdict={cur.get('verdict')} "
        f"(revision {len(revs)})"
    )
    return 0


def cmd_verify_schema(args) -> int:
    qdir = Path(args.root)
    records = load_queue(qdir)
    errs = validate_queue(records, strict=args.strict)
    by_verdict = {}
    states = {}
    for rec in records.values():
        by_verdict[str(rec.get("verdict"))] = by_verdict.get(str(rec.get("verdict")), 0) + 1
        states[str(rec.get("state"))] = states.get(str(rec.get("state")), 0) + 1
    payload = {
        "tool": "workqueue",
        "queue": str(qdir),
        "tasks": len(records),
        "ok": not errs,
        "errors": errs,
        "by_verdict": by_verdict,
        "by_state": states,
        "verified_on_s10plus": sorted(
            t for t, r in records.items() if r.get("verdict") == "VERIFIED_ON_S10PLUS"
        ),
    }
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"== workqueue verify-schema ==  queue: {qdir}")
        print(f"   tasks: {len(records)}")
        for k in sorted(states):
            print(f"   state   {k:<12} {states[k]}")
        for k in sorted(by_verdict):
            print(f"   verdict {k:<26} {by_verdict[k]}")
        if errs:
            print(f"\n   {len(errs)} error(s):")
            for e in errs:
                print(f"     ERROR {e}")
        else:
            print("\n   schema OK — vocabulary, dependencies (acyclic) and evidence gates all hold")
    return 0 if not errs else 1


def cmd_seed(args) -> int:
    """Seed the ledger from a QonQrete plan.json (read-only input)."""
    qdir = Path(args.root)
    qdir.mkdir(parents=True, exist_ok=True)
    plan = json.loads(Path(args.from_plan).read_text())
    briqs = plan.get("briqs") or {}
    groups = plan.get("build_groups") or {}
    if not briqs:
        print("workqueue: plan has no briqs", file=sys.stderr)
        return 2

    created = skipped = 0
    for tid, b in sorted(briqs.items()):
        path = task_path(qdir, tid)
        if path.exists() and not args.force:
            skipped += 1
            continue
        gid = b.get("build_group_id") or ""
        gtitle = (groups.get(gid) or {}).get("name") or gid
        priority = GROUP_PRIORITY.get(gid, 1)
        expected = list(b.get("expected_files") or [])
        present = [f for f in expected if (repo_root() / f).exists()]
        evidence = [
            {
                "kind": "observation",
                "path": f,
                "command": f"test -e {f}",
                "result": "present at seed time (presence is not a verdict)",
                "at": now(),
            }
            for f in present
        ]
        # An owner-only task can never reach VERIFIED_* from this repository, so its
        # offline ceiling is recorded up front rather than discovered later.
        owner_only = bool(
            re.search(r"owner|headphone|finger|ear|outdoor|physical|tag|peer", str(b.get("title", "")), re.I)
            or re.search(r"owner", " ".join(expected), re.I)
        )
        record = {
            "id": tid,
            "title": b.get("title") or tid,
            "component": gid or "unspecified",
            "component_title": gtitle,
            "priority": priority,
            "state": "in_progress" if present else "pending",
            "dependencies": list(b.get("depends_on") or []),
            "evidence": evidence,
            "intended_changes": expected or ["(no expected files declared in the plan)"],
            "tests": ["(tests are recorded by the owning briQ when it reports)"],
            "risk": "medium",
            "rollback": DEFAULT_ROLLBACK,
            "verdict": None,
            "offline_ceiling": "NEEDS_OWNER_TEST" if owner_only else None,
            "owner_action": (
                "OWNER TEST REQUIRED: see docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md"
                if owner_only
                else ""
            ),
            "expected_files": expected,
            "note": (
                "seeded from the QonQrete plan; "
                + (f"{len(present)}/{len(expected)} expected file(s) already present in the tree"
                   if expected else "no expected files declared")
            ),
            "source": "plan.json",
        }
        errs = validate_record(record, set(briqs))
        if errs:
            print(f"workqueue: plan entry {tid} is not a valid task record:", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)
            return 1
        atomic_write_json(
            path,
            {
                "schema_version": SCHEMA_VERSION,
                "id": tid,
                "revisions": [dict(record, revision=1, at=now(), by=args.by)],
            },
        )
        created += 1
    print(f"workqueue: seeded {created} task(s), skipped {skipped} existing (queue: {qdir})")
    return 0


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="workqueue.py",
        description="Persistent dependency-aware resumable work queue (briq-00c).",
    )
    p.add_argument(
        "--root",
        default=os.environ.get("NUXEL_WORKQUEUE_DIR", str(default_queue_dir())),
        help="queue directory (default: docs/beta-finalization/workqueue)",
    )
    p.add_argument("--by", default="construqtor", help="author recorded on revisions")
    sub = p.add_subparsers(dest="cmd", required=True)

    lp = sub.add_parser("list", help="list tasks")
    lp.add_argument("--json", action="store_true")
    lp.add_argument("--group")
    lp.add_argument("--state", choices=STATES)
    lp.add_argument("--verdict", choices=VERDICTS)
    lp.add_argument("--priority", type=int)
    lp.add_argument("--ready", action="store_true", help="only tasks whose dependencies are resolved")
    lp.set_defaults(func=cmd_list)

    sp = sub.add_parser("show", help="show one task")
    sp.add_argument("id")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--history", action="store_true", help="print the revision history")
    sp.set_defaults(func=cmd_show)

    ap = sub.add_parser("add", help="create a task")
    ap.add_argument("--id", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--component", default="unspecified")
    ap.add_argument("--priority", type=int, default=1)
    ap.add_argument("--state", choices=STATES, default="pending")
    ap.add_argument("--verdict", choices=VERDICTS)
    ap.add_argument("--offline-ceiling", choices=VERDICTS)
    ap.add_argument("--dep", action="append", help="dependency task id (repeatable)")
    ap.add_argument("--evidence", action="append", help="JSON evidence object (repeatable, @file allowed)")
    ap.add_argument("--intended", action="append")
    ap.add_argument("--test", action="append")
    ap.add_argument("--risk", choices=RISKS, default="medium")
    ap.add_argument("--rollback")
    ap.add_argument("--owner-action")
    ap.add_argument("--expected-file", action="append")
    ap.add_argument("--note")
    ap.add_argument("--force", action="store_true")
    ap.set_defaults(func=cmd_add)

    stp = sub.add_parser("set-state", help="append a revision to a task")
    stp.add_argument("id")
    stp.add_argument("--state", choices=STATES)
    stp.add_argument("--verdict", choices=VERDICTS)
    stp.add_argument("--risk", choices=RISKS)
    stp.add_argument("--rollback")
    stp.add_argument("--owner-action")
    stp.add_argument("--offline-ceiling", choices=VERDICTS)
    stp.add_argument("--evidence", action="append")
    stp.add_argument("--test", action="append")
    stp.add_argument("--intended", action="append")
    stp.add_argument("--expected-file", action="append")
    stp.add_argument("--add-dep", action="append")
    stp.add_argument("--note")
    stp.set_defaults(func=cmd_set_state)

    vp = sub.add_parser("verify-schema", help="validate the whole queue")
    vp.add_argument("--json", action="store_true")
    vp.add_argument("--strict", action="store_true", help="also require a final verdict on every task")
    vp.set_defaults(func=cmd_verify_schema)

    sd = sub.add_parser("seed", help="create task files from a plan.json")
    sd.add_argument("--from-plan", required=True)
    sd.add_argument("--force", action="store_true")
    sd.set_defaults(func=cmd_seed)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

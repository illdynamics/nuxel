#!/usr/bin/env python3
"""Owner feedback through the real Nuxel Notes store (PWNAGE-46000).

The Notes app persists an array under Bridge storage key ``nuxel-notes``.  This
helper preserves every existing note and only edits the dedicated feedback note
identified by its stable id.  It never writes other note bodies.

Commands
  init [--run-id ID]                 create/preserve the dedicated note
  arm --test-id ID --instruction S   set CURRENT TEST and ANSWER: WAITING
  idle --instruction S               show instructions without an answer gate
  read                               print only the feedback note status
  wait --test-id ID [--timeout 30]   watch one answer, then confirm/rollback

``wait`` exits 0 pass, 1 fail/blank/timeout/expired, 2 Notes/Bridge unavailable.

Important: an externally armed note (the owner followed the agent's message and
typed WAITING themselves) is valid.  The baseline is the first observation in
this process, so the owner only has to change the ANSWER line from WAITING for
the current challenge.  A pre-existing ``yes`` is therefore always stale.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.request

API = os.environ.get("NUXEL_API_URL", "http://127.0.0.1:8080/api/v1/rpc")
TITLE = "PWNAGE-46000 Rotation Test Feedback"
DEFAULT_ID = "pwnage-46000-rotation-feedback"
ORIENTATIOND = os.environ.get("NUXEL_ORIENTATIOND", "/usr/libexec/nuxel/nuxel-orientationd")
ANSWER_RE = re.compile(r"^ANSWER:\s*(.*)$", re.MULTILINE)
TEST_RE = re.compile(r"^CURRENT TEST:\s*(.*)$", re.MULTILINE)
STATUS_PATH = "/run/nuxel-orientation/status.json"
REQUEST_PATH = "/run/nuxel-orientation/request.json"


def rpc(namespace, verb, params):
    body = json.dumps({"app_id": "nuxel-notes", "namespace": namespace,
                       "verb": verb, "params": params}).encode()
    req = urllib.request.Request(API, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def read_notes():
    doc = rpc("storage", "read", {"key": "nuxel-notes"})
    result = doc.get("result") if isinstance(doc, dict) else None
    if not isinstance(result, dict) or result.get("success") is False:
        raise RuntimeError("Notes store read failed: %r" % (result or doc))
    data = result.get("data")
    if data is None:
        return [], result
    if not isinstance(data, list):
        raise RuntimeError("Notes store is not an array")
    return data, result


def write_notes(notes):
    doc = rpc("storage", "write", {"key": "nuxel-notes", "data": notes})
    result = doc.get("result") if isinstance(doc, dict) else None
    if not isinstance(result, dict) or result.get("success") is False:
        raise RuntimeError("Notes store write failed: %r" % (result or doc))
    return result


def find_note(notes):
    for n in notes:
        if isinstance(n, dict) and (n.get("id") == DEFAULT_ID or
                                    (n.get("title") or "").strip() == TITLE):
            return n
    return None


def now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def initial_body(run_id):
    return (
        "PWNAGE-46000 ROTATION FEEDBACK\n"
        "Run ID: %s\n\n"
        "The agent will ask one physical test at a time.\n"
        "Keep this note open while testing.\n"
        "When the displayed orientation AND touch controls work correctly, "
        "replace WAITING with: yes (or works).\n"
        "If any part fails, type: no. You may also delete WAITING and leave the "
        "answer empty to report failure.\n"
        "Do not leave an old yes in place for a new test.\n\n"
        "CURRENT TEST: WAITING FOR AGENT\n"
        "ANSWER: WAITING\n"
        "OPTIONAL DETAILS:\n"
    ) % run_id


def answer_of(body):
    m = ANSWER_RE.search(body or "")
    return (m.group(1).strip() if m else "")


def test_of(body):
    m = TEST_RE.search(body or "")
    return (m.group(1).strip() if m else "")


def status():
    try:
        with open(STATUS_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def confirm(trial_id, answer, request_id=None):
    req = {"action": "confirm", "trial_id": trial_id, "answer": answer,
           "request_id": request_id or ("notes-%d-%d" % (os.getpid(), int(time.time() * 1000)))}
    try:
        os.makedirs(os.path.dirname(REQUEST_PATH), exist_ok=True)
        tmp = REQUEST_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(req, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, REQUEST_PATH)
        return True
    except OSError:
        return False


def _active_trial():
    st = status()
    trial = st.get("trial") or {}
    if not trial.get("pending_confirmation"):
        return None
    return trial


def cmd_init(args):
    notes, _ = read_notes()
    note = find_note(notes)
    changed = False
    if note is None:
        ts = now_iso()
        note = {"id": DEFAULT_ID, "title": TITLE, "body": initial_body(args.run_id),
                "createdAt": ts, "updatedAt": ts}
        notes.append(note)
        changed = True
    elif args.recreate_body:
        note["body"] = initial_body(args.run_id)
        note["updatedAt"] = now_iso()
        changed = True
    if changed:
        write_notes(notes)
    print(json.dumps({"ok": True, "created": changed, "note": {
        "id": note.get("id"), "title": note.get("title"),
        "updatedAt": note.get("updatedAt")}}, indent=2))
    return 0


def _rewrite_note(body):
    notes, _ = read_notes()
    note = find_note(notes)
    if note is None:
        raise RuntimeError("dedicated feedback note does not exist; run init")
    note["body"] = body
    note["updatedAt"] = now_iso()
    write_notes(notes)
    return note["updatedAt"]


def cmd_arm(args):
    body = (
        "PWNAGE-46000 ROTATION FEEDBACK\n"
        "CURRENT TEST: %s\n"
        "ANSWER: WAITING\n"
        "INSTRUCTIONS: %s\n"
        "OPTIONAL DETAILS:\n"
    ) % (args.test_id, args.instruction)
    ts = _rewrite_note(body)
    print(json.dumps({"ok": True, "test_id": args.test_id, "updatedAt": ts}, indent=2))
    return 0


def cmd_idle(args):
    body = (
        "PWNAGE-46000 ROTATION FEEDBACK\n"
        "CURRENT TEST: NONE (agent is working)\n"
        "ANSWER: -\n"
        "INSTRUCTIONS: %s\n"
        "OPTIONAL DETAILS:\n"
    ) % args.instruction
    ts = _rewrite_note(body)
    print(json.dumps({"ok": True, "updatedAt": ts}, indent=2))
    return 0


def cmd_read(args):
    notes, _ = read_notes()
    note = find_note(notes)
    if note is None:
        print(json.dumps({"ok": True, "missing": True}, indent=2))
        return 0
    print(json.dumps({"ok": True, "id": note.get("id"), "title": note.get("title"),
                      "updatedAt": note.get("updatedAt"),
                      "test": test_of(note.get("body")),
                      "answer": answer_of(note.get("body"))}, indent=2))
    return 0


def cmd_wait(args):
    """Watch exactly one challenge.

    The owner edits the open Notes note; the agent never rewrites it.  The
    challenge is bound to the daemon's trial id, so a stale ``yes`` from an
    earlier challenge can never commit a later transform.  The first observed
    answer is the baseline; PASS/FAIL requires the note timestamp or answer to
    change afterwards AND the daemon trial still to be pending.

    With ``--require-waiting`` the baseline answer must be WAITING, which proves
    the owner re-armed this exact challenge.
    """
    test_id = args.test_id or "unlabelled"
    deadline = time.monotonic() + args.timeout
    baseline = None
    polls = 0
    while time.monotonic() < deadline:
        notes, _ = read_notes()
        note = find_note(notes)
        polls += 1
        if note is None:
            raise RuntimeError("dedicated feedback note disappeared")
        body = note.get("body") or ""
        test = test_of(body)
        answer = answer_of(body)
        updated = note.get("updatedAt")
        trial = _active_trial()
        if args.trial_id and trial and (trial.get("id") or trial.get("request_id")) != args.trial_id:
            print(json.dumps({"event": "superseded_trial", "expected": args.trial_id,
                              "active": trial.get("id")}), flush=True)
            return 1
        if args.trial_id and not trial:
            print(json.dumps({"event": "expired", "trial": args.trial_id,
                              "answer": answer}), flush=True)
            return 1
        if baseline is None:
            baseline = {"updatedAt": updated, "answer": answer, "test": test}
            print(json.dumps({"event": "baseline", **baseline}), flush=True)
            if args.require_waiting and answer.strip().lower() != "waiting":
                print(json.dumps({"event": "not_armed", "answer": answer}), flush=True)
                return 2
        elif updated != baseline["updatedAt"] or answer != baseline["answer"]:
            low = answer.strip().lower()
            if low in ("yes", "works", "pass"):
                if not trial:
                    print(json.dumps({"event": "expired", "answer": answer}), flush=True)
                    return 1
                confirm(args.trial_id or trial.get("id") or trial.get("request_id") or test_id, "yes")
                print(json.dumps({"event": "pass", "answer": answer,
                                  "updatedAt": updated, "polls": polls,
                                  "trial": trial.get("id"), "test": test}), flush=True)
                return 0
            if low in ("no", "fail", "failed", ""):
                if trial:
                    confirm(args.trial_id or trial.get("id") or trial.get("request_id") or test_id,
                            low or "blank")
                print(json.dumps({"event": "fail", "answer": answer,
                                  "updatedAt": updated, "polls": polls, "test": test}), flush=True)
                return 1
        time.sleep(0.5)
    trial = _active_trial()
    if trial:
        confirm(args.trial_id or trial.get("id") or trial.get("request_id") or test_id, "blank")
        print(json.dumps({"event": "timeout", "test_id": test_id,
                          "polls": polls, "rolled_back": True}), flush=True)
    else:
        print(json.dumps({"event": "timeout_no_active_trial", "test_id": test_id,
                          "polls": polls}), flush=True)
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("--run-id", default="pwnage-46000-%d" % int(time.time()))
    p.add_argument("--recreate-body", action="store_true")
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("arm")
    p.add_argument("--test-id", required=True)
    p.add_argument("--instruction", default="Follow the agent's instructions.")
    p.set_defaults(fn=cmd_arm)
    p = sub.add_parser("idle")
    p.add_argument("--instruction", default="Agent is working; no test is active.")
    p.set_defaults(fn=cmd_idle)
    p = sub.add_parser("read")
    p.set_defaults(fn=cmd_read)
    p = sub.add_parser("wait")
    p.add_argument("--test-id", default="")
    p.add_argument("--trial-id", default="")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--require-waiting", action="store_true")
    p.set_defaults(fn=cmd_wait)
    args = ap.parse_args()
    try:
        return args.fn(args)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

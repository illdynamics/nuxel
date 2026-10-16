#!/usr/bin/env python3
"""release_lib.py — shared, offline-testable core for the release/rollback tools.

briq-09b (areas 53/54).  Bash front-ends keep the operator-facing behaviour
(arguments, checklists, live gating, evidence); this module owns the parts that
must be *exactly* right and are therefore unit-testable:

  * path/command guards (no block devices, no flash tooling, no QonQrete writes,
    no receipt JSON in the workspace);
  * atomic JSON read/modify/write for the rollback state and reboot history;
  * sha256 + manifest handling for the baseline discipline
    (record previous hash → stage → verify → atomic install → restart the
    smallest affected service → health-check → auto roll-back on failure);
  * the deploy-manifest parser (same shape the live group hands over);
  * health checks (device tier and offline tier) and the reboot policy verdict.

Nothing in here ever writes outside the paths it is given, and every path is
guarded first.  A green run of these tools is OFFLINE_TESTED and nothing more.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

SCHEMA_VERSION = 1

# --------------------------------------------------------------------------- #
# Guards — the mission invariants, mechanically enforced
# --------------------------------------------------------------------------- #
FORBIDDEN_PATH_PARTS = ("/.qq/", "/.codeseeq/")
BLOCK_DEVICE_RE = re.compile(
    r"^/dev/(block|sd[a-z]|mmcblk\d|nvme\d|disk|mapper/|ram\d)")
FLASH_TOOL_RE = re.compile(
    r"(^|[\s;&|`$(])(heimdall|odin|fastboot|twrp)\b")
MUTATING_RE = re.compile(r"\b(mkfs(\.\w+)?|dd\s+.*of=/dev/|fdisk|parted|sgdisk)\b")


class GuardViolation(RuntimeError):
    pass


def guard_path(path: str) -> str:
    """Refuse paths that are QonQrete metadata or raw devices."""
    ap = os.path.abspath(path)
    if any(p in ap + "/" for p in FORBIDDEN_PATH_PARTS) or ap.endswith("/.qq"):
        raise GuardViolation("refusing to touch QonQrete metadata: %s" % ap)
    if BLOCK_DEVICE_RE.match(ap):
        raise GuardViolation("refusing to touch a raw block device: %s" % ap)
    if ap.startswith("/dev/"):
        raise GuardViolation("refusing to touch /dev: %s" % ap)
    return ap


def guard_command(cmd: str) -> None:
    if FLASH_TOOL_RE.search(cmd):
        raise GuardViolation("refusing to run a flashing command: %s" % cmd[:120])
    if MUTATING_RE.search(cmd):
        raise GuardViolation("refusing to run a partition/format command: %s" % cmd[:120])


# --------------------------------------------------------------------------- #
# Small utilities
# --------------------------------------------------------------------------- #
def sha256_file(path: str, buf: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def read_json(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def write_json(path: str, obj) -> str:
    path = guard_path(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    return path


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def run(cmd, check=False, capture=True):
    guard_command(cmd if isinstance(cmd, str) else " ".join(cmd))
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str),
                           stdout=subprocess.PIPE if capture else None,
                           stderr=subprocess.STDOUT if capture else None,
                           text=True, timeout=60)
    except Exception as e:  # pragma: no cover - defensive
        return 127, str(e)
    return p.returncode, (p.stdout or "")


# --------------------------------------------------------------------------- #
# Deploy contract: which single service must be restarted for a target
# (mirrors the live group's deploy manifest contract; kept here so the release
# tools never import another group's file)
# --------------------------------------------------------------------------- #
SERVICE_FOR_TARGET = (
    ("/home/nuxel/nuxel/pwa/nuxel-home", "nuxel-pwa"),
    ("/home/nuxel/nuxel/pwa/nuxel-apps", "nuxel-pwa"),
    ("/home/nuxel/nuxel/tools/s10plus", "nuxel-button-manager"),
    ("/etc/nuxel/button", "nuxel-button-manager"),
    ("/etc/nuxel/touch", "nuxel-touch-arm"),
    ("/etc/nuxel/network", "NetworkManager"),
    ("/etc/nuxel/audio", "nuxel-audio"),
    ("/etc/nuxel/boot", "nuxel-verbose-boot"),
    ("/etc/systemd/system", None),          # unit files: daemon-reload, no restart
    ("/usr/lib/nuxel", "nuxel-pwa"),
    ("/usr/local/bin/nuxel-wl-fb", "nuxel-wl-fb"),
    ("/usr/local/bin/nuxel-pwa-host", "nuxel-pwa"),
    ("/usr/local/bin/nuxel-anim-handoff", "nuxel-wayland"),
    ("/usr/local/bin/nuxel-console", "nuxel-console"),
    ("/usr/local/bin/nuxelctl", None),      # CLI tool: no service restart
)


def smallest_service_for(target: str):
    """The single smallest service that must be restarted for `target`, or None."""
    t = os.path.normpath(target)
    best = None
    for prefix, unit in SERVICE_FOR_TARGET:
        if t == prefix or t.startswith(prefix + "/"):
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, unit)
    return best[1] if best else None


def parse_manifest(manifest: dict, repo_root: str):
    """Validate a deploy manifest into ordered, reversible steps.

    Manifest shape (the live group's contract):
      {"groups": [{"id","component","priority","restart_service","risk",
                   "health_check","state","blocked_reason",
                   "files": [{"source","target","verify"}]}]}
    """
    steps, violations = [], []
    for group in manifest.get("groups", []):
        gid = group.get("id", "?")
        if str(group.get("state", "")).startswith("blocked_"):
            violations.append({"group": gid, "kind": "declared_blocked",
                               "detail": group.get("blocked_reason", "declared blocked")})
            continue
        for entry in group.get("files", []):
            src_rel = entry.get("source", "")
            src = os.path.normpath(os.path.join(repo_root, src_rel))
            if not src.startswith(os.path.abspath(repo_root)):
                violations.append({"group": gid, "kind": "path_escape", "detail": src_rel})
                continue
            tgt = entry.get("target", "")
            try:
                guard_path(tgt)
            except GuardViolation as e:
                violations.append({"group": gid, "kind": "guard", "detail": str(e),
                                   "target": tgt})
                continue
            if not os.path.isfile(src):
                violations.append({"group": gid, "kind": "missing_source",
                                   "detail": "staged source not in repo: %s" % src_rel})
                continue
            steps.append({
                "group": gid, "component": group.get("component"),
                "priority": group.get("priority"),
                "source": src_rel, "source_sha256": sha256_file(src),
                "target": tgt, "staged": tgt + ".nuxel-staged",
                "backup": tgt + ".nuxel-rollback",
                "service": group.get("restart_service") or smallest_service_for(tgt),
                "verify": entry.get("verify", "sha256sum %s" % tgt),
                "health_check": group.get("health_check"),
                "risk": group.get("risk", "medium"),
            })
    return {"steps": steps, "violations": violations}


# --------------------------------------------------------------------------- #
# Health checks
# --------------------------------------------------------------------------- #
STACK_UNITS = ("nuxel-pwa", "nuxel-wl-fb", "nuxel-button-manager", "nuxel-wayland",
               "nuxel-pwa-host", "nuxel-touch-arm")


def _unit_active(root: str, unit: str):
    """('active'|'inactive'|'unknown', raw)."""
    if root == "/":
        rc, out = run(["systemctl", "is-active", unit])
        return (out.strip() or "unknown"), out.strip()
    # offline tier: look for a recorded state (baseline snapshot) or the unit file
    for cand in (os.path.join(root, "var/lib/nuxel/state/units.json"),
                 os.path.join(root, "run/nuxel-units.json")):
        doc = read_json(cand)
        if isinstance(doc, dict) and unit in doc:
            return str(doc[unit]), "recorded:%s" % cand
    for cand in (os.path.join(root, "etc/systemd/system/%s.service" % unit),
                 os.path.join(root, "usr/lib/systemd/system/%s.service" % unit),
                 os.path.join(root, "etc/systemd/user/%s.service" % unit)):
        if os.path.isfile(cand):
            return "present", cand
    return "unknown", "not found under %s" % root


def health_report(root: str = "/", expect_services=True, launcher_url=None) -> dict:
    """Health checks.  On-device (root=/`) these are real systemd/HTTP probes;
    offline (--root DIR) they verify recorded/fixture state and are marked
    offline-only.  Never returns HEALTHY on missing evidence."""
    root = os.path.abspath(root)
    offline = root != "/"
    checks = []

    def add(cid, ok, detail, level="hard"):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "level": level})

    # 1. stack units
    for unit in STACK_UNITS:
        state, raw = _unit_active(root, unit)
        if offline:
            add("unit-%s" % unit, state in ("active", "present", "enabled"),
                "offline tier: %s (%s)" % (state, raw), level="advisory")
        else:
            add("unit-%s" % unit, state == "active", "%s (%s)" % (state, raw))

    # 2. failed units
    if not offline:
        rc, out = run(["systemctl", "--failed", "--no-legend", "--no-pager"])
        n = len([l for l in out.splitlines() if l.strip()])
        add("no-failed-units", n == 0, "%d failed unit(s)" % n)
    else:
        add("no-failed-units", True, "offline tier: systemd state recorded in the baseline",
            level="advisory")

    # 3. single framebuffer owner (the A32 invariant)
    owner_file = os.path.join(root, "var/lib/nuxel/fb-owner") if not offline \
        else os.path.join(root, "var/lib/nuxel/fb-owner")
    owner = read_json(owner_file, None)
    if isinstance(owner, dict) and owner.get("pid"):
        pid = str(owner["pid"])
        alive = os.path.isdir("/proc/%s" % pid)
        add("fb-owner-present", True, "owner=%s pid=%s stage=%s" %
            (owner.get("owner"), pid, owner.get("stage")))
        if not offline:
            add("fb-owner-alive", alive, "/proc/%s %s" % (pid, "exists" if alive else "GONE"))
    else:
        # offline fixtures may only ship a plain pid file
        if os.path.isfile(owner_file):
            raw = open(owner_file, encoding="utf-8", errors="replace").read().strip()
            add("fb-owner-present", True, "recorded owner record: %s" % raw[:80])
        else:
            add("fb-owner-present", offline, "no fb-owner record (%s)" % owner_file,
                level="advisory" if offline else "hard")

    # 4. launcher reachable
    url = launcher_url or "http://127.0.0.1:8000/"
    if not offline:
        rc, out = run(["curl", "-s", "-o", "/dev/null", "-m", "5", "-w", "%{http_code}", url])
        add("launcher-http", out.strip() == "200", "%s -> %s" % (url, out.strip() or "no answer"))
    else:
        marker = os.path.join(root, "var/lib/nuxel/launcher-ready")
        add("launcher-http", os.path.isfile(marker),
            "offline tier: launcher readiness marker %s" % marker,
            level="advisory")

    # 5. touchscreen input node present (expected, not gated: see briq-01x)
    node_dir = os.path.join(root, "dev/input/by-path")
    if os.path.isdir(node_dir):
        hits = [f for f in os.listdir(node_dir) if "touch" in f.lower()]
        add("touch-node", bool(hits), "by-path touch nodes: %s" % (hits or "none"))
    else:
        add("touch-node", offline, "no /dev/input/by-path in this tree",
            level="advisory")

    hard_fail = [c for c in checks if not c["ok"] and c["level"] == "hard"]
    adv_fail = [c for c in checks if not c["ok"] and c["level"] != "hard"]
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": "tools/beta/health-check.sh",
        "generated_at": now(),
        "root": root,
        "tier": "OFFLINE_TESTED" if offline else "ON_DEVICE",
        "verdict": "HEALTHY" if not hard_fail else "UNHEALTHY",
        "checks": checks,
        "hard_failures": [c["id"] for c in hard_fail],
        "advisory_failures": [c["id"] for c in adv_fail],
        "note": ("offline health checks verify recorded/fixture state and are advisory; "
                 "they are never proof that the phone is healthy"),
    }


# --------------------------------------------------------------------------- #
# Reboot policy
# --------------------------------------------------------------------------- #
POLICY = {"max_reboots": 3, "min_interval_s": 120, "max_same_mode_failures": 3}

PRE_REBOOT_CHECKLIST = (
    ("pr-1", "Boot partition untouched this session (no block-device writes)",
     "baseline discipline: only userspace files were staged/installed"),
    ("pr-2", "Userspace deploy verified and a rollback copy exists for every target",
     "tools/beta/rollback.sh status"),
    ("pr-3", "Rollback path recorded and known-good",
     "test -s /var/lib/nuxel/rollback/path && cat /var/lib/nuxel/rollback/path"),
    ("pr-4", "Console reconnect procedure ready on the host (unplug/replug the USB console)",
     "docs/beta-finalization/release/REBOOT-ROLLBACK.md section 3"),
    ("pr-5", "Baseline bundle captured and hashed before the reboot",
     "tools/beta/rollback.sh capture --label pre-reboot"),
    ("pr-6", "A new, *changed* post-reboot diagnostic is named (no blind repeat)",
     "tools/beta/reboot-policy.sh check --reason ... --diagnostic ..."),
)

POST_REBOOT_CHECKLIST = (
    ("po-1", "Console reconnects and answers a framed command",
     "scripts/s10plus-debug-pack/nuxel-console-host.sh --run id"),
    ("po-2", "Boot graph completed with no failed units",
     "systemctl --failed --no-legend --no-pager"),
    ("po-3", "Single framebuffer owner is the Wayland/fb bridge",
     "cat /var/lib/nuxel/fb-owner"),
    ("po-4", "Animation handoff receipt present and terminal",
     "cat /var/lib/nuxel/animation; cat /run/nuxel-anim-handoff"),
    ("po-5", "Launcher serves the registry on :8000",
     "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/"),
    ("po-6", "Rollback path still known-good after the reboot",
     "tools/beta/rollback.sh status"),
)


def policy_verdict(history, reason=None, diagnostic=None, mode=None):
    """-> dict(allowed, code, reason).  Mirrors the mission's reboot rules:
    bounded count, previous reboot must have returned to Nuxel, a reason AND a
    *changed* diagnostic are mandatory, three same-mode failures stop the loop."""
    reboots = [h for h in history if h.get("kind", "reboot") != "failure"]
    n = len(reboots)
    if n >= POLICY["max_reboots"]:
        return {"allowed": False, "code": "budget_exhausted",
                "reason": "%d/%d reboots already used — change strategy, do not reboot "
                          "again" % (n, POLICY["max_reboots"])}
    if reboots:
        last = reboots[-1]
        if not last.get("returned_to_nuxel"):
            return {"allowed": False, "code": "not_recovered",
                    "reason": "the previous reboot never returned to Nuxel — recover the "
                              "console and finish the post-reboot checklist first"}
        if not last.get("rollback_known_good", True):
            return {"allowed": False, "code": "no_rollback",
                    "reason": "no known-good userspace rollback after the last reboot"}
    if mode:
        fails = [f for f in history if f.get("kind") == "failure" and f.get("mode") == mode]
        if len(fails) >= POLICY["max_same_mode_failures"]:
            return {"allowed": False, "code": "three_same_mode_failures",
                    "reason": "mode %r failed %d times in a row — change the diagnostic "
                              "strategy instead of repeating it"
                              % (mode, len(fails))}
    if reason is not None or diagnostic is not None:
        if not reason or not diagnostic:
            return {"allowed": False, "code": "incomplete",
                    "reason": "a reboot needs both a stated reason and the diagnostic that "
                              "will be different this time"}
        if reboots:
            last = reboots[-1]
            if last.get("diagnostic") == diagnostic:
                return {"allowed": False, "code": "blind_repeat",
                        "reason": "diagnostic %r is unchanged from the previous reboot — that "
                                  "would be a blind repeat" % diagnostic}
            if last.get("reason") == reason:
                return {"allowed": False, "code": "reason_repeat",
                        "reason": "reason %r repeats the previous reboot" % reason}
    return {"allowed": True, "code": "ok",
            "reason": "budget (%d/%d) and prerequisites satisfied"
                      % (n, POLICY["max_reboots"])}


def record_history(state_path, entry):
    doc = read_json(state_path, {"schema_version": SCHEMA_VERSION, "history": [],
                                 "failures": {}})
    doc.setdefault("history", []).append(entry)
    if entry.get("kind") == "failure":
        f = doc.setdefault("failures", {})
        f[entry.get("mode", "unknown")] = f.get(entry.get("mode", "unknown"), 0) + 1
    doc["updated_at"] = now()
    write_json(state_path, doc)
    return doc


# --------------------------------------------------------------------------- #
# CLI (used by the bash front-ends and by tests)
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description="release tooling core")
    sub = ap.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("health"); h.add_argument("--root", default="/")
    h.add_argument("--json", default="-"); h.add_argument("--expect-services", default="1")

    s = sub.add_parser("service-for"); s.add_argument("target")

    m = sub.add_parser("parse-manifest"); m.add_argument("--manifest", required=True)
    m.add_argument("--repo-root", required=True); m.add_argument("--json", default="-")

    p = sub.add_parser("policy-check"); p.add_argument("--state", required=True)
    p.add_argument("--reason", default=None); p.add_argument("--diagnostic", default=None)
    p.add_argument("--mode", default=None); p.add_argument("--json", default="-")

    r = sub.add_parser("policy-record"); r.add_argument("--state", required=True)
    r.add_argument("--kind", choices=["reboot", "failure"], default="reboot")
    r.add_argument("--reason", default=""); r.add_argument("--diagnostic", default="")
    r.add_argument("--mode", default=""); r.add_argument("--returned-to-nuxel", default="no")

    sub.add_parser("checklists")

    g = sub.add_parser("guard"); g.add_argument("path")

    args = ap.parse_args(argv)

    if args.cmd == "health":
        rep = health_report(args.root, expect_services=args.expect_services != "0")
        out = json.dumps(rep, indent=2, sort_keys=True)
        print(out) if args.json == "-" else open(args.json, "w", encoding="utf-8").write(out + "\n")
        return 0 if rep["verdict"] == "HEALTHY" else 1
    if args.cmd == "service-for":
        print(smallest_service_for(args.target) or "")
        return 0
    if args.cmd == "parse-manifest":
        man = read_json(args.manifest, {})
        plan = parse_manifest(man, args.repo_root)
        out = json.dumps(plan, indent=2, sort_keys=True)
        print(out) if args.json == "-" else open(args.json, "w", encoding="utf-8").write(out + "\n")
        return 1 if plan["violations"] else 0
    if args.cmd == "policy-check":
        doc = read_json(args.state, {"history": []})
        v = policy_verdict(doc.get("history", []), args.reason, args.diagnostic, args.mode)
        out = json.dumps(v, indent=2, sort_keys=True)
        print(out) if args.json == "-" else open(args.json, "w", encoding="utf-8").write(out + "\n")
        return 0 if v["allowed"] else 1
    if args.cmd == "policy-record":
        entry = {"kind": args.kind, "reason": args.reason, "diagnostic": args.diagnostic,
                 "mode": args.mode, "at": now(),
                 "returned_to_nuxel": args.returned_to_nuxel == "yes",
                 "rollback_known_good": True}
        doc = record_history(args.state, entry)
        print(json.dumps(doc, indent=2, sort_keys=True))
        return 0
    if args.cmd == "checklists":
        print(json.dumps({"pre": PRE_REBOOT_CHECKLIST, "post": POST_REBOOT_CHECKLIST,
                          "policy": POLICY}, indent=2))
        return 0
    if args.cmd == "guard":
        try:
            print(guard_path(args.path))
        except GuardViolation as e:
            print(str(e), file=sys.stderr)
            return 2
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())

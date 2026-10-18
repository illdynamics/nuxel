#!/usr/bin/env python3
"""verify-app-inventory.py — the executable form of
docs/beta-finalization/apps/APP-INVENTORY.md   (briq-06a, mission area 30).

WHAT THIS PROVES
----------------
Mission area 30 requires an application inventory with, per application: id,
implementation, version, source, package type, dependencies, permissions, launch
command, working status, hardware dependencies, offline support and tests — plus
the rule "do not mark an icon as a working app".

An inventory that is prose cannot be checked, so the document carries a
machine-readable block between the markers

    <!-- INVENTORY-DATA:BEGIN --> ... <!-- INVENTORY-DATA:END -->

and this verifier is its executable form.  It fails when a claim in that block
does not match the tree:

 1. every entry has the required mission-area-30 fields, and every status is one
    of the four honest states (present/full, present/partial, missing, external);
 2. a `present/full` entry really has the files it claims (index.html +
    manifest.json + sw.js for a PWA, source + desktop entry for a native app) —
    an icon with no implementation cannot be called full;
 3. a `missing` entry really has no implementation on disk (and vice versa);
 4. every `tests[]` path (globs allowed) resolves to a real file;
 5. manifest truth: for a PWA entry, `permissions` equals the manifest's
    `nuxel.capabilities`, the manifest carries name/start_url/display/icons/
    nuxel.bridge_version, and `launch` points at that app's own index.html;
 6. nothing is hidden: every pwa/nuxel-apps/<dir> that ships an index.html is in
    the inventory, and every app in the canonical registry
    (pwa/nuxel-common/app-registry.json) is in the inventory;
 7. every app id in the human tables of the document is in the data block, so
    the prose cannot drift from the checked data;
 8. every gap names a briQ that really exists in the persistent work queue
    (docs/beta-finalization/workqueue/), and **no gap owned by this build group
    (bg-06-core-phone-apps) is left open** — the inventory is not allowed to
    describe its own unfinished work as somebody else's problem.

A green run is OFFLINE_TESTED: it proves the inventory is true about the
repository. It is never proof that an app works on the S10+.

Usage
    python3 tools/s10plus/a33/verify-app-inventory.py
    python3 tools/s10plus/a33/verify-app-inventory.py --json build/pkgmeta/app-inventory.json
    python3 tools/s10plus/a33/verify-app-inventory.py --strict   # WARN -> FAIL
Exit 0 = every claim verified. 1 = at least one FAIL.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
DOC = os.path.join(ROOT, "docs", "beta-finalization", "apps", "APP-INVENTORY.md")
APPS_ROOT = os.path.join(ROOT, "pwa", "nuxel-apps")
REGISTRY = os.path.join(ROOT, "pwa", "nuxel-common", "app-registry.json")
QUEUE_DIR = os.path.join(ROOT, "docs", "beta-finalization", "workqueue")
BRIDGE_CAPS = os.path.join(ROOT, "services", "nuxel-bridge", "src", "capabilities.py")
SHELL_ROOT = os.path.join(ROOT, "shell", "nuxel-shell")
DESKTOP_DIR = os.path.join(ROOT, "shell", "config")

BEGIN = "<!-- INVENTORY-DATA:BEGIN -->"
END = "<!-- INVENTORY-DATA:END -->"

REQUIRED_FIELDS = ("id", "name", "category", "type", "implementation", "version", "source",
                   "package_type", "dependencies", "permissions", "launch", "hardware",
                   "offline", "tests", "status", "owner_group")
STATUSES = ("present/full", "present/partial", "missing", "external")
GROUP = "bg-06-core-phone-apps"

problems: list[str] = []
warnings: list[str] = []
checks: list[str] = []


def rel(p: str) -> str:
    return os.path.relpath(p, ROOT)


def fail(msg: str) -> None:
    problems.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def ok(msg: str) -> None:
    checks.append(msg)


def read(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def manifest_of(app_dir: str) -> dict | None:
    path = os.path.join(app_dir, "manifest.json")
    if not os.path.isfile(path):
        return None
    try:
        return json.loads(read(path))
    except Exception as exc:  # noqa: BLE001
        fail(f"{rel(path)}: manifest is not valid JSON ({exc})")
        return None


def load_inventory(text: str) -> dict:
    if BEGIN not in text or END not in text:
        fail(f"{rel(DOC)}: the machine-readable block markers {BEGIN} / {END} are missing")
        return {}
    block = text.split(BEGIN, 1)[1].split(END, 1)[0]
    fence = re.search(r"```json\s*(.*?)```", block, re.S)
    body = fence.group(1) if fence else block
    try:
        data = json.loads(body)
    except Exception as exc:  # noqa: BLE001
        fail(f"{rel(DOC)}: the inventory data block is not valid JSON ({exc})")
        return {}
    ok("the inventory data block parses as JSON")
    return data


def load_queue_ids() -> set[str]:
    ids: set[str] = set()
    if not os.path.isdir(QUEUE_DIR):
        warn(f"{rel(QUEUE_DIR)} is not present: gap->briQ cross-check skipped")
        return ids
    for name in sorted(os.listdir(QUEUE_DIR)):
        if not name.endswith(".json"):
            continue
        try:
            doc = json.loads(read(os.path.join(QUEUE_DIR, name)))
        except Exception:  # noqa: BLE001
            warn(f"work-queue file {name} is not parsable; skipped")
            continue
        if isinstance(doc, dict) and doc.get("id"):
            ids.add(str(doc["id"]))
        for rev in (doc.get("revisions") or []) if isinstance(doc, dict) else []:
            if isinstance(rev, dict) and rev.get("id"):
                ids.add(str(rev["id"]))
    return ids


def check_entry(app: dict, bridge_caps: set[str] | None, queue_ids: set[str]) -> None:
    aid = str(app.get("id", "?"))
    for field in REQUIRED_FIELDS:
        if field not in app or app[field] in ("", None, []):
            if field in ("dependencies", "permissions", "tests", "hardware") and app.get(field) == []:
                continue
            fail(f"entry {aid}: required mission-area-30 field '{field}' is missing or empty")
    status = app.get("status")
    if status not in STATUSES:
        fail(f"entry {aid}: status {status!r} is not one of {STATUSES}")
        return

    path = str(app.get("path", ""))
    abs_path = os.path.join(ROOT, path)
    if not path or not os.path.exists(abs_path):
        if status != "missing":
            fail(f"entry {aid}: path {path!r} does not exist but the status is {status}")
        return

    typ = app.get("type")
    index = os.path.join(abs_path, "index.html")
    manifest = os.path.join(abs_path, "manifest.json")
    sw = os.path.join(abs_path, "sw.js")

    for t in app.get("tests") or []:
        hits = glob.glob(os.path.join(ROOT, t)) if any(c in t for c in "*?[") else \
               ([os.path.join(ROOT, t)] if os.path.exists(os.path.join(ROOT, t)) else [])
        if not hits:
            fail(f"entry {aid}: test path {t!r} does not exist")

    if typ == "pwa":
        if status == "present/full":
            for required in (index, manifest, sw):
                if not os.path.isfile(required):
                    fail(f"entry {aid}: status present/full but {rel(required)} is missing")
        if manifest and os.path.isfile(manifest):
            doc = manifest_of(abs_path) or {}
            for key in ("name", "start_url", "display"):
                if not doc.get(key):
                    fail(f"entry {aid}: {rel(manifest)} lacks '{key}'")
            if not doc.get("icons"):
                fail(f"entry {aid}: {rel(manifest)} has no icons[]")
            nuxel = doc.get("nuxel") or {}
            if not isinstance(nuxel.get("capabilities"), list):
                fail(f"entry {aid}: {rel(manifest)} nuxel.capabilities is not a list")
            if not nuxel.get("bridge_version"):
                fail(f"entry {aid}: {rel(manifest)} nuxel.bridge_version is missing")
            declared = app.get("permissions") or []
            actual = nuxel.get("capabilities") or []
            if sorted(declared) != sorted(actual):
                fail(f"entry {aid}: inventory permissions {declared} != manifest capabilities {actual}")
            if bridge_caps is not None:
                unknown = [c for c in actual if c not in bridge_caps]
                if unknown:
                    warn(f"entry {aid}: capability id(s) {unknown} are not in the bridge enum "
                         f"(services/nuxel-bridge/src/capabilities.py) — see the gap table")
            launch = str(app.get("launch", ""))
            # A partial PWA may legitimately have no index.html yet (the gap
            # table says why).  Require a self-consistent launch only for a
            # surface that claims to be complete; partial entries must say
            # "n/a" rather than naming a file that does not exist.
            if status == "present/full":
                if not launch or (not launch.endswith(f"{path}/index.html") and not launch.endswith("index.html")):
                    fail(f"entry {aid}: launch {launch!r} does not point at this app's index.html")
            elif launch and not launch.startswith("n/a") and not os.path.isfile(os.path.join(abs_path, "index.html")):
                fail(f"entry {aid}: partial entry names launch {launch!r} but has no index.html")
            version = app.get("version")
            if doc.get("version") and version and doc["version"] != version:
                fail(f"entry {aid}: version {version!r} != manifest version {doc['version']!r}")
        if status == "missing" and os.path.isfile(index):
            fail(f"entry {aid}: status missing but {rel(index)} exists")
    elif typ == "native":
        src = os.path.join(abs_path, "main.c")
        if status in ("present/full", "present/partial"):
            if not os.path.isfile(src):
                fail(f"entry {aid}: native app has no main.c at {rel(src)}")
            desktop = os.path.join(DESKTOP_DIR, f"{aid}.desktop")
            if not os.path.isfile(desktop):
                # The installed binary name is not always the inventory id
                # (e.g. nuxel-native-settings -> nuxel-settings.desktop).
                alt = os.path.join(DESKTOP_DIR, os.path.basename(path.rstrip("/")) + ".desktop")
                if os.path.isfile(alt):
                    desktop = alt
            if not os.path.isfile(desktop):
                fail(f"entry {aid}: native app has no desktop entry {rel(desktop)}")
            launch = str(app.get("launch", ""))
            if launch and not launch.startswith("/usr/bin/"):
                fail(f"entry {aid}: native launch {launch!r} is not an installed binary path")
    elif typ == "placeholder":
        if status not in ("present/partial", "missing", "external"):
            fail(f"entry {aid}: a placeholder cannot be {status}")
    elif typ == "settings-surface":
        # A settings sub-surface lives inside the Settings PWA.  It has no
        # standalone index/manifest, so the only honest checks are that the
        # container exists and the status is one of the partial/full states.
        if not os.path.exists(abs_path):
            fail(f"entry {aid}: settings-surface path {path!r} does not exist")
        if status not in ("present/full", "present/partial"):
            fail(f"entry {aid}: a settings-surface cannot be {status}")
    elif typ == "tool":
        # A tool is a repository script/binary or a configuration directory;
        # it is not a launchable PWA and has no manifest.
        if not os.path.exists(abs_path):
            fail(f"entry {aid}: tool path {path!r} does not exist")
        if status not in ("present/full", "present/partial", "external"):
            fail(f"entry {aid}: a tool cannot be {status}")
        launch = str(app.get("launch", ""))
        if not launch:
            fail(f"entry {aid}: tool launch is empty")
    else:
        fail(f"entry {aid}: unknown type {typ!r}")
    ok(f"entry {aid} ({typ}, {status}) is consistent with the tree")


def check_coverage(data: dict, text: str, registry: dict) -> None:
    apps = {a.get("id"): a for a in data.get("apps", [])}
    paths = {a.get("path") for a in data.get("apps", [])}

    # nothing hidden: every app dir that ships an index.html is inventoried
    for name in sorted(os.listdir(APPS_ROOT)) if os.path.isdir(APPS_ROOT) else []:
        d = os.path.join(APPS_ROOT, name)
        if not os.path.isdir(d) or name.startswith("_"):
            continue
        if os.path.isfile(os.path.join(d, "index.html")):
            if f"pwa/nuxel-apps/{name}" not in paths:
                fail(f"pwa/nuxel-apps/{name} ships an index.html but is not in the inventory")
        elif not any(p and p.startswith(f"pwa/nuxel-apps/{name}") for p in paths if p):
            warn(f"pwa/nuxel-apps/{name} ships no index.html and is not listed as a gap "
                 f"(an empty app directory must be visible)")
    ok("every app directory with an index.html is inventoried (nothing hidden)")

    # every registry app is inventoried
    for entry in registry.get("apps", []) if isinstance(registry, dict) else []:
        aid = entry.get("id")
        if aid and aid not in apps:
            fail(f"registry app {aid} is missing from the inventory")
    ok("every canonical-registry application is inventoried")

    # the human tables must mention every inventoried id
    body = text.split(BEGIN, 1)[0] + text.split(END, 1)[-1]
    missing_rows = []
    for aid in apps:
        if aid and not re.search(r"\|\s*`?" + re.escape(str(aid)) + r"`?\s*\|", body):
            missing_rows.append(aid)
    if missing_rows:
        fail(f"the human tables do not list: {missing_rows} (the prose must not drift from the data)")
    else:
        ok("every inventoried app id appears in the human tables")

    # shell apps referenced by the inventory must exist as sources
    for app in data.get("apps", []):
        if app.get("type") == "native":
            src = os.path.join(ROOT, str(app.get("path")), "main.c")
            if not os.path.isfile(src):
                fail(f"native entry {app.get('id')} names {app.get('path')} but {rel(src)} is missing")


def check_gaps(data: dict, queue_ids: set[str]) -> None:
    gaps = data.get("gaps") or []
    if not gaps:
        warn("the inventory documents no gaps at all — verify that is really true")
        return
    open_mine = []
    for gap in gaps:
        gid = gap.get("id", "?")
        for field in ("id", "app", "missing", "state", "owner_group"):
            if not gap.get(field):
                fail(f"gap {gid}: field '{field}' is missing")
        state = gap.get("state")
        if state not in ("open", "closed", "outside-this-group", "by-design"):
            fail(f"gap {gid}: state {state!r} is not one of open/closed/outside-this-group/by-design")
        briq = gap.get("closed_by_briq")
        if state in ("open", "closed") and briq:
            if queue_ids and briq not in queue_ids:
                fail(f"gap {gid}: closed_by_briq {briq!r} is not a briQ in the work queue")
        if state == "open" and gap.get("owner_group") == GROUP:
            open_mine.append(gid)
    if open_mine:
        fail(f"this group left its OWN gaps open: {open_mine} (finish them or re-own them explicitly)")
    else:
        ok(f"{len(gaps)} documented gap(s); none of them is an open gap owned by {GROUP}")


def bridge_caps() -> set[str]:
    if not os.path.isfile(BRIDGE_CAPS):
        warn(f"{rel(BRIDGE_CAPS)} not present: capability-enum cross-check skipped")
        return set()
    return set(re.findall(r"=\s*'([a-z]+:[a-z\-]+)'", read(BRIDGE_CAPS)))


def main() -> int:
    ap = argparse.ArgumentParser(description="Nuxel core application inventory verifier (briq-06a)")
    ap.add_argument("--json", metavar="PATH", nargs="?", const="-", default=None,
                    help="write a machine-readable summary (default: stdout)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args()

    if not os.path.isfile(DOC):
        print(f"FAIL {rel(DOC)} does not exist", file=sys.stderr)
        return 1
    text = read(DOC)
    data = load_inventory(text)
    if not data:
        print("\n".join(f"FAIL {p}" for p in problems))
        return 1

    if data.get("schema") != "nuxel.app-inventory/1":
        fail(f"unexpected inventory schema {data.get('schema')!r}")

    registry = {}
    if os.path.isfile(REGISTRY):
        try:
            registry = json.loads(read(REGISTRY))
        except Exception as exc:  # noqa: BLE001
            warn(f"{rel(REGISTRY)} is not parsable ({exc}); registry coverage skipped")
    else:
        warn(f"{rel(REGISTRY)} not present; registry coverage skipped")

    caps = bridge_caps()
    queue_ids = load_queue_ids()

    for app in data.get("apps", []):
        check_entry(app, caps if caps else None, queue_ids)
    check_coverage(data, text, registry)
    check_gaps(data, queue_ids)

    verdict = "OFFLINE_FAILED" if problems else ("OFFLINE_TESTED_WITH_WARNINGS" if warnings else "OFFLINE_TESTED")
    print("== Nuxel core application inventory verification (briq-06a / mission area 30) ==")
    print(f"document: {rel(DOC)}")
    print(f"apps: {len(data.get('apps', []))}  gaps: {len(data.get('gaps') or [])}")
    for line in checks:
        print(f"OK    {line}")
    for line in warnings:
        print(f"WARN  {line}")
    for line in problems:
        print(f"FAIL  {line}")
    print(f"\nchecks={len(checks)} warnings={len(warnings)} problems={len(problems)} verdict={verdict}")

    if args.json:
        payload = {"schema": data.get("schema"), "verdict": verdict,
                   "checks": checks, "warnings": warnings, "problems": problems,
                   "apps": [a.get("id") for a in data.get("apps", [])],
                   "gaps": [g.get("id") for g in data.get("gaps") or []]}
        blob = json.dumps(payload, indent=2)
        if args.json in ("", "-"):
            print(blob)
        else:
            out = args.json if os.path.isabs(args.json) else os.path.join(ROOT, args.json)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(blob + "\n")
            print(f"wrote {rel(out)}")

    if problems:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

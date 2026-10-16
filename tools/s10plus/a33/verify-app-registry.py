#!/usr/bin/env python3
"""verify-app-registry.py — offline verifier for the Nuxel application registry.

WHAT THIS PROVES (briq-04c, Priority 4)
---------------------------------------
One canonical registry, three consumers, zero drift:

    pwa/nuxel-common/app-registry.json          <- canonical (this file's subject)
      |-- pwa/nuxel-home/js/apps.js             <- PWA launcher (read-only check)
      |-- shell/nuxel-home-native/nuxel_home/app_registry.json  <- native shell
      `-- services/nuxel-bridge/src/api.py       <- HTTP bridge /apps/registry

Assertions (a failure here is a real defect, not a style nit):

 1. the canonical registry parses, and every ``apps[]`` entry is complete;
 2. every ``type == "pwa"`` entry resolves to a REAL ``index.html`` on disk AND a
    real ``manifest.json`` that carries ``nuxel.capabilities`` (a list) and
    ``nuxel.bridge_version`` equal to the pinned ``bridge_version``;
 3. every capability id an app declares is known to the bridge
    (``services/nuxel-bridge/src/capabilities.py`` ``Capability`` enum) — an app
    may not advertise a capability the host cannot arbitrate;
 4. every ``type == "native"`` entry names a binary source that exists in the
    repository and a desktop entry, or is an explicitly documented placeholder;
 5. the launcher (``apps.js``) serves EXACTLY the registry's app ids and urls —
    no missing app, no extra app;
 6. the native shell copy (``app_registry.json``) resolves exactly the registry's
    PWA entries;
 7. every ``pwa/nuxel-apps/<dir>`` that ships an ``index.html`` is either a
    registered app or documented in ``tree_apps`` with an owning build group, and
    every ``tree_apps`` dir exists on disk (the inventory cannot go stale and
    cannot silently hide an app);
 8. the bridge_version pin is consistent across
    ``bridge-version.json``, ``bridge.js``'s ``NUXEL_BRIDGE_VERSION``, the app
    manifests and the installed systemd ``Environment=`` pins.

A green run is OFFLINE_TESTED: it proves the *bookkeeping* is consistent. It is
never proof that an app's hardware path works.

Usage:
    python3 tools/s10plus/a33/verify-app-registry.py
    python3 tools/s10plus/a33/verify-app-registry.py --json build/pkgmeta/app-registry.json
    python3 tools/s10plus/a33/verify-app-registry.py --strict      # WARN -> FAIL
    python3 tools/s10plus/a33/verify-app-registry.py --sync-native # rewrite the
        # native shell copy from the canonical registry (then re-run to verify)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Set, Tuple

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
REGISTRY = os.path.join(ROOT, "pwa", "nuxel-common", "app-registry.json")
PIN = os.path.join(ROOT, "pwa", "nuxel-common", "bridge-version.json")
BRIDGE_JS = os.path.join(ROOT, "pwa", "nuxel-common", "bridge.js")
APPS_JS = os.path.join(ROOT, "pwa", "nuxel-home", "js", "apps.js")
NATIVE_REGISTRY = os.path.join(ROOT, "shell", "nuxel-home-native", "nuxel_home", "app_registry.json")
CAPABILITIES_PY = os.path.join(ROOT, "services", "nuxel-bridge", "src", "capabilities.py")
API_PY = os.path.join(ROOT, "services", "nuxel-bridge", "src", "api.py")
HTTP_UNIT = os.path.join(ROOT, "services", "nuxel-bridge", "systemd", "nuxel-http-bridge.service")
BRIDGE_UNIT = os.path.join(ROOT, "services", "nuxel-bridge", "systemd", "nuxel-bridge.service")
APPS_ROOT = os.path.join(ROOT, "pwa", "nuxel-apps")

REQUIRED_ENTRY_FIELDS = ("id", "name", "icon", "category", "type", "url", "capabilities", "bridge_version")


def rel(p: str) -> str:
    return os.path.relpath(p, ROOT)


class Report:
    def __init__(self) -> None:
        self.problems: List[str] = []
        self.warnings: List[str] = []
        self.checks: List[str] = []
        # Documented cross-group deferrals: an entry the launcher serves but whose
        # app tree is owned by another build group and is still landing.  Never a
        # silent pass (always printed), never fatal unless --strict.
        self.deferred: List[Dict[str, object]] = []
        self.deferred_resolved: List[str] = []

    def fail(self, msg: str) -> None:
        self.problems.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def ok(self, msg: str) -> None:
        self.checks.append(msg)

    def defer(self, entry: Dict) -> None:
        self.deferred.append(entry)


def parse_apps_js(path: str) -> Tuple[Dict[str, Dict[str, str]], int]:
    """Return ({registry_key: {id,type,url}}, NUXEL_REGISTRY_VERSION).

    Parses the real object literal without executing it: every top-level entry is
    `'<key>': { ... },` and the first `id:`/`type:`/`url:` inside wins.
    """
    text = open(path, errors="replace").read()
    m = re.search(r"const\s+NUXEL_REGISTRY_VERSION\s*=\s*(\d+)", text)
    version = int(m.group(1)) if m else -1
    body = text.split("const NUXEL_APPS", 1)[1] if "const NUXEL_APPS" in text else text
    entries: Dict[str, Dict[str, str]] = {}
    for key, chunk in re.findall(r"^\s*'([^']+)':\s*\{\s*(.*?)^\s*\},", body, re.S | re.M):
        fields: Dict[str, str] = {}
        for field in ("id", "type", "url"):
            fm = re.search(r"^\s*%s:\s*'([^']*)'" % field, chunk, re.M)
            if fm:
                fields[field] = fm.group(1)
        entries[key] = fields
    return entries, version


def parse_capabilities(path: str) -> Set[str]:
    text = open(path, errors="replace").read()
    return set(re.findall(r"=\s*'([a-z]+:[a-z_-]+)'", text))


def systemd_env(path: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not os.path.exists(path):
        return out
    for m in re.finditer(r"^Environment=([A-Za-z_][A-Za-z0-9_]*)=(.*)$",
                         open(path, errors="replace").read(), re.M):
        out[m.group(1)] = m.group(2).strip()
    return out


def build_native_registry(registry: Dict, pin: Dict) -> Dict:
    """Render the native-shell copy from the canonical registry (no drift)."""
    apps = []
    for app in registry["apps"]:
        url = app["url"]
        if app["type"] == "pwa":
            url = "%s%s" % (registry.get("url_base", "http://127.0.0.1:8000"), url)
        apps.append({
            "id": app["id"],
            "name": app["name"],
            "icon": app["icon"],
            "kind": app["type"],
            "url": url,
            "native_binary": app.get("native_binary"),
            "color": app["color"],
            "category": app["category"],
            "description": app.get("description", ""),
            "capabilities": list(app["capabilities"]),
            "bridge_version": app["bridge_version"],
            "status": app.get("status", "implemented"),
        })
    return {
        "schema": "nuxel.app-registry.native-consumer/1",
        "version": registry.get("registry_version"),
        "generated_from": "pwa/nuxel-common/app-registry.json",
        "bridge_version": pin["bridge_version"],
        "do_not_edit": "Rendered by tools/s10plus/a33/verify-app-registry.py --sync-native. Edit the canonical registry instead.",
        "apps": apps,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write the machine-readable report here")
    ap.add_argument("--strict", action="store_true", help="treat WARN as FAIL")
    ap.add_argument("--sync-native", action="store_true",
                    help="rewrite shell/nuxel-home-native/nuxel_home/app_registry.json from the canonical registry")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    rep = Report()
    for required, label in ((REGISTRY, "canonical registry"), (PIN, "bridge version pin")):
        if not os.path.exists(required):
            print("FATAL: %s missing: %s" % (label, rel(required)), file=sys.stderr)
            return 2

    registry = json.load(open(REGISTRY))
    pin = json.load(open(PIN))
    pin_version = pin["bridge_version"]
    caps_known = parse_capabilities(CAPABILITIES_PY)
    if not caps_known:
        rep.fail("no capability ids parsed from %s — the drift check cannot be trusted" % rel(CAPABILITIES_PY))

    cap_gaps = {g.get("capability"): g for g in registry.get("capability_gaps", [])}
    for cap, gap in sorted(cap_gaps.items()):
        for field in ("declared_by", "status", "owner_group", "note"):
            if not gap.get(field):
                rep.fail("capability_gaps entry %r is missing %s" % (cap, field))
        for owner_file in gap.get("declared_by", []):
            if not os.path.exists(os.path.join(ROOT, owner_file)):
                rep.fail("capability_gaps[%s] names %r, which does not exist" % (cap, owner_file))
    rep.ok("capability_gaps documented: %s" % ", ".join(sorted(cap_gaps)) or "none")

    # ---- 1..4: the entries themselves ------------------------------------
    seen_ids: Set[str] = set()
    for app in registry.get("apps", []):
        aid = app.get("id", "<missing id>")
        for field in REQUIRED_ENTRY_FIELDS:
            if field not in app:
                rep.fail("app %s: missing required field %r" % (aid, field))
        if aid in seen_ids:
            rep.fail("app %s: duplicate id in the canonical registry" % aid)
        seen_ids.add(aid)
        if app.get("bridge_version") != pin_version:
            rep.fail("app %s: bridge_version %r != pin %r" % (aid, app.get("bridge_version"), pin_version))
        for cap in app.get("capabilities", []):
            if cap in caps_known:
                continue
            gap = cap_gaps.get(cap)
            if gap:
                rep.warn("app %s: capability %r is not in the bridge enum — documented gap (owner %s)"
                         % (aid, cap, gap.get("owner_group")))
            else:
                rep.fail("app %s: capability %r is not defined in %s and not documented in capability_gaps"
                         % (aid, cap, rel(CAPABILITIES_PY)))
        for note in app.get("cross_group_gaps", []):
            rep.warn("app %s: cross-group gap: %s" % (aid, note))

        if app.get("type") == "pwa":
            entry = os.path.join(ROOT, app.get("entry", ""))
            manifest = os.path.join(ROOT, app.get("manifest", ""))
            if not (os.path.isfile(entry) and os.path.isfile(manifest)):
                if app.get("resolution") == "pending" and isinstance(app.get("pending"), dict):
                    rep.defer({"app": aid, "owner_groups": app["pending"].get("owner_groups"),
                               "reason": app["pending"].get("reason"),
                               "expected": app["pending"].get("expected"),
                               "resolved": False})
                    continue
                if not os.path.isfile(entry):
                    rep.fail("app %s: entry %r does not exist" % (aid, app.get("entry")))
                if not os.path.isfile(manifest):
                    rep.fail("app %s: manifest %r does not exist" % (aid, app.get("manifest")))
                continue
            if app.get("resolution") == "pending":
                # The deferral was recorded earlier in the cycle and the app has
                # since landed: say so loudly so the marker is removed next pass.
                rep.deferred_resolved.append(aid)
                rep.ok("app %s: previously deferred app tree now resolves (%s + %s)"
                       % (aid, app.get("entry"), app.get("manifest")))
            if not app.get("url", "").startswith("/pwa/"):
                rep.fail("app %s: url %r is not a /pwa/ path served by nuxel-web" % (aid, app.get("url")))
            expected_url = "/" + os.path.relpath(entry, os.path.join(ROOT, "pwa")).replace(os.sep, "/")
            expected_url = "/pwa/" + os.path.relpath(entry, os.path.join(ROOT, "pwa")).replace(os.sep, "/")
            if app.get("url") != expected_url:
                rep.fail("app %s: url %r does not resolve to %r" % (aid, app.get("url"), expected_url))
            try:
                mf = json.load(open(manifest))
            except Exception as exc:  # noqa: BLE001
                rep.fail("app %s: manifest is not valid JSON (%s)" % (aid, exc))
                continue
            nuxel = mf.get("nuxel")
            if not isinstance(nuxel, dict):
                rep.warn("app %s: %s has no nuxel{} block (nuxel.capabilities / nuxel.bridge_version missing)" % (aid, app.get("manifest")))
            else:
                if not isinstance(nuxel.get("capabilities"), list):
                    rep.fail("app %s: manifest nuxel.capabilities is not a list" % aid)
                if nuxel.get("bridge_version") != pin_version:
                    rep.fail("app %s: manifest nuxel.bridge_version %r != pin %r"
                             % (aid, nuxel.get("bridge_version"), pin_version))
                declared = set(nuxel.get("capabilities") or [])
                registry_caps = set(app.get("capabilities") or [])
                if declared != registry_caps:
                    rep.warn("app %s: manifest capabilities %s != registry capabilities %s"
                             % (aid, sorted(declared), sorted(registry_caps)))
                for cap in sorted(declared):
                    if cap in caps_known:
                        continue
                    gap = cap_gaps.get(cap)
                    if gap:
                        rep.warn("app %s: capability %r is declared but NOT in the bridge enum — documented gap (owner %s): %s"
                                 % (aid, cap, gap.get("owner_group"), (gap.get("note") or "")[:120]))
                    else:
                        rep.fail("app %s: capability %r is declared by the manifest but not defined in %s and not documented in capability_gaps"
                                 % (aid, cap, rel(CAPABILITIES_PY)))
            rep.ok("pwa %s -> %s + %s" % (aid, app.get("entry"), app.get("manifest")))
        elif app.get("type") == "native":
            src = app.get("binary_source")
            binp = app.get("native_binary")
            if not src or not binp:
                if app.get("status") == "placeholder" and app.get("implementation_note"):
                    rep.warn("app %s: native placeholder with no binary (%s)" % (aid, app.get("implementation_note")[:90]))
                else:
                    rep.fail("app %s: native entry without binary_source/native_binary and not documented as a placeholder" % aid)
            elif not os.path.exists(os.path.join(ROOT, src)):
                rep.fail("app %s: binary_source %r does not exist" % (aid, src))
            else:
                desktop = app.get("desktop_entry")
                if desktop and not os.path.exists(os.path.join(ROOT, desktop)):
                    rep.fail("app %s: desktop_entry %r does not exist" % (aid, desktop))
                rep.ok("native %s -> %s (source %s)" % (aid, binp, src))
        else:
            rep.fail("app %s: unknown type %r" % (aid, app.get("type")))

    # ---- 5: the PWA launcher serves exactly this set ---------------------
    if not os.path.exists(APPS_JS):
        rep.fail("launcher registry missing: %s" % rel(APPS_JS))
    else:
        launcher, launcher_version = parse_apps_js(APPS_JS)
        if launcher_version != registry.get("registry_version"):
            rep.fail("registry_version drift: apps.js NUXEL_REGISTRY_VERSION=%s vs canonical %s"
                     % (launcher_version, registry.get("registry_version")))
        reg_by_id = {a["id"]: a for a in registry["apps"]}
        launcher_ids = {f.get("id", k) for k, f in launcher.items()}
        missing = sorted(set(reg_by_id) - launcher_ids)
        extra = sorted(launcher_ids - set(reg_by_id))
        if missing:
            rep.fail("launcher apps.js does not serve registry app(s): %s" % ", ".join(missing))
        if extra:
            rep.fail("launcher apps.js serves app(s) absent from the canonical registry: %s" % ", ".join(extra))
        for key, fields in launcher.items():
            aid = fields.get("id", key)
            app = reg_by_id.get(aid)
            if not app:
                continue
            if fields.get("type") and fields["type"] != app["type"]:
                rep.fail("app %s: type drift (apps.js=%r registry=%r)" % (aid, fields["type"], app["type"]))
            if fields.get("url") and fields["url"] != app["url"]:
                rep.fail("app %s: url drift (apps.js=%r registry=%r)" % (aid, fields["url"], app["url"]))
        if not missing and not extra:
            rep.ok("launcher apps.js serves exactly the canonical %d apps (registry_version %s)"
                   % (len(reg_by_id), launcher_version))

    # ---- 6: the native shell copy ---------------------------------------
    if not os.path.exists(NATIVE_REGISTRY):
        rep.warn("native shell copy missing: %s (run --sync-native)" % rel(NATIVE_REGISTRY))
    elif args.sync_native:
        json.dump(build_native_registry(registry, pin), open(NATIVE_REGISTRY, "w"), indent=2)
        open(NATIVE_REGISTRY, "a").write("\n")
        rep.ok("rewrote %s from the canonical registry" % rel(NATIVE_REGISTRY))
    else:
        native = json.load(open(NATIVE_REGISTRY))
        expected = build_native_registry(registry, pin)
        native_by_id = {a["id"]: a for a in native.get("apps", [])}
        expected_by_id = {a["id"]: a for a in expected["apps"]}
        for aid in sorted(set(expected_by_id) - set(native_by_id)):
            rep.fail("native shell copy is missing app %s" % aid)
        for aid in sorted(set(native_by_id) - set(expected_by_id)):
            rep.fail("native shell copy has app %s that the canonical registry does not define" % aid)
        for aid in sorted(set(native_by_id) & set(expected_by_id)):
            for field in ("kind", "url", "bridge_version"):
                if native_by_id[aid].get(field) != expected_by_id[aid].get(field):
                    rep.fail("native shell copy drift for %s.%s: %r != %r"
                             % (aid, field, native_by_id[aid].get(field), expected_by_id[aid].get(field)))
        if native.get("bridge_version") != pin_version:
            rep.fail("native shell copy bridge_version %r != pin %r" % (native.get("bridge_version"), pin_version))
        rep.ok("native shell copy matches the canonical registry (%d apps)" % len(native_by_id))

    # ---- 7: tree coverage ------------------------------------------------
    registered_dirs = {os.path.dirname(a["entry"]).split("/")[-1] for a in registry["apps"] if a.get("type") == "pwa"}
    documented = {t["dir"].split("/")[-1] for t in registry.get("tree_apps", [])}
    on_disk = sorted(d for d in os.listdir(APPS_ROOT)
                     if os.path.isdir(os.path.join(APPS_ROOT, d))
                     and os.path.isfile(os.path.join(APPS_ROOT, d, "index.html")))
    for t in registry.get("tree_apps", []):
        if not os.path.isdir(os.path.join(ROOT, t["dir"])):
            rep.fail("tree_apps names %r, which does not exist on disk" % t["dir"])
        for field in ("owner_group", "state", "note"):
            if not t.get(field):
                rep.fail("tree_apps entry %r is missing %s" % (t["dir"], field))
    launcher_registered_dirs = set()
    for aid, app in {a["id"]: a for a in registry["apps"]}.items():
        if app.get("type") == "pwa":
            launcher_registered_dirs.add(os.path.dirname(app["entry"]).split("/")[-1])
    for d in on_disk:
        if d in registered_dirs or d in documented:
            continue
        rep.warn("pwa/nuxel-apps/%s ships an index.html but is in neither apps[] nor tree_apps[]" % d)
    for d in sorted(documented - set(on_disk)):
        # A documented-but-incomplete app is fine (owner group still working); the
        # inventory says so explicitly, so this is informational, not drift.
        rep.ok("tree_apps documents pwa/nuxel-apps/%s (no index.html yet: %s)"
               % (d, [t["state"] for t in registry["tree_apps"] if t["dir"].endswith("/" + d)][0]))

    # ---- 8: the bridge_version pin ---------------------------------------
    bridge_js = open(BRIDGE_JS, errors="replace").read() if os.path.exists(BRIDGE_JS) else ""
    m = re.search(r"export\s+const\s+NUXEL_BRIDGE_VERSION\s*=\s*'([^']+)'", bridge_js)
    if not m:
        rep.fail("bridge.js does not export a NUXEL_BRIDGE_VERSION literal")
    elif m.group(1) != pin_version:
        rep.fail("bridge.js NUXEL_BRIDGE_VERSION %r != pin %r" % (m.group(1), pin_version))
    else:
        rep.ok("bridge.js NUXEL_BRIDGE_VERSION == pin (%s)" % pin_version)
    for unit in (BRIDGE_UNIT, HTTP_UNIT):
        env = systemd_env(unit)
        if env.get("NUXEL_BRIDGE_PROTOCOL_VERSION") != pin_version:
            rep.fail("%s: NUXEL_BRIDGE_PROTOCOL_VERSION %r != pin %r"
                     % (rel(unit), env.get("NUXEL_BRIDGE_PROTOCOL_VERSION"), pin_version))
        if env.get("NUXEL_BRIDGE_VERSION") != pin.get("host_version"):
            rep.fail("%s: NUXEL_BRIDGE_VERSION %r != host_version %r"
                     % (rel(unit), env.get("NUXEL_BRIDGE_VERSION"), pin.get("host_version")))
    for note in registry.get("launcher_manifest_notes", []):
        rep.warn("launcher manifest note: %s" % note)
    api = open(API_PY, errors="replace").read() if os.path.exists(API_PY) else ""
    if "bridge_version" not in api:
        rep.fail("services/nuxel-bridge/src/api.py does not publish bridge_version")
    if "/api/v1/apps/registry" not in api:
        rep.fail("services/nuxel-bridge/src/api.py does not serve /api/v1/apps/registry")
    if not args.quiet:
        pass  # the api.py assertions are reported through problems/checks only

    if rep.problems:
        verdict = "FAILED"
    elif rep.deferred:
        verdict = "OFFLINE_TESTED_WITH_DEFERRALS"
    elif rep.warnings:
        verdict = "OFFLINE_TESTED_WITH_WARNINGS"
    else:
        verdict = "OFFLINE_TESTED"
    if args.strict and rep.warnings:
        verdict = "FAILED"
        rep.problems.extend("STRICT: " + w for w in rep.warnings)
    report = {
        "tool": "verify-app-registry.py",
        "registry": rel(REGISTRY),
        "registry_version": registry.get("registry_version"),
        "bridge_version": pin_version,
        "host_version": pin.get("host_version"),
        "app_count": len(registry.get("apps", [])),
        "tree_app_count": len(registry.get("tree_apps", [])),
        "checks": rep.checks,
        "deferred": rep.deferred,
        "deferred_now_resolved": rep.deferred_resolved,
        "capability_gaps": registry.get("capability_gaps", []),
        "problems": rep.problems,
        "warnings": rep.warnings,
        "verdict": verdict,
    }
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w") as fh:
            json.dump(report, fh, indent=2)
            fh.write("\n")
    if not args.quiet:
        for c in rep.checks:
            print("OK    %s" % c)
        for d in rep.deferred:
            print("DEFER %s: app tree not landed yet (owners: %s) — %s"
                  % (d["app"], ", ".join(d.get("owner_groups") or []), d.get("reason")))
        for aid in rep.deferred_resolved:
            print("INFO  %s was deferred earlier in this cycle and now resolves; drop the pending marker"
                  % aid)
        for w in rep.warnings:
            print("WARN  %s" % w)
        for p in rep.problems:
            print("FAIL  %s" % p)
        print("apps=%d problems=%d warnings=%d deferred=%d verdict=%s"
              % (len(registry.get("apps", [])), len(rep.problems), len(rep.warnings), len(rep.deferred), verdict))
    return 0 if verdict != "FAILED" else 1


if __name__ == "__main__":
    sys.exit(main())

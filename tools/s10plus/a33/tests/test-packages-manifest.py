#!/usr/bin/env python3
"""Offline test for the Fedora 43 package manifest + verifier (briq-04a).

Proves the properties the mission asks for, using only real repository metadata
that is already cached under build/pkgmeta/ (or the network when available):

  1. the essential manifest resolves against the real Fedora 43 aarch64 GA +
     updates metadata (`resolved`, rc 0);
  2. resolving against GA ALONE fails on the systemd pin — i.e. the pin is
     load-bearing and the failure mode is demonstrable (`--ga-only`);
  3. with no metadata source at all the verifier reports
     BLOCKED_EXTERNAL_RESOURCE instead of inventing versions (empty cache);
  4. there is no `--skip-unavailable` / `--skip-broken` anywhere in the rootfs
     builder — an unavailable essential package must abort the build;
  5. every package the manifest declares is actually requested by the builder's
     `dnf install` line (the manifest is not documentation-only);
  6. metadata provenance is recorded (repomd.xml sha256 + the compressed and
     decompressed sha256 of the primary.xml payload actually parsed), so every
     NEVRA in the manifest is attributable to a specific Fedora 43 artifact and
     a reviewer can re-fetch and re-derive it. Drift in an unpinned repository is
     reported (the repos move), a missing provenance record is a failure.
  7. DEPENDENCIES, not just existence (briq-04a rev 2): every essential package's
     rpm requirements resolve against the repository set, the requirement
     classifier and the rpm RICH (boolean) dependency evaluator behave as
     specified, and a requirement that only the OTHER repository provides still
     resolves (the measured `stevia` (updates) -> `libdconf.so.1()(64bit)` (GA)
     case -- a real defect this suite is the regression test for).
  8. the manifest is DATA: it validates against the embedded JSON schema, and a
     tampered manifest is REJECTED rather than silently consumed by the builder.

Usage:  python3 tools/s10plus/a33/tests/test-packages-manifest.py
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
VERIFY = os.path.join(ROOT, "tools", "s10plus", "a33", "verify-packages.py")
MANIFEST = os.path.join(ROOT, "images", "s10plus", "packages-manifest.json")
BUILDER = os.path.join(ROOT, "images", "s10plus", "build-phone-rootfs-inside-fedora.sh")
CACHE = os.path.join(ROOT, "build", "pkgmeta")

# Packages that are carried by the manifest for completeness but are deliberately
# NOT on the install line (documented in DEPENDENCY-REPORT.md).
INSTALL_LINE_EXEMPT = {
    "dbus-broker",  # installed (kept one systemctl away) -> actually installed; kept here only if absent
}


def run_verify(args):
    """Run the verifier and return (rc, report). The report is requested with
    --report so --quiet really is quiet (stdout stays free of JSON)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "report.json")
        proc = subprocess.run([sys.executable, VERIFY] + args + ["--quiet", "--report", out],
                              capture_output=True, text=True)
        try:
            with open(out) as fh:
                report = json.load(fh)
        except (OSError, ValueError):
            report = {"stderr": proc.stderr[-2000:], "stdout": proc.stdout[-2000:]}
    return proc.returncode, report


def load_verify_module():
    """Import verify-packages.py so its pure functions can be unit-tested."""
    spec = importlib.util.spec_from_file_location("nuxel_verify_packages", VERIFY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_requirement_classifier(vp, check):
    """The classifier decides what a requirement IS; a wrong answer turns the
    dependency check into a rubber stamp, so every MEASURED shape is pinned."""
    measured = [
        ("rpmlib(RichDependencies)", "rpmlib"),
        ("config(systemd)", "config"),
        ("/usr/bin/sh", "file"),
        ("/etc/pam.d/system-auth", "file"),
        ("libc.so.6()(64bit)", "capability"),
        ("ld-linux-aarch64.so.1(GLIBC_2.17)(64bit)", "capability"),
        ("python3.13dist(something)", "capability"),
        ("(wpa_supplicant >= 1:1.1 or iwd)", "rich"),
        ("(util-linux-core or util-linux)", "rich"),
        ("hicolor-icon-theme", "package"),
        ("openssl-libs", "package"),
        ("", "empty"),
    ]
    bad = [(name, vp.classify_requirement(name), want) for name, want in measured
           if vp.classify_requirement(name) != want]
    check(not bad, "requirement classifier matches every measured rpm shape"
          + (" -- wrong: %s" % bad if bad else ""))
    check(vp.req_base_name("systemd >= 258.11") == "systemd",
          "a version constraint is stripped from the requirement name")
    check(vp.req_base_name("libc.so.6()(64bit)") == "libc.so.6()(64bit)",
          "a capability name is NOT truncated at '('")


def test_rich_dependency_evaluator(vp, check):
    """Tri-state evaluation of rpm RICH dependencies. Never a guess."""
    names = {"wpa_supplicant", "util-linux", "systemd", "redhat-rpm-config", "mesa-dri-drivers"}
    providers = {"glibc-gconv-extra(aarch-64)": "glibc-gconv-extra-2.42-17.fc43.aarch64",
                 "mesa-dri-drivers(aarch-64)": "mesa-dri-drivers-25.3.6-3.fc43.aarch64"}

    def resolve(atom, versioned=False):
        if atom.startswith("/") or atom.startswith("rpmlib("):
            return None
        return True if (atom in names or atom in providers) else False

    cases = [
        ("(wpa_supplicant >= 1:1.1 or iwd)", True, "or: one satisfied atom is enough"),
        ("(util-linux-core or util-linux)", True, "or: the second atom resolves"),
        ("(absent-a or absent-b)", False, "or: nothing satisfies it -> resolvable FAIL"),
        ("(absent if absent-cond else util-linux)", True,
         "if/else: an unsatisfied condition uses the else branch"),
        ("(absent if systemd else absent-2)", False,
         "if/else: a satisfied condition demands the first operand"),
        ("(absent if absent)", True, "if: an unsatisfied condition is vacuous"),
        ("(absent if systemd)", False, "if: a satisfied condition demands the target"),
        ("(/etc/pam.d/system-auth if systemd)", None,
         "if: a FILE requirement cannot be decided from primary.xml"),
        ("(systemd and util-linux)", True, "and: every operand resolves"),
        ("(systemd and absent)", False, "and: one missing operand fails the pair"),
        ("((a or b) and c)", False, "nested groups evaluate before the outer operator"),
    ]
    bad = []
    for expr, want, why in cases:
        got = vp.eval_rich(expr, resolve)
        if got is not want:
            bad.append((expr, got, want, why))
    check(not bad, "rich dependency evaluator is tri-state correct"
          + (" -- wrong: %s" % bad if bad else ""))
    check(vp.split_rich("wpa_supplicant >= 1:1.1 or iwd") == ["wpa_supplicant >= 1:1.1", "or", "iwd"],
          "split_rich keeps version constraints in the operand")
    check(vp.rich_atoms("(glibc-gconv-extra(aarch-64) = 2.42 if redhat-rpm-config)")
          == ["glibc-gconv-extra(aarch-64)", "redhat-rpm-config"],
          "rich_atoms yields the atom names (constraints and parentheses stripped)")


GA_FIXTURE = """<?xml version="1.0"?>
<metadata xmlns="http://linux.duke.edu/metadata/common" xmlns:rpm="http://linux.duke.edu/metadata/rpm">
<package type="rpm"><name>dconf</name><arch>aarch64</arch>
<version epoch="0" ver="0.49.0" rel="1.fc43"/>
<format><rpm:provides><rpm:entry name="dconf"/>
<rpm:entry name="libdconf.so.1()(64bit)"/></rpm:provides></format></package>
</metadata>"""

UPDATES_FIXTURE = """<?xml version="1.0"?>
<metadata xmlns="http://linux.duke.edu/metadata/common" xmlns:rpm="http://linux.duke.edu/metadata/rpm">
<package type="rpm"><name>stevia</name><arch>aarch64</arch>
<version epoch="0" ver="0.54.0" rel="1.fc43"/>
<format><rpm:requires><rpm:entry name="libdconf.so.1()(64bit)"/>
<rpm:entry name="libnope.so.9()(64bit)"/></rpm:requires></format></package>
<package type="rpm"><name>stevia-osk</name><arch>noarch</arch>
<version epoch="0" ver="0.54.0" rel="1.fc43"/>
<format><rpm:requires><rpm:entry name="stevia-osk-data"/></rpm:requires></format></package>
</metadata>"""


def test_cross_repository_provider_resolution(vp, check):
    """Regression: a requirement in one repository, provided only in the other.

    Measured on Fedora 43 aarch64: `stevia` lives in `updates` and requires
    `libdconf.so.1()(64bit)`, which only `dconf` in the GA repository provides.
    A per-repository resolution reported that pair as unsatisfiable -- a false
    FAILED on a package set dnf installs without complaint. The fix resolves
    the needed set globally; this test keeps it fixed.
    """
    ga = GA_FIXTURE.encode()
    updates = UPDATES_FIXTURE.encode()
    want = {"stevia", "stevia-osk"}
    a = vp.parse_primary(ga, want)
    b = vp.parse_primary(updates, want)
    requires = {}
    for parsed in (a, b):
        for pname, by_nevra in parsed["requires"].items():
            requires.setdefault(pname, {}).update(by_nevra)
    names = a["names"] | b["names"]
    needed = vp.global_needed(requires)
    providers = {}
    for parsed, xml in ((a, ga), (b, updates)):
        for cap, prov in vp.scan_providers(xml, needed).items():
            providers.setdefault(cap, prov)
    check("libdconf.so.1()(64bit)" in needed and "libdconf.so.1()(64bit)" in providers,
          "a requirement in the second repo finds its provider in the first (stevia/dconf)")
    check(providers.get("libdconf.so.1()(64bit)") == "dconf-0.49.0-1.fc43.aarch64",
          "the providing NEVRA is attributed, not just a boolean")
    dep = vp.resolve_dependencies([("stevia", "stevia-0.54.0-1.fc43.aarch64"),
                                   ("stevia-osk", "stevia-osk-0.54.0-1.fc43.noarch")],
                                  names, providers, requires)
    # Both classes of miss must be caught: a capability with no provider
    # (libnope.so.9) and a plain package name that no package carries
    # (stevia-osk-data). Everything else in the fixture resolves.
    missed = sorted(u["requirement"] for u in dep["unresolved"])
    check(missed == ["libnope.so.9()(64bit)", "stevia-osk-data"],
          "both an unprovided capability and an unknown package name are unresolved")
    check(all(u["kind"] in ("capability", "package") for u in dep["unresolved"]),
          "every unresolved requirement records its classified kind")
    check(dep["per_package"]["stevia"]["by_kind"].get("capability") == 2,
          "per-package requirement counts are recorded")
    check(vp.INDEX_CACHE_VERSION >= 2,
          "the derived index cache is versioned (a stale cache cannot change a verdict)")


def main():
    failures = []

    def check(cond, msg):
        print(("  OK   " if cond else "  FAIL ") + msg)
        if not cond:
            failures.append(msg)

    manifest = json.load(open(MANIFEST))
    declared = {}
    for group in manifest["groups"]:
        for pkg in group["packages"]:
            declared[pkg["name"]] = pkg.get("nevra")
    print("[packages] manifest: %d packages in %d groups (verdict %s)"
          % (len(declared), len(manifest["groups"]), manifest.get("verdict")))
    check(manifest.get("verdict") == "resolved", "the shipped manifest records verdict=resolved")
    check(manifest.get("unavailable") in ([], None), "the shipped manifest records no unavailable package")
    check(manifest.get("resolved_count") == len(declared),
          "resolved_count (%s) == declared packages (%d)" % (manifest.get("resolved_count"), len(declared)))
    check(all(v for v in declared.values()), "every declared package carries a real NEVRA")
    protected = {p["id"] for p in manifest.get("protected_compat_items", [])}
    check({"libsystemd-4.14-patch", "a26-rootfs-fixes"} <= protected,
          "both protected compatibility items are recorded: %s" % sorted(protected))

    print("[packages] real Fedora 43 metadata resolution")
    rc, report = run_verify(["--offline", "--cache-dir", CACHE])
    if report.get("verdict") == "BLOCKED_EXTERNAL_RESOURCE":
        rc, report = run_verify([])  # no cache: try the network
    resolution_report = report
    check(report.get("verdict") == "resolved",
          "essential packages resolve against real metadata (verdict %r, rc %s)" % (report.get("verdict"), rc))
    check(rc == 0, "the verifier exits 0 on a resolved manifest")
    resolved = report.get("resolved", {}) or {}
    for name, nevra in sorted(declared.items()):
        check(resolved.get(name) == nevra,
              "%s resolves exactly to the pinned NEVRA (%s)" % (name, nevra))
    print("        resolver notes: %s" % (report.get("resolver_note") or report.get("notes")
                                           or "; ".join(report.get("log", [])[:2]) or "(see report JSON)"))
    print("        metadata source: %s" % (report.get("metadata_source") or report.get("cache_dir") or "default cache"))

    print("[packages] the systemd pin is load-bearing")
    rc, report = run_verify(["--ga-only", "--offline" if os.path.isdir(CACHE) else "--ga-only"])
    check(rc != 0, "GA-only resolution FAILS (rc %s) rather than silently dropping the pin" % rc)
    check(report.get("verdict") == "FAILED", "GA-only verdict is FAILED (%r)" % report.get("verdict"))
    pin_mismatches = report.get("pin_mismatches") or []
    check(any(p.get("package") == "systemd" for p in pin_mismatches),
          "the GA-only failure names the systemd pin mismatch")

    print("[packages] metadata provenance is recorded (every NEVRA is attributable)")
    prov = (manifest.get("source") or {}).get("metadata_provenance") or []
    check(len(prov) >= 2, "the manifest records provenance for both Fedora 43 repositories (%d)" % len(prov))
    for rec in prov:
        repo = rec.get("repo", "?")
        rm = (rec.get("repomd") or {}).get("sha256", "")
        pr = rec.get("primary") or {}
        check(len(rm) == 64 and all(c in "0123456789abcdef" for c in rm),
              "%s repomd.xml sha256 recorded (%s)" % (repo.rsplit("/", 1)[-1] or repo, rm[:12] or "missing"))
        check(len(pr.get("compressed_sha256", "")) == 64,
              "%s primary payload sha256 recorded (%s bytes)" % (repo.rsplit("/", 1)[-1] or repo, pr.get("compressed_bytes")))
        check(len(pr.get("decompressed_sha256", "")) == 64,
              "%s decompressed primary sha256 recorded" % (repo.rsplit("/", 1)[-1] or repo))
        check(bool(pr.get("href")), "%s primary href recorded" % (repo.rsplit("/", 1)[-1] or repo))
    live_prov = resolution_report.get("metadata_provenance") or []
    check(len(live_prov) >= 2, "the verifier report carries the same provenance chain (%d)" % len(live_prov))
    # Reproducibility: re-deriving from the cached artifacts must produce the
    # recorded hashes. Drift in `updates` is possible by design (the repos move)
    # and is reported, not hidden; a mismatch in the GA repository is a failure.
    by_repo = {r.get("repo"): r for r in prov}
    for rec in live_prov:
        want = by_repo.get(rec.get("repo"))
        got = (rec.get("primary") or {}).get("compressed_sha256")
        if not want:
            continue
        same = (want.get("primary") or {}).get("compressed_sha256") == got
        ga = "/releases/43/" in (rec.get("repo") or "")
        if same:
            print("  OK   %s metadata is bit-identical to the recorded artifact" % rec["repo"].rsplit("/", 1)[-1])
        elif ga:
            check(False, "GA metadata drifted for %s (recorded %s, current %s) - re-run --emit-manifest"
                  % (rec["repo"], (want.get("primary") or {}).get("compressed_sha256", "")[:12], (got or "")[:12]))
        else:
            print("  INFO %s metadata drifted (documented: the updates repo moves) recorded=%s current=%s"
                  % (rec["repo"].rsplit("/", 1)[-1], (want.get("primary") or {}).get("compressed_sha256", "")[:12], (got or "")[:12]))

    print("[packages] no metadata source is reported, not guessed")
    with tempfile.TemporaryDirectory() as tmp:
        rc, report = run_verify(["--offline", "--cache-dir", tmp])
        check(rc != 0, "an empty cache exits non-zero")
        check(report.get("verdict") == "BLOCKED_EXTERNAL_RESOURCE",
              "an empty cache reports BLOCKED_EXTERNAL_RESOURCE (%r)" % report.get("verdict"))
        check(not (report.get("resolved") or {}), "nothing is reported as resolved without metadata")

    print("[packages] the builder cannot hide an unavailable package")
    builder = open(BUILDER).read()
    active = [ln for ln in builder.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    active_text = "\n".join(active)
    for flag in ("--skip-unavailable", "--skip-broken", "--setopt=strict=0"):
        check(flag not in active_text, "the builder never uses %s (comments excluded)" % flag)
    check("--skip-unavailable" in builder,
          "the builder documents why --skip-unavailable is not used")
    check("verify-packages.py" in builder,
          "the builder runs verify-packages.py before installing (fail fast on metadata)")
    check("set -Eeuo pipefail" in builder, "the builder runs under set -Eeuo pipefail")

    print("[packages] the manifest is what the builder installs")
    lines = builder.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if re.search(r"\binstall\s*\\\s*$", line) and any("dnf " in lines[j] for j in range(max(0, idx - 4), idx)):
            start = idx
    check(start is not None, "the dnf install line was located in the builder")
    install_lines = []
    if start is not None:
        after = lines[start].split(" install", 1)[1].rstrip(" \\")
        install_lines.append(after)
        for line in lines[start + 1:]:
            stripped = line.strip()
            if stripped.endswith("\\"):
                install_lines.append(stripped[:-1])
                continue
            install_lines.append(stripped)
            break
    tokens = set()
    for line in install_lines:
        for tok in line.split():
            tokens.add(re.sub(r"-(\d|:).*$", "", tok))  # normalise NEVRA/version forms
    check(bool(tokens), "the dnf install line was parsed (%d tokens)" % len(tokens))
    missing = sorted(n for n in declared if n not in tokens)
    check(not missing, "every manifest package is requested by the builder install line"
          + (" — missing: %s" % ", ".join(missing) if missing else ""))
    unexpected = sorted(t for t in tokens if t not in declared and not t.startswith("--"))
    print("        install-line tokens not in the manifest: %s" % (unexpected or "none"))

    vp = load_verify_module()
    print("[packages] requirement classifier, rich deps, cross-repo providers")
    test_requirement_classifier(vp, check)
    test_rich_dependency_evaluator(vp, check)
    test_cross_repository_provider_resolution(vp, check)

    print("[packages] the manifest carries the dependency evidence")
    deps = manifest.get("dependencies") or {}
    check(bool(deps), "the manifest has a dependencies{} block")
    check(deps.get("unresolved") == [], "no essential dependency is unresolved (%s)"
          % (deps.get("unresolved") or "none"))
    check((deps.get("requirements_total") or 0) > 0,
          "the manifest records the requirement count (%s)" % deps.get("requirements_total"))
    kinds = deps.get("by_kind") or {}
    check(kinds.get("package", 0) > 0 and kinds.get("capability", 0) > 0,
          "requirements are classified (package=%s capability=%s file=%s rich=%s)"
          % (kinds.get("package"), kinds.get("capability"), kinds.get("file"), kinds.get("rich")))
    per_pkg = deps.get("per_package") or {}
    no_dep = [p["name"] for g in manifest["groups"] for p in g["packages"]
              if p["name"] not in per_pkg]
    check(not no_dep, "every manifest package carries its resolved requirements:[]"
          + (" -- missing: %s" % no_dep if no_dep else ""))
    bad_dep = [p["name"] for g in manifest["groups"] for p in g["packages"]
               if (p.get("requires") or {}).get("unresolved")]
    check(not bad_dep, "no package entry carries an unresolved requirement"
          + (" -- %s" % bad_dep if bad_dep else ""))
    check(deps.get("unverifiable_from_primary", {}).get("file", 0) > 0,
          "file requirements are counted as unverifiable-from-primary, not as verified")

    print("[packages] the manifest is validated as DATA (JSON schema, fail closed)")
    rc, report = run_verify(["--validate-manifest"])
    check(rc == 0, "the shipped manifest passes the embedded schema (rc=%s)" % rc)
    with tempfile.TemporaryDirectory() as tmp:
        broken = json.loads(json.dumps(manifest))
        broken["dependencies"] = {}
        broken["groups"][0]["packages"][0]["nevra"] = "not-a-nevra"
        path = os.path.join(tmp, "packages-manifest.json")
        with open(path, "w") as fh:
            json.dump(broken, fh)
        proc = subprocess.run([sys.executable, VERIFY, "--validate-manifest", "--manifest", path],
                              capture_output=True, text=True)
        check(proc.returncode != 0, "a tampered manifest is REJECTED (rc=%s)" % proc.returncode)
        check("MANIFEST INVALID" in proc.stdout and "dependencies" in proc.stdout,
              "the rejection names the malformed property (%s)"
              % (proc.stdout.strip().splitlines()[0][:110] if proc.stdout.strip() else "no output"))
        proc2 = subprocess.run([sys.executable, VERIFY, "--validate-manifest",
                                "--manifest", os.path.join(tmp, "missing.json")],
                               capture_output=True, text=True)
        check(proc2.returncode != 0, "a missing manifest is a failure, not a pass (rc=%s)"
              % proc2.returncode)

    print("[packages] the 4.14 compatibility items still exist in the tree")
    check(os.path.exists(os.path.join(ROOT, "tools", "s10plus", "a26", "nuxel-rootfs-fixes.sh")),
          "a26/nuxel-rootfs-fixes.sh present")
    check(os.path.exists(os.path.join(ROOT, "boot", "s10plus", "payload")),
          "the carried boot payload directory is present (libsystemd patch location)")

    if failures:
        print("\nFAILED: %d assertion(s)" % len(failures))
        return 1
    print("\nAll package-manifest checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

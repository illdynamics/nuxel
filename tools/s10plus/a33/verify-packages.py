#!/usr/bin/env python3
"""verify-packages.py - verified Fedora 43 aarch64 package manifest for Nuxel.

WHY THIS EXISTS
---------------
The S10+ userspace is a real Fedora 43 ARM64 RPM install; it is NOT built from a
hand-maintained list of guessed versions.  The one thing that must never happen
is a build that silently resolves a *different* systemd than the one Nuxel's
carried kernel-4.14 patch was compiled against: the S10+ boots the patched
`libsystemd-shared-258.11-1.fc43.so` (boot/s10plus/payload/), which Nuxel's
initramfs installs over `/usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so`
at boot (tools/s10plus/a17/edit-init-a17.py).  If DNF ever resolves systemd to a
different NEVRA the ABI of the two libraries diverges and every service start
degrades back to `ENOSYS` (see docs/s10plus-autonomous-boot-repair/
SYSTEMD-COMPATIBILITY.md).  That is the reason this tool exists.

WHAT IT DOES
------------
1. Locates real Fedora 43 aarch64 repository metadata (`repomd.xml` ->
   `primary.xml.[zst|gz|xz|zck]`) - network or an offline mirror.
2. Builds the set of every available package NEVRA in that repository.
3. Checks the Nuxel essential-package list from
   `images/s10plus/packages-manifest.json`:
     * every package must exist for aarch64,
     * every package marked `pin` must resolve to EXACTLY that NEVRA,
     * unavailable essential packages are reported, never hidden -
       there is no `--skip-unavailable` here, by design.
4. Cross-checks the carried 4.14 libsystemd patch against the resolved systemd
   NEVRA (filename version must equal the pinned systemd version).
5. `--emit-manifest` rewrites images/s10plus/packages-manifest.json from the
   real metadata (that is how the checked-in manifest was produced).

VERDICTS
--------
    resolved                      every essential package exists; all pins match
    BLOCKED_EXTERNAL_RESOURCE     no metadata source reachable and no usable cache
    FAILED                        metadata present but an essential package is
                                  missing, or a pin does not match

USAGE
-----
    python3 tools/s10plus/a33/verify-packages.py                # verify (network)
    python3 tools/s10plus/a33/verify-packages.py --offline      # verify (cache only)
    python3 tools/s10plus/a33/verify-packages.py --emit-manifest
    python3 tools/s10plus/a33/verify-packages.py --repo file:///srv/mirror/f43
    python3 tools/s10plus/a33/verify-packages.py --primary-xml /path/primary.xml

Nothing here touches a device, a partition, or /Users/wicked/x/nuxel/.qq.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import lzma
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
MANIFEST_PATH = os.path.join(REPO_ROOT, "images", "s10plus", "packages-manifest.json")
PAYLOAD_DIR = os.path.join(REPO_ROOT, "boot", "s10plus", "payload")
# Fedora 43 aarch64: the GA "Everything" repository AND its "updates"
# repository.  BOTH are required and this is not cosmetic: systemd-258.11-1.fc43
# (the NEVRA the carried 4.14 libsystemd-shared patch was built from) and the
# `stevia`/`stevia-phosh-osk-provider` OSK packages exist ONLY in `updates`;
# the GA repo carries systemd-258-1.fc43 and no `stevia` at all.
DEFAULT_REPOS = [
    "https://dl.fedoraproject.org/pub/fedora/linux/releases/43/Everything/aarch64/os",
    "https://dl.fedoraproject.org/pub/fedora/linux/updates/43/Everything/aarch64",
]
DEFAULT_REPO = DEFAULT_REPOS[0]  # kept for callers that want the GA repo alone
DEFAULT_CACHE = os.path.join(REPO_ROOT, "build", "pkgmeta", "fedora43-aarch64")
RELEASEVER = "43"
BASearch = "aarch64"

# ---------------------------------------------------------------------------
# The essential package list.  Grouped so the dependency report can be read by
# component.  `pin` entries carry an exact NEVRA that MUST be preserved; every
# other entry only has to exist for aarch64 in the Fedora 43 repository.
# ---------------------------------------------------------------------------
SYSTEMD_PIN = "systemd-258.11-1.fc43.aarch64"

ESSENTIAL_GROUPS: "List[Tuple[str, str, List[dict]]]" = [
    ("base", "Fedora base OS, init and the 4.14-compatible service manager", [
        {"name": "filesystem"}, {"name": "setup"}, {"name": "fedora-release"},
        {"name": "glibc"}, {"name": "glibc-langpack-en"},
        {"name": "bash"}, {"name": "coreutils"}, {"name": "util-linux"},
        {"name": "findutils"}, {"name": "grep"}, {"name": "sed"}, {"name": "gawk"},
        {"name": "shadow-utils"}, {"name": "procps-ng"}, {"name": "kmod"},
        {"name": "e2fsprogs"}, {"name": "ca-certificates"}, {"name": "curl"},
        # systemd is PINNED: the carried kernel-4.14 libsystemd-shared patch
        # ships as libsystemd-shared-<ver>-<rel>.fc43.so and the SONAME contains
        # that exact version-release, so a drift here silently ignores the patch
        # and every unit start goes back to `ENOSYS`.  The GA repo has
        # systemd-258-1.fc43; the pinned NEVRA is only in `updates`.
        {"name": "systemd", "pin": SYSTEMD_PIN},
        {"name": "systemd-udev", "same_release_as": "systemd"},
        {"name": "systemd-networkd", "same_release_as": "systemd"},
    ]),
    ("dbus", "System message bus (dbus-daemon is the 4.14-usable implementation)", [
        {"name": "dbus-daemon"}, {"name": "dbus-broker"},
    ]),
    ("python", "Python 3 runtime used by every Nuxel service", [
        {"name": "python3"},
    ]),
    ("graphics", "Software display path (wlroots/pixman; no DRM on this kernel)", [
        {"name": "mesa-dri-drivers"}, {"name": "mesa-libEGL"}, {"name": "mesa-libgbm"},
        {"name": "libinput"}, {"name": "seatd"},
    ]),
    ("session", "Wayland compositor, phone shell and on-screen keyboard", [
        {"name": "phoc"}, {"name": "phosh"}, {"name": "stevia"},
        {"name": "stevia-phosh-osk-provider"}, {"name": "greetd"},
    ]),
    ("webkit", "WebKitGTK/GTK runtime for nuxel-pwa-host (the launcher surface)", [
        {"name": "gtk3"}, {"name": "webkit2gtk4.1"}, {"name": "gtk4"},
        {"name": "libadwaita"},
    ]),
    ("network", "Connectivity stack", [
        {"name": "NetworkManager"}, {"name": "NetworkManager-wifi"},
        {"name": "ModemManager"}, {"name": "iproute"},
    ]),
    ("connectors", "D-Bus connectors nuxel-bridge talks to", [
        {"name": "geoclue2"}, {"name": "bluez"},
    ]),
    ("audio", "PipeWire/WirePlumber + ALSA (beyond-madera card path)", [
        {"name": "pipewire"}, {"name": "wireplumber"}, {"name": "alsa-lib"},
    ]),
    ("security", "Polkit authorisation + nftables firewall", [
        {"name": "polkit"}, {"name": "nftables"},
    ]),
    ("power", "Power/session peripherals", [
        {"name": "upower"},
    ]),
]


def log(msg: str) -> None:
    sys.stderr.write("[verify-packages] %s\n" % msg)


# ---------------------------------------------------------------------------
# decompression: stdlib first, then the zstd module, then the zstd CLI.
# ---------------------------------------------------------------------------
def _zstd_decompress(data: bytes) -> Optional[bytes]:
    try:  # python >= 3.14 stdlib
        import compression.zstd as _z  # type: ignore
        return _z.decompress(data)
    except Exception:  # noqa: BLE001
        pass
    try:
        import zstandard  # type: ignore
        return zstandard.ZstdDecompressor().decompress(data, max_output_size=512 * 1024 * 1024)
    except Exception:  # noqa: BLE001
        pass
    exe = shutil.which("zstd")
    if exe:
        p = subprocess.run([exe, "-d", "-c"], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode == 0:
            return p.stdout
    return None


def _decompress(name: str, data: bytes) -> Tuple[Optional[bytes], Optional[str]]:
    """Return (xml_bytes, error). Supports .zst/.gz/.xz and raw xml."""
    if name.endswith(".zst") or data[:4] == b"\x28\xb5\x2f\xfd":
        out = _zstd_decompress(data)
        if out is None:
            return None, "no zstd decoder (need python zstandard module or the zstd CLI)"
        return out, None
    if name.endswith(".gz") or data[:2] == b"\x1f\x8b":
        return gzip.decompress(data), None
    if name.endswith(".xz") or data[:6] == b"\xfd7zXZ\x00":
        return lzma.decompress(data), None
    if name.endswith(".zck"):
        return None, "zchunk (.zck) is not supported; use the .zst primary metadata"
    return data, None


def repo_cache_dir(cache_dir: str, repo: str) -> str:
    """Per-repository cache subdir (both repos end in .../aarch64)."""
    key = hashlib.sha1(repo.encode()).hexdigest()[:12]
    return os.path.join(cache_dir, key)


def fetch(url: str, cache_path: str, offline: bool) -> Tuple[Optional[bytes], Optional[str]]:
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as fh:
            return fh.read(), None
    if offline:
        return None, "cache miss for %s" % url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nuxel-verify-packages/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (repo URL is operator-supplied)
            data = resp.read()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return None, "fetch failed for %s: %s" % (url, exc)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "wb") as fh:
        fh.write(data)
    return data, None


def repo_base(base: str) -> str:
    return base.rstrip("/")


def fetch_primary(repo: str, cache_dir: str, offline: bool
                  ) -> Tuple[Optional[bytes], Optional[str], Dict[str, object]]:
    """Fetch and return (primary_xml, error, provenance).

    `provenance` is the chain-of-custody record for this repository: which
    artifact was fetched, from where, and its sha256. It is emitted in the
    report and in the manifest so a reviewer can re-fetch the exact same
    metadata and re-derive the package set (evidence discipline: no version in
    the manifest is unattributable).
    """
    base = repo_base(repo)
    if base.startswith("file://"):
        local = base[len("file://"):]
        repomd_path = os.path.join(local, "repodata", "repomd.xml")
        if not os.path.exists(repomd_path):
            return None, "no repomd.xml under %s" % local, {}
        with open(repomd_path, "rb") as fh:
            repomd = fh.read()
    else:
        repomd, err = fetch(base + "/repodata/repomd.xml", os.path.join(cache_dir, "repomd.xml"), offline)
        if repomd is None:
            return None, err, {}
    try:
        root = ET.fromstring(repomd)
    except ET.ParseError as exc:
        return None, "repomd.xml is not valid XML: %s" % exc, {}
    href = None
    for data in root:
        if data.tag.rsplit("}", 1)[-1] != "data":
            continue
        if data.get("type") != "primary":
            continue
        for child in data:
            if child.tag.rsplit("}", 1)[-1] == "location":
                href = child.get("href")
                break
        if href:
            break
    if not href:
        return None, "repomd.xml has no <data type=primary>", {}
    # Fetch the primary payload (file:// or http).
    if base.startswith("file://"):
        p = os.path.join(base[len("file://"):], href)
        if not os.path.exists(p):
            return None, "primary metadata %s missing in mirror" % href, {}
        with open(p, "rb") as fh:
            raw = fh.read()
    else:
        cache_name = os.path.join(cache_dir, os.path.basename(href))
        raw, err = fetch(base + "/" + href, cache_name, offline)
        if raw is None:
            return None, err, {}
    xml, err = _decompress(href, raw)
    if xml is None:
        return None, "could not decompress %s: %s" % (href, err), {}
    provenance = {
        "repo": repo_base(repo),
        "repomd": {"sha256": hashlib.sha256(repomd).hexdigest()},
        "primary": {"href": href,
                    "compressed_sha256": hashlib.sha256(raw).hexdigest(),
                    "compressed_bytes": len(raw),
                    "decompressed_sha256": hashlib.sha256(xml).hexdigest()},
    }
    return xml, None, provenance


def parse_primary(xml: bytes) -> Dict[str, List[str]]:
    """Return {package_name: [NEVRA, ...]} for arch aarch64/noarch."""
    index: Dict[str, List[str]] = {}
    root = ET.fromstring(xml)
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag[: root.tag.index("}") + 1]
    for pkg in root.findall(ns + "package"):
        name = pkg.findtext(ns + "name")
        arch = pkg.findtext(ns + "arch")
        if not name or arch not in ("aarch64", "noarch"):
            continue
        ver = pkg.find(ns + "version")
        if ver is None:
            continue
        epoch = ver.get("epoch") or "0"
        v = ver.get("ver") or ""
        rel = ver.get("rel") or ""
        if epoch not in ("0", ""):
            nevra = "%s-%s:%s-%s.%s" % (name, epoch, v, rel, arch)
        else:
            nevra = "%s-%s-%s.%s" % (name, v, rel, arch)
        index.setdefault(name, []).append(nevra)
    for k in index:
        index[k].sort()
    return index


_VER_TOKEN = None  # lazily compiled


def _ver_tokens(text: str):
    """Tokenise a version-release for rpm-ish ordering.

    Runs of digits compare numerically, everything else lexically, and a
    numeric run always beats a non-numeric run.  This is deliberately simple
    (not a full rpmvercmp) but it puts 1.4.11 > 1.4.8 and 258.11-1 > 258-1 in
    the right order, which is all the manifest needs.
    """
    import re
    tokens = []
    for part in re.findall(r"[0-9]+|[^0-9]+", text):
        if part.isdigit():
            tokens.append((1, int(part), ""))
        else:
            tokens.append((0, 0, part))
    return tuple(tokens)


def verkey(nevra: str):
    """Sort key selecting the newest NEVRA of a package."""
    return _ver_tokens(nevra_version(nevra))


def nevra_version(nevra: str) -> str:
    """Return "<version>-<release>" from a NEVRA.

    Package names may themselves contain '-', so the version-release is read
    from the RIGHT: systemd-udev-258.11-1.fc43.aarch64 -> "258.11-1.fc43".
    """
    body = nevra
    for suffix in (".aarch64", ".noarch", ".src", ".x86_64"):
        if body.endswith(suffix):
            body = body[: -len(suffix)]
            break
    parts = body.split("-")
    if len(parts) < 3:
        return body
    return "-".join(parts[-2:])


def carried_patch_systemd_version() -> Optional[str]:
    """Read the version of the carried 4.14 libsystemd-shared patch filename."""
    if not os.path.isdir(PAYLOAD_DIR):
        return None
    hits = [f for f in os.listdir(PAYLOAD_DIR) if f.startswith("libsystemd-shared-") and f.endswith(".so")]
    if not hits:
        return None
    return hits[0][len("libsystemd-shared-"):-len(".so")]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Verify the Fedora 43 aarch64 package manifest")
    ap.add_argument("--repo", action="append", default=None,
                    help="repository base URL (http(s):// or file://); repeatable. "
                         "Default: the Fedora 43 aarch64 GA repo AND its updates repo.")
    ap.add_argument("--ga-only", action="store_true",
                    help="resolve against the GA repository only (expected to FAIL the systemd pin)")
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE)
    ap.add_argument("--offline", action="store_true", help="use the cache only; never touch the network")
    ap.add_argument("--primary-xml", help="use an already-decompressed primary.xml")
    ap.add_argument("--manifest", default=MANIFEST_PATH)
    ap.add_argument("--emit-manifest", action="store_true", help="rewrite the manifest from real metadata")
    ap.add_argument("--report", help="write the JSON report to this path as well as stdout")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    os.makedirs(args.cache_dir, exist_ok=True)
    start = time.time()

    repos = args.repo if args.repo else ([DEFAULT_REPOS[0]] if args.ga_only else list(DEFAULT_REPOS))

    indices: "List[Tuple[str, Dict[str, List[str]]]]" = []
    errors: List[str] = []
    total = 0
    provenance: List[dict] = []
    if args.primary_xml:
        with open(args.primary_xml, "rb") as fh:
            raw_px = fh.read()
        xml, err = _decompress(args.primary_xml, raw_px)
        if xml is None:
            errors.append(err or "could not read --primary-xml")
        else:
            idx = parse_primary(xml)
            total = sum(len(v) for v in idx.values())
            indices.append((args.primary_xml, idx))
            provenance.append({
                "repo": args.primary_xml,
                "primary": {"href": os.path.basename(args.primary_xml),
                            "compressed_sha256": hashlib.sha256(raw_px).hexdigest(),
                            "compressed_bytes": len(raw_px),
                            "decompressed_sha256": hashlib.sha256(xml).hexdigest()},
                "source": "local primary.xml",
            })
    else:
        for repo in repos:
            xml, err, prov = fetch_primary(repo, repo_cache_dir(args.cache_dir, repo), args.offline)
            if xml is None:
                errors.append("%s: %s" % (repo, err))
                continue
            idx = parse_primary(xml)
            n = sum(len(v) for v in idx.values())
            total += n
            log("%s -> %d aarch64/noarch NEVRAs" % (repo, n))
            indices.append((repo, idx))
            if prov:
                prov["source"] = "offline cache" if args.offline else "network (dl.fedoraproject.org)"
                prov["nevra_count"] = n
                provenance.append(prov)

    report = {
        "tool": "verify-packages.py",
        "fedora_release": RELEASEVER,
        "basearch": BASearch,
        "repos": [r for r, _ in indices] or repos,
        "offline": args.offline,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": "FAILED",
        "missing": [],
        "pin_mismatches": [],
        "resolved": {},
        "carried_patch_systemd_version": carried_patch_systemd_version(),
        "metadata_provenance": provenance,
        "errors": [],
        "duration_s": 0.0,
    }

    if not indices:
        report["verdict"] = "BLOCKED_EXTERNAL_RESOURCE"
        report["errors"].extend(errors or ["no metadata source"])
        report["duration_s"] = round(time.time() - start, 3)
        _emit(report, args)
        log("verdict=BLOCKED_EXTERNAL_RESOURCE (%s)" % (errors or "no metadata source"))
        return 3
    if errors:
        report["errors"].extend(errors)

    # merged view: name -> NEVRA set across every repository we could read.
    merged: Dict[str, List[str]] = {}
    for _repo, idx in indices:
        for name, nevras in idx.items():
            merged.setdefault(name, [])
            merged[name].extend(nevras)
    for name in merged:
        merged[name] = sorted(set(merged[name]))
    report["package_count"] = sum(len(v) for v in merged.values())
    log("loaded %d distinct package NEVRAs for aarch64/noarch from %d real Fedora %s repositories"
        % (report["package_count"], len(indices), RELEASEVER))

    # Resolve the essential list.
    resolved = {}
    same_rel: "List[Tuple[str, str]]" = []
    for group, _desc, pkgs in ESSENTIAL_GROUPS:
        for spec in pkgs:
            name = spec["name"]
            avail = merged.get(name, [])
            if not avail:
                report["missing"].append({"group": group, "package": name,
                                          "pin": spec.get("pin")})
                continue
            if spec.get("pin"):
                # newest occurrence wins; the pin must be present verbatim.
                resolved[name] = spec["pin"]
                if spec["pin"] not in avail:
                    report["pin_mismatches"].append({"group": group, "package": name,
                                                     "expected": spec["pin"], "available": avail})
            else:
                resolved[name] = max(avail, key=verkey)  # newest available
            if spec.get("same_release_as"):
                same_rel.append((name, spec["same_release_as"]))
    # same_release_as: systemd subpackages must be the same version-release as
    # the pinned systemd, otherwise the shared library ABI the patch targets
    # will not match the installed binaries.
    for name, anchor in same_rel:
        want = nevra_version(resolved[anchor]) if anchor in resolved else None
        got = nevra_version(resolved[name]) if name in resolved else None
        report.setdefault("release_alignment", {})[name] = {"anchor": anchor, "want": want, "got": got}
        if want and got and want != got:
            report["pin_mismatches"].append({"group": "base", "package": name,
                                             "expected": "%s (same release as %s)" % (got, anchor),
                                             "available": sorted(merged.get(name, []), key=verkey)[-4:],
                                             "reason": "systemd subpackage is not the same "
                                                       "version-release as the pinned systemd"})
    report["resolved"] = resolved

    # Cross-check the carried 4.14 libsystemd patch against the systemd pin.
    cpv = report["carried_patch_systemd_version"]
    sysnevra = resolved.get("systemd")
    report["carried_patch_matches_systemd"] = bool(cpv and sysnevra and nevra_version(sysnevra) == cpv)
    if cpv is None:
        report["errors"].append("carried libsystemd-shared patch not found in %s" % PAYLOAD_DIR)
    elif sysnevra and not report["carried_patch_matches_systemd"]:
        report["errors"].append(
            "carried patch is libsystemd-shared-%s.so but the manifest resolves systemd-%s "
            "(rebuild the patch or repin systemd)" % (cpv, nevra_version(sysnevra)))

    if report["missing"] or report["pin_mismatches"]:
        report["verdict"] = "FAILED"
    else:
        report["verdict"] = "resolved"

    if args.emit_manifest and report["verdict"] == "resolved":
        _write_manifest(report, args.manifest)

    report["duration_s"] = round(time.time() - start, 3)
    _emit(report, args)
    log("verdict=%s resolved=%d missing=%d pin_mismatches=%d" %
        (report["verdict"], len(resolved), len(report["missing"]), len(report["pin_mismatches"])))
    return 0 if report["verdict"] == "resolved" else 1


def _emit(report: dict, args) -> None:
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w") as fh:
            fh.write(text + "\n")
    if not args.quiet:
        print(text)


def _write_manifest(report: dict, path: str) -> None:
    resolved = report["resolved"]
    groups = []
    for group, desc, pkgs in ESSENTIAL_GROUPS:
        entries = []
        for spec in pkgs:
            name = spec["name"]
            if name not in resolved:
                continue
            entry = {"name": name, "nevra": resolved[name]}
            if spec.get("pin"):
                entry["pin"] = True
                entry["pin_reason"] = (
                    "ABI of the carried kernel-4.14 libsystemd-shared patch "
                    "(boot/s10plus/payload/libsystemd-shared-%s.so)" % report["carried_patch_systemd_version"]
                )
            entries.append(entry)
        groups.append({"id": group, "description": desc, "packages": entries})

    manifest = {
        "schema_version": 1,
        "generated": report["generated"],
        "source": {
            "distribution": "fedora",
            "release": RELEASEVER,
            "basearch": BASearch,
            "repos": report["repos"],
            "metadata": "repomd.xml -> primary.xml (real repository metadata)",
            "metadata_provenance": report.get("metadata_provenance", []),
            "package_count": report.get("package_count"),
        },
        "policy": {
            "no_skip_unavailable": True,
            "essential_packages_must_exist": True,
            "pins_must_match_exactly": True,
        },
        "protected_compat_items": [
            {
                "id": "libsystemd-4.14-patch",
                "what": "patched libsystemd-shared for kernels without pidfd_open/waitid(P_PIDFD)",
                "carried_version": report["carried_patch_systemd_version"],
                "source_edits": ["src/basic/process-util.c (posix_spawn fallback)",
                                 "src/basic/pidref.c (PidRef without pidfd degrades)"],
                "builder": "tools/s10plus/a17/build-systemd4.sh + tools/s10plus/a17/nuxel-systemd-edit.py",
                "installed_by": "tools/s10plus/a17/edit-init-a17.py (initramfs, over /usr/lib64/systemd/)",
                "constraint": "the systemd RPM NEVRA must stay %s" % resolved.get("systemd"),
            },
            {
                "id": "a26-rootfs-fixes",
                "what": "userdbd/dbus-broker/udevd containment on 4.14",
                "builder": "tools/s10plus/a26/nuxel-rootfs-fixes.sh (runs on the staging tree)",
                "details": ["nsswitch: drop the systemd varlink module",
                            "mask systemd-userdbd.{service,socket}",
                            "system bus -> dbus-daemon.service",
                            "mask systemd-udevd + its sockets"],
            },
        ],
        "groups": groups,
        "unavailable": report["missing"],
        "pin_mismatches": report["pin_mismatches"],
        "verdict": report["verdict"],
        "resolved_count": len(resolved),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    log("wrote manifest: %s (%d packages)" % (path, len(resolved)))


if __name__ == "__main__":
    sys.exit(main())

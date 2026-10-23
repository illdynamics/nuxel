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
5. It resolves DEPENDENCIES, not just package existence (briq-04a, revision 2):
   the rpm `Requires` of every candidate NEVRA of every essential package are
   read from the SAME primary.xml that resolved the package, classified by
   shape (package / capability / file / rpmlib / config) and resolved against
   the repository's package names and its real `rpm:provides` entries. A
   requirement nothing in Fedora 43 satisfies is a FAILURE, never a warning.
6. `--validate-manifest` checks the checked-in manifest against the JSON schema
   embedded here (stdlib-only, no jsonschema dependency) and fails closed on a
   malformed or incomplete document; `--emit-manifest` refuses to write a
   manifest that does not validate.
7. `--emit-manifest` rewrites images/s10plus/packages-manifest.json from the
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
import io
import json
import lzma
import os
import re
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
# Bump whenever the DERIVED parse result changes shape (classification rules,
# recorded fields).  A stale derived cache silently changing a verdict is the
# exact failure this number prevents.
INDEX_CACHE_VERSION = 2
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
        # A65-01: real GIO TLS backend (GnuTLS) so libsoup3/WebKitGTK can do
        # HTTPS. Without this the launcher/browser only has GDummyTlsBackend and
        # every https:// load fails with "TLS support is not available".
        {"name": "glib-networking"},
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


def _rpm_ns(root) -> str:
    """The `rpm:` XML namespace of the primary metadata (never hardcoded)."""
    for el in root.iter():
        tag = el.tag
        if isinstance(tag, str) and tag.endswith("}requires"):
            return tag[: tag.rindex("}") + 1]
    return "{http://linux.duke.edu/metadata/rpm}"


def classify_requirement(name: str) -> str:
    """Classify an rpm requirement by SHAPE (rpm has no "kind" field).

    Fedora's primary.xml spells requirements and provides as raw rpm capability
    strings, e.g.

        rpmlib(RichDependencies) <= 4.12.0-1     -> rpmlib
        config(systemd) = 258.11-1.fc43          -> config
        /usr/bin/sh                              -> file
        libc.so.6()(64bit)                       -> capability  (soname+version)
        python3.13dist(something)                -> capability
        hicolor-icon-theme                       -> package     (plain name)
        systemd >= 258.11                        -> package     (versioned)

    Only "package" (and a version constraint on one) can be resolved against a
    repository package NAME; everything else must be resolved against a
    provider's `rpm:provides` entry.  Getting this classification wrong is how
    a dependency check turns into a rubber stamp, so it is a named function
    with its own tests (tests/test-packages-manifest.py).
    """
    n = (name or "").strip()
    if not n:
        return "empty"
    if n.startswith("("):
        # rpm RICH (boolean) dependency: "(A or B)", "(A if B else C)", …
        return "rich"
    if n.startswith("rpmlib("):
        return "rpmlib"
    if n.startswith("config("):
        return "config"
    if n.startswith("/"):
        return "file"
    if "(" in n or ")" in n or " " in n or any(op in n for op in (">=", "<=", "==", "!=", ">", "<", "=")):
        # sonames with a version suffix, python3dist(...), rich deps, and any
        # comparison operator all land here; none is a package name.
        return "capability"
    return "package"


def req_base_name(name: str) -> str:
    """The capability name of a requirement, with any version constraint removed.

    `systemd >= 258.11` -> `systemd`; `libc.so.6()(64bit)` -> unchanged.
    """
    n = (name or "").strip()
    m = re.match(r"^([^\s<>=!]+)\s*(?:[<>=!]+.*)?$", n)
    return m.group(1) if m else n


_RICH_OPS = ("without", "with", "else", "if", "and", "or")


def split_rich(text: str) -> List[str]:
    """Split a rich dependency body into [operand, op, operand, ...] tokens.

    Only TOP-LEVEL operator KEYWORDS delimited by whitespace split the string,
    so version constraints survive intact:

        "wpa_supplicant >= 1:1.1 or iwd"   -> ['wpa_supplicant >= 1:1.1', 'or', 'iwd']
        "glibc-gconv-extra(aarch-64) = 2.42 if redhat-rpm-config"
                                          -> ['glibc-gconv-extra(aarch-64) = 2.42',
                                              'if', 'redhat-rpm-config']
        "(a or b) and c"                  -> ['(a or b)', 'and', 'c']

    Returns [] when the text does not have the alternating operand/operator
    shape rpm requires; the caller then records the expression as undecidable
    instead of guessing a verdict.
    """
    parts: List[str] = []
    buf = ""
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "(":
            depth += 1
            buf += ch
            i += 1
            continue
        if ch == ")":
            depth -= 1
            buf += ch
            i += 1
            continue
        if depth == 0 and ch.isspace() and buf.strip():
            matched = None
            for op in _RICH_OPS:
                if text.startswith(op + " ", i + 1):
                    matched = op
                    break
                if i + 1 + len(op) == n and text.startswith(op, i + 1):
                    matched = op
                    break
            if matched:
                parts.append(buf.strip())
                parts.append(matched)
                buf = ""
                i += len(matched) + 1
                while i < n and text[i].isspace():
                    i += 1
                continue
        buf += ch
        i += 1
    if buf.strip():
        parts.append(buf.strip())
    if not parts:
        return []
    # Alternation check: operand, op, operand, op, ... , operand
    for idx, tok in enumerate(parts):
        if idx % 2 == 0:
            if tok in _RICH_OPS:
                return []
        else:
            if tok not in _RICH_OPS:
                return []
    if len(parts) % 2 == 0:
        return []
    return parts


def strip_outer_parens(text: str) -> str:
    """Remove ONE pair of enclosing parentheses if they wrap the whole text."""
    t = text.strip()
    if not (t.startswith("(") and t.endswith(")")):
        return t
    depth = 0
    for i, ch in enumerate(t):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and i != len(t) - 1:
                return t           # the parens do not wrap the whole expression
    return t[1:-1].strip() if depth == 0 else t


def rich_atoms(expr: str) -> List[str]:
    """Every atom name mentioned by a rich dependency (recursively)."""
    out: List[str] = []
    body = strip_outer_parens(expr)
    parts = split_rich(body)
    if not parts:
        return out
    for i, tok in enumerate(parts):
        if i % 2 == 1:
            continue               # operator
        if tok.startswith("("):
            out.extend(rich_atoms(tok))
        else:
            out.append(tok.split()[0] if tok.split() else tok)
    return out


def eval_rich(expr: str, resolve) -> Optional[bool]:
    """Evaluate a rich dependency. Returns True / False / None (undecidable).

    `resolve(atom_name, versioned) -> True|False|None`, where None means "this
    verifier cannot decide from primary.xml" (a file requirement, rpmlib(), or
    an unsupported operator shape).  Tri-state logic, never a guess:

        and      : False if any operand is False; else None if any is None; else True
        with     : same as and
        or       : True if any operand is True; else None if any is None; else False
        if       : (A if B)            -> B False => True (vacuous); B True => A
        if/else  : (A if B else C)     -> B True => A; B False => C
        without  : (A without B)       -> B False => A; else undecidable
    """
    body = strip_outer_parens(expr)
    parts = split_rich(body)
    if not parts:
        return None
    operands = parts[0::2]
    ops = parts[1::2]

    def operand_value(tok: str) -> Optional[bool]:
        if tok.startswith("("):
            return eval_rich(tok, resolve)
        bits = tok.split()
        if not bits:
            return None
        return resolve(bits[0], len(bits) > 1)

    if not ops:
        return operand_value(operands[0])

    values = [operand_value(o) for o in operands]

    if ops == ["and"] or ops == ["with"]:
        if any(v is False for v in values):
            return False
        return None if any(v is None for v in values) else True
    if ops == ["or"]:
        if any(v is True for v in values):
            return True
        return None if any(v is None for v in values) else False
    if ops == ["if"]:
        cond = values[1]
        if cond is False:
            return True            # the condition is not satisfied: vacuous
        if cond is None:
            return None
        return values[0]
    if ops == ["if", "else"]:
        cond = values[1]
        if cond is None:
            return None
        return values[0] if cond else values[2]
    if ops == ["without"]:
        return values[0] if values[1] is False else None
    return None                     # mixed operators: refused, never guessed


def parse_primary(xml: bytes, want_requires: "Optional[set]" = None) -> Dict[str, object]:
    """Parse one primary.xml into the index plus the dependency evidence.

    Returns
    -------
    {
      "index":     {package_name: [NEVRA, ...]},          # aarch64 + noarch
      "requires":  {package_name: {NEVRA: [{name, pre, base, kind}, ...]}},
      "names":     {package_name, ...},
    }

    (Providers are resolved separately by scan_providers(), because the needed
    set is only complete once EVERY repository has been read.)

    `want_requires` bounds the work: requirements are recorded only for the
    package names the caller asks about (the essential list), and providers are
    collected only for the exact requirement strings those packages declare.
    That keeps the dependency check proportional to the essential set while
    still resolving against the WHOLE repository.
    """
    want = want_requires or set()
    root = ET.fromstring(xml)
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag[: root.tag.index("}") + 1]
    rpm = _rpm_ns(root)
    index: Dict[str, List[str]] = {}
    requires: Dict[str, Dict[str, List[dict]]] = {}
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
        if name in want:
            fmt = pkg.find(ns + "format")
            entries: List[dict] = []
            if fmt is not None:
                rel_el = fmt.find(rpm + "requires")
                if rel_el is not None:
                    for entry in rel_el.findall(rpm + "entry"):
                        rn = entry.get("name")
                        if not rn:
                            continue
                        entries.append({
                            "name": rn,
                            "base": req_base_name(rn),
                            "kind": classify_requirement(rn),
                            "pre": entry.get("pre") == "1",
                            "versioned": bool(entry.get("flags")),
                            "constraint": ("%s %s" % (entry.get("flags"), " ".join(
                                x for x in (entry.get("epoch"), entry.get("ver"), entry.get("rel")) if x))
                                ).strip() if entry.get("flags") else None,
                        })
            requires.setdefault(name, {})[nevra] = entries
    for k in index:
        index[k].sort()

    return {"index": index, "requires": requires, "names": set(index)}


def global_needed(requires: Dict[str, Dict[str, List[dict]]]) -> "set":
    """Every requirement string that must be resolvable, across ALL repositories.

    This MUST be computed globally: on Fedora 43 the requiring package and the
    providing package are frequently in *different* repositories (measured:
    `stevia` is in `updates` and requires `libdconf.so.1()(64bit)`, which only
    `dconf` in the GA repository provides).  A per-repository resolution would
    report that pair as unsatisfiable - a false FAILED on a package set that
    dnf installs without complaint.
    """
    needed = set()
    for by_name in requires.values():
        for entries in by_name.values():
            for r in entries:
                if r["kind"] in ("package", "capability"):
                    needed.add(r["base"])
                elif r["kind"] == "rich":
                    # An atom inside a rich dependency is still a capability
                    # some package must provide ("(wpa_supplicant or iwd)").
                    for atom in rich_atoms(r["name"]):
                        if atom and not atom.startswith("/") and not atom.startswith("rpmlib("):
                            needed.add(atom)
    return needed


def needed_fingerprint(needed: "set") -> str:
    return hashlib.sha256("\n".join(sorted(needed)).encode()).hexdigest()[:16]


def scan_providers(xml: bytes, needed: "set") -> Dict[str, str]:
    """Return {capability_or_package_name: providing NEVRA} for `needed`.

    Streams the primary.xml (iterparse + clear) instead of materialising a
    second ElementTree: the GA metadata is ~180 MB of XML and the dependency
    pass must not double the peak memory of the resolve pass.  Only the exact
    strings listed in `needed` are stored, so the result stays small even
    though `rpm:provides` across the repository is millions of entries.
    """
    providers: Dict[str, str] = {}
    if not needed:
        return providers
    buf = io.BytesIO(xml)
    ns = ""
    rpm = "{http://linux.duke.edu/metadata/rpm}"
    for _event, el in ET.iterparse(buf, events=("end",)):
        if not el.tag.endswith("}package") and el.tag != "package":
            continue
        if not ns:
            ns = el.tag[: el.tag.rindex("}") + 1] if el.tag.startswith("{") else ""
        prov = el.find("%sformat/%sprovides" % (ns, rpm))
        if prov is not None:
            hit = [e.get("name") for e in prov.findall(rpm + "entry")
                   if e.get("name") in needed]
            if hit:
                name = el.findtext(ns + "name")
                arch = el.findtext(ns + "arch")
                ver = el.find(ns + "version")
                if name and arch and ver is not None:
                    nevra = "%s-%s-%s.%s" % (name, ver.get("ver") or "",
                                             ver.get("rel") or "", arch)
                    for cap in hit:
                        providers.setdefault(cap, nevra)
        el.clear()
    return providers


def resolve_dependencies(essential: "List[Tuple[str, str]]",
                         names: "set", providers: Dict[str, str],
                         requires: Dict[str, Dict[str, List[dict]]]) -> dict:
    """Resolve the requirements of the essential packages against the repository.

    `essential` = [(package_name, resolved_nevra), ...]
    `names`     = every package NAME in the resolved repositories (union)
    `providers` = capability/name -> providing NEVRA (union, from rpm:provides)
    `requires`  = {package_name: {NEVRA: [requirement, ...]}} (union)

    Returns the evidence block that goes into the report and the manifest.  A
    "package"/"capability" requirement is resolved if the repository carries a
    package of that name or a provider of that exact capability; anything else
    is `unresolved` and the caller fails closed on a non-empty list.
    """

    by_kind: Dict[str, int] = {}
    unresolved: List[dict] = []
    unverifiable: Dict[str, int] = {"file": 0, "rpmlib": 0, "config": 0, "empty": 0,
                                    "rich": 0, "rich_unparsable": 0}
    rich_resolved = 0
    rich_unverifiable: List[dict] = []

    def resolve_atom(name: str, versioned: bool = False):
        """Tri-state: True/False/None for one requirement atom."""
        kind = classify_requirement(name)
        if kind in ("file", "rpmlib", "config", "empty"):
            return None            # cannot be decided from primary.xml
        if name in names or name in providers:
            return True
        return False

    per_package: Dict[str, dict] = {}
    sample_providers: Dict[str, str] = {}
    total = 0
    for pkg_name, nevra in essential:
        per_nevra = (requires.get(pkg_name) or {})
        reqs: List[dict] = per_nevra.get(nevra) or []
        counts: Dict[str, int] = {}
        unresolved_here: List[str] = []
        plain: List[str] = []
        for r in reqs:
            kind = r["kind"]
            counts[kind] = counts.get(kind, 0) + 1
            by_kind[kind] = by_kind.get(kind, 0) + 1
            total += 1
            if kind == "rich":
                verdict = eval_rich(r["name"], resolve_atom)
                if verdict is True:
                    rich_resolved += 1
                    continue
                if verdict is None:
                    unverifiable["rich"] = unverifiable.get("rich", 0) + 1
                    rich_unverifiable.append({"package": pkg_name, "nevra": nevra,
                                              "raw": r["name"]})
                    continue
                if not split_rich(strip_outer_parens(r["name"])):
                    unverifiable["rich_unparsable"] = unverifiable.get("rich_unparsable", 0) + 1
                unresolved_here.append(r["name"])
                unresolved.append({"package": pkg_name, "nevra": nevra,
                                   "requirement": r["name"], "raw": r["name"], "kind": "rich"})
                continue
            if kind in ("file", "rpmlib", "config", "empty"):
                unverifiable[kind] = unverifiable.get(kind, 0) + 1
                continue
            base = r["base"]
            if base in names or base in providers:
                if r["kind"] == "capability" and base in providers and len(sample_providers) < 12:
                    sample_providers.setdefault(base, providers[base])
                if r["kind"] == "package":
                    plain.append(base)
                continue
            unresolved_here.append(base)
            unresolved.append({"package": pkg_name, "nevra": nevra,
                               "requirement": base, "raw": r["name"], "kind": kind})
        per_package[pkg_name] = {
            "nevra": nevra,
            "total": len(reqs),
            "by_kind": counts,
            "package_requirements": sorted(set(plain)),
            "unresolved": sorted(set(unresolved_here)),
        }
    return {
        "policy": {
            "fail_closed": True,
            "name_resolution": "a requirement is resolved if a repository package carries that "
                               "name or a repository package provides that exact capability "
                               "(rpm:provides from the same primary.xml)",
            "version_satisfaction": "delegated to dnf's solver: this verifier matches "
                                    "names/capabilities, it does not compare EVR strings",
            "file_requirements": "'kind=file' requirements (/usr/bin/sh) cannot be resolved from "
                                 "primary.xml - Fedora keeps file provides in filelists.xml, which "
                                 "this verifier deliberately does not download; they are counted, "
                                 "never reported as verified",
        },
        "essential_packages": len(essential),
        "requirements_total": total,
        "by_kind": by_kind,
        "rich_dependencies_resolved": rich_resolved,
        "unresolved": unresolved,
        "unverifiable_from_primary": unverifiable,
        "unverifiable_rich": rich_unverifiable,
        "sample_providers": sample_providers,
        "per_package": per_package,
    }


# ---------------------------------------------------------------------------
# MANIFEST JSON SCHEMA (stdlib-only validation, fail closed)
# ---------------------------------------------------------------------------
# The manifest is DATA the rootfs builder consumes, so a malformed manifest is
# as fatal as a missing package: a builder that globs over `groups` would
# silently install a SUBSET of the userspace.  The schema is embedded here (no
# jsonschema module on a Fedora 43 ARM64 phone image / build host) and is
# enforced by --validate-manifest and before every --emit-manifest write.
MANIFEST_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "schema", "generated", "source", "policy",
                 "protected_compat_items", "groups", "unavailable", "pin_mismatches",
                 "verdict", "resolved_count", "dependencies"],
    "additionalProperties": True,
    "properties": {
        "schema_version": {"type": "integer", "enum": [1]},
        "schema": {"type": "string", "pattern": "^nuxel\.packages-manifest/"},
        "generated": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T"},
        "verdict": {"type": "string", "enum": ["resolved", "FAILED", "BLOCKED_EXTERNAL_RESOURCE"]},
        "unavailable": {"type": "array"},
        "pin_mismatches": {"type": "array"},
        "resolved_count": {"type": "integer", "minimum": 1},
        "source": {
            "type": "object",
            "required": ["distribution", "release", "basearch", "repos", "metadata",
                         "metadata_provenance", "package_count"],
            "properties": {
                "distribution": {"type": "string", "enum": ["fedora"]},
                "release": {"type": "string", "enum": ["43"]},
                "basearch": {"type": "string", "enum": ["aarch64"]},
                "repos": {"type": "array", "minItems": 1},
                "metadata_provenance": {
                    "type": "array", "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["repo", "repomd", "primary"],
                        "properties": {
                            "repo": {"type": "string", "pattern": "/aarch64"},
                            "repomd": {"type": "object", "required": ["sha256"]},
                            "primary": {"type": "object",
                                        "required": ["href", "compressed_sha256",
                                                     "compressed_bytes"]},
                        },
                    },
                },
            },
        },
        "policy": {
            "type": "object",
            "required": ["no_skip_unavailable", "essential_packages_must_exist",
                         "pins_must_match_exactly"],
            "properties": {
                "no_skip_unavailable": {"type": "boolean", "enum": [True]},
                "essential_packages_must_exist": {"type": "boolean", "enum": [True]},
                "pins_must_match_exactly": {"type": "boolean", "enum": [True]},
            },
        },
        "protected_compat_items": {
            "type": "array", "minItems": 2,
            "items": {"type": "object", "required": ["id", "what"],
                      "properties": {"id": {"type": "string"}}},
        },
        "dependencies": {
            "type": "object",
            "required": ["policy", "essential_packages", "requirements_total",
                         "by_kind", "unresolved", "unverifiable_from_primary", "per_package"],
            "properties": {
                "essential_packages": {"type": "integer", "minimum": 1},
                "requirements_total": {"type": "integer", "minimum": 0},
                "unresolved": {"type": "array"},
                "per_package": {"type": "object"},
            },
        },
        "groups": {
            "type": "array", "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "description", "packages"],
                "properties": {
                    "id": {"type": "string"},
                    "packages": {
                        "type": "array", "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["name", "nevra"],
                            "properties": {
                                "name": {"type": "string"},
                                "nevra": {"type": "string",
                                          "pattern": "\.(aarch64|noarch)$"},
                            },
                        },
                    },
                },
            },
        },
    },
}

_SCHEMA_TYPES = {
    "object": dict, "array": list, "string": str, "integer": int,
    "number": (int, float), "boolean": bool,
}


def validate_json_schema(instance, schema, path: str = "$") -> List[str]:
    """Validate `instance` against the (draft-07 subset) schema. Returns errors.

    Supported: type, enum, required, properties, items, additionalProperties
    (bool), minItems, minimum, pattern.  That is the whole vocabulary the
    manifest schema uses; anything else would be silently ignored, so the
    validator asserts the schema itself only uses supported keywords.
    """
    errs: List[str] = []
    supported = {"type", "enum", "required", "properties", "items",
                 "additionalProperties", "minItems", "minimum", "pattern",
                 "description"}
    unknown = set(schema) - supported
    if unknown:
        raise AssertionError("schema keyword %r is not implemented (would be ignored silently)"
                             % sorted(unknown))
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(isinstance(instance, _SCHEMA_TYPES[t]) for t in types):
            errs.append("%s: expected %s, got %s" % (path, "|".join(types), type(instance).__name__))
            return errs
    if "enum" in schema and instance not in schema["enum"]:
        errs.append("%s: %r is not one of %r" % (path, instance, schema["enum"]))
    if isinstance(instance, str) and "pattern" in schema:
        if not re.search(schema["pattern"], instance):
            errs.append("%s: %r does not match %r" % (path, instance, schema["pattern"]))
    if isinstance(instance, (int, float)) and not isinstance(instance, bool) and "minimum" in schema:
        if instance < schema["minimum"]:
            errs.append("%s: %r < minimum %r" % (path, instance, schema["minimum"]))
    if isinstance(instance, list) and "minItems" in schema and len(instance) < schema["minItems"]:
        errs.append("%s: %d item(s) < minItems %d" % (path, len(instance), schema["minItems"]))
    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errs.extend(validate_json_schema(item, schema["items"], "%s[%d]" % (path, i)))
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errs.append("%s: required property %r is missing" % (path, key))
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in instance:
                errs.extend(validate_json_schema(instance[key], sub, "%s.%s" % (path, key)))
        if schema.get("additionalProperties") is False:
            extra = set(instance) - set(props)
            if extra:
                errs.append("%s: unexpected propert(ies) %r" % (path, sorted(extra)))
    return errs


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
    ap.add_argument("--validate-manifest", action="store_true",
                    help="validate the checked-in manifest against the embedded JSON schema "
                         "(stdlib-only) and exit without touching the network")
    ap.add_argument("--no-index-cache", action="store_true",
                    help="re-parse the primary metadata instead of reusing build/pkgmeta index cache")
    ap.add_argument("--report", help="write the JSON report to this path as well as stdout")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if args.validate_manifest:
        # Fail closed: the manifest is data the rootfs builder consumes, so a
        # malformed manifest is as fatal as a missing package.
        try:
            with open(args.manifest) as fh:
                doc = json.load(fh)
        except (OSError, ValueError) as exc:
            print("[verify-packages] MANIFEST INVALID: cannot read/parse %s: %s" % (args.manifest, exc))
            return 4
        problems = validate_json_schema(doc, MANIFEST_SCHEMA)
        if doc.get("verdict") != "resolved":
            problems.append("$.verdict: the shipped manifest records %r, not 'resolved'" % doc.get("verdict"))
        for entry in doc.get("unavailable") or []:
            problems.append("$.unavailable: %r is declared unavailable" % entry)
        if doc.get("resolved_count") != sum(len(g["packages"]) for g in doc.get("groups", [])):
            problems.append("$.resolved_count: %r != the number of packages in groups[]"
                            % doc.get("resolved_count"))
        if doc.get("pin_mismatches"):
            problems.append("$.pin_mismatches: %r" % doc["pin_mismatches"])
        deps = doc.get("dependencies") or {}
        if deps.get("unresolved"):
            problems.append("$.dependencies.unresolved: %d requirement(s) unresolvable"
                            % len(deps["unresolved"]))
        resolved_pkgs = [p["nevra"] for g in doc.get("groups", []) for p in g["packages"]]
        carried = None
        for item in doc.get("protected_compat_items") or []:
            if item.get("id") == "libsystemd-4.14-patch":
                carried = item.get("carried_version")
        pinned_systemd = [p["nevra"] for g in doc.get("groups", [])
                          for p in g["packages"] if p.get("pin") and p["name"] == "systemd"]
        if not pinned_systemd:
            problems.append("$: no pinned systemd entry in groups[] (the 4.14 patch anchor is gone)")
        elif carried is None:
            problems.append("$: protected_compat_items[] does not record the carried 4.14 patch version")
        elif pinned_systemd[0] != "systemd-%s.aarch64" % carried:
            problems.append("$: the pinned systemd NEVRA %r does not match the carried 4.14 patch %r"
                            % (pinned_systemd[0], carried))
        if problems:
            print("[verify-packages] MANIFEST INVALID (%d problem(s)): %s"
                  % (len(problems), json.dumps(problems, indent=1)))
            log("verdict=FAILED (manifest schema validation)")
            return 4
        print("[verify-packages] manifest schema OK: %d package(s), %d requirement(s) resolved "
              "across %d group(s)" % (len(resolved_pkgs), deps.get("requirements_total", 0),
                                      len(doc.get("groups", []))))
        log("verdict=resolved (manifest schema validation, stdlib validator)")
        return 0

    try:
        os.makedirs(args.cache_dir, exist_ok=True)
    except OSError as e:
        # The default cache lives under `build/pkgmeta/`, which is gitignored and
        # therefore does NOT exist on a clean checkout.  On the CI S10+ runner the
        # repo root is bind-mounted read-only inside the arm64 container, so this
        # makedirs() fails with "Read-only file system".  The cache is purely an
        # optimization (a fresh runner has nothing to reuse), so fall back to a
        # writable temp dir and keep building.
        print("[verify-packages] cache_dir %s not writable (%s); using %s"
              % (args.cache_dir, e.args[1] if e.args else e, tempfile.gettempdir()))
        args.cache_dir = tempfile.mkdtemp(prefix="nuxel-pkgmeta-")
    start = time.time()

    repos = args.repo if args.repo else ([DEFAULT_REPOS[0]] if args.ga_only else list(DEFAULT_REPOS))

    # The dependency check is bounded to the packages this manifest is about:
    # their `Requires` are recorded, and providers are collected only for the
    # exact requirement strings those packages declare.
    want_requires = {spec["name"] for _g, _d, pkgs in ESSENTIAL_GROUPS for spec in pkgs}

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
            parsed = parse_primary(xml, want_requires)
            total = sum(len(v) for v in parsed["index"].values())
            indices.append((args.primary_xml, parsed, xml))
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
            cache = repo_cache_dir(args.cache_dir, repo)
            xml, err, prov = fetch_primary(repo, cache, args.offline)
            if xml is None:
                errors.append("%s: %s" % (repo, err))
                continue
            parsed = None
            cache_key = (prov or {}).get("primary", {}).get("compressed_sha256")
            index_cache = os.path.join(cache, "index-%s.json" % (cache_key or "nocache")[:16])
            if cache_key and not args.no_index_cache and os.path.exists(index_cache):
                try:
                    with open(index_cache) as fh:
                        doc = json.load(fh)
                    if doc.get("cache_version") != INDEX_CACHE_VERSION:
                        raise ValueError("index cache version %r != %r (re-parsing)"
                                         % (doc.get("cache_version"), INDEX_CACHE_VERSION))
                    parsed = {"index": doc["index"], "requires": doc["requires"],
                              "names": set(doc["names"])}
                    log("%s -> reused the parsed index cache (%s)" % (repo, os.path.basename(index_cache)))
                except (OSError, ValueError, KeyError) as exc:  # noqa: BLE001
                    log("%s -> index cache unusable (%s); re-parsing" % (repo, exc))
                    parsed = None
            if parsed is None:
                parsed = parse_primary(xml, want_requires)
                if cache_key and not args.no_index_cache:
                    try:
                        os.makedirs(cache, exist_ok=True)
                        with open(index_cache, "w") as fh:
                            json.dump({"cache_version": INDEX_CACHE_VERSION,
                                       "index": parsed["index"], "requires": parsed["requires"],
                                       "names": sorted(parsed["names"])}, fh)
                    except OSError as exc:  # a cache we cannot write is not a failure
                        log("%s -> could not write the index cache (%s)" % (repo, exc))
            n = sum(len(v) for v in parsed["index"].values())
            total += n
            log("%s -> %d aarch64/noarch NEVRAs" % (repo, n))
            indices.append((repo, parsed, xml))
            if prov:
                prov["source"] = "offline cache" if args.offline else "network (dl.fedoraproject.org)"
                prov["nevra_count"] = n
                provenance.append(prov)

    report = {
        "tool": "verify-packages.py",
        "fedora_release": RELEASEVER,
        "basearch": BASearch,
        "repos": [r for r, _p, _x in indices] or repos,
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
    merged_names: "set" = set()
    merged_requires: Dict[str, Dict[str, List[dict]]] = {}
    for _repo, parsed, _xml in indices:
        merged_names |= parsed["names"]
        for pname, by_nevra in parsed["requires"].items():
            merged_requires.setdefault(pname, {}).update(by_nevra)
        for name, nevras in parsed["index"].items():
            merged.setdefault(name, [])
            merged[name].extend(nevras)
    for name in merged:
        merged[name] = sorted(set(merged[name]))
    report["package_count"] = sum(len(v) for v in merged.values())
    log("loaded %d distinct package NEVRAs for aarch64/noarch from %d real Fedora %s repositories"
        % (report["package_count"], len(indices), RELEASEVER))

    # Providers, for the GLOBAL needed set (a requirer in one repository is
    # routinely provided by a package in the other - measured on Fedora 43).
    # The scan streams each primary.xml, so it costs I/O but not peak memory.
    needed = global_needed(merged_requires)
    fp = needed_fingerprint(needed)
    merged_providers: Dict[str, str] = {}
    for repo, parsed, xml in indices:
        cached = parsed.get("providers")
        if cached is not None and parsed.get("providers_fingerprint") == fp:
            found = cached
        else:
            found = scan_providers(xml, needed)
        log("%s -> %d provider(s) for the %d needed requirement(s)"
            % (repo, len(found), len(needed)))
        for cap, provider in found.items():
            merged_providers.setdefault(cap, provider)
    log("providers: %d of %d needed requirement(s) have a provider in the repository set"
        % (len(merged_providers), len(needed)))

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

    # ---- dependencies (briq-04a rev 2) ------------------------------------
    # The essential list proves the packages EXIST; this proves their rpm
    # requirements are satisfiable by the same repository set.  Fail closed:
    # an unresolved requirement is a FAILED verdict, never a warning.
    report["dependencies"] = resolve_dependencies(
        [(name, resolved[name]) for name in sorted(resolved)],
        merged_names, merged_providers, merged_requires)
    log("dependencies: %d requirement(s) of %d package(s); %d unresolved; "
        "unverifiable-from-primary=%s"
        % (report["dependencies"]["requirements_total"],
           report["dependencies"]["essential_packages"],
           len(report["dependencies"]["unresolved"]),
           {k: v for k, v in report["dependencies"]["unverifiable_from_primary"].items() if v}))

    if report["missing"] or report["pin_mismatches"] or report["dependencies"]["unresolved"]:
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


def _manifest_dependencies(report: dict) -> dict:
    """The dependency evidence as it goes into the manifest (bounded size)."""
    dep = report.get("dependencies") or {}
    return {
        "policy": dep.get("policy", {}),
        "essential_packages": dep.get("essential_packages", 0),
        "requirements_total": dep.get("requirements_total", 0),
        "by_kind": dep.get("by_kind", {}),
        "unresolved": dep.get("unresolved", []),
        "unverifiable_from_primary": dep.get("unverifiable_from_primary", {}),
        "sample_providers": dep.get("sample_providers", {}),
        "per_package": dep.get("per_package", {}),
    }


def _write_manifest(report: dict, path: str) -> None:
    resolved = report["resolved"]
    groups = []
    for group, desc, pkgs in ESSENTIAL_GROUPS:
        entries = []
        for spec in pkgs:
            name = spec["name"]
            if name not in resolved:
                continue
            dep = (report.get("dependencies") or {}).get("per_package", {}).get(name) or {}
            entry = {"name": name, "nevra": resolved[name],
                     "requires": {
                         "total": dep.get("total", 0),
                         "by_kind": dep.get("by_kind", {}),
                         "packages": dep.get("package_requirements", []),
                         "unresolved": dep.get("unresolved", []),
                     }}
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
        "schema": "nuxel.packages-manifest/1",
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
        "dependencies": _manifest_dependencies(report),
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
    # A manifest is only written if it validates against the embedded schema:
    # the builder consumes this file as data, so a malformed one must never land.
    problems = validate_json_schema(manifest, MANIFEST_SCHEMA)
    if problems:
        raise SystemExit("refusing to write an invalid manifest: %s" % json.dumps(problems, indent=1))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    log("wrote manifest: %s (%d packages, %d requirement(s) resolved)"
        % (path, len(resolved), manifest["dependencies"]["requirements_total"]))


if __name__ == "__main__":
    sys.exit(main())

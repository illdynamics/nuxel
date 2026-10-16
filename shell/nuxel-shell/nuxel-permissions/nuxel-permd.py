#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
nuxel-permd - Nuxel per-capability permission manager, enforcement planner and
review tool (briq-05a).

This is the repository-side, offline-testable heart of the Nuxel permission
system. It owns the durable grant store that the GTK app (main.c) and the portal
(services/nuxel-portal) read, and it is the only place that is allowed to say
WHAT A GRANT ACTUALLY ENFORCES.

Truth rules implemented here (they are not documentation, they are code):

  * Every grant record carries the enforcement mechanism, the attacker
    privilege class it holds against, and a limitation string copied from the
    canonical capability registry (capabilities.json). A capability whose
    kernel mechanism does not exist on the target (e.g. Landlock on Linux
    4.14) is stored with enforceable="no"/"partial" - never "yes".
  * Unsupported manifest tokens (sms_send_raw, landlock, ptrace, ...) are
    reported as unsupported, never silently granted.
  * Nothing here claims enforcement against root. Every claim is scoped to the
    unprivileged-app privilege class.

Store layout (default /var/lib/nuxel/permissions, override NUXEL_PERMISSIONS_DIR):

    <store>/<app-id>.json            flat grants dict, portal-compatible
    <store>/state/<app-id>.json      reviewable extended record (declared vs
                                     granted, enforcement snapshot, hashes)
    <store>/state/defaults.json      fail-closed policy
    <store>/state/audit.log          append-only JSONL audit trail
    <store>/state/enforce/<app>.json generated sandbox profile overlay

The flat file is intentionally kept exactly in the shape
services/nuxel-portal/src/portal.py:PermissionStore writes, so the portal and
this tool are always looking at the same bytes.

Usage:
    nuxel-permd.py list [--json]
    nuxel-permd.py show <app-id> [--json]
    nuxel-permd.py grant <app-id> <capability> [--duration always|session|once]
    nuxel-permd.py revoke <app-id> <capability>
    nuxel-permd.py revoke-all <app-id>
    nuxel-permd.py check <app-id> <capability>
    nuxel-permd.py sync [--root DIR] [--dry-run]
    nuxel-permd.py review [--root DIR] [--json] [--strict]
    nuxel-permd.py enforcement-matrix [--json]
    nuxel-permd.py kernel-facts [--json] [--config PATH]
    nuxel-permd.py enforce-plan <app-id> [--out FILE] [--root DIR]
    nuxel-permd.py serve [--port N] [--bind ADDR]
    nuxel-permd.py self-test
"""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import platform
import re
import socket
import sys
import time

VERSION = "1.0.0"
SCHEMA_VERSION = 2

DEFAULT_STORE = os.environ.get("NUXEL_PERMISSIONS_DIR", "/var/lib/nuxel/permissions")
DEFAULT_ROOT = os.environ.get("NUXEL_ROOT", os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

DEFAULT_CAP_REGISTRY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "capabilities.json")

# Exit codes (stable, used by tools and tests)
EXIT_OK = 0
EXIT_DENIED = 1
EXIT_USAGE = 2
EXIT_UNSUPPORTED = 3
EXIT_STORE = 4
EXIT_UNSAFE = 5

VALID_DURATIONS = ("once", "session", "always")

# Tokens that must never be accepted as a grantable capability.
HARD_UNSUPPORTED = (
    "sms_send_raw",
    "modem:raw",
    "kernel:module",
    "landlock",
    "ptrace",
    "selinux",
    "lockdown",
    "root",
    "sudo",
)


def _now():
    return time.time()


def _sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except (IOError, OSError):
        return None
    return h.hexdigest()


def app_id_to_safe(app_id):
    """Mirror portal.py:PermissionStore._app_path sanitisation exactly."""
    return app_id.replace("/", "_").replace("..", "_")


class Registry(object):
    """Canonical capability registry (capabilities.json)."""

    def __init__(self, path=None):
        self.path = path or DEFAULT_CAP_REGISTRY
        self.raw = {}
        self.caps = {}
        self.mechanisms = {}
        self.trusted_owner = "root"
        self.exempt_from_grant = ()
        self.reload()

    def reload(self):
        with open(self.path, "r") as fh:
            self.raw = json.load(fh)
        self.mechanisms = self.raw.get("mechanisms", {})
        self.caps = {}
        for cap in self.raw.get("capabilities", []):
            self.caps[cap["id"]] = cap
        self.aliases = {}
        for cap in self.raw.get("capabilities", []):
            for alias in cap.get("aliases", []) or []:
                self.aliases[alias] = cap["id"]
            if cap.get("portal_type"):
                self.aliases.setdefault(cap["portal_type"], cap["id"])
        self.token_map = dict(self.raw.get("manifest_tokens", {}))
        self.unsupported = set(self.raw.get("unsupported_manifest_tokens", []))
        self.unsupported.update(HARD_UNSUPPORTED)
        # Apps that must never be blocked from their own data even if a grant is
        # absent (they are the stores themselves).
        self.exempt_from_grant = tuple(self.raw.get("grant_exempt_apps", ()))

    def resolve(self, token):
        """Resolve a manifest/portal token to a canonical capability id.

        Returns (capability_id or None, unsupported_reason or None).
        """
        if not token:
            return None, "empty capability token"
        tok = token.strip()
        if tok in self.unsupported:
            return None, "unsupported capability token: %s" % tok
        if tok in self.caps:
            return tok, None
        # Explicit namespace map first: 'phone:status' is phone_status, NOT the
        # 'phone' alias of 'call'. Getting this wrong would silently widen a
        # telephony grant into a status read.
        mapped = self.token_map.get(tok)
        if mapped and mapped in self.caps:
            return mapped, None
        base = tok.split(":", 1)[0]
        if base in self.unsupported:
            return None, "unsupported capability token: %s" % tok
        if tok in self.aliases:
            return self.aliases[tok], None
        if base in self.caps:
            return base, None
        if base in self.aliases:
            return self.aliases[base], None
        return None, "unknown capability token: %s" % tok

    def capability(self, cap_id):
        return self.caps.get(cap_id)

    def enforcement_of(self, cap_id):
        cap = self.caps.get(cap_id)
        if not cap:
            return {
                "id": cap_id,
                "mechanisms": ["none"],
                "enforceable": "no",
                "enforces_against": "nobody",
                "limitation": "not in the canonical capability registry",
                "verdict": "NOT_SUPPORTED_ON_DEVICE",
            }
        mech = [self.mechanisms.get(m, {"title": m}) for m in cap.get("mechanisms", [])]
        return {
            "id": cap["id"],
            "title": cap.get("title", cap["id"]),
            "portal_type": cap.get("portal_type"),
            "risk": cap.get("risk", "medium"),
            "group": cap.get("group", "other"),
            "mechanisms": cap.get("mechanisms", []),
            "mechanism_titles": [m.get("title", m) for m in mech],
            "enforceable": cap.get("enforceable", "no"),
            "enforces_against": cap.get("enforces_against", "nobody"),
            "limitation": cap.get("limitation", ""),
            "verdict": cap.get("verdict", "IMPLEMENTED_NOT_DEPLOYED"),
            "test": cap.get("test", ""),
            "grant_required": cap.get("grant_required", True),
        }

    def token_map_for_display(self):
        return dict(self.token_map)

    def matrix(self):
        out = []
        for cap_id in sorted(self.caps):
            out.append(self.enforcement_of(cap_id))
        return out


class Store(object):
    """Durable, reviewable, portal-compatible grant store."""

    def __init__(self, directory=None, registry=None):
        self.dir = directory or DEFAULT_STORE
        self.state_dir = os.path.join(self.dir, "state")
        self.enforce_dir = os.path.join(self.state_dir, "enforce")
        self.registry = registry or Registry()

    # ---- paths -----------------------------------------------------------
    def grants_path(self, app_id):
        return os.path.join(self.dir, app_id_to_safe(app_id) + ".json")

    def state_path(self, app_id):
        return os.path.join(self.state_dir, app_id_to_safe(app_id) + ".json")

    def audit_path(self):
        return os.path.join(self.state_dir, "audit.log")

    def defaults_path(self):
        return os.path.join(self.state_dir, "defaults.json")

    def ensure_dirs(self):
        for path in (self.dir, self.state_dir, self.enforce_dir):
            try:
                os.makedirs(path)
            except OSError:
                if not os.path.isdir(path):
                    raise

    # ---- raw grants (portal-compatible) ----------------------------------
    def get_grants(self, app_id):
        path = self.grants_path(app_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as fh:
                data = json.load(fh)
        except (ValueError, IOError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def write_grants(self, app_id, grants):
        self.ensure_dirs()
        path = self.grants_path(app_id)
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(grants, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def is_granted(self, app_id, capability, consume_once=False):
        cap_id, why = self.registry.resolve(capability)
        if cap_id is None:
            return False
        grants = self.get_grants(app_id)
        grant = grants.get(cap_id)
        if not isinstance(grant, dict):
            return False
        if grant.get("duration") == "once" and consume_once:
            self.revoke(app_id, cap_id, reason="once-consumed")
            return True
        return True

    # ---- state (reviewable extended record) ------------------------------
    def get_state(self, app_id):
        path = self.state_path(app_id)
        if not os.path.exists(path):
            return {"schema_version": SCHEMA_VERSION, "app_id": app_id,
                    "declared": [], "unsupported": [], "grants": {},
                    "enforcement": {}, "updated": None}
        try:
            with open(path, "r") as fh:
                return json.load(fh)
        except (ValueError, IOError, OSError):
            return {"schema_version": SCHEMA_VERSION, "app_id": app_id,
                    "declared": [], "unsupported": [], "grants": {},
                    "enforcement": {}, "updated": None}

    def write_state(self, app_id, state):
        self.ensure_dirs()
        state["schema_version"] = SCHEMA_VERSION
        state["app_id"] = app_id
        state["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        state["enforcement"] = dict(
            (g, self.registry.enforcement_of(g))
            for g in sorted(self.get_grants(app_id))
        )
        path = self.state_path(app_id)
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)

    def audit(self, action, app_id, capability=None, **extra):
        self.ensure_dirs()
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "epoch": _now(),
            "action": action,
            "app_id": app_id,
            "capability": capability,
            "actor": os.environ.get("NUXEL_AUDIT_ACTOR", "nuxel-permd"),
            "euid": os.geteuid() if hasattr(os, "geteuid") else None,
        }
        entry.update(extra)
        with open(self.audit_path(), "a") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")

    # ---- mutations -------------------------------------------------------
    def grant(self, app_id, capability, duration="always", evidence=None):
        cap_id, why = self.registry.resolve(capability)
        if cap_id is None:
            raise UnsupportedCapability(why)
        if duration not in VALID_DURATIONS:
            raise ValueError("duration must be one of %s" % (VALID_DURATIONS,))
        enforce = self.registry.enforcement_of(cap_id)
        grants = self.get_grants(app_id)
        record = {
            "granted_at": _now(),
            "duration": duration,
            "portal_type": enforce.get("portal_type") or cap_id,
            # the honest part: the grant stores what it will actually do
            "mechanisms": enforce["mechanisms"],
            "enforceable": enforce["enforceable"],
            "enforces_against": enforce["enforces_against"],
            "limitation": enforce["limitation"],
            "verdict": enforce["verdict"],
        }
        if evidence:
            record["evidence"] = evidence
        grants[cap_id] = record
        self.write_grants(app_id, grants)
        state = self.get_state(app_id)
        state.setdefault("grants", {})[cap_id] = record
        self.write_state(app_id, state)
        self.audit("grant", app_id, cap_id, duration=duration,
                   enforceable=enforce["enforceable"],
                   enforces_against=enforce["enforces_against"])
        return record

    def revoke(self, app_id, capability, reason="user"):
        cap_id, why = self.registry.resolve(capability)
        if cap_id is None:
            raise UnsupportedCapability(why)
        grants = self.get_grants(app_id)
        existed = cap_id in grants
        grants.pop(cap_id, None)
        self.write_grants(app_id, grants)
        state = self.get_state(app_id)
        state.setdefault("grants", {}).pop(cap_id, None)
        self.write_state(app_id, state)
        self.audit("revoke", app_id, cap_id, reason=reason, existed=existed)
        return existed

    def revoke_all(self, app_id):
        grants = self.get_grants(app_id)
        path = self.grants_path(app_id)
        if os.path.exists(path):
            os.remove(path)
        state = self.get_state(app_id)
        state["grants"] = {}
        self.write_state(app_id, state)
        self.audit("revoke-all", app_id, None, revoked=sorted(grants))
        return sorted(grants)


class UnsupportedCapability(Exception):
    pass


class TestRecord(object):
    """A single audit finding with a scope and a severity."""

    def __init__(self, code, severity, app_id, detail, capability=None):
        self.code = code
        self.severity = severity      # "error" | "warning" | "info"
        self.app_id = app_id
        self.detail = detail
        self.capability = capability

    def as_dict(self):
        return {
            "code": self.code,
            "severity": self.severity,
            "app_id": self.app_id,
            "capability": self.capability,
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# Discovery: declared capabilities come from real files, never from assumptions
# ---------------------------------------------------------------------------

PWA_MANIFEST_GLOBS = (
    "pwa/*/manifest.json",
    "pwa/*/*/manifest.json",
)

SHELL_APP_DIRS = (
    "shell/nuxel-shell",
)

SANDBOX_PROFILE_DIR = "shell/nuxel-shell/nuxel-sandbox/profiles"


def _rel(root, path):
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def discover(root, registry):
    """Return {app_id: {sources: [...], declared: [...], unsupported: [...]}}."""
    import glob as _glob

    found = {}

    def slot(app_id):
        if app_id not in found:
            found[app_id] = {"app_id": app_id, "sources": [], "declared": [],
                             "unsupported": [], "declared_detail": []}
        return found[app_id]

    # 1. PWA manifests (pwa/**/manifest.json with a "nuxel" block)
    for pattern in PWA_MANIFEST_GLOBS:
        for path in sorted(_glob.glob(os.path.join(root, pattern))):
            try:
                with open(path, "r") as fh:
                    manifest = json.load(fh)
            except (ValueError, IOError, OSError):
                continue
            nuxel = manifest.get("nuxel")
            if not isinstance(nuxel, dict):
                continue
            tokens = nuxel.get("capabilities") or []
            # Derive a stable app id: prefer an explicit id, else the directory.
            app_dir = os.path.dirname(path)
            app_id = nuxel.get("app_id") or os.path.basename(app_dir)
            if os.path.basename(root) and app_dir == os.path.join(root, "pwa"):
                app_id = "nuxel-home"
            rec = slot(app_id)
            rec["sources"].append({"kind": "pwa-manifest", "path": _rel(root, path),
                                   "sha256": _sha256_file(path),
                                   "app_type": nuxel.get("app_type")})
            rec["declared_detail"].append({"kind": "pwa-manifest",
                                           "path": _rel(root, path),
                                           "tokens": list(tokens)})
            for token in tokens:
                cap_id, why = registry.resolve(token)
                if cap_id is None:
                    rec["unsupported"].append({"token": token, "reason": why,
                                               "path": _rel(root, path)})
                elif cap_id not in rec["declared"]:
                    rec["declared"].append(cap_id)

    # 2. Sandbox profiles (shell/nuxel-shell/nuxel-sandbox/profiles/*.json)
    prof_dir = os.path.join(root, SANDBOX_PROFILE_DIR)
    if os.path.isdir(prof_dir):
        for name in sorted(os.listdir(prof_dir)):
            if not name.endswith(".json") or name == "default.json":
                continue
            path = os.path.join(prof_dir, name)
            try:
                with open(path, "r") as fh:
                    prof = json.load(fh)
            except (ValueError, IOError, OSError):
                continue
            app_id = prof.get("app_id") or name[:-5]
            rec = slot(app_id)
            rec["sources"].append({"kind": "sandbox-profile",
                                   "path": _rel(root, path),
                                   "sha256": _sha256_file(path),
                                   "network_class": prof.get("network_class")})
            tokens = prof.get("capabilities") or []
            rec["declared_detail"].append({"kind": "sandbox-profile",
                                           "path": _rel(root, path),
                                           "tokens": list(tokens)})
            for token in tokens:
                cap_id, why = registry.resolve(token)
                if cap_id is None:
                    rec["unsupported"].append({"token": token, "reason": why,
                                               "path": _rel(root, path)})
                elif cap_id not in rec["declared"]:
                    rec["declared"].append(cap_id)

    # 3. App registry (configs/nuxel/app-registry) as an authoritative cross-check
    reg_path = os.path.join(root, "configs/nuxel/app-registry/app_registry.json")
    if os.path.isfile(reg_path):
        try:
            with open(reg_path, "r") as fh:
                reg = json.load(fh)
            for app in reg.get("apps", []):
                app_id = app.get("app_id")
                if not app_id:
                    continue
                rec = slot(app_id)
                rec["sources"].append({"kind": "app-registry",
                                       "path": _rel(root, reg_path),
                                       "sha256": _sha256_file(reg_path),
                                       "network_class": app.get("network_class"),
                                       "cgroup_name": app.get("cgroup_name")})
                tokens = app.get("capabilities") or []
                rec["declared_detail"].append({"kind": "app-registry",
                                               "path": _rel(root, reg_path),
                                               "tokens": list(tokens)})
                for token in tokens:
                    cap_id, why = registry.resolve(token)
                    if cap_id is None:
                        rec["unsupported"].append({"token": token, "reason": why,
                                                   "path": _rel(root, reg_path)})
                    elif cap_id not in rec["declared"]:
                        rec["declared"].append(cap_id)
        except (ValueError, IOError, OSError):
            pass

    # 4. Native shell apps (directories) - presence only, no capabilities.
    shell_dir = os.path.join(root, "shell/nuxel-shell")
    if os.path.isdir(shell_dir):
        for name in sorted(os.listdir(shell_dir)):
            if not name.startswith("nuxel-"):
                continue
            if not os.path.isdir(os.path.join(shell_dir, name)):
                continue
            rec = slot(name)
            rec["sources"].append({"kind": "shell-app-dir",
                                   "path": _rel(root, os.path.join(shell_dir, name))})

    for app_id in found:
        found[app_id]["declared"] = sorted(found[app_id]["declared"])
    return found


# ---------------------------------------------------------------------------
# Kernel truth: what this kernel can actually enforce
# ---------------------------------------------------------------------------

KERNEL_FEATURE_REQUIREMENTS = {
    "landlock": (5, 13, "Landlock LSM (per-app filesystem/path confinement)"),
    "lockdown": (4, 17, "Kernel lockdown LSM"),
    "nft_socket_cgroupv2": (5, 13, "nftables 'socket cgroupv2' per-cgroup match"),
    "fs_verity": (5, 4, "fs-verity file authenticity"),
    "init_on_free": (5, 3, "init_on_alloc/init_on_free memory zeroing"),
    "stackleak": (4, 20, "STACKLEAK stack erasure"),
    "bpf_lsm": (5, 7, "BPF LSM hooks (systemd bpf-restrict-fs)"),
    "cfi": (5, 13, "Kernel control-flow integrity (arm64)"),
    "shadow_call_stack": (5, 7, "arm64 Shadow Call Stack"),
    "arm64_bti": (5, 9, "arm64 Branch Target Identification user/kernel"),
    "memfd_secret": (5, 14, "memfd_secret"),
}


def parse_kernel_release(text):
    m = re.match(r"\s*(\d+)\.(\d+)", text or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def _read_first(paths, reader=None):
    for path in paths:
        try:
            with open(path, "r") as fh:
                data = fh.read()
        except (IOError, OSError):
            continue
        if reader:
            data = reader(data)
        return path, data
    return None, None


def _sysctl(path):
    _, val = _read_first([path])
    return val.strip() if val else None


def kernel_facts(fixture=None, config_path=None):
    """Collect measured kernel facts. Never guesses: unknown is a value."""
    facts = {
        "source": "live",
        "release": None,
        "release_tuple": None,
        "arch": None,
        "landlock_abi": None,
        "seccomp_actions_avail": None,
        "lsm_list": None,
        "apparmor_enabled": "unknown",
        "selinux_enabled": "unknown",
        "yama_ptrace_scope": None,
        "userns_max": None,
        "bpf_unprivileged_disabled": None,
        "cgroup2_controllers": None,
        "cgroup_v1_net_cls": "unknown",
        "auditd_present": None,
        "kernel_config": {},
        "kernel_config_source": None,
        "features": {},
        "mechanism_availability": {},
        "notes": [],
    }

    if fixture:
        with open(fixture, "r") as fh:
            fx = json.load(fh)
        facts["source"] = "fixture:%s" % fixture
        facts["release"] = fx.get("release")
        facts["arch"] = fx.get("arch")
        facts["landlock_abi"] = fx.get("landlock_abi")
        facts["seccomp_actions_avail"] = fx.get("seccomp_actions_avail")
        facts["lsm_list"] = fx.get("lsm_list")
        facts["yama_ptrace_scope"] = fx.get("yama_ptrace_scope")
        facts["userns_max"] = fx.get("userns_max")
        facts["bpf_unprivileged_disabled"] = fx.get("bpf_unprivileged_disabled")
        facts["cgroup2_controllers"] = fx.get("cgroup2_controllers")
        facts["cgroup_v1_net_cls"] = fx.get("cgroup_v1_net_cls", "unknown")
        facts["auditd_present"] = fx.get("auditd_present")
        facts["kernel_config"] = fx.get("kernel_config", {})
        facts["kernel_config_source"] = fx.get("kernel_config_source",
                                               "fixture")
        facts["notes"] = list(fx.get("notes", []))
    else:
        facts["release"] = platform.release()
        facts["arch"] = platform.machine()
        _, abi = _read_first(["/proc/sys/kernel/landlock/abi_version"])
        facts["landlock_abi"] = abi.strip() if abi else None
        _, avail = _read_first(["/proc/sys/kernel/seccomp/actions_avail"])
        facts["seccomp_actions_avail"] = avail.strip() if avail else None
        _, lsm = _read_first(["/sys/kernel/security/lsm"])
        facts["lsm_list"] = lsm.strip() if lsm else None
        facts["yama_ptrace_scope"] = _sysctl("/proc/sys/kernel/yama/ptrace_scope")
        facts["userns_max"] = _sysctl("/proc/sys/user/max_user_namespaces")
        facts["bpf_unprivileged_disabled"] = _sysctl(
            "/proc/sys/kernel/unprivileged_bpf_disabled")
        _, cg = _read_first(["/sys/fs/cgroup/cgroup.controllers"])
        facts["cgroup2_controllers"] = cg.strip() if cg else None
        if os.path.isdir("/sys/fs/cgroup/net_cls"):
            facts["cgroup_v1_net_cls"] = "mounted"
        elif os.path.isdir("/sys/fs/cgroup/net_cls,net_prio"):
            facts["cgroup_v1_net_cls"] = "mounted"
        else:
            facts["cgroup_v1_net_cls"] = "absent"

        # Kernel config: /proc/config.gz (measured on the handset), then
        # /boot/config-$(uname -r), then the vendor tree defconfig fallback.
        cfg = {}
        cfg_src = None
        if config_path:
            cfg_src, text = _read_first([config_path], None)
            if text:
                cfg = _parse_kconfig(text)
        if not cfg:
            for path in ("/proc/config.gz",):
                if os.path.exists(path):
                    try:
                        import gzip
                        with gzip.open(path, "rt", errors="replace") as fh:
                            cfg = _parse_kconfig(fh.read())
                        cfg_src = path
                    except (IOError, OSError):
                        pass
                    break
        if not cfg:
            cfg_src, text = _read_first(["/boot/config-%s" % (facts["release"] or ""),
                                         "/lib/modules/%s/config" % (facts["release"] or "")])
            if text:
                cfg = _parse_kconfig(text)
        facts["kernel_config"] = cfg
        facts["kernel_config_source"] = cfg_src
        if not cfg:
            facts["notes"].append(
                "kernel config not readable; CONFIG_* dependent claims are "
                "UNVERIFIED on this host (run nuxel-security-audit.sh on the device)")
        if facts["lsm_list"] is None:
            facts["notes"].append(
                "/sys/kernel/security/lsm not readable; LSM availability is UNVERIFIED")

    # LSM conclusions
    lsm_list = facts["lsm_list"]
    if lsm_list:
        lsms = [x.strip() for x in lsm_list.split(",") if x.strip()]
        facts["lsm_list"] = lsms
        facts["apparmor_enabled"] = "yes" if "apparmor" in lsms else "no"
        facts["selinux_enabled"] = "yes" if "selinux" in lsms else "no"
    if facts["kernel_config"].get("CONFIG_SECURITY_APPARMOR") == "y":
        facts["apparmor_enabled"] = ("yes" if facts["apparmor_enabled"] in ("yes", "unknown")
                                     else facts["apparmor_enabled"])
    if facts["kernel_config"].get("CONFIG_SECURITY_SELINUX") == "y":
        facts["selinux_enabled"] = ("yes" if facts["selinux_enabled"] in ("yes", "unknown")
                                    else facts["selinux_enabled"])
    if os.path.isdir("/sys/kernel/security/apparmor") and not fixture:
        facts["apparmor_enabled"] = "yes"

    rt = parse_kernel_release(facts["release"] or "")
    facts["release_tuple"] = list(rt) if rt else None

    # Mainline version requirements: deterministic, no guessing needed
    for feature, (maj, minr, desc) in sorted(KERNEL_FEATURE_REQUIREMENTS.items()):
        entry = {"description": desc, "requires": "%d.%d" % (maj, minr)}
        if rt is None:
            entry["available"] = "unknown"
            entry["reason"] = "kernel release unparsable"
        elif rt >= (maj, minr):
            entry["available"] = "possible"
            entry["reason"] = "mainline requirement met; confirm with CONFIG_/sysfs"
        else:
            entry["available"] = "no"
            entry["reason"] = ("requires >= %d.%d; this kernel is %s"
                               % (maj, minr, facts["release"]))
        facts["features"][feature] = entry

    # Landlock is the one feature we can read directly from sysfs
    if facts["landlock_abi"]:
        facts["features"]["landlock"]["available"] = "yes"
        facts["features"]["landlock"]["reason"] = (
            "/proc/sys/kernel/landlock/abi_version = %s" % facts["landlock_abi"])
    elif fixture or facts["source"] == "live":
        if rt is not None and rt < (5, 13):
            facts["features"]["landlock"]["available"] = "no"
            facts["features"]["landlock"]["reason"] = (
                "no /proc/sys/kernel/landlock/abi_version and kernel < 5.13")

    # seccomp / cgroup / netfilter mechanisms
    seccomp_ok = False
    if facts["seccomp_actions_avail"]:
        seccomp_ok = True
    elif facts["kernel_config"].get("CONFIG_SECCOMP_FILTER") == "y":
        seccomp_ok = True
    elif fixture and fx_has(fixture, "seccomp_actions_avail"):
        seccomp_ok = True
    facts["mechanism_availability"] = {
        "seccomp_bpf": "yes" if seccomp_ok else ("no" if facts["kernel_config"] else "unknown"),
        "namespaces": ("yes" if facts["kernel_config"].get("CONFIG_NAMESPACES") == "y"
                       else "unknown"),
        "user_namespaces": (
            "yes" if (facts["userns_max"] and facts["userns_max"] not in ("0",))
            else ("no" if facts["userns_max"] else "unknown")),
        "cgroup_v2": ("yes" if facts["cgroup2_controllers"] else "unknown"),
        "cgroup_v1_net_cls": facts["cgroup_v1_net_cls"],
        "nftables": ("yes" if os.path.exists("/sys/module/nf_tables")
                     or os.path.exists("/proc/net/netfilter") else "unknown"),
        "nft_socket_cgroupv2": facts["features"]["nft_socket_cgroupv2"]["available"],
        "landlock": facts["features"]["landlock"]["available"],
        "apparmor": facts["apparmor_enabled"],
        "audit": ("yes" if facts["auditd_present"] else "unknown"),
    }
    return facts


def fx_has(fixture, key):
    try:
        with open(fixture, "r") as fh:
            return key in json.load(fh)
    except Exception:
        return False


def _parse_kconfig(text):
    cfg = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#!"):
            continue
        if line.startswith("# "):
            # "# CONFIG_FOO is not set"
            if " is not set" in line:
                key = line[2:].split(" is not set")[0].strip()
                if key.startswith("CONFIG_"):
                    cfg[key] = "n"
            continue
        if line.startswith("CONFIG_") and "=" in line:
            key, val = line.split("=", 1)
            cfg[key.strip()] = val.strip()
    return cfg


def downgrade_for_kernel(enforcement, facts):
    """Cap an enforcement claim by what the kernel on THIS host can do."""
    mechs = enforcement.get("mechanisms", [])
    avail = facts.get("mechanism_availability", {})
    missing = []
    for m in mechs:
        if m == "sandbox-profile":
            if avail.get("landlock") == "no":
                missing.append("Landlock (filesystem confinement) unavailable on kernel %s"
                               % facts.get("release"))
            if avail.get("nft_socket_cgroupv2") == "no":
                missing.append("nftables socket cgroupv2 match unavailable on kernel %s "
                               "(cgroup v1 net_cls classid is used instead)"
                               % facts.get("release"))
        if m == "apparmor" and avail.get("apparmor") == "no":
            missing.append("AppArmor LSM not present in /sys/kernel/security/lsm")
    out = dict(enforcement)
    out["kernel_missing"] = sorted(set(missing))
    return out


# ---------------------------------------------------------------------------
# Review: declared vs granted vs actually-enforceable
# ---------------------------------------------------------------------------

def review(root, store, registry, facts=None, require_granted=False):
    facts = facts or kernel_facts()
    discovered = discover(root, registry)
    findings = []
    apps = []

    for app_id in sorted(discovered):
        rec = discovered[app_id]
        grants = store.get_grants(app_id)
        declared = rec["declared"]
        granted = sorted(grants)

        for unsup in rec["unsupported"]:
            # Two different things, two different severities:
            #   * a token Nuxel deliberately refuses (raw modem, kernel module,
            #     landlock, ptrace, root/sudo) -> ERROR, it can never be granted
            #   * a token that is not registered yet -> WARNING, it is still
            #     fail-closed (no grant can exist), but the app author must
            #     register it in capabilities.json so its enforcement truth is
            #     reviewable instead of unknown
            refused = unsup["reason"].startswith("unsupported")
            findings.append(TestRecord(
                "unsupported_capability" if refused else "unregistered_capability",
                "error" if refused else "warning", app_id,
                "%s declares %r: %s"
                % (unsup["path"], unsup["token"], unsup["reason"]),
                capability=unsup["token"]))

        for cap_id in declared:
            enf_pre = registry.enforcement_of(cap_id)
            if not enf_pre.get("grant_required", True):
                # Not a protected resource (audio output, clock read): there is
                # nothing to grant, so nothing to report.
                continue
            if cap_id not in grants:
                sev = "error" if require_granted else "info"
                enf = registry.enforcement_of(cap_id)
                if enf["verdict"] in ("NOT_SUPPORTED_ON_DEVICE",):
                    sev = "error" if require_granted else "warning"
                    detail = ("%s is declared but cannot be enforced on this device: %s"
                              % (cap_id, enf["limitation"]))
                else:
                    detail = ("%s is declared with no stored grant "
                              "(fail-closed: the portal refuses it)" % cap_id)
                findings.append(TestRecord("declared_not_granted", sev, app_id,
                                           detail, capability=cap_id))

        for cap_id, grant in sorted(grants.items()):
            enf = registry.enforcement_of(cap_id)
            if cap_id not in declared:
                findings.append(TestRecord(
                    "grant_not_declared", "warning", app_id,
                    "grant exists for %s but no manifest/profile declares it "
                    "(orphan grant)" % cap_id, capability=cap_id))
            if grant.get("enforceable") == "yes" and enf["enforceable"] != "yes":
                findings.append(TestRecord(
                    "enforcement_claim_mismatch", "error", app_id,
                    "stored grant claims full enforcement for %s but the "
                    "registry says %r - a cosmetic switch that lies about "
                    "enforcement" % (cap_id, enf["enforceable"]),
                    capability=cap_id))
            if not grant.get("limitation"):
                findings.append(TestRecord(
                    "missing_limitation", "error", app_id,
                    "stored grant for %s carries no limitation statement; "
                    "enforcement claims must be reviewable" % cap_id,
                    capability=cap_id))
            if (enf.get("grant_required", True)
                    and enf["enforces_against"] == "nobody"
                    and grant.get("duration") == "always"):
                findings.append(TestRecord(
                    "ineffective_grant", "warning", app_id,
                    "%s is stored as an always-grant but nothing enforces it"
                    % cap_id, capability=cap_id))
            if grant.get("duration") == "session":
                findings.append(TestRecord(
                    "stale_session_grant", "warning", app_id,
                    "%s has a session grant persisted on disk; session grants "
                    "must be dropped at boot" % cap_id, capability=cap_id))

        # drift between the app registry and the sandbox profile
        kinds = {}
        for detail in rec["declared_detail"]:
            kinds.setdefault(detail["kind"], []).append(sorted(detail["tokens"]))
        if "app-registry" in kinds and "sandbox-profile" in kinds:
            reg_tokens = set(_canon_tokens(kinds["app-registry"][0], registry))
            prof_tokens = set(_canon_tokens(kinds["sandbox-profile"][0], registry))
            # The registry lists what an app MAY request; the sandbox profile
            # lists what it is actually launched with. Granting less is the
            # expected (fail-closed) direction and is not an error. Granting
            # something the registry never declared IS an error - that is
            # privilege widening through profile drift.
            widened = prof_tokens - reg_tokens
            narrower = reg_tokens - prof_tokens
            if widened:
                findings.append(TestRecord(
                    "declaration_drift", "error", app_id,
                    "sandbox profile grants %s which the app registry does not "
                    "declare for this app" % sorted(widened)))
            if narrower:
                findings.append(TestRecord(
                    "declared_not_launched", "info", app_id,
                    "%s is declared in the app registry but not in the sandbox "
                    "profile (fail-closed; requires an explicit grant)"
                    % sorted(narrower)))

        enforcement = {}
        for cap_id in sorted(set(declared) | set(granted)):
            enf = downgrade_for_kernel(registry.enforcement_of(cap_id), facts)
            enf["granted"] = cap_id in grants
            enforcement[cap_id] = enf
        apps.append({
            "app_id": app_id,
            "declared": declared,
            "granted": granted,
            "unsupported": rec["unsupported"],
            "sources": rec["sources"],
            "enforcement": enforcement,
        })

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    return {
        "root": root,
        "kernel": {"release": facts.get("release"),
                   "source": facts.get("source"),
                   "apparmor": facts.get("apparmor_enabled"),
                   "landlock": facts.get("mechanism_availability", {}).get("landlock")},
        "apps": apps,
        "findings": [f.as_dict() for f in findings],
        "summary": {
            "apps": len(apps),
            "declared_capabilities": sum(len(a["declared"]) for a in apps),
            "grants": sum(len(a["granted"]) for a in apps),
            "errors": len(errors),
            "warnings": len(warnings),
            "requires_granted": require_granted,
            "verdict": ("OK" if not errors else "MISMATCH"),
        },
    }


def _canon_tokens(tokens, registry):
    out = []
    for token in tokens:
        cap_id, _why = registry.resolve(token)
        out.append(cap_id or token)
    return out


def consistent_mismatches(report):
    """Return only the hard mismatches (errors) from a review report."""
    return [f for f in report["findings"] if f["severity"] == "error"]


# ---------------------------------------------------------------------------
# Enforcement plan (what the sandbox/nftables should actually receive)
# ---------------------------------------------------------------------------

CAPABILITY_DEVICES = {
    "camera": ["/dev/video0", "/dev/video1"],
    "microphone": ["/dev/snd/"],
    "network": ["/dev/net/tun"],
    "usb": ["/dev/bus/usb/"],
}


def _classid_for(app_id, registry_app=None):
    if registry_app and registry_app.get("cgroup_classid"):
        return int(registry_app["cgroup_classid"])
    import zlib
    minor = (zlib.crc32(app_id.encode("utf-8")) % 0xFFFD) + 1
    return 0x01030000 | minor


def enforce_plan(root, store, registry, app_id, facts=None):
    """Build the concrete enforcement overlay for one app from its grants."""
    facts = facts or kernel_facts()
    discovered = discover(root, registry)
    rec = discovered.get(app_id, {"declared": [], "unsupported": [], "sources": []})
    grants = store.get_grants(app_id)

    reg_app = None
    reg_path = os.path.join(root, "configs/nuxel/app-registry/app_registry.json")
    if os.path.isfile(reg_path):
        try:
            with open(reg_path, "r") as fh:
                for app in json.load(fh).get("apps", []):
                    if app.get("app_id") == app_id:
                        reg_app = app
                        break
        except (ValueError, IOError, OSError):
            pass

    classid = _classid_for(app_id, reg_app)
    network_granted = "network" in grants
    granted = sorted(grants)
    denied = [c for c in rec["declared"] if c not in grants]

    devices = []
    for cap_id in granted:
        devices.extend(CAPABILITY_DEVICES.get(cap_id, []))

    notes = []
    for cap_id in granted:
        enf = registry.enforcement_of(cap_id)
        if enf["enforceable"] != "yes":
            notes.append("%s: %s" % (cap_id, enf["limitation"]))
    avail = facts.get("mechanism_availability", {})
    if avail.get("landlock") == "no":
        notes.append("landlock_unavailable: no path-level filesystem confinement; "
                     "app data isolation relies on DAC (file ownership/mode)")
    if avail.get("nft_socket_cgroupv2") == "no":
        notes.append("nft_cgroupv2_unavailable: per-app network match uses "
                     "cgroup v1 net_cls classid 0x%08x (nft 'meta cgroup 0x%08x')"
                     % (classid, classid))
    if avail.get("apparmor") in ("unknown", "no"):
        notes.append("apparmor_%s: MAC labels must not be claimed as enforcing"
                     % avail.get("apparmor"))

    plan = {
        "schema_version": SCHEMA_VERSION,
        "app_id": app_id,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generated_by": "nuxel-permd %s" % VERSION,
        "kernel": {"release": facts.get("release"), "source": facts.get("source")},
        "grants": dict((c, {"duration": grants[c].get("duration"),
                            "enforceable": grants[c].get("enforceable"),
                            "enforces_against": grants[c].get("enforces_against")})
                       for c in granted),
        "denied": denied,
        "unsupported": rec["unsupported"],
        "sandbox": {
            "cgroup_name": "app-" + re.sub(r"[^a-z0-9-]+", "-",
                                           app_id.lower()).strip("-"),
            "cgroup_classid": classid,
            "cgroup_classid_hex": "0x%08x" % classid,
            "nft_match": "meta cgroup 0x%08x" % classid,
            "network_class": "public" if network_granted else "isolated",
            "capabilities": granted,
            "advisory_devices": sorted(set(devices)),
            "apparmor_profile": "nuxel-%s" % re.sub(r"[^a-z0-9-]+", "-",
                                                    app_id.lower()).strip("-"),
            "apparmor_available": avail.get("apparmor"),
        },
        "evidence": {
            "sources": rec["sources"],
        },
        "honest_notes": notes,
    }
    return plan


# ---------------------------------------------------------------------------
# HTTP API for the Settings app and the Privacy app (no GTK dependency)
# ---------------------------------------------------------------------------

def serve(store, registry, root, bind="127.0.0.1", port=8765,
          allow_insecure_writes=False):
    from http.server import BaseHTTPRequestHandler, HTTPServer

    token = os.environ.get("NUXEL_PERMD_TOKEN")

    class Handler(BaseHTTPRequestHandler):
        server_version = "nuxel-permd/" + VERSION

        def log_message(self, fmt, *args):
            sys.stderr.write("[nuxel-permd] %s\n" % (fmt % args))

        # -- helpers
        def _json(self, code, payload):
            body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _authorised(self):
            if allow_insecure_writes:
                return True
            if not token:
                return False
            hdr = self.headers.get("Authorization", "")
            return hdr == "Bearer " + token

        def _parts(self):
            path = self.path.split("?", 1)[0]
            return [p for p in path.split("/") if p]

        # -- routes
        def do_GET(self):
            parts = self._parts()
            if parts[:2] == ["api", "v1"]:
                rest = parts[2:]
            else:
                return self._json(404, {"error": "not found"})
            if rest == ["health"]:
                return self._json(200, {"status": "ok", "version": VERSION,
                                        "store": store.dir})
            if rest == ["enforcement", "matrix"]:
                return self._json(200, {"capabilities": registry.matrix(),
                                        "mechanisms": registry.mechanisms})
            if rest == ["kernel", "facts"]:
                return self._json(200, kernel_facts())
            if rest == ["review"]:
                return self._json(200, review(root, store, registry))
            if rest == ["apps"]:
                apps = []
                for app_id in sorted(discover(root, registry)):
                    grants = store.get_grants(app_id)
                    apps.append({"app_id": app_id,
                                 "grants": sorted(grants),
                                 "grant_count": len(grants)})
                return self._json(200, {"apps": apps})
            if len(rest) == 3 and rest[0] == "apps" and rest[2] == "permissions":
                app_id = rest[1]
                st = store.get_state(app_id)
                return self._json(200, {
                    "app_id": app_id,
                    "grants": store.get_grants(app_id),
                    "declared": st.get("declared", []),
                    "unsupported": st.get("unsupported", []),
                    "enforcement": st.get("enforcement", {}),
                })
            return self._json(404, {"error": "not found",
                                    "path": self.path})

        def do_POST(self):
            if not self._authorised():
                return self._json(403, {
                    "error": "writes are disabled or unauthorised",
                    "hint": "set NUXEL_PERMD_TOKEN and send "
                            "Authorization: Bearer <token>; "
                            "writes are never enabled implicitly",
                })
            parts = self._parts()
            rest = parts[2:] if parts[:2] == ["api", "v1"] else []
            try:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b"{}"
                payload = json.loads(body.decode("utf-8") or "{}")
            except (ValueError, UnicodeDecodeError):
                return self._json(400, {"error": "invalid JSON body"})

            if len(rest) == 5 and rest[0] == "apps" and rest[2] == "permissions":
                app_id, cap, action = rest[1], rest[3], rest[4]
                try:
                    if action == "grant":
                        rec = store.grant(app_id, cap,
                                          duration=payload.get("duration", "always"))
                        return self._json(200, {"granted": rec})
                    if action == "revoke":
                        existed = store.revoke(app_id, cap, reason="api")
                        return self._json(200, {"revoked": existed})
                except UnsupportedCapability as exc:
                    return self._json(422, {"error": str(exc)})
                except ValueError as exc:
                    return self._json(400, {"error": str(exc)})
                return self._json(404, {"error": "unknown action"})
            if len(rest) == 3 and rest[0] == "apps" and rest[2] == "revoke-all":
                rev = store.revoke_all(rest[1])
                return self._json(200, {"revoked": rev})
            return self._json(404, {"error": "not found", "path": self.path})

    httpd = HTTPServer((bind, port), Handler)
    sys.stderr.write(
        "[nuxel-permd] serving on http://%s:%d (store=%s, writes=%s)\n"
        % (bind, port, store.dir,
           "token" if (token and not allow_insecure_writes) else
           ("INSECURE-ALLOWED" if allow_insecure_writes else "disabled")))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return EXIT_OK


# ---------------------------------------------------------------------------
# sync: record declarations (and, on request, the shipped defaults)
# ---------------------------------------------------------------------------

def sync(root, store, registry, apply_shipped_defaults=False, dry_run=False):
    discovered = discover(root, registry)
    written = []
    granted = []
    for app_id in sorted(discovered):
        rec = discovered[app_id]
        state = store.get_state(app_id)
        state["declared"] = rec["declared"]
        state["unsupported"] = rec["unsupported"]
        state["declared_detail"] = rec["declared_detail"]
        state["sources"] = rec["sources"]
        if not dry_run:
            store.write_state(app_id, state)
        written.append(app_id)

    if apply_shipped_defaults:
        reg_path = os.path.join(root, "configs/nuxel/app-registry/app_registry.json")
        if os.path.isfile(reg_path):
            try:
                with open(reg_path, "r") as fh:
                    reg = json.load(fh)
            except (ValueError, IOError, OSError):
                reg = {"apps": []}
            for app in reg.get("apps", []):
                app_id = app.get("app_id")
                if not app_id:
                    continue
                for token in app.get("default_capabilities", []) or []:
                    cap_id, why = registry.resolve(token)
                    if cap_id is None:
                        continue
                    enf = registry.enforcement_of(cap_id)
                    if enf["verdict"] in ("NOT_SUPPORTED_ON_DEVICE",):
                        continue
                    if dry_run:
                        granted.append((app_id, cap_id, "dry-run"))
                        continue
                    store.grant(app_id, cap_id, duration="always",
                                evidence=["shipped default from "
                                          "configs/nuxel/app-registry/app_registry.json"])
                    granted.append((app_id, cap_id, "granted"))
    return {"recorded": written, "shipped_defaults": granted, "dry_run": dry_run}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print(obj, as_json=False):
    if as_json:
        print(json.dumps(obj, indent=2, sort_keys=True))
        return
    if isinstance(obj, list):
        for row in obj:
            print(row if isinstance(row, str) else json.dumps(row, sort_keys=True))
        return
    print(json.dumps(obj, indent=2, sort_keys=True))


def _cmd_list(args, store, registry, root):
    out = []
    for app_id in sorted(discover(root, registry)):
        grants = store.get_grants(app_id)
        out.append({"app_id": app_id, "grants": sorted(grants)})
    if args.json:
        _print(out, True)
        return EXIT_OK
    if not out:
        print("(no apps discovered under %s)" % root)
        return EXIT_OK
    width = max(len(a["app_id"]) for a in out)
    for a in out:
        print("%-*s  %d grant(s)%s" % (width, a["app_id"], len(a["grants"]),
                                       ("  " + ", ".join(a["grants"])) if a["grants"] else ""))
    return EXIT_OK


def _cmd_show(args, store, registry, root):
    app_id = args.app_id
    grants = store.get_grants(app_id)
    state = store.get_state(app_id)
    facts = kernel_facts(getattr(args, "fixture", None), getattr(args, "config", None))
    enforcement = {}
    for cap_id in sorted(set(list(grants) + state.get("declared", []))):
        enf = downgrade_for_kernel(registry.enforcement_of(cap_id), facts)
        enf["granted"] = cap_id in grants
        enforcement[cap_id] = enf
    payload = {"app_id": app_id, "store": store.dir, "grants": grants,
               "declared": state.get("declared", []),
               "unsupported": state.get("unsupported", []),
               "enforcement": enforcement,
               "kernel": {"release": facts.get("release"), "source": facts.get("source")}}
    if args.json:
        _print(payload, True)
        return EXIT_OK
    print("App:            %s" % app_id)
    print("Store:          %s" % store.dir)
    print("Kernel:         %s (%s)" % (facts.get("release"), facts.get("source")))
    print("Declared:       %s" % (", ".join(state.get("declared", [])) or "-"))
    print("Unsupported:    %s" % (", ".join(u["token"] for u in state.get("unsupported", [])) or "-"))
    print("")
    if not enforcement:
        print("(no capabilities declared or granted)")
        return EXIT_OK
    for cap_id in sorted(enforcement):
        enf = enforcement[cap_id]
        print("%s %s" % ("[granted]" if enf["granted"] else "[ denied]", cap_id))
        print("    mechanisms:       %s" % ", ".join(enf["mechanisms"]))
        print("    enforceable:      %s (against %s)" % (enf["enforceable"],
                                                          enf["enforces_against"]))
        print("    verdict:          %s" % enf["verdict"])
        print("    limitation:       %s" % enf["limitation"])
        if enf.get("kernel_missing"):
            for miss in enf["kernel_missing"]:
                print("    kernel_gap:       %s" % miss)
    return EXIT_OK


def _cmd_grant(args, store, registry, root):
    try:
        rec = store.grant(args.app_id, args.capability, duration=args.duration)
    except UnsupportedCapability as exc:
        print("REFUSED: %s" % exc, file=sys.stderr)
        return EXIT_UNSUPPORTED
    except ValueError as exc:
        print("usage: %s" % exc, file=sys.stderr)
        return EXIT_USAGE
    print("granted %s to %s (duration=%s)" % (args.capability, args.app_id, args.duration))
    print("  enforceable:     %s (against %s)" % (rec["enforceable"],
                                                  rec["enforces_against"]))
    print("  mechanisms:      %s" % ", ".join(rec["mechanisms"]))
    print("  limitation:      %s" % rec["limitation"])
    if rec["enforceable"] != "yes":
        print("  NOTE: this grant is NOT fully enforceable on the target kernel; "
              "it is a portal/policy gate, not a kernel boundary.")
    return EXIT_OK


def _cmd_revoke(args, store, registry, root):
    try:
        existed = store.revoke(args.app_id, args.capability)
    except UnsupportedCapability as exc:
        print("REFUSED: %s" % exc, file=sys.stderr)
        return EXIT_UNSUPPORTED
    print("%s %s from %s" % ("revoked" if existed else "no grant for",
                             args.capability, args.app_id))
    return EXIT_OK


def _cmd_revoke_all(args, store, registry, root):
    revoked = store.revoke_all(args.app_id)
    print("revoked %d capability grant(s) from %s: %s"
          % (len(revoked), args.app_id, ", ".join(revoked) or "-"))
    return EXIT_OK


def _cmd_check(args, store, registry, root):
    granted = store.is_granted(args.app_id, args.capability, consume_once=True)
    enf = registry.enforcement_of(registry.resolve(args.capability)[0] or args.capability)
    if granted:
        print("granted: %s %s (enforceable=%s against %s)"
              % (args.app_id, args.capability, enf["enforceable"],
                 enf["enforces_against"]))
        return EXIT_OK
    print("denied: %s %s" % (args.app_id, args.capability))
    return EXIT_DENIED


def _cmd_review(args, store, registry, root):
    facts = kernel_facts(getattr(args, "fixture", None), getattr(args, "config", None))
    report = review(root, store, registry, facts=facts,
                    require_granted=args.require_granted)
    if args.json:
        _print(report, True)
    else:
        print("Permission review of %s" % root)
        print("Kernel:  %s (%s) - apparmor=%s landlock=%s"
              % (report["kernel"]["release"], report["kernel"]["source"],
                 report["kernel"]["apparmor"], report["kernel"]["landlock"]))
        print("Apps:    %d, declared capabilities: %d, stored grants: %d"
              % (report["summary"]["apps"],
                 report["summary"]["declared_capabilities"],
                 report["summary"]["grants"]))
        print("")
        for finding in report["findings"]:
            print("%-7s %-24s %s: %s" % (finding["severity"].upper(),
                                         finding["code"], finding["app_id"],
                                         finding["detail"]))
        if not report["findings"]:
            print("(no findings)")
        print("")
        print("Verdict: %s (%d error(s), %d warning(s))"
              % (report["summary"]["verdict"], report["summary"]["errors"],
                 report["summary"]["warnings"]))
    return EXIT_OK if report["summary"]["errors"] == 0 else EXIT_DENIED


def _cmd_matrix(args, store, registry, root):
    facts = kernel_facts(getattr(args, "fixture", None), getattr(args, "config", None))
    rows = [downgrade_for_kernel(row, facts) for row in registry.matrix()]
    if args.json:
        _print({"kernel": {"release": facts.get("release"), "source": facts.get("source")},
                "capabilities": rows,
                "mechanism_availability": facts.get("mechanism_availability")}, True)
        return EXIT_OK
    width = max(len(r["id"]) for r in rows)
    print("%-*s  %-10s %-16s %s" % (width, "capability", "enforce", "against", "mechanisms"))
    for row in rows:
        print("%-*s  %-10s %-16s %s" % (width, row["id"], row["enforceable"],
                                        row["enforces_against"],
                                        ", ".join(row["mechanisms"])))
    print("")
    print("mechanism availability on %s: %s"
          % (facts.get("release"), json.dumps(facts.get("mechanism_availability"),
                                              sort_keys=True)))
    return EXIT_OK


def _cmd_kernel_facts(args, store, registry, root):
    facts = kernel_facts(getattr(args, "fixture", None), getattr(args, "config", None))
    _print(facts, True) if args.json else _print(facts)
    return EXIT_OK


def _cmd_enforce_plan(args, store, registry, root):
    facts = kernel_facts(getattr(args, "fixture", None), getattr(args, "config", None))
    plan = enforce_plan(root, store, registry, args.app_id, facts=facts)
    if args.out:
        store.ensure_dirs()
        with open(args.out, "w") as fh:
            json.dump(plan, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print("wrote %s" % args.out)
    elif args.write_overlay:
        store.ensure_dirs()
        path = os.path.join(store.enforce_dir, app_id_to_safe(args.app_id) + ".json")
        with open(path, "w") as fh:
            json.dump(plan, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print("wrote %s" % path)
    else:
        _print(plan, True)
    return EXIT_OK


def _cmd_sync(args, store, registry, root):
    res = sync(root, store, registry,
               apply_shipped_defaults=args.apply_shipped_defaults,
               dry_run=args.dry_run)
    if args.json:
        _print(res, True)
    else:
        print("recorded declarations for %d app(s)%s"
              % (len(res["recorded"]), " (dry-run)" if res["dry_run"] else ""))
        if res["shipped_defaults"]:
            for app_id, cap_id, state in res["shipped_defaults"]:
                print("  %-24s %-14s %s" % (app_id, cap_id, state))
    return EXIT_OK


def _cmd_serve(args, store, registry, root):
    return serve(store, registry, root, bind=args.bind, port=args.port,
                 allow_insecure_writes=args.allow_insecure_writes)


def _cmd_self_test(args, store, registry, root):
    failures = 0

    def check(name, cond, extra=""):
        nonlocal failures
        print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)))
        if not cond:
            failures += 1

    check("registry loads", len(registry.caps) >= 15, len(registry.caps))
    cap_id, why = registry.resolve("camera:capture")
    check("alias resolves", cap_id == "camera", (cap_id, why))
    cap_id, why = registry.resolve("landlock")
    check("unsupported token refused", cap_id is None and why, (cap_id, why))
    cap_id, why = registry.resolve("nonsense")
    check("unknown token refused", cap_id is None, (cap_id, why))
    enf = registry.enforcement_of("clipboard")
    check("clipboard marked not supported", enf["enforceable"] == "no", enf["enforceable"])
    enf = registry.enforcement_of("camera")
    check("camera never claims full enforcement",
          enf["enforceable"] in ("partial", "no"), enf["enforceable"])
    facts = kernel_facts()
    check("kernel facts collected", bool(facts.get("release")), facts.get("release"))
    rt = parse_kernel_release("4.14.253")
    check("kernel release parses", rt == (4, 14), rt)
    print("")
    print("self-test %s (%d failure(s))" % ("PASSED" if not failures else "FAILED", failures))
    return EXIT_OK if not failures else EXIT_DENIED


def build_parser():
    p = argparse.ArgumentParser(prog="nuxel-permd.py",
                                description="Nuxel per-capability permission "
                                            "manager and enforcement review tool")
    p.add_argument("--store", default=DEFAULT_STORE,
                   help="permission store directory (default %s)" % DEFAULT_STORE)
    p.add_argument("--registry", default=DEFAULT_CAP_REGISTRY,
                   help="capability registry JSON")
    p.add_argument("--root", default=DEFAULT_ROOT,
                   help="repository root used for manifest discovery")
    p.add_argument("--fixture", default=None,
                   help="read kernel facts from a fixture JSON instead of the host")
    p.add_argument("--config", default=None, help="kernel config file to read")
    sub = p.add_subparsers(dest="command")

    sp = sub.add_parser("list", help="list apps and their grant counts")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("show", help="show one app's grants and enforcement truth")
    sp.add_argument("app_id")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("grant", help="grant one capability to one app")
    sp.add_argument("app_id")
    sp.add_argument("capability")
    sp.add_argument("--duration", default="always", choices=list(VALID_DURATIONS))

    sp = sub.add_parser("revoke", help="revoke one capability")
    sp.add_argument("app_id")
    sp.add_argument("capability")

    sp = sub.add_parser("revoke-all", help="revoke every capability from one app")
    sp.add_argument("app_id")

    sp = sub.add_parser("check", help="exit 0 if granted, 1 if denied")
    sp.add_argument("app_id")
    sp.add_argument("capability")

    sp = sub.add_parser("sync", help="record manifest/profile declarations")
    sp.add_argument("--apply-shipped-defaults", action="store_true",
                    help="also grant the app registry's default_capabilities "
                         "(explicit first-boot opt-in; audited)")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("review", help="cross-check declarations against grants")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--require-granted", action="store_true",
                    help="treat declared-but-ungranted as an error")

    sp = sub.add_parser("enforcement-matrix", help="capability enforcement truth table")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("kernel-facts", help="measured kernel capability report")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("enforce-plan", help="generate the sandbox/nftables overlay for an app")
    sp.add_argument("app_id")
    sp.add_argument("--out", default=None)
    sp.add_argument("--write-overlay", action="store_true",
                    help="write to <store>/state/enforce/<app>.json")

    sp = sub.add_parser("serve", help="serve the JSON API for the UI apps")
    sp.add_argument("--bind", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8765)
    sp.add_argument("--allow-insecure-writes", action="store_true",
                    help="allow writes without NUXEL_PERMD_TOKEN "
                         "(documented, never the default)")

    sub.add_parser("self-test", help="run internal consistency checks")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return EXIT_USAGE
    try:
        registry = Registry(args.registry)
    except (IOError, OSError, ValueError) as exc:
        print("cannot load capability registry %s: %s" % (args.registry, exc),
              file=sys.stderr)
        return EXIT_STORE
    store = Store(args.store, registry)
    root = args.root

    handlers = {
        "list": _cmd_list,
        "show": _cmd_show,
        "grant": _cmd_grant,
        "revoke": _cmd_revoke,
        "revoke-all": _cmd_revoke_all,
        "check": _cmd_check,
        "review": _cmd_review,
        "enforcement-matrix": _cmd_matrix,
        "kernel-facts": _cmd_kernel_facts,
        "enforce-plan": _cmd_enforce_plan,
        "sync": _cmd_sync,
        "serve": _cmd_serve,
        "self-test": _cmd_self_test,
    }
    return handlers[args.command](args, store, registry, root)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except UnsupportedCapability as exc:
        print("REFUSED: %s" % exc, file=sys.stderr)
        sys.exit(EXIT_UNSUPPORTED)

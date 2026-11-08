"""Canonical Nuxel firewall paths (single source, env-overridable).

Runtime tests override these through environment variables so the unit suite
never touches /etc, /var/lib or /run on a developer machine.
"""
import os


def _env(name, default):
    return os.environ.get(name, default)


# Persistent owner policy / shipped default (read-only in the tree).
CONFIG_DIR = _env("NUXEL_CONFIG_DIR", "/etc/nuxel")
FIREWALL_CONFIG_DIR = _env("NUXEL_FIREWALL_CONFIG_DIR", os.path.join(CONFIG_DIR, "firewall"))
POLICY_FILE = _env("NUXEL_FIREWALL_POLICY_FILE", os.path.join(FIREWALL_CONFIG_DIR, "policy.json"))

# Persistent state: snapshots, last-known-good, pending transaction, audit.
STATE_DIR = _env("NUXEL_FIREWALL_STATE_DIR", "/var/lib/nuxel/firewall")

# Runtime status + dry-run renders (never persisted).
RUN_DIR = _env("NUXEL_RUN_DIR", "/run/nuxel")
FIREWALL_RUN_DIR = _env("NUXEL_FIREWALL_RUN_DIR", os.path.join(RUN_DIR, "firewall"))
DRY_RUN_DIR = _env("NUXEL_FIREWALL_DRY_RUN_DIR", os.path.join(FIREWALL_RUN_DIR, "dry-run"))


def ensure_dirs():
    for d in (FIREWALL_CONFIG_DIR, STATE_DIR, FIREWALL_RUN_DIR, DRY_RUN_DIR):
        os.makedirs(d, exist_ok=True)

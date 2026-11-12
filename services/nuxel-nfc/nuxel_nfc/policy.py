"""Per-app NFC authorization against the shared permD grant store.

The daemon owns the root-only controller socket, so it is the enforcement
point for the ``nfc`` capability: every scan/read/write/enable request carries
the caller's ``app_id`` and is checked against the same JSON store the
Settings app and the Permission Manager read and write.

Rules (fail closed):
  * ``status``/``diagnostics`` are not gated - they only report hardware and
    firmware inventory, never tag data.
  * ``read``/``clear``/``cancel`` need the stored ``nfc`` grant for the app.
  * ``scan`` and ``write`` are the actions that touch the owner's tags, so
    they require an explicit grant; an absent record is a deny.
  * an explicit ``decision: deny`` record always wins; an app may not
    switch the controller on if the owner has denied it.

Owner surfaces (Settings, Home, Permission Manager) are allowed to toggle the
controller on/off without a per-app grant, because they are the surface the
owner uses to manage the exact same policy.  They still need a grant to read
tag contents through the same socket.
"""
from __future__ import annotations

import json
import os

PERMISSIONS_DIR = os.environ.get("NUXEL_PERMISSIONS_DIR") or "/var/lib/nuxel/permissions"
CAPABILITY = "nfc"

OWNER_SURFACES = frozenset((
    "org.nuxel.Settings", "nuxel-settings", "org.nuxel.Home", "org.nuxel.Shell",
    "org.nuxel.Permissions",
))

# Verbs that only change controller power state (no tag data crosses the bus).
# These stay usable by the owner UI even before an NFC grant exists so the
# user can turn the radio on and then grant access to their tag app.
POWER_VERBS = frozenset(("enable", "set-enabled", "disable", "off"))
# Verbs that expose or mutate tag contents, or observe tag presence.
TAG_VERBS = frozenset(("scan", "read", "read-tag", "write", "write-tag", "clear",
                       # bridge-side alias for a one-shot scan
                       "test-tag"))


def _safe(app_id):
    return str(app_id).replace("/", "_").replace("..", "_")


def _grants(app_id):
    if not app_id:
        return {}
    base = PERMISSIONS_DIR
    for name in (_safe(app_id), app_id):
        path = os.path.join(base, name + ".json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict):
            return doc
    return {}


def _records(grants):
    """Every nfc-shaped grant record in an app's store file.

    permD writes capability records at the top level; the bridge/portal store
    wraps them in a ``grants`` object.  Both are accepted, and aliases
    (nfc:read, portal_type=nfc, delegate records) count for the same resource.
    """
    candidates = []
    for key in (CAPABILITY, "nfc:read", "nfc:scan", "nfc:tag", "tag:read"):
        rec = grants.get(key)
        if isinstance(rec, dict):
            candidates.append(rec)
    for value in grants.values():
        if isinstance(value, dict) and value.get("portal_type") == CAPABILITY:
            candidates.append(value)
    nested = grants.get("grants")
    if isinstance(nested, dict):
        rec = nested.get(CAPABILITY)
        if isinstance(rec, dict):
            candidates.append(rec)
    return candidates


def authorize(app_id, verb, scope=TAG_VERBS):
    """Decide whether ``app_id`` may perform ``verb``.

    Returns ``{"allowed": bool, "reason": str, "source": str}``.
    """
    scope = TAG_VERBS if scope is None else scope
    if verb in POWER_VERBS and (app_id in OWNER_SURFACES or app_id is None):
        return {"allowed": True, "reason": "owner-surface", "source": "policy"}
    if verb not in scope and verb not in POWER_VERBS:
        return {"allowed": False, "reason": "unknown verb", "source": "policy"}
    if not app_id:
        return {"allowed": False,
                "reason": "no app_id: unidentifiable caller cannot read tags",
                "source": "policy"}
    grants = _grants(app_id)
    records = _records(grants)
    # An explicit deny always wins over any allow record for the same app.
    if any(rec.get("decision") == "deny" or rec.get("granted") is False
           for rec in records):
        return {"allowed": False, "reason": "explicit deny", "source": "explicit-deny"}
    if not records:
        return {"allowed": False, "reason": "capability not granted",
                "source": "not-granted"}
    return {"allowed": True, "reason": "grant", "source": "grant"}

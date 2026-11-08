"""Policy semantics: direction defaults, app inheritance, migration, profiles.

The owner's requested default posture is INPUT deny, FORWARD deny, OUTPUT allow.
Per-app egress controls layer on top of the configurable global outbound default.
"""
from . import schema

NETWORK_CATEGORIES = ("lan", "wifi", "cellular", "vpn", "usb", "wired")


def global_outbound_default(policy):
    """'allow' or 'deny' — the effective global outbound mode."""
    return policy["defaults"]["output"]


def app_outbound(policy, app_id):
    """Effective outbound decision for one app ('allow'/'deny')."""
    app = policy["apps"].get(app_id)
    if app and app["outbound"] in ("allow", "deny"):
        return app["outbound"]
    mode = policy["app_defaults"]["outbound"]
    if mode == "allow":
        return "allow"
    if mode == "deny":
        return "deny"
    # inherit_global
    return global_outbound_default(policy)


def app_network_decision(policy, app_id, category):
    """Effective decision for one app on one network category."""
    app = policy["apps"].get(app_id)
    if app and category in app["networks"] and app["networks"][category] in ("allow", "deny"):
        return app["networks"][category]
    return app_outbound(policy, app_id)


def new_app_decision(policy):
    """Decision assigned to an app that appears for the first time."""
    mode = policy["app_defaults"]["new_app_policy"]
    if mode == "allow":
        return "allow"
    if mode == "deny":
        return "deny"
    return app_outbound(policy, "_new_app_placeholder")


def migrate_legacy_overrides(policy, legacy):
    """Preserve explicit legacy per-app blocks/allows as explicit overrides.

    `legacy` maps app_id -> {'network_class': 'public'|'isolated'} (or similar).
    'isolated'/'deny' becomes explicit deny; 'public'/'allow' becomes explicit
    allow.  Apps with no historical override inherit the new global default.
    """
    counts = {"preserved_deny": 0, "preserved_allow": 0, "inheriting": 0}
    migrated = dict(policy)
    migrated.setdefault("apps", {})
    for app_id, entry in (legacy or {}).items():
        cls = (entry or {}).get("network_class", entry if isinstance(entry, str) else "")
        if cls in ("isolated", "deny", "block"):
            migrated["apps"].setdefault(app_id, {})["outbound"] = "deny"
            counts["preserved_deny"] += 1
        elif cls in ("public", "allow", "network", "internet"):
            migrated["apps"].setdefault(app_id, {})["outbound"] = "allow"
            counts["preserved_allow"] += 1
        else:
            counts["inheriting"] += 1
    return migrated, counts


def normalize_app_id(app_id):
    """Deterministic, collision-safe normalization for kernel identities."""
    out = "".join(c.lower() if c.isalnum() or c == "-" else "-" for c in app_id)
    out = re_sub(out)
    return out or "unknown"


def re_sub(s):
    import re
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def builtin_profiles():
    return {
        "default": {
            "name": "Default",
            "defaults": {"input": "deny", "forward": "deny", "output": "allow"},
        },
        "strict-outbound": {
            "name": "Strict outbound",
            "defaults": {"input": "deny", "forward": "deny", "output": "deny"},
        },
        "public-wifi": {
            "name": "Public Wi-Fi",
            "defaults": {"input": "deny", "forward": "deny", "output": "allow"},
        },
        "offline": {
            "name": "Offline",
            "defaults": {"input": "deny", "forward": "deny", "output": "deny"},
        },
    }


def apply_profile(policy, profile_id):
    """Return a policy with the profile's direction defaults applied."""
    profiles = policy.get("profiles", {}) or {}
    prof = profiles.get(profile_id)
    if prof is None:
        prof = builtin_profiles().get(profile_id)
    if prof is None:
        raise schema.PolicyValidationError("unknown profile %r" % profile_id)
    out = dict(policy)
    defaults = dict(out.get("defaults", {}))
    for direction in ("input", "forward", "output"):
        if direction in prof.get("defaults", {}):
            defaults[direction] = prof["defaults"][direction]
    out["defaults"] = defaults
    return out

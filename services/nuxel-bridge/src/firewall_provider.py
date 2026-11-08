"""Nuxel Firewall — bridge provider (thin, validated wrapper).

The privileged firewall logic lives in services/nuxel-firewall/nuxel_firewall.
This module exposes it through the bridge's `handle(verb, params)` contract so a
PWA can only call named, structured methods — never arbitrary shell/rule text.
"""
import os
import sys

_BASE = os.environ.get(
    "NUXEL_FIREWALL_PKG",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                 "nuxel-firewall"))
if os.path.isdir(_BASE) and _BASE not in sys.path:
    sys.path.insert(0, _BASE)

try:
    from nuxel_firewall.provider import FirewallProvider
    from nuxel_firewall import schema
    _AVAILABLE = True
except Exception as exc:  # pragma: no cover - degraded import
    FirewallProvider = None
    schema = None
    _IMPORT_ERROR = str(exc)
    _AVAILABLE = False

_READ_VERBS = {"status", "backend-capabilities", "installed-apps", "interfaces",
               "listeners", "rules", "pending-transaction", "dry-run"}
_MUTATING_VERBS = {"apply", "confirm", "rollback", "enable", "disable",
                   "set-direction-default", "set-app-rule", "set-service-rule",
                   "activate-profile"}

# Only the owner surfaces may mutate firewall policy.
_OWNER_APP_IDS = {"org.nuxel.Firewall", "org.nuxel.Home", "nuxel-settings"}

_provider = None


def _get():
    global _provider
    if not _AVAILABLE:
        return None
    if _provider is None:
        _provider = FirewallProvider()
    return _provider


def handle(verb, params, caller_app_id=None):
    if not _AVAILABLE:
        return {"success": False, "error": "firewall provider unavailable",
                "detail": _IMPORT_ERROR}
    params = params if isinstance(params, dict) else {}
    caller = caller_app_id or params.get("caller", "")
    try:
        p = _get()
        if verb in _MUTATING_VERBS and caller not in _OWNER_APP_IDS:
            return {"success": False, "error": "capability_denied",
                    "detail": "only the Firewall app, Home or Settings may mutate firewall policy"}

        if verb == "status":
            return {"success": True, "data": p.get_status()}
        if verb == "backend-capabilities":
            return {"success": True, "data": p.get_backend_capabilities()}
        if verb == "installed-apps":
            return {"success": True, "data": p.get_installed_apps()}
        if verb == "interfaces":
            return {"success": True, "data": p.get_interfaces()}
        if verb == "listeners":
            return {"success": True, "data": p.get_listeners()}
        if verb == "rules":
            return {"success": True, "data": p.get_rules()}
        if verb == "pending-transaction":
            return {"success": True, "data": p.get_pending_transaction()}
        if verb == "dry-run":
            return {"success": True, "data": p.dry_run()}
        if verb == "apply":
            return {"success": True, "data": p.apply(params.get("rollback_after"))}
        if verb == "confirm":
            return {"success": True, "data": p.confirm()}
        if verb == "rollback":
            return {"success": True, "data": p.rollback()}
        if verb == "enable":
            return {"success": True, "data": p.enable()}
        if verb == "disable":
            return {"success": True, "data": p.disable()}
        if verb == "set-direction-default":
            return {"success": True, "data": p.set_direction_default(
                params.get("direction"), params.get("action"))}
        if verb == "set-app-rule":
            return {"success": True, "data": p.set_app_rule(
                params.get("app_id"), params.get("outbound"))}
        if verb == "set-service-rule":
            return {"success": True, "data": p.set_service_rule(
                params.get("service_id"), params.get("source_cidrs") or [],
                params.get("enabled"))}
        if verb == "activate-profile":
            return {"success": True, "data": p.activate_profile(params.get("profile_id"))}
        return {"success": False, "error": "unknown verb", "verb": verb}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc), "error_code": "PROVIDER_ERROR"}

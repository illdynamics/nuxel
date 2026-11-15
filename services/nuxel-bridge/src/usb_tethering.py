#!/usr/bin/env python3
"""Nuxel USB networking gadget provider (userspace; no flashing).

This module is a READ-BACK adapter plus a thin, typed action surface for the
single gadget owner, ``/usr/lib/nuxel/nuxel-usb-mode.sh``.

Gadget compositions (all keep the CDC-ACM recovery console):

  charging       ACM only (safe default / rollback target)
  file_transfer  ACM + MTP
  usb_network    ACM + CDC-NCM — local USB Ethernet + SSH, no Internet share
  usb_tethering  ACM + CDC-NCM composition flagged for explicit Internet share

Internet sharing itself lives in ``usb_tether.py`` (scoped nftables) and is
started/stopped separately.  A tethering *composition* alone is not Internet.

Nothing here mutates the gadget directly: configfs is owned by
``nuxel-usb-mode.sh``, which serialises transitions with flock(), journals them
and rolls back to ACM-only on failure.  This module only invokes that helper
with a fixed argv list (never a shell) and reports the helper's REAL recorded
state; it never fabricates success and never infers "active" from a configfs
directory.

Read roots are overridable for offline tests (``NUXEL_USB_MODE_HELPER``,
``NUXEL_USB_MODE_STATE``, ``NUXEL_USB_MODE_SELECTION``).
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict, Optional

HELPER = "/usr/lib/nuxel/nuxel-usb-mode.sh"
ACTIVATION = "/run/nuxel/usb-mode.state"
SELECTION = "/run/nuxel/connection-mode.json"

# Owner-facing mode names and their compatibility aliases.
_MODES = {
    "off": "charging",
    "charging": "charging",
    "file_transfer": "file_transfer",
    "usb-net": "usb_network",
    "usb_network": "usb_network",
    "usbnet": "usb_network",
    "usb-tether": "usb_tethering",
    "usb_tethering": "usb_tethering",
    "tether": "usb_tethering",
}
_NETWORK_MODES = ("usb_network", "usb_tethering")


def _root(env: str, default: str) -> str:
    return os.environ.get(env, default)


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def normalize_function(function: Optional[str]) -> str:
    """Only CDC-NCM is enabled for this release.

    RNDIS/ECM/EEM source paths exist in the kernel, but they have not passed a
    physical teardown/ACM-preservation soak, and macOS has no native RNDIS.
    The kernel-level NCM lifecycle fix and its userspace marker gate NCM.
    """
    fn = str(function or "ncm").strip().lower()
    if fn not in ("ncm", "auto", ""):
        return ""
    return "ncm"


def current_state() -> Dict[str, Any]:
    selection = _read_json(_root("NUXEL_USB_MODE_SELECTION", SELECTION))
    activation = _read_json(_root("NUXEL_USB_MODE_STATE", ACTIVATION))
    selected = str(selection.get("mode", "") or "charging")
    mode = str(activation.get("mode", "") or "charging")
    active = bool(activation.get("active"))
    if not active:
        mode = "charging" if mode else ""
    label = str(activation.get("source", "") or "")
    if mode in _NETWORK_MODES:
        # The state file records the true live check (netdev present + UDC
        # configured); never report a network mode active otherwise.
        active = active and bool(activation.get("interface"))
    if not active:
        mode = "charging"
    fn = "ncm" if mode in _NETWORK_MODES else ""
    return {
        "success": True,
        "selected": selected,
        "mode": mode,
        "active": active,
        "interface": activation.get("interface", "") if mode in _NETWORK_MODES else "",
        "function": fn,
        "upstream": activation.get("upstream", "") or "",
        "source": label,
        "tether_composition": bool(activation.get("tether_composition")),
        "device_ip": activation.get("phone_address", "") if mode in _NETWORK_MODES else "",
        "host_ip": activation.get("host_address", "") if mode in _NETWORK_MODES else "",
        "subnet": "10.15.19.0/24" if mode in _NETWORK_MODES else "",
        "acm_preserved": bool(activation.get("source", "").startswith(("gadget:acm", "gadget:ncm+acm", "gadget:mtp+acm", "rollback:acm"))),
        "last_error": activation.get("error"),
        "transaction": activation.get("transaction"),
    }


def set_mode(mode: str, function: str = "ncm") -> Dict[str, Any]:
    """Request a transition through the single gadget owner.

    ``mode`` accepts the typed names above.  ``function`` must be NCM (the only
    physically targeted data plane for this batch); anything else is refused
    instead of silently substituting a different function.
    """
    target = _MODES.get(str(mode or "").strip().lower())
    if not target:
        return {"success": False, "error": "unknown-mode", "mode": mode,
                "error_code": "INVALID_MODE",
                "allowed": sorted(k for k in _MODES if k != "off")}
    fn = normalize_function(function)
    if not fn:
        return {"success": False, "error": "unsupported-function", "function": function,
                "error_code": "UNSUPPORTED_FUNCTION",
                "detail": "only CDC-NCM is enabled; RNDIS/ECM/EEM are not physically "
                          "validated and macOS has no native RNDIS driver"}
    helper = _root("NUXEL_USB_MODE_HELPER", HELPER)
    if not os.path.exists(helper):
        return {"success": False, "error": "usb-mode-helper-missing", "mode": mode,
                "error_code": "PROVIDER_UNAVAILABLE",
                "detail": "the single USB gadget owner is not installed on this image"}
    want = target
    if want == "usb_network":
        want = "usb_network"
    try:
        proc = subprocess.run([helper, want], capture_output=True, text=True,
                              timeout=90, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "helper-timeout", "mode": target,
                "error_code": "TIMEOUT"}
    except OSError as exc:
        return {"success": False, "error": "helper-exec-failed", "mode": target,
                "detail": str(exc), "error_code": "EXEC_FAILED"}
    result = current_state()
    result["requested"] = target
    result["helper_rc"] = proc.returncode
    result["helper_output"] = (proc.stdout or "").strip()[:4000]
    # The manager is the source of truth: success means the requested
    # composition is the one the running kernel reports now.
    if target == "charging":
        result["success"] = proc.returncode == 0 and not result["active"]
    else:
        result["success"] = (proc.returncode == 0 and result["active"]
                             and result["mode"] == target)
    if not result["success"] and not result.get("last_error"):
        result["last_error"] = (proc.stderr or proc.stdout or "").strip()[:800] or \
            "helper did not confirm the requested composition"
    return result


def start_tethering_composition() -> Dict[str, Any]:
    return set_mode("usb_tethering", "ncm")


def stop() -> Dict[str, Any]:
    return set_mode("charging", "ncm")


def preflight(mode: str = "usb_network") -> Dict[str, Any]:
    """Read-only capability summary for the UI (no configfs mutation)."""
    state = current_state()
    return {
        "success": True,
        "requested": _MODES.get(str(mode).lower()),
        "helper_present": os.path.exists(_root("NUXEL_USB_MODE_HELPER", HELPER)),
        "active": state["active"],
        "mode": state["mode"],
        "ncm_function": "ncm",
        "acm_preserved": state.get("acm_preserved"),
        "device_ip": state.get("device_ip"),
        "host_ip": state.get("host_ip"),
        "last_error": state.get("last_error"),
        "mutated": False,
    }


def enable_for_host(upstream: Optional[str] = None) -> Dict[str, Any]:
    """Explicit owner action: USB network composition, then Internet sharing.

    This is the one-step equivalent of (a) USB Network ON, (b) USB Tether
    start.  Both remain separate states in the status document; this only
    sequences them for the Settings/Quick Settings action that literally asks
    to share Internet with the attached computer.

    Returns the tether provider's real read-back.  It never reports Internet
    verified: only the attached computer's own end-to-end evidence can do that
    (``usb-tether host-report``).
    """
    import usb_tether  # same package dir; imported lazily for tests
    comp = set_mode("usb_tethering", "ncm")
    if not comp.get("success"):
        return {"success": False, "stage": "usb-network",
                "error": comp.get("error") or comp.get("last_error"),
                "error_code": comp.get("error_code") or "USB_NOT_ACTIVE",
                "usb": comp}
    teth = usb_tether.start(upstream, source="usb-net:enable-for-host")
    teth["stage"] = "usb-tether"
    teth["usb"] = current_state()
    return teth


def disable_all(source: str = "api") -> Dict[str, Any]:
    """Stop Internet sharing first, then return the gadget to ACM-only."""
    import usb_tether
    t = usb_tether.stop(source=source)
    u = stop()
    return {"success": bool(u.get("success")), "tether": t, "usb": u}

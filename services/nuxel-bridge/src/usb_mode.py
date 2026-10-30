#!/usr/bin/env python3
"""Nuxel USB connection-mode state machine (userspace, no flashing).

Charging and File Transfer are two explicit modes:

  charging       normal charging + the existing USB CDC-ACM console stays
                 available.  No storage export is active.
  file_transfer  a real supported transfer endpoint is activated through the
                 dedicated helper /usr/lib/nuxel/nuxel-usb-mode.sh and the
                 endpoint truth is read back from /run/nuxel/usb-mode.state.

This module NEVER marks a mode active unless the helper records success.  It
never exposes a mounted live root/home filesystem as raw USB mass storage; the
helper is responsible for that safety decision and this module only reports what
the helper actually did.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict

HELPER = "/usr/lib/nuxel/nuxel-usb-mode.sh"
SELECTION = "/run/nuxel/connection-mode.json"
ACTIVATION = "/run/nuxel/usb-mode.state"

_ALLOWED = {"charging", "file_transfer"}


def _root(env: str, default: str) -> str:
    return os.environ.get(env, default)


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r") as fh:
            data = __import__("json").load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".new"
    with open(tmp, "w") as fh:
        __import__("json").dump(data, fh)
        fh.write("\n")
    os.replace(tmp, path)


def current_state() -> Dict[str, Any]:
    """Return the persisted selected mode plus the last activation truth."""
    selection = _read_json(_root("NUXEL_CONNECTION_MODE", SELECTION))
    activation = _read_json(_root("NUXEL_USB_MODE_STATE", ACTIVATION))
    selected = str(selection.get("mode", "charging"))
    if selected not in _ALLOWED:
        selected = "charging"
    return {
        "selected": selected,
        "transition_in_progress": bool(selection.get("transition_in_progress")),
        "endpoint_state": activation.get("endpoint_state", "inactive"),
        "active": bool(activation.get("active")),
        "source": activation.get("source", "unavailable:not-activated"),
        "last_error": activation.get("error"),
    }


def set_mode(mode: str) -> Dict[str, Any]:
    """Request a mode transition and return the REAL result.

    The helper performs the gadget/storage change and writes the activation
    state.  A missing helper is reported as an error, never as success.
    """
    if mode not in _ALLOWED:
        return {"success": False, "error": "unknown-mode", "mode": mode}
    if not os.path.exists(_root("NUXEL_USB_MODE_HELPER", HELPER)):
        return {
            "success": False,
            "error": "usb-mode-helper-missing",
            "mode": mode,
            "detail": "the safe USB-mode helper is not installed on this image",
        }
    selection_path = _root("NUXEL_CONNECTION_MODE", SELECTION)
    _write_json(selection_path, {
        "mode": mode,
        "transition_in_progress": True,
    })
    try:
        proc = subprocess.run(
            [_root("NUXEL_USB_MODE_HELPER", HELPER), mode],
            capture_output=True, text=True, timeout=45,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        _write_json(selection_path, {"mode": mode, "transition_in_progress": False,
                                     "last_error": "helper-timeout"})
        return {"success": False, "error": "helper-timeout", "mode": mode}
    except OSError as exc:
        _write_json(selection_path, {"mode": mode, "transition_in_progress": False,
                                     "last_error": str(exc)})
        return {"success": False, "error": "helper-exec-failed", "mode": mode,
                "detail": str(exc)}

    activation = _read_json(_root("NUXEL_USB_MODE_STATE", ACTIVATION))
    if mode == "charging":
        # Charging is successful when the helper confirmed charging mode; the
        # transfer endpoint being inactive is the CORRECT state for charging.
        ok = activation.get("mode") == "charging" and not bool(activation.get("active"))
    else:
        # File Transfer is successful only when the endpoint is genuinely active.
        ok = bool(activation.get("active")) and activation.get("mode") == mode
    _write_json(selection_path, {
        "mode": mode,
        "transition_in_progress": False,
        "last_error": None if ok else activation.get("error", "helper-rejected"),
    })
    result = current_state()
    result["success"] = ok
    result["helper_rc"] = proc.returncode
    result["helper_output"] = (proc.stdout or "").strip()[:4000]
    if not ok and not result.get("last_error"):
        result["last_error"] = activation.get("error") or "helper did not confirm activation"
    return result

#!/usr/bin/env python3
"""Resolve launcher app ids to the compositor's real Wayland app_id.

Flatpak identities are reverse-DNS (``com.sindresorhus.Caprine``) while many
Electron/Qt/GTK clients publish a short product or StartupWMClass value as the
xdg_toplevel app_id (``Caprine``, ``ferdium``, ``teams-for-linux``).  A focus
or close request for the reverse-DNS id therefore silently matches nothing and
the window stays behind Home.

This module is the single normalization rule used by the bridge.  It never
executes a client-supplied string: only an already-validated app id is used to
read that app's exported desktop entry, and only app_id tokens from the trusted
compositor listing are compared.
"""
from __future__ import annotations

import os
import re
from typing import Iterable, List, Optional, Sequence, Set

APP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
APP_ID_TOKEN_RE = re.compile(r"app_id=(\S+)")

# System and per-user Flatpak exports, then native desktop entries.
DESKTOP_DIRS = (
    "/var/lib/flatpak/exports/share/applications",
    "/home/nuxel/.local/share/flatpak/exports/share/applications",
    "/usr/share/applications",
    "/home/nuxel/.local/share/applications",
)


def norm_app_id(value: object) -> str:
    """Case/punctuation-insensitive key used for comparison only."""
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def desktop_startup_wm_class(app_id: str) -> str:
    """Read StartupWMClass from the exact exported desktop file for ``app_id``.

    The app id is validated and used as a filename component only; no caller
    supplied path is opened.  Failure is non-fatal and returns ``""``.
    """
    if not isinstance(app_id, str) or not APP_ID_RE.match(app_id):
        return ""
    for base in DESKTOP_DIRS:
        path = os.path.join(base, app_id + ".desktop")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                in_desktop = False
                for raw in fh:
                    line = raw.strip()
                    if line.startswith("["):
                        in_desktop = (line == "[Desktop Entry]")
                        continue
                    if in_desktop and line.startswith("StartupWMClass="):
                        value = line.split("=", 1)[1].strip()
                        if value:
                            return value
        except OSError:
            continue
    return ""


def app_surface_candidates(app_id: str) -> List[str]:
    """Return ordered, unique candidate surface ids for one launcher app id."""
    if not isinstance(app_id, str) or not app_id:
        return []
    out: List[str] = [app_id]
    if "." in app_id:
        out.append(app_id.rsplit(".", 1)[-1])
    wm_class = desktop_startup_wm_class(app_id)
    if wm_class:
        out.append(wm_class)
    seen: Set[str] = set()
    unique: List[str] = []
    for item in out:
        key = norm_app_id(item)
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def surface_matches(wanted: str, actual: str) -> bool:
    """True when ``actual`` is a credible compositor id for ``wanted``."""
    wanted_key = norm_app_id(wanted)
    actual_key = norm_app_id(actual)
    if not wanted_key or not actual_key:
        return False
    if wanted_key == actual_key:
        return True
    candidates = [norm_app_id(c) for c in app_surface_candidates(wanted)]
    if actual_key in candidates:
        return True
    # Short product names are the common mismatch (Caprine, ferdium, zapzap).
    # Require at least five characters so single-letter/empty ids cannot match.
    if len(actual_key) >= 5 and wanted_key.endswith(actual_key):
        return True
    if len(wanted_key) >= 5 and actual_key.endswith(wanted_key):
        return True
    for key in candidates:
        if len(actual_key) >= 5 and key.endswith(actual_key):
            return True
        if len(key) >= 5 and actual_key.endswith(key):
            return True
    return False


def surface_ids_from_listing(listing: str) -> List[str]:
    """Extract app_id tokens from ``nuxel-foreign-toplevel list`` output."""
    if not isinstance(listing, str):
        return []
    out: List[str] = []
    for token in APP_ID_TOKEN_RE.findall(listing):
        if token not in out:
            out.append(token)
    return out


def resolve_from_listing(listing: str, app_id: str) -> Optional[str]:
    """Return the compositor app_id that should be focused/closed, or None."""
    if not isinstance(app_id, str) or not app_id:
        return None
    actuals = surface_ids_from_listing(listing)
    exact_keys = {norm_app_id(c) for c in app_surface_candidates(app_id)}
    for actual in actuals:
        if norm_app_id(actual) in exact_keys:
            return actual
    for actual in actuals:
        if surface_matches(app_id, actual):
            return actual
    return None

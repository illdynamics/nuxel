#!/usr/bin/env python3
"""Read-only WAD discovery and streaming for Nuxel Doom.

The browser UI is sandboxed and must never receive a general filesystem API.
This module exposes only regular ``.wad`` files below a fixed allowlist of game
data directories, addresses them by content digest, and returns the raw WAD
bytes for the WebAssembly Chocolate Doom engine to write into its virtual FS.

There is no write path and no caller-supplied path.  The allowlist is the only
authority; symlinks are resolved and must still land inside an allowed root.
"""
from __future__ import annotations

import hashlib
import os
import re
import time
from typing import Any, Dict, List, Optional

ALLOWED_ROOTS = (
    "/home/nuxel/doom",
    "/home/nuxel/Downloads",
    "/home/nuxel/Documents",
    "/usr/share/doom",
    "/usr/share/games/doom",
    "/usr/local/share/doom",
)
SUFFIXES = (".wad",)
MAX_WAD_BYTES = 1024 * 1024 * 1024  # 1 GiB: reject absurd files, not player WADs
ID_RE = re.compile(r"^[0-9a-f]{64}$")
CACHE_TTL = 5.0
_CACHE: Dict[str, Any] = {"at": 0.0, "items": [], "by_id": {}}

PRETTY = {
    "freedoom1": "Freedoom: Phase 1",
    "freedoom2": "Freedoom: Phase 2",
    "freedm": "FreeDM",
    "doom": "Doom (shareware)",
    "doom1": "Doom (shareware)",
    "doom2": "Doom II",
    "tnt": "TNT: Evilution",
    "plutonia": "The Plutonia Experiment",
    "heretic": "Heretic",
    "hexen": "Hexen",
    "strife": "Strife",
}


def _pretty(path: str) -> str:
    stem = os.path.splitext(os.path.basename(path))[0]
    return PRETTY.get(stem.lower(), stem.replace("_", " ").replace("-", " ").title())


def _inside_allowed(path: str) -> bool:
    real = os.path.realpath(path)
    for root in ALLOWED_ROOTS:
        real_root = os.path.realpath(root)
        try:
            if os.path.commonpath((real, real_root)) == real_root:
                return True
        except ValueError:
            continue
    return False


def _wad_meta(path: str) -> Optional[Dict[str, Any]]:
    try:
        size = os.path.getsize(path)
        if size < 12 or size > MAX_WAD_BYTES:
            return None
        with open(path, "rb") as fh:
            head = fh.read(12)
            if len(head) < 12 or head[:4] not in (b"IWAD", b"PWAD"):
                return None
            count = int.from_bytes(head[4:8], "little")
            offset = int.from_bytes(head[8:12], "little")
            if count <= 0 or count > 65535 or offset < 12 or offset >= size:
                return None
            names: List[str] = []
            fh.seek(offset)
            for _ in range(min(count, 4096)):
                ent = fh.read(16)
                if len(ent) < 16:
                    break
                names.append(ent[8:16].rstrip(b"\x00").decode("ascii", "replace"))
        tags = ["IWAD" if head[:4] == b"IWAD" else "PWAD"]
        if any(n in ("E1M1", "E2M1", "E3M1", "E4M1") for n in names):
            tags.append("Doom 1")
        if "MAP01" in names:
            tags.append("Doom 2 / Hexen")
        if any(n in ("FREEDOOM", "FREEDM") for n in names):
            tags.append("Freedoom")
        return {"magic": head[:4].decode("ascii"), "tags": tags,
                "lumps": count, "size": size}
    except OSError:
        return None


def _digest(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def refresh(force: bool = False) -> List[Dict[str, Any]]:
    """Return the allowlisted WAD catalogue, digest-addressed."""
    now = time.time()
    if not force and now - _CACHE["at"] < CACHE_TTL:
        return list(_CACHE["items"])
    items: List[Dict[str, Any]] = []
    seen = set()
    by_id: Dict[str, Dict[str, Any]] = {}
    for root in ALLOWED_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # Bounded, non-hidden walk; do not follow directory symlinks.
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for name in filenames:
                if name.startswith(".") or not name.lower().endswith(SUFFIXES):
                    continue
                path = os.path.join(dirpath, name)
                if not os.path.isfile(path) or not _inside_allowed(path):
                    continue
                real = os.path.realpath(path)
                if real in seen:
                    continue
                meta = _wad_meta(real)
                if not meta:
                    continue
                try:
                    digest = _digest(real)
                except OSError:
                    continue
                if digest in by_id:
                    continue
                seen.add(real)
                item = {
                    "id": digest,
                    "name": _pretty(real),
                    "file": os.path.basename(real),
                    "path": real,
                    **meta,
                }
                items.append(item)
                by_id[digest] = item
    items.sort(key=lambda w: (0 if "IWAD" in w["tags"] else 1,
                              w["name"].lower(), w["file"].lower()))
    _CACHE.update({"at": now, "items": items, "by_id": by_id})
    return list(items)


def public_catalogue() -> Dict[str, Any]:
    """JSON-safe catalogue.  Absolute paths are omitted from the response."""
    items = []
    for item in refresh():
        items.append({k: v for k, v in item.items() if k != "path"})
    return {"success": True, "count": len(items), "wads": items}


def lookup(wad_id: str) -> Optional[Dict[str, Any]]:
    if not isinstance(wad_id, str) or not ID_RE.match(wad_id):
        return None
    refresh()
    return _CACHE["by_id"].get(wad_id)


def read_bytes(wad_id: str) -> Optional[bytes]:
    item = lookup(wad_id)
    if not item:
        return None
    path = item["path"]
    if not _inside_allowed(path):
        return None
    try:
        with open(path, "rb") as fh:
            data = fh.read(MAX_WAD_BYTES + 1)
    except OSError:
        return None
    if len(data) > MAX_WAD_BYTES:
        return None
    return data

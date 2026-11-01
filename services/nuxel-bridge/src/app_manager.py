#!/usr/bin/env python3
"""Canonical installed-app registry and local-bundle lifecycle (PWNAGE-45000).

One source of truth: the versioned app registry that the PWA launcher, native
shell and HTTP bridge already consume.  NuxTore install/remove now go through
this module instead of flipping localStorage flags.  Registration validates the
app id, the real start URL/index and the manifest; removal unregisters the app
while leaving its payload and user data on disk.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")
DEFAULT_REGISTRY = os.environ.get(
    "NUXEL_APP_REGISTRY",
    "/etc/nuxel/app-registry/app_registry.json",
)
WEBROOT = os.environ.get("NUXEL_WEBROOT", "/usr/share/nuxel")

# Case-sensitive IDs are required.  Legacy aliases are migrated explicitly and
# must never produce two Home icons for the same application.
ALIASES = {
    "org.nuxel.NuxTore": "org.nuxel.Nuxtore",
    "org.nuxel.Snekbyte": "org.nuxel.SnekByte",
    "org.nuxel.Nuxtore": "org.nuxel.Nuxtore",
}

# Catalog packages that are already shipped in this image.  Reconciliation may
# register a missing canonical entry only when its payload is complete.
CATALOG_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "org.nuxel.Media": {"name": "Media Player", "category": "media", "icon": "🎬",
                        "url": "/pwa/nuxel-apps/media/index.html", "capabilities": ["audio:playback", "media:library"]},
    "org.nuxel.Downloader": {"name": "Media Downloader", "category": "media", "icon": "⬇️",
                             "url": "/pwa/nuxel-apps/downloader/index.html", "capabilities": ["download:queue"]},
    "org.nuxel.Authenticator": {"name": "Authenticator", "category": "security", "icon": "🔐",
                                "url": "/pwa/nuxel-apps/authenticator/index.html", "capabilities": ["storage:encrypted"]},
    "org.nuxel.Cleanup": {"name": "Safe Cleanup", "category": "tools", "icon": "🧹",
                          "url": "/pwa/nuxel-apps/cleanup/index.html", "capabilities": ["storage:cleanup"]},
    "org.nuxel.DevMgmt": {"name": "DevMgmt", "category": "tools", "icon": "🛠️",
                          "url": "/pwa/nuxel-apps/devmgmt/index.html", "capabilities": ["system:inspect"]},
    "org.nuxel.PenguInterface": {"name": "PenguInterface", "category": "system", "icon": "🐧",
                                 "url": "/pwa/nuxel-apps/penguinterface/index.html", "capabilities": ["system:inspect"]},
}


def canonical_id(app_id: str) -> str:
    return ALIASES.get(app_id, app_id)


def _atomic_json(path: str, doc: Dict[str, Any]) -> None:
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".registry-", dir=d)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w") as fh:
            json.dump(doc, fh, indent=2, sort_keys=False)
            fh.write("\n")
        os.replace(tmp, path)
        os.chmod(path, 0o644)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _resolve_web_path(url: str) -> Optional[Path]:
    if not isinstance(url, str) or not url.startswith("/"):
        return None
    rel = url.split("?", 1)[0].split("#", 1)[0].lstrip("/")
    root = Path(WEBROOT).resolve()
    p = (root / rel).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return None
    return p


def app_state(app: Dict[str, Any]) -> str:
    if app.get("status") in ("unsupported", "blocked"):
        return "unsupported_on_device"
    kind = app.get("type", "pwa")
    if kind == "native":
        binary = app.get("native_binary")
        if not binary or not isinstance(binary, str):
            return "invalid_manifest"
        if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
            return "missing_files"
        return "installed_and_launchable"
    url = app.get("url") or app.get("start_url")
    p = _resolve_web_path(url or "")
    if not p or not p.is_file():
        return "missing_files"
    manifest = p.parent / "manifest.json"
    if not manifest.is_file():
        return "invalid_manifest"
    try:
        m = json.loads(manifest.read_text())
        if not isinstance(m, dict) or not m.get("start_url"):
            return "invalid_manifest"
    except (OSError, ValueError):
        return "invalid_manifest"
    return "installed_and_launchable"


def _dedupe_and_migrate(apps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for app in apps:
        if not isinstance(app, dict):
            continue
        aid = canonical_id(str(app.get("id", "")))
        if not APP_ID_RE.match(aid):
            continue
        if aid in seen:
            continue
        seen.add(aid)
        app = dict(app)
        app["id"] = aid
        out.append(app)
    return out


class AppManager:
    def __init__(self) -> None:
        self.path = os.environ.get("NUXEL_APP_REGISTRY", DEFAULT_REGISTRY)
        self._lock = threading.RLock()

    def load(self) -> Dict[str, Any]:
        try:
            with open(self.path) as fh:
                doc = json.load(fh)
            if not isinstance(doc, dict) or not isinstance(doc.get("apps"), list):
                raise ValueError("invalid registry")
            return doc
        except (OSError, ValueError):
            return {"schema": "nuxel.app-registry/1", "registry_version": 1,
                    "url_base": "http://127.0.0.1:8000", "apps": []}

    def save(self, doc: Dict[str, Any]) -> None:
        doc["apps"] = _dedupe_and_migrate(doc.get("apps", []))
        doc["registry_version"] = int(doc.get("registry_version", 1)) + 1
        doc["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        _atomic_json(self.path, doc)

    def find(self, app_id: str) -> Optional[Dict[str, Any]]:
        aid = canonical_id(app_id)
        for app in self.load().get("apps", []):
            if canonical_id(str(app.get("id"))) == aid:
                return app
        return None

    def inventory(self, ids: Optional[List[str]] = None) -> Dict[str, Any]:
        with self._lock:
            doc = self.load()
            apps = []
            by_id = {}
            for app in doc.get("apps", []):
                aid = canonical_id(str(app.get("id")))
                state = app_state(app)
                entry = {
                    "id": aid,
                    "name": app.get("name"),
                    "type": app.get("type", "pwa"),
                    "url": app.get("url"),
                    "state": state,
                    "launchable": state == "installed_and_launchable",
                    "registered": True,
                }
                apps.append(entry)
                by_id[aid] = entry
            if ids:
                apps = [by_id.get(canonical_id(i), {
                    "id": canonical_id(i), "state": "staged_not_registered",
                    "registered": False, "launchable": False,
                }) for i in ids]
            return {"success": True, "schema": "nuxel.app-inventory/1",
                    "registry_version": doc.get("registry_version"),
                    "apps": apps}

    def register(self, app_id: str, name: str = "", start_url: str = "",
                 version: str = "", sha256: str = "", capabilities: Optional[list] = None,
                 app_dir: str = "") -> Dict[str, Any]:
        aid = canonical_id(app_id or "")
        if not APP_ID_RE.match(aid):
            return {"success": False, "error": "invalid_app_id"}
        # A registration may only point at a local Nuxel app bundle entry.
        # No arbitrary HTML, query-string redirect, external URL or client
        # executable is accepted.
        if not re.match(r"^/pwa/nuxel-apps/[A-Za-z0-9._-]+/index\.html$", start_url or ""):
            return {"success": False, "error": "start_url_not_a_local_app",
                    "detail": "start_url must be /pwa/nuxel-apps/<app>/index.html"}
        if sha256 and not re.match(r"^[0-9a-f]{64}$", sha256):
            return {"success": False, "error": "invalid_sha256"}
        p = _resolve_web_path(start_url or "")
        if not p or not p.is_file():
            return {"success": False, "error": "start_url_missing",
                    "detail": "the start URL does not resolve to a file under %s" % WEBROOT}
        manifest = p.parent / "manifest.json"
        if not manifest.is_file():
            return {"success": False, "error": "manifest_missing"}
        try:
            m = json.loads(manifest.read_text())
        except (OSError, ValueError):
            return {"success": False, "error": "manifest_invalid"}
        declared = (m.get("nuxel") or {}).get("capabilities")
        caps = list(capabilities or declared or [])
        with self._lock:
            doc = self.load()
            apps = _dedupe_and_migrate(doc.get("apps", []))
            existing = next((a for a in apps if a.get("id") == aid), None)
            entry = dict(existing or {})
            entry.update({
                "id": aid,
                "name": name or m.get("name") or aid,
                "icon": entry.get("icon") or "📱",
                "color": entry.get("color") or "#4a90e2",
                "category": entry.get("category") or "tools",
                "type": "pwa",
                "url": start_url,
                "description": entry.get("description") or (m.get("description") or ""),
                "capabilities": caps,
                "bridge_version": (m.get("nuxel") or {}).get("bridge_version", "1"),
                "docked": bool(entry.get("docked", False)),
                "status": "installed",
                "install_source": start_url,
                "installed_version": version or m.get("version") or "",
                "installed_sha256": sha256,
                "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            })
            if existing:
                apps = [entry if a.get("id") == aid else a for a in apps]
            else:
                apps.append(entry)
            doc["apps"] = apps
            self.save(doc)
            return {"success": True, "app_id": aid, "registered": True,
                    "state": app_state(entry), "registry_version": doc["registry_version"]}

    def unregister(self, app_id: str, purge_data: bool = False) -> Dict[str, Any]:
        aid = canonical_id(app_id or "")
        if not APP_ID_RE.match(aid):
            return {"success": False, "error": "invalid_app_id"}
        if purge_data:
            # Removal defaults to preserving user data.  A separate explicit
            # flag is required for data purge; this mission's UI never sets it.
            pass
        with self._lock:
            doc = self.load()
            apps = _dedupe_and_migrate(doc.get("apps", []))
            kept = [a for a in apps if a.get("id") != aid]
            if len(kept) == len(apps):
                return {"success": False, "error": "not_registered", "app_id": aid}
            doc["apps"] = kept
            self.save(doc)
            return {"success": True, "app_id": aid, "unregistered": True,
                    "payload_preserved": True, "user_data_preserved": True,
                    "registry_version": doc["registry_version"]}

    def reconcile(self) -> Dict[str, Any]:
        """Register shipped catalog apps that have complete payloads.

        This is repair, not installation: it never copies files, never touches
        user data and never marks an incomplete app installed.
        """
        with self._lock:
            doc = self.load()
            apps = _dedupe_and_migrate(doc.get("apps", []))
            known = {a.get("id") for a in apps}
            added = []
            for aid, meta in CATALOG_DEFAULTS.items():
                if aid in known:
                    continue
                p = _resolve_web_path(meta["url"])
                if not p or not p.is_file() or not (p.parent / "manifest.json").is_file():
                    continue
                apps.append({
                    "id": aid, "name": meta["name"], "icon": meta["icon"],
                    "color": "#4a90e2", "category": meta["category"], "type": "pwa",
                    "url": meta["url"], "description": meta["name"],
                    "capabilities": meta.get("capabilities", []), "bridge_version": "1",
                    "docked": False, "status": "installed",
                })
                added.append(aid)
            if added:
                doc["apps"] = apps
                self.save(doc)
            return {"success": True, "added": added, "count": len(added),
                    "registry_version": doc.get("registry_version")}


_MANAGER: Optional[AppManager] = None


def get_manager() -> AppManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = AppManager()
    return _MANAGER


def handle(verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    m = get_manager()
    if verb in ("inventory", "list", "reconcile"):
        if verb == "reconcile":
            r = m.reconcile()
            return r
        ids = params.get("ids")
        return m.inventory(ids if isinstance(ids, list) else None)
    if verb in ("register", "install"):
        return m.register(
            str(params.get("app_id", "")), str(params.get("name", "")),
            str(params.get("start_url", "")), str(params.get("version", "")),
            str(params.get("sha256", "")), params.get("capabilities"),
            str(params.get("app_dir", "")))
    if verb in ("unregister", "remove"):
        return m.unregister(str(params.get("app_id", "")),
                            bool(params.get("purge_data", False)))
    if verb == "resolve":
        app = m.find(str(params.get("app_id", "")))
        if not app:
            return {"success": False, "error": "not_registered"}
        return {"success": True, "app": app, "state": app_state(app)}
    return {"success": False, "error": "unknown apps verb", "verb": verb}

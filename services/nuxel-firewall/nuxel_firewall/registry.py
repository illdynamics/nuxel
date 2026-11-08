"""Canonical installed-app inventory (merge, do not duplicate)."""
import json
import os


def _load(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def canonical_apps():
    """Merge launcher registry + native app registry by stable app id."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    launcher = _load(os.path.join(root, "pwa", "nuxel-common", "app-registry.json")) or {}
    native = _load(os.path.join(root, "configs", "nuxel", "app-registry",
                                "app_registry.json")) or {}
    if not native:
        native = _load("/etc/nuxel/app-registry/app_registry.json") or {}
    if not launcher:
        launcher = _load("/etc/nuxel/app-registry/app_registry.json") or {}
    merged = {}
    for app in launcher.get("apps", []):
        app_id = app.get("id")
        if app_id:
            merged.setdefault(app_id, {}).update({
                "app_id": app_id,
                "name": app.get("name", app_id),
                "type": app.get("type", "unknown"),
                "category": app.get("category", "other"),
                "status": app.get("status", "unknown"),
            })
    for app in native.get("apps", []):
        app_id = app.get("app_id")
        if not app_id:
            continue
        entry = merged.setdefault(app_id, {"app_id": app_id, "name": app.get("name", app_id)})
        entry.update({
            "type": app.get("type", entry.get("type", "unknown")),
            "executable": app.get("executable"),
            "cgroup_name": app.get("cgroup_name"),
            "cgroup_classid": app.get("cgroup_classid"),
            "network_class": app.get("network_class"),
        })
    return list(merged.values())


def classid_collisions(apps):
    """Detect duplicate non-null cgroup_classid values."""
    seen = {}
    collisions = {}
    for app in apps:
        cid = app.get("cgroup_classid")
        if cid is None:
            continue
        seen.setdefault(cid, []).append(app["app_id"])
    for cid, ids in seen.items():
        if len(ids) > 1:
            collisions[cid] = ids
    return collisions

"""Nuxel Home — App Registry Model

Loads app definitions from app_registry.json (canonical source),
falling back to hardcoded APP_DEFINITIONS if the JSON is missing.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

ORDER_FILE = os.path.expanduser("~/.config/nuxel/home-order.json")

APP_DEFINITIONS = [
    # ── 5 PWA apps ──────────────────────────────────────────────
    {
        "id": "org.nuxel.Notes",
        "name": "Notes",
        "icon": "📝",
        "color": "#607D8B",
        "category": "productivity",
        "kind": "pwa",
        "url": "http://127.0.0.1:8000/pwa/nuxel-apps/notes/index.html",
        "description": "Take notes",
        "capabilities": [],
    },
    {
        "id": "org.nuxel.Files",
        "name": "Files",
        "icon": "📁",
        "color": "#3F51B5",
        "category": "tools",
        "kind": "pwa",
        "url": "http://127.0.0.1:8000/pwa/nuxel-apps/files/index.html",
        "description": "File browser",
        "capabilities": [],
    },
    {
        "id": "org.nuxel.Calendar",
        "name": "Calendar",
        "icon": "📅",
        "color": "#E91E63",
        "category": "productivity",
        "kind": "pwa",
        "url": "http://127.0.0.1:8000/pwa/nuxel-apps/calendar/index.html",
        "description": "Calendar and events",
        "capabilities": ["notifications:send"],
    },
    {
        "id": "org.nuxel.Mail",
        "name": "Mail",
        "icon": "✉️",
        "color": "#FF9800",
        "category": "productivity",
        "kind": "pwa",
        "url": "http://127.0.0.1:8000/pwa/nuxel-apps/mail/index.html",
        "description": "Email client",
        "capabilities": ["notifications:send", "notifications:receive"],
    },
    {
        "id": "org.nuxel.Camera",
        "name": "Camera",
        "icon": "📷",
        "color": "#795548",
        "category": "media",
        "kind": "pwa",
        "url": "http://127.0.0.1:8000/pwa/nuxel-apps/camera-gallery/index.html",
        "description": "Take photos and browse gallery",
        "capabilities": ["camera:capture"],
    },
    # ── 4 native-placeholder apps ───────────────────────────────
    {
        "id": "org.nuxel.Settings",
        "name": "Settings",
        "icon": "⚙️",
        "color": "#78909C",
        "category": "system",
        "kind": "native-placeholder",
        "url": "",
        "description": "System settings",
        "capabilities": [],
    },
    {
        "id": "org.nuxel.Phone",
        "name": "Phone",
        "icon": "📞",
        "color": "#4CAF50",
        "category": "communication",
        "kind": "native-placeholder",
        "url": "",
        "description": "Make phone calls",
        "capabilities": ["call:initiate", "call:end"],
    },
    {
        "id": "org.nuxel.Messages",
        "name": "Messages",
        "icon": "💬",
        "color": "#2196F3",
        "category": "communication",
        "kind": "native-placeholder",
        "url": "",
        "description": "Send and receive messages",
        "capabilities": ["sms:send", "sms:receive"],
    },
    {
        "id": "org.nuxel.Contacts",
        "name": "Contacts",
        "icon": "👤",
        "color": "#9C27B0",
        "category": "communication",
        "kind": "native-placeholder",
        "url": "",
        "description": "Manage your contacts",
        "capabilities": ["contacts:read", "contacts:write"],
    },
]

# Path to the canonical app registry JSON
_REGISTRY_JSON = os.path.join(os.path.dirname(__file__), 'app_registry.json')


def _load_registry_json():
    """Try to load app definitions from app_registry.json.

    Returns list of app dicts on success, None on failure.
    """
    if not os.path.exists(_REGISTRY_JSON):
        logger.debug("app_registry.json not found — using hardcoded definitions")
        return None

    try:
        with open(_REGISTRY_JSON, 'r') as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to parse app_registry.json: %s — falling back", exc)
        return None

    apps = data.get('apps', [])
    version = data.get('version', 'unknown')

    if not apps:
        logger.warning("app_registry.json has no apps — falling back")
        return None

    # Normalize: ensure every app dict has all required fields
    normalized = []
    for app in apps:
        normalized.append({
            "id": app.get("id", ""),
            "name": app.get("name", app.get("id", "")),
            "icon": app.get("icon", "📱"),
            "color": app.get("color", "#607D8B"),
            "category": app.get("category", "other"),
            "kind": app.get("kind", "pwa"),
            "url": app.get("url", ""),
            "native_binary": app.get("native_binary"),
            "description": app.get("description", ""),
            "capabilities": app.get("capabilities", []),
        })

    logger.info("Loaded %d apps from app_registry.json v%s", len(normalized), version)
    return normalized


class AppRegistry:
    """Manages app definitions and persistent drag-reorder state."""

    def __init__(self):
        # Load canonical JSON first, fall back to hardcoded definitions
        definitions = _load_registry_json()
        if definitions is None:
            definitions = APP_DEFINITIONS

        self._apps = {a["id"]: AppDef(
            id=a.get("id", ""),
            name=a.get("name", a.get("id", "")),
            icon=a.get("icon", "📱"),
            color=a.get("color", "#607D8B"),
            category=a.get("category", "other"),
            kind=a.get("kind", "pwa"),
            url=a.get("url", ""),
            native_binary=a.get("native_binary"),
            description=a.get("description", ""),
            capabilities=a.get("capabilities", []),
        ) for a in definitions}

        self._order = None  # list of app IDs in user's preferred order
        self._load_order()

    # ── accessors ────────────────────────────────────────────────

    def get_all(self):
        """Return apps in user's preferred order, then remaining by default order."""
        ordered = []
        remaining = list(self._apps.values())

        if self._order:
            order_map = {app_id: i for i, app_id in enumerate(self._order)}
            ordered = sorted(
                [a for a in remaining if a.id in order_map],
                key=lambda a: order_map[a.id],
            )
            remaining = [a for a in remaining if a.id not in order_map]

        return ordered + remaining

    def get(self, app_id):
        return self._apps.get(app_id)

    # ── dynamic registry (runtime add/remove) ────────────────────

    def _persist(self):
        """Write the current registry back to app_registry.json."""
        apps = []
        for app in self._apps.values():
            apps.append({
                "id": app.id,
                "name": app.name,
                "icon": app.icon,
                "color": app.color,
                "category": app.category,
                "kind": app.kind,
                "url": app.url,
                "native_binary": app.native_binary,
                "description": getattr(app, "description", ""),
                "capabilities": list(app.capabilities),
            })
        payload = {"version": "1.0.0", "apps": apps}
        try:
            with open(_REGISTRY_JSON, "w") as fh:
                json.dump(payload, fh, indent=2)
            logger.info("Persisted %d apps to %s", len(apps), _REGISTRY_JSON)
        except OSError as exc:
            logger.error("Failed to persist app registry: %s", exc)

    def add_app(self, defn):
        """Register a new app at runtime and persist it.

        `defn` is a dict (or AppDef) with the same shape as entries in
        app_registry.json. If the app already exists its definition is updated
        (state implicitly transitions from uninstalled -> installed).
        """
        if isinstance(defn, AppDef):
            app = defn
        else:
            app = AppDef(
                id=defn.get("id", ""),
                name=defn.get("name", defn.get("id", "")),
                icon=defn.get("icon", "📱"),
                color=defn.get("color", "#607D8B"),
                category=defn.get("category", "other"),
                kind=defn.get("kind", "pwa"),
                url=defn.get("url", ""),
                native_binary=defn.get("native_binary"),
                description=defn.get("description", ""),
                capabilities=defn.get("capabilities", []),
            )
        if not app.id:
            raise ValueError("App def without id cannot be added")
        self._apps[app.id] = app
        self._persist()
        return app

    def remove_app(self, app_id):
        """Unregister an app at runtime and persist it.

        Returns True if the app existed and was removed, False otherwise.
        """
        if app_id not in self._apps:
            logger.warning("remove_app: %s not in registry", app_id)
            return False
        del self._apps[app_id]
        if self._order and app_id in self._order:
            self._order = [a for a in self._order if a != app_id]
            self.save_order(self._order)
        self._persist()
        return True

    @staticmethod
    def wipe_app_data(app_id):
        """Delete the per-app data directory for the given PWA.

        Data lives under ~/.local/share/nuxel/apps/<app_id>.
        Returns True if something was removed, False otherwise.
        """
        base = os.path.expanduser("~/.local/share/nuxel/apps")
        target = os.path.join(base, app_id)
        if not os.path.exists(target):
            logger.info("wipe_app_data: no data dir for %s", app_id)
            return False
        try:
            import shutil
            shutil.rmtree(target)
            logger.info("Wiped app data for %s at %s", app_id, target)
            return True
        except OSError as exc:
            logger.error("Failed to wipe app data for %s: %s", app_id, exc)
            return False

    def __len__(self):
        return len(self._apps)

    def __iter__(self):
        return iter(self.get_all())

    # ── order persistence ────────────────────────────────────────

    def _load_order(self):
        if not os.path.exists(ORDER_FILE):
            return
        try:
            with open(ORDER_FILE, "r") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                self._order = data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load app order: %s", exc)

    def save_order(self, order_ids):
        """Persist the current order to disk."""
        os.makedirs(os.path.dirname(ORDER_FILE), exist_ok=True)
        try:
            with open(ORDER_FILE, "w") as fh:
                json.dump(order_ids, fh, indent=2)
            self._order = order_ids
        except OSError as exc:
            logger.error("Failed to save app order: %s", exc)

    def reset_order(self):
        """Clear saved order and use defaults."""
        self._order = None
        try:
            if os.path.exists(ORDER_FILE):
                os.remove(ORDER_FILE)
        except OSError as exc:
            logger.warning("Failed to remove order file: %s", exc)


class AppDef:
    """Immutable app definition."""

    __slots__ = (
        "id", "name", "icon", "color", "category",
        "kind", "url", "native_binary", "description", "capabilities",
    )

    def __init__(self, **kw):
        for slot in self.__slots__:
            setattr(self, slot, kw.get(slot, ""))
        self.capabilities = list(kw.get("capabilities", []))
        self.native_binary = kw.get("native_binary")

    def is_pwa(self):
        return self.kind == "pwa"

    def is_native_placeholder(self):
        return self.kind == "native-placeholder"

    def __repr__(self):
        return f"<AppDef {self.id}: {self.name} ({self.kind})>"

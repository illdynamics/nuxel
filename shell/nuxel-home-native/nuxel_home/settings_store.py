"""Nuxel Home — Settings Store

Reads and writes JSON config files from ~/.config/nuxel/.
Provides get(key, default) and set(key, value) for arbitrary
flat-string settings. Used by app_model for order persistence
and can be extended for other config needs.

File layout:
  ~/.config/nuxel/
    home-order.json   (managed by AppRegistry)
    home-settings.json (managed by SettingsStore)
"""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

SETTINGS_DIR = os.path.expanduser("~/.config/nuxel")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "home-settings.json")


class SettingsStore:
    """Simple JSON key-value store for home-settings.json.

    Thread-safe for GLib main-loop usage (no locks needed since
    all reads/writes happen in the same main-loop thread).
    """

    def __init__(self, path: str = SETTINGS_FILE):
        self._path = path
        self._data: Dict[str, Any] = {}
        self._dirty = False
        self._load()

    # ── Public API ───────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Read a value from the settings store."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Write a value and persist to disk immediately."""
        self._data[key] = value
        self._dirty = True
        self._save()

    def delete(self, key: str) -> None:
        """Remove a key from the store."""
        self._data.pop(key, None)
        self._dirty = True
        self._save()

    def keys(self) -> Dict[str, Any]:
        """Return a shallow copy of all settings."""
        return dict(self._data)

    def clear(self) -> None:
        """Reset all settings and persist."""
        self._data.clear()
        self._dirty = True
        self._save()

    # ── Internal ─────────────────────────────────────────────────

    def _load(self) -> None:
        """Load settings from disk, creating defaults if missing."""
        if not os.path.exists(self._path):
            logger.debug("Settings file not found at %s, using defaults", self._path)
            self._data = {}
            return

        try:
            with open(self._path, "r") as fh:
                self._data = json.load(fh)
            if not isinstance(self._data, dict):
                logger.warning("Settings file is not a dict, resetting")
                self._data = {}
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load settings: %s", exc)
            self._data = {}

    def _save(self) -> None:
        """Flush data to disk atomically."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        tmp_path = self._path + ".tmp"
        try:
            with open(tmp_path, "w") as fh:
                json.dump(self._data, fh, indent=2, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, self._path)
        except OSError as exc:
            logger.error("Failed to save settings: %s", exc)
        self._dirty = False

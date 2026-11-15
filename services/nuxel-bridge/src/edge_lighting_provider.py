#!/usr/bin/env python3
"""Canonical Nuxel Edge Lighting controller (PWNAGE-103000).

This module is the SINGLE owner of Edge Lighting *policy state*.  It is a
presentation-only controller:

  * It never writes an LED node.  The S10+ has no notification/RGB LED; the
    effect is an AMOLED display overlay rendered by Home (the one WebView
    owner), never by a framebuffer writer and never by the camera flash.
  * It never mutates notification state (no read/archive/dismiss).
  * It implements the eight S10-style effects (basic, wave, bubble, multicolor,
    heart, fireworks, eclipse, echo), Wave as the persisted default, the Nuxel
    theme accent as the default colour, DND / reduced-motion / per-app policy,
    duration + width/intensity/transparency controls, capability reporting and
    a safe preview that does NOT ingest a burst (so it cannot be used to flood
    the real notification path).

Event flow (one real notification -> one bounded animation):

    org.nuxel.Notifications (system bus) --NotificationAdded--> bridge watch
        -> handle("event", payload)  (pure: validation, coalescing, policy)
        -> journal append           (/var/lib/nuxel/edge-lighting/events.jsonl)
        -> Home polls the bounded journal (GET /api/v1/edge-lighting/events)
           and runs ONE cancellable animation per accepted event.

The notification record itself is the deduplication key: the hub re-emits the
same record id for a replace/progress update, so one record produces at most
one animation within DEDUP_WINDOW_MS.  A different record id inside the
coalesce window is folded into the already-running animation instead of
spawning a second one.

Files (overridable for offline tests):
  NUXEL_EDGE_CONFIG   /var/lib/nuxel/edge-lighting/settings.json   (user settings)
  NUXEL_EDGE_POLICY   /etc/nuxel/edge-lighting/edge-lighting.json  (shipped default)
  NUXEL_EDGE_STATE    /var/lib/nuxel/edge-lighting/state.json      (status)
  NUXEL_EDGE_JOURNAL  /var/lib/nuxel/edge-lighting/events.jsonl    (events)
  NUXEL_DND_STATE     /var/lib/nuxel/notifications/dnd.json        (read-only)
  NUXEL_APP_REGISTRY  /etc/nuxel/app-registry/app_registry.json    (read-only)

Why the settings document lives under /var/lib: the HTTP bridge unit runs with
ProtectSystem=strict and only /var/lib/nuxel (plus a few explicit /etc paths)
is writable.  /etc/nuxel/edge-lighting is the read-only shipped default, exactly
like other Nuxel policy files; the user's chosen effect/colour/duration must
persist, so it is stored in the writable data directory and SEEDED from the
shipped default on a clean profile and on upgrade.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_POLICY_PATH = "/etc/nuxel/edge-lighting/edge-lighting.json"
DEFAULT_CONFIG = "/var/lib/nuxel/edge-lighting/settings.json"
DEFAULT_STATE = "/var/lib/nuxel/edge-lighting/state.json"
DEFAULT_JOURNAL = "/var/lib/nuxel/edge-lighting/events.jsonl"
DEFAULT_DND_STATE = "/var/lib/nuxel/notifications/dnd.json"
DEFAULT_APP_REGISTRY = "/etc/nuxel/app-registry/app_registry.json"

SCHEMA_VERSION = 1
EFFECTS: Tuple[str, ...] = ("basic", "wave", "bubble", "multicolor",
                            "heart", "fireworks", "eclipse", "echo")
WIDTHS: Tuple[str, ...] = ("thin", "medium", "wide")
TRANSPARENCIES: Tuple[str, ...] = ("low", "medium", "high")
SCREEN_MODES: Tuple[str, ...] = ("screen_on",)          # only proven mode
UNAVAILABLE_SCREEN_MODES = ("screen_off", "always")
COLOR_MODES: Tuple[str, ...] = ("theme", "preset", "custom", "app")
DEFAULT_ACCENT = "#63f0bd"                              # theme fallback only
DURATION_MIN_MS = 600
DURATION_MAX_MS = 6000
DURATION_DEFAULT_MS = 1800
DEDUP_WINDOW_MS = 1500          # same record id: one animation
COALESCE_WINDOW_MS = 700        # other record id while one runs: fold in
PENDING_TTL_S = 20              # undelivered events expire (never replay old alerts)
JOURNAL_MAX_BYTES = 96 * 1024
JOURNAL_KEEP_BYTES = 48 * 1024
MAX_PENDING = 8

DEFAULTS: Dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "enabled": True,
    "effect": "wave",
    "color_mode": "theme",
    "color": None,
    "width": "medium",
    "transparency": "medium",
    "duration_ms": DURATION_DEFAULT_MS,
    "screen_mode": "screen_on",
    "respect_dnd": True,
    "respect_reduced_motion": True,
    "reduced_motion_style": "static",
    "source_mode": "all",        # all | allowlist (explicit, survives re-render)
    "allowed_apps": [],          # used when source_mode == allowlist
    "blocked_apps": [],
    # Lifecycle toggles (PWNAGE-SSP).  Each is independent.  The configured
    # Nuxel behaviour (owner, 2026-11-14) is: waking the panel and unlocking
    # play the configured Edge FX.  A stored document still wins for every key
    # it carries; absent keys resolve to this default.  They are evaluated by
    # nuxel-home's edge renderer on the real session events; a mode the stack
    # cannot animate is reported unavailable rather than silently ignored.
    "lifecycle": {
        "screen_on": True,       # brief edge pulse when the panel comes on
        "screen_off": False,     # edge pulse before the panel blanks
        "lock": False,           # edge pulse when the lockscreen locks
        "unlock": True,          # edge pulse when the lockscreen unlocks
    },
}

LIFECYCLE_KEYS: Tuple[str, ...] = ("screen_on", "screen_off", "lock", "unlock")


# ---------------------------------------------------------------- helpers ----
def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r") as fh:
            doc = json.load(fh)
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def _atomic_json(path: str, doc: Dict[str, Any]) -> bool:
    d = os.path.dirname(path) or "."
    try:
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".edge-", dir=d)
        try:
            os.fchmod(fd, 0o644)
            with os.fdopen(fd, "w") as fh:
                json.dump(doc, fh, sort_keys=True, indent=2)
                fh.write("\n")
            os.replace(tmp, path)
            os.chmod(path, 0o644)
            return True
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    except OSError:
        return False


def _valid_color(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    v = value.strip()
    if len(v) == 7 and v[0] == "#":
        try:
            int(v[1:], 16)
            return v.lower()
        except ValueError:
            return None
    return None


def _bounded_int(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _safe_str(value: Any, limit: int = 200) -> str:
    if value is None:
        return ""
    s = str(value)
    # Strip control characters so a hostile summary cannot break the journal.
    s = "".join(ch for ch in s if ch >= " " and ch != "\x7f")
    return s[:limit]


class EdgeLightingProvider:
    def __init__(self) -> None:
        self.config_path = os.environ.get("NUXEL_EDGE_CONFIG", DEFAULT_CONFIG)
        self.policy_path = os.environ.get("NUXEL_EDGE_POLICY", DEFAULT_POLICY_PATH)
        self.state_path = os.environ.get("NUXEL_EDGE_STATE", DEFAULT_STATE)
        self.journal_path = os.environ.get("NUXEL_EDGE_JOURNAL", DEFAULT_JOURNAL)
        self.dnd_path = os.environ.get("NUXEL_DND_STATE", DEFAULT_DND_STATE)
        self.registry_path = os.environ.get("NUXEL_APP_REGISTRY", DEFAULT_APP_REGISTRY)
        self._lock = threading.RLock()
        self._seq = 0
        self._pending: List[Dict[str, Any]] = []
        self._last_record: Dict[str, float] = {}
        self._last_accept_at = 0.0
        self._last_event: Dict[str, Any] = {}
        self._stats = {"accepted": 0, "folded": 0, "deduped": 0, "suppressed": 0}
        self._last_error: Optional[str] = None
        self._config = self._load_config()
        if self._config.get("config_source") in ("defaults", "shipped-default"):
            # Materialise the clean-profile default (Wave, theme accent) so the
            # persisted user document exists from first boot and survives
            # upgrades and service-worker reloads.
            self._save_config()
        self._recover_seq()
        self._rotate_journal_if_needed()

    # ---------------------------------------------------------- config ----
    def _load_config(self) -> Dict[str, Any]:
        raw = _read_json(self.config_path)
        if raw:
            return self._normalise(raw, source="file")
        # Clean profile / upgrade: seed the user document from the shipped
        # policy default (Wave, theme accent, 1800 ms) without overwriting a
        # user document that already exists.
        shipped = _read_json(self.policy_path)
        return self._normalise(shipped, source="shipped-default" if shipped else "defaults")

    def _normalise(self, raw: Dict[str, Any], source: str = "patch") -> Dict[str, Any]:
        merged = dict(DEFAULTS)
        merged.update({k: v for k, v in (raw or {}).items() if k in DEFAULTS})
        effect = str(merged.get("effect") or "wave").lower()
        merged["effect"] = effect if effect in EFFECTS else "wave"
        mode = str(merged.get("color_mode") or "theme").lower()
        merged["color_mode"] = mode if mode in COLOR_MODES else "theme"
        color = _valid_color(merged.get("color"))
        merged["color"] = color
        if merged["color_mode"] in ("preset", "custom") and not color:
            # A colour mode without a real colour falls back to the theme.
            merged["color_mode"] = "theme"
        width = str(merged.get("width") or "medium").lower()
        merged["width"] = width if width in WIDTHS else "medium"
        tr = str(merged.get("transparency") or "medium").lower()
        merged["transparency"] = tr if tr in TRANSPARENCIES else "medium"
        merged["duration_ms"] = _bounded_int(merged.get("duration_ms"),
                                             DURATION_DEFAULT_MS, DURATION_MIN_MS, DURATION_MAX_MS)
        merged["screen_mode"] = "screen_on"
        merged["enabled"] = bool(merged.get("enabled", True))
        merged["respect_dnd"] = bool(merged.get("respect_dnd", True))
        merged["respect_reduced_motion"] = bool(merged.get("respect_reduced_motion", True))
        rm = str(merged.get("reduced_motion_style") or "static").lower()
        merged["reduced_motion_style"] = rm if rm in ("static", "off") else "static"
        for key in ("allowed_apps", "blocked_apps"):
            vals = merged.get(key)
            if not isinstance(vals, list):
                vals = []
            merged[key] = sorted({_safe_str(v, 128) for v in vals if _safe_str(v, 128)})
        # Lifecycle toggles are strict booleans.  An unknown key from a newer
        # revision is preserved inside the document but never guessed ON; a
        # string "false" (from a sloppy form post) is not truthy either.
        lc_raw = merged.get("lifecycle")
        if not isinstance(lc_raw, dict):
            lc_raw = {}
        lc = dict(DEFAULTS["lifecycle"])
        for k in LIFECYCLE_KEYS:
            if k in DEFAULTS["lifecycle"] and lc_raw.get(k) is None:
                # An explicit null (or an absent key) is "not configured":
                # resolve it to the configured default instead of OFF.
                continue
            if isinstance(lc_raw.get(k), bool):
                lc[k] = lc_raw[k]
        merged["lifecycle"] = lc
        # Backwards compatible migration: an older document with a non-empty
        # allowlist was in allowlist mode; an empty one meant all apps.  The
        # explicit source_mode lets the UI distinguish "filter off" from "all
        # 48 apps happen to be selected" and keeps Allow-all idempotent.
        # The base DEFAULTS already carries source_mode=all, so look at the
        # caller's document, not the merged dict, to detect a legacy file.
        raw_mode = str((raw or {}).get("source_mode") or "").lower()
        if raw_mode in ("all", "allowlist"):
            merged["source_mode"] = raw_mode
        else:
            merged["source_mode"] = "allowlist" if merged.get("allowed_apps") else "all"
        if merged["source_mode"] == "allowlist" and not merged.get("allowed_apps"):
            merged["source_mode"] = "all"
        merged["schema_version"] = SCHEMA_VERSION
        merged["config_source"] = source
        return merged

    def _writable(self) -> bool:
        d = os.path.dirname(self.config_path) or "."
        try:
            if not os.path.isdir(d):
                os.makedirs(d, exist_ok=True)
            return os.access(d, os.W_OK)
        except OSError:
            return False

    def _save_config(self) -> bool:
        doc = dict(self._config)
        doc["updated_at"] = int(time.time())
        return _atomic_json(self.config_path, doc)

    # ------------------------------------------------------- capability ----
    def _registry_ids(self) -> set:
        doc = _read_json(self.registry_path)
        apps = doc.get("apps") if isinstance(doc.get("apps"), list) else []
        ids = set()
        for app in apps:
            if isinstance(app, dict) and app.get("id"):
                ids.add(str(app["id"]))
        return ids

    def _dnd(self) -> Dict[str, Any]:
        doc = _read_json(self.dnd_path)
        active = bool(doc.get("enabled", False))
        return {"active": active, "reason": doc.get("reason") or ("manual" if active else "off"),
                "source": self.dnd_path}

    def capability(self) -> Dict[str, Any]:
        """Honest capability model, derived from the actual display bridge."""
        screen_on = True    # Home renders the overlay in the on-screen WebView.
        # Screen-off edge lighting needs an edge-only, low-power render path that
        # can run while the panel is blanked.  This stack has none (the display
        # bridge copies the full Wayland surface to fb0; the panel backlight is
        # controlled separately), so it is reported, not promised.
        screen_off_reason = ("NOT_SUPPORTED_BY_CURRENT_DISPLAY_STACK: the PWA overlay "
                             "only renders while the WebView and panel are on; there is no "
                             "edge-only low-power render path")
        return {
            "effect_family": list(EFFECTS),
            "effects_supported": list(EFFECTS),
            "effects_unavailable": [],
            "default_effect": "wave",
            "screen_modes": [{"id": "screen_on", "available": True,
                              "label": "While screen is on"},
                             {"id": "screen_off", "available": False,
                              "label": "While screen is off", "reason": screen_off_reason},
                             {"id": "always", "available": False,
                              "label": "Always", "reason": screen_off_reason,
                              "depends_on": "screen_off"}],
            "renderer": {"owner": "nuxel-home", "kind": "dom_overlay",
                         "framebuffer_writes": False, "second_compositor": False,
                         "hardware_led": False, "camera_flash": False},
            "notification_led": {"present": False,
                                 "label": "No notification/RGB LED on this device"},
            "color_model": {"modes": list(COLOR_MODES), "default_accent": DEFAULT_ACCENT,
                            "custom": "hex"},
            "reduced_motion_default": "static",
            "screen_on_label": "AMOLED display effect (not a physical LED)",
            # Lifecycle toggles are per-event animations rendered by Home while
            # the WebView is on screen.  screen_on/lock/unlock happen with the
            # panel and WebView already awake; screen_off is reported
            # available only when a pre-blank animation window exists.
            "lifecycle": {
                "screen_on": {"available": True},
                "screen_off": {"available": True,
                               "reason": "animated during the display blank-out window; "
                                         "not visible after the panel is fully off"},
                "lock": {"available": True},
                "unlock": {"available": True},
            },
        }

    # ----------------------------------------------------------- status ----
    def status(self) -> Dict[str, Any]:
        with self._lock:
            cfg = dict(self._config)
            cap = self.capability()
            dnd = self._dnd()
            return {
                "success": True,
                "schema_version": SCHEMA_VERSION,
                "config": cfg,
                "settings_path": self.config_path,
                "policy_path": self.policy_path,
                "defaults": dict(DEFAULTS),
                "persistence": {"writable": os.access(os.path.dirname(self.config_path) or ".", os.W_OK),
                                "kind": "user document under /var/lib (survives reboot)"},
                "capability": cap,
                "dnd": dnd,
                "pending": len(self._pending),
                "last_seq": self._seq,
                "stats": dict(self._stats),
                "last_event": self._last_event or None,
                "last_error": self._last_error,
                "source": "edge_lighting_provider",
            }

    # ---------------------------------------------------------- policy ----
    def _app_allowed(self, app_id: str) -> Tuple[bool, str]:
        allowed = self._config.get("allowed_apps") or []
        if self._config.get("source_mode", "all") == "all":
            allowed = []
        blocked = self._config.get("blocked_apps") or []
        if app_id and app_id in blocked:
            return False, "blocked_app"
        if allowed and app_id not in allowed:
            return False, "not_in_allowlist"
        return True, "allowed"

    def _evaluate(self, doc: Dict[str, Any]) -> Tuple[bool, str]:
        """Pure policy gate for a real notification record (no side effects)."""
        if not self._config.get("enabled", True):
            return False, "disabled"
        app_id = _safe_str(doc.get("app_id"), 128)
        allowed, why = self._app_allowed(app_id)
        if not allowed:
            return False, why
        if self._config.get("respect_dnd", True) and self._dnd()["active"]:
            return False, "dnd"
        if self._config.get("screen_mode", "screen_on") != "screen_on":
            # The schema is clamped to screen_on; this branch is a guard only.
            return False, "screen_mode_unsupported"
        return True, "accepted"

    # ---------------------------------------------------------- journal ----
    def _recover_seq(self) -> None:
        try:
            with open(self.journal_path, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                fh.seek(max(0, size - 8192))
                tail = fh.read().decode("utf-8", "replace").splitlines()
            for line in reversed(tail):
                try:
                    self._seq = max(self._seq, int(json.loads(line).get("seq") or 0))
                except (ValueError, TypeError):
                    continue
                break
        except OSError:
            pass

    def _rotate_journal_if_needed(self) -> None:
        """Keep only the tail of the journal; a malformed tail is dropped.

        Rotation is deterministic on provider construction and before each
        append, so a journal that was cut or corrupted is repaired even when no
        new event ever arrives.
        """
        try:
            if os.path.getsize(self.journal_path) <= JOURNAL_MAX_BYTES:
                return
            with open(self.journal_path, "rb") as fh:
                fh.seek(-JOURNAL_KEEP_BYTES, os.SEEK_END)
                keep = fh.read().split(b"\n", 1)[-1]
            # Keep only complete, valid JSON lines from the tail.
            kept_lines = []
            for line in keep.split(b"\n"):
                try:
                    json.loads(line.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    continue
                kept_lines.append(line)
            tmp = self.journal_path + ".tmp"
            with open(tmp, "wb") as fh:
                if kept_lines:
                    fh.write(b"\n".join(kept_lines[:MAX_PENDING]) + b"\n")
            os.replace(tmp, self.journal_path)
            os.chmod(self.journal_path, 0o644)
        except OSError:
            self._last_error = "journal rotation failed"

    def _append_journal(self, entry: Dict[str, Any]) -> None:
        try:
            d = os.path.dirname(self.journal_path) or "."
            os.makedirs(d, exist_ok=True)
            self._rotate_journal_if_needed()
            with open(self.journal_path, "a") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
            os.chmod(self.journal_path, 0o644)
        except OSError as exc:
            self._last_error = "journal write failed: %s" % exc

    # ------------------------------------------------------------ event ----
    def handle_event(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Accept a REAL notification record from the hub watch.  Idempotent."""
        with self._lock:
            if not isinstance(doc, dict):
                return {"success": False, "error": "event must be a JSON object"}
            ok, why = self._evaluate(doc)
            if not ok:
                self._stats["suppressed"] += 1
                return {"success": True, "accepted": False, "reason": why}
            try:
                rec_id = int(doc.get("id"))
            except (TypeError, ValueError):
                return {"success": False, "error": "notification id is required"}
            now = time.monotonic()
            last = self._last_record.get(str(rec_id), 0.0)
            if now - last < DEDUP_WINDOW_MS / 1000.0:
                self._stats["deduped"] += 1
                return {"success": True, "accepted": False, "reason": "duplicate_record"}
            self._last_record[str(rec_id)] = now
            # Prune the dedupe map; it must never grow without bound.
            if len(self._last_record) > 256:
                cutoff = now - 60.0
                self._last_record = {k: v for k, v in self._last_record.items() if v >= cutoff}
            if now - self._last_accept_at < COALESCE_WINDOW_MS / 1000.0:
                self._stats["folded"] += 1
                self._last_accept_at = now
                return {"success": True, "accepted": False, "reason": "coalesced",
                        "active_seq": self._seq}

            self._seq += 1
            self._last_accept_at = now
            self._stats["accepted"] += 1
            cfg = self._config
            # Non-sensitive display metadata only: app identity, category and
            # the chosen colour.  Summary/body/contact names never leave the hub.
            entry = {
                "seq": self._seq,
                "kind": "notification",
                "record_id": rec_id,
                "app_id": _safe_str(doc.get("app_id"), 128),
                # No app_name/summary/body/icon: an app_name is usually the
                # sender/contact label on many hubs.  The renderer resolves the
                # display name from the canonical registry by app_id.
                "category": _safe_str(doc.get("category") or _category_of(doc), 64),
                "urgency": _safe_str(doc.get("urgency") or "normal", 16),
                "effect": cfg["effect"],
                "color_mode": cfg["color_mode"],
                "color": cfg["color"],
                "width": cfg["width"],
                "transparency": cfg["transparency"],
                "duration_ms": cfg["duration_ms"],
                "reduced_motion_style": cfg["reduced_motion_style"],
                "created_at": int(time.time()),
            }
            self._last_event = {"seq": self._seq, "record_id": rec_id,
                                "app_id": entry["app_id"], "at": int(time.time())}
            self._append_journal(entry)
            return {"success": True, "accepted": True, "seq": self._seq,
                    "event": entry}

    # ---------------------------------------------------------- preview ----
    def preview(self, effect: Optional[str] = None, duration_ms: Optional[int] = None,
                color: Optional[str] = None) -> Dict[str, Any]:
        """A preview event: presentation only, never touches notification state.

        Previews are deliberately NOT deduplicated so the owner can compare
        effects back-to-back; like real events they are not journaled (there is
        no real notification behind them) and only one is pending at a time.
        """
        with self._lock:
            eff = str(effect or self._config["effect"]).lower()
            if eff not in EFFECTS:
                return {"success": False, "error": "unknown effect", "effects": list(EFFECTS)}
            dur = _bounded_int(duration_ms if duration_ms is not None else self._config["duration_ms"],
                               self._config["duration_ms"], DURATION_MIN_MS, DURATION_MAX_MS)
            col = _valid_color(color) if color else self._config.get("color")
            return {"success": True, "kind": "preview", "effect": eff,
                    "color": col, "color_mode": self._config["color_mode"],
                    "width": self._config["width"],
                    "transparency": self._config["transparency"],
                    "duration_ms": dur, "seq": self._seq,
                    "notification_state_changed": False,
                    "label": "Preview — no notification was created or changed"}

    # ------------------------------------------------------------- polls ----
    def events_since(self, since: int) -> Dict[str, Any]:
        """Return journal entries with seq > since.  Read-only, small, bounded."""
        with self._lock:
            since = _bounded_int(since, 0, 0, 2 ** 31)
            out: List[Dict[str, Any]] = []
            try:
                with open(self.journal_path, "r", errors="replace") as fh:
                    for line in fh:
                        try:
                            entry = json.loads(line)
                        except ValueError:
                            continue
                        if int(entry.get("seq") or 0) > since:
                            out.append(entry)
            except OSError:
                pass
            out = out[-MAX_PENDING:]
            return {"success": True, "events": out, "last_seq": self._seq}

    # ---------------------------------------------------------- settings ----
    def update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params = params or {}
        with self._lock:
            patch = {}
            for key in ("enabled", "effect", "color_mode", "color", "width",
                        "transparency", "duration_ms", "respect_dnd",
                        "respect_reduced_motion", "reduced_motion_style",
                        "source_mode", "allowed_apps", "blocked_apps",
                        "lifecycle"):
                if key in params:
                    patch[key] = params[key]
            if "lifecycle" in patch and not isinstance(patch["lifecycle"], dict):
                return {"success": False, "error": "lifecycle must be an object"}
            if "effect" in patch and str(patch["effect"]).lower() not in EFFECTS:
                return {"success": False, "error": "unknown effect",
                        "effects": list(EFFECTS)}
            if "color" in patch and patch["color"] not in (None, "", "theme"):
                if not _valid_color(patch["color"]):
                    return {"success": False, "error": "color must be #rrggbb or null"}
            if "duration_ms" in patch:
                try:
                    int(patch["duration_ms"])
                except (TypeError, ValueError):
                    return {"success": False, "error": "duration_ms must be an integer"}
            if "source_mode" in patch and str(patch["source_mode"]) not in ("all", "allowlist"):
                return {"success": False, "error": "source_mode must be all or allowlist"}
            if "source_mode" in patch and patch["source_mode"] == "all":
                # Explicit all-apps: clear the filter atomically with the mode.
                patch.setdefault("allowed_apps", [])
            if "allowed_apps" in patch or "blocked_apps" in patch:
                known = self._registry_ids()
                for key in ("allowed_apps", "blocked_apps"):
                    vals = patch.get(key)
                    if vals is None:
                        continue
                    if not isinstance(vals, list):
                        return {"success": False, "error": key + " must be a list"}
                    if known:
                        unknown = [v for v in vals if str(v) not in known]
                        if unknown:
                            return {"success": False, "error": "unknown app id in " + key,
                                    "unknown": unknown}
            merged_raw = dict(self._config, **patch)
            # A row-level edit that supplies a non-empty allowlist without an
            # explicit mode was an implicit allowlist in the old UI contract.
            if "allowed_apps" in patch and "source_mode" not in patch:
                merged_raw["source_mode"] = "allowlist" if patch["allowed_apps"] else "all"
            self._config = self._normalise(merged_raw, source="user")
            if not self._save_config():
                self._last_error = "settings write failed; change is in memory only"
                return {"success": False, "error": self._last_error, "config": self._config}
            return {"success": True, "config": self._config,
                    "persisted": self.config_path}

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._config = self._normalise({}, source="reset")
            if not self._save_config():
                return {"success": False, "error": "settings write failed",
                        "config": self._config}
            return {"success": True, "config": self._config, "persisted": self.config_path}


def _category_of(doc: Dict[str, Any]) -> str:
    hints = doc.get("hints") if isinstance(doc.get("hints"), dict) else {}
    return str(hints.get("category") or hints.get("x-nuxel-category") or "")


_PROVIDER: Optional[EdgeLightingProvider] = None


def get_provider() -> EdgeLightingProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = EdgeLightingProvider()
    return _PROVIDER


def handle(verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    p = get_provider()
    if verb in ("status", "get", "capability"):
        return p.status()
    if verb in ("set", "update", "save"):
        return p.update(params)
    if verb == "reset":
        return p.reset()
    if verb in ("preview", "test"):
        return p.preview(params.get("effect"), params.get("duration_ms"), params.get("color"))
    if verb == "events":
        return p.events_since(params.get("since", 0))
    if verb == "event":
        # Called by the canonical system-bus watch in api.py, never by a PWA.
        return p.handle_event(params)
    return {"success": False, "error": "unknown edge-lighting verb", "verb": verb}

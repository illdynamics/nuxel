#!/usr/bin/env python3
"""Shared Nuxel File Handler + FileChooser policy library (PWNAGE-97000).

This module is deliberately standard-library only.  It is imported by the
unprivileged XDG ``org.freedesktop.impl.portal.FileChooser`` backend, by the
root-owned HTTP bridge (Settings RPC), and by the command-line maintenance
tool.  Keeping one implementation means the Settings panel, the picker and the
MIME defaults can never disagree about the effective policy.

Two separate contracts are represented here and must never be conflated:

* picker policy (``global_picker_policy`` / ``app_picker_overrides``) tells the
  FileChooser backend which source to show first;
* MIME defaults (``mime_defaults`` + the user's ``mimeapps.list``) tell the
  desktop which application opens an existing file.

``org.nuxel.Portal`` is the hardware-permission broker.  It is not involved in
either contract.
"""
from __future__ import annotations

import fnmatch
import json
import mimetypes
import os
import pwd
import re
import stat
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SCHEMA_VERSION = 1
POLICIES = ("ask", "gallery", "files")
OVERRIDE_POLICIES = ("inherit",) + POLICIES
APP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@+-]{0,127}$")
DESKTOP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*\.desktop$")
MIME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]*$")

IMAGE_MIMES = (
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp",
    "image/tiff", "image/heic", "image/heif", "image/avif",
)
VIDEO_MIMES = (
    "video/mp4", "video/webm", "video/x-matroska", "video/quicktime",
    "video/x-m4v", "video/x-msvideo", "video/3gpp", "video/mpeg",
)
MEDIA_MIMES = IMAGE_MIMES + VIDEO_MIMES
GALLERY_MIMES = IMAGE_MIMES + VIDEO_MIMES
DIRECTORY_MIME = "inode/directory"

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".heif",
    ".avif", ".tif", ".tiff",
}
VIDEO_EXTS = {".mp4", ".webm", ".mkv", ".mov", ".m4v", ".avi", ".3gp", ".mpeg", ".mpg"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS

DEFAULT_CONFIG = {
    "schema_version": SCHEMA_VERSION,
    "global_picker_policy": "ask",
    "app_picker_overrides": {
        "org.signal.Signal": "inherit",
        "org.ferdium.Ferdium": "inherit",
        "com.rtosta.zapzap": "inherit",
    },
    "mime_defaults": {},
}

DEFAULT_MIME_DEFAULTS = {
    "image/jpeg": "org.nuxel.Photos.desktop",
    "image/png": "org.nuxel.Photos.desktop",
    "image/webp": "org.nuxel.Photos.desktop",
    "image/gif": "org.nuxel.Photos.desktop",
    "video/mp4": "org.nuxel.Photos.desktop",
    "video/webm": "org.nuxel.Photos.desktop",
    "video/x-matroska": "org.nuxel.Photos.desktop",
    DIRECTORY_MIME: "org.nuxel.Files.desktop",
}

DEFAULT_DESKTOP_DIRS = (
    "/usr/share/applications",
    "/usr/local/share/applications",
    "/var/lib/flatpak/exports/share/applications",
)
USER_DESKTOP_SUFFIX = ".local/share/applications"
USER_FLATPAK_EXPORTS = ".local/share/flatpak/exports/share/applications"


class FileHandlerError(Exception):
    """A validated, user-presentable file-handler error."""

    def __init__(self, message: str, code: str = "FILE_HANDLER_ERROR"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class DesktopEntry:
    desktop_id: str
    path: str
    name: str
    mime_types: Tuple[str, ...]
    exec_line: str = ""
    categories: Tuple[str, ...] = ()
    flatpak_id: str = ""
    no_display: bool = False

    @property
    def package_format(self) -> str:
        return "flatpak" if self.flatpak_id else "native"

    @property
    def app_id(self) -> str:
        return self.flatpak_id or self.desktop_id[:-8]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "desktop_id": self.desktop_id,
            "app_id": self.app_id,
            "name": self.name,
            "path": self.path,
            "mime_types": list(self.mime_types),
            "categories": list(self.categories),
            "package_format": self.package_format,
            "exec": self.exec_line,
            "no_display": self.no_display,
        }


# ---------------------------------------------------------------------------
# Paths and user identity
# ---------------------------------------------------------------------------

def session_home() -> str:
    """Return the graphical session home without trusting root's HOME."""
    configured = os.environ.get("NUXEL_SESSION_HOME")
    if configured and os.path.isdir(configured):
        return os.path.realpath(configured)
    session_user_name = os.environ.get("NUXEL_SESSION_USER")
    if session_user_name:
        try:
            entry = pwd.getpwnam(session_user_name)
            if entry.pw_dir and os.path.isdir(entry.pw_dir):
                return os.path.realpath(entry.pw_dir)
        except KeyError:
            pass
    if os.getuid() != 0:
        value = os.environ.get("HOME")
        if value and value not in ("/", "/root") and os.path.isdir(value):
            return os.path.realpath(value)
        try:
            return pwd.getpwuid(os.getuid()).pw_dir
        except KeyError:
            return os.path.expanduser("~")
    # Root-owned services (HTTP bridge) must still use the graphical user's
    # config and mimeapps file.  Prefer the established Nuxel account, then the
    # first ordinary /home account.
    try:
        entry = pwd.getpwnam("nuxel")
        if os.path.isdir(entry.pw_dir):
            return os.path.realpath(entry.pw_dir)
    except KeyError:
        pass
    try:
        for entry in pwd.getpwall():
            if entry.pw_uid >= 1000 and entry.pw_uid < 65534 and os.path.isdir(entry.pw_dir):
                return os.path.realpath(entry.pw_dir)
    except Exception:
        pass
    return "/home/nuxel"


def session_user() -> Optional[pwd.struct_passwd]:
    home = session_home()
    try:
        for entry in pwd.getpwall():
            if os.path.realpath(entry.pw_dir) == home:
                return entry
    except Exception:
        pass
    try:
        return pwd.getpwuid(os.getuid())
    except KeyError:
        return None


def config_home(home: Optional[str] = None) -> str:
    configured = os.environ.get("XDG_CONFIG_HOME")
    if configured:
        return os.path.abspath(configured)
    return os.path.join(home or session_home(), ".config")


def settings_path(home: Optional[str] = None) -> str:
    configured = os.environ.get("NUXEL_FILE_HANDLERS_CONFIG")
    if configured:
        return os.path.abspath(configured)
    return os.path.join(config_home(home), "nuxel", "file-handlers.json")


def mimeapps_path(home: Optional[str] = None) -> str:
    configured = os.environ.get("NUXEL_MIMEAPPS_PATH")
    if configured:
        return os.path.abspath(configured)
    return os.path.join(config_home(home), "mimeapps.list")


def _chown_session(path: str) -> None:
    if os.geteuid() != 0:
        return
    user = session_user()
    if user is None:
        return
    try:
        os.chown(path, user.pw_uid, user.pw_gid)
    except OSError:
        pass


def _atomic_write(path: str, text: str, mode: int = 0o644) -> None:
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, mode=0o755, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".%s." % os.path.basename(path), dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
        _chown_session(path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Settings schema
# ---------------------------------------------------------------------------

def _valid_app_id(value: str) -> bool:
    return bool(APP_ID_RE.match(str(value or "")))


def _valid_mime(value: str) -> bool:
    return bool(MIME_RE.match(str(value or "")))


def normalize_settings(raw: Any) -> Dict[str, Any]:
    doc = json.loads(json.dumps(DEFAULT_CONFIG))
    if not isinstance(raw, dict):
        return doc
    schema = raw.get("schema_version", SCHEMA_VERSION)
    try:
        schema = int(schema)
    except (TypeError, ValueError):
        schema = SCHEMA_VERSION
    if schema < 1:
        schema = SCHEMA_VERSION
    doc["schema_version"] = SCHEMA_VERSION
    policy = str(raw.get("global_picker_policy", "ask"))
    doc["global_picker_policy"] = policy if policy in POLICIES else "ask"

    overrides = raw.get("app_picker_overrides")
    clean: Dict[str, str] = {}
    if isinstance(overrides, dict):
        for app_id, value in overrides.items():
            app_id = str(app_id)
            value = str(value)
            if _valid_app_id(app_id) and value in OVERRIDE_POLICIES:
                clean[app_id] = value
    for app_id, value in DEFAULT_CONFIG["app_picker_overrides"].items():
        clean.setdefault(app_id, value)
    doc["app_picker_overrides"] = dict(sorted(clean.items()))

    mime_defaults: Dict[str, str] = {}
    incoming = raw.get("mime_defaults")
    if isinstance(incoming, dict):
        for mime, desktop_id in incoming.items():
            mime = str(mime)
            desktop_id = str(desktop_id)
            if _valid_mime(mime) and DESKTOP_ID_RE.match(desktop_id):
                mime_defaults[mime] = desktop_id
    doc["mime_defaults"] = dict(sorted(mime_defaults.items()))
    return doc


def load_settings(path: Optional[str] = None) -> Dict[str, Any]:
    target = path or settings_path()
    try:
        with open(target, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        return normalize_settings(None)
    except (OSError, ValueError):
        # A damaged settings document must never invent authority silently.
        return normalize_settings(None)
    return normalize_settings(raw)


def save_settings(doc: Any, path: Optional[str] = None) -> Dict[str, Any]:
    clean = normalize_settings(doc)
    target = path or settings_path()
    _atomic_write(target, json.dumps(clean, indent=2, sort_keys=True) + "\n", 0o600)
    return clean


def resolve_policy(doc: Dict[str, Any], app_id: str) -> str:
    app_id = str(app_id or "")
    overrides = doc.get("app_picker_overrides") if isinstance(doc, dict) else {}
    if isinstance(overrides, dict):
        value = overrides.get(app_id, "inherit")
        if value in POLICIES:
            return value
    value = doc.get("global_picker_policy") if isinstance(doc, dict) else "ask"
    return value if value in POLICIES else "ask"


def initial_source(doc: Dict[str, Any], app_id: str, filters_rules: Sequence[Tuple[int, str]],
                   kind: str) -> str:
    if kind != "open":
        return "files"
    policy = resolve_policy(doc, app_id)
    if policy == "files":
        return "files"
    if policy == "gallery":
        return "gallery"
    return "gallery" if filter_rules_are_media(filters_rules) else "files"


# ---------------------------------------------------------------------------
# Portal filter parsing / matching
# ---------------------------------------------------------------------------

def filter_rules(options: Any) -> List[Tuple[int, str]]:
    rules: List[Tuple[int, str]] = []
    if not isinstance(options, dict):
        try:
            options = dict(options or {})
        except Exception:
            return rules
    try:
        filters = options.get("filters", []) or []
        for item in filters:
            try:
                _name, subrules = item[0], item[1]
            except (TypeError, IndexError):
                continue
            for rule in subrules:
                try:
                    rtype = int(rule[0])
                    pattern = str(rule[1])
                except (TypeError, ValueError, IndexError):
                    continue
                if rtype in (0, 1) and pattern:
                    rules.append((rtype, pattern))
    except Exception:
        return []
    return rules


def media_filters(rules: Sequence[Tuple[int, str]]) -> bool:
    return filter_rules_are_media(rules)


def filter_rules_are_media(rules: Sequence[Tuple[int, str]]) -> bool:
    if not rules:
        return False
    saw_specific = False
    for rtype, pattern in rules:
        p = pattern.lower()
        if rtype == 1:
            if p.startswith("image/") or p.startswith("video/"):
                saw_specific = True
                continue
            return False
        # A glob rule is media only when every token names a supported media
        # extension.  Generic patterns such as '*.*' remain Files-first.
        tokens = [t for t in re.split(r"[;,]", p) if t.strip()]
        if not tokens:
            return False
        for token in tokens:
            token = token.strip().lower()
            matching = [ext for ext in MEDIA_EXTS if token.endswith("*" + ext)]
            if matching:
                saw_specific = True
                continue
            return False
    return saw_specific


def path_matches(path: str, rules: Sequence[Tuple[int, str]]) -> bool:
    if not rules:
        return True
    name = os.path.basename(path).lower()
    ext = os.path.splitext(name)[1].lower()
    mime = mimetypes.guess_type(path)[0] or ""
    for rtype, pattern in rules:
        if rtype == 0:
            for token in re.split(r"[;,]", pattern):
                token = token.strip().lower()
                if token and fnmatch.fnmatchcase(name, token):
                    return True
        elif mime and fnmatch.fnmatchcase(mime.lower(), pattern.lower()):
            return True
        elif pattern in ("image/*", "video/*") and (
                (pattern == "image/*" and ext in IMAGE_EXTS) or
                (pattern == "video/*" and ext in VIDEO_EXTS)):
            return True
    return False


def decode_path(value: Any) -> Optional[str]:
    """Decode the null-terminated byte array used by portal path options."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        raw = bytes(bytearray(value))
    except (TypeError, ValueError):
        return None
    raw = raw.split(b"\x00", 1)[0]
    return os.fsdecode(raw) if raw else None


# ---------------------------------------------------------------------------
# Canonical paths and approved roots
# ---------------------------------------------------------------------------

def approved_roots(home: Optional[str] = None) -> List[str]:
    home = os.path.realpath(home or session_home())
    roots = [home]
    configured = os.environ.get("NUXEL_CHOOSER_ROOTS", "")
    for raw in configured.split(":"):
        raw = raw.strip()
        if raw and os.path.isabs(raw):
            roots.append(os.path.realpath(raw))
    # Real files written by the Nuxel Camera store are user-visible media.
    roots.append(os.path.realpath(os.environ.get("NUXEL_MEDIA_DIR", "/var/lib/nuxel/media")))
    user = os.path.basename(home)
    roots.extend(os.path.realpath(p) for p in (
        "/run/media/%s" % user,
        "/media/%s" % user,
    ))
    unique: List[str] = []
    for root in roots:
        if root and root not in unique and os.path.isdir(root):
            unique.append(root)
    return unique


def _inside(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([path, root]) == root
    except (ValueError, OSError):
        return False


def canonical_selection(path: Any, *, roots: Optional[Sequence[str]] = None,
                        must_exist: bool = True, follow_final: bool = True) -> str:
    """Resolve and validate one selected path against the approved roots.

    ``..`` is rejected before resolution; realpath() then closes symlink escapes.
    For save targets, ``follow_final=False`` validates the parent but not a
    final path component that does not exist yet.
    """
    if not isinstance(path, (str, os.PathLike)):
        raise FileHandlerError("invalid path", "INVALID_PATH")
    text = os.fsdecode(path)
    if "\x00" in text:
        raise FileHandlerError("path contains NUL", "INVALID_PATH")
    if not os.path.isabs(text):
        raise FileHandlerError("path must be absolute", "INVALID_PATH")
    parts = [p for p in text.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise FileHandlerError("path traversal is not allowed", "INVALID_PATH")
    roots = [os.path.realpath(r) for r in (roots or approved_roots())]
    candidate = os.path.realpath(text) if follow_final else os.path.abspath(text)
    if not follow_final:
        parent = os.path.realpath(os.path.dirname(candidate))
        resolved = os.path.join(parent, os.path.basename(candidate))
        if not any(_inside(parent, root) for root in roots):
            raise FileHandlerError("path escapes approved roots", "OUTSIDE_ALLOWED_ROOT")
        if must_exist and not os.path.lexists(resolved):
            raise FileHandlerError("path does not exist", "NOT_FOUND")
        return resolved
    if not any(_inside(candidate, root) for root in roots):
        raise FileHandlerError("path escapes approved roots", "OUTSIDE_ALLOWED_ROOT")
    if must_exist:
        if not os.path.exists(candidate):
            raise FileHandlerError("path does not exist", "NOT_FOUND")
        if not os.access(candidate, os.R_OK):
            raise FileHandlerError("path is not readable", "ACCESS_DENIED")
    return candidate


def ensure_selected_shape(path: str, kind: str, *, directory: bool = False) -> str:
    if kind == "folder" or directory:
        if not os.path.isdir(path):
            raise FileHandlerError("a folder is required", "NOT_A_DIRECTORY")
    elif kind == "open":
        if not os.path.isfile(path):
            raise FileHandlerError("a regular file is required", "NOT_A_FILE")
    elif kind in ("save", "save_files"):
        if os.path.isdir(path):
            raise FileHandlerError("a file name is required", "IS_A_DIRECTORY")
    return path


# ---------------------------------------------------------------------------
# file:// URI encoding
# ---------------------------------------------------------------------------

def file_uri(path: str) -> str:
    """Encode an absolute path without hand-rolled percent escaping."""
    if not os.path.isabs(path):
        raise FileHandlerError("file URI requires an absolute path", "INVALID_PATH")
    try:
        from gi.repository import GLib  # type: ignore
        return GLib.filename_to_uri(os.path.abspath(path), None)
    except Exception:
        import urllib.parse
        return "file://" + urllib.parse.quote(os.path.abspath(path), safe="/")


def decode_file_uri(uri: str) -> str:
    from urllib.parse import unquote, urlparse
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise FileHandlerError("not a file URI", "INVALID_URI")
    if parsed.netloc not in ("", "localhost"):
        raise FileHandlerError("remote file URI is not a local selection", "INVALID_URI")
    return unquote(parsed.path)


# ---------------------------------------------------------------------------
# Desktop entries and MIME applications
# ---------------------------------------------------------------------------

def _desktop_dirs(home: Optional[str] = None) -> List[str]:
    override = os.environ.get("NUXEL_DESKTOP_DIRS", "")
    if override:
        return [os.path.abspath(p) for p in override.split(":") if p]
    home = home or session_home()
    dirs = [
        os.path.join(home, USER_DESKTOP_SUFFIX),
        os.path.join(home, USER_FLATPAK_EXPORTS),
    ]
    dirs.extend(DEFAULT_DESKTOP_DIRS)
    out: List[str] = []
    for directory in dirs:
        if directory not in out:
            out.append(directory)
    return out


def parse_desktop_entry(path: str) -> Optional[DesktopEntry]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read(128 * 1024)
    except OSError:
        return None
    group = None
    values: Dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            if group == "Desktop Entry" and values:
                break
            group = line[1:-1]
            continue
        if group != "Desktop Entry" or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values.setdefault(key.strip(), value.strip())
    if not values:
        return None
    desktop_id = os.path.basename(path)
    name = values.get("Name") or desktop_id[:-8]
    mimetypes_value = values.get("MimeType", "")
    mime_types = tuple(sorted({m.strip() for m in mimetypes_value.split(";") if m.strip()}))
    categories = tuple(c.strip() for c in values.get("Categories", "").split(";") if c.strip())
    return DesktopEntry(
        desktop_id=desktop_id,
        path=os.path.abspath(path),
        name=name,
        mime_types=mime_types,
        exec_line=values.get("Exec", ""),
        categories=categories,
        flatpak_id=values.get("X-Flatpak", ""),
        no_display=(values.get("NoDisplay", "").lower() == "true"),
    )


def desktop_catalog(home: Optional[str] = None) -> Dict[str, DesktopEntry]:
    entries: Dict[str, DesktopEntry] = {}
    for directory in _desktop_dirs(home):
        try:
            names = sorted(os.listdir(directory))
        except OSError:
            continue
        for name in names:
            if not name.endswith(".desktop"):
                continue
            item = parse_desktop_entry(os.path.join(directory, name))
            if item is not None and not item.no_display:
                entries.setdefault(item.desktop_id, item)
    return entries


def installed_handlers(mime: str, home: Optional[str] = None) -> List[DesktopEntry]:
    mime = str(mime)
    if not _valid_mime(mime):
        return []
    result = [e for e in desktop_catalog(home).values() if mime in e.mime_types]
    return sorted(result, key=lambda e: (e.name.lower(), e.desktop_id.lower()))


def validate_handler(mime: str, desktop_id: str, home: Optional[str] = None) -> DesktopEntry:
    if not _valid_mime(mime):
        raise FileHandlerError("invalid MIME type", "INVALID_MIME")
    if not DESKTOP_ID_RE.match(str(desktop_id or "")):
        raise FileHandlerError("invalid desktop id", "INVALID_DESKTOP_ID")
    entry = desktop_catalog(home).get(desktop_id)
    if entry is None:
        raise FileHandlerError("desktop entry is not installed", "HANDLER_NOT_INSTALLED")
    if mime not in entry.mime_types:
        raise FileHandlerError("desktop entry does not declare this MIME type",
                               "HANDLER_NOT_ASSOCIATED")
    return entry


def _parse_mime_groups(text: str) -> Dict[str, List[Tuple[str, str]]]:
    groups: Dict[str, List[Tuple[str, str]]] = {}
    group = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            group = stripped[1:-1]
            groups.setdefault(group, [])
        elif group is not None and "=" in line and not stripped.startswith("#"):
            key, value = line.split("=", 1)
            groups[group].append((key.strip(), value.strip()))
    return groups


def effective_mime_defaults(home: Optional[str] = None) -> Dict[str, str]:
    """Apply freedesktop MIME precedence: user, then XDG config dirs, then system."""
    home = home or session_home()
    paths: List[str] = [mimeapps_path(home)]
    config_dirs = os.environ.get("XDG_CONFIG_DIRS", "/etc/xdg").split(":")
    paths.extend(os.path.join(d, "mimeapps.list") for d in config_dirs if d)
    paths.append("/usr/share/applications/mimeapps.list")
    defaults: Dict[str, str] = {}
    seen_files = set()
    for path in paths:
        if path in seen_files:
            continue
        seen_files.add(path)
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        groups = _parse_mime_groups(text)
        for mime, value in groups.get("Default Applications", []):
            if mime not in defaults and value:
                defaults[mime] = value.split(";", 1)[0]
        for mime, value in groups.get("Removed Associations", []):
            if mime in defaults:
                removed = {v for v in value.split(";") if v}
                if defaults[mime] in removed:
                    defaults.pop(mime, None)
    return defaults


def _mimeapps_group_span(lines: Sequence[str], name: str) -> Optional[Tuple[int, int]]:
    start = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if start is not None:
                return start, index
            if stripped[1:-1] == name:
                start = index
    if start is not None:
        return start, len(lines)
    return None


def set_mime_default_text(text: str, mime: str, desktop_id: str) -> str:
    lines = text.splitlines(keepends=True)
    span = _mimeapps_group_span(lines, "Default Applications")
    if span is None:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.append("[Default Applications]\n")
        span = (len(lines) - 1, len(lines))
    start, end = span
    replaced = False
    for index in range(start + 1, end):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if key == mime:
            suffix = "\n" if lines[index].endswith("\n") else ""
            lines[index] = "%s=%s%s" % (mime, desktop_id, suffix)
            replaced = True
            break
    if not replaced:
        insert_at = end
        while insert_at > start + 1 and not lines[insert_at - 1].strip():
            insert_at -= 1
        lines.insert(insert_at, "%s=%s\n" % (mime, desktop_id))

    # A previous explicit removal must not shadow the newly selected handler.
    span = _mimeapps_group_span(lines, "Removed Associations")
    if span is not None:
        start, end = span
        for index in range(start + 1, end):
            stripped = lines[index].strip()
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() != mime:
                continue
            kept = [v for v in value.split(";") if v and v != desktop_id]
            suffix = "\n" if lines[index].endswith("\n") else ""
            lines[index] = ("%s=%s%s" % (mime, ";".join(kept) + (";" if kept else ""), suffix)
                            if kept else "")
    return "".join(lines)


def remove_mime_default_text(text: str, mime: str) -> str:
    lines = text.splitlines(keepends=True)
    span = _mimeapps_group_span(lines, "Default Applications")
    if span is None:
        return text
    start, end = span
    kept = []
    for index, line in enumerate(lines):
        if start < index < end and line.strip().split("=", 1)[0].strip() == mime:
            continue
        kept.append(line)
    return "".join(kept)


def read_user_mimeapps(home: Optional[str] = None) -> str:
    path = mimeapps_path(home)
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return "[Default Applications]\n\n[Added Associations]\n\n[Removed Associations]\n"


def write_user_mimeapps(text: str, home: Optional[str] = None) -> None:
    _atomic_write(mimeapps_path(home), text if text.endswith("\n") else text + "\n", 0o644)


def set_mime_default(mime: str, desktop_id: str, home: Optional[str] = None) -> Dict[str, Any]:
    entry = validate_handler(mime, desktop_id, home)
    text = set_mime_default_text(read_user_mimeapps(home), mime, desktop_id)
    write_user_mimeapps(text, home)
    return {"mime": mime, "desktop_id": entry.desktop_id, "name": entry.name,
            "path": mimeapps_path(home)}


def remove_mime_default(mime: str, home: Optional[str] = None) -> Dict[str, Any]:
    if not _valid_mime(mime):
        raise FileHandlerError("invalid MIME type", "INVALID_MIME")
    text = remove_mime_default_text(read_user_mimeapps(home), mime)
    write_user_mimeapps(text, home)
    return {"mime": mime, "removed": True, "path": mimeapps_path(home)}


def ensure_default_handlers(home: Optional[str] = None) -> Dict[str, Any]:
    """Seed the per-user defaults without overriding an existing USER choice.

    System-wide defaults (for example Totem or eog) are intentionally replaced
    in the per-user file for the capabilities Nuxel actually implements.  A
    key already present in the user's own mimeapps.list is never overwritten.
    """
    home = home or session_home()
    catalog = desktop_catalog(home)
    text = read_user_mimeapps(home)
    user_defaults = _parse_mime_groups(text).get("Default Applications", [])
    user_keys = {key for key, value in user_defaults if value}
    changed = []
    for mime, desktop_id in DEFAULT_MIME_DEFAULTS.items():
        if mime in user_keys:
            continue
        entry = catalog.get(desktop_id)
        if entry is None or mime not in entry.mime_types:
            continue
        text = set_mime_default_text(text, mime, desktop_id)
        changed.append({"mime": mime, "desktop_id": desktop_id})
    if changed:
        write_user_mimeapps(text, home)
    return {"changed": changed, "mimeapps": mimeapps_path(home),
            "effective": effective_mime_defaults(home)}


# ---------------------------------------------------------------------------
# App inventory
# ---------------------------------------------------------------------------

def _registry_path() -> str:
    return os.environ.get("NUXEL_APP_REGISTRY", "/etc/nuxel/app-registry/app_registry.json")


def app_inventory(home: Optional[str] = None) -> List[Dict[str, Any]]:
    home = home or session_home()
    apps: Dict[str, Dict[str, Any]] = {}
    try:
        registry = json.loads(Path(_registry_path()).read_text(encoding="utf-8"))
        rows = registry.get("apps") if isinstance(registry, dict) else None
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                app_id = str(row.get("id") or "")
                if not _valid_app_id(app_id):
                    continue
                apps[app_id] = {
                    "id": app_id,
                    "name": str(row.get("name") or app_id),
                    "type": str(row.get("type") or "app"),
                    "package_format": str(row.get("type") or "app"),
                    "installed": row.get("status") not in ("unsupported", "blocked"),
                    "source": "registry",
                    "description": str(row.get("description") or ""),
                    "desktop_id": "",
                }
    except (OSError, ValueError):
        pass

    for entry in desktop_catalog(home).values():
        app_id = entry.app_id
        if not _valid_app_id(app_id):
            continue
        row = apps.get(app_id) or {}
        is_pwa_registry_entry = row.get("source") == "registry" and row.get("type") == "pwa"
        row.update({
            "id": app_id,
            "name": entry.name or row.get("name") or app_id,
            "type": row.get("type") if is_pwa_registry_entry else (
                "native" if entry.package_format == "native" else "flatpak"),
            "package_format": row.get("package_format") if is_pwa_registry_entry else entry.package_format,
            "installed": True,
            "source": "registry+desktop-entry" if is_pwa_registry_entry else "desktop-entry",
            "desktop_id": entry.desktop_id,
            "desktop_entry": entry.path,
            "exec": entry.exec_line,
        })
        apps[app_id] = row
    return sorted(apps.values(), key=lambda a: (a.get("name") or a["id"]).lower())


def picker_policy_inventory(doc: Dict[str, Any], home: Optional[str] = None) -> List[Dict[str, Any]]:
    apps = app_inventory(home)
    overrides = doc.get("app_picker_overrides") or {}
    for app in apps:
        value = overrides.get(app["id"], "inherit")
        app["picker_policy"] = value if value in OVERRIDE_POLICIES else "inherit"
        app["effective_policy"] = resolve_policy(doc, app["id"])
    return apps


# ---------------------------------------------------------------------------
# Portal health
# ---------------------------------------------------------------------------

def _read_portals_conf() -> Tuple[str, str]:
    candidates = [
        os.environ.get("NUXEL_PORTALS_CONF", ""),
        "/etc/xdg-desktop-portal/portals.conf",
    ]
    config_dirs = os.environ.get("XDG_CONFIG_DIRS", "/etc/xdg").split(":")
    candidates.extend(os.path.join(d, "xdg-desktop-portal", "portals.conf")
                      for d in config_dirs if d)
    for path in candidates:
        if not path:
            continue
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        backend = "gtk"
        in_preferred = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped == "[preferred]":
                in_preferred = True
                continue
            if stripped.startswith("["):
                in_preferred = False
            if in_preferred and stripped.startswith("org.freedesktop.impl.portal.FileChooser="):
                backend = stripped.split("=", 1)[1].strip() or backend
        return backend, path
    return "missing", ""


def _bus_names(home: Optional[str] = None) -> Dict[str, Any]:
    home = home or session_home()
    user = session_user()
    env = dict(os.environ)
    env.update({
        "HOME": home,
        "XDG_RUNTIME_DIR": "/run/user/%d" % user.pw_uid if user else env.get("XDG_RUNTIME_DIR", ""),
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/%d/bus" % user.pw_uid if user else env.get("DBUS_SESSION_BUS_ADDRESS", ""),
        "XDG_CURRENT_DESKTOP": "Nuxel",
    })
    busctl_argv = ["busctl", "--user", "list", "--no-pager", "--no-legend"]
    argv = busctl_argv
    if os.geteuid() == 0 and user is not None:
        # The HTTP bridge runs with NoNewPrivileges=yes, which blocks the
        # runuser setuid transition.  Use the same transient system-manager
        # credential drop as the bridge's native app launcher.
        argv = ["/usr/bin/systemd-run", "--wait", "--pipe", "--collect", "--quiet",
                "--unit=nuxel-fh-status-%d-%d" % (os.getpid(), int(time.time() * 1000)),
                "--uid=%d" % user.pw_uid, "--gid=%d" % user.pw_gid]
        for key in ("HOME", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS", "XDG_CURRENT_DESKTOP"):
            argv.append("--setenv=%s=%s" % (key, env[key]))
        argv.extend(busctl_argv)
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=8, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc), "owners": {}}
    owners: Dict[str, Optional[str]] = {}
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        owner = None if parts[1] in ("-", "n/a") else parts[1]
        owners[parts[0]] = owner
    return {"error": None if proc.returncode == 0 else (proc.stderr or "").strip(),
            "owners": owners}


def _state_doc(home: Optional[str] = None) -> Dict[str, Any]:
    user = session_user()
    uid = user.pw_uid if user else os.getuid()
    path = os.environ.get("NUXEL_CHOOSER_STATE", "/run/user/%d/nuxel-portal-chooser.state" % uid)
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def portal_status(home: Optional[str] = None) -> Dict[str, Any]:
    home = home or session_home()
    backend, conf_path = _read_portals_conf()
    bus = _bus_names(home)
    owners = bus.get("owners") or {}
    frontend = owners.get("org.freedesktop.portal.Desktop")
    nuxel_backend = owners.get("org.freedesktop.impl.portal.desktop.nuxel")
    gtk_backend = owners.get("org.freedesktop.impl.portal.desktop.gtk")
    documents = owners.get("org.freedesktop.portal.Documents")
    selected_owner = nuxel_backend if backend == "nuxel" else (
        gtk_backend if backend == "gtk" else None)
    descriptor = "/usr/share/xdg-desktop-portal/portals/%s.portal" % backend
    state = _state_doc(home)
    backend_available = bool(selected_owner) or (
        backend not in ("missing",) and os.path.isfile(descriptor))
    return {
        "schema_version": 1,
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", "Nuxel"),
        "portals_conf": conf_path,
        "filechooser_backend": backend,
        "filechooser_backend_descriptor": descriptor if os.path.isfile(descriptor) else "",
        "frontend_available": bool(frontend),
        "frontend_owner": frontend or "",
        "backend_available": backend_available,
        "backend_owner": selected_owner or "",
        "nuxel_backend_owner": nuxel_backend or "",
        "gtk_backend_owner": gtk_backend or "",
        "documents_portal_available": bool(documents),
        "documents_portal_owner": documents or "",
        "bus_error": bus.get("error"),
        "last_chooser": state,
        "note": "org.nuxel.Portal is the hardware-permission broker; it is not the FileChooser frontend",
    }


# ---------------------------------------------------------------------------
# Settings RPC payloads
# ---------------------------------------------------------------------------

def _mime_catalog(home: Optional[str] = None) -> Dict[str, Any]:
    catalog = desktop_catalog(home)
    effective = effective_mime_defaults(home)
    categories = {
        "images": list(IMAGE_MIMES),
        "videos": list(VIDEO_MIMES),
        "directories": [DIRECTORY_MIME],
        "documents": ["text/plain", "application/pdf"],
        "archives": ["application/zip", "application/x-tar", "application/gzip"],
    }
    out: Dict[str, Any] = {}
    for mime in sorted(set(MEDIA_MIMES + (DIRECTORY_MIME,) + tuple(
            m for group in categories.values() for m in group))):
        handlers = []
        for entry in catalog.values():
            if mime in entry.mime_types:
                handlers.append(entry.as_dict())
        out[mime] = {
            "default": effective.get(mime, ""),
            "handlers": sorted(handlers, key=lambda e: e["name"].lower()),
        }
    return {"categories": categories, "mime": out,
            "mimeapps": mimeapps_path(home)}


def settings_view(doc: Dict[str, Any], home: Optional[str] = None) -> Dict[str, Any]:
    clean = normalize_settings(doc)
    return {
        "success": True,
        "schema_version": SCHEMA_VERSION,
        "settings": clean,
        "settings_path": settings_path(home),
        "mimeapps_path": mimeapps_path(home),
        "apps": picker_policy_inventory(clean, home),
        "picker_policies": list(POLICIES),
        "override_policies": list(OVERRIDE_POLICIES),
        "mime_catalog": _mime_catalog(home),
        "portal": portal_status(home),
    }


def apply_settings(raw: Any, home: Optional[str] = None) -> Dict[str, Any]:
    clean = normalize_settings(raw)
    # Validate every proposed MIME default BEFORE persisting either document.
    # A missing/undeclared handler is a real error, never a green label.
    for mime, desktop_id in clean.get("mime_defaults", {}).items():
        validate_handler(mime, desktop_id, home)
    save_settings(clean, settings_path(home))
    for mime, desktop_id in clean.get("mime_defaults", {}).items():
        set_mime_default(mime, desktop_id, home)
    return settings_view(clean, home)


def reset_settings(home: Optional[str] = None) -> Dict[str, Any]:
    clean = save_settings(DEFAULT_CONFIG, settings_path(home))
    return settings_view(clean, home)


# ---------------------------------------------------------------------------
# Real frontend test client (D-Bus)
# ---------------------------------------------------------------------------

def parse_test_picker_output(stdout: str, stderr: str = "", rc: int = 0) -> Dict[str, Any]:
    """Parse the test client's machine-readable result without trusting noise.

    The client prints one JSON document, but `systemd-run --pipe` and graphical
    startup warnings can prepend text.  Prefer the last complete JSON line, then
    the whole payload, then a bounded brace-delimited slice.  A parse failure is
    reported truthfully; it is never converted into a fake success.
    """
    text = (stdout or "").strip()
    candidates: List[str] = []
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            candidates.append(line)
    if text:
        candidates.append(text)
    if "{" in text and "}" in text:
        candidates.append(text[text.find("{"):text.rfind("}") + 1])
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            parsed = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if isinstance(parsed, dict):
            parsed.setdefault("success", False)
            return parsed
    return {
        "success": False,
        "error": "test_client_failed",
        "rc": int(rc or 0),
        "detail": ((stderr or stdout or "").strip()[-2000:]),
    }


def frontend_picker_request(options: Optional[Dict[str, Any]] = None,
                            timeout: float = 180.0) -> Dict[str, Any]:
    """Call the real xdg-desktop-portal frontend and wait for its Response.

    This function must run as the graphical session user with the user's session
    bus.  It is never a direct backend method call: the frontend performs backend
    selection from portals.conf and owns the public request object.
    """
    import dbus  # local import: standard-library-only unit tests need not load it
    import dbus.mainloop.glib  # type: ignore
    from gi.repository import GLib  # type: ignore

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    obj = bus.get_object("org.freedesktop.portal.Desktop",
                         "/org/freedesktop/portal/desktop")
    iface = dbus.Interface(obj, "org.freedesktop.portal.FileChooser")
    opts = dict(options or {})
    state: Dict[str, Any] = {"done": False, "code": None, "results": None,
                             "path": "", "error": None}
    loop = GLib.MainLoop()

    def on_response(code, results, path=None):
        try:
            state["results"] = json.loads(json.dumps(
                {str(k): (str(v) if not isinstance(v, (list, tuple)) else [str(x) for x in v])
                 for k, v in dict(results).items()}))
        except Exception:
            state["results"] = {}
        state["code"] = int(code)
        state["path"] = str(path or state["path"])
        state["done"] = True
        loop.quit()

    bus.add_signal_receiver(
        on_response, signal_name="Response",
        dbus_interface="org.freedesktop.portal.Request",
        path_keyword="path",
    )

    def invoke():
        try:
            dbus_opts = {}
            for key, value in opts.items():
                if key == "filters" and isinstance(value, (list, tuple)):
                    filters = []
                    for item in value:
                        try:
                            name, rules = item[0], item[1]
                        except (TypeError, IndexError):
                            continue
                        d_rules = []
                        for rule in rules or []:
                            try:
                                d_rules.append(dbus.Struct(
                                    (dbus.UInt32(int(rule[0])), dbus.String(str(rule[1]))),
                                    signature="us"))
                            except (TypeError, ValueError, IndexError):
                                continue
                        filters.append(dbus.Struct(
                            (dbus.String(str(name)),
                             dbus.Array(d_rules, signature="(us)")),
                            signature="sa(us)"))
                    dbus_opts[key] = dbus.Array(filters, signature="(sa(us))")
                elif key == "files" and isinstance(value, (list, tuple)):
                    dbus_opts[key] = dbus.Array(
                        [dbus.ByteArray(os.fsencode(str(name)) + b"\x00")
                         for name in value], signature="ay")
                elif key in ("current_folder", "current_file"):
                    raw = value if isinstance(value, bytes) else os.fsencode(str(value))
                    dbus_opts[key] = dbus.ByteArray(raw.rstrip(b"\x00") + b"\x00")
                elif isinstance(value, bool):
                    dbus_opts[key] = dbus.Boolean(value)
                elif isinstance(value, int):
                    dbus_opts[key] = dbus.UInt32(value)
                elif isinstance(value, str):
                    dbus_opts[key] = dbus.String(value)
                elif isinstance(value, (list, tuple)):
                    dbus_opts[key] = value
            handle = iface.OpenFile("", "PWNAGE-97000 Test Picker",
                                    dbus.Dictionary(dbus_opts, signature="sv"))
            state["path"] = str(handle)
        except Exception as exc:  # noqa: BLE001
            state["error"] = "%s: %s" % (type(exc).__name__, exc)
            loop.quit()
        return False

    GLib.idle_add(invoke)
    GLib.timeout_add_seconds(int(max(1, timeout)), lambda: (loop.quit(), False)[-1])
    loop.run()
    if state["error"]:
        return {"success": False, "error": state["error"],
                "request_path": state["path"], "frontend": True}
    if not state["done"]:
        return {"success": False, "error": "timeout", "request_path": state["path"],
                "frontend": True, "timeout_s": timeout}
    uris = state["results"].get("uris", []) if isinstance(state["results"], dict) else []
    if isinstance(uris, str):
        uris = [uris]
    return {
        "success": int(state["code"]) == 0,
        "response": int(state["code"]),
        "results": state["results"],
        "uris": list(uris),
        "request_path": state["path"],
        "frontend": True,
        "cancelled": int(state["code"]) == 1,
    }


def harness_test_document(home: Optional[str] = None) -> str:
    """Create a harmless, recognisable sample file for the Settings test button."""
    home = home or session_home()
    directory = os.path.join(home, "Documents")
    os.makedirs(directory, mode=0o700, exist_ok=True)
    _chown_session(directory)
    path = os.path.join(directory, "nuxel-file-handler-test.txt")
    body = "Nuxel File Handler test %s\nSelect this harmless file to verify the picker.\n" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _atomic_write(path, body, 0o600)
    return path

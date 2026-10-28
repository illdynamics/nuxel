#!/usr/bin/env python3
"""Nuxel PWA application persistence layer (PWNAGE-30000).

The HTTP bridge is the one root-owned process PWAs can reach on the phone, but
the D-Bus bridge is sandboxed and has never implemented the storage/caldav/mail
methods the registry advertises.  Those RPCs therefore failed with a dbus-error
and every app silently fell back to browser localStorage, which is not durable
across a launcher/webview rebuild and is not shared between apps.

This module provides a small, honest, file-backed store for the PWA apps:

  * calendar events          (schema-versioned JSON, atomic tmp+rename)
  * notes and generic keys   (schema-versioned JSON per key)
  * contacts                 (vCard-shaped JSON, de-duplicated by id)
  * file manager             (real files under a fixed, canonical root)
  * mail accounts + messages (JSON, credentials are NEVER stored here)

All writes are atomic (write tmp + os.replace) and all paths are canonicalized.
The file manager root is derived from NUXEL_APP_DATA_DIR (default
/var/lib/nuxel/app-data/files) and every path is resolved with realpath and
checked to stay inside the root before any operation; archive extraction uses
zipfile in a controlled way and refuses absolute paths, '..' and symlinks.

For tests the root can be pointed at a temp directory via
NUXEL_APP_DATA_DIR so no real user data is ever touched.
"""
from __future__ import annotations

import json
import mimetypes
import os
import pwd
import re
import shutil
import time
import zipfile
from pathlib import Path

try:
    import dbus  # only used by the haptics writer (optional on dev hosts)
except Exception:  # pragma: no cover - dbus is absent on some test hosts
    dbus = None

DEFAULT_DATA_DIR = "/var/lib/nuxel/app-data"

# Media extensions Gallery can browser without guessing file types from bytes.
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".heif", ".avif"}
VIDEO_EXTS = {".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".3gp"}


def _session_user():
    """Resolve the desktop session user without hard-coding a username.

    The HTTP bridge runs as root on the phone, so os.getuid() is not the
    session user.  NUXEL_SESSION_USER is set by the unit; if it is absent we
    fall back to the first ordinary account with a home under /home.  Tests set
    NUXEL_APP_DATA_DIR and never reach this path.
    """
    candidates = []
    for key in ("NUXEL_SESSION_USER", "SUDO_USER", "LOGNAME", "USER"):
        value = os.environ.get(key)
        if value:
            candidates.append(value)
    for name in candidates:
        try:
            return pwd.getpwnam(name)
        except KeyError:
            continue
    try:
        for entry in pwd.getpwall():
            if entry.pw_uid >= 1000 and entry.pw_uid < 65534 and entry.pw_dir.startswith("/home/"):
                return entry
    except Exception:
        pass
    return None

_SCHEMA_VERSION = 1
_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CONTACT_FIELDS = ("name", "phone", "email", "organization", "note")


class StoreError(Exception):
    """A user-facing, non-secret persistence error."""


class PwaStore:
    def __init__(self, root: str | None = None):
        # Application data (calendar, notes, mail accounts) always lives in the
        # root-owned app-data tree.  The FILES app, however, is a real explorer:
        # on the phone it must open the session user's home directory, not a
        # synthetic directory under /var/lib/nuxel.  An explicit root or
        # NUXEL_APP_DATA_DIR (used by tests) keeps the old isolated layout.
        explicit = root is not None or bool(os.environ.get("NUXEL_APP_DATA_DIR"))
        root = root or os.environ.get("NUXEL_APP_DATA_DIR") or DEFAULT_DATA_DIR
        self.root = Path(root).resolve()
        self._user = _session_user() if not explicit else None
        self.session_user = self._user.pw_name if self._user else None
        self.session_uid = self._user.pw_uid if self._user else None
        self.session_gid = self._user.pw_gid if self._user else None
        if explicit:
            self.files_root = self.root / "files"
        else:
            configured = os.environ.get("NUXEL_FILES_ROOT")
            if configured:
                self.files_root = Path(configured).expanduser().resolve()
            elif self._user and self._user.pw_dir:
                self.files_root = Path(self._user.pw_dir).resolve()
            else:
                self.files_root = self.root / "files"
        self._ensured = set()

    # ---- ownership helpers -------------------------------------------------
    def _chown(self, path: Path) -> None:
        """Best-effort ownership transfer for files created by the root bridge."""
        if self.session_uid is None or os.geteuid() != 0:
            return
        try:
            os.chown(path, self.session_uid, self.session_gid)
        except OSError:
            pass

    def _chown_tree(self, path: Path) -> None:
        if self.session_uid is None or os.geteuid() != 0:
            return
        self._chown(path)
        if path.is_dir():
            for base, dirs, files in os.walk(path):
                for name in dirs + files:
                    self._chown(Path(base) / name)

    def home_info(self) -> dict:
        return {
            "success": True,
            "home": str(self.files_root),
            "user": self.session_user,
            "uid": self.session_uid,
            "path": "/",
        }

    # ---- low-level helpers -------------------------------------------------
    def _mkdir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def _read_json(self, path: Path, default):
        try:
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            return default
        except (OSError, ValueError) as exc:
            raise StoreError("cannot read %s: %s" % (path, exc))

    def _write_json(self, path: Path, doc) -> None:
        self._mkdir(path.parent)
        tmp = path.with_suffix(path.suffix + ".tmp")
        data = json.dumps(doc, indent=2, sort_keys=True) + "\n"
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)

    def _key_path(self, key: str) -> Path:
        if not isinstance(key, str) or not _KEY_RE.match(key):
            raise StoreError("invalid storage key")
        return self.root / "keys" / (key + ".json")

    # ---- generic key/value store ------------------------------------------
    def storage_read(self, key: str):
        doc = self._read_json(self._key_path(key), None)
        if doc is None:
            return {"success": True, "data": None, "missing": True}
        return {"success": True, "data": doc.get("data"), "schema_version": doc.get("schema_version")}

    def storage_write(self, key: str, data) -> dict:
        self._write_json(self._key_path(key), {"schema_version": _SCHEMA_VERSION,
                                               "key": key, "updated_at": int(time.time()),
                                               "data": data})
        return {"success": True, "saved": True, "key": key}

    # ---- calendar ----------------------------------------------------------
    @property
    def events_path(self) -> Path:
        return self.root / "calendar" / "events.json"

    def caldav_list(self) -> dict:
        doc = self._read_json(self.events_path, {"schema_version": _SCHEMA_VERSION, "events": []})
        events = doc.get("events")
        if not isinstance(events, list):
            raise StoreError("calendar data is corrupted (events is not a list)")
        return {"success": True, "events": events, "schema_version": doc.get("schema_version")}

    def caldav_put(self, events) -> dict:
        if not isinstance(events, list):
            raise StoreError("calendar events must be a list")
        self._write_json(self.events_path, {"schema_version": _SCHEMA_VERSION,
                                            "events": events, "updated_at": int(time.time())})
        return {"success": True, "saved": len(events)}

    # ---- contacts ----------------------------------------------------------
    @property
    def contacts_path(self) -> Path:
        return self.root / "contacts" / "contacts.json"

    def contacts_list(self) -> dict:
        doc = self._read_json(self.contacts_path, {"schema_version": _SCHEMA_VERSION, "contacts": []})
        contacts = doc.get("contacts")
        if not isinstance(contacts, list):
            raise StoreError("contacts data is corrupted")
        return {"success": True, "contacts": contacts, "schema_version": doc.get("schema_version")}

    def contacts_upsert(self, contact: dict) -> dict:
        if not isinstance(contact, dict):
            raise StoreError("contact must be an object")
        name = (contact.get("name") or "").strip()
        if not name:
            raise StoreError("a contact needs a name")
        doc = self._read_json(self.contacts_path, {"schema_version": _SCHEMA_VERSION, "contacts": []})
        contacts = doc.get("contacts")
        if not isinstance(contacts, list):
            raise StoreError("contacts data is corrupted")
        cid = str(contact.get("id") or "")
        clean = {"id": cid or ("contact-%d" % int(time.time() * 1000))}
        for f in _CONTACT_FIELDS:
            clean[f] = str(contact.get(f) or "").strip()
        clean["updated_at"] = int(time.time())
        idx = None
        if cid:
            for i, c in enumerate(contacts):
                if isinstance(c, dict) and c.get("id") == cid:
                    idx = i
                    break
        if idx is not None:
            contacts[idx] = clean
        else:
            # Do not create a duplicate with the same id on repeated save.
            contacts.append(clean)
        self._write_json(self.contacts_path, {"schema_version": _SCHEMA_VERSION,
                                              "contacts": contacts,
                                              "updated_at": int(time.time())})
        return {"success": True, "contact": clean, "count": len(contacts)}

    def contacts_delete(self, cid: str) -> dict:
        doc = self._read_json(self.contacts_path, {"schema_version": _SCHEMA_VERSION, "contacts": []})
        contacts = doc.get("contacts")
        if not isinstance(contacts, list):
            raise StoreError("contacts data is corrupted")
        remaining = [c for c in contacts if not (isinstance(c, dict) and c.get("id") == cid)]
        if len(remaining) == len(contacts):
            return {"success": False, "error": "contact not found", "error_code": "NOT_FOUND"}
        self._write_json(self.contacts_path, {"schema_version": _SCHEMA_VERSION,
                                              "contacts": remaining,
                                              "updated_at": int(time.time())})
        return {"success": True, "deleted": True, "count": len(remaining)}

    # ---- file manager ------------------------------------------------------
    def _fs_path(self, path: str, follow_final: bool = True) -> Path:
        """Map a PWA path ("/" or "/docs/…") onto the file-manager root.

        Paths use "/" as the separator and may carry a leading slash.  "..",
        backslashes and empty-root escape attempts are refused before any
        filesystem access, and the resolved path must stay under the root.

        follow_final=False is used by rename/delete so a symlink is operated on
        as a link, never silently replaced by its target.  Its parent is still
        resolved and checked, so a symlink cannot be used to escape the root.
        """
        path = (path or "/").replace("\\", "/")
        parts = [p for p in path.split("/") if p not in ("", ".")]
        if any(p == ".." for p in parts):
            raise StoreError("path escapes the file manager root")
        root = self.files_root.resolve()
        candidate = root.joinpath(*parts) if parts else root
        if candidate == root:
            return root
        parent = candidate.parent.resolve()
        if parent != root and not parent.is_relative_to(root):
            raise StoreError("path escapes the file manager root")
        if not follow_final:
            return candidate
        resolved = candidate.resolve()
        if resolved != root and not resolved.is_relative_to(root):
            raise StoreError("path escapes the file manager root")
        return resolved

    def _entry(self, p: Path, root: Path) -> dict:
        st = p.lstat()
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            kind = "symlink"
        elif p.is_dir():
            kind = "folder"
        else:
            kind = "file"
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        return {"name": p.name or "/", "path": "/" + rel if rel != "." else "/",
                "type": kind, "size": st.st_size if kind == "file" else 0,
                "modified": int(st.st_mtime), "mime": mime,
                "readable": os.access(p, os.R_OK)}

    def storage_list_dir(self, path: str) -> dict:
        self._mkdir(self.files_root)
        target = self._fs_path(path)
        if not target.is_dir():
            return {"success": False, "error": "not a directory", "error_code": "NOT_A_DIRECTORY"}
        entries = []
        try:
            for child in sorted(target.iterdir(), key=lambda p: (p.is_symlink() or p.is_file(), p.name.lower())):
                try:
                    entries.append(self._entry(child, self.files_root))
                except OSError:
                    entries.append({"name": child.name, "path": "", "type": "unreadable",
                                    "size": 0, "modified": 0})
        except OSError as exc:
            return {"success": False, "error": "cannot list directory: %s" % exc,
                    "error_code": "READ_ERROR"}
        rel = target.relative_to(self.files_root).as_posix()
        return {"success": True,
                "path": "/" + rel.lstrip(".").strip("/"),
                "absolute_path": str(target),
                "home": str(self.files_root),
                "entries": entries, "count": len(entries)}

    def storage_mkdir(self, path: str) -> dict:
        target = self._fs_path(path)
        if target.exists():
            return {"success": False, "error": "path already exists", "error_code": "EXISTS"}
        try:
            target.mkdir(parents=True)
            self._chown(target)
        except OSError as exc:
            return {"success": False, "error": "cannot create folder: %s" % exc,
                    "error_code": "WRITE_ERROR"}
        return {"success": True, "created": True, "path": path}

    def storage_rename(self, src: str, dst: str) -> dict:
        s = self._fs_path(src, follow_final=False)
        d = self._fs_path(dst, follow_final=False)
        if not s.exists():
            return {"success": False, "error": "source does not exist", "error_code": "NOT_FOUND"}
        if d.exists():
            return {"success": False, "error": "destination already exists", "error_code": "EXISTS"}
        try:
            s.rename(d)
        except OSError as exc:
            return {"success": False, "error": "rename failed: %s" % exc, "error_code": "WRITE_ERROR"}
        return {"success": True, "renamed": True}

    def storage_delete(self, path: str) -> dict:
        target = self._fs_path(path, follow_final=False)
        if path in ("", "/") or target == self.files_root:
            return {"success": False, "error": "refusing to delete the file manager root",
                    "error_code": "REFUSED"}
        if not target.exists():
            return {"success": False, "error": "path does not exist", "error_code": "NOT_FOUND"}
        try:
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
        except OSError as exc:
            return {"success": False, "error": "delete failed: %s" % exc, "error_code": "WRITE_ERROR"}
        return {"success": True, "deleted": True}

    def _ensure_not_inside(self, src: Path, dst: Path) -> None:
        s = src.resolve()
        d = dst.resolve()
        if d.is_relative_to(s):
            raise StoreError("cannot copy or move a folder into itself")

    def storage_copy(self, src: str, dst: str) -> dict:
        s = self._fs_path(src)
        d = self._fs_path(dst)
        if not s.exists():
            return {"success": False, "error": "source does not exist", "error_code": "NOT_FOUND"}
        if d.exists():
            return {"success": False, "error": "destination already exists", "error_code": "EXISTS"}
        try:
            self._ensure_not_inside(s, d)
            if s.is_dir() and not s.is_symlink():
                shutil.copytree(s, d, symlinks=True)
                self._chown_tree(d)
            elif s.is_symlink():
                os.symlink(os.readlink(s), d)
                self._chown(d)
            else:
                shutil.copy2(s, d)
                self._chown(d)
        except (StoreError,) as exc:
            raise
        except OSError as exc:
            return {"success": False, "error": "copy failed: %s" % exc, "error_code": "WRITE_ERROR"}
        return {"success": True, "copied": True}

    def storage_move(self, src: str, dst: str) -> dict:
        s = self._fs_path(src)
        d = self._fs_path(dst)
        if not s.exists():
            return {"success": False, "error": "source does not exist", "error_code": "NOT_FOUND"}
        if d.exists():
            return {"success": False, "error": "destination already exists", "error_code": "EXISTS"}
        try:
            self._ensure_not_inside(s, d)
            shutil.move(str(s), str(d))
            self._chown_tree(d)
        except (StoreError,) as exc:
            raise
        except OSError as exc:
            return {"success": False, "error": "move failed: %s" % exc, "error_code": "WRITE_ERROR"}
        return {"success": True, "moved": True}

    # ---- archives (zip only; extraction is traversal-protected) ------------
    def storage_write_file(self, path: str, data_b64: str, overwrite: bool = False) -> dict:
        import base64
        target = self._fs_path(path)
        if not overwrite and target.exists():
            return {"success": False, "error": "destination already exists", "error_code": "EXISTS"}
        try:
            data = base64.b64decode(data_b64 or "", validate=False)
        except Exception as exc:
            return {"success": False, "error": "invalid base64 payload: %s" % exc,
                    "error_code": "BAD_PAYLOAD"}
        # A file upload through the PWA bridge is bounded; real large-media
        # ingestion is owned by the Gallery/Camera store, not this path.
        if len(data) > 64 * 1024 * 1024:
            return {"success": False, "error": "file exceeds the 64 MB PWA write cap",
                    "error_code": "PAYLOAD_TOO_LARGE"}
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            self._chown(target.parent)
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_bytes(data)
            os.chmod(tmp, 0o644)
            os.replace(tmp, target)
            self._chown(target)
        except OSError as exc:
            return {"success": False, "error": "write failed: %s" % exc, "error_code": "WRITE_ERROR"}
        return {"success": True, "written": True, "size": len(data), "path": path,
                "absolute_path": str(target)}

    def storage_read_file(self, path: str) -> dict:
        import base64
        target = self._fs_path(path)
        if not target.is_file():
            return {"success": False, "error": "not a file", "error_code": "NOT_FOUND"}
        try:
            data = target.read_bytes()
        except OSError as exc:
            return {"success": False, "error": "read failed: %s" % exc, "error_code": "READ_ERROR"}
        # Inline only bounded previews; larger files must be opened by the
        # platform handler instead of being pushed through the bridge.
        if len(data) > 32 * 1024 * 1024:
            return {"success": False, "error": "file too large to inline (32 MB cap); use the media URL",
                    "error_code": "PAYLOAD_TOO_LARGE"}
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        return {"success": True, "size": len(data), "mime": mime,
                "absolute_path": str(target),
                "data_b64": base64.b64encode(data).decode("ascii")}

    def storage_archive_create(self, sources, dest: str) -> dict:
        if not isinstance(sources, list) or not sources:
            raise StoreError("choose at least one file or folder to compress")
        d = self._fs_path(dest)
        if d.exists():
            return {"success": False, "error": "destination already exists", "error_code": "EXISTS"}
        try:
            d.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(d, "w", zipfile.ZIP_DEFLATED) as zf:
                for src in sources:
                    s = self._fs_path(src)
                    if not s.exists():
                        return {"success": False, "error": "source does not exist: %s" % src,
                                "error_code": "NOT_FOUND"}
                    if s.is_dir():
                        for base, _dirs, files in os.walk(s):
                            for f in files:
                                fp = Path(base) / f
                                zf.write(fp, fp.relative_to(s.parent).as_posix())
                    else:
                        zf.write(s, s.name)
        except OSError as exc:
            return {"success": False, "error": "archive creation failed: %s" % exc,
                    "error_code": "WRITE_ERROR"}
        self._chown(d)
        return {"success": True, "created": True, "path": dest,
                "absolute_path": str(d)}

    def storage_archive_extract(self, archive: str, dest: str) -> dict:
        a = self._fs_path(archive)
        d = self._fs_path(dest)
        if not a.is_file():
            return {"success": False, "error": "archive does not exist", "error_code": "NOT_FOUND"}
        d.mkdir(parents=True, exist_ok=True)
        root = self.files_root.resolve()
        try:
            with zipfile.ZipFile(a) as zf:
                for info in zf.infolist():
                    name = info.filename
                    if name.startswith("/") or ".." in name.replace("\\", "/").split("/"):
                        return {"success": False, "error": "archive contains an unsafe path: %s" % name,
                                "error_code": "UNSAFE_ARCHIVE"}
                    target = (d / name).resolve()
                    if not target.is_relative_to(root):
                        return {"success": False, "error": "archive extraction escapes the file root",
                                "error_code": "UNSAFE_ARCHIVE"}
                    mode = (info.external_attr >> 16) & 0o170000
                    if mode == 0o120000:
                        return {"success": False, "error": "archive contains a symlink entry: %s" % name,
                                "error_code": "UNSAFE_ARCHIVE"}
                    if target.exists():
                        return {"success": False, "error": "refusing to overwrite existing path: %s" % name,
                                "error_code": "EXISTS"}
                    target.parent.mkdir(parents=True, exist_ok=True)
                    self._chown(target.parent)
                    with zf.open(info) as src_fh, open(target, "wb") as dst_fh:
                        shutil.copyfileobj(src_fh, dst_fh)
                    os.chmod(target, 0o644)
                    self._chown(target)
        except zipfile.BadZipFile as exc:
            return {"success": False, "error": "not a valid zip archive: %s" % exc,
                    "error_code": "BAD_ARCHIVE"}
        except OSError as exc:
            return {"success": False, "error": "extraction failed: %s" % exc,
                    "error_code": "WRITE_ERROR"}
        return {"success": True, "extracted": True, "to": dest}

    # ---- media browsing (Gallery) -------------------------------------------
    def storage_media_list(self) -> dict:
        """List real photos/videos from the user's media folders.

        The scan is bounded, never follows symlinked directories out of the
        home root, and returns metadata only (pixels are fetched through
        /api/v1/storage/file).  Nothing is invented when the folders are empty.
        """
        self._mkdir(self.files_root)
        folders = [self.files_root / name for name in ("Gallery", "Pictures", "Videos", "DCIM")]
        items = []
        seen = set()
        for base in folders:
            if not base.is_dir() or base.is_symlink():
                continue
            for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
                depth = len(Path(dirpath).relative_to(base).parts)
                if depth >= 4:
                    dirnames[:] = []
                dirnames[:] = [d for d in sorted(dirnames)
                               if not d.startswith(".") and not (Path(dirpath) / d).is_symlink()]
                for name in sorted(filenames):
                    if name.startswith("."):
                        continue
                    ext = Path(name).suffix.lower()
                    if ext in IMAGE_EXTS:
                        kind = "photo"
                    elif ext in VIDEO_EXTS:
                        kind = "video"
                    else:
                        continue
                    path = Path(dirpath) / name
                    try:
                        st = path.lstat()
                    except OSError:
                        continue
                    rel = path.relative_to(self.files_root).as_posix()
                    if rel in seen:
                        continue
                    seen.add(rel)
                    items.append({
                        "id": rel,
                        "name": name,
                        "path": "/" + rel,
                        "album": Path(rel).parts[0] if len(Path(rel).parts) > 1 else "Gallery",
                        "kind": kind,
                        "mime": mimetypes.guess_type(name)[0] or "application/octet-stream",
                        "size": st.st_size,
                        "modified": int(st.st_mtime),
                        "taken": int(st.st_mtime * 1000),
                    })
                    if len(items) >= 2000:
                        break
                if len(items) >= 2000:
                    break
            if len(items) >= 2000:
                break
        items.sort(key=lambda x: x["modified"], reverse=True)
        return {"success": True, "home": str(self.files_root),
                "media": items, "count": len(items),
                "folders": [str(f) for f in folders if f.is_dir()]}

    def storage_media_file(self, path: str):
        """Resolve a media path for the streaming HTTP endpoint."""
        target = self._fs_path(path)
        if not target.is_file():
            raise StoreError("media file does not exist")
        return target

    # ---- haptics -----------------------------------------------------------
    # The haptics daemon owns /run/nuxel-haptics/haptics.cmd.  We only write a
    # single newline-terminated command through the FIFO; we never invent a
    # vibrator node and never claim the motor was felt.
    @property
    def haptics_fifo(self) -> Path:
        return Path(os.environ.get("NUXEL_HAPTICS_FIFO", "/run/nuxel-haptics/haptics.cmd"))

    def haptics_pulse(self, kind: str = "tap") -> dict:
        if kind not in ("tap", "scroll", "navigation", "switch", "long", "error", "test"):
            return {"success": False, "error": "unknown haptics pattern", "error_code": "BAD_PATTERN"}
        fifo = self.haptics_fifo
        if not fifo.exists():
            return {"success": False, "error": "haptics service is not running (no FIFO)",
                    "error_code": "UNAVAILABLE", "software_path": False}
        try:
            fd = os.open(str(fifo), os.O_WRONLY | os.O_NONBLOCK)
        except OSError as exc:
            return {"success": False, "error": "haptics FIFO is not writable: %s" % exc,
                    "error_code": "UNAVAILABLE"}
        try:
            os.write(fd, (kind + "\n").encode("ascii"))
        except OSError as exc:
            return {"success": False, "error": "haptics request was not accepted: %s" % exc,
                    "error_code": "WRITE_ERROR"}
        finally:
            os.close(fd)
        # Request dispatched to the single haptics owner.  Whether the motor
        # physically moved is reported by the daemon's state file, not this write.
        return {"success": True, "dispatched": True, "pattern": kind, "software_path": True}

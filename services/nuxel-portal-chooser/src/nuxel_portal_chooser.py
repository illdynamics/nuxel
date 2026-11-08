#!/usr/bin/env python3
"""Nuxel XDG Desktop Portal FileChooser backend (PWNAGE-97000).

This is the real ``org.freedesktop.impl.portal.FileChooser`` backend selected by
``configs/nuxel/portals.conf``.  It is deliberately separate from
``org.nuxel.Portal``, the hardware-permission broker.

One request/response flow, two explicit Nuxel sources:

* Gallery — the same real media provider used by ``org.nuxel.Photos``
  (``storage.media-list`` plus the file-backed Nuxel Camera store).
* Files — the same approved-root file provider used by ``org.nuxel.Files``.

The selected files are returned to the original portal request as ``file://``
URIs.  Cancel returns response 1.  A backend error returns response 2.  No file
is returned unless it is still readable and inside an approved root.  The XDG
portal frontend remains responsible for Document portal grants to sandboxed
callers; this backend never widens a sandbox.
"""
from __future__ import annotations

import json
import mimetypes
import os
import pwd
import sys
import threading
import time
import traceback
from pathlib import Path

import dbus
import dbus.service
import dbus.mainloop.glib
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango  # noqa: E402


def _load_policy_module():
    here = Path(__file__).resolve()
    candidates = [
        Path("/usr/lib/nuxel"),
        here.parents[2] / "nuxel-file-handlers" / "src",
        here.parents[1] / "nuxel-file-handlers" / "src",
        here.parent / "nuxel-file-handlers",
    ]
    for base in candidates:
        if (base / "nuxel_file_handlers.py").is_file():
            sys.path.insert(0, str(base))
            break
    import nuxel_file_handlers as fh  # noqa: E402
    return fh


fh = _load_policy_module()

BUS_NAME = "org.freedesktop.impl.portal.desktop.nuxel"
OBJECT_PATH = "/org/freedesktop/portal/desktop"
IFACE = "org.freedesktop.impl.portal.FileChooser"
REQUEST_IFACE = "org.freedesktop.impl.portal.Request"
SERVICE_VERSION = "1.1.0"

_UID = os.getuid()
_UID_RUNTIME = "/run/user/%d" % _UID if os.path.isdir("/run/user/%d" % _UID) else "/tmp"
STATE_PATH = os.environ.get("NUXEL_CHOOSER_STATE") or os.path.join(
    _UID_RUNTIME, "nuxel-portal-chooser.state")
LOG_PATH = os.environ.get("NUXEL_CHOOSER_LOG") or os.path.join(
    _UID_RUNTIME, "nuxel-portal-chooser.log")

GALLERY_LIMIT = max(12, min(600, int(os.environ.get("NUXEL_CHOOSER_GALLERY_LIMIT", "200"))))
THUMB_PX = 132
MAX_SELECTED = 64
REQUEST_TIMEOUT_S = max(30, min(1800, int(os.environ.get("NUXEL_CHOOSER_TIMEOUT", "600"))))
MAX_ACTIVE_REQUESTS = 4

_audit_lock = threading.Lock()
_counts = {"requests": 0, "selected": 0, "cancelled": 0, "errors": 0}


# ---------------------------------------------------------------------------
# Diagnostics (never record filenames or paths)
# ---------------------------------------------------------------------------

def audit(path: str = STATE_PATH, **fields) -> None:
    doc = {
        "schema_version": 2,
        "service": BUS_NAME,
        "backend": "nuxel-portal-chooser",
        "version": SERVICE_VERSION,
        "pid": os.getpid(),
        "updated_at": time.time(),
    }
    with _audit_lock:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                old = json.load(handle)
            if isinstance(old, dict):
                doc.update({k: v for k, v in old.items()
                            if k not in doc and k not in ("updated_at", "last_request")})
        except (OSError, ValueError):
            pass
        doc.update(fields)
        doc["counts"] = dict(_counts)
        tmp = path + ".%d.tmp" % os.getpid()
        try:
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(doc, handle, sort_keys=True)
                handle.write("\n")
            os.replace(tmp, path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def _log(message: str) -> None:
    line = "%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), message)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError:
        sys.stderr.write(line)


def normalize_environment() -> None:
    """Make D-Bus activation and the graphical session agree on HOME/display."""
    uid = os.getuid()
    try:
        pw = pwd.getpwuid(uid)
    except KeyError:
        pw = None
    home = os.environ.get("HOME", "")
    if uid != 0 and (not home or home == "/root" or not os.path.isdir(home)):
        if pw is not None:
            os.environ["HOME"] = pw.pw_dir
    if not os.environ.get("XDG_RUNTIME_DIR"):
        candidate = "/run/user/%d" % uid
        os.environ["XDG_RUNTIME_DIR"] = candidate if os.path.isdir(candidate) else "/run/nuxel-wayland"
    if not os.environ.get("WAYLAND_DISPLAY"):
        candidate = os.path.join(os.environ["XDG_RUNTIME_DIR"], "wayland-0")
        if os.path.exists(candidate):
            os.environ["WAYLAND_DISPLAY"] = "wayland-0"
    os.environ.setdefault("XDG_CURRENT_DESKTOP", "Nuxel")
    os.environ.setdefault("GDK_BACKEND", "wayland")
    os.environ.setdefault("GSK_RENDERER", "cairo")
    os.environ.setdefault("PIPEWIRE_RUNTIME_DIR", "/run/nuxel-wayland")


# ---------------------------------------------------------------------------
# Real Gallery/Files providers
# ---------------------------------------------------------------------------

def _load_store_modules():
    here = Path(__file__).resolve()
    candidates = [
        Path("/usr/lib/nuxel/nuxel-bridge"),
        Path("/usr/lib/nuxel"),
        here.parents[2] / "nuxel-bridge" / "src",
        here.parents[1] / "nuxel-bridge" / "src",
    ]
    for base in candidates:
        if (base / "pwa_store.py").is_file():
            sys.path.insert(0, str(base))
            break
    try:
        import pwa_store  # type: ignore
    except Exception:
        pwa_store = None
    try:
        import media_store  # type: ignore
    except Exception:
        media_store = None
    return pwa_store, media_store


PWA_STORE, MEDIA_STORE = _load_store_modules()


def _media_kind(path: str) -> str:
    return "video" if os.path.splitext(path)[1].lower() in fh.VIDEO_EXTS else "photo"


def gallery_media(rules, limit: int = GALLERY_LIMIT, home: str | None = None):
    """Return real media rows from the Gallery provider and camera store.

    Every row carries a real, existing absolute path.  Base64-only camera
    records are intentionally excluded: the picker never fabricates a file URI.
    """
    home = os.path.realpath(home or fh.session_home())
    rows = []
    seen = set()
    store = None
    if PWA_STORE is not None:
        try:
            store = PWA_STORE.PwaStore()
            listing = store.storage_media_list()
            if isinstance(listing, dict) and listing.get("success") is not False:
                for item in listing.get("media") or []:
                    if not isinstance(item, dict):
                        continue
                    rel = str(item.get("path") or "")
                    path = os.path.realpath(os.path.join(store.files_root, rel.lstrip("/")))
                    if path in seen or not os.path.isfile(path):
                        continue
                    if not fh.path_matches(path, rules):
                        continue
                    seen.add(path)
                    rows.append({"path": path, "name": os.path.basename(path),
                                 "mime": item.get("mime") or mimetypes.guess_type(path)[0] or
                                         "application/octet-stream",
                                 "mtime": float(item.get("modified") or 0),
                                 "kind": item.get("kind") or _media_kind(path),
                                 "source": "gallery"})
        except Exception as exc:  # noqa: BLE001 - fall through to a bounded scan
            _log("GALLERY_PROVIDER_ERROR %s: %s" % (type(exc).__name__, exc))
    roots = [os.path.join(home, name) for name in ("Gallery", "Pictures", "DCIM", "Videos")]
    if store is not None and hasattr(store, "files_root"):
        roots.append(os.path.join(str(store.files_root), "VoiceRecordings"))
    roots.extend([
        os.path.join(os.environ.get("NUXEL_MEDIA_DIR", "/var/lib/nuxel/media"),
                     "pictures", "Nuxel Camera"),
        os.path.join(os.environ.get("NUXEL_MEDIA_DIR", "/var/lib/nuxel/media"),
                     "videos", "Nuxel Camera"),
    ])
    # Camera store records are authoritative and have real paths.
    if MEDIA_STORE is not None:
        try:
            # _scan() is the read-only filesystem reconciliation.  The public
            # list() refreshes a root-owned cache index; the chooser runs as the
            # graphical user and must not attempt that write.
            store_obj = MEDIA_STORE.media_store()
            records = store_obj._scan() if hasattr(store_obj, "_scan") else store_obj.list()
            for item in records:
                path = os.path.realpath(str(item.get("path") or ""))
                if path and path not in seen and os.path.isfile(path) and fh.path_matches(path, rules):
                    seen.add(path)
                    rows.append({"path": path, "name": os.path.basename(path),
                                 "mime": item.get("mime") or mimetypes.guess_type(path)[0] or
                                         "application/octet-stream",
                                 "mtime": float(item.get("taken") or item.get("mtime") or 0),
                                 "kind": item.get("kind") or _media_kind(path),
                                 "source": "camera"})
        except Exception as exc:  # noqa: BLE001
            _log("CAMERA_PROVIDER_ERROR %s: %s" % (type(exc).__name__, exc))
    # Fallback bounded scan for real files that the provider did not index.
    if len(rows) < limit:
        allowed = fh.approved_roots(home)
        stack = []
        for root in roots:
            real = os.path.realpath(root)
            if os.path.isdir(real) and any(fh._inside(real, a) for a in allowed):
                stack.append((real, 0))
        while stack and len(rows) < limit * 4:
            directory, depth = stack.pop()
            try:
                entries = list(os.scandir(directory))
            except OSError:
                continue
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if depth < 4 and not entry.name.startswith("."):
                            stack.append((entry.path, depth + 1))
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    path = os.path.realpath(entry.path)
                    if path in seen or not fh.path_matches(path, rules):
                        continue
                    if os.path.splitext(path)[1].lower() not in fh.MEDIA_EXTS:
                        continue
                    seen.add(path)
                    rows.append({"path": path, "name": os.path.basename(path),
                                 "mime": mimetypes.guess_type(path)[0] or "application/octet-stream",
                                 "mtime": entry.stat(follow_symlinks=False).st_mtime,
                                 "kind": _media_kind(path), "source": "gallery"})
                except OSError:
                    continue
    rows.sort(key=lambda row: row.get("mtime") or 0, reverse=True)
    return rows[:limit]


class FileEntry:
    __slots__ = ("path", "name", "type", "size", "modified", "mime", "readable")

    def __init__(self, row):
        self.path = str(row.get("path") or "")
        self.name = str(row.get("name") or "")
        self.type = str(row.get("type") or "file")
        self.size = int(row.get("size") or 0)
        self.modified = int(row.get("modified") or 0)
        self.mime = str(row.get("mime") or "")
        self.readable = bool(row.get("readable", True))


class FilesSource:
    """Files browser state backed by the same PwaStore provider as Files."""

    def __init__(self, options, kind, rules, home=None):
        self.options = options
        self.kind = kind
        self.rules = rules
        self.home = os.path.realpath(home or fh.session_home())
        self.root = self.home
        self.store = None
        if PWA_STORE is not None:
            try:
                self.store = PWA_STORE.PwaStore()
                self.root = os.path.realpath(str(self.store.files_root))
            except Exception:
                self.store = None
        self.cwd = "/"
        current = fh.decode_path(options.get("current_folder"))
        if current:
            virtual = self.virtual_path(current)
            if virtual is not None:
                self.cwd = virtual

    def virtual_path(self, path):
        if not path:
            return None
        if path.startswith("/") and not os.path.isabs(path):
            return path or "/"
        real = os.path.realpath(path)
        if fh._inside(real, self.root):
            rel = os.path.relpath(real, self.root)
            return "/" if rel == "." else "/" + rel.replace(os.sep, "/")
        return None

    def absolute_path(self, virtual):
        virtual = str(virtual or "/").replace("\\", "/")
        parts = [p for p in virtual.split("/") if p not in ("", ".")]
        if any(p == ".." for p in parts):
            raise fh.FileHandlerError("path traversal is not allowed", "INVALID_PATH")
        path = os.path.realpath(os.path.join(self.root, *parts))
        if not fh._inside(path, self.root):
            raise fh.FileHandlerError("path escapes the Files root", "OUTSIDE_ALLOWED_ROOT")
        return path

    def list_dir(self, virtual=None):
        target = virtual if virtual is not None else self.cwd
        if self.store is not None:
            try:
                result = self.store.storage_list_dir(target)
            except Exception as exc:  # noqa: BLE001 - report an empty honest view
                _log("FILES_PROVIDER_ERROR %s: %s" % (type(exc).__name__, exc))
                result = {"success": False}
            if isinstance(result, dict) and result.get("success") is not False:
                rows = [FileEntry(row) for row in result.get("entries") or []]
            else:
                rows = []
        else:
            absolute = self.absolute_path(target)
            rows = []
            try:
                with os.scandir(absolute) as iterator:
                    for entry in iterator:
                        try:
                            stat = entry.stat(follow_symlinks=False)
                            if entry.is_symlink():
                                kind = "symlink"
                            elif entry.is_dir(follow_symlinks=False):
                                kind = "folder"
                            else:
                                kind = "file"
                            rows.append(FileEntry({
                                "name": entry.name,
                                "path": "/" + os.path.relpath(entry.path, self.root).replace(os.sep, "/"),
                                "type": kind,
                                "size": stat.st_size,
                                "modified": int(stat.st_mtime),
                                "mime": mimetypes.guess_type(entry.name)[0] or "",
                                "readable": os.access(entry.path, os.R_OK),
                            }))
                        except OSError:
                            continue
            except OSError:
                rows = []
            rows.sort(key=lambda row: (0 if row.type == "folder" else 1, row.name.lower()))
        if self.kind in ("open", "folder"):
            rows = [row for row in rows if row.type != "symlink" and
                    (row.type == "folder" or row.path == "" or fh.path_matches(
                        self.absolute_path(row.path), self.rules))]
        return rows

    def can_select(self, entry):
        if entry.type == "folder":
            return self.kind == "folder"
        if entry.type != "file" or not entry.readable:
            return False
        return self.kind == "open" and fh.path_matches(self.absolute_path(entry.path), self.rules)


def _safe_create_file(path: str, overwrite: bool = False) -> str:
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        raise fh.FileHandlerError("save folder does not exist", "NOT_FOUND")
    if os.path.isdir(path):
        raise fh.FileHandlerError("save target is a directory", "IS_A_DIRECTORY")
    try:
        if os.path.exists(path):
            if not overwrite:
                raise fh.FileHandlerError("save target already exists", "EXISTS")
            if not os.access(path, os.W_OK):
                raise fh.FileHandlerError("save target is not writable", "ACCESS_DENIED")
            return path
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
    except FileExistsError:
        raise fh.FileHandlerError("save target already exists", "EXISTS")
    except OSError as exc:
        raise fh.FileHandlerError("cannot create save target: %s" % exc, "WRITE_ERROR")
    return path


def _collision_free(path: str, used: set) -> str:
    if path not in used and not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    index = 1
    while True:
        candidate = "%s (%d)%s" % (base, index, ext)
        if candidate not in used and not os.path.exists(candidate):
            return candidate
        index += 1


# ---------------------------------------------------------------------------
# GTK chooser UI
# ---------------------------------------------------------------------------

CHOOSER_CSS = b"""
window.nuxel-chooser, .nuxel-chooser { background: #101820; color: #eaf2f8; }
.nuxel-chooser .chooser-head { padding: 10px 12px 6px; }
.nuxel-chooser .chooser-title { font-size: 16px; font-weight: 700; }
.nuxel-chooser .chooser-sub { color: #8fa2b3; font-size: 12px; }
.nuxel-chooser stackswitcher button { min-height: 44px; min-width: 132px; font-size: 14px; }
.nuxel-chooser .gallery { background: #101820; }
.nuxel-chooser flowboxchild { padding: 4px; border-radius: 12px; }
.nuxel-chooser flowboxchild:selected { background: #1b5e86; }
.nuxel-chooser .thumb-name { font-size: 11px; color: #cfdae4; }
.nuxel-chooser .thumb-box { padding: 4px; }
.nuxel-chooser .chooser-status { color: #ffd166; font-size: 12px; padding: 4px 12px; }
.nuxel-chooser button { min-height: 40px; }
.nuxel-chooser .pathbar button { min-height: 34px; padding: 2px 8px; font-size: 11px; }
.nuxel-chooser .file-row { min-height: 52px; padding: 4px 8px; }
.nuxel-chooser .file-row-name { font-size: 13px; font-weight: 600; }
.nuxel-chooser .file-row-meta { font-size: 10px; color: #8fa2b3; }
.nuxel-chooser list { background: #101820; }
.nuxel-chooser .browser-head { padding: 4px 8px; }
.nuxel-chooser .save-name { font-size: 14px; min-height: 42px; }
"""


class NuxelChooserDialog:
    def __init__(self, backend, handle, kind, title, options, rules, media, policy,
                 app_id=""):
        self.backend = backend
        self.app_id = str(app_id or "")
        self.settings = fh.load_settings()
        self.handle = str(handle)
        self.kind = kind
        self.options = dict(options)
        self.rules = list(rules)
        self.media = list(media)
        self.policy = policy
        self.files = FilesSource(options, kind, rules)
        self.result_paths = []
        self.response_code = 2
        self.source = "none"
        self._closed_by_portal = False
        self._alive = True
        self._finished = False
        self._on_done = None
        self._thumb_queue = []
        self._autotest = os.environ.get("NUXEL_CHOOSER_AUTOTEST", "")
        self._timeout_id = None
        self._dialog = Gtk.Dialog()
        self._dialog.get_style_context().add_class("nuxel-chooser")
        self._dialog.set_title(title or "Select a file")
        self._dialog.set_decorated(False)
        self._dialog.set_modal(True)
        self._dialog.set_keep_above(True)
        self._dialog.set_default_size(344, 636)
        self._dialog.set_size_request(320, 460)
        try:
            self._dialog.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        except Exception:
            pass
        self._dialog.connect("destroy", self._on_destroy)
        self._dialog.connect("delete-event", self._on_delete)
        provider = Gtk.CssProvider()
        provider.load_from_data(CHOOSER_CSS)
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._build(title)

    def _build(self, title):
        content = self._dialog.get_content_area()
        content.set_spacing(0)
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        head.get_style_context().add_class("chooser-head")
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        title_label = Gtk.Label(label=title or ("Save file" if self.kind in ("save", "save_files") else "Select a file"))
        title_label.set_xalign(0.0)
        title_label.get_style_context().add_class("chooser-title")
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._title_label = title_label
        self._sub = Gtk.Label(label="Choose Gallery or Files")
        self._sub.set_xalign(0.0)
        self._sub.get_style_context().add_class("chooser-sub")
        titles.pack_start(title_label, False, False, 0)
        titles.pack_start(self._sub, False, False, 0)
        titles.set_hexpand(True)
        close = Gtk.Button(label="\u2715")
        close.set_relief(Gtk.ReliefStyle.NONE)
        close.set_tooltip_text("Cancel")
        close.set_size_request(48, 48)
        close.connect("clicked", lambda *_: self.cancel("close-button"))
        head.pack_start(titles, True, True, 0)
        head.pack_start(close, False, False, 0)
        content.pack_start(head, False, False, 0)

        self._outer = Gtk.Stack()
        self._outer.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._outer.set_transition_duration(90)
        if self.kind == "open" or self.kind == "folder":
            switcher = Gtk.StackSwitcher()
            switcher.set_stack(self._outer)
            switcher.set_halign(Gtk.Align.CENTER)
            content.pack_start(switcher, False, False, 0)
        self._gallery_page, self._flow = self._build_gallery_page()
        self._files_page, self._browser = self._build_files_page()
        if self.kind == "open":
            self._outer.add_titled(self._gallery_page, "gallery", "Gallery")
        self._outer.add_titled(self._files_page, "files", "Files")
        content.pack_start(self._outer, True, True, 0)
        self._status = Gtk.Label(label="")
        self._status.set_xalign(0.0)
        self._status.get_style_context().add_class("chooser-status")
        self._status.set_no_show_all(True)
        content.pack_start(self._status, False, False, 0)
        accept_label = str(self.options.get("accept_label") or
                           ("Save" if self.kind in ("save", "save_files") else "Open"))
        self._accept_id = Gtk.ResponseType.ACCEPT
        self._dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self._dialog.add_button(accept_label, self._accept_id)
        self._dialog.set_default_response(self._accept_id)
        self._dialog.connect("response", self._on_response)
        initial = fh.initial_source(self.settings, self.app_id, self.rules, self.kind)
        if initial == "gallery" and self.kind == "open":
            self._outer.set_visible_child_name("gallery")
        else:
            self._outer.set_visible_child_name("files")
        self._on_source_changed(self._outer, None)
        self._outer.connect("notify::visible-child-name", self._on_source_changed)
        self._flow.connect("child-activated", self._on_gallery_activate)
        self._schedule_thumbnails()
        self._timeout_id = GLib.timeout_add_seconds(REQUEST_TIMEOUT_S, self._on_timeout)
        if self._autotest:
            GLib.timeout_add(900, self._run_autotest)

    def _build_gallery_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.get_style_context().add_class("gallery")
        stack = Gtk.Stack()
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        flow = Gtk.FlowBox()
        flow.set_valign(Gtk.Align.START)
        flow.set_max_children_per_line(4)
        flow.set_min_children_per_line(2)
        flow.set_selection_mode(
            Gtk.SelectionMode.MULTIPLE if bool(self.options.get("multiple", False))
            else Gtk.SelectionMode.SINGLE)
        flow.set_activate_on_single_click(False)
        flow.set_row_spacing(6)
        flow.set_column_spacing(6)
        flow.set_margin_start(8)
        flow.set_margin_end(8)
        flow.set_margin_top(8)
        flow.set_margin_bottom(8)
        scroll.add(flow)
        stack.add_named(scroll, "grid")
        empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        empty.set_valign(Gtk.Align.CENTER)
        empty.set_halign(Gtk.Align.CENTER)
        empty.set_margin_start(16)
        empty.set_margin_end(16)
        label = Gtk.Label(label="No matching media in Gallery.")
        label.set_line_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        empty.pack_start(label, False, False, 0)
        browse = Gtk.Button(label="Browse Files instead")
        browse.connect("clicked", lambda *_: self._outer.set_visible_child_name("files"))
        empty.pack_start(browse, False, False, 0)
        stack.add_named(empty, "empty")
        page.pack_start(stack, True, True, 0)
        stack.set_visible_child_name("grid" if self.media else "empty")
        self._gallery_stack = stack
        return page, flow

    def _build_files_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.get_style_context().add_class("browser")
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        head.get_style_context().add_class("browser-head")
        up = Gtk.Button(label="↑")
        up.set_tooltip_text("Parent folder")
        up.connect("clicked", lambda *_: self._browser_go_up())
        home = Gtk.Button(label="⌂")
        home.set_tooltip_text("Home")
        home.connect("clicked", lambda *_: self._browser_navigate("/"))
        self._pathbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self._pathbar.get_style_context().add_class("pathbar")
        path_scroll = Gtk.ScrolledWindow()
        path_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        path_scroll.add(self._pathbar)
        path_scroll.set_hexpand(True)
        head.pack_start(up, False, False, 0)
        head.pack_start(home, False, False, 0)
        head.pack_start(path_scroll, True, True, 0)
        page.pack_start(head, False, False, 0)
        search_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_row.set_margin_start(8)
        search_row.set_margin_end(8)
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Filter this folder")
        self._search.connect("changed", lambda *_: self._browser_render())
        search_row.pack_start(self._search, True, True, 0)
        if self.kind == "folder":
            choose_folder = Gtk.Button(label="Use this folder")
            choose_folder.connect("clicked", lambda *_: self._dialog.response(self._accept_id))
            search_row.pack_start(choose_folder, False, False, 0)
        page.pack_start(search_row, False, False, 0)
        self._save_name = None
        if self.kind == "save":
            self._save_name = Gtk.Entry()
            self._save_name.get_style_context().add_class("save-name")
            self._save_name.set_placeholder_text("File name")
            current_name = str(self.options.get("current_name") or "")
            if current_name:
                self._save_name.set_text(current_name)
            self._save_name.set_margin_start(8)
            self._save_name.set_margin_end(8)
            self._save_name.set_margin_top(4)
            self._save_name.set_margin_bottom(4)
            page.pack_start(self._save_name, False, False, 0)
        elif self.kind == "save_files":
            summary = Gtk.Label(label=self._save_files_summary())
            summary.set_xalign(0.0)
            summary.set_margin_start(8)
            summary.set_margin_end(8)
            summary.set_line_wrap(True)
            page.pack_start(summary, False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(
            Gtk.SelectionMode.MULTIPLE if (self.kind == "open" and
                                           bool(self.options.get("multiple", False)))
            else Gtk.SelectionMode.SINGLE)
        self._list.connect("row-activated", self._on_file_row_activated)
        scroll.add(self._list)
        page.pack_start(scroll, True, True, 0)
        self._browser_status = Gtk.Label(label="")
        self._browser_status.set_xalign(0.0)
        self._browser_status.set_margin_start(8)
        self._browser_status.set_margin_end(8)
        page.pack_start(self._browser_status, False, False, 0)
        self._browser_render()
        return page, self

    def _save_files_summary(self):
        names = self._save_file_names()
        return "Save %d file(s) into the selected folder: %s" % (
            len(names), ", ".join(names[:6]) + ("…" if len(names) > 6 else ""))

    def _save_file_names(self):
        names = []
        try:
            raw_files = self.options.get("files", []) or []
            for raw in raw_files:
                name = fh.decode_path(raw)
                if name and "/" not in name and name not in (".", ".."):
                    names.append(name)
        except (TypeError, ValueError):
            names = []
        if not names:
            current = str(self.options.get("current_name") or "")
            if current:
                names = [os.path.basename(current)]
        return names[:MAX_SELECTED]

    # ---- Files UI -------------------------------------------------------
    def _browser_status_set(self, text):
        self._browser_status.set_text(text)

    def _browser_navigate(self, path):
        try:
            self.files.absolute_path(path)
        except fh.FileHandlerError as exc:
            self._browser_status_set(str(exc))
            return
        self.files.cwd = path or "/"
        self._search.set_text("")
        self._browser_render()

    def _browser_go_up(self):
        if self.files.cwd == "/":
            return
        parts = [p for p in self.files.cwd.split("/") if p]
        parts.pop()
        self._browser_navigate("/" + "/".join(parts) if parts else "/")

    def _browser_breadcrumb(self):
        for child in list(self._pathbar.get_children()):
            self._pathbar.remove(child)
        root = Gtk.Button(label="Home")
        root.connect("clicked", lambda *_: self._browser_navigate("/"))
        self._pathbar.pack_start(root, False, False, 0)
        cumulative = ""
        for part in [p for p in self.files.cwd.split("/") if p]:
            cumulative += "/" + part
            label = Gtk.Label(label="›")
            self._pathbar.pack_start(label, False, False, 0)
            button = Gtk.Button(label=part)
            path = cumulative
            button.connect("clicked", lambda _b, p=path: self._browser_navigate(p))
            self._pathbar.pack_start(button, False, False, 0)
        self._pathbar.show_all()

    def _browser_render(self):
        if not hasattr(self, "_list"):
            return
        self._browser_breadcrumb()
        try:
            rows = self.files.list_dir()
        except fh.FileHandlerError as exc:
            rows = []
            self._browser_status_set(str(exc))
        query = (self._search.get_text() or "").strip().lower() if hasattr(self, "_search") else ""
        if query:
            rows = [row for row in rows if query in row.name.lower()]
        for child in list(self._list.get_children()):
            self._list.remove(child)
        if not rows:
            row = Gtk.ListBoxRow()
            row.set_selectable(False)
            row.set_activatable(False)
            label = Gtk.Label(label="This folder is empty" if not query else "No matching entries")
            label.set_margin_top(18)
            label.set_margin_bottom(18)
            row.add(label)
            self._list.add(row)
        for entry in rows:
            self._list.add(self._file_row(entry))
        self._list.show_all()
        if not query:
            self._browser_status_set("%d item(s)" % len(rows))

    def _file_row(self, entry):
        row = Gtk.ListBoxRow()
        row._nuxel_entry = entry
        row.set_activatable(entry.type == "folder" or self.files.can_select(entry))
        row.set_selectable(entry.type != "symlink")
        row.get_style_context().add_class("file-row")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        icon = Gtk.Label(label="📁" if entry.type == "folder" else
                         ("🔗" if entry.type == "symlink" else _file_icon(entry.name)))
        icon.set_width_chars(2)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        name = Gtk.Label(label=entry.name)
        name.set_xalign(0.0)
        name.set_ellipsize(Pango.EllipsizeMode.END)
        name.get_style_context().add_class("file-row-name")
        if entry.type == "folder":
            meta_text = "Folder"
        else:
            size = entry.size
            units = ["B", "KB", "MB", "GB"]
            index = 0
            while size >= 1024 and index < len(units) - 1:
                size /= 1024.0
                index += 1
            meta_text = ("%.0f %s" if index == 0 else "%.1f %s") % (size, units[index])
            if entry.mime:
                meta_text += " · " + entry.mime
        meta = Gtk.Label(label=meta_text)
        meta.set_xalign(0.0)
        meta.get_style_context().add_class("file-row-meta")
        text.pack_start(name, False, False, 0)
        text.pack_start(meta, False, False, 0)
        box.pack_start(icon, False, False, 0)
        box.pack_start(text, True, True, 0)
        row.add(box)
        return row

    def _on_file_row_activated(self, _listbox, row):
        entry = getattr(row, "_nuxel_entry", None)
        if entry is None:
            return
        if entry.type == "folder":
            self._browser_navigate(entry.path)
        elif self.files.can_select(entry):
            self._dialog.response(self._accept_id)

    def _selected_file_entries(self):
        out = []
        for row in self._list.get_selected_rows():
            entry = getattr(row, "_nuxel_entry", None)
            if entry is not None and entry.type == "file":
                out.append(entry)
        return out

    # ---- Gallery UI -----------------------------------------------------
    def _schedule_thumbnails(self):
        if not self.media:
            return
        icon_theme = Gtk.IconTheme.get_default()
        placeholder = None
        try:
            placeholder = icon_theme.load_icon("image-x-generic", 96, 0)
        except Exception:
            pass
        for item in self.media:
            child = Gtk.FlowBoxChild()
            child._nuxel_media = item
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.get_style_context().add_class("thumb-box")
            image = Gtk.Image()
            image.set_size_request(THUMB_PX, THUMB_PX)
            if placeholder is not None:
                image.set_from_pixbuf(placeholder)
            else:
                image.set_from_icon_name("image-x-generic", Gtk.IconSize.DIALOG)
            label = Gtk.Label(label=item["name"])
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_max_width_chars(16)
            label.get_style_context().add_class("thumb-name")
            box.pack_start(image, True, True, 0)
            box.pack_start(label, False, False, 0)
            child.add(box)
            self._flow.add(child)
            self._thumb_queue.append((image, item["path"]))
        self._flow.show_all()
        GLib.idle_add(self._decode_batch)

    def _decode_batch(self):
        if not self._alive:
            return False
        for _ in range(3):
            if not self._thumb_queue:
                return False
            image, path = self._thumb_queue.pop(0)
            ext = os.path.splitext(path)[1].lower()
            try:
                if ext in fh.VIDEO_EXTS:
                    raise ValueError("video")
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, THUMB_PX, THUMB_PX, True)
                image.set_from_pixbuf(pixbuf)
            except Exception:
                try:
                    icon = Gtk.IconTheme.get_default().load_icon(
                        "video-x-generic" if ext in fh.VIDEO_EXTS else "image-x-generic", 96, 0)
                    image.set_from_pixbuf(icon)
                except Exception:
                    pass
        return True

    def _selected_gallery_media(self):
        out = []
        try:
            for child in self._flow.get_selected_children():
                item = getattr(child, "_nuxel_media", None)
                if item is not None:
                    out.append(item)
        except Exception:
            pass
        return out

    def _on_source_changed(self, stack, _pspec):
        name = stack.get_visible_child_name()
        if name == "gallery":
            self._sub.set_text("Real media from Gallery and the Nuxel Camera store")
        elif self.kind in ("save", "save_files"):
            self._sub.set_text("Choose a destination in Files")
        elif self.kind == "folder":
            self._sub.set_text("Choose a folder in Files")
        else:
            self._sub.set_text("Browse approved Files locations")
        self._status.hide()

    def _on_gallery_activate(self, _flow, child):
        self._dialog.response(self._accept_id)

    def _show_status(self, text):
        self._status.set_text(text)
        self._status.show()

    def _on_timeout(self):
        if self._alive:
            self._show_status("The request timed out")
            self._finish(2, [])
        return False

    def _on_destroy(self, *_args):
        self._alive = False

    def _on_delete(self, *_args):
        self.cancel("delete-event")
        return True

    def cancel(self, why="cancel"):
        if not self._alive:
            return
        self.response_code = 1
        self.source = "cancelled"
        try:
            self._dialog.response(Gtk.ResponseType.CANCEL)
        except Exception:
            self._finish(1, [])

    def close_from_portal(self):
        self._closed_by_portal = True
        self.cancel("portal-close")

    def _on_response(self, _dialog, response):
        if response == Gtk.ResponseType.CANCEL:
            self.source = "cancelled"
            self.response_code = 1
            self.result_paths = []
            self._finish(1, [])
            return
        if response != self._accept_id:
            return
        try:
            paths = self._collect_result()
        except fh.FileHandlerError as exc:
            self._show_status(str(exc))
            return
        if not paths:
            self._show_status("Select an item first.")
            return
        self.result_paths = paths
        self.response_code = 0
        self._finish(0, paths)

    def _collect_result(self):
        source = self._outer.get_visible_child_name()
        self.source = source or "files"
        if self.kind == "folder":
            path = self._browser_current_folder()
            path = fh.canonical_selection(path, must_exist=True)
            return [fh.ensure_selected_shape(path, "folder")]
        if self.kind == "save":
            target = self._browser_save_target()
            return [target]
        if self.kind == "save_files":
            return self._browser_save_targets()
        if source == "gallery":
            rows = self._selected_gallery_media()
        else:
            rows = self._selected_file_entries()
        if not rows:
            return []
        paths = []
        for row in rows[:MAX_SELECTED]:
            path = row["path"] if isinstance(row, dict) else self.files.absolute_path(row.path)
            path = fh.canonical_selection(path, must_exist=True)
            fh.ensure_selected_shape(path, "open")
            if not fh.path_matches(path, self.rules) and source == "files":
                # Portal filters are user guidance, but a Files selection that
                # the caller cannot accept is still rejected rather than
                # pretending it matched.
                continue
            paths.append(path)
        if not paths:
            raise fh.FileHandlerError("selected file does not match the request filters",
                                      "FILTER_MISMATCH")
        if not bool(self.options.get("multiple", False)) and len(paths) > 1:
            paths = paths[:1]
        return paths

    def _browser_current_folder(self):
        return self.files.absolute_path(self.files.cwd)

    def _browser_save_target(self):
        name = (self._save_name.get_text() if self._save_name is not None else "").strip()
        if not name or name in (".", "..") or "/" in name or name.startswith("."):
            raise fh.FileHandlerError("enter a safe file name", "INVALID_NAME")
        folder = self._browser_current_folder()
        target = fh.canonical_selection(os.path.join(folder, name), must_exist=False,
                                        follow_final=False)
        if os.path.exists(target):
            if os.environ.get("NUXEL_CHOOSER_AUTOTEST"):
                # The harness explicitly supplied an existing path; never use
                # this branch in normal operation.
                return target
            confirm = Gtk.MessageDialog(
                transient_for=self._dialog, modal=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Replace existing file?")
            confirm.format_secondary_text("The file already exists. The requesting app may overwrite it.")
            answer = confirm.run()
            confirm.destroy()
            if answer != Gtk.ResponseType.YES:
                raise fh.FileHandlerError("save cancelled: file exists", "EXISTS")
            return target
        return _safe_create_file(target)

    def _browser_save_targets(self):
        names = self._save_file_names()
        if not names:
            raise fh.FileHandlerError("the request supplied no file names", "INVALID_NAME")
        folder = self._browser_current_folder()
        out = []
        used = set()
        for name in names[:MAX_SELECTED]:
            if not name or "/" in name or name in (".", ".."):
                continue
            raw = fh.canonical_selection(os.path.join(folder, name), must_exist=False,
                                         follow_final=False)
            target = _collision_free(raw, used)
            used.add(target)
            out.append(_safe_create_file(target))
        if not out:
            raise fh.FileHandlerError("no safe save targets", "INVALID_NAME")
        return out

    # ---- test automation ------------------------------------------------
    def _run_autotest(self):
        if not self._alive:
            return False
        try:
            mode = self._autotest
            if mode.startswith("cancel"):
                self.cancel("autotest")
                return False
            if mode.startswith("gallery"):
                self._outer.set_visible_child_name("gallery")
                count = 2 if "multi" in mode else 1
                selected = 0
                for index in range(min(count, len(self.media))):
                    child = self._flow.get_child_at_index(index)
                    if child is not None:
                        self._flow.select_child(child)
                        selected += 1
                if not selected:
                    self.cancel("autotest-empty")
                    return False
                self._dialog.response(self._accept_id)
                return False
            if (mode.startswith("files:") or mode.startswith("save:") or
                    mode.startswith("savefiles:")):
                payload = mode.split(":", 1)[1]
                self._outer.set_visible_child_name("files")
                if mode.startswith("savefiles:"):
                    virtual = self.files.virtual_path(payload)
                    if virtual is None:
                        self.cancel("autotest-outside-root")
                        return False
                    self.files.cwd = virtual
                    self._browser_render()
                elif mode.startswith("save:"):
                    path = payload
                    virtual = self.files.virtual_path(os.path.dirname(path))
                    if virtual is None:
                        self.cancel("autotest-outside-root")
                        return False
                    self.files.cwd = virtual
                    self._browser_render()
                    if self._save_name is not None:
                        self._save_name.set_text(os.path.basename(path))
                else:
                    virtual = self.files.virtual_path(payload)
                    if virtual is None:
                        self.cancel("autotest-outside-root")
                        return False
                    self.files.cwd = os.path.dirname(virtual) or "/"
                    self._browser_render()
                    if self.kind == "folder" and os.path.isdir(payload):
                        # Directory mode: navigate INTO the requested folder;
                        # Accept then returns the current folder.
                        self.files.cwd = virtual
                        self._browser_render()
                    else:
                        for row in self._list.get_children():
                            entry = getattr(row, "_nuxel_entry", None)
                            if entry is not None and entry.path == virtual:
                                self._list.select_row(row)
                                break
                GLib.timeout_add(250, self._autotest_accept)
                return False
        except Exception as exc:  # noqa: BLE001
            _log("AUTOTEST_ERROR %s: %s" % (type(exc).__name__, exc))
            self.cancel("autotest-error")
        return False

    def _autotest_accept(self):
        if self._alive:
            self._dialog.response(self._accept_id)
        return False

    # ---- lifecycle ------------------------------------------------------
    def _finish(self, code, paths):
        if self._finished:
            return
        self._finished = True
        self._alive = False
        if self._timeout_id is not None:
            try:
                GLib.source_remove(self._timeout_id)
            except Exception:
                pass
            self._timeout_id = None
        try:
            self._dialog.destroy()
        except Exception:
            pass
        callback = self._on_done
        self._on_done = None
        if callback is not None:
            try:
                callback(code, list(paths), self.source)
            except Exception as exc:  # noqa: BLE001
                _log("DONE_CALLBACK_ERROR %s: %s" % (type(exc).__name__, exc))

    def start(self, on_done):
        self._on_done = on_done
        self._dialog.show_all()
        self._status.hide()
        self._dialog.present_with_time(Gdk.CURRENT_TIME)


def _file_icon(name):
    ext = os.path.splitext(name)[1].lower()
    if ext in fh.IMAGE_EXTS:
        return "🖼️"
    if ext in fh.VIDEO_EXTS:
        return "🎬"
    if ext in (".mp3", ".wav", ".flac", ".ogg", ".opus"):
        return "🎵"
    if ext in (".zip", ".tar", ".gz", ".bz2", ".7z"):
        return "📦"
    if ext == ".pdf":
        return "📄"
    if ext in (".txt", ".md", ".log"):
        return "📃"
    return "📄"


# ---------------------------------------------------------------------------
# D-Bus backend
# ---------------------------------------------------------------------------

class PortalRequest(dbus.service.Object):
    def __init__(self, bus, path, backend, handle):
        super().__init__(bus, path)
        self.backend = backend
        self.handle = handle

    @dbus.service.method(REQUEST_IFACE, in_signature="", out_signature="")
    def Close(self):
        self.backend.close_handle(self.handle)


class NuxelFileChooser(dbus.service.Object):
    def __init__(self, bus):
        super().__init__(bus, OBJECT_PATH)
        self.bus = bus
        self.settings = fh.load_settings()
        self.app_id = ""
        self._requests = {}
        self._choosers = {}
        self._lock = threading.Lock()

    def _reload_settings(self):
        self.settings = fh.load_settings()

    def close_handle(self, handle):
        with self._lock:
            chooser = self._choosers.get(handle)
        if chooser is not None:
            chooser.close_from_portal()

    def _run_request(self, handle, app_id, title, options, kind, reply, error):
        started = time.monotonic()
        _counts["requests"] += 1
        handle = str(handle)
        self.app_id = str(app_id or "")
        self._reload_settings()
        rules = fh.filter_rules(options)
        with self._lock:
            if len(self._choosers) >= MAX_ACTIVE_REQUESTS:
                _counts["errors"] += 1
                _log("REQUEST_REJECTED active=%d" % len(self._choosers))
                reply(dbus.UInt32(2), dbus.Dictionary({}, signature="sv"))
                return
            request = PortalRequest(self.bus, handle, self, handle)
            self._requests[handle] = request
        audit(STATE_PATH, state="observed", last_outcome="observed",
              last_source="pending", last_request={
                  "app_id": self.app_id, "kind": kind,
                  "multiple": bool(options.get("multiple", False)),
                  "filter_count": len(rules),
                  "directory": bool(options.get("directory", False)),
                  "has_current_folder": bool(options.get("current_folder")),
                  "policy": fh.resolve_policy(self.settings, self.app_id),
              })
        try:
            media = gallery_media(rules) if kind == "open" else []
            chooser = NuxelChooserDialog(self, handle, kind, str(title or ""),
                                         options, rules, media,
                                         fh.initial_source(self.settings, self.app_id,
                                                           rules, kind),
                                         app_id=self.app_id)
            with self._lock:
                self._choosers[handle] = chooser
            audit(STATE_PATH, state="presented", last_outcome="presented",
                  last_source="none", presented=True,
                  autotest=chooser._autotest.split(":", 1)[0])

            def done(code, paths, source):
                try:
                    if code == 0 and paths:
                        _counts["selected"] += 1
                        outcome = "selected"
                    elif chooser._closed_by_portal:
                        _counts["cancelled"] += 1
                        outcome = "cancelled-by-portal"
                    elif code == 1:
                        _counts["cancelled"] += 1
                        outcome = "cancelled"
                    else:
                        _counts["errors"] += 1
                        outcome = "error"
                    duration_ms = int((time.monotonic() - started) * 1000)
                    audit(STATE_PATH, state="ready", last_outcome=outcome,
                          last_source=source, presented=False,
                          selected_count=len(paths), duration_ms=duration_ms,
                          last_request={
                              "app_id": self.app_id, "kind": kind,
                              "outcome": outcome, "source": source,
                              "selected_count": len(paths),
                              "duration_ms": duration_ms,
                          })
                    if code != 0 or not paths:
                        reply(dbus.UInt32(2 if code not in (0, 1) else 1),
                              dbus.Dictionary({}, signature="sv"))
                        return
                    results = {"uris": dbus.Array(
                        [dbus.String(fh.file_uri(path)) for path in paths], signature="s")}
                    if kind in ("save", "save_files"):
                        results["writable"] = dbus.Boolean(True)
                    reply(dbus.UInt32(0), dbus.Dictionary(results, signature="sv"))
                except Exception:  # noqa: BLE001
                    _log(traceback.format_exc())
                    try:
                        reply(dbus.UInt32(2), dbus.Dictionary({}, signature="sv"))
                    except Exception:
                        pass
                finally:
                    with self._lock:
                        self._requests.pop(handle, None)
                        self._choosers.pop(handle, None)
                    try:
                        request.remove_from_connection()
                    except Exception:
                        pass

            chooser.start(done)
        except Exception as exc:  # noqa: BLE001
            _counts["errors"] += 1
            _log("REQUEST_ERROR %s: %s" % (type(exc).__name__, exc))
            _log(traceback.format_exc())
            audit(STATE_PATH, state="ready", last_outcome="error",
                  last_error=type(exc).__name__, presented=False,
                  last_source="error")
            with self._lock:
                self._requests.pop(handle, None)
                self._choosers.pop(handle, None)
            try:
                request.remove_from_connection()
            except Exception:
                pass
            try:
                reply(dbus.UInt32(2), dbus.Dictionary({}, signature="sv"))
            except Exception:
                pass

    @dbus.service.method(IFACE, in_signature="osssa{sv}", out_signature="ua{sv}",
                         async_callbacks=("reply", "error"))
    def OpenFile(self, handle, app_id, parent_window, title, options,
                 reply=None, error=None):
        opts = dict(options)
        opts["_parent"] = str(parent_window or "")
        kind = "folder" if bool(opts.get("directory", False)) else "open"
        self._run_request(handle, app_id, title, opts, kind, reply, error)

    @dbus.service.method(IFACE, in_signature="osssa{sv}", out_signature="ua{sv}",
                         async_callbacks=("reply", "error"))
    def SaveFile(self, handle, app_id, parent_window, title, options,
                 reply=None, error=None):
        opts = dict(options)
        opts["_parent"] = str(parent_window or "")
        self._run_request(handle, app_id, title, opts, "save", reply, error)

    @dbus.service.method(IFACE, in_signature="osssa{sv}", out_signature="ua{sv}",
                         async_callbacks=("reply", "error"))
    def SaveFiles(self, handle, app_id, parent_window, title, options,
                  reply=None, error=None):
        opts = dict(options)
        opts["_parent"] = str(parent_window or "")
        self._run_request(handle, app_id, title, opts, "save_files", reply, error)


def print_status() -> int:
    doc = {}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as handle:
            doc = json.load(handle)
    except (OSError, ValueError):
        doc = {"schema_version": 2, "service": BUS_NAME,
               "backend": "nuxel-portal-chooser", "state": "not-running"}
    doc.setdefault("service", BUS_NAME)
    doc.setdefault("backend", "nuxel-portal-chooser")
    doc["portal"] = fh.portal_status()
    print(json.dumps(doc, indent=2, sort_keys=True))
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if "--status" in argv:
        return print_status()
    if "--version" in argv:
        print("%s %s" % (BUS_NAME, SERVICE_VERSION))
        return 0
    normalize_environment()
    GLib.set_prgname("nuxel-portal-chooser")
    GLib.set_application_name("Nuxel File Chooser")
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    try:
        Gtk.init()
    except Exception as exc:  # noqa: BLE001
        _log("GTK_INIT_FAILED %s" % exc)
        return 3
    bus = dbus.SessionBus()
    try:
        name = dbus.service.BusName(BUS_NAME, bus, do_not_queue=True)
    except dbus.exceptions.NameExistsException:
        _log("NAME_ALREADY_OWNED %s" % BUS_NAME)
        return 0
    chooser = NuxelFileChooser(bus)
    try:
        os.unlink(STATE_PATH)
    except OSError:
        pass
    audit(STATE_PATH, state="ready", last_outcome="idle", last_source="none",
          presented=False, selected_count=0,
          autotest=os.environ.get("NUXEL_CHOOSER_AUTOTEST", "").split(":", 1)[0])
    _log("READY %s %s pid=%d" % (BUS_NAME, SERVICE_VERSION, os.getpid()))
    try:
        Gtk.main()
    finally:
        try:
            del chooser
        except Exception:
            pass
        try:
            del name
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

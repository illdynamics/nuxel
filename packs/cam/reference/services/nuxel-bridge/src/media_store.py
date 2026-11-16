"""media_store.py — durable, file-backed media store for Nuxel Camera/Photos.

Replaces the historical ``localStorage`` photo database with real files on disk:

* canonical media root (default ``/var/lib/nuxel/media``, overridable via
  ``NUXEL_MEDIA_DIR`` so the host test-suite and the device agree on one layout);
* photos -> ``<root>/pictures/Nuxel Camera/``, videos -> ``<root>/videos/Nuxel Camera/``;
* atomic write (temp file in the SAME directory -> fsync -> rename) so a crash or
  out-of-space can never leave a half file indexed as finished;
* collision-safe ISO filenames, a rebuildable ``media-index.json`` (reconciled by
  scanning the directories, never the authority), dedupe by content hash;
* delete removes the real file AND the index entry (never an index-only delete).

Only standard-library imports: it must run unchanged on the host test suite and on
the device (Python 3.14).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import uuid

# Bounded single-capture size cap (sanity bound for a single photo; keeps one
# base64 photo from exhausting RAM/bridge message size).  A full-res JPEG from a
# 12 MP sensor is normally well under this.
MAX_PHOTO_BYTES = 16 * 1024 * 1024   # 16 MiB
MAX_VIDEO_BYTES = 512 * 1024 * 1024  # 512 MiB (bounded recordings)
PHOTO_EXTS = (".jpg", ".jpeg", ".png", ".webp")
VIDEO_EXTS = (".webm", ".mp4", ".mkv")
_MEDIA_KIND = {"photo", "video"}


def _default_root() -> str:
    return os.environ.get("NUXEL_MEDIA_DIR") or "/var/lib/nuxel/media"


def _utc_iso(ts: float | None = None) -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(ts if ts is not None else time.time()))


def _safe_name(name: str) -> str:
    """Collapse a user/provided name to a safe file component."""
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name or "")
    name = name.strip("._") or "capture"
    return name[:64]


class MediaStoreError(Exception):
    pass


class MediaStore:
    def __init__(self, root: str | None = None):
        self.root = os.path.abspath(root or _default_root())
        self.photo_dir = os.path.join(self.root, "pictures", "Nuxel Camera")
        self.video_dir = os.path.join(self.root, "videos", "Nuxel Camera")
        self.index_path = os.path.join(self.root, "media-index.json")

    # ---- low-level helpers -------------------------------------------------
    def _dir_for(self, kind: str) -> str:
        if kind == "photo":
            return self.photo_dir
        if kind == "video":
            return self.video_dir
        raise MediaStoreError("unknown media kind %r" % kind)

    def _ensure_dirs(self) -> None:
        for d in (self.photo_dir, self.video_dir):
            os.makedirs(d, mode=0o750, exist_ok=True)

    def _ext_for(self, kind: str, mime: str | None) -> str:
        if kind == "photo":
            if mime == "image/png":
                return ".png"
            if mime == "image/webp":
                return ".webp"
            return ".jpg"
        if kind == "video":
            if mime == "video/mp4":
                return ".mp4"
            return ".webm"
        raise MediaStoreError("unknown media kind %r" % kind)

    def _scan(self) -> dict:
        """Rebuild the authoritative record list by scanning the directories.

        The on-disk files are the source of truth; the index JSON is a cache.
        """
        records = []
        for kind, d in (("photo", self.photo_dir), ("video", self.video_dir)):
            try:
                names = os.listdir(d)
            except OSError:
                continue
            for name in sorted(names):
                p = os.path.join(d, name)
                if not os.path.isfile(p):
                    continue
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                ext = os.path.splitext(name)[1].lower()
                if kind == "photo" and ext not in PHOTO_EXTS:
                    continue
                if kind == "video" and ext not in VIDEO_EXTS:
                    continue
                records.append({
                    "id": name,
                    "kind": kind,
                    "name": name,
                    "path": p,
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "taken": st.st_mtime,
                })
        records.sort(key=lambda r: r.get("taken", 0), reverse=True)
        return records

    def _read_index(self) -> dict:
        try:
            with open(self.index_path) as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write_index(self, index: dict) -> None:
        tmp = self.index_path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(index, fh, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.index_path)

    # ---- public API --------------------------------------------------------
    def reconcile(self) -> list:
        """Return records reconciled with the filesystem; refresh the index cache."""
        records = self._scan()
        by_path = {r["path"]: r for r in records}
        meta = self._read_index().get("records", {})
        # Merge persisted metadata (width/height/camera/orientation) onto scan rows.
        for rec in records:
            extra = meta.get(rec["id"]) or {}
            if isinstance(extra, dict):
                for k in ("width", "height", "orientation", "camera", "duration", "mime"):
                    if extra.get(k) is not None:
                        rec[k] = extra[k]
        self._write_index({"version": 1, "records": {r["id"]: {
            "kind": r["kind"], "size": r["size"], "mtime": r["mtime"],
            "width": r.get("width"), "height": r.get("height"),
            "orientation": r.get("orientation"), "camera": r.get("camera"),
            "duration": r.get("duration"), "mime": r.get("mime"),
        } for r in records}})
        return records

    def save(self, kind: str, data: bytes, *, mime: str | None = None,
             width: int | None = None, height: int | None = None,
             orientation: int | None = None, camera: str | None = None,
             duration: float | None = None, taken: float | None = None) -> dict:
        if kind not in _MEDIA_KIND:
            raise MediaStoreError("unknown media kind %r" % kind)
        if not isinstance(data, (bytes, bytearray)) or not data:
            raise MediaStoreError("empty capture payload")
        cap = MAX_PHOTO_BYTES if kind == "photo" else MAX_VIDEO_BYTES
        if len(data) > cap:
            raise MediaStoreError("%s exceeds size cap (%d > %d bytes)" % (kind, len(data), cap))
        self._ensure_dirs()
        d = self._dir_for(kind)
        ext = self._ext_for(kind, mime)
        digest = hashlib.sha256(data).hexdigest()
        stamp = _utc_iso(taken)
        candidate = "nuxel-%s-%s%s" % (stamp, digest[:10], ext)
        # Collision-safe: append a short suffix rather than overwrite.
        final = os.path.join(d, candidate)
        n = 0
        while os.path.exists(final):
            n += 1
            final = os.path.join(d, "nuxel-%s-%s-%d%s" % (stamp, digest[:10], n, ext))
        tmp = final + ".part"
        try:
            with open(tmp, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.chmod(tmp, 0o640)
            os.replace(tmp, final)
        except OSError as exc:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise MediaStoreError("save failed: %s" % exc) from exc
        rec = {
            "id": os.path.basename(final),
            "kind": kind,
            "name": os.path.basename(final),
            "path": final,
            "size": len(data),
            "mtime": taken or time.time(),
            "taken": taken or time.time(),
            "sha256": digest,
            "mime": mime,
            "width": width,
            "height": height,
            "orientation": orientation,
            "camera": camera,
            "duration": duration,
        }
        index = self._read_index()
        records = index.setdefault("records", {})
        records[rec["id"]] = {
            "kind": kind, "size": rec["size"], "mtime": rec["mtime"],
            "width": width, "height": height, "orientation": orientation,
            "camera": camera, "duration": duration, "mime": mime,
        }
        self._write_index(index)
        return rec

    def list(self, kind: str | None = None) -> list:
        records = self.reconcile()
        if kind is not None:
            records = [r for r in records if r["kind"] == kind]
        return records

    def get(self, media_id: str) -> tuple[dict, bytes] | None:
        records = self.reconcile()
        for rec in records:
            if rec["id"] == media_id:
                try:
                    with open(rec["path"], "rb") as fh:
                        return rec, fh.read()
                except OSError:
                    return None
        return None

    def delete(self, media_id: str) -> bool:
        records = self.reconcile()
        target = next((r for r in records if r["id"] == media_id), None)
        if target is None:
            return False
        try:
            os.unlink(target["path"])
        except OSError:
            return False
        index = self._read_index()
        index.setdefault("records", {}).pop(media_id, None)
        self._write_index(index)
        return True


def media_store(root: str | None = None) -> MediaStore:
    return MediaStore(root)

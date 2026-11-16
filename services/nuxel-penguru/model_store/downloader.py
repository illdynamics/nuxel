#!/usr/bin/env python3
"""Resumable, verified model downloader.

State machine:
  NOT_INSTALLED -> USER_CONFIRMED -> CHECK_SPACE -> DOWNLOADING
  -> VERIFY_SIGNATURE -> VERIFY_HASHES -> VERIFY_FORMAT
  -> VERIFY_LICENSE_ACK -> ATOMIC_INSTALL -> SELF_TEST -> READY
Any failure -> QUARANTINED/ERROR with partial files cleaned.

The hash in the manifest is trusted only because the manifest is signed; an
unsigned manifest can download for inspection but can never reach READY.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
import urllib.request
from typing import Any, Dict, Optional

from common import paths
from common import registry as reg

_LOCK = threading.RLock()
_JOBS: Dict[str, Dict[str, Any]] = {}
THREADS: Dict[str, threading.Thread] = {}
MIN_FREE_AFTER = 1 << 30  # 1 GiB safety reserve


def _job_dir(job_id: str) -> str:
    return os.path.join(paths.DOWNLOAD_ROOT, job_id)


def _set(job: Dict[str, Any], state: str, detail: str = "", progress: float = 0.0):
    job.update(state=state, detail=detail, progress=round(progress, 4),
               updated=time.time())


def _free_bytes(path: str) -> int:
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize


def start_download(registry: reg.ModelRegistry, model_id: str, variant_id: str,
                   license_accepted: bool, license_revision: str) -> Dict[str, Any]:
    m = next((x for x in registry.manifests()
              if x["model_id"] == model_id and x["variant_id"] == variant_id), None)
    if m is None:
        return {"ok": False, "error": "unknown_package"}
    if not license_accepted or license_revision != m["source_revision"]:
        return {"ok": False, "error": "license_ack_required",
                "detail": "accept the exact revision's license notice first"}
    job_id = "%s-%s-%d" % (model_id, variant_id, int(time.time() * 1000))
    job = {"job_id": job_id, "model_id": model_id, "variant_id": variant_id,
           "state": "user_confirmed", "progress": 0.0, "detail": "",
           "total_bytes": sum(f["size_bytes"] for f in m["files"]),
           "received_bytes": 0, "updated": time.time()}
    with _LOCK:
        _JOBS[job_id] = job
    t = threading.Thread(target=_run, args=(job, registry, m), daemon=True)
    THREADS[job_id] = t
    t.start()
    return {"ok": True, "job_id": job_id, "state": job["state"]}


def download_status(job_id: str) -> Dict[str, Any]:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return {"ok": False, "error": "unknown_job"}
        return {"ok": True, "job": dict(job)}


def cancel_download(job_id: str) -> Dict[str, Any]:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return {"ok": False, "error": "unknown_job"}
        job["cancel"] = True
        return {"ok": True, "job_id": job_id}


def _run(job: Dict[str, Any], registry: reg.ModelRegistry, m: Dict[str, Any]):
    jdir = _job_dir(job["job_id"])
    try:
        os.makedirs(jdir, mode=0o750, exist_ok=True)
        _set(job, "check_space")
        need = job["total_bytes"] * 2 + MIN_FREE_AFTER
        if _free_bytes(paths.STATE_DIR) < need:
            raise RuntimeError("insufficient storage")
        _set(job, "downloading")
        for f in m["files"]:
            if job.get("cancel"):
                raise RuntimeError("cancelled by owner")
            dst = os.path.join(jdir, f["path"] + ".part")
            final = os.path.join(jdir, f["path"])
            if os.path.exists(final):
                continue
            _download(f["path"], m["source_url"], dst, f["size_bytes"], job)
            h = hashlib.sha256()
            with open(dst, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != f["sha256"]:
                raise RuntimeError("sha256 mismatch for %s" % f["path"])
            os.replace(dst, final)
        _set(job, "verify_signature")
        signed, why = reg.verify_signature(m, registry.trusted_key)
        if not signed:
            # By design: refuse READY without release trust.  Keep the bytes
            # quarantined for owner review but never selectable.
            _set(job, "quarantined", "manifest is not signed by a trusted key: " + why,
                 1.0)
            raise RuntimeError("manifest_untrusted")
        _set(job, "verify_hashes", progress=1.0)
        _set(job, "verify_format")
        if m["format"] != "GGUF":
            _set(job, "quarantined", "non-GGUF download is not installed by this path", 1.0)
            raise RuntimeError("format_not_supported")
        _set(job, "atomic_install")
        target = os.path.join(registry.package_dir(m))
        os.makedirs(os.path.dirname(target), mode=0o750, exist_ok=True)
        if os.path.exists(target):
            raise RuntimeError("target already exists; refusing to overwrite")
        os.replace(jdir, target)
        _set(job, "self_test")
        job["state"] = "ready_for_self_test"
        job["package_dir"] = target
        _set(job, "ready_for_self_test", "package verified; runtime self-test required",
             1.0)
    except Exception as exc:  # noqa: BLE001
        partial = os.path.join(jdir)
        try:
            if os.path.isdir(partial):
                for name in os.listdir(partial):
                    if name.endswith(".part"):
                        os.unlink(os.path.join(partial, name))
        except OSError:
            pass
        with _LOCK:
            if job.get("state") not in ("quarantined",):
                _set(job, "error", str(exc))


def _download(rel: str, base_url: str, dst: str, size: int, job: Dict[str, Any]):
    have = os.path.getsize(dst) if os.path.exists(dst) else 0
    headers = {}
    if have:
        headers["Range"] = "bytes=%d-" % have
    req = urllib.request.Request(base_url, headers=headers)
    mode = "ab" if have else "wb"
    with urllib.request.urlopen(req, timeout=60) as resp, open(dst, mode) as out:
        if have and resp.status != 206:
            have = 0
            out.close()
            out = open(dst, "wb")
        while True:
            if job.get("cancel"):
                raise RuntimeError("cancelled by owner")
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            have += len(chunk)
            with _LOCK:
                job["received_bytes"] = have
                job["progress"] = min(1.0, have / float(size or 1))
    if have != size:
        raise RuntimeError("size mismatch: got %d expected %d" % (have, size))


def delete_model(registry: reg.ModelRegistry, model_id: str, variant_id: str
                 ) -> Dict[str, Any]:
    m = next((x for x in registry.manifests()
              if x["model_id"] == model_id and x["variant_id"] == variant_id), None)
    if m is None:
        return {"ok": False, "error": "unknown_package"}
    d = registry.package_dir(m)
    if not os.path.isdir(d):
        return {"ok": False, "error": "not_installed"}
    # Only remove inside the immutable package directory (never a parent).
    if not os.path.abspath(d).startswith(os.path.abspath(paths.MODELS_DIR) + os.sep):
        return {"ok": False, "error": "refused_path"}
    for name in os.listdir(d):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            os.unlink(p)
    try:
        os.rmdir(d)
    except OSError:
        return {"ok": False, "error": "directory_not_empty"}
    return {"ok": True, "deleted": model_id + "/" + variant_id}

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
import uuid
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
    signed, why = registry.download_eligibility(m)
    if not signed:
        return {"ok": False, "error": "manifest_untrusted", "detail": why}
    with _LOCK:
        if any(j["state"] not in ("ready", "staged", "error", "cancelled", "quarantined") for j in _JOBS.values()):
            return {"ok": False, "error": "download_busy"}
    job_id = "%s-%s-%s" % (model_id, variant_id, uuid.uuid4().hex)
    job = {"job_id": job_id, "model_id": model_id, "variant_id": variant_id,
           "state": "user_confirmed", "progress": 0.0, "detail": "",
           "total_bytes": sum(f["size_bytes"] for f in m["files"]),
           "received_bytes": 0, "updated": time.time()}
    with _LOCK:
        if any(j["state"] not in ("ready", "staged", "error", "cancelled", "quarantined") for j in _JOBS.values()):
            return {"ok": False, "error": "download_busy"}
        _JOBS[job_id] = job
    t = threading.Thread(target=_run, args=(job, registry, m), daemon=True)
    THREADS[job_id] = t
    t.start()
    return {"ok": True, "job_id": job_id, "state": job["state"]}


def start_beak_download(component_id: str, consent: bool) -> Dict[str, Any]:
    """Stage exactly one allowlisted component, never install or execute it."""
    from beak.catalog import listing
    item = next((x for x in listing() if x["id"] == component_id), None)
    if item is None:
        return {"ok": False, "error": "unknown_beak_component"}
    if item.get("download_allowed") is not True:
        return {"ok": False, "error": "source_unverified",
                "detail": "Automatic installation is disabled until a compatible pinned source, checksum and license are verified"}
    if consent is not True:
        return {"ok": False, "error": "owner_review_required"}
    with _LOCK:
        if any(j["state"] not in ("ready", "staged", "error", "cancelled", "quarantined") for j in _JOBS.values()):
            return {"ok": False, "error": "download_busy"}
        jid = "beak-%s-%s" % (component_id, uuid.uuid4().hex)
        job = {"job_id": jid, "component_id": component_id, "state": "user_confirmed",
               "progress": 0., "detail": "", "received_bytes": 0,
               "total_bytes": 0, "updated": time.time()}
        _JOBS[jid] = job
        thread = threading.Thread(target=_beak_stage, args=(job, item), daemon=True)
        THREADS[jid] = thread
        thread.start()
    return {"ok": True, "job_id": jid, "state": job["state"]}


def _beak_stage(job: Dict[str, Any], item: Dict[str, Any]):
    """Bounded HTTPS streaming, SHA256 receipt, and quarantine-only destination."""
    import urllib.parse
    jid = job["job_id"]
    base = os.path.join(paths.STATE_DIR, "beak", "staging")
    dst_dir = os.path.join(base, jid)
    max_bytes = int(item["max_bytes"])
    try:
        os.makedirs(base, mode=0o700, exist_ok=True)
        state = os.path.realpath(paths.STATE_DIR)
        if (os.path.islink(base) or os.path.islink(os.path.dirname(base)) or
                not os.path.realpath(base).startswith(state + os.sep)):
            raise RuntimeError("Refusing untrusted staging path or symlink")
        os.makedirs(dst_dir, mode=0o700, exist_ok=False)
        if _free_bytes(paths.STATE_DIR) < max_bytes + MIN_FREE_AFTER:
            raise RuntimeError("Not enough free space for worst-case file size and 1 GiB reserve")
        partial = os.path.join(dst_dir, item["filename"] + ".part")
        request = urllib.request.Request(item["url"], headers={"User-Agent": "Nuxel-Beak/0.9"})
        _set(job, "downloading", "Downloading into untrusted staging; not installable")
        digest = hashlib.sha256()
        received = 0
        with urllib.request.urlopen(request, timeout=30) as src:
            desturl = urllib.parse.urlparse(src.url)
            if desturl.scheme != "https" or desturl.username or desturl.password:
                raise RuntimeError("Non-HTTPS/credentialed redirect blocked")
            with open(partial, "xb") as out:
                while True:
                    if job.get("cancel"):
                        raise RuntimeError("cancelled by owner")
                    block = src.read(262144)
                    if not block:
                        break
                    received += len(block)
                    if received > max_bytes or _free_bytes(paths.STATE_DIR) < MIN_FREE_AFTER:
                        raise RuntimeError("Component size/storage budget exceeded")
                    out.write(block)
                    digest.update(block)
                    job["received_bytes"] = received
                    _set(job, "downloading", "Staged bytes: %d" % received,
                         min(0.99, received / max_bytes))
        if received == 0:
            raise RuntimeError("Empty component rejected")
        os.replace(partial, os.path.join(dst_dir, item["filename"]))
        receipt = {"component_id": item["id"], "source": item["url"],
                   "sha256_observed_untrusted": digest.hexdigest(),
                   "size_bytes": received, "trusted": False, "runtime_ready": False,
                   "created_at": time.time()}
        with open(os.path.join(dst_dir, "STAGING-RECEIPT.json"), "w") as out:
            json.dump(receipt, out, indent=2)
        _set(job, "staged", "Downloaded and hashed. NOT installed or trusted; requires pinned signature, license and runtime self-test.", 1.)
    except Exception as exc:
        shutil.rmtree(dst_dir, ignore_errors=True)
        _set(job, "cancelled" if job.get("cancel") else "error", str(exc))


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
        if job.get("cancel"):
            raise RuntimeError("cancelled by owner")
        os.makedirs(jdir, mode=0o750, exist_ok=True)
        _set(job, "check_space")
        need = job["total_bytes"] + MIN_FREE_AFTER
        if _free_bytes(paths.STATE_DIR) < need:
            raise RuntimeError("insufficient storage")
        target = registry.package_dir(m)
        if os.path.isdir(target):
            st = registry.verify_installed(m)
            if st.status not in (reg.STATUS_VERIFIED_SIGNED, reg.STATUS_READY):
                raise RuntimeError("existing package failed verification; delete before retry")
            _record_license(m, target)
            _self_test(job, m, target)
            return
        _set(job, "downloading")
        for f in m["files"]:
            if job.get("cancel"):
                raise RuntimeError("cancelled by owner")
            dst = os.path.join(jdir, f["path"] + ".part")
            final = os.path.join(jdir, f["path"])
            if os.path.exists(final):
                continue
            if "inline_utf8" in f:
                with open(dst, "wb") as stream:
                    stream.write(f["inline_utf8"].encode("utf-8"))
            else:
                _download(f["path"], f.get("url", m["source_url"]), dst, f["size_bytes"], job)
            h = hashlib.sha256()
            with open(dst, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    if job.get("cancel"):
                        raise RuntimeError("cancelled by owner")
                    h.update(chunk)
            if h.hexdigest() != f["sha256"]:
                raise RuntimeError("sha256 mismatch for %s" % f["path"])
            with open(dst, "rb") as fh:
                if m["format"] == "GGUF" and fh.read(4) != b"GGUF":
                    raise RuntimeError("invalid GGUF header")
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
        if m["format"] not in ("GGUF", "ONNX_CLASSIFIER", "WHISPER"):
            _set(job, "quarantined", "non-GGUF download is not installed by this path", 1.0)
            raise RuntimeError("format_not_supported")
        _set(job, "atomic_install")
        if job.get("cancel"):
            raise RuntimeError("cancelled by owner")
        target = os.path.join(registry.package_dir(m))
        os.makedirs(os.path.dirname(target), mode=0o750, exist_ok=True)
        if os.path.exists(target):
            raise RuntimeError("target already exists; refusing to overwrite")
        os.replace(jdir, target)
        _record_license(m, target)
        _self_test(job, m, target)
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
                _set(job, "cancelled" if job.get("cancel") else "error", str(exc))


def _record_license(manifest, target):
    staged = os.path.join(target, "license-acceptance.json.tmp")
    with open(staged, "w") as fh:
        json.dump({"revision": manifest["source_revision"], "at": time.time(),
                   "notice": manifest["license"]}, fh)
    os.replace(staged, os.path.join(target, "license-acceptance.json"))


def _self_test(job, manifest, target):
    if job.get("cancel"):
        raise RuntimeError("cancelled by owner")
    if manifest.get("format") == "WHISPER":
        from voice.speech import self_test
        _set(job, "self_test", "Loading local speech decoder", 1.0)
        self_test(target)
        if job.get("cancel"):
            raise RuntimeError("cancelled by owner")
        record = {"result": "pass", "engine": "whisper.cpp", "at": time.time(),
                  "manifest_sha256": hashlib.sha256(reg.canonical_manifest_bytes(manifest)).hexdigest()}
        with open(os.path.join(target, "self-test.json.tmp"), "w") as stream:
            json.dump(record, stream)
        os.replace(os.path.join(target, "self-test.json.tmp"), os.path.join(target, "self-test.json"))
        _set(job, "ready", "Local speech decoder loaded and inference completed", 1.0)
        return
    if manifest.get("format") == "ONNX_CLASSIFIER":
        from sonarbird.router import Classifier
        _set(job, "self_test", "Loading MiniLM and verifying real sentence embeddings", 1.0)
        classifier = Classifier(target)
        scores, margin = classifier.classify("Implement a Python sorting function")
        if not scores or max(scores, key=scores.get) != "CODE":
            raise RuntimeError("MiniLM classifier self-test failed: " + str(classifier._load_error))
        classifier.unload()
        if job.get("cancel"):
            raise RuntimeError("cancelled by owner")
        record = {"result": "pass", "engine": "onnxruntime", "version": "1.32.0",
                  "at": time.time(), "manifest_sha256": hashlib.sha256(reg.canonical_manifest_bytes(manifest)).hexdigest()}
        with open(os.path.join(target, "self-test.json.tmp"), "w") as stream:
            json.dump(record, stream)
        os.replace(os.path.join(target, "self-test.json.tmp"), os.path.join(target, "self-test.json"))
        _set(job, "ready", "MiniLM signature, hashes and real routing inference verified", 1.0)
        return
    from runtime.llama_cpp.adapter import LlamaCppRuntime
    from common.runtime_api import RuntimeProfile
    if job.get("cancel"):
        raise RuntimeError("cancelled by owner")
    _set(job, "self_test", "Loading exact package and generating test tokens", 1.0)
    rt = LlamaCppRuntime(runner=False)
    result = rt.self_test(manifest, target, RuntimeProfile(
        engine="llama.cpp", package_format="GGUF", threads=4, context_limit=4096), max_tokens=8)
    if job.get("cancel"):
        raise RuntimeError("cancelled by owner")
    if result.get("result") != "pass" or (result.get("loaded") or {}).get("architecture") != manifest["architecture"]:
        raise RuntimeError("runtime self-test failed: " + str(result.get("code", "architecture mismatch")))
    record = {"manifest_sha256": hashlib.sha256(reg.canonical_manifest_bytes(manifest)).hexdigest(), "result": "pass", "engine": "llama.cpp", "version": manifest["runtime"]["min_commit"],
              "at": time.time(), "load_ms": result["loaded"].get("load_ms"),
              "output_sha256": hashlib.sha256(result["output"].encode()).hexdigest()}
    with open(os.path.join(target, "self-test.json.tmp"), "w") as fh:
        json.dump(record, fh)
    os.replace(os.path.join(target, "self-test.json.tmp"), os.path.join(target, "self-test.json"))
    _set(job, "ready", "Signature, SHA-256, architecture and real generation verified", 1.0)


def _download(rel: str, base_url: str, dst: str, size: int, job: Dict[str, Any]):
    for attempt in range(3):
        try:
            if job.get("cancel"):
                raise RuntimeError("cancelled by owner")
            have = os.path.getsize(dst) if os.path.exists(dst) else 0
            headers = {"Range": "bytes=%d-" % have} if have else {}
            req = urllib.request.Request(base_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                if not resp.url.startswith("https://"):
                    raise RuntimeError("insecure redirect refused")
                if have and resp.status == 206:
                    if not resp.headers.get("Content-Range", "").startswith("bytes %d-" % have):
                        raise RuntimeError("invalid range response")
                else:
                    have = 0
                with open(dst, "ab" if have else "wb") as out:
                    while True:
                        if job.get("cancel"):
                            raise RuntimeError("cancelled by owner")
                        chunk = resp.read(1 << 18)
                        if not chunk:
                            break
                        have += len(chunk)
                        if have > size:
                            raise RuntimeError("download exceeds declared size")
                        out.write(chunk)
                        with _LOCK:
                            job["received_bytes"] = have
                            job["progress"] = min(1.0, have / float(size))
            if have != size:
                raise OSError("incomplete transfer")
            return
        except (OSError, TimeoutError):
            if attempt == 2 or job.get("cancel"):
                raise
            time.sleep(2 ** attempt)


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
    if not os.path.abspath(d).startswith(os.path.abspath(registry.models_root) + os.sep):
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

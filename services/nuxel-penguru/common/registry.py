#!/usr/bin/env python3
"""PenGuru model registry and package integrity.

Manifests are DATA, never instructions.  A package becomes READY only when a
trusted detached Ed25519 signature over the canonical manifest matches and
every listed file matches its recorded size and SHA-256.  With no trusted key
configured, the strongest possible state is VERIFIED_UNSIGNED, which the
service reports honestly and never treats as READY.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

MODEL_IDS = ("chatbird", "codebird", "sonarbird")
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SAFE_FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,200}$")

STATUS_NOT_INSTALLED = "not_installed"
STATUS_DOWNLOADING = "downloading"
STATUS_VERIFIED_UNSIGNED = "verified_unsigned"
STATUS_VERIFIED_SIGNED = "verified_signed"
STATUS_SELF_TESTED = "self_tested"
STATUS_READY = "ready"
STATUS_NOT_PORTABLE = "not_portable"
STATUS_ERROR = "error"
STATUS_QUARANTINED = "quarantined"


class ManifestError(ValueError):
    pass


def canonical_manifest_bytes(manifest: Dict[str, Any]) -> bytes:
    """Canonical bytes over which a release signature is computed.

    Excludes only the ``signature`` member.  Keys are sorted and separators
    compact so a re-serialised manifest yields the same bytes.
    """
    body = {k: v for k, v in manifest.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_manifest(m: Any) -> List[str]:
    """Return every schema problem; empty means structurally valid."""
    errors: List[str] = []
    if not isinstance(m, dict):
        return ["manifest is not an object"]
    if m.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    model_id = m.get("model_id")
    if model_id not in MODEL_IDS:
        errors.append("model_id must be one of %s" % (MODEL_IDS,))
    if not isinstance(m.get("variant_id"), str) or not SAFE_ID.match(m.get("variant_id") or ""):
        errors.append("variant_id must be a safe slug")
    if m.get("format") not in ("GGUF", "ONNX_GENAI", "ONNX_CLASSIFIER"):
        errors.append("format must be GGUF, ONNX_GENAI or ONNX_CLASSIFIER")
    revision = m.get("source_revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        errors.append("source_revision must be an immutable 40-hex commit")
    url = m.get("source_url", "")
    if not isinstance(url, str) or not url.startswith("https://"):
        errors.append("source_url must be https")
    if "/resolve/main/" in (url or ""):
        errors.append("source_url must not be a mutable resolve/main reference")
    files = m.get("files")
    if not isinstance(files, list) or not files:
        errors.append("files must be a non-empty list")
    else:
        for f in files:
            if not isinstance(f, dict):
                errors.append("file entry is not an object")
                continue
            path = f.get("path")
            if not isinstance(path, str) or not SAFE_FILE.match(path):
                errors.append("file path is not a safe relative filename: %r" % (path,))
            size = f.get("size_bytes")
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
                errors.append("file size_bytes must be a positive integer")
            if not _valid_sha256(f.get("sha256")):
                errors.append("file sha256 must be 64 lowercase hex characters")
    rt = m.get("runtime")
    if not isinstance(rt, dict) or rt.get("engine") not in (
            "llama.cpp", "onnxruntime-genai", "onnxruntime"):
        errors.append("runtime.engine is invalid")
    lic = m.get("license")
    if not isinstance(lic, dict) or not isinstance(lic.get("spdx"), str):
        errors.append("license.spdx is required")
    return errors


def _load_pubkey(path: str) -> Optional[Any]:
    if not path or not os.path.exists(path):
        return None
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey)
        from cryptography.hazmat.primitives import serialization
        with open(path, "rb") as fh:
            return serialization.load_pem_public_key(fh.read())
    except Exception:  # noqa: BLE001 - absent key = no trust, never a bypass
        return None


def verify_signature(manifest: Dict[str, Any], pubkey_path: str) -> Tuple[bool, str]:
    """Verify the detached Ed25519 signature over canonical manifest bytes."""
    sig = manifest.get("signature")
    if not isinstance(sig, dict) or sig.get("alg") != "ed25519":
        return False, "manifest is unsigned"
    key = _load_pubkey(pubkey_path)
    if key is None:
        return False, "no trusted manifest key configured"
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        raw = base64.b64decode(sig.get("value", ""), validate=True)
        key.verify(raw, canonical_manifest_bytes(manifest))
        return True, "signature ok"
    except Exception as exc:  # noqa: BLE001
        return False, "signature invalid: %s" % type(exc).__name__


def sha256_file(path: str, limit: Optional[int] = None) -> Tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            n += len(chunk)
            if limit is not None and n > limit:
                raise ManifestError("file grew beyond declared size")
            h.update(chunk)
    return h.hexdigest(), n


@dataclass
class PackageState:
    model_id: str
    variant_id: str
    status: str
    detail: str = ""
    revision: str = ""
    manifest: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "variant_id": self.variant_id,
            "status": self.status,
            "detail": self.detail,
            "revision": self.revision,
        }


class ModelRegistry:
    """Read-only view over packaged manifests and installed model packages."""

    def __init__(self, manifests_dir: str, models_root: str,
                 trusted_key: Optional[str] = None,
                 allow_test_keys: bool = False):
        self._hash_cache = {}
        self.allow_test_keys = allow_test_keys
        self.manifests_dir = manifests_dir
        self.models_root = models_root
        self.trusted_key = trusted_key or os.environ.get(
            "NUXEL_PENGURU_MANIFEST_KEY", "/etc/nuxel/penguru/manifest-pubkey.pem")

    def manifests(self) -> List[Dict[str, Any]]:
        out = []
        try:
            names = sorted(os.listdir(self.manifests_dir))
        except OSError:
            return out
        for name in names:
            if not name.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.manifests_dir, name)) as fh:
                    m = json.load(fh)
            except (OSError, ValueError):
                continue
            if validate_manifest(m):
                continue
            out.append(m)
        return out

    def package_dir(self, m: Dict[str, Any]) -> str:
        return os.path.join(self.models_root, m["model_id"], m["source_revision"],
                            m["variant_id"])

    def download_eligibility(self, manifest: Dict[str, Any]) -> Tuple[bool, str]:
        signed, reason = verify_signature(manifest, self.trusted_key)
        if signed and manifest.get("trust") == "test_signed" and not self.allow_test_keys:
            return False, "Test signature requires explicit test-build authorization; not a release package"
        if not signed:
            return False, reason
        if manifest["format"] != "GGUF":
            return False, "This installer supports GGUF only"
        return True, "Trusted manifest; owner must accept the exact revision's license"

    def verify_installed(self, m: Dict[str, Any]) -> PackageState:
        d = self.package_dir(m)
        if not os.path.isdir(d):
            return PackageState(m["model_id"], m["variant_id"],
                                STATUS_NOT_INSTALLED,
                                "package is not installed", m["source_revision"], m)
        signed, why = verify_signature(m, self.trusted_key)
        if signed and not self.allow_test_keys and \
                m.get("trust") == "test_signed":
            signed, why = False, "test signature is not a release trust root"
        for f in m["files"]:
            p = os.path.join(d, f["path"])
            if not os.path.isfile(p):
                return PackageState(m["model_id"], m["variant_id"], STATUS_ERROR,
                                    "missing file %s" % f["path"],
                                    m["source_revision"], m)
            st = os.stat(p, follow_symlinks=False)
            if os.path.islink(p):
                raise ManifestError("symlink model file refused")
            stamp = (st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
            cached = self._hash_cache.get(p)
            if cached and cached[0] == stamp:
                digest, size = cached[1]
            else:
                digest, size = sha256_file(p, f["size_bytes"])
                self._hash_cache[p] = (stamp, (digest, size))
            if size != f["size_bytes"]:
                return PackageState(m["model_id"], m["variant_id"], STATUS_ERROR,
                                    "size mismatch for %s" % f["path"],
                                    m["source_revision"], m)
            if digest != f["sha256"]:
                return PackageState(m["model_id"], m["variant_id"], STATUS_ERROR,
                                    "sha256 mismatch for %s" % f["path"],
                                    m["source_revision"], m)
        state = STATUS_VERIFIED_SIGNED if signed else STATUS_VERIFIED_UNSIGNED
        rec = self.self_test_record(m)
        if rec and rec.get("result") == "pass" and signed:
            state = STATUS_READY
        return PackageState(m["model_id"], m["variant_id"], state,
                            "bytes match manifest; " + why,
                            m["source_revision"], m)

    def cards(self) -> List[Dict[str, Any]]:
        """Exactly three logical model cards with their package variants."""
        cards: Dict[str, Dict[str, Any]] = {
            mid: {"model_id": mid, "variants": []} for mid in MODEL_IDS
        }
        for m in self.manifests():
            st = self.verify_installed(m)
            downloadable, download_reason = self.download_eligibility(m)
            card = cards.setdefault(m["model_id"], {"model_id": m["model_id"],
                                                    "variants": []})
            card["name"] = m.get("name", m["model_id"])
            card["role"] = m.get("role")
            card["variants"].append({
                "variant_id": m["variant_id"],
                "format": m["format"],
                "architecture": m.get("architecture"),
                "quantization": m.get("quantization"),
                "source_repo": m.get("source_repo"),
                "files": m["files"],
                "source_revision": m.get("source_revision"),
                "size_bytes": sum(f["size_bytes"] for f in m["files"]),
                "engine": m["runtime"]["engine"],
                "license": m.get("license", {}),
                "status": st.status,
                "detail": st.detail,
                "redistribution": (m.get("license") or {}).get("redistribution"),
                "self_test": self.self_test_record(m),
                "download_allowed": downloadable,
                "download_reason": download_reason,
            })
        for mid in MODEL_IDS:
            cards[mid].setdefault("variants", [])
            cards[mid]["available"] = any(
                v["status"] in (STATUS_READY, STATUS_SELF_TESTED, STATUS_VERIFIED_SIGNED)
                for v in cards[mid]["variants"])
        return [cards[mid] for mid in MODEL_IDS]

    def self_test_record(self, m: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        path = os.path.join(self.package_dir(m), "self-test.json")
        try:
            with open(path) as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            return None
        if not isinstance(doc, dict):
            return None
        return {k: doc.get(k) for k in ("result", "engine", "version", "at",
                                         "load_ms", "prompt", "output_sha256")}

    def ready_manifest(self, model_id: str, variant_id: Optional[str] = None
                       ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Return a manifest only when the package has passed its self-test."""
        for m in self.manifests():
            if m["model_id"] != model_id:
                continue
            if variant_id and m["variant_id"] != variant_id:
                continue
            st = self.verify_installed(m)
            if st.status == STATUS_READY:
                return m, "ready"
        return None, "no verified package with a passing self-test"

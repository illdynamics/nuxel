#!/usr/bin/env python3
"""Registry/manifest trust tests.  No model bytes, device or network needed."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SVC = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(SVC, "..", ".."))
sys.path.insert(0, SVC)

from common import registry  # noqa: E402

FAIL = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


def write_manifest(d, m):
    with open(os.path.join(d, m["variant_id"] + ".json"), "w") as fh:
        json.dump(m, fh)


def sample():
    return {
        "schema_version": 1, "model_id": "chatbird", "role": "chat",
        "name": "ChatBird", "variant_id": "gguf-q4km", "format": "GGUF",
        "architecture": "llama", "quantization": "Q4_K_M",
        "source_repo": "x/y",
        "source_revision": "a" * 40,
        "source_url": "https://example.invalid/resolve/%s/m.gguf" % ("a" * 40),
        "files": [{"path": "m.gguf", "size_bytes": 4, "sha256": ""}],
        "runtime": {"engine": "llama.cpp", "context_limit": 4096},
        "license": {"spdx": "Apache-2.0", "redistribution": "review_required"},
        "signature": None,
    }


def main():
    print("[manifests] packaged manifests are structurally valid and immutable")
    reg0 = registry.ModelRegistry(os.path.join(SVC, "manifests"), "/nonexistent")
    found = {m["model_id"]: m for m in reg0.manifests()}
    check(set(found) == {"chatbird", "codebird"}, "exactly ChatBird and CodeBird GGUF manifests ship")
    for mid, m in found.items():
        check(not registry.validate_manifest(m), "%s manifest schema ok" % mid)
        check("resolve/main" not in m["source_url"], "%s pins an immutable revision URL" % mid)
        check(len(m["source_revision"]) == 40, "%s records a 40-hex revision" % mid)
    check(any(c["model_id"] == "sonarbird" for c in reg0.cards()),
          "SonarBird is a logical card even with no approved package yet")
    check(len(reg0.cards()) == 3, "exactly three logical model cards")

    print("[manifests] hostile manifests are refused")
    bad = sample()
    bad["source_url"] = "https://example.invalid/resolve/main/m.gguf"
    check("source_url must not be a mutable resolve/main reference"
          in registry.validate_manifest(bad), "resolve/main is refused")
    bad = sample()
    bad["files"][0]["path"] = "../../etc/passwd"
    check(any("not a safe relative filename" in e for e in registry.validate_manifest(bad)),
          "path traversal in file list is refused")
    bad = sample()
    bad["source_revision"] = "main"
    check(any("40-hex" in e for e in registry.validate_manifest(bad)),
          "mutable branch name is refused as a revision")

    with tempfile.TemporaryDirectory() as root:
        mdir = os.path.join(root, "manifests")
        models = os.path.join(root, "models")
        os.makedirs(mdir)
        data = b"GGUF"
        m = sample()
        m["files"][0]["sha256"] = hashlib.sha256(data).hexdigest()
        write_manifest(mdir, m)
        reg = registry.ModelRegistry(mdir, models, trusted_key=os.path.join(root, "no.pem"))
        st = reg.verify_installed(m)
        check(st.status == registry.STATUS_NOT_INSTALLED, "absent package is not_installed")

        pkg = reg.package_dir(m)
        os.makedirs(pkg)
        with open(os.path.join(pkg, "m.gguf"), "wb") as fh:
            fh.write(data)
        st = reg.verify_installed(m)
        check(st.status == registry.STATUS_VERIFIED_UNSIGNED,
              "correct bytes with no trusted key are VERIFIED_UNSIGNED, never READY")
        check(reg.ready_manifest("chatbird")[0] is None,
              "unsigned package is not selectable for inference")

        with open(os.path.join(pkg, "m.gguf"), "wb") as fh:
            fh.write(b"EVIL")
        st = reg.verify_installed(m)
        check(st.status == registry.STATUS_ERROR and "sha256" in st.detail,
              "corrupt bytes are an error")

        # Sign with a temporary Ed25519 key.
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        except Exception:
            check(True, "signature path skipped: cryptography unavailable")
            print("\n%s" % ("ALL PASS" if not FAIL else "%d FAILURES" % len(FAIL)))
            return 1 if FAIL else 0
        key = Ed25519PrivateKey.generate()
        pub = os.path.join(root, "pub.pem")
        with open(pub, "wb") as fh:
            fh.write(key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo))
        with open(os.path.join(pkg, "m.gguf"), "wb") as fh:
            fh.write(data)
        m["signature"] = {"alg": "ed25519",
                          "value": base64.b64encode(
                              key.sign(registry.canonical_manifest_bytes(m))).decode()}
        write_manifest(mdir, m)
        reg = registry.ModelRegistry(mdir, models, trusted_key=pub)
        st = reg.verify_installed(m)
        check(st.status == registry.STATUS_VERIFIED_SIGNED,
              "trusted signature + correct bytes is VERIFIED_SIGNED")
        check(reg.ready_manifest("chatbird")[0] is None,
              "signed package without a passing self-test is still not selectable")
        with open(os.path.join(pkg, "self-test.json"), "w") as fh:
            json.dump({"result": "pass", "engine": "llama.cpp"}, fh)
        got, why = reg.ready_manifest("chatbird")
        check(got is not None and why == "ready",
              "signed package with passing self-test is READY")

        m2 = dict(m)
        m2["files"] = [dict(m["files"][0], sha256="0" * 64)]
        write_manifest(mdir, m2)
        os.rename(os.path.join(mdir, "gguf-q4km.json"),
                  os.path.join(mdir, "tampered.json"))
        st = registry.ModelRegistry(mdir, models, trusted_key=pub).verify_installed(m2)
        check(st.status == registry.STATUS_ERROR,
              "payload changed after signing is refused (signature is over content)")

    print("\n%s" % ("ALL PASS" if not FAIL else "%d FAILURES" % len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Sign (or verify) a PenGuru model manifest with an Ed25519 release key.

Usage:
  sign-manifest.py sign   <manifest.json> <private.pem> [--test-key]
  sign-manifest.py verify <manifest.json> <public.pem>

The signature covers canonical manifest bytes excluding the signature member.
A test signature is labelled so it cannot be mistaken for a release trust root.
"""
from __future__ import annotations

import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SVC = os.path.dirname(HERE)
sys.path.insert(0, SVC)

from common import registry  # noqa: E402


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    op, mpath, keypath = argv[1], argv[2], argv[3]
    with open(mpath) as fh:
        m = json.load(fh)
    if op == "verify":
        ok, why = registry.verify_signature(m, keypath)
        print(("OK " if ok else "FAIL ") + why)
        return 0 if ok else 1
    if op != "sign":
        return 2
    from cryptography.hazmat.primitives import serialization
    with open(keypath, "rb") as fh:
        key = serialization.load_pem_private_key(fh.read(), password=None)
    test = "--test-key" in argv
    # The scope is part of the signed body so a test signature cannot be
    # re-labelled as a release signature without invalidating it.
    m["trust"] = "test_signed" if test else "release_signed"
    sig = key.sign(registry.canonical_manifest_bytes(m))
    m["signature"] = {"alg": "ed25519", "value": base64.b64encode(sig).decode(),
                      "key_id": os.path.basename(keypath),
                      "scope": "test" if test else "release"}
    with open(mpath, "w") as fh:
        json.dump(m, fh, indent=2)
        fh.write("\n")
    print("signed", mpath, "scope=%s" % m["signature"]["scope"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

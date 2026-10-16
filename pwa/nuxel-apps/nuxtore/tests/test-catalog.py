#!/usr/bin/env python3
"""NuxTore offline test suite — signatures, digests, safety gates, canonical form.

    python3 pwa/nuxel-apps/nuxtore/tests/test-catalog.py

Standard library only (no pytest, no network).  Every assertion maps to a claim
made in docs/beta-finalization/apps/NUXTORE.md:

  T1  Ed25519 matches the RFC 8032 test vectors (verifier is real)
  T2  Python and JavaScript canonicalise the signed payload identically
  T3  A staged + signed catalog verifies; tampering with a field breaks it
  T4  Tampering with a staged file is caught by the digest check
  T5  An unsigned package is refused, and only becomes installable after the
      policy allows it AND the operator types the package id
  T6  The shipped catalog in this repository passes; the deliberately unsigned
      demo entry is refused; external-publish policy is false
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, ".."))
TOOLS = os.path.join(APP, "tools")
sys.path.insert(0, TOOLS)

import ed25519_ref as ed            # noqa: E402
import nuxtore_common as nc         # noqa: E402
import nuxtore_verify as verify_mod  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name, ("  — " + detail) if detail else ""))
    return cond


def t1_rfc8032():
    vectors = [
        ("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
         "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
         "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
        ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
         "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
         "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
        ("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
         "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025", "af82",
         "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"),
    ]
    ok = True
    for seed_hex, pub_hex, msg_hex, sig_hex in vectors:
        seed, pub = bytes.fromhex(seed_hex), bytes.fromhex(pub_hex)
        msg, sig = bytes.fromhex(msg_hex), bytes.fromhex(sig_hex)
        ok &= ed.publickey(seed) == pub
        ok &= ed.signature(msg, seed, pub) == sig
        ok &= ed.checkvalid(sig, msg, pub) is True
        bad = bytearray(sig)
        bad[5] ^= 0x40
        ok &= ed.checkvalid(bytes(bad), msg, pub) is False
    return check("T1 ed25519 matches RFC 8032 vectors (sign, verify, reject tampered)", ok)


def t2_cross_language_canonical():
    payload = {"schema_version": 1, "id": "org.nuxel.Test", "nested": {"b": 2, "a": [3, 1]},
               "flag": True, "none": None, "size": 4096}
    py = nc.canonical(payload).decode("ascii")
    if not shutil.which("node"):
        check("T2 python/JS canonical JSON identical", True, "node not available — skipped")
        return True
    js = subprocess.run(
        ["node", "-e",
         "const C=require(process.argv[1]);process.stdout.write(C.canonicalJson(JSON.parse(process.argv[2])))",
         os.path.join(APP, "js", "nuxtore-crypto.js"), json.dumps(payload)],
        capture_output=True, text=True)
    return check("T2 python/JS canonical JSON identical", js.returncode == 0 and js.stdout == py,
                 js.stdout.strip() or js.stderr.strip())


def make_fixture(tmp, signed=True):
    """Stage one tiny app into a temp NuxTore app dir; return (app_dir, catalog_path)."""
    root = os.path.join(tmp, "root")
    app_src = os.path.join(root, "pwa", "nuxel-apps", "fixture")
    os.makedirs(os.path.join(app_src, "js"))
    open(os.path.join(app_src, "index.html"), "w").write("<h1>fixture</h1>")
    open(os.path.join(app_src, "js", "fixture.js"), "w").write("console.log('fixture')\n")
    app = os.path.join(tmp, "app")
    os.makedirs(os.path.join(app, "catalog", "bundles"))
    os.makedirs(os.path.join(app, "catalog", "keys"))
    seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    pub = ed.publickey(seed)
    open(os.path.join(app, "catalog", "keys", "fixture-key.ed25519.pub"), "w").write(pub.hex() + "\n")
    files = nc.walk_app(app_src)
    digest = nc.bundle_digest(files)
    pkg = {
        "id": "org.nuxel.Fixture", "name": "Fixture", "version": "1.0.0", "category": "tools",
        "summary": "fixture package", "description": "fixture", "license": "GPL-3.0-or-later",
        "size_bytes": sum(f["size"] for f in files), "file_count": len(files),
        "sha256": digest, "bundle": "bundles/org.nuxel.Fixture-1.0.0.bundle.json",
        "source": {"type": "local-bundle", "uri": "pwa/nuxel-apps/fixture", "provenance": "test fixture"},
        "install": {"type": "pwa", "app_id": "org.nuxel.Fixture",
                    "start_url": "/pwa/nuxel-apps/fixture/index.html", "mode": "staged"},
        "requires": [], "capabilities": [], "state_hint": "available",
    }
    if signed:
        pkg["signature"] = {"alg": "ed25519", "key_id": "fixture-key",
                            "value": ed.b64e(ed.signature(nc.canonical(pkg), seed, pub))}
    nc.save_json(os.path.join(app, "catalog", "bundles",
                              "org.nuxel.Fixture-1.0.0.bundle.json"), files)
    cat = {"schema_version": 1, "catalog_id": "fixture", "generated": "2026-01-01T00:00:00Z",
           "publisher": {"name": "fixture", "key_id": "fixture-key"},
           "policy": {"require_signature": True, "allow_unsigned_with_confirmation": True,
                      "allow_http": False, "allow_external_publish": False,
                      "max_package_bytes": 1 << 20, "allowed_source_types": ["local-bundle"]},
           "packages": [pkg]}
    path = os.path.join(app, "catalog", "nuxtore-catalog.json")
    nc.save_json(path, cat)
    return app, path, root


def t3_signature_tamper(tmp):
    app, cat, root = make_fixture(os.path.join(tmp, "t3"), signed=True)
    results, ok = verify_mod.verify(cat, root, (), app)
    good = check("T3a staged+signature-valid catalog verifies", ok and results[0]["verdict"] == "SIGNED_VERIFIED",
                 results[0]["verdict"])
    doc = nc.load_json(cat)
    doc["packages"][0]["summary"] = "tampered summary"          # digest still valid, signature must break
    nc.save_json(cat, doc)
    results, ok = verify_mod.verify(cat, root, (), app)
    tamper = check("T3b a changed field breaks the signature", results[0]["verdict"] == "SIGNATURE_INVALID",
                   results[0]["verdict"])
    return good and tamper


def t4_digest_tamper(tmp):
    app, cat, root = make_fixture(os.path.join(tmp, "t4"), signed=True)
    victim = os.path.join(root, "pwa", "nuxel-apps", "fixture", "js", "fixture.js")
    open(victim, "w").write("console.log('fixture MUTATED')\n")
    results, ok = verify_mod.verify(cat, root, (), app)
    return check("T4 a tampered staged file is caught by the digest check",
                 results[0]["verdict"] == "DIGEST_MISMATCH", results[0]["verdict"])


def t5_unsigned_gate(tmp):
    app, cat, root = make_fixture(os.path.join(tmp, "t5"), signed=False)
    results, ok = verify_mod.verify(cat, root, (), app)
    refused = check("T5a unsigned package is refused without confirmation",
                    results[0]["verdict"] == "UNSIGNED_REFUSED", results[0]["verdict"])
    results2, ok2 = verify_mod.verify(cat, root, ("org.nuxel.Fixture",), app)
    allowed = check("T5b unsigned package installs only after explicit confirmation",
                    results2[0]["verdict"] == "UNSIGNED_ALLOWED", results2[0]["verdict"])
    # and the JS gate must agree with the Python gate
    if shutil.which("node"):
        js = subprocess.run(["node", os.path.join(HERE, "test-catalog.js")],
                            capture_output=True, text=True)
        allowed = check("T5c JS install gate agrees with the Python gate",
                        js.returncode == 0, (js.stdout or js.stderr).strip()[-200:]) and allowed
    return refused and allowed


def t6_shipped_catalog():
    cat = os.path.join(APP, "catalog", "nuxtore-catalog.json")
    if not os.path.exists(cat):
        return check("T6 shipped catalog verified", False, "run tools/nuxtore-stage.py first")
    results, ok = verify_mod.verify(cat, nc.START, ())
    by_id = {r["id"]: r for r in results}
    a = check("T6a shipped catalog verifies without integrity failures", ok,
              "%d packages" % len(results))
    b = check("T6b every signed package in the shipped catalog verifies",
              all(r["verdict"] in ("SIGNED_VERIFIED", "UNSIGNED_REFUSED") for r in results),
              ", ".join(sorted(set(r["verdict"] for r in results))))
    c = check("T6c the deliberately unsigned demo entry is refused",
              by_id.get("org.example.UnsignedDemo", {}).get("verdict") == "UNSIGNED_REFUSED",
              by_id.get("org.example.UnsignedDemo", {}).get("verdict", "missing"))
    doc = nc.load_json(cat)
    d = check("T6d external publishing is structurally forbidden in the policy",
              doc["policy"]["allow_external_publish"] is False and doc["policy"]["allow_http"] is False)
    return a and b and c and d


def main():
    print("NuxTore offline test suite")
    with tempfile.TemporaryDirectory() as tmp:
        t1_rfc8032()
        t2_cross_language_canonical()
        t3_signature_tamper(tmp)
        t4_digest_tamper(tmp)
        t5_unsigned_gate(tmp)
    t6_shipped_catalog()
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        print("failed: %s" % ", ".join(FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Verify the NuxTore local catalog offline — signature, provenance, digests.

It never trusts the catalog.  For every package it

  * re-hashes every file listed in the bundle from the working tree,
  * recomputes the bundle digest and compares it with the digest in the catalog,
  * verifies the Ed25519 signature over the canonical package payload,
  * applies the catalog policy (signature required, no HTTP, size cap,
    allowed source types) and reports the install verdict.

Verdicts
    SIGNED_VERIFIED      signature valid, digest valid, policy satisfied -> installable
    UNSIGNED_REFUSED     no signature and policy does not allow unsigned installs
    UNSIGNED_ALLOWED     no signature, policy allows it AND --confirm-unsigned was passed
    DIGEST_MISMATCH      a file on disk does not match the recorded digest   (FAIL)
    SIGNATURE_INVALID    the signature does not verify over the payload      (FAIL)
    POLICY_VIOLATION     HTTP source / oversize / unknown source type        (FAIL)

Exit status: 0 when nothing failed, 1 when any package FAILed, 2 on usage error.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ed25519_ref as ed          # noqa: E402
import nuxtore_common as nc       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, ".."))
DEFAULT_CATALOG = os.path.join(APP, "catalog", "nuxtore-catalog.json")
ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def ascii_ok(value):
    try:
        value.encode("ascii")
        return True
    except (UnicodeEncodeError, AttributeError):
        return False


def verify(catalog_path, root, confirm_unsigned=(), app=None):
    app = app or APP
    cat = nc.load_json(catalog_path)
    policy = cat.get("policy", {})
    results = []

    if cat.get("schema_version") != 1:
        return [{"id": "-", "verdict": "POLICY_VIOLATION",
                 "detail": "unsupported catalog schema_version"}], False

    for pkg in cat.get("packages", []):
        pid = pkg.get("id", "?")
        problems = []
        notes = []

        # ---- structural / policy checks (cheap, before any hashing) ----
        for field in ("id", "name", "version", "sha256", "bundle", "source", "install"):
            if field not in pkg:
                problems.append("missing field %s" % field)
        if not ID_RE.match(pid or ""):
            problems.append("package id is not a safe ASCII identifier")
        src = pkg.get("source", {})
        if src.get("type") not in policy.get("allowed_source_types", ["local-bundle"]):
            problems.append("source type %r not allowed by policy" % src.get("type"))
        for key, val in src.items():
            if isinstance(val, str) and "http://" in val:
                problems.append("http source URI refused by policy (allow_http=false)")
        if pkg.get("size_bytes", 0) > policy.get("max_package_bytes", 1 << 62):
            problems.append("package exceeds max_package_bytes")
        for field in ("id", "name", "version", "summary", "description", "sha256",
                      "bundle", "license"):
            if isinstance(pkg.get(field), str) and not ascii_ok(pkg[field]):
                problems.append("signed field %s must be ASCII (canonical form)" % field)

        # ---- bundle + digest ----
        files = None
        if not problems:
            bpath = os.path.join(app, "catalog", pkg["bundle"])
            if not os.path.exists(bpath):
                problems.append("bundle manifest missing: %s" % pkg["bundle"])
            else:
                files = nc.load_json(bpath)
                if nc.bundle_digest(files) != pkg["sha256"]:
                    problems.append("bundle digest does not match package sha256")
                missing = mismatched = 0
                for entry in files:
                    full = os.path.join(root, entry["path"])
                    if not os.path.exists(full):
                        missing += 1
                        continue
                    if nc.sha256_file(full) != entry["sha256"] or \
                       os.path.getsize(full) != entry["size"]:
                        mismatched += 1
                if missing:
                    problems.append("%d of %d listed files are missing from the tree"
                                    % (missing, len(files)))
                if mismatched:
                    problems.append("%d of %d listed files have a different digest"
                                    % (mismatched, len(files)))
                notes.append("%d files, %d bytes" % (len(files), pkg.get("size_bytes", 0)))

        # ---- signature ----
        sig = pkg.get("signature")
        signed_ok = False
        if problems:
            pass
        elif not sig:
            notes.append("no signature (unsigned package)")
        else:
            key_id = sig.get("key_id", "")
            pub_path = os.path.join(app, "catalog", "keys", "%s.ed25519.pub" % key_id)
            if sig.get("alg") != "ed25519":
                problems.append("unsupported signature algorithm %r" % sig.get("alg"))
            elif not os.path.exists(pub_path):
                problems.append("unknown signing key %r (no public key on device)" % key_id)
            else:
                pub = bytes.fromhex(open(pub_path).read().strip())
                payload = {k: v for k, v in pkg.items() if k != "signature"}
                if not ascii_ok(nc.canonical(payload).decode("ascii", "ignore")):
                    pass
                try:
                    raw = ed.b64d(sig.get("value", ""))
                except Exception:
                    raw = b""
                if not ed.checkvalid(raw, nc.canonical(payload), pub):
                    problems.append("ed25519 signature does not verify over the payload")
                else:
                    signed_ok = True
                    notes.append("signed by %s" % key_id)

        # ---- verdict ----
        if problems and any("digest" in p or "digest" in p for p in problems):
            verdict = "DIGEST_MISMATCH"
        elif problems and any("signature" in p for p in problems):
            verdict = "SIGNATURE_INVALID"
        elif problems:
            verdict = "POLICY_VIOLATION"
        elif signed_ok:
            verdict = "SIGNED_VERIFIED"
        elif pid in confirm_unsigned and policy.get("allow_unsigned_with_confirmation"):
            verdict = "UNSIGNED_ALLOWED"
        else:
            verdict = "UNSIGNED_REFUSED"

        results.append({
            "id": pid, "version": pkg.get("version", "?"), "verdict": verdict,
            "installable": verdict in ("SIGNED_VERIFIED", "UNSIGNED_ALLOWED"),
            "notes": "; ".join(notes + problems),
            "problems": problems,
        })

    failed = any(r["verdict"] in ("DIGEST_MISMATCH", "SIGNATURE_INVALID",
                                  "POLICY_VIOLATION") for r in results)
    return results, not failed


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verify the NuxTore catalog offline")
    ap.add_argument("--catalog", default=DEFAULT_CATALOG)
    ap.add_argument("--root", default=nc.START, help="workspace root the bundle paths are relative to")
    ap.add_argument("--confirm-unsigned", action="append", default=[],
                    metavar="PKG_ID", help="explicitly confirm one unsigned package")
    ap.add_argument("--app", default=None, help="NuxTore app dir (defaults to this tool's app)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--require-signature", action="store_true",
                    help="treat UNSIGNED_REFUSED as a failure too")
    args = ap.parse_args(argv)

    results, clean = verify(args.catalog, args.root, tuple(args.confirm_unsigned), args.app)
    if args.json:
        import json
        print(json.dumps({"catalog": args.catalog, "ok": clean,
                          "packages": results}, indent=2))
    else:
        print("NuxTore catalog verification — %s" % args.catalog)
        for r in results:
            flag = "OK " if r["installable"] else ("!! " if r["verdict"].endswith(("MISMATCH", "INVALID", "VIOLATION")) else "-- ")
            print("  %s%-24s %-8s %-17s %s" % (flag, r["id"], r["version"],
                                               r["verdict"], r["notes"]))
        print("  => %s" % ("all packages verified" if clean else "INTEGRITY FAILURE"))
    hard_fail = not clean
    if args.require_signature and any(r["verdict"] == "UNSIGNED_REFUSED" for r in results):
        hard_fail = True
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())

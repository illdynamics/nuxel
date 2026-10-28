#!/usr/bin/env python3
"""Stage Nuxel apps into the NuxTore local catalog and sign them (offline).

WHAT IT DOES (no network, ever)
-------------------------------
  1. reads  catalog/package-sources.json   (which app dirs the catalog offers)
  2. walks each app dir and writes a content-addressed bundle manifest
     catalog/bundles/<id>-<version>.bundle.json  [ {path,sha256,size}, … ]
  3. computes the package digest = SHA-256 of the canonical bundle file list
  4. signs each package with Ed25519 over canonical(package minus signature)
  5. writes catalog/nuxtore-catalog.json

This tool NEVER publishes, uploads, or submits anything: the mission forbids
external publishing and store submission.  The catalog is a local artefact that
ships inside the OS image.

USAGE
    python3 nuxtore-stage.py                 # re-stage + re-sign the catalog
    python3 nuxtore-stage.py --check         # stage in memory, report drift only
    python3 nuxtore-stage.py --gen-key       # create a fresh DEV key pair
    python3 nuxtore-stage.py --key <path>

KEY POLICY — read this before using the shipped key
    catalog/keys/nuxel-beta-dev.key.txt is a PUBLISHED DEVELOPMENT FIXTURE.  It
    signs nothing of value, it protects nothing, and it is in the repository on
    purpose so the offline verifier and its tests are reproducible.  It is not a
    trust anchor and must never be used for a production catalog; a production
    catalog uses a key whose private half never enters the repository.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ed25519_ref as ed          # noqa: E402
import nuxtore_common as nc       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, ".."))
CATALOG = os.path.join(APP, "catalog")
SOURCES = os.path.join(CATALOG, "package-sources.json")
OUT = os.path.join(CATALOG, "nuxtore-catalog.json")


def load_or_gen_key(path, gen=False):
    if os.path.exists(path):
        doc = nc.load_json(path)
        return bytes.fromhex(doc["seed_hex"]), true_like(doc.get("test_fixture"))
    if not gen:
        raise SystemExit("no signing key at %s — run --gen-key" % path)
    seed = os.urandom(32)
    pub = ed.publickey(seed)
    nc.save_json(path, {
        "comment": ("PUBLISHED TEST FIXTURE — not a trust anchor, protects nothing. "
                    "Private half is in the repository on purpose so the offline "
                    "verifier and its tests are reproducible."),
        "test_fixture": True,
        "seed_hex": seed.hex(),
        "public_hex": pub.hex(),
    })
    return seed, True


def true_like(v):
    return bool(v)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-key", action="store_true")
    ap.add_argument("--check", action="store_true", help="report drift, write nothing")
    ap.add_argument("--key", default=os.path.join(CATALOG, "keys", "nuxel-beta-dev.key.txt"))
    args = ap.parse_args(argv)

    seed, _fixture = load_or_gen_key(args.key, gen=args.gen_key)
    if args.gen_key:
        print("# dev key pair written to %s" % args.key)
        return 0

    src = nc.load_json(SOURCES)
    pub = ed.publickey(seed)
    key_id = src["publisher"]["key_id"]
    pub_path = os.path.join(CATALOG, "keys", "%s.ed25519.pub" % key_id)
    if not args.check:
        with open(pub_path, "w") as fh:
            fh.write(pub.hex() + "\n")

    packages, drift = [], []
    for s in src["packages"]:
        app_dir = os.path.join(nc.START, s["app_dir"])
        if not os.path.isdir(app_dir):
            print("!! missing app dir %s" % s["app_dir"], file=sys.stderr)
            return 1
        files = nc.walk_app(app_dir)
        digest = nc.bundle_digest(files)
        bundle_rel = "bundles/%s-%s.bundle.json" % (s["id"], s["version"])
        pkg = {
            "id": s["id"], "name": s["name"], "version": s["version"],
            "category": s["category"], "summary": s["summary"],
            "description": s["description"],
            "license": s.get("license", "GPL-3.0-or-later (Nuxel project)"),
            "size_bytes": sum(f["size"] for f in files),
            "file_count": len(files),
            "sha256": digest,
            "bundle": bundle_rel,
            "source": s["source"],
            "install": s["install"],
            "requires": s.get("requires", []),
            "capabilities": s.get("capabilities", []),
            "state_hint": s.get("state_hint", "available"),
        }
        # Every package, including the deliberately unsigned refusal fixture,
        # needs its content bundle: the verifier must be able to re-hash it and
        # then still refuse installation on the signature gate.
        if not args.check:
            nc.save_json(os.path.join(CATALOG, bundle_rel), files)
        elif os.path.exists(os.path.join(CATALOG, bundle_rel)):
            old = nc.load_json(os.path.join(CATALOG, bundle_rel))
            if old != files:
                drift.append(s["id"])
        if s.get("unsigned"):
            packages.append(pkg)                     # deliberately unsigned demo entry
            continue
        pkg["signature"] = {
            "alg": "ed25519",
            "key_id": key_id,
            "value": ed.b64e(ed.signature(nc.canonical(pkg), seed, pub)),
        }
        packages.append(pkg)

    catalog = {
        "schema_version": 1,
        "catalog_id": src["catalog_id"],
        "generated": src["generated"],
        "publisher": src["publisher"],
        "policy": src["policy"],
        "notice": ("Local, offline-first catalog. NuxTore never publishes or submits "
                   "packages to any external store; every package is staged from this "
                   "repository and hash-pinned here."),
        "packages": packages,
    }
    if args.check:
        if drift:
            print("DRIFT: %s" % ", ".join(drift))
            return 1
        print("no drift — catalog bundles match the working tree")
        return 0
    nc.save_json(OUT, catalog)
    print("staged %d packages -> %s" % (len(packages), OUT))
    for p in packages:
        print("  %-26s %-8s %s%s" % (p["id"], p["version"], p["sha256"][:16],
                                      "" if "signature" in p else "  (UNSIGNED)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

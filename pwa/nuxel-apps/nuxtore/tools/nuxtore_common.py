"""Shared canonicalisation + bundle-digest rules for NuxTore (std-lib only).

CANONICAL FORM (the exact bytes a signature covers)
---------------------------------------------------
  json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

`ensure_ascii=True` is load-bearing: the browser side canonicalises with
`JSON.stringify` over recursively sorted keys, which emits UTF-8 verbatim and
never \\uXXXX-escapes.  The catalog schema therefore restricts every
signature-covered string field to printable ASCII, so both encoders emit the
identical bytes.  Anything non-ASCII must live outside the signed payload.

BUNDLE DIGEST
-------------
A package's `sha256` is the SHA-256 of the canonical JSON of its file list:

    [{"path": "<repo-relative>", "sha256": "<hex>", "size": <int>}, ...]   sorted by path

so the digest is a content hash of the whole staged app, and every listed file
can be re-hashed from the working tree at any time (that is what
`nuxtore-verify.py` does — it never trusts the catalog).
"""
import hashlib
import json
import os

# "catalog" is skipped so NuxTore can describe itself without a digest cycle:
# the catalog contains a digest of every staged app, including NuxTore.
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", "catalog"}
SKIP_FILES = {".DS_Store", ".keep"}
SKIP_SUFFIX = (".pyc", ".pyo")


def canonical(obj):
    """The canonical signed representation (bytes)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_app(app_dir, start=None):
    """Every stageable file under app_dir, as root-relative dicts sorted by path.

    `start` is the tree the recorded paths are relative to.  It defaults to the
    real workspace root, which is what the stager wants; the offline test passes
    the root of its throw-away fixture tree, so a staged fixture produces paths
    that its verifier root can actually resolve.
    """
    base = start or START
    out = []
    for root, dirs, files in os.walk(app_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            if name in SKIP_FILES or name.endswith(SKIP_SUFFIX):
                continue
            full = os.path.join(root, name)
            out.append({
                "path": os.path.relpath(full, base).replace(os.sep, "/"),
                "sha256": sha256_file(full),
                "size": os.path.getsize(full),
            })
    out.sort(key=lambda e: e["path"])
    return out


def bundle_digest(files):
    """SHA-256 of the canonical file list = the package digest."""
    return hashlib.sha256(canonical(files)).hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True, ensure_ascii=True)
        fh.write("\n")


def repo_root():
    """The Nuxel workspace root (…/pwa/nuxel-apps/nuxtore/tools/nuxtore-common.py)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))


START = repo_root()

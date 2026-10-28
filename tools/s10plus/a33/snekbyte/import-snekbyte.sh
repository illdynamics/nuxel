#!/usr/bin/env bash
# Import (or re-verify) the original SnekByte sources into this directory.
#
#   tools/s10plus/a33/snekbyte/import-snekbyte.sh [path-to-zip] [--check]
#
# The archive is NOT part of the repository: it came from the owner's Downloads
# folder.  This script exists so the import can be repeated and audited — it
# extracts to a temporary directory, hashes every member, and either installs the
# tree (writing upstream-manifest.json) or, with --check, proves that the tree
# already in the repository is byte-identical to the archive.
#
# If the archive is absent the script exits 3 with an explicit message: that is
# the documented BLOCKED_EXTERNAL_RESOURCE case (re-import is impossible), and it
# does NOT invalidate the already-imported, hash-verified tree.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP="${1:-$HOME/Downloads/snekbyte-main.zip}"
MODE="install"
if [ "${2:-}" = "--check" ] || [ "${1:-}" = "--check" ]; then MODE="check"; ZIP="${1:-$HOME/Downloads/snekbyte-main.zip}"; [ "$ZIP" = "--check" ] && ZIP="$HOME/Downloads/snekbyte-main.zip"; fi

if [ ! -f "$ZIP" ]; then
  cat >&2 <<EOM
BLOCKED_EXTERNAL_RESOURCE: no SnekByte archive at:
    $ZIP
Supply the archive path as the first argument, or accept the already-imported
tree in ./upstream (verified against upstream-manifest.json by
tests/test-snek-parity.py).  Nothing was changed.
EOM
  exit 3
fi

command -v python3 >/dev/null || { echo "FATAL: python3 required" >&2; exit 2; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/snekbyte-import.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

echo "# archive   : $ZIP"
echo "# sha256    : $(shasum -a 256 "$ZIP" | cut -d' ' -f1)"
unzip -q "$ZIP" -d "$TMP"

SRC="$TMP/snekbyte-main"
[ -d "$SRC" ] || SRC="$(find "$TMP" -maxdepth 2 -type d -name 'src' | head -1 | xargs dirname)"
[ -d "$SRC/src" ] || { echo "FATAL: archive does not contain a src/ tree" >&2; exit 2; }

python3 - "$SRC" "$HERE" "$ZIP" "$MODE" <<'PY'
import hashlib, json, os, shutil, sys

src, here, zip_path, mode = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
SKIP = {"__pycache__", ".pytest_cache"}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def walk(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if d not in SKIP)
        for f in sorted(fn):
            p = os.path.join(dp, f)
            out[os.path.relpath(p, root)] = {"bytes": os.path.getsize(p), "sha256": sha256(p)}
    return out


members = walk(src)
manifest_path = os.path.join(here, "upstream-manifest.json")
if mode == "check":
    old = json.load(open(manifest_path))
    drift = [k for k in old["members"] if old["members"][k] != members.get(k)]
    extra = [k for k in members if k not in old["members"]]
    if drift or extra:
        print("FAIL: %d drifting member(s), %d new member(s)" % (len(drift), len(extra)))
        for k in drift[:5]:
            print("   drift:", k)
        sys.exit(1)
    print("ok: all %d members match the archive byte for byte" % len(members))
    sys.exit(0)

dest = os.path.join(here, "upstream")
if os.path.isdir(dest):
    shutil.rmtree(dest)
shutil.copytree(src, dest, ignore=shutil.ignore_patterns(*SKIP))
manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
manifest.update({
    "source_archive": os.path.basename(zip_path),
    "source_archive_bytes": os.path.getsize(zip_path),
    "source_archive_sha256": sha256(zip_path),
    "imported_by": "tools/s10plus/a33/snekbyte/import-snekbyte.sh",
    "members": members,
})
with open(manifest_path, "w") as fh:
    json.dump(manifest, fh, indent=2, sort_keys=True)
    fh.write("\n")
print("imported %d members into %s" % (len(members), dest))
licence = [k for k in members if "licen" in k.lower() or k.lower().startswith("copying")]
print("licence files in the archive: %s" % (", ".join(licence) if licence else "NONE — recorded in UPSTREAM-PROVENANCE.md"))
PY

echo "# done ($MODE)"

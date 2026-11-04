#!/usr/bin/env bash
# PWNAGE-60000 fail-closed GPU image verifier.
#
#   tools/s10plus/a67/nuxel-gpu-image-verify.sh <rootfs-stage> [--manifest PATH]
#
# Checks the exact pinned Mesa/wlroots/EGL/profile set, install paths, modes,
# SHA-256 hashes, GLVND symlinks, the kbase EGL probe and the production
# profile.  A release image must never silently ship stock Mesa or software GL.
# Never touches a device or a partition; this is a tree verifier.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
STAGE="${1:-}"
MANIFEST="${NUXEL_GPU_MANIFEST:-$ROOT/release/s10plus/gpu/gpu-manifest.json}"
REQUIRE_PROBE="${NUXEL_GPU_REQUIRE_PROBE:-1}"
if [ -z "$STAGE" ] || [ ! -d "$STAGE" ]; then
  echo "usage: $0 <rootfs-stage> [--manifest PATH]" >&2
  exit 2
fi
shift || true
while [ $# -gt 0 ]; do
  case "$1" in
    --manifest) MANIFEST="$2"; shift 2 ;;
    --no-probe) REQUIRE_PROBE=0; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -f "$MANIFEST" ] || { echo "ERROR: GPU manifest missing: $MANIFEST" >&2; exit 1; }
GPU_DIR="$(dirname "$MANIFEST")"
SUMS="$GPU_DIR/SHA256SUMS"
[ -f "$SUMS" ] || SUMS="$GPU_DIR/gpu-SHA256SUMS"
[ -f "$SUMS" ] || { echo "ERROR: no SHA256SUMS/gpu-SHA256SUMS beside $MANIFEST" >&2; exit 1; }

python3 - "$STAGE" "$MANIFEST" "$REQUIRE_PROBE" "$SUMS" <<'PY'
import hashlib, json, os, stat, subprocess, sys
stage, manifest_path, require_probe, sums_path = sys.argv[1], sys.argv[2], sys.argv[3] == "1", sys.argv[4]
errors, warnings = [], []
m = json.load(open(manifest_path))

def verify_sums():
    """A release directory has the asset files next to SHA256SUMS and must
    match exactly.  A runtime copy (/usr/share/nuxel) intentionally has only
    the manifest and checksum text; per-file manifest hashes still run below.
    Never skip a real release mismatch.
    """
    sums_dir = os.path.dirname(sums_path)
    entries = []
    with open(sums_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                errors.append("malformed checksum line: %r" % line)
                continue
            entries.append((parts[0].lower(), parts[1].strip()))
    present = [n for _, n in entries if os.path.isfile(os.path.join(sums_dir, n))]
    if not present:
        print("NOTE: %s is a runtime manifest copy; per-file hashes enforced"
              % sums_path)
        return
    if len(present) != len(entries):
        missing = sorted(set(n for _, n in entries) - set(present))
        errors.append("release checksum assets missing: %s" % ", ".join(missing))
    for want, name in entries:
        path = os.path.join(sums_dir, name)
        if not os.path.isfile(path):
            continue
        got = sha256(path)
        if got != want:
            errors.append("release checksum mismatch for %s" % name)

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

verify_sums()
if m.get("schema") != "nuxel.gpu-manifest/1":
    errors.append("unexpected manifest schema: %r" % m.get("schema"))

for entry in m.get("files", []):
    rel = entry["install"].lstrip("/")
    path = os.path.join(stage, rel)
    if not os.path.isfile(path):
        errors.append("missing installed GPU asset: %s" % entry["install"])
        continue
    got = sha256(path)
    if got != entry["sha256"]:
        errors.append("hash mismatch for %s: %s != %s" % (entry["install"], got, entry["sha256"]))
    want_mode = int(entry.get("mode", "0644"), 8)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    if entry.get("mode") == "0755" and not (mode & 0o111):
        errors.append("asset is not executable: %s (mode %04o)" % (entry["install"], mode))
    elif (mode & 0o777) != want_mode:
        errors.append("mode mismatch for %s: %04o != %04o" % (entry["install"], mode, want_mode))

for link in m.get("symlinks", []):
    path = os.path.join(stage, link["path"].lstrip("/"))
    if not os.path.islink(path):
        errors.append("missing symlink: %s" % link["path"])
        continue
    got = os.readlink(path)
    if got != link["target"]:
        errors.append("symlink %s -> %r, expected %r" % (link["path"], got, link["target"]))

# The stock Mesa EGL library must never be the active link.
egl_link = os.path.join(stage, "usr/lib64/libEGL_mesa.so.0")
if os.path.islink(egl_link):
    target = os.readlink(egl_link)
    if "nuxel-bak" in target or target.endswith("libEGL_mesa.so.0.0.0.nuxel-bak"):
        errors.append("libEGL_mesa.so.0 points at the stock backup: %s" % target)

profile_path = os.path.join(stage, "etc/nuxel/graphics/graphics-profile.json")
profile = os.path.join(stage, "usr/lib/nuxel/nuxel-graphics-profile")
if not os.path.isfile(profile_path):
    errors.append("production graphics-profile.json missing")
elif not os.path.isfile(profile):
    errors.append("nuxel-graphics-profile helper missing")
else:
    env = dict(os.environ, NUXEL_GRAPHICS_PROFILE=profile_path,
               NUXEL_GPU_PROBE_DISABLE="1")
    p = subprocess.run([sys.executable, profile, "validate"], capture_output=True,
                       text=True, env=env)
    if p.returncode != 0:
        errors.append("installed profile failed validation: %s" % p.stdout.strip())
    doc = json.load(open(profile_path))
    if doc.get("default_profile") != "gpu-rendered-shm-presented":
        errors.append("default_profile is %r, expected gpu-rendered-shm-presented"
                      % doc.get("default_profile"))
    for section in ("webkitgtk", "gtk3"):
        sec = doc.get(section) or {}
        if sec.get("fallback") != "software-safe":
            errors.append("%s.fallback must be software-safe" % section)
        if (doc.get("profiles") or {}).get("gpu-rendered-dmabuf-presented", {}).get("available"):
            errors.append("gpu-rendered-dmabuf-presented must remain unavailable")
        if (doc.get("profiles") or {}).get("fully-accelerated", {}).get("available"):
            errors.append("fully-accelerated must remain unavailable")

probe = m.get("probe") or {}
probe_path = os.path.join(stage, probe.get("install", "").lstrip("/"))
if require_probe:
    if not os.path.isfile(probe_path):
        errors.append("kbase EGL probe missing: %s" % probe.get("install"))
    else:
        try:
            out = subprocess.run(["file", "-b", probe_path], capture_output=True, text=True).stdout
            if "aarch64" not in out and "ARM aarch64" not in out:
                errors.append("kbase EGL probe is not an aarch64 ELF: %s" % out.strip())
        except Exception:
            warnings.append("file(1) unavailable; could not check probe architecture")

# PWNAGE-60000: the boot-time PWN36000 bootstrap must not overwrite the
# production session.  If the stage exists, require the guarded script and the
# same session content in both locations.
stage3600 = os.path.join(stage, "usr/lib/nuxel/stage36000")
if os.path.isdir(stage3600):
    apply_script = os.path.join(stage3600, "apply-pwnage36000.sh")
    staged_session = os.path.join(stage3600, "session/nuxel-session.sh")
    if not os.path.isfile(apply_script):
        errors.append("PWN36000 apply script missing from stage36000")
    else:
        text = open(apply_script, "r", encoding="utf-8", errors="replace").read()
        if "kept newer deployed /usr/lib/nuxel/nuxel-session.sh" not in text:
            errors.append("PWN36000 apply script can overwrite a newer deployed session")
    if not os.path.isfile(staged_session):
        errors.append("staged nuxel-session.sh missing")
    elif os.path.isfile(os.path.join(stage, "usr/lib/nuxel/nuxel-session.sh")):
        if sha256(staged_session) != sha256(os.path.join(stage, "usr/lib/nuxel/nuxel-session.sh")):
            errors.append("staged and deployed nuxel-session.sh differ")

# Runtime manifest belongs in the image for the diagnostics command.
installed_manifest = os.path.join(stage, "usr/share/nuxel/gpu-manifest.json")
if not os.path.isfile(installed_manifest):
    warnings.append("runtime manifest not installed at /usr/share/nuxel/gpu-manifest.json")
elif sha256(installed_manifest) != sha256(manifest_path):
    errors.append("installed runtime manifest differs from the release manifest")

if errors:
    print("GPU IMAGE VERIFY: FAIL", file=sys.stderr)
    for e in errors:
        print("ERROR: " + e, file=sys.stderr)
    for w in warnings:
        print("WARNING: " + w, file=sys.stderr)
    raise SystemExit(1)
print("GPU IMAGE VERIFY: PASS (%d files, %d symlinks)" %
      (len(m.get("files", [])), len(m.get("symlinks", []))))
for w in warnings:
    print("WARNING: " + w)
PY

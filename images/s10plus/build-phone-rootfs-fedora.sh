#!/usr/bin/env bash
# Build a true Fedora Linux 43 aarch64 Nuxel PHONE userspace on Apple Silicon.
# Output is built from real Fedora RPMs. Never produces a fabricated success image.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${NUXEL_S10PLUS_OUTPUT:-$ROOT/build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img}"
if [[ "${1:-}" == --help ]]; then
 cat <<'USAGE'
Usage: bash images/s10plus/build-phone-rootfs-fedora.sh
  NUXEL_S10PLUS_OUTPUT=/absolute/path.img  override output path
  NUXEL_S10PLUS_IMAGE_MB=4096           change root filesystem size (MiB)
Requires Docker Desktop on Apple Silicon (or Linux aarch64), internet and >=8GiB free.
Runs Fedora 43 ARM64 DNF in Docker, builds an ext4 with Python3, systemd,
Phosh, Phoc, and Samsung overlays, then checks the resulting image offline.
Fedora uses systemd: OpenRC is NOT installed by this builder.
Package-complete != physically boot tested; framebuffer/GPU/DTBO compatibility unverified.
USAGE
 exit 0
fi
command -v podman >/dev/null 2>&1 || { echo 'ERROR: Docker Desktop or Docker Engine is required' >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo 'ERROR: Python3 needed for artifact validation' >&2; exit 2; }
case "$OUT" in /*) ;; *) echo 'ERROR: NUXEL_S10PLUS_OUTPUT must be absolute' >&2; exit 2;; esac
MB="${NUXEL_S10PLUS_IMAGE_MB:-4096}"
[[ "$MB" =~ ^[0-9]+$ ]] && (( MB >= 3072 && MB <= 8192 )) || { echo 'ERROR: use 3072–8192 MiB image size' >&2; exit 2; }
mkdir -p "$(dirname "$OUT")"
[[ ! -e "$OUT" ]] || { echo "ERROR: refusing to overwrite existing $OUT" >&2; exit 2; }
OUTDIR="$(cd "$(dirname "$OUT")" && pwd)"
NAME="$(basename "$OUT")"
echo "[nuxel] Fedora 43 aarch64 mobile image -> $OUT ($MB MiB)"
# On an SELinux-enforcing workstation a read-only bind mount is still blocked
# without a label; the repo is mounted read-only, so disabling label separation
# for this build container is the least-privilege way to make the documented
# build reproducible on Fedora hosts as well as Ubuntu CI.
SECURITY_ARGS=()
if command -v selinuxenabled >/dev/null 2>&1 && selinuxenabled; then
  SECURITY_ARGS+=(--security-opt label=disable)
fi
podman run --rm --platform linux/arm64 --user root "${SECURITY_ARGS[@]}" \
  --mount "type=bind,source=$ROOT,target=/nuxel,readonly" \
  --mount "type=bind,source=$OUTDIR,target=/deliver" \
  -e "NUXEL_IMAGE_NAME=$NAME" -e "NUXEL_IMAGE_MB=$MB" \
  --entrypoint /bin/bash fedora:43 \
  /nuxel/images/s10plus/build-phone-rootfs-inside-fedora.sh
[[ -s "$OUT" ]] || { echo 'ERROR: container returned without image' >&2; exit 1; }
python3 "$ROOT/tools/s10plus/verify-fedora-phone-rootfs.py" --ext4 "$OUT" || {
  echo 'ERROR: resulting image did not meet Fedora ARM64 runtime checks; not flash-ready.' >&2; exit 1;
}
echo "[nuxel] Fedora ARM64 phone runtime packaged and offline-validated: $OUT"
echo '[nuxel] Hardware boot, DTBO choice, DRM/display and touch remain UNVERIFIED.'

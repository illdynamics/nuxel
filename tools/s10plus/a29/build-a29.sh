#!/usr/bin/env bash
# ============================================================================
# build-a29.sh — build the A29 phone binaries for Fedora 43 aarch64.
#
# Builds inside a native arm64 Fedora container (podman on Apple Silicon) so the
# GLib/GTK3/WebKitGTK headers match the phone's RPMs exactly; a cross sysroot
# would be a second source of truth.  Nothing here is flashed: the outputs are
# deployed over the USB live console by nuxel-live-deploy.sh.
#
#   ./build-a29.sh              # build into build/out/s10plus/a29
#   ./build-a29.sh --shell      # interactive container for debugging a build
# ============================================================================
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
OUT="$ROOT/build/out/s10plus/a29"
ENGINE="${NUXEL_CONTAINER_ENGINE:-podman}"
IMAGE="${NUXEL_BUILD_IMAGE:-registry.fedoraproject.org/fedora:43}"
mkdir -p "$OUT"

READY='dnf -y --setopt=install_weak_deps=False install
    gcc make pkgconf-pkg-config wayland-devel wayland-protocols-devel
    gtk3-devel webkit2gtk4.1-devel
    >/tmp/dnf.log 2>&1 || { tail -40 /tmp/dnf.log; exit 1; }'

# --build: compile every A29 binary inside one container session
BUILD='
set -e
cd /src
wayland-scanner client-header wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-client-protocol.h
wayland-scanner private-code  wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-protocol.c
CFLAGS="-O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11"
gcc $CFLAGS $(pkg-config --cflags wayland-client) -o out/nuxel-wl-fb nuxel-wl-fb.c \
    wlr-screencopy-unstable-v1-protocol.c $(pkg-config --libs wayland-client)
gcc $CFLAGS -o out/nuxel-touch-arm nuxel-touch-arm.c
gcc $CFLAGS $(pkg-config --cflags gtk+-3.0 webkit2gtk-4.1) -o out/nuxel-pwa-host nuxel-pwa-host.c \
    $(pkg-config --libs gtk+-3.0 webkit2gtk-4.1)
for b in nuxel-wl-fb nuxel-touch-arm nuxel-pwa-host; do
  printf "%-18s %s  %s\n" "$b" "$(stat -c %s out/$b)" "$(sha256sum out/$b | cut -c1-16)"
done
file out/nuxel-wl-fb | sed "s/^/file: /"
'

if [ "${1:-}" = "--shell" ]; then
  exec "$ENGINE" run --rm -it --platform linux/arm64 -v "$HERE:/src:z" -w /src "$IMAGE" bash
fi

"$ENGINE" run --rm --platform linux/arm64 -v "$HERE:/src:z" -w /src "$IMAGE" \
  bash -lc "$READY; mkdir -p /src/out; $BUILD"

# The container ran as root: give the artifacts back to the invoking user.
"$ENGINE" run --rm --platform linux/arm64 -v "$HERE:/src:z" -w /src "$IMAGE" \
  chown -R "$(id -u):$(id -g)" /src/out >/dev/null 2>&1 || true

cp -f "$HERE/out/nuxel-wl-fb" "$HERE/out/nuxel-touch-arm" "$HERE/out/nuxel-pwa-host" "$OUT/" 2>/dev/null || true
echo "--- artifacts in $OUT ---"
( cd "$OUT" && sha256sum nuxel-wl-fb nuxel-touch-arm nuxel-pwa-host 2>/dev/null | tee SHA256SUMS )

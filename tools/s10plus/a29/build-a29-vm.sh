#!/usr/bin/env bash
# ============================================================================
# build-a29-vm.sh — build the A29 phone binaries on the live UTM VM.
#
# WHY THE VM AND NOT A CONTAINER: the UTM guest is Fedora 43 aarch64 with the
# *same* RPM versions the handset image carries (webkit2gtk4.1-2.52.5-1.fc43,
# gtk3-3.24.52-1.fc43), so the ELF dependencies are matched by construction.  A
# podman/docker cross-build is not used: on this host the podman machine's
# gvproxy API socket is unstable ("unable to connect to gvproxy socket").
#
# The binaries are NOT flashed: nuxel-live-deploy.sh installs them over the USB
# live console.
#
#   ./build-a29-vm.sh                # build + fetch into build/out/s10plus/a29
#   VM=nuxel@192.168.64.3 ./build-a29-vm.sh
# ============================================================================
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
OUT="$ROOT/build/out/s10plus/a29"
VM="${VM:-nuxel@192.168.64.3}"
SSH=(ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$VM")
DEPS=(webkit2gtk4.1-devel gtk3-devel wayland-protocols-devel pkgconf-pkg-config gcc)
mkdir -p "$OUT"

echo "== 1. build deps on $VM (dnf, idempotent)"
"${SSH[@]}" 'missing=""; for p in webkit2gtk4.1-devel gtk3-devel wayland-protocols-devel pkgconf-pkg-config gcc; do rpm -q $p >/dev/null 2>&1 || missing="$missing $p"; done; if [ -n "$missing" ]; then echo nuxel | sudo -S dnf -y --setopt=install_weak_deps=False install $missing >/tmp/dnf-a29.log 2>&1 || { tail -30 /tmp/dnf-a29.log; exit 1; }; fi; pkg-config --modversion webkit2gtk-4.1 gtk+-3.0 wayland-client'

echo "== 2. ship sources"
"${SSH[@]}" 'mkdir -p ~/a29build'
scp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "$HERE/nuxel-wl-fb.c" "$HERE/nuxel-touch-arm.c" "$HERE/nuxel-pwa-host.c" \
    "$HERE/wlr-screencopy-unstable-v1.xml" "$VM:~/a29build/"

echo "== 3. compile"
"${SSH[@]}" 'set -e; cd ~/a29build
  wayland-scanner client-header wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-client-protocol.h
  wayland-scanner private-code  wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-protocol.c
  CF="-O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11"
  gcc $CF $(pkg-config --cflags wayland-client) -o nuxel-wl-fb nuxel-wl-fb.c \
      wlr-screencopy-unstable-v1-protocol.c $(pkg-config --libs wayland-client)
  gcc $CF -o nuxel-touch-arm nuxel-touch-arm.c
  gcc $CF $(pkg-config --cflags gtk+-3.0 webkit2gtk-4.1) -o nuxel-pwa-host nuxel-pwa-host.c \
      $(pkg-config --libs gtk+-3.0 webkit2gtk-4.1)
  for b in nuxel-wl-fb nuxel-touch-arm nuxel-pwa-host; do
    file $b | grep -q "ARM aarch64" || { echo "$b is not aarch64"; exit 1; }
  done
  sha256sum nuxel-wl-fb nuxel-touch-arm nuxel-pwa-host'

echo "== 4. fetch"
for b in nuxel-wl-fb nuxel-touch-arm nuxel-pwa-host; do
  scp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$VM:~/a29build/$b" "$OUT/$b"
done
( cd "$OUT" && sha256sum nuxel-wl-fb nuxel-touch-arm nuxel-pwa-host | tee SHA256SUMS )
echo "== artifacts in $OUT"

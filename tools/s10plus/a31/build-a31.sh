#!/usr/bin/env bash
# build-a31.sh — build the A31 phone components on the LIVE UTM VM.
#
# Build channel = the running UTM guest (Fedora 43 aarch64): the same
# webkit2gtk4.1-2.52.x / gtk3 / libwayland the handset image carries, so the ELF
# dependencies match by construction.  The podman/gvproxy cross-build path is
# deliberately NOT used (measured unstable on this host, A29).
#
#   ./build-a31.sh            # -> build/out/s10plus/a31/{nuxel-wl-fb,nuxel-pwa-host,libnuxel-libinput-path.so}
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
A29="$ROOT/tools/s10plus/a29"
OUT="$ROOT/build/out/s10plus/a31"
VM="${VM:-nuxel@192.168.64.3}"
SSH=(ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$VM")
SCP=(scp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)
mkdir -p "$OUT"

echo "== 1. deps on $VM"
"${SSH[@]}" 'missing=""; for p in wayland-devel wayland-protocols-devel pkgconf-pkg-config gcc gtk3-devel webkit2gtk4.1-devel; do rpm -q $p >/dev/null 2>&1 || missing="$missing $p"; done; if [ -n "$missing" ]; then echo "installing:$missing"; echo nuxel | sudo -S dnf -y --setopt=install_weak_deps=False install $missing >/tmp/dnf-a31.log 2>&1 || { tail -30 /tmp/dnf-a31.log; exit 1; }; fi; pkg-config --modversion wayland-client gtk+-3.0 webkit2gtk-4.1'

echo "== 2. ship source"
"${SSH[@]}" 'mkdir -p ~/a31build'
"${SCP[@]}" "$HERE/nuxel-wl-fb.c" "$HERE/nuxel-pwa-host.c" "$HERE/nuxel-libinput-path.c" "$A29/wlr-screencopy-unstable-v1.xml" "$VM:~/a31build/"

echo "== 3. compile (aarch64)"
"${SSH[@]}" 'set -e; cd ~/a31build
  wayland-scanner client-header wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-client-protocol.h
  wayland-scanner private-code  wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-protocol.c
  CFLAGS="-O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11"
  gcc $CFLAGS $(pkg-config --cflags wayland-client) -o nuxel-wl-fb nuxel-wl-fb.c \
      wlr-screencopy-unstable-v1-protocol.c $(pkg-config --libs wayland-client)
  gcc $CFLAGS $(pkg-config --cflags gtk+-3.0 webkit2gtk-4.1) -o nuxel-pwa-host nuxel-pwa-host.c \
      $(pkg-config --libs gtk+-3.0 webkit2gtk-4.1)
  gcc $CFLAGS -shared -fPIC -o libnuxel-libinput-path.so nuxel-libinput-path.c -ldl
  for b in nuxel-wl-fb nuxel-pwa-host libnuxel-libinput-path.so; do file $b | grep -q "ARM aarch64" || { echo "NOT aarch64: $b"; exit 1; }; done
  sha256sum nuxel-wl-fb nuxel-pwa-host libnuxel-libinput-path.so'

echo "== 4. fetch"
"${SCP[@]}" "$VM:~/a31build/nuxel-wl-fb" "$VM:~/a31build/nuxel-pwa-host" "$VM:~/a31build/libnuxel-libinput-path.so" "$OUT/"
( cd "$OUT" && sha256sum nuxel-wl-fb nuxel-pwa-host libnuxel-libinput-path.so | tee SHA256SUMS )

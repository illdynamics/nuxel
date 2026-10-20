#!/usr/bin/env bash
# build-a30.sh — build the A30 (single-framebuffer-owner) bridge on the live UTM VM.
#
# Build channel = the running UTM guest (Fedora 43 aarch64, same libwayland the
# handset image carries).  No containers: the podman/gvproxy cross path is
# unstable on this host and is deliberately not used.
#
#   ./build-a30.sh            # -> build/out/s10plus/a30/nuxel-wl-fb
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
A29="$ROOT/tools/s10plus/a29"
OUT="$ROOT/build/out/s10plus/a30"
VM="${VM:-nuxel@192.168.64.3}"
SSH=(ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$VM")
SCP=(scp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)
mkdir -p "$OUT"

echo "== 1. deps on $VM"
"${SSH[@]}" 'missing=""; for p in wayland-devel wayland-protocols-devel pkgconf-pkg-config gcc; do rpm -q $p >/dev/null 2>&1 || missing="$missing $p"; done; if [ -n "$missing" ]; then echo nuxel | sudo -S dnf -y --setopt=install_weak_deps=False install $missing >/tmp/dnf-a30.log 2>&1 || { tail -30 /tmp/dnf-a30.log; exit 1; }; fi; pkg-config --modversion wayland-client'

echo "== 2. ship source"
"${SSH[@]}" 'mkdir -p ~/a30build'
"${SCP[@]}" "$A29/nuxel-wl-fb.c" "$A29/wlr-screencopy-unstable-v1.xml" "$VM:~/a30build/"

echo "== 3. compile (aarch64)"
"${SSH[@]}" 'set -e; cd ~/a30build
  wayland-scanner client-header wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-client-protocol.h
  wayland-scanner private-code  wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-protocol.c
  gcc -O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11 $(pkg-config --cflags wayland-client) \
      -o nuxel-wl-fb nuxel-wl-fb.c wlr-screencopy-unstable-v1-protocol.c $(pkg-config --libs wayland-client)
  file nuxel-wl-fb | grep -q "ARM aarch64" || { echo "not aarch64"; exit 1; }
  sha256sum nuxel-wl-fb'

echo "== 4. fetch"
"${SCP[@]}" "$VM:~/a30build/nuxel-wl-fb" "$OUT/nuxel-wl-fb"
( cd "$OUT" && sha256sum nuxel-wl-fb | tee SHA256SUMS )

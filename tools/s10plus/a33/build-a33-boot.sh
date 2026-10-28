#!/usr/bin/env bash
# build-a33-boot.sh — build the A33 boot-surface bridge (briq-02a/02c).
#
# WHY THIS SCRIPT EXISTS
#   tools/s10plus/a33/nuxel-wl-fb.c is the handset's framebuffer bridge: the
#   receipt-driven animation handoff, the single-/dev/fb0-owner lock, the receipt
#   writer and the protected XRGB8888 -> DECON ABGR_8888 conversion all live in
#   it.  It is a Linux userspace program (fbdev + Wayland), so it cannot be built
#   on this macOS development host — and until this script existed, nothing built
#   it at all: the A32 script builds the A32 copy in tools/s10plus/a32/.
#
# BUILD CHANNELS (tried in order; nothing is ever guessed or faked)
#   1. the UTM Fedora 43 aarch64 guest (native build, matching ELF deps),
#      reachable as $VM (default nuxel@192.168.64.3),
#   2. a local cross toolchain ($CROSS_COMPILE gcc) *if* it can see the Wayland
#      client headers (probed, not assumed),
#   3. otherwise: reported as skipped, with the exact command to run by hand.
#      A build that did not happen is NEVER reported as a pass.
#
# OUTPUT (deliberately NOT the A32 output directory, so the byte-pinned A32
#   artifacts in docs/beta-finalization/baseline-protection.json can still be
#   reproduced after this script has run):
#       build/out/s10plus/a33-boot/{nuxel-wl-fb,SHA256SUMS,build.log}
#
# NOTHING HERE TOUCHES THE PHONE, A PARTITION, A BOOTLOADER OR A BLOCK DEVICE.
# It compiles userspace C and (on the guest) runs the bridge's own offline
# self-tests: --colour-selftest, --colour-dump, --handoff-selftest.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
A29="$ROOT/tools/s10plus/a29"
OUT="${OUT:-$ROOT/build/out/s10plus/a33-boot}"
VM="${VM:-nuxel@192.168.64.3}"
SSH=(ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=8 "$VM")
SCP=(scp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=8)
CFLAGS_COMMON="-O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11"

say() { printf '%s\n' "$*"; }
mkdir -p "$OUT"

SRC=("$HERE/nuxel-wl-fb.c" "$HERE/nuxel-handoff-logic.h" "$A29/wlr-screencopy-unstable-v1.xml")
for f in "${SRC[@]}"; do
  [ -f "$f" ] || { say "build-a33-boot: missing source $f"; exit 2; }
done

say "== A33 boot bridge (nuxel-wl-fb) =="
say "   source : $HERE/nuxel-wl-fb.c"
say "   output : $OUT"

probe_local_toolchain() {
  local cc="${CROSS_COMPILE:-}gcc"
  command -v "$cc" >/dev/null 2>&1 || return 1
  local probe; probe="$(mktemp -t nuxel-wl-probe.XXXXXX)"
  printf '#include <linux/fb.h>\n#include <wayland-client.h>\nint main(void){return 0;}\n' > "$probe"
  if "$cc" -fsyntax-only -x c "$probe" >/dev/null 2>&1; then rm -f "$probe"; return 0; fi
  rm -f "$probe"; return 1
}

build_on_vm() {
  say "== channel 1: the UTM Fedora 43 aarch64 guest ($VM) =="
  "${SSH[@]}" true >/dev/null 2>&1 || return 1
  "${SSH[@]}" 'mkdir -p ~/a33boot' || return 1
  "${SCP[@]}" "$HERE/nuxel-wl-fb.c" "$HERE/nuxel-handoff-logic.h" \
              "$A29/wlr-screencopy-unstable-v1.xml" "$VM:~/a33boot/" || return 1
  "${SSH[@]}" "set -e
    missing=''
    for p in wayland-devel wayland-protocols-devel pkgconf-pkg-config gcc; do
      rpm -q \$p >/dev/null 2>&1 || missing=\"\$missing \$p\"
    done
    if [ -n \"\$missing\" ]; then
      echo \"installing:\$missing\"
      sudo dnf -y --setopt=install_weak_deps=False install \$missing >/tmp/dnf-a33boot.log 2>&1 || { tail -20 /tmp/dnf-a33boot.log; exit 1; }
    fi
    cd ~/a33boot
    wayland-scanner client-header wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-client-protocol.h
    wayland-scanner private-code  wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-protocol.c
    gcc $CFLAGS_COMMON \$(pkg-config --cflags wayland-client) -o nuxel-wl-fb nuxel-wl-fb.c \
        wlr-screencopy-unstable-v1-protocol.c \$(pkg-config --libs wayland-client)
    file nuxel-wl-fb | grep -q 'ARM aarch64'       || { echo 'NOT aarch64'; exit 1; }
    file nuxel-wl-fb | grep -q 'dynamically linked' || { echo 'NOT dynamic'; exit 1; }
    echo '-- colour selftest --';   ./nuxel-wl-fb --colour-selftest
    echo '-- handoff selftest --';  ./nuxel-wl-fb --handoff-selftest
    echo '-- colour dump header --'; ./nuxel-wl-fb --colour-dump | head -1
    sha256sum nuxel-wl-fb" | tee "$OUT/build.log" || return 1
  "${SCP[@]}" "$VM:~/a33boot/nuxel-wl-fb" "$OUT/nuxel-wl-fb" || return 1
  ( cd "$OUT" && sha256sum nuxel-wl-fb | tee SHA256SUMS ) >/dev/null
  say "   -> $OUT/nuxel-wl-fb ($(wc -c < "$OUT/nuxel-wl-fb") bytes)"
  say "   NOTE: built and self-tested on the guest; it is NOT deployed to the phone by this"
  say "         script (deployment is the serialized live group's job)."
  return 0
}

build_cross() {
  local cc="${CROSS_COMPILE:-}gcc" as="${CROSS_COMPILE:-}as"
  say "== channel 2: local cross toolchain ($cc) =="
  probe_local_toolchain || return 1
  local tmp; tmp="$(mktemp -d -t a33boot.XXXXXX)"
  cp "$HERE/nuxel-wl-fb.c" "$HERE/nuxel-handoff-logic.h" "$A29/wlr-screencopy-unstable-v1.xml" "$tmp/"
  ( cd "$tmp" || exit 1
    command -v wayland-scanner >/dev/null 2>&1 || exit 9
    wayland-scanner client-header wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-client-protocol.h || exit 9
    wayland-scanner private-code  wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-protocol.c || exit 9
    "$cc" $CFLAGS_COMMON $(pkg-config --cflags wayland-client) -o nuxel-wl-fb nuxel-wl-fb.c \
        wlr-screencopy-unstable-v1-protocol.c $(pkg-config --libs wayland-client)
  ) > "$OUT/build.log" 2>&1
  local rc=$?
  if [ $rc -ne 0 ]; then
    say "   cross build failed (rc=$rc) — see $OUT/build.log"
    tail -5 "$OUT/build.log" | sed 's/^/   /'
    rm -rf "$tmp"
    return 1
  fi
  # aarch64 ELFs cannot execute on this macOS host: the guest is the execution channel
  cp "$tmp/nuxel-wl-fb" "$OUT/nuxel-wl-fb"
  ( cd "$OUT" && sha256sum nuxel-wl-fb | tee SHA256SUMS ) >/dev/null
  say "   -> $OUT/nuxel-wl-fb (cross-compiled; run it on the guest for the self-tests)"
  rm -rf "$tmp"
  return 0
}

if build_on_vm; then
  say "BUILD_A33_BOOT=OK channel=vm"
  exit 0
fi
say "   guest not reachable — trying a local cross toolchain"
if build_cross; then
  say "BUILD_A33_BOOT=OK channel=cross (self-tests must run on the guest)"
  exit 0
fi

say ""
say "BUILD_A33_BOOT=SKIPPED reason=BLOCKED_EXTERNAL_RESOURCE"
say "   The A33 bridge is a Linux userspace program (linux/fb.h + Wayland client)."
say "   Neither the UTM guest ($VM) nor a cross toolchain with Wayland headers is"
say "   reachable from here, so the build did NOT happen — this is not a pass."
say "   Run one of these where the toolchain exists:"
say "     bash tools/s10plus/a33/build-a33-boot.sh                 # with the VM up"
say "     CROSS_COMPILE=aarch64-linux-gnu- bash tools/s10plus/a33/build-a33-boot.sh"
say "     ssh <guest> 'cd ~/a33boot && gcc -O2 -Wall -Wextra -std=gnu11 \\"
say "        \$(pkg-config --cflags wayland-client) -o nuxel-wl-fb nuxel-wl-fb.c \\"
say "        wlr-screencopy-unstable-v1-protocol.c \$(pkg-config --libs wayland-client)'"
say "   The offline source-level proof (colour golden bytes, handoff decision table)"
say "   does not need this build and runs anywhere: tools/s10plus/a33/tests/run-boot-tests.sh"
exit 3

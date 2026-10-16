#!/usr/bin/env bash
# build-a33-buttons.sh — build the A33 button manager and its offline replay helper.
#
# WHY A SEPARATE SCRIPT
#   The A32 build (tools/s10plus/a32/build-a32.sh) builds the PROTECTED baseline
#   artifacts. This builds the A33 additions into their own output directory so a
#   build of this group can never overwrite an A32 artifact, and so the A32
#   hashes recorded in docs/beta-finalization/baseline-protection.json can still
#   be reproduced byte-for-byte after this script has run.
#
# RUNS
#   * on the target / UTM Fedora 43 aarch64 guest (native aarch64 build), or
#   * on any host with a cross toolchain via CROSS_COMPILE=aarch64-linux-gnu-
#
# NOTHING HERE TOUCHES THE PHONE, A PARTITION, A BOOTLOADER OR A BLOCK DEVICE.
# It compiles userspace C and, on request, installs userspace files.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
OUT="${OUT:-$ROOT/build/out/s10plus/a33}"
CC="${CC:-${CROSS_COMPILE:-}gcc}"
STRIP="${STRIP:-${CROSS_COMPILE:-}strip}"

mkdir -p "$OUT"

say() { printf '%s\n' "$*"; }

command -v "$CC" >/dev/null 2>&1 || {
  say "build-a33-buttons: compiler '$CC' not found."
  say "  On this macOS host the daemon cannot be built (it needs <linux/input.h> and"
  say "  alsa-lib). Build it on the UTM Fedora 43 aarch64 guest, or set CROSS_COMPILE."
  exit 1
}

say "== building nuxel-button-fsm-sim (host-side offline replay) =="
# The same state machine, compiled from the header only: no libasound, no
# linux/input.h, so this helper also builds on a macOS development host.
"$CC" -std=c11 -O1 -Wall -o "$OUT/nuxel-button-fsm-sim" \
      -DNUXEL_FSM_MAIN -x c "$HERE/nuxel-button-fsm.h"
say "   -> $OUT/nuxel-button-fsm-sim"

# The daemon needs <linux/input.h> and alsa-lib. Probe rather than fail obscurely:
# a missing header here is an environment fact, not a source error.
probe=$(mktemp -t nuxel-alsa-probe.XXXXXX)
printf '#include <alsa/asoundlib.h>\n#include <linux/input.h>\nint main(void){return 0;}\n' > "$probe"
if ! "$CC" -fsyntax-only -x c "$probe" 2>/dev/null; then
  say ""
  say "== SKIPPED: nuxel-button-manager (no alsa-lib / linux/input.h here) =="
  say "   This host cannot build the daemon - it is a Linux userspace binary."
  say "   Build it on the UTM Fedora 43 aarch64 guest (or with a cross toolchain):"
  say "     ssh <guest> 'cd /tmp && gcc -std=gnu11 -O2 -Wall -Wextra \\"
  say "        -o nuxel-button-manager nuxel-button-manager.c -lasound'"
  say "   The replay helper above still builds and still drives the SAME state"
  say "   machine, so the offline test suite is not weakened by this skip."
  exit 3
fi

say "== building nuxel-button-manager (aarch64 userspace) =="
# -O2 -Wall -Wextra: the A33 source builds warning-free on Fedora 43 (GCC 15.3.1).
# If a warning appears, fix the source - do not silence it here.
"$CC" -std=gnu11 -O2 -Wall -Wextra -o "$OUT/nuxel-button-manager" \
      "$HERE/nuxel-button-manager.c" -lasound
say "   -> $OUT/nuxel-button-manager"

say "== sanity: the replay helper must agree with the spec =="
"$OUT/nuxel-button-fsm-sim" --menu-dump | sed -n '1,3p'

say ""
say "build complete. Install (userspace only, no flashing, no partition writes):"
say "  install -D -m0755 $OUT/nuxel-button-manager      /usr/lib/nuxel/nuxel-button-manager"
say "  install -D -m0755 $OUT/nuxel-button-fsm-sim      /usr/lib/nuxel/nuxel-button-fsm-sim"
say "  install -D -m0644 $HERE/nuxel-button-manager.service /etc/systemd/system/nuxel-button-manager.service"
say "  install -D -m0644 $ROOT/configs/nuxel/input/button-fsm.json  /etc/nuxel/input/button-fsm.json"
say "  install -D -m0644 $ROOT/configs/nuxel/buttons/reboot-gate.json /etc/nuxel/buttons/reboot-gate.json"
say "  systemctl daemon-reload && systemctl restart nuxel-button-manager"
say "  nuxel-button-manager --probe      # verify the node resolution on the device"

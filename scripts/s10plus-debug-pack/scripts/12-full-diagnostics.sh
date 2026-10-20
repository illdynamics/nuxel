#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
init_out full-collection
require_recovery
say 'Collecting read-only TWRP + previous-boot diagnostics.'
steps=(
  01-previous-boot-overview.sh
  02-pstore-capture.sh
  03-last-kmsg-capture.sh
  04-twrp-recovery-logs.sh
  05-partitions-mounts.sh
  06-recovery-kernel-info.sh
  07-mac-usb-snapshot.sh
)
failed=0
for step in "${steps[@]}"; do
  say "=== $step ==="
  if ! NUXEL_OUT="$NUXEL_OUT" bash "$SCRIPT_DIR/$step" > "$NUXEL_OUT/run-${step%.sh}.log" 2>&1; then
    warn "Step $step failed, inspect run-${step%.sh}.log"
    failed=$((failed+1))
  fi
done
# Optional offline inputs; no raw image ever included in the resulting captures.
if [ -n "${NUXEL_BOOT_IMAGE:-}" ]; then
  bash "$SCRIPT_DIR/09-inspect-boot-image.sh" "$NUXEL_BOOT_IMAGE" > "$NUXEL_OUT/run-09-boot-image.log" 2>&1 || warn 'Boot inspection failed'
fi
if [ -n "${NUXEL_ROOTFS_IMAGE:-}" ]; then
  bash "$SCRIPT_DIR/10-inspect-fedora-rootfs.sh" "$NUXEL_ROOTFS_IMAGE" > "$NUXEL_OUT/run-10-rootfs.log" 2>&1 || warn 'Rootfs inspection failed'
fi
python3 "$PACK_DIR/tools/triage.py" "$NUXEL_OUT" > "$NUXEL_OUT/run-triage.log" 2>&1 || warn 'Triage failed'
printf 'Collection step failures: %d\n' "$failed" > "$NUXEL_OUT/COLLECTION-RESULT.txt"
say "Finished. Start with $NUXEL_OUT/TRIAGE.md"
say "To produce a redacted ZIP for sharing: bash '$SCRIPT_DIR/14-create-share-bundle.sh' '$NUXEL_OUT'"

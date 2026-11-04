#!/usr/bin/env bash
# PWNAGE-61000 rollback.  Narrow by design: never removes audio/ABOX firmware,
# never flashes a partition, never touches EFS/modem/recovery.
#
# Usage:
#   rollback-pwnage61000.sh --rootfs / [--receipt] [--firmware] [--userspace] [--restore-guard] [--all] [--dry-run]
#
# Kernel/DTB rollback is deliberately manual and documented in
# docs/beta-finalization/live/PWNAGE-61000-MFC-REPORT.md.
set -euo pipefail

ROOTFS="/"
DO_RECEIPT=0; DO_FW=0; DO_USER=0; DO_GUARD=0; DRY=0
while [ $# -gt 0 ]; do
    case "$1" in
        --rootfs) ROOTFS="$2"; shift 2 ;;
        --receipt) DO_RECEIPT=1; shift ;;
        --firmware) DO_FW=1; shift ;;
        --userspace) DO_USER=1; shift ;;
        --restore-guard) DO_GUARD=1; shift ;;
        --all) DO_RECEIPT=1; DO_FW=1; DO_USER=1; DO_GUARD=1; shift ;;
        --dry-run) DRY=1; shift ;;
        --help|-h) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown: $1" >&2; exit 2 ;;
    esac
done
rm_() {
    if [ "$DRY" -eq 1 ]; then echo "would remove: $1"; else rm -f -- "$1" && echo "removed: $1"; fi
}
[ "$DO_RECEIPT" -eq 1 ] && rm_ "$ROOTFS/etc/nuxel/mfc/safety-receipt.json"
[ "$DO_FW" -eq 1 ] && rm_ "$ROOTFS/lib/firmware/mfc_fw.bin"
if [ "$DO_USER" -eq 1 ]; then
    rm_ "$ROOTFS/usr/lib/nuxel/nuxel-mfc-diag"
    rm_ "$ROOTFS/usr/lib/nuxel/nuxel-mfc-decode"
    rm_ "$ROOTFS/usr/lib/nuxel/nuxel-mfc-play"
    rm_ "$ROOTFS/usr/lib/nuxel/nuxel-mfc-safety-receipt.py"
    rm_ "$ROOTFS/usr/share/nuxel/mfc-status.schema.json"
    rm_ "$ROOTFS/run/nuxel/mfc/status.json"
fi
if [ "$DO_GUARD" -eq 1 ]; then
    for p in libgstvideo4linux2.so libgstv4l2codecs.so libgstkms.so libgstopengl.so; do
        f="$ROOTFS/usr/lib64/gstreamer-1.0/$p"
        d="$f.nuxel-disabled"
        if [ -e "$f" ] && [ ! -e "$d" ]; then
            if [ "$DRY" -eq 1 ]; then echo "would disable: $f"; else mv "$f" "$d" && echo "guard restored: $f"; fi
        fi
    done
    for d in "$ROOTFS/root/.cache/gstreamer-1.0" "$ROOTFS/home/nuxel/.cache/gstreamer-1.0"; do
        [ -d "$d" ] || continue
        if [ "$DRY" -eq 1 ]; then echo "would remove registry caches in $d"; else find "$d" -maxdepth 1 -name 'registry.*' -type f -delete 2>/dev/null || true; fi
    done
fi
echo "rollback complete (rootfs=$ROOTFS dry-run=$DRY)"
echo "kernel/DTB: keep the previous known-good boot image; this script never flashes."

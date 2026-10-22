#!/bin/sh
# a50-rollback.sh — restore the known-good A50-pre-change Nuxel userspace.
#
# A50 made no persistent changes, so this helper is a *documented* restore path
# for a FUTURE change, not something needed now. It:
#   1. verifies the known-good live bridge SHA-256 before considering a restore;
#   2. restores .prev binaries only after re-verifying them;
#   3. restarts the smallest affected service;
#   4. refuses any partition/boot/kernel/flash path and never reboots.
set -eu

KNOWN_BRIDGE="bc38e12d075ebdd9e7a4cec43740760948a35794ad2d51b303f79d4f6191d123"
BIN_DIR="/usr/lib/nuxel"

# Guards (echo-only in this run; apply via the live console deploy tool, not here)
for p in "$@"; do
  case "$p" in
    /dev/*|*boot*|*kernel*|*BOOT*|*dtb*|*DTBO*|*recovery*|*EFS*|*modem*)
      echo "REFUSED flash-adjacent path: $p" >&2; exit 2 ;;
  esac
done

echo "A50 rollback helper — reference only (A50 made no changes)."
echo "To restore the bridge after a future change:"
echo "  1. sha256sum $BIN_DIR/nuxel-wl-fb   # expect $KNOWN_BRIDGE"
echo "  2. cp -p $BIN_DIR/nuxel-wl-fb.prev $BIN_DIR/nuxel-wl-fb"
echo "  3. systemctl restart nuxel-wl-fb"
echo "To restore the PWA assets: use the A49 off-device backups + restart nuxel-wayland."
echo "Never reboot automatically; never write a partition/kernel/bootloader."
exit 0

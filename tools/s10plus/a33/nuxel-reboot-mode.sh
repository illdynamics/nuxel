#!/bin/bash
# nuxel-reboot-mode.sh — request a one-shot boot mode and reboot, from CLI/live console.
# Usage: nuxel-reboot-mode.sh {verbose|safe|diag|debug|normal}
set -u
MODE="${1:-}"
FLAGS=/var/lib/nuxel/boot
mkdir -p "$FLAGS"
case "$MODE" in
  verbose) echo "requested_by=nuxel-reboot-mode at=$(date -Iseconds)" > "$FLAGS/verbose-once" ;;
  safe)    echo "requested_by=nuxel-reboot-mode at=$(date -Iseconds)" > "$FLAGS/safe-mode-once" ;;
  diag)    echo "requested_by=nuxel-reboot-mode at=$(date -Iseconds)" > "$FLAGS/diag-once" ;;
  debug)   echo "requested_by=nuxel-reboot-mode at=$(date -Iseconds)" > "$FLAGS/debug-once" ;;
  normal)  rm -f "$FLAGS/verbose-once" "$FLAGS/safe-mode-once" "$FLAGS/diag-once" "$FLAGS/debug-once"; echo "all one-shot flags cleared"; exit 0 ;;
  *) echo "usage: nuxel-reboot-mode.sh {verbose|safe|diag|debug|normal}" >&2; exit 2 ;;
esac
echo "one-shot $MODE requested; rebooting now"
systemctl reboot
exit 0

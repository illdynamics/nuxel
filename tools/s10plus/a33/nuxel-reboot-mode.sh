#!/bin/bash
# nuxel-reboot-mode.sh — stage a one-shot mode; an actual reboot is separately
# guarded.  A mode request must never turn into an unbounded reboot merely
# because a console command was pasted or a UI callback was duplicated.
# Usage: nuxel-reboot-mode.sh {verbose|safe|diag|debug|normal} [--reboot --acknowledge]
set -u
MODE="${1:-}"
REBOOT=0
ACK=0
shift 2>/dev/null || true
while [ "$#" -gt 0 ]; do
  case "$1" in
    --reboot) REBOOT=1 ;;
    --acknowledge) ACK=1 ;;
    *) echo "usage: nuxel-reboot-mode.sh {verbose|safe|diag|debug|normal} [--reboot --acknowledge]" >&2; exit 2 ;;
  esac
  shift
done
FLAGS=/var/lib/nuxel/boot
mkdir -p "$FLAGS"
case "$MODE" in
  verbose) echo "requested_by=nuxel-reboot-mode at=$(date -Iseconds)" > "$FLAGS/verbose-once" ;;
  safe)    echo "requested_by=nuxel-reboot-mode at=$(date -Iseconds)" > "$FLAGS/safe-mode-once" ;;
  diag)    echo "requested_by=nuxel-reboot-mode at=$(date -Iseconds)" > "$FLAGS/diag-once" ;;
  debug)   echo "requested_by=nuxel-reboot-mode at=$(date -Iseconds)" > "$FLAGS/debug-once" ;;
  normal)  rm -f "$FLAGS/verbose-once" "$FLAGS/safe-mode-once" "$FLAGS/diag-once" "$FLAGS/debug-once"; echo "all one-shot flags cleared"; exit 0 ;;
  *) echo "usage: nuxel-reboot-mode.sh {verbose|safe|diag|debug|normal} [--reboot --acknowledge]" >&2; exit 2 ;;
esac
echo "one-shot $MODE requested; no reboot issued"
if [ "$REBOOT" -eq 1 ]; then
  if [ "$ACK" -ne 1 ]; then
    echo "REFUSED: --reboot requires --acknowledge" >&2
    exit 64
  fi
  if [ ! -x /usr/libexec/nuxel/nuxel-bootmode-guard.py ]; then
    echo "REFUSED: bootmode guard is absent; leave the request staged for a supervised reboot" >&2
    exit 69
  fi
  echo "REQUESTED_REBOOT=normal-userspace; invoke the bounded reboot policy, not systemctl directly"
  exit 75
fi
exit 0

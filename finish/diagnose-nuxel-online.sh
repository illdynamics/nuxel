#!/bin/bash
# Diagnostic watchdog: wait for the ocean fastboot device, then capture safe
# getvars + the full lk2nd/kernel oem log WITHOUT rebooting or flashing.
set -u
LOG=/x/nuxel/.diag.log
: > "$LOG"
log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }

log "diag watchdog started; polling for fastboot device (30 min)..."
DEADLINE=$(( $(date +%s) + 1800 ))
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  OUT="$(FBTIMEOUT=25 /tmp/fb devices 2>&1 || true)"
  if [ -n "$OUT" ]; then
    log "FOUND: $OUT"
    break
  fi
  sleep 2
done
OUT="$(FBTIMEOUT=25 /tmp/fb devices 2>&1 || true)"
if [ -z "$OUT" ]; then
  log "TIMEOUT: no device after 30 min."
  exit 2
fi

# Safe getvars only (NEVER current-slot / slot-suffixes / has-slot:*)
for v in product serialno securestate unlocked version max-download-size; do
  R="$(FBTIMEOUT=40 /tmp/fb getvar "$v" 2>&1 || true)"
  log "getvar $v => $(echo "$R" | tr '\n' ' ' | tr -s ' ')"
done

log "=== oem log ==="
FBTIMEOUT=60 /tmp/fb oem log 2>&1 | tee -a "$LOG"
log "=== diag capture complete; device left in fastboot ==="

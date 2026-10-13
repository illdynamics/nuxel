#!/bin/bash
# One-shot online finisher for the Moto G7 Power Nuxel flash.
# Waits for the stock-ABOOT fastboot device to enumerate, then flashes.
set -u
LOG=/x/nuxel/.flash-finish.log
WORK=/x/nuxel
DTBO="$WORK/build/out/g7power/stock/firmware/extracted/dtbo.img"
BOOT="$WORK/build/out/g7power/lk2nd-nuxel-qcdt-combined-boot.img"
ROOTFS="$WORK/build/out/g7power/nuxel-ocean-rootfs.img"

log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }

log "watchdog started; waiting for fastboot device..."

# Wait up to 20 minutes for a fastboot device to enumerate.
DEADLINE=$(( $(date +%s) + 1200 ))
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  OUT="$(FBTIMEOUT=30 /tmp/fb devices 2>&1 || true)"
  if [ -n "$OUT" ]; then
    log "device found: $OUT"
    break
  fi
  sleep 3
done

OUT="$(FBTIMEOUT=30 /tmp/fb devices 2>&1 || true)"
if [ -z "$OUT" ]; then
  log "TIMEOUT: no fastboot device enumerated after 20 min."
  exit 2
fi

log "preflight getvars"
FBTIMEOUT=60 /tmp/fb getvar product        2>&1 | tee -a "$LOG"
FBTIMEOUT=60 /tmp/fb getvar securestate    2>&1 | tee -a "$LOG"
FBTIMEOUT=60 /tmp/fb getvar max-download-size 2>&1 | tee -a "$LOG"

log "flashing stock dtbo"
FBTIMEOUT=300 /tmp/fb flash dtbo "$DTBO" 2>&1 | tee -a "$LOG"
log "flashing boot_a (lk2nd + nuxel qcdt)"
FBTIMEOUT=300 /tmp/fb flash boot_a "$BOOT" 2>&1 | tee -a "$LOG"
log "flashing boot_b (lk2nd + nuxel qcdt)"
FBTIMEOUT=300 /tmp/fb flash boot_b "$BOOT" 2>&1 | tee -a "$LOG"
log "flashing userdata rootfs (478 MiB)"
FBTIMEOUT=600 /tmp/fb flash userdata "$ROOTFS" 2>&1 | tee -a "$LOG"
log "rebooting"
FBTIMEOUT=120 /tmp/fb reboot 2>&1 | tee -a "$LOG"
log "DONE"

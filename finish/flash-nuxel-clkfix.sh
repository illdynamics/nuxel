#!/bin/bash
# Flash the clk_ignore_unused display-stability fix to BOTH boot slots.
# Safe getvars only (NEVER current-slot / slot-suffixes / has-slot:*).
set -u
LOG=/x/nuxel/.flash-clkfix.log
WORK=/x/nuxel
DTBO="$WORK/build/out/g7power/stock/firmware/extracted/dtbo.img"
BOOT="$WORK/build/out/g7power/lk2nd-nuxel-qcdt-sysb-clkfix-combined-boot.img"
log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }
: > "$LOG"

OUT="$(FBTIMEOUT=30 /tmp/fb devices 2>&1 || true)"
if [ -z "$OUT" ]; then
  log "no fastboot device"
  exit 2
fi
log "device: $OUT"
for v in product securestate max-download-size; do
  log "getvar $v: $(FBTIMEOUT=40 /tmp/fb getvar $v 2>&1 | tr '\n' ' ' | tr -s ' ')"
done
log "oem log (tail):"
FBTIMEOUT=60 /tmp/fb oem log 2>&1 | tail -30 | tee -a "$LOG"

log "flash dtbo (stock)"
FBTIMEOUT=300 /tmp/fb flash dtbo "$DTBO" 2>&1 | tee -a "$LOG"
log "flash boot_a (clkfix)"
FBTIMEOUT=300 /tmp/fb flash boot_a "$BOOT" 2>&1 | tee -a "$LOG"
log "flash boot_b (clkfix)"
FBTIMEOUT=300 /tmp/fb flash boot_b "$BOOT" 2>&1 | tee -a "$LOG"
log "reboot"
FBTIMEOUT=120 /tmp/fb reboot 2>&1 | tee -a "$LOG"
log "DONE"

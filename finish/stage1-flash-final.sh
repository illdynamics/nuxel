#!/bin/bash
# Nuxel G7 Power — STAGE 1: clean flash of the -final chain (guide §6)
# Fixes the earlier attempt's bug: `BOOT=... FBTIMEOUT=... $FB ...` never sets
# the shell var for "$BOOT" expansion (bash expands args BEFORE prefix assigns).
set -u
FB=/tmp/fb
W=/x/nuxel
LOG=$W/.stage1.log
DTBO=$W/build/out/g7power/stock/firmware/extracted/dtbo.img
BOOT=$W/build/out/g7power/lk2nd-nuxel-final-combined.img
ROOTFS=$W/build/out/g7power/nuxel-ocean-rootfs-final.img
log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }
: > "$LOG"

log "=== preflight (safe getvars only) ==="
log "devices: $(FBTIMEOUT=30 $FB devices 2>&1 | tr '\n' ' ')"
PROD=$(FBTIMEOUT=40 $FB getvar product 2>&1 | tr -d '\r')
SEC=$(FBTIMEOUT=40 $FB getvar securestate 2>&1 | tr -d '\r')
MDS=$(FBTIMEOUT=40 $FB getvar max-download-size 2>&1 | tr -d '\r')
log "product: $PROD"
log "securestate: $SEC"
log "max-download-size: $MDS"
case "$PROD" in *ocean*) : ;; *) log "ABORT: product is not ocean"; exit 1;; esac
case "$SEC" in *flashing_unlocked*) : ;; *) log "ABORT: not flashing_unlocked"; exit 1;; esac

log "=== 6.2 flash dtbo (stock, anti-brick step) ==="
FBTIMEOUT=120 $FB flash dtbo "$DTBO" 2>&1 | tee -a "$LOG"

log "=== 6.3 flash combined boot (lk2nd@0 + nuxel payload@512KiB) to boot_a ==="
FBTIMEOUT=300 $FB flash boot_a "$BOOT" 2>&1 | tee -a "$LOG"
log "=== 6.3 flash combined boot to boot_b ==="
FBTIMEOUT=300 $FB flash boot_b "$BOOT" 2>&1 | tee -a "$LOG"

log "=== 6.4 flash rootfs (478 MiB) to userdata ==="
FBTIMEOUT=900 $FB flash userdata "$ROOTFS" 2>&1 | tee -a "$LOG"
RC=${PIPESTATUS[0]}
if [ "$RC" -ne 0 ]; then
  log "userdata flash rc=$RC -> trying system_b fallback"
  FBTIMEOUT=900 $FB flash system_b "$ROOTFS" 2>&1 | tee -a "$LOG"
fi
log "=== STAGE 1 flashed; leaving device in fastboot (no reboot yet) ==="

#!/bin/bash
# Nuxel G7 Power — flash a combined (lk2nd+payload) boot image + rootfs, then
# leave the device in fastboot. usage: flash-chain.sh <combined.img> [rootfs]
set -u
FB=/tmp/fb
W=/x/nuxel
BOOT=${1:?usage: flash-chain.sh <combined-boot.img> [rootfs.img]}
ROOTFS=${2:-$W/build/out/g7power/nuxel-ocean-rootfs-final.img}
DTBO=$W/build/out/g7power/stock/firmware/extracted/dtbo.img
LOG=$W/.flash-chain.log
log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }
: > "$LOG"
log "preflight (safe getvars only)"
log "devices: $(FBTIMEOUT=30 $FB devices 2>&1 | tr '\n' ' ')"
PROD=$(FBTIMEOUT=40 $FB getvar product 2>&1 | tr -d '\r'); log "product: $PROD"
SEC=$(FBTIMEOUT=40 $FB getvar securestate 2>&1 | tr -d '\r'); log "securestate: $SEC"
case "$PROD" in *ocean*) :;; *) log "ABORT: product != ocean"; exit 1;; esac
case "$SEC" in *flashing_unlocked*) :;; *) log "ABORT: not flashing_unlocked"; exit 1;; esac
log "BOOT=$BOOT ($(stat -c%s "$BOOT" 2>/dev/null) bytes, sha $(sha256sum "$BOOT" | cut -c1-16))"
log "ROOTFS=$ROOTFS ($(stat -c%s "$ROOTFS" 2>/dev/null) bytes)"
log "=== 1/4 flash dtbo (stock, anti-brick, FIRST) ==="
FBTIMEOUT=120 $FB flash dtbo "$DTBO" 2>&1 | tee -a "$LOG"
log "=== 2/4 flash boot_a ==="
FBTIMEOUT=300 $FB flash boot_a "$BOOT" 2>&1 | tee -a "$LOG"
log "=== 3/4 flash boot_b ==="
FBTIMEOUT=300 $FB flash boot_b "$BOOT" 2>&1 | tee -a "$LOG"
log "=== 4/4 flash userdata (rootfs) ==="
FBTIMEOUT=900 $FB flash userdata "$ROOTFS" 2>&1 | tee -a "$LOG"
RC=${PIPESTATUS[0]}
if [ "$RC" -ne 0 ]; then
  log "userdata refused (rc=$RC) -> system_b fallback"
  FBTIMEOUT=900 $FB flash system_b "$ROOTFS" 2>&1 | tee -a "$LOG"
fi
log "=== chain flashed OK; device left in fastboot (no reboot yet) ==="

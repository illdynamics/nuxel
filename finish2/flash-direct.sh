#!/bin/bash
# Direct-boot chain: ABOOT boots the Nuxel kernel straight from `boot` (no lk2nd).
set -u
FB=/tmp/fb; W=/x/nuxel
DTBO=$W/build/out/g7power/stock/firmware/extracted/dtbo.img
BOOT=$W/build/out/g7power/nuxel-ocean-boot-simpledrm-qcdt.img
ROOTFS=$W/build/out/g7power/nuxel-ocean-rootfs-final.img
LOG=$W/.flash-direct.log
log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }
: > "$LOG"
log "devices: $(FBTIMEOUT=30 $FB devices 2>&1 | tr '\n' ' ')"
P=$(FBTIMEOUT=40 $FB getvar product 2>&1|tr -d '\r'); log "$P"
S=$(FBTIMEOUT=40 $FB getvar securestate 2>&1|tr -d '\r'); log "$S"
case "$P" in *ocean*) :;; *) log ABORT; exit 1;; esac
case "$S" in *flashing_unlocked*) :;; *) log ABORT; exit 1;; esac
log "=== 1/4 dtbo_a (stock) ==="; FBTIMEOUT=120 $FB flash dtbo_a "$DTBO" 2>&1 | tee -a "$LOG"
log "=== 2/4 boot_a = nuxel kernel (direct) ==="; FBTIMEOUT=300 $FB flash boot_a "$BOOT" 2>&1 | tee -a "$LOG"
log "=== 3/4 boot_b = nuxel kernel (direct) ==="; FBTIMEOUT=300 $FB flash boot_b "$BOOT" 2>&1 | tee -a "$LOG"
log "=== 4/4 system_b = rootfs ==="; FBTIMEOUT=900 $FB flash system_b "$ROOTFS" 2>&1 | tee -a "$LOG"
log "=== done ==="

#!/bin/bash
# Nuxel G7 Power — corrected (extlinux) chain. Leaves device in fastboot.
set -u
FB=/tmp/fb
W=/x/nuxel
DTBO=$W/build/out/g7power/stock/firmware/extracted/dtbo.img
LK2ND=$W/build/out/g7power/lk2nd.img
BOOTFS=$W/build/out/g7power/nuxel-boot-ext2-simpledrm.img
ROOTFS=$W/build/out/g7power/nuxel-ocean-rootfs-final.img
LOG=$W/.flash-extlinux.log
log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }
: > "$LOG"
log "preflight"
log "devices: $(FBTIMEOUT=30 $FB devices 2>&1 | tr '\n' ' ')"
P=$(FBTIMEOUT=40 $FB getvar product 2>&1 | tr -d '\r'); log "$P"
S=$(FBTIMEOUT=40 $FB getvar securestate 2>&1 | tr -d '\r'); log "$S"
case "$P" in *ocean*) :;; *) log "ABORT product"; exit 1;; esac
case "$S" in *flashing_unlocked*) :;; *) log "ABORT not unlocked"; exit 1;; esac
for f in "$DTBO" "$LK2ND" "$BOOTFS" "$ROOTFS"; do log "$(basename $f) $(stat -c%s $f) bytes sha $(sha256sum $f | cut -c1-16)"; done
log "=== 1/5 dtbo_a (stock) ==="; FBTIMEOUT=120 $FB flash dtbo_a "$DTBO" 2>&1 | tee -a "$LOG"
log "=== 2/5 boot_a = lk2nd ==="; FBTIMEOUT=300 $FB flash boot_a "$LK2ND" 2>&1 | tee -a "$LOG"
log "=== 3/5 boot_b = lk2nd ==="; FBTIMEOUT=300 $FB flash boot_b "$LK2ND" 2>&1 | tee -a "$LOG"
log "=== 4/5 system_a = extlinux bootfs ==="; FBTIMEOUT=300 $FB flash system_a "$BOOTFS" 2>&1 | tee -a "$LOG"
log "=== 5/5 system_b = rootfs ==="; FBTIMEOUT=900 $FB flash system_b "$ROOTFS" 2>&1 | tee -a "$LOG"
log "=== done; device left in fastboot ==="

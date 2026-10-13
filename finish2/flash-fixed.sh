#!/bin/bash
set -u
LOG=/x/nuxel/.flash-fixed.log
FB=/tmp/fb
W=/x/nuxel
BOOT="$W/build/out/g7power/lk2nd-nuxel-qcdt-fixed-combined.img"
ROOTFS="$W/build/out/g7power/nuxel-ocean-rootfs.img"
log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }
: > "$LOG"

log "start; devices: $(FBTIMEOUT=30 $FB devices 2>&1 | tr '\n' ' ')"
log "product: $(FBTIMEOUT=30 $FB getvar product 2>&1 | tr '\n' ' ')"
log "securestate: $(FBTIMEOUT=30 $FB getvar securestate 2>&1 | tr '\n' ' ')"

log "=== flash boot_a (combined: lk2nd@0 + fixed nuxel payload@512KiB) ==="
FBTIMEOUT=300 $FB flash boot_a "$BOOT" 2>&1 | tee -a "$LOG"
log "=== flash boot_b (combined, slot _b insurance) ==="
FBTIMEOUT=300 $FB flash boot_b "$BOOT" 2>&1 | tee -a "$LOG"
log "=== flash system_b (nuxel rootfs 478MiB) ==="
FBTIMEOUT=900 $FB flash system_b "$ROOTFS" 2>&1 | tee -a "$LOG"
log "=== flash system_a (nuxel rootfs 478MiB - hedge so either slot roots) ==="
FBTIMEOUT=900 $FB flash system_a "$ROOTFS" 2>&1 | tee -a "$LOG"
log "DONE flashing; device left in fastboot (not rebooting yet)"

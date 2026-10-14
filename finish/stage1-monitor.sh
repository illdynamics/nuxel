#!/bin/bash
set -u
FB=/tmp/fb
LOG=/x/nuxel/.stage1-boot.log
: > "$LOG"
log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }
log "issuing reboot -> $(FBTIMEOUT=60 $FB reboot 2>&1 | tr '\n' ' ')"
DEADLINE=$(( $(date +%s) + 180 ))
SAW_FASTBOOT=0
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  U="$(lsusb | grep -Ei '22b8:|1d6b:0104|05c6:' | sed 's/^.*ID //')"
  T="$(ls /dev/ttyACM* 2>/dev/null | tr '\n' ' ')"
  log "usb=[$(echo "$U" | tr '\n' ';')] ttyACM=[$T]"
  case "$U" in
    *1d6b:0104*) log "*** NUXEL USB GADGET UP (1d6b:0104) — userspace is alive ***"; break;;
    *22b8:2e80*) SAW_FASTBOOT=1;;
  esac
  sleep 4
done
log "done (saw_fastboot=$SAW_FASTBOOT)"

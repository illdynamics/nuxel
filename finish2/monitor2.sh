#!/bin/bash
# Observe USB transitions after a reboot for a window, with per-event timestamps.
# usage: monitor2.sh [seconds]   (default 180)
set -u
FB=/tmp/fb
LOG=/x/nuxel/.monitor2.log
WIN=${1:-180}
: > "$LOG"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
log "pre: devices=$(FBTIMEOUT=20 $FB devices 2>&1 | tr '\n' ' ')"
log "rebooting..."
FBTIMEOUT=60 $FB reboot 2>&1 | tee -a "$LOG"
END=$(( $(date +%s) + WIN ))
PREV=""
FB_EV=0; GD_EV=0; ACM_EV=0; EDL_EV=0
while [ "$(date +%s)" -lt "$END" ]; do
  U="$(lsusb 2>/dev/null | grep -Ei '22b8|1d6b:0104|05c6' | sed 's/^.*ID //' | tr '\n' ';')"
  T="$(ls /dev/ttyACM* 2>/dev/null | tr '\n' ' ')"
  CUR="$U|$T"
  if [ "$CUR" != "$PREV" ]; then
    log "t+$(( WIN - (END - $(date +%s)) ))s usb=[$U] ttyACM=[$T]"
    PREV="$CUR"
  fi
  case "$U" in *22b8*) FB_EV=1;; esac
  case "$U" in *1d6b:0104*) GD_EV=1;; esac
  case "$U" in *05c6*) EDL_EV=1;; esac
  [ -n "$T" ] && ACM_EV=1
  sleep 0.4
done
log "RESULT saw_fastboot=$FB_EV saw_gadget=$GD_EV saw_ttyACM=$ACM_EV saw_edl=$EDL_EV"
if [ "$FB_EV" = 1 ] && [ "$GD_EV" = 0 ] && [ "$ACM_EV" = 0 ]; then log "VERDICT: LOOP (back in fastboot)"; fi
if [ "$GD_EV" = 1 ] || [ "$ACM_EV" = 1 ]; then log "VERDICT: NUXEL USERSPACE UP"; fi
if [ "$FB_EV" = 0 ]; then log "VERDICT: no fastboot -> left it (black/up or silent loop)"; fi

#!/bin/bash
# Reboot the device and watch USB for 90s. Decides loop vs 'black/up'.
#  22b8:2e80 reappears  -> reboot-loop (screen flashing)  -> RETRY
#  1d6b:0104 / ttyACM0  -> Nuxel userspace up            -> SUCCESS
#  silence              -> left fastboot, no gadget seen -> ambiguous
set -u
FB=/tmp/fb
LOG=/x/nuxel/.boot-observed.log
: > "$LOG"
log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }
log "devices before reboot: $(FBTIMEOUT=20 $FB devices 2>&1 | tr '\n' ' ')"
log "rebooting..."
FBTIMEOUT=60 $FB reboot 2>&1 | tee -a "$LOG"
END=$(( $(date +%s) + 90 ))
SAW_FB=0; SAW_GADGET=0; SAW_ACM=0; SAW_EDL=0; N=0
while [ "$(date +%s)" -lt "$END" ]; do
  U="$(lsusb | grep -Ei '22b8:2e80|1d6b:0104|05c6:9008|0x05c6' | sed 's/^.*ID //')"
  T="$(ls /dev/ttyACM* 2>/dev/null | tr '\n' ' ')"
  if [ -n "$U" ] || [ -n "$T" ]; then
    N=$((N+1)); log "t+$(( 90 - (END - $(date +%s)) ))s usb=[$(echo "$U"|tr '\n' ';')] ttyACM=[$T]"
  fi
  case "$U" in *22b8:2e80*) SAW_FB=1;; *1d6b:0104*) SAW_GADGET=1;; *05c6:9008*) SAW_EDL=1;; esac
  [ -n "$T" ] && SAW_ACM=1
  sleep 0.5
done
log "RESULT: saw_fastboot=$SAW_FB saw_gadget=$SAW_GADGET saw_ttyACM=$SAW_ACM saw_edl=$SAW_EDL"
if [ "$SAW_FB" = 1 ] && [ "$SAW_GADGET" = 0 ]; then log "VERDICT: REBOOT-LOOP / back in fastboot -> fix & retry"; fi
if [ "$SAW_GADGET" = 1 ] || [ "$SAW_ACM" = 1 ]; then log "VERDICT: NUXEL USERSPACE UP (gadget/ttyACM) -> SUCCESS"; fi
if [ "$SAW_FB" = 0 ] && [ "$SAW_GADGET" = 0 ] && [ "$SAW_ACM" = 0 ]; then log "VERDICT: went silent (no fastboot, no gadget) -> likely black/up, ambiguous"; fi

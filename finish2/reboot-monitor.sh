#!/bin/bash
set -u
LOG=/x/nuxel/.boot-monitor.log
FB=/tmp/fb
: > "$LOG"
log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }
log "current devices: $(FBTIMEOUT=20 $FB devices 2>&1 | tr '\n' ' ')"
log "issuing reboot"
FBTIMEOUT=60 $FB reboot 2>&1 | tee -a "$LOG"
DEADLINE=$(( $(date +%s) + 150 ))
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  D="$(FBTIMEOUT=15 $FB devices 2>&1 | tr '\n' ' ')"
  if [ -n "$D" ]; then
    P="$(FBTIMEOUT=15 $FB getvar product 2>&1 | tr '\n' ' ')"
    log "ENUMERATED: $D | $P"
    case "$P" in
      *lk2nd*|*lk2nd-msm8953*) log "=== lk2nd fastboot; capturing oem log ==="; FBTIMEOUT=60 $FB oem log 2>&1 | tee /x/nuxel/.lk2nd-oemlog-fixed.txt | tail -40; log "CAPTURED"; exit 0 ;;
      *ocean*) log "stock ABOOT fastboot (boot did not stay up)"; exit 2 ;;
    esac
  fi
  sleep 5
done
log "NO USB enumeration within 150s (device may be up, or in a non-enumerating reboot loop)"

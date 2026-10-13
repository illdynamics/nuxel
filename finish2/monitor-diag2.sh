#!/bin/bash
set -u
LOG=/x/nuxel/.diag2-monitor.log
FB=/tmp/fb
: > "$LOG"
log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }
DEADLINE=$(( $(date +%s) + 220 ))
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  D="$(FBTIMEOUT=15 $FB devices 2>&1 | tr '\n' ' ')"
  if [ -n "$D" ]; then
    P="$(FBTIMEOUT=15 $FB getvar product 2>&1 | tr '\n' ' ')"
    log "ENUM: $D | $P"
    case "$P" in
      *lk2nd*)
        log "*** LK2ND FASTBOOT REACHED ***"
        log "--- oem log ---"; FBTIMEOUT=60 $FB oem log 2>&1 | tee /x/nuxel/.lk2nd-oemlog-diag2.txt
        log "--- oem ramoops regions ---"; FBTIMEOUT=60 $FB oem ramoops regions 2>&1 | tee -a "$LOG"
        log "--- oem ramoops raw (staged 512K) ---"
        FBTIMEOUT=120 $FB oem ramoops raw 2>&1 | tee -a "$LOG"
        FBTIMEOUT=120 $FB get_staged /x/nuxel/.ramoops-raw-diag2.bin 2>&1 | tee -a "$LOG"
        ls -la /x/nuxel/.ramoops-raw-diag2.bin 2>&1 | tee -a "$LOG"
        log "--- oem ramoops console ---"; FBTIMEOUT=60 $FB oem ramoops console 2>&1 | tee -a "$LOG"; FBTIMEOUT=60 $FB get_staged /x/nuxel/.ramoops-console-diag2.bin 2>&1 | tee -a "$LOG"
        log "--- oem ramoops dump ---"; FBTIMEOUT=60 $FB oem ramoops dump 2>&1 | tee -a "$LOG"; FBTIMEOUT=60 $FB get_staged /x/nuxel/.ramoops-dump-diag2.bin 2>&1 | tee -a "$LOG"
        log "DONE-CAPTURED"
        exit 0 ;;
      *ocean*) log "stock ABOOT fastboot (diag did not force lk2nd fastboot)"; sleep 5 ;;
    esac
  fi
  sleep 4
done
log "TIMEOUT: no lk2nd fastboot within 220s"

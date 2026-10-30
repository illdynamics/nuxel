#!/usr/bin/env bash
# Nuxel S10+ ABOX Calliope core-firmware reload.
#
# Root cause (PWNAGE-38000): this Samsung 4.14 kernel probes the ABOX before the
# rootfs is mounted, so request_firmware_direct() cannot find
# calliope_sram.bin/calliope_dram.bin during the first abox_enable().  The core
# firmware is only downloaded on a cold boot (has_reset=true).  Later runtime
# resumes take the "wakeup from WFI" path and skip the core download, so the
# ABOX DSP stays in `Invalid calliope state: 0` forever.
#
# Safe userspace fix: after /lib/firmware is actually available, force the ABOX
# device through one runtime-suspend/resume cycle.  runtime_suspend calls
# abox_disable() and runtime_resume calls abox_enable(); because the ABOX timer
# is not set, that resume is a cold-boot path and re-downloads the four core
# blobs.  This is the same resume path a normal device PM transition would use;
# it does not write mixer/register values and does not touch firmware partitions.
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

ABOX=/sys/devices/platform/18c50000.abox
CONTROL="${ABOX}/power/control"
STATUS="${ABOX}/power/runtime_status"
VERSION="${ABOX}/calliope_version"
FW_NAMES=(
    calliope_sram.bin
    calliope_sram_2.bin
    calliope_dram.bin
    calliope_dram_2.bin
)

log() { printf 'nuxel-abox-firmware-reload: %s\n' "$*" >&2; }

wait_for_status() {  # wait_for_status <desired> <tenths>
    local want="$1" max="${2:-50}" n=0 st
    while [ "$n" -lt "$max" ]; do
        st="$(cat "$STATUS" 2>/dev/null || true)"
        [ "$st" = "$want" ] && return 0
        n=$((n + 1))
        sleep 0.1
    done
    return 1
}

[ -d "$ABOX" ] || { log "ABOX sysfs node absent: $ABOX"; exit 1; }
[ -w "$CONTROL" ] || { log "ABOX power/control not writable"; exit 1; }

if timeout 2 grep -aq 'MUB0' "$VERSION" 2>/dev/null; then
    log "Calliope core firmware already loaded"
    exit 0
fi

missing=0
for fw in "${FW_NAMES[@]}"; do
    if [ ! -r "/lib/firmware/$fw" ] && [ ! -r "/usr/lib/firmware/$fw" ]; then
        log "firmware file missing: $fw"
        missing=1
    fi
done
[ "$missing" -eq 0 ] || { log "refusing to cycle ABOX without core firmware"; exit 1; }

orig="$(cat "$CONTROL" 2>/dev/null || true)"
[ -n "$orig" ] || orig=on
log "forcing ABOX runtime suspend/resume to reload core firmware (control was '$orig')"

echo auto > "$CONTROL"
if wait_for_status suspended 150; then
    log "ABOX runtime-suspended; resuming to reload core firmware"
else
    log "ABOX did not runtime-suspend within 15s (status=$(cat "$STATUS" 2>/dev/null || true))"
    printf '%s\n' "$orig" > "$CONTROL" || true
    exit 1
fi

# The resume write can block in uninterruptible rpm_resume on this 4.14
# vendor kernel for ~50 s on the first cold-boot PM cycle.  Bound it exactly
# like the suspend write; the boot wrapper retries the whole cycle when this
# attempt does not produce a MUB0 calliope_version.
if timeout -k 1 5 sh -c 'printf on > "$1"' _ "$CONTROL" 2>/dev/null; then
    log "ABOX runtime-resume requested"
else
    log "ABOX power/control resume write deferred (not ready)"
fi
wait_for_status active 50 || \
    log "ABOX did not become active within 5s (status=$(cat "$STATUS" 2>/dev/null || true))"

if [ "$orig" != on ]; then
    printf '%s\n' "$orig" > "$CONTROL" || true
fi

# Firmware download + BOOT_DONE IPC are asynchronous after resume, but on this
# hardware they complete in well under a second once the ABOX resumes.  Give it
# a short settle time, then probe without ever blocking boot forever.
sleep 3
if timeout 3 grep -aq 'MUB0' "$VERSION" 2>/dev/null; then
    log "Calliope core firmware loaded after PM cycle"
else
    log "PM cycle complete; calliope readiness not yet confirmed (audio route/test-audio will validate)"
fi
exit 0

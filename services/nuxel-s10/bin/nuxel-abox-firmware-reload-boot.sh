#!/usr/bin/env bash
# Boot-time wrapper for nuxel-abox-firmware-reload.sh.
#
# The Wayland session starts PipeWire and the audio-route service opens the ALSA
# card; both can hold an ABOX runtime-PM reference.  The core-firmware reload
# must run without that reference, so this wrapper stops them, waits for the
# audio processes to exit, reloads the blobs, then restarts them.  Boot sound is
# ordered after this unit, so it only plays once the DSP is ready.
#
# 2026-10-29: this used to trust the reload script's exit code, which is 0 even
# when `calliope_version` is still empty (the script reports "readiness not yet
# confirmed").  On a cold boot that left the DSP in `Invalid calliope state: 0`
# and RDMA1 accepted hw_params but never advanced hw_ptr - i.e. no audio at all.
# The wrapper now VERIFIES readiness (`calliope_version` == MUB0) and retries the
# PM cycle a bounded number of times before restoring the session.
set -uo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

ABOX=/sys/devices/platform/18c50000.abox
VERSION="$ABOX/calliope_version"
RELOAD=/usr/lib/nuxel/nuxel-abox-firmware-reload.sh
ATTEMPTS=${NUXEL_ABOX_RELOAD_ATTEMPTS:-4}

log() { printf 'nuxel-abox-firmware-reload-boot: %s\n' "$*" >&2; }

calliope_ready() {
    # MUB0 (the live Calliope core version).  The file is a raw u32; an
    # uninitialised DSP reads back empty or all zero.
    timeout 2 grep -aq 'MUB0' "$VERSION" 2>/dev/null
}

stop_session() {
    systemctl stop nuxel-wayland.service 2>/dev/null || true
    systemctl stop nuxel-audio-route.service 2>/dev/null || true
    systemctl stop nuxel-audio-route-retry.service 2>/dev/null || true
    local n=0
    while systemctl is-active nuxel-wayland.service nuxel-audio-route.service >/dev/null 2>&1; do
        n=$((n + 1))
        [ "$n" -lt 80 ] || break
        sleep 0.1
    done
    n=0
    while pgrep -f 'pipewire|wireplumber|gst-launch|pulseaudio' >/dev/null 2>&1; do
        n=$((n + 1))
        [ "$n" -lt 60 ] || break
        sleep 0.1
    done
    sleep 0.5
}

start_session() {
    log "restarting Nuxel audio route/session"
    # Start the session FIRST: it publishes the PipeWire runtime/socket the
    # route script verifies.  Starting the route before PipeWire exists made
    # the route defer with "static PipeWire sink absent" on every cold boot.
    systemctl --no-block start nuxel-wayland.service 2>/dev/null || true
    n=0
    while [ "$n" -lt 100 ]; do
        [ -S /run/nuxel-wayland/pipewire-0 ] && break
        n=$((n + 1))
        sleep 0.1
    done
    if [ -S /run/nuxel-wayland/pipewire-0 ]; then
        log "PipeWire session socket ready; applying the audio route"
    else
        log "PipeWire session socket not ready after 10s; route will rely on its retry timer"
    fi
    # Synchronous and bounded by the route unit's TimeoutStartSec.  The boot cue
    # is ordered After=this unit; returning before the route has applied made a
    # one-shot 45 s cue fail on a cold boot even though the route succeeded
    # ~27 s later.
    systemctl start nuxel-audio-route.service 2>/dev/null || \
        log "audio route not ready yet; retry timer will re-apply it"
}

# Fast path: the kernel already loaded the core blobs (CONFIG_EXTRA_FIRMWARE, or
# a normal warm resume).  Never cycle the DSP for nothing.
if calliope_ready; then
    log "Calliope core firmware already loaded (version=MUB0); no PM cycle needed"
    exit 0
fi

log "stopping Nuxel audio session/route before ABOX firmware reload"
stop_session

rc=1
attempt=0
while [ "$attempt" -lt "$ATTEMPTS" ]; do
    attempt=$((attempt + 1))
    log "ABOX firmware reload attempt $attempt/$ATTEMPTS"
    if [ -x "$RELOAD" ]; then
        timeout 60 "$RELOAD" >&2 || log "reload script returned $?"
    else
        log "reload script absent: $RELOAD"
        break
    fi
    # BOOT_DONE IPC is asynchronous after the resume; poll instead of guessing.
    n=0
    while [ "$n" -lt 40 ]; do
        if calliope_ready; then rc=0; break; fi
        n=$((n + 1))
        sleep 0.25
    done
    [ "$rc" -eq 0 ] && break
    log "calliope_version still not MUB0 after attempt $attempt"
    # A later attempt needs the session gone again (PipeWire may have grabbed the
    # card between attempts on a retry path).
    stop_session
done

if [ "$rc" -eq 0 ]; then
    log "Calliope core firmware READY (version=MUB0) after $attempt attempt(s)"
else
    log "Calliope core firmware NOT ready after $attempt attempt(s); restoring session honestly"
fi

start_session
exit "$rc"

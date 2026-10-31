#!/bin/sh
# Nuxel standalone audio session.  PipeWire/WirePlumber/PipeWire-Pulse run in
# their own systemd cgroup so the ABOX core-firmware reload can drop the ALSA
# runtime-PM reference without stopping the compositor or the launcher.
set -eu
RUNTIME=${XDG_RUNTIME_DIR:-/run/nuxel-wayland}
export XDG_RUNTIME_DIR="$RUNTIME"
export PIPEWIRE_RUNTIME_DIR="$RUNTIME"
export PULSE_SERVER="${PULSE_SERVER:-unix:$RUNTIME/pulse/native}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$RUNTIME/bus}"
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

log() { printf '%s nuxel-audio-session: %s\n' "$(date -u +%FT%TZ)" "$*"; }

# The session bus is created by nuxel-session.sh before the launcher starts.
n=0
while [ ! -S "$RUNTIME/bus" ] && [ "$n" -lt 100 ]; do n=$((n+1)); sleep 0.1; done
[ -S "$RUNTIME/bus" ] || log "session bus not ready; continuing without it"

chgrp -R audio /dev/snd 2>/dev/null || true
chmod -R g+rw /dev/snd 2>/dev/null || true

pipewire >/run/nuxel-pipewire.out 2>&1 &
PIPE_PID=$!
n=0
while [ ! -S "$RUNTIME/pipewire-0" ] && [ "$n" -lt 40 ]; do n=$((n+1)); sleep 0.1; done
if [ ! -S "$RUNTIME/pipewire-0" ]; then
  log "pipewire socket missing after 4s"
  kill "$PIPE_PID" 2>/dev/null || true
  exit 1
fi
log "pipewire socket ready pid=$PIPE_PID"
wireplumber >/run/nuxel-wireplumber.out 2>&1 &
pipewire-pulse >/run/nuxel-pipewire-pulse.out 2>&1 &
wait "$PIPE_PID"

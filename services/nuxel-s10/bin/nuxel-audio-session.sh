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

# A socket inode is created before the core accepts clients.  WirePlumber exits
# immediately with "Failed to connect to PipeWire" when it races that window.
# On 2026-11-07 this left the whole image without a default sink/source:
#   * nuxel-audio-route.sh could not set the default sink, so the route stayed
#     deferred and nuxel-soundd refused every cue;
#   * the button manager's wpctl readback failed and fell back to the 0..1 ALSA
#     fader, making volume keys jump only between 0% and 100%;
#   * Capture defaulted to the speaker monitor instead of the WDMA1 mic.
# Wait for the real core object before starting clients.
deadline=$(( $(date +%s) + 10 ))
core_ready=0
while [ "$(date +%s)" -lt "$deadline" ]; do
  if [ -S "$RUNTIME/pipewire-0" ] && \
     timeout -k 1 1 pw-cli info 0 2>/dev/null | grep -q 'PipeWire:Interface:Core'; then
    core_ready=1
    break
  fi
  sleep 0.1
done
if [ ! -S "$RUNTIME/pipewire-0" ]; then
  log "pipewire socket missing after 10s"
  kill "$PIPE_PID" 2>/dev/null || true
  exit 1
fi
if [ "$core_ready" -eq 1 ]; then
  log "pipewire core ready pid=$PIPE_PID"
else
  log "pipewire socket present but core not yet accepting clients; WirePlumber will retry"
fi

# WirePlumber owns the default-node metadata and session policy.  Keep it
# supervised: if PipeWire is restarted (the ABOX firmware reload does this at
# boot) WirePlumber exits and must reconnect, otherwise the default sink and
# source remain unpublished for the rest of the boot.
start_wireplumber() {
  while :; do
    wireplumber >>/run/nuxel-wireplumber.out 2>&1
    rc=$?
    log "wireplumber exited rc=$rc; restarting in 1s"
    sleep 1
  done
}
start_wireplumber &
WIRE_PID=$!

# Pulse compatibility is a separate PipeWire client.  Start it after the core
# is reachable; it will publish the same default sink/source that WirePlumber
# selects.
pipewire-pulse >/run/nuxel-pipewire-pulse.out 2>&1 &
PULSE_PID=$!

# systemd stops this unit before the ABOX core-firmware reload and on every
# reboot.  PipeWire may ignore the first SIGTERM for several seconds; forward it
# explicitly and bound the wait so a stop is deterministic (not an 8 s timeout).
term() {
  trap - TERM INT
  kill -TERM "$PULSE_PID" "$WIRE_PID" "$PIPE_PID" 2>/dev/null || true
  pkill -TERM -x wireplumber 2>/dev/null || true
  n=0
  while [ "$n" -lt 30 ]; do
    kill -0 "$PIPE_PID" 2>/dev/null || break
    n=$((n+1)); sleep 0.1
  done
  kill -KILL "$PULSE_PID" "$WIRE_PID" "$PIPE_PID" 2>/dev/null || true
  pkill -KILL -x wireplumber 2>/dev/null || true
  wait 2>/dev/null || true
  exit 0
}
trap term TERM INT

wait "$PIPE_PID"

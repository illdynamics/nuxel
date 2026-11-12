#!/bin/sh
# Give the unprivileged session user access to the root-owned PulseAudio/
# PipeWire socket.  Nothing is widened beyond the nuxel group; every path is
# created by this script (never by the audio daemon) where needed.
set -u
PULSE_DIR=/run/nuxel-wayland/pulse
SOCK=$PULSE_DIR/native
USER_RT=/run/user/1000

if ! getent group nuxel >/dev/null 2>&1; then
    echo "nuxel-audio-perms: group nuxel missing; nothing to do"
    exit 0
fi

# This unit is ordered after the audio session, but PipeWire may still be
# creating pulse/ when it runs; wait (bounded) for the socket instead of
# silently doing nothing (which is how the mic disappeared after reboots).
i=0
while [ ! -S "$SOCK" ] && [ "$i" -lt 100 ]; do
    sleep 0.1
    i=$((i + 1))
done

if [ -d "$PULSE_DIR" ]; then
    chgrp nuxel "$PULSE_DIR" 2>/dev/null || true
    chmod 0750 "$PULSE_DIR" 2>/dev/null || true
fi
# The socket must be a real socket file owned by the audio daemon; a symlink
# here (even one a helper created pointing at itself) breaks the server.
if [ -L "$SOCK" ]; then
    rm -f "$SOCK" 2>/dev/null || true
fi
if [ -S "$SOCK" ]; then
    chgrp nuxel "$SOCK" 2>/dev/null || true
    chmod 0770 "$SOCK" 2>/dev/null || true
fi

# Flatpak --socket=pulseaudio resolves the socket through $XDG_RUNTIME_DIR/pulse.
# A directory symlink would recurse back into itself once the link is replaced,
# so the directory is real and only the socket inside it is linked.
if [ -L "$USER_RT/pulse" ]; then
    rm -f "$USER_RT/pulse" 2>/dev/null || true
fi
mkdir -p "$USER_RT/pulse" 2>/dev/null || true
chown nuxel:nuxel "$USER_RT/pulse" 2>/dev/null || true
chmod 0750 "$USER_RT/pulse" 2>/dev/null || true
if [ -S "$SOCK" ]; then
    rm -f "$USER_RT/pulse/native" 2>/dev/null || true
    ln -s "$SOCK" "$USER_RT/pulse/native" 2>/dev/null || true
    chown -h nuxel:nuxel "$USER_RT/pulse/native" 2>/dev/null || true
fi
echo "nuxel-audio-perms: $SOCK -> ${SOCK} (group nuxel), published at $USER_RT/pulse/native"

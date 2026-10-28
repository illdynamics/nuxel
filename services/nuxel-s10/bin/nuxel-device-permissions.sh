#!/bin/sh
# Device-node policy for images where systemd-udevd cannot run on the 4.14
# vendor kernel.  The live image has systemd-udevd masked, so this script is the
# authoritative policy; the udev rules are intentionally NOT installed.
set -u
say() { echo "$(date -u +%FT%TZ) nuxel-device-permissions: $*"; }

# nuxel is in the audio group.  Use one group for the nodes the user-facing
# console tools need; the daemons themselves run as root.
if [ -d /dev/snd ]; then
    chgrp audio /dev/snd/* 2>/dev/null || true
    chmod 0660 /dev/snd/* 2>/dev/null || true
    say "sound nodes group=audio mode=0660"
fi
for t in /dev/ttySAC1 /dev/ttyBCM /dev/ttyHS*; do
    [ -e "$t" ] || continue
    chgrp audio "$t" 2>/dev/null || true
    chmod 0660 "$t" 2>/dev/null || true
    say "$t group=audio mode=0660"
done
if [ -e /dev/rfkill ]; then
    chgrp audio /dev/rfkill 2>/dev/null || true
    chmod 0660 /dev/rfkill 2>/dev/null || true
    say "/dev/rfkill group=audio mode=0660"
fi
for i in /dev/input/event*; do
    [ -e "$i" ] || continue
    chgrp audio "$i" 2>/dev/null || true
    chmod 0660 "$i" 2>/dev/null || true
done
exit 0

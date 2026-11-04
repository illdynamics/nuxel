#!/bin/sh
# PWNAGE-63000: lock the Nuxel Secret Service collection before suspend.
# This script never prints or stores a secret.  It is installed as
# /usr/lib/systemd/system-sleep/nuxel-keyring-lock and is also safe to run by hand.
set -eu
BUS=/run/nuxel-wayland/bus
[ -S "$BUS" ] || exit 0
ADDR="unix:path=$BUS"
DEF=$(timeout 5 busctl --address="$ADDR" call org.freedesktop.secrets \
        /org/freedesktop/secrets org.freedesktop.Secret.Service \
        ReadAlias s default 2>/dev/null | sed -n 's/^o "\(.*\)"$/\1/p' || true)
[ -n "$DEF" ] && [ "$DEF" != "/" ] || exit 0
timeout 8 busctl --address="$ADDR" call org.freedesktop.secrets \
    /org/freedesktop/secrets org.freedesktop.Secret.Service \
    Lock ao 1 "$DEF" >/dev/null 2>&1 || true
logger -t nuxel-keyring "pre-suspend collection lock requested" 2>/dev/null || true
exit 0

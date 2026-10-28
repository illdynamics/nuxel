#!/bin/sh
# Early boot wrapper for nuxel-device-permissions.service.
#
# This unit is ordered Before=nuxel-wayland.service, so it installs the staged
# PWN36000 files before the compositor/lockscreen exists.  The slower service
# work (package install, Bluetooth/geoclue/Wi-Fi restarts) is delegated to a
# transient unit so it cannot delay the panel or be killed with this oneshot.
set -u
LOG=/var/lib/nuxel/apply-pwnage36000.log
say() { printf '%s %s\n' "$(date -u +%FT%TZ 2>/dev/null || date)" "$*" >>"$LOG" 2>/dev/null || true; }

REAL=/usr/lib/nuxel/nuxel-device-permissions.sh.real-36000
if [ -x "$REAL" ]; then
    "$REAL" "$@" >>"$LOG" 2>&1 || true
fi

STAGE=${NUXEL_STAGE:-/usr/lib/nuxel/stage36000}
if [ -f "$STAGE/apply-pwnage36000.sh" ]; then
    say "early-wrapper: files-only begin"
    sh "$STAGE/apply-pwnage36000.sh" --files-only >>"$LOG" 2>&1 || true
    say "early-wrapper: files-only done"
    if command -v systemd-run >/dev/null 2>&1 && \
       systemd-run --unit=nuxel-apply-36000 --collect --no-block \
           /bin/sh "$STAGE/apply-pwnage36000.sh" --services >>"$LOG" 2>&1; then
        say "early-wrapper: services delegated to nuxel-apply-36000"
    else
        say "early-wrapper: systemd-run unavailable; using detached fallback"
        ( setsid sh "$STAGE/apply-pwnage36000.sh" --services >>"$LOG" 2>&1 & ) || true
    fi
else
    say "early-wrapper: stage missing at $STAGE"
fi
exit 0

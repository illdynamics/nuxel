#!/bin/sh
# NUXEL-105200: guarantee the owner's LAN is in the sshd AllowUsers allowlist.
#
# Why this exists
# ---------------
# 60-nuxel-tri-link.conf restricts SSH to 10.20.30.0/24 + 10.15.19.0/24 (and
# loopback).  The owner's home LAN is 192.168.178.0/24, and that CIDR lived only
# in 61-nuxel-lan38.conf, installed by one deploy step.  Whenever that step was
# skipped, lost with an image rebuild, or shadowed, sshd refused every Wi-Fi
# connection BEFORE authentication ("Permission denied (publickey)") while the
# USB console still worked -- the measured "Wi-Fi SSH is broken" symptom.
#
# The fix is a drop-in that is written *and verified* every time sshd starts, so
# the allowlist can never silently regress.  It only ever EXTENDS the allowlist
# (sshd accumulates AllowUsers across drop-ins) and it never touches auth
# methods: 60-nuxel-tri-link.conf still enforces public-key-only, root
# prohibit-password, and no tunnels.
#
# Idempotent; no-op when the file already has the exact contents.
set -u
DIR=/etc/ssh/sshd_config.d
F="$DIR/61-nuxel-lan38.conf"
WANT='AllowUsers nuxel@192.168.178.0/24 root@192.168.178.0/24'
log() { printf 'nuxel-ssh-lan-allow: %s\n' "$*" >&2; }

[ -d "$DIR" ] || { log "no $DIR (sshd has no drop-in support?) - nothing to do"; exit 0; }

if [ -r "$F" ] && grep -Eq "^[[:space:]]*${WANT}[[:space:]]*$" "$F"; then
    exit 0
fi

tmp="$F.nuxel-new.$$"
{
    printf '# Nuxel - owner home LAN SSH allowlist (managed by nuxel-ssh-lan-allow).\n'
    printf '# Generated because the CIDR was missing from the live drop-in.\n'
    printf '%s\n' "$WANT"
} > "$tmp" 2>/dev/null || { log "cannot write $tmp"; exit 1; }
chmod 0644 "$tmp" 2>/dev/null || true
mv -f "$tmp" "$F" || { rm -f "$tmp"; log "cannot install $F"; exit 1; }

if [ -r "$F" ] && grep -Eq "^[[:space:]]*${WANT}[[:space:]]*$" "$F"; then
    log "installed LAN allowlist in $F"
    exit 0
fi
log "installed $F but it does not verify - inspect it"
exit 1

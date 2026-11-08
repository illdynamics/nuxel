#!/bin/sh
# Print the Nuxel banner once for a LOCAL interactive login shell.
# Deliberately silent for SSH sessions (sshd already prints /etc/banner via
# ssHD Banner), non-interactive commands, SCP/SFTP, pipes and nested shells.
# v0.8.2: one banner only, and the SSH one is /etc/banner.  zsh prints the same banner from nuxel.zsh; the shared
# NUXEL_BANNER_SHOWN marker prevents duplication when one shell execs another.
case $- in *i*) ;; *) return 0 2>/dev/null || exit 0 ;; esac
[ -t 1 ] || { return 0 2>/dev/null || exit 0; }
[ -n "${SSH_CONNECTION:-}${SSH_CLIENT:-}${SSH_TTY:-}" ] && { return 0 2>/dev/null || exit 0; }
[ "${NUXEL_BANNER:-1}" = "0" ] && { return 0 2>/dev/null || exit 0; }
[ -n "${NUXEL_BANNER_SHOWN:-}" ] && { return 0 2>/dev/null || exit 0; }
NUXEL_BANNER_SHOWN=1
export NUXEL_BANNER_SHOWN
# /etc/banner is the canonical owner-supplied banner (also used by sshd).
# The legacy /etc/nuxel/banner fallback exists only for images that predate
# that file; it is never printed for an SSH session.
if [ -r /etc/banner ]; then
    cat /etc/banner
elif [ -r /etc/nuxel/banner ]; then
    cat /etc/nuxel/banner
elif [ -r /usr/lib/nuxel/zsh/nuxel-banner ]; then
    cat /usr/lib/nuxel/zsh/nuxel-banner
fi

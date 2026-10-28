#!/bin/sh
# Print the Nuxel banner once for an interactive login shell.
# Deliberately silent for non-interactive commands, SCP/SFTP, pipes and
# nested shells.  zsh prints the same banner from nuxel.zsh; the shared
# NUXEL_BANNER_SHOWN marker prevents duplication when one shell execs another.
case $- in *i*) ;; *) return 0 2>/dev/null || exit 0 ;; esac
[ -t 1 ] || { return 0 2>/dev/null || exit 0; }
[ "${NUXEL_BANNER:-1}" = "0" ] && { return 0 2>/dev/null || exit 0; }
[ -n "${NUXEL_BANNER_SHOWN:-}" ] && { return 0 2>/dev/null || exit 0; }
NUXEL_BANNER_SHOWN=1
export NUXEL_BANNER_SHOWN
if [ -r /etc/nuxel/banner ]; then
    cat /etc/nuxel/banner
elif [ -r /usr/lib/nuxel/zsh/nuxel-banner ]; then
    cat /usr/lib/nuxel/zsh/nuxel-banner
fi

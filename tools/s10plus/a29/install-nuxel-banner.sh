#!/bin/sh
# Install the repository's ./banner as the one canonical console banner.
#
# Paths:
#   /etc/banner                         exact copy (root:root 0644)
#   /etc/issue -> /etc/banner            local getty / serial login prompt
#   /etc/ssh/sshd_config.d/50-nuxel-banner.conf
#                                        pre-auth SSH banner
#   /etc/profile.d/99-nuxel-banner.sh    local USB/TTY interactive shells only
#
# The SSH banner is shown before authentication and the profile hook is skipped
# for SSH sessions, so a remote login sees the banner exactly once.  Running
# sshd -t before reload prevents a malformed drop-in from locking out SSH.
set -eu

ROOT="${NUXEL_ROOT:-}"
SRC="${1:-}"
[ -n "$SRC" ] || SRC="$(cd "$(dirname "$0")/../../.." && pwd)/banner"
[ -f "$SRC" ] || { echo "banner source not found: $SRC" >&2; exit 1; }

install_file() { # source target mode
    src="$1"; dst="$2"; mode="$3"
    mkdir -p "$(dirname "$dst")"
    if [ -e "$dst" ] && [ ! -e "$dst.pwnage33000-bak" ]; then
        cp -a "$dst" "$dst.pwnage33000-bak"
    fi
    install -m "$mode" -o root -g root "$src" "$dst"
}

install_file "$SRC" "$ROOT/etc/banner" 0644

# /etc/issue is normally a symlink to ../usr/lib/issue.  Replace it with a
# symlink to the canonical banner; keep the old link as a backup.
if [ -L "$ROOT/etc/issue" ] && [ ! -e "$ROOT/etc/issue.pwnage33000-bak" ]; then
    cp -a "$ROOT/etc/issue" "$ROOT/etc/issue.pwnage33000-bak"
fi
ln -sfn /etc/banner "$ROOT/etc/issue"

mkdir -p "$ROOT/etc/ssh/sshd_config.d"
if [ -e "$ROOT/etc/ssh/sshd_config.d/50-nuxel-banner.conf" ]; then
    [ -e "$ROOT/etc/ssh/sshd_config.d/50-nuxel-banner.conf.pwnage33000-bak" ] || \
        cp -a "$ROOT/etc/ssh/sshd_config.d/50-nuxel-banner.conf" \
              "$ROOT/etc/ssh/sshd_config.d/50-nuxel-banner.conf.pwnage33000-bak"
fi
cat > "$ROOT/etc/ssh/sshd_config.d/50-nuxel-banner.conf" <<'SSHD'
# Nuxel canonical banner (pre-authentication).  Source: /etc/banner.
Banner /etc/banner
SSHD
chmod 0644 "$ROOT/etc/ssh/sshd_config.d/50-nuxel-banner.conf"

if [ -e "$ROOT/etc/profile.d/99-nuxel-banner.sh" ]; then
    [ -e "$ROOT/etc/profile.d/99-nuxel-banner.sh.pwnage33000-bak" ] || \
        cp -a "$ROOT/etc/profile.d/99-nuxel-banner.sh" \
              "$ROOT/etc/profile.d/99-nuxel-banner.sh.pwnage33000-bak"
fi
cat > "$ROOT/etc/profile.d/99-nuxel-banner.sh" <<'PROFILE'
# Local TTY/USB-serial interactive sessions only.  SSH already receives the
# canonical banner pre-authentication, so it is intentionally skipped here.
case $- in *i*) ;; *) return 0 2>/dev/null || exit 0 ;; esac
[ -n "${SSH_CONNECTION:-}" ] && return 0 2>/dev/null || true
[ -r /etc/banner ] && cat /etc/banner
PROFILE
chmod 0644 "$ROOT/etc/profile.d/99-nuxel-banner.sh"

if [ -z "$ROOT" ]; then
    if command -v sshd >/dev/null 2>&1; then
        sshd -t
    fi
    if systemctl is-active --quiet sshd 2>/dev/null; then
        systemctl reload sshd
    fi
fi

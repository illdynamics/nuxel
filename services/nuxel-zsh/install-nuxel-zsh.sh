#!/bin/sh
# install-nuxel-zsh.sh — idempotent Nuxel zsh + prompt + banner installer.
#
#   sudo ./install-nuxel-zsh.sh                 # install for all users
#   sudo ./install-nuxel-zsh.sh --set-shell nuxel
#   ./install-nuxel-zsh.sh --root /tmp/stage --no-package   # test/stage
#
# It never changes a user's default shell unless --set-shell is given, and
# never overwrites an existing system or user configuration without a backup.
set -eu

HERE=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=/
SET_SHELL=
DO_PACKAGE=1
USER_NAME=
ROOT_EXPLICIT=0

usage() {
    cat <<'USAGE'
usage: install-nuxel-zsh.sh [--root DIR] [--set-shell [USER]] [--no-package]

  --root DIR         stage under DIR instead of / (for tests/images)
  --set-shell [USER] change USER's login shell to zsh (default: root)
  --no-package       do not install the zsh package; fail if zsh is absent
USAGE
}

while [ $# -gt 0 ]; do
    case $1 in
        --root) [ $# -ge 2 ] || { echo "install: --root needs a directory" >&2; exit 2; }; ROOT=$2; ROOT_EXPLICIT=1; shift ;;
        --set-shell)
            SET_SHELL=1
            if [ $# -ge 2 ] && [ "${2#-}" = "$2" ]; then USER_NAME=$2; shift; fi
            ;;
        --no-package) DO_PACKAGE=0 ;;
        --help|-h) usage; exit 0 ;;
        *) echo "install: unknown option '$1'" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

if [ "$ROOT" = "/" ]; then DEST=; else DEST=${ROOT%/}; fi
t() { printf '%s%s\n' "$DEST" "$1"; }

need_root() {
    if [ "$ROOT_EXPLICIT" = 0 ] && [ "$(id -u)" != 0 ]; then
        echo "install: run as root (or use --root DIR for staging)" >&2
        exit 1
    fi
}
need_root

find_zsh() {
    if command -v zsh >/dev/null 2>&1; then command -v zsh; return 0; fi
    for z in /bin/zsh /usr/bin/zsh /usr/local/bin/zsh; do [ -x "$z" ] && { echo "$z"; return 0; }; done
    return 1
}

if ! ZSH=$(find_zsh); then
    if [ "$DO_PACKAGE" = 0 ]; then
        echo "install: zsh not found and --no-package was given" >&2
        exit 1
    fi
    echo "install: zsh not found; installing via the available package manager"
    if command -v dnf >/dev/null 2>&1; then dnf install -y zsh
    elif command -v apt-get >/dev/null 2>&1; then apt-get update && apt-get install -y zsh
    elif command -v pacman >/dev/null 2>&1; then pacman -Sy --noconfirm zsh
    elif command -v zypper >/dev/null 2>&1; then zypper --non-interactive install zsh
    else echo "install: no supported package manager; install zsh first" >&2; exit 1
    fi
    ZSH=$(find_zsh) || { echo "install: zsh still not found after install" >&2; exit 1; }
fi
echo "install: zsh = $ZSH"

install -d -m 0755 "$(t /usr/lib/nuxel/zsh)" "$(t /etc/nuxel)" "$(t /etc/profile.d)" "$(t /usr/local/bin)"
install -m 0644 "$HERE/nuxel.zsh" "$(t /usr/lib/nuxel/zsh/nuxel.zsh)"
install -m 0755 "$HERE/nuxel-theme" "$(t /usr/lib/nuxel/zsh/nuxel-theme)"
install -m 0755 "$HERE/nuxel-theme" "$(t /usr/local/bin/nuxel-theme)"
install -m 0644 "$HERE/nuxel-banner" "$(t /usr/lib/nuxel/zsh/nuxel-banner)"
install -m 0755 "$HERE/nuxel-banner.sh" "$(t /etc/profile.d/nuxel-banner.sh)"

# System defaults: never clobber an existing file.  A local admin may have
# already chosen a different default; per-user nuxel-theme remains available.
if [ -e "$(t /etc/nuxel/zsh.conf)" ]; then
    echo "install: keeping existing /etc/nuxel/zsh.conf"
else
    install -m 0644 "$HERE/nuxel-zsh.conf" "$(t /etc/nuxel/zsh.conf)"
    echo "install: wrote /etc/nuxel/zsh.conf (theme 1 default)"
fi
if [ -e "$(t /etc/nuxel/banner)" ]; then
    echo "install: keeping existing /etc/nuxel/banner"
else
    install -m 0644 "$HERE/nuxel-banner" "$(t /etc/nuxel/banner)"
    echo "install: wrote /etc/nuxel/banner"
fi

# Global zshrc source block.  Back up once per changed install and never add
# the block twice (idempotent).
ZSHRC=$(t /etc/zshrc)
MARK_BEGIN='# >>> nuxel-zsh >>>'
MARK_END='# <<< nuxel-zsh <<<'
if [ -f "$ZSHRC" ] && grep -Fq "$MARK_BEGIN" "$ZSHRC"; then
    echo "install: /etc/zshrc already sources nuxel.zsh"
else
    if [ -f "$ZSHRC" ]; then
        backup="$ZSHRC.nuxel-rollback.$(date +%Y%m%dT%H%M%S)"
        cp -p "$ZSHRC" "$backup"
        echo "install: backed up /etc/zshrc -> $backup"
    fi
    {
        printf '\n%s\n' "$MARK_BEGIN"
        printf '[ -r /usr/lib/nuxel/zsh/nuxel.zsh ] && source /usr/lib/nuxel/zsh/nuxel.zsh\n'
        printf '%s\n' "$MARK_END"
    } >> "$ZSHRC"
    echo "install: /etc/zshrc sources /usr/lib/nuxel/zsh/nuxel.zsh"
fi

if [ "$SET_SHELL" = 1 ]; then
    USER_NAME=${USER_NAME:-root}
    if [ "$DEST" != "" ]; then
        echo "install: --set-shell skipped for staged root $ROOT" >&2
    elif ! id "$USER_NAME" >/dev/null 2>&1; then
        echo "install: unknown user '$USER_NAME'" >&2; exit 1
    else
        if command -v chsh >/dev/null 2>&1; then
            chsh -s "$ZSH" "$USER_NAME"
            echo "install: login shell for $USER_NAME -> $ZSH"
        else
            echo "install: chsh not available; change $USER_NAME's shell manually" >&2
        fi
    fi
fi

echo "install: done. Open a new zsh to use theme 1; run 'nuxel-theme' to switch."

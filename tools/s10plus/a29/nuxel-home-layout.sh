#!/bin/sh
# Establish the Nuxel session user's home layout idempotently.
#
# This is deliberately NOT hard-coded to /home/user: the user name and home
# come from the account database (NUXEL_SESSION_USER, default nuxel).  Existing
# files and existing directory ownership are never overwritten; missing folders
# are created with the user's ownership, and the XDG user-dirs file is created
# only when absent so a user's own choices are preserved.
set -eu

USER_NAME="${NUXEL_SESSION_USER:-nuxel}"
HOME_DIR="$(getent passwd "$USER_NAME" | cut -d: -f6)"
[ -n "$HOME_DIR" ] || { echo "nuxel-home-layout: no home for $USER_NAME" >&2; exit 1; }
GROUP_NAME="$(id -gn "$USER_NAME" 2>/dev/null || echo "$USER_NAME")"

for d in Desktop Gallery Config Documents Downloads Music Pictures Videos VoiceRecordings Templates Public; do
    path="$HOME_DIR/$d"
    if [ ! -e "$path" ]; then
        install -d -m 0755 -o "$USER_NAME" -g "$GROUP_NAME" "$path"
        echo "nuxel-home-layout: created $path"
    elif [ -d "$path" ]; then
        # Keep user content untouched; only fix a directory that is explicitly
        # owned by root and still has the standard 0755 group/world mode.
        owner="$(stat -c %U "$path" 2>/dev/null || echo '')"
        if [ "$owner" = "root" ]; then
            chown "$USER_NAME:$GROUP_NAME" "$path" 2>/dev/null || true
        fi
    fi
done

CONFIG_DIR="$HOME_DIR/.config"
if [ ! -e "$CONFIG_DIR/user-dirs.dirs" ]; then
    install -d -m 0700 -o "$USER_NAME" -g "$GROUP_NAME" "$CONFIG_DIR"
    cat > "$CONFIG_DIR/user-dirs.dirs" <<EOXDG
# Written once by Nuxel; edit freely, it is not rewritten.
XDG_DESKTOP_DIR="$HOME/Desktop"
XDG_DOWNLOAD_DIR="$HOME/Downloads"
XDG_TEMPLATES_DIR="$HOME/Templates"
XDG_PUBLICSHARE_DIR="$HOME/Public"
XDG_DOCUMENTS_DIR="$HOME/Documents"
XDG_MUSIC_DIR="$HOME/Music"
XDG_PICTURES_DIR="$HOME/Pictures"
XDG_VIDEOS_DIR="$HOME/Videos"
EOXDG
    chown "$USER_NAME:$GROUP_NAME" "$CONFIG_DIR/user-dirs.dirs"
    chmod 0644 "$CONFIG_DIR/user-dirs.dirs"
fi

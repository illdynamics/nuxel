#!/bin/sh
# Install the generated Nuxel cyan Xcursor theme and select it for the root
# phoc session.  Safe to re-run; phoc reloads cursor-theme via GSettings.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEST=${DEST:-/usr/share/icons/nuxel}
BUS=${BUS:-unix:path=/run/nuxel-wayland/bus}
python3 "$HERE/nuxel-cursor-theme.py" --dest "$DEST"
if command -v gsettings >/dev/null 2>&1; then
  DBUS_SESSION_BUS_ADDRESS="$BUS" XDG_RUNTIME_DIR=/run/nuxel-wayland \
    gsettings set org.gnome.desktop.interface cursor-theme nuxel 2>/dev/null || true
  DBUS_SESSION_BUS_ADDRESS="$BUS" XDG_RUNTIME_DIR=/run/nuxel-wayland \
    gsettings set org.gnome.desktop.interface cursor-size 32 2>/dev/null || true
  echo "cursor-theme=$(DBUS_SESSION_BUS_ADDRESS="$BUS" XDG_RUNTIME_DIR=/run/nuxel-wayland gsettings get org.gnome.desktop.interface cursor-theme 2>/dev/null || echo unknown)"
fi
echo "NUXEL_CURSORS_INSTALLED $DEST"

#!/bin/sh
# Install the Nuxel touch-first Doom launcher and route the installed Crispy
# Doom Flatpak entry through it.  Run as root on the handset.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "$(id -u)" != "0" ]; then
    exec sudo "$0" "$@"
fi

STAMP=$(date +%Y%m%dT%H%M%S)
BACKUP="/root/nuxel-doom-launcher-$STAMP"
mkdir -p "$BACKUP"
for path in \
    /usr/lib/nuxel/nuxel-flatpak-doom \
    /usr/lib/nuxel/nuxel-crispy-doom \
    /usr/lib/nuxel/nuxel-doom-launcher \
    /usr/share/applications/org.nuxel.DoomLauncher.desktop; do
    [ -e "$path" ] && cp -a "$path" "$BACKUP"/
done

install -o root -g root -m 0755 "$HERE/nuxel-doom-launcher" /usr/lib/nuxel/nuxel-doom-launcher
install -o root -g root -m 0755 "$HERE/nuxel-crispy-doom" /usr/lib/nuxel/nuxel-crispy-doom
install -o root -g root -m 0755 "$HERE/nuxel-flatpak-doom" /usr/lib/nuxel/nuxel-flatpak-doom
install -o root -g root -m 0644 "$HERE/org.nuxel.DoomLauncher.desktop" \
    /usr/share/applications/org.nuxel.DoomLauncher.desktop
ln -sfn /usr/lib/nuxel/nuxel-doom-launcher /usr/local/bin/nuxel-doom-launcher
ln -sfn /usr/lib/nuxel/nuxel-crispy-doom /usr/local/bin/nuxel-crispy-doom
python3 -m py_compile /usr/lib/nuxel/nuxel-doom-launcher

echo "Installed.  Backup: $BACKUP"
echo "Crispy Doom (io.github.fabiangreffrath.Doom) now opens the touch launcher."

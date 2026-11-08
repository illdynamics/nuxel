#!/bin/sh
# Build and install the phoc OSK re-show hook.  Run as root on the phone.
set -eu

SRC=/root/phoc-osk-reshow-src
BUILD=/root/phoc-osk-reshow-build
TARBALL=/root/phoc-v0.54.0.tar.gz
URL='https://gitlab.gnome.org/World/Phosh/phoc/-/archive/v0.54.0/phoc-v0.54.0.tar.gz'
PATCH_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ ! -f "$TARBALL" ]; then
  curl -L --fail -o "$TARBALL" "$URL"
fi
rm -rf "$SRC" "$BUILD"
mkdir -p "$SRC"
tar xzf "$TARBALL" -C "$SRC" --strip-components=1
patch -d "$SRC" -p1 < "$PATCH_DIR/phoc-osk-reshow.patch"

meson setup "$BUILD" "$SRC" \
  -Dembed-wlroots=disabled -Dxwayland=disabled \
  -Dtests=false -Dman=false -Dgtk_doc=false
ninja -C "$BUILD"

B=/var/backups/nuxel/phoc-osk-reshow-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$B"
cp -a /usr/sbin/phoc "$B/phoc.prev"
install -m755 "$BUILD/src/phoc" /usr/sbin/phoc
systemctl restart nuxel-wayland
echo "installed phoc; previous binary in $B"

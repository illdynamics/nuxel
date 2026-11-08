#!/bin/sh
# Build and install phoc with the opt-in zwp_text_input_v1 compatibility shim.
# Run as root on the phone.  The shim is controlled at runtime by
# /run/nuxel-text-input-v1.enabled (written by nuxel-keyboard-apply.sh), so no
# rebuild is needed to turn it on or off from Settings.
set -eu

SRC=/root/phoc-text-input-v1-src
BUILD=/root/phoc-text-input-v1-build
TARBALL=/root/phoc-v0.54.0.tar.gz
URL='https://gitlab.gnome.org/World/Phosh/phoc/-/archive/v0.54.0/phoc-v0.54.0.tar.gz'
PATCH_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ ! -f "$TARBALL" ]; then
  curl -L --fail -o "$TARBALL" "$URL"
fi

# Rebuild from a clean extraction so repeated runs never stack patches.
if [ -e "$SRC" ]; then
  find "$SRC" -mindepth 1 -delete
else
  mkdir -p "$SRC"
fi
tar xzf "$TARBALL" -C "$SRC" --strip-components=1
patch -d "$SRC" -p1 < "$PATCH_DIR/phoc-text-input-v1.patch"

if [ -e "$BUILD" ]; then
  find "$BUILD" -mindepth 1 -delete
fi
meson setup "$BUILD" "$SRC" \
  -Dembed-wlroots=disabled -Dxwayland=disabled \
  -Dtests=false -Dman=false -Dgtk_doc=false
ninja -C "$BUILD"

B=/var/backups/nuxel/phoc-text-input-v1-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$B"
for target in /usr/sbin/phoc /usr/bin/phoc; do
  if [ -e "$target" ]; then
    cp -a "$target" "$B/$(basename "$(dirname "$target")")-$(basename "$target").prev"
    install -m755 "$BUILD/src/phoc" "$target"
  fi
done
sha256sum "$BUILD/src/phoc" /usr/sbin/phoc
systemctl restart nuxel-wayland
echo "installed phoc + text-input-v1 shim; previous binaries in $B"

#!/bin/sh
# Build and install phoc with Nuxel's physical-keyboard-aware OSK policy.
#
# Base: phoc v0.54.0 + tools/s10plus/a76/phoc-text-input-v1.patch (the combined
# OSK re-show + zwp_text_input_v1 compatibility patch already running live).
# Delta: tools/s10plus/a77/phoc-input-auto-hide.patch:
#   * virtual/uinput keyboards (ydotoold, test devices) are not "hardware
#     keyboards" for Stevia's auto-hide decision;
#   * tapping an already-focused text field does not force the OSK back up
#     while a real keyboard is attached.
# Run as root on the phone.
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SRC=${SRC:-/root/phoc-input-auto-hide-src}
BUILD=${BUILD:-/root/phoc-input-auto-hide-build}
TARBALL=${TARBALL:-/root/phoc-v0.54.0.tar.gz}
URL=${URL:-https://gitlab.gnome.org/World/Phosh/phoc/-/archive/v0.54.0/phoc-v0.54.0.tar.gz}
BASE_PATCH=${BASE_PATCH:-$HERE/../a76/phoc-text-input-v1.patch}
DELTA_PATCH=$HERE/phoc-input-auto-hide.patch

[ -r "$BASE_PATCH" ] || { echo "missing base patch: $BASE_PATCH" >&2; exit 2; }
[ -r "$DELTA_PATCH" ] || { echo "missing delta patch: $DELTA_PATCH" >&2; exit 2; }

if [ ! -f "$TARBALL" ]; then
  curl -L --fail -o "$TARBALL" "$URL"
fi

if [ -e "$SRC" ]; then find "$SRC" -mindepth 1 -delete; else mkdir -p "$SRC"; fi
tar xzf "$TARBALL" -C "$SRC" --strip-components=1
patch -d "$SRC" -p1 < "$BASE_PATCH"
patch -d "$SRC" -p1 < "$DELTA_PATCH"

if [ -e "$BUILD" ]; then find "$BUILD" -mindepth 1 -delete; fi
meson setup "$BUILD" "$SRC" \
  -Dembed-wlroots=disabled -Dxwayland=disabled \
  -Dtests=false -Dman=false -Dgtk_doc=false
ninja -C "$BUILD"

B=/var/backups/nuxel/phoc-input-auto-hide-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$B"
for target in /usr/sbin/phoc /usr/bin/phoc; do
  if [ -e "$target" ]; then
    cp -a "$target" "$B/$(basename "$(dirname "$target")")-$(basename "$target").prev"
    install -m755 "$BUILD/src/phoc" "$target"
  fi
done
sha256sum "$BUILD/src/phoc" /usr/sbin/phoc
systemctl restart nuxel-wayland.service
echo "installed phoc with input auto-hide; previous binary in $B"

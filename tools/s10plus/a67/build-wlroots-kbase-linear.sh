#!/usr/bin/env bash
# Build wlroots 0.19.3 with the Nuxel kbase surfaceless + LINEAR-only
# linux-dmabuf patches.  Run ON THE PHONE (native aarch64) or in an
# aarch64 Fedora 43 container.
#
# Why: the renderer reports RGB formats with ARM tiled/SPARSE modifiers as
# well as LINEAR.  The kbase Wayland exporter physically allocates a linear
# udmabuf, so advertising the ARM modifiers makes Mesa tag a linear buffer
# with a tiled modifier; the compositor import then blocks/fails.  The
# PWNAGE-53000 fix advertises only (fourcc, LINEAR) pairs.
set -euo pipefail
ROOT="${ROOT:-/nuxel}"
WORK="${WORK:-/work/wlroots53000}"
OUT="${OUT:-/usr/local/lib/nuxel-gpu/wlroots53000}"
SRC="$WORK/wlroots"
# shellcheck source=gpu-build-pins.env
. "$ROOT/tools/s10plus/a67/gpu-build-pins.env"

dnf -y install meson ninja-build git wayland-devel wayland-protocols-devel \
  libinput-devel libseat-devel mesa-libEGL-devel mesa-libGLES-devel \
  mesa-libgbm-devel libdrm-devel libdisplay-info-devel libxkbcommon-devel \
  pixman-devel xcb-util-wm-devel xcb-util-renderutil-devel libxcb-devel \
  xorg-x11-server-Xwayland-devel hwdata >/dev/null
# Fedora ships pnp.ids without a pkg-config file; wlroots needs the variable.
[ -f /usr/share/pkgconfig/hwdata.pc ] || printf \
  'pkgdatadir=/usr/share/hwdata\nName: hwdata\nDescription: hardware identification databases\nVersion: 1\n' \
  > /usr/share/pkgconfig/hwdata.pc

mkdir -p "$WORK" "$OUT"
if [ ! -d "$SRC/.git" ]; then
  git clone "$WLROOTS_REPO" "$SRC"
fi
git -C "$SRC" fetch --tags --force origin
git -C "$SRC" checkout --detach "$WLROOTS_COMMIT"
test "$(git -C "$SRC" rev-parse HEAD)" = "$WLROOTS_COMMIT" || {
  echo "ERROR: wlroots HEAD is not the pinned commit $WLROOTS_COMMIT" >&2; exit 1; }
git -C "$SRC" reset --hard "$WLROOTS_COMMIT"
git -C "$SRC" clean -ffdx

# The linear patch is cumulative: it contains the surfaceless backend fix,
# the explicit v3 dmabuf global and the LINEAR-only filter.  It applies
# cleanly to a pristine wlroots 0.19.3 tree.
PATCH="$ROOT/$WLROOTS_PATCH"
git -C "$SRC" apply --check "$PATCH"
git -C "$SRC" apply "$PATCH"
echo "wlroots pinned: tag=$WLROOTS_TAG commit=$WLROOTS_COMMIT patch=$PATCH"

rm -rf "$SRC/build"
meson setup "$SRC/build" -Dbuildtype=release -Db_ndebug=true -Dwerror=false \
  -Drenderers=gles2 -Dbackends=drm,libinput -Dallocators=gbm,udmabuf \
  -Dsession=enabled -Dxwayland=enabled -Dexamples=false \
  -Dlibliftoff=disabled -Dcolor-management=disabled
ninja -C "$SRC/build" libwlroots-0.19.so
mkdir -p "$OUT"
cp -f "$SRC/build/libwlroots-0.19.so" "$OUT/libwlroots-0.19.so"
# The rootfs builder packages build/out/s10plus/kbase-gpu/lib.  Keep the
# linear build there when that staging tree exists, so a clean image build
# cannot silently ship the old surfaceless-only library.
PKG="${PKG_OUT:-$ROOT/build/out/s10plus/kbase-gpu/lib}"
if [ -d "$PKG" ]; then
  cp -f "$SRC/build/libwlroots-0.19.so" "$PKG/libwlroots-0.19.so"
  echo "packaged: $PKG/libwlroots-0.19.so"
fi
sha256sum "$OUT/libwlroots-0.19.so"

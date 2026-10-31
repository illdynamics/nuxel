#!/usr/bin/env bash
# Build wlroots 0.19.3 with the kbase-surfaceless patch for the S10+.
# Run INSIDE the podman build container (native aarch64):
#
#   podman exec nuxelbuild bash /nuxel/tools/s10plus/a67/build-wlroots-kbase.sh
#
# Produces /work/wlroots-out/libwlroots-0.19.so.
set -euo pipefail

ROOT="${ROOT:-/nuxel}"
WORK="${WORK:-/work/wlroots}"
OUT="${OUT:-/work/wlroots-out}"
SRC="$WORK/wlroots"
BUILD="$SRC/build"

mkdir -p "$WORK" "$OUT"
if [ ! -d "$SRC/.git" ]; then
  git clone --depth 1 --branch 0.19.3 \
    https://gitlab.freedesktop.org/wlroots/wlroots.git "$SRC"
fi

PATCH="$ROOT/tools/s10plus/a67/wlroots-kbase-surfaceless.patch"
if ! git -C "$SRC" apply --reverse --check "$PATCH" >/dev/null 2>&1; then
  git -C "$SRC" apply "$PATCH"
fi

dnf -y install meson ninja-build wayland-devel wayland-protocols-devel \
  pixman-devel libxkbcommon-devel libinput-devel libseat-devel \
  mesa-libEGL-devel mesa-libGLES-devel mesa-libgbm-devel libdrm-devel \
  libdisplay-info-devel xorg-x11-server-Xwayland-devel \
  libxcb-devel xcb-util-wm-devel xcb-util-renderutil-devel >/dev/null

if [ ! -f "$BUILD/build.ninja" ]; then
  meson setup "$BUILD" -Dbuildtype=release -Db_ndebug=true -Dwerror=false \
    -Drenderers=gles2 -Dbackends=drm,libinput -Dallocators=gbm,udmabuf \
    -Dsession=enabled -Dxwayland=enabled -Dexamples=false \
    -Dlibliftoff=disabled -Dcolor-management=disabled
fi

ninja -C "$BUILD" libwlroots-0.19.so
cp -f "$BUILD/libwlroots-0.19.so" "$OUT/libwlroots-0.19.so"
printf 'built: %s\n' "$OUT/libwlroots-0.19.so"

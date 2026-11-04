#!/usr/bin/env bash
# Build the experimental Wayland-WSI Mesa for kbase (PWNAGE-50000).
#
# This is NOT the default compositor library.  It adds:
#   * EGL_PLATFORM_WAYLAND on /dev/mali0 (no DRM render node required)
#   * exportable wl_buffers through sealed memfd + /dev/udmabuf
#   * kbase import of the exported dma-buf for rendering
#
# The main Phoc session must stay on the surfaceless build; enabling
# linux-dmabuf inside the live kbase compositor is not stable yet.
set -euo pipefail
ROOT="${ROOT:-/nuxel}"
WORK="${WORK:-/work/mesa-wayland}"
OUT="${OUT:-/work/mesa-wayland-out}"
REPO="${REPO:-$WORK/mesa-unified-drivers}"
BUILD="$REPO/build-wayland-wsi"
# shellcheck source=gpu-build-pins.env
. "$ROOT/tools/s10plus/a67/gpu-build-pins.env"

mkdir -p "$WORK" "$OUT"
if [ ! -d "$REPO/.git" ]; then
  git clone "$MESA_REPO" "$REPO"
fi
git -C "$REPO" fetch --tags --force origin
git -C "$REPO" checkout --detach "$MESA_COMMIT"
test "$(git -C "$REPO" rev-parse HEAD)" = "$MESA_COMMIT" || {
  echo "ERROR: Mesa HEAD is not the pinned commit $MESA_COMMIT" >&2; exit 1; }
git -C "$REPO" reset --hard "$MESA_COMMIT"
git -C "$REPO" clean -ffdx
PATCH="$ROOT/$MESA_PATCH"
git -C "$REPO" apply --check "$PATCH"
git -C "$REPO" apply "$PATCH"
echo "mesa pinned: $MESA_VERSION commit=$MESA_COMMIT patch=$PATCH"

dnf -y install meson ninja-build flex bison pkgconf-pkg-config \
  python3-mako python3-packaging python3-pyyaml llvm-devel clang clang-devel \
  libclc-devel spirv-llvm-translator-devel spirv-tools-devel spirv-headers-devel \
  libglvnd-devel zlib-devel expat-devel libdrm-devel wayland-devel \
  wayland-protocols-devel vulkan-headers patchelf >/dev/null

if [ ! -f "$BUILD/build.ninja" ]; then
  meson setup "$BUILD" \
    -Dbuildtype=release -Db_ndebug=true -Dwerror=false \
    -Dplatforms=wayland -Dgallium-drivers=panfrost -Dvulkan-drivers= \
    -Degl=enabled -Dgles1=disabled -Dgles2=enabled -Dglx=disabled -Dgbm=disabled \
    -Dllvm=enabled -Dmesa-clc=enabled -Dprecomp-compiler=enabled \
    -Dglvnd=enabled -Degl-lib-suffix= -Dgles-lib-suffix=_mesa \
    -Dunversion-libgallium=true -Dvideo-codecs= -Dtools= \
    -Dzstd=disabled -Dlmsensors=disabled \
    -Dallow-fallback-for=libdrm --force-fallback-for=libdrm \
    -Dlibdrm:default_library=static
fi

ninja -C "$BUILD" src/egl/libEGL_mesa.so.0.0.0 \
  src/gallium/targets/dri/libgallium_dri.so
cp -f "$BUILD/src/egl/libEGL_mesa.so.0.0.0" "$OUT/libEGL_mesa.so.0.0.0"
cp -f "$BUILD/src/gallium/targets/dri/libgallium_dri.so" "$OUT/libgallium_dri.so"
patchelf --set-rpath '$ORIGIN' "$OUT/libEGL_mesa.so.0.0.0"
printf 'built experimental Wayland WSI: %s\n' "$OUT"

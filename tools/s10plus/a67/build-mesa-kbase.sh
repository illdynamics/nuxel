#!/usr/bin/env bash
# Build Mesa panfrost-on-kbase for the S10+ (aarch64 glibc, Fedora 43).
# Run INSIDE the podman build container (native aarch64):
#
#   podman exec nuxelbuild bash /nuxel/tools/s10plus/a67/build-mesa-kbase.sh
#
# Produces /work/mesa-out/{libEGL_mesa.so.0.0.0,libgallium_dri.so,50_mesa.json}.
set -euo pipefail

ROOT="${ROOT:-/nuxel}"
WORK="${WORK:-/work/mesa}"
OUT="${OUT:-/work/mesa-out}"
REPO="${REPO:-$WORK/mesa-unified-drivers}"
BUILD="$REPO/build-linux"

mkdir -p "$WORK" "$OUT"
if [ ! -d "$REPO/.git" ]; then
  git clone --depth 1 https://github.com/JimVulkan/mesa-unified-drivers.git "$REPO"
fi

# Build dependencies (Fedora 43 aarch64).
dnf -y install meson ninja-build flex bison pkgconf-pkg-config \
  python3-mako python3-packaging python3-pyyaml \
  llvm-devel clang clang-devel libclc-devel spirv-llvm-translator-devel \
  spirv-tools-devel spirv-headers-devel libglvnd-devel zlib-devel expat-devel \
  libdrm-devel wayland-devel wayland-protocols-devel >/dev/null

if [ ! -f "$BUILD/build.ninja" ]; then
  meson setup "$BUILD" \
    -Dbuildtype=release -Db_ndebug=true -Dwerror=false \
    -Dplatforms= -Dgallium-drivers=panfrost -Dvulkan-drivers= \
    -Degl=enabled -Dgles1=disabled -Dgles2=enabled \
    -Dglx=disabled -Dgbm=disabled -Dllvm=enabled \
    -Dmesa-clc=enabled -Dprecomp-compiler=enabled \
    -Dglvnd=enabled -Degl-lib-suffix= -Dgles-lib-suffix=_mesa \
    -Dunversion-libgallium=true -Dvideo-codecs= -Dtools= \
    -Dzstd=disabled -Dlmsensors=disabled \
    -Dallow-fallback-for=libdrm --force-fallback-for=libdrm \
    -Dlibdrm:default_library=static
fi

ninja -C "$BUILD" \
  src/egl/libEGL_mesa.so.0.0.0 \
  src/gallium/targets/dri/libgallium_dri.so

# Install layout: libEGL_mesa finds libgallium_dri via $ORIGIN on the phone.
cp -f "$BUILD/src/egl/libEGL_mesa.so.0.0.0" "$OUT/libEGL_mesa.so.0.0.0"
patchelf --set-rpath '$ORIGIN' "$OUT/libEGL_mesa.so.0.0.0"
cp -f "$BUILD/src/gallium/targets/dri/libgallium_dri.so" "$OUT/libgallium_dri.so"
cp -f "$BUILD/src/egl/50_mesa.json" "$OUT/50_mesa.json"
printf 'built: %s\n' "$OUT/libEGL_mesa.so.0.0.0 $OUT/libgallium_dri.so $OUT/50_mesa.json"

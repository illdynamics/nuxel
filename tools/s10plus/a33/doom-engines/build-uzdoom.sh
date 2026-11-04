#!/usr/bin/env bash
# Build the native aarch64 UZDoom comparison engine from pinned source.
#
#   tools/s10plus/a33/doom-engines/build-uzdoom.sh [--install]
#
# UZDoom does not publish a Linux arm64 AppImage.  This script builds 5.0.3
# from source on the phone (or any Fedora 43 aarch64 box) with the software
# renderer available for the S10+ vendor kernel, which has no /dev/dri node.
# It never flashes, never touches a partition, and only installs when
# --install is passed.
set -euo pipefail

VERSION="5.0.3"
COMMIT="7910df7102033fd7754a317f3254f24101135926"
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
SRC="${UZDOOM_SRC:-$HOME/uzdoom-src}"
PREFIX="${UZDOOM_PREFIX:-/usr/lib/nuxel/uzdoom}"
JOBS="${UZDOOM_JOBS:-$(nproc 2>/dev/null || echo 4)}"
DO_INSTALL=0
[ "${1:-}" = "--install" ] && DO_INSTALL=1

if [ ! -f "$SRC/CMakeLists.txt" ]; then
  command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
  git clone --branch "$VERSION" --depth 1 https://github.com/UZDoom/UZDoom.git "$SRC"
fi
[ "$(git -C "$SRC" rev-parse HEAD 2>/dev/null || true)" = "$COMMIT" ] || {
  echo "WARNING: $SRC is not the pinned UZDoom $VERSION commit $COMMIT" >&2
}

# Fedora 43 aarch64 build dependencies.  Keep this explicit so the source is
# reproducible and no x86 AppImage or unknown prebuilt binary is introduced.
if command -v dnf >/dev/null; then
  sudo -n dnf -y install \
    cmake gcc-c++ SDL2-devel openal-soft-devel zlib-devel bzip2-devel \
    libjpeg-turbo-devel libvpx-devel libwebp-devel libX11-devel \
    libXrandr-devel libXi-devel libXcursor-devel libXinerama-devel \
    mesa-libGL-devel mesa-libGLU-devel gtk3-devel pulseaudio-libs-devel \
    alsa-lib-devel libsndfile-devel >/dev/null
fi

cmake -S "$SRC" -B "$SRC/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_NONFREE=OFF \
  -DUSE_UPDATER=OFF \
  -DFORCE_NO_LTO=ON \
  -DNO_OPENAL=OFF
cmake --build "$SRC/build" -j"$JOBS"

echo "UZDoom binary: $SRC/build/uzdoom"
if [ "$DO_INSTALL" = 1 ]; then
  sudo install -d -m 0755 "$PREFIX"
  sudo cmake --install "$SRC/build" --prefix "$PREFIX"
  # UZDoom resolves its own pk3 relative to the executable on this build.
  find "$PREFIX" -maxdepth 4 -name '*.pk3' -print
  echo "Installed under $PREFIX"
fi

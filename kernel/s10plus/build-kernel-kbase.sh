#!/usr/bin/env bash
# Build the S10+ kernel with DRM core, kbase/UDMABUF GPU sharing, and the
# proven DPU20 fbdev panel path.
#
# Usage:
#   NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel-kbase.sh [--clone] [--clean]
#
# This is the same build as kernel/s10plus/build-kernel.sh plus the
# configs/nuxel-drm-kbase.fragment override and the UDMABUF backport patch.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEVICE=s10plus
KSRC="$ROOT/kernel/$DEVICE/.build/src"
KOUT="$ROOT/kernel/$DEVICE/.build/out"
DEFCONFIG=exynos9820-beyond2lte_defconfig
FRAG="$ROOT/kernel/$DEVICE/configs/nuxel-drm-kbase.fragment"
JOBS="${JOBS:-$( (command -v nproc >/dev/null && nproc) || echo 4)}"
CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}"
DO_CLONE=0
DO_CLEAN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --clone) DO_CLONE=1; shift ;;
    --clean) DO_CLEAN=1; shift ;;
    --jobs) JOBS="$2"; shift 2 ;;
    --cross) CROSS_COMPILE="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ $DO_CLEAN -eq 1 ]] && rm -rf "$KOUT"
mkdir -p "$KOUT" "$KSRC"

if [[ $DO_CLONE -eq 1 || ! -d "$KSRC/.git" ]]; then
  if [ ! -f "$KSRC/Makefile" ]; then
    git clone --filter=blob:none --no-checkout \
      https://github.com/Linux4/android_kernel_samsung_exynos9820 "$KSRC"
  fi
  git -C "$KSRC" checkout f7194c1d15eded1c2a1a4dc63825b26103435cc0
fi

# Apply the repo's kernel patches, including 0005-udmabuf.
shopt -s nullglob
for patch in "$ROOT/kernel/$DEVICE/patches"/*.patch; do
  grep -qE '^# STUB([[:space:]]|$)' "$patch" && continue
  if git -C "$KSRC" apply --reverse --check "$patch" >/dev/null 2>&1; then
    echo "[kernel] already applied: $(basename "$patch")"
  elif git -C "$KSRC" apply --check "$patch" >/dev/null 2>&1; then
    git -C "$KSRC" apply "$patch"
    echo "[kernel] applied: $(basename "$patch")"
  else
    echo "[kernel] ERROR: patch does not apply: $(basename "$patch")" >&2
    exit 1
  fi
done
shopt -u nullglob

bash "$ROOT/tools/kernel-relax-werror.sh" "$KSRC"

make -C "$KSRC" O="$KOUT" ARCH=arm64 CROSS_COMPILE= "$DEFCONFIG"

while IFS= read -r line; do
  case "$line" in ''|'#'*) continue;; esac
  key=${line%%=*}; val=${line#*=}
  if [ "$val" = n ]; then
    if grep -q "^${key}=" "$KOUT/.config"; then
      sed -i "s|^${key}=.*|# ${key} is not set|" "$KOUT/.config"
    elif ! grep -q "^# ${key} is not set" "$KOUT/.config"; then
      printf '# %s is not set\n' "$key" >> "$KOUT/.config"
    fi
  elif grep -q "^${key}=" "$KOUT/.config"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$KOUT/.config"
  elif grep -q "^# ${key} is not set" "$KOUT/.config"; then
    sed -i "s|^# ${key} is not set|${key}=${val}|" "$KOUT/.config"
  else
    printf '%s=%s\n' "$key" "$val" >> "$KOUT/.config"
  fi
done < "$FRAG"

make -C "$KSRC" O="$KOUT" ARCH=arm64 CROSS_COMPILE= olddefconfig
grep -q '^CONFIG_DRM=y' "$KOUT/.config"
grep -q '^# CONFIG_DRM_EXYNOS is not set' "$KOUT/.config"
grep -q '^CONFIG_UDMABUF=y' "$KOUT/.config"
grep -q '^CONFIG_MALI_BIFROST_R26P0=y' "$KOUT/.config"

make -C "$KSRC" O="$KOUT" ARCH=arm64 CROSS_COMPILE= -j"$JOBS" Image.gz dtbs
echo "[kernel] done: $KOUT/arch/arm64/boot/Image.gz"

#!/usr/bin/env bash
# =============================================================================
# Thin per-device wrapper: kernel/google-pixel-10-pro-xl/build-kernel.sh
#
# Pins the device key to mustang and forwards every argument to the shared
# kernel build dispatcher kernel/build-kernel.sh. Keeps the per-device path
# referenced by kernel/google-pixel-10-pro-xl/README-toolchain.md working and
# makes the device explicit so no environment is required.
#
# The dispatcher resolves the device via --device/NUXEL_DEVICE (the shared
# selector never guesses) and refuses non-mustang devices; this wrapper makes
# mustang explicit.
#
# Real mustang kernel (Tensor G5 / gs501) needs the PRIVATE vendor tree
# android-gs-mustang-6.12. Without it the dispatcher falls back to the public
# GKI android16-6.12 scaffold, which is NOT bootable on mustang hardware.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# shellcheck disable=SC2310
exec bash "${ROOT}/kernel/build-kernel.sh" --device mustang "$@"

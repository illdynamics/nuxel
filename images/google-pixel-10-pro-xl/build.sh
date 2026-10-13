#!/usr/bin/env bash
# =============================================================================
# Thin per-device wrapper: images/google-pixel-10-pro-xl/build.sh
#
# Forwards every argument to the shared device dispatcher images/build.sh with
# the device key pinned to mustang. Keeps mustang-specific documentation and
# any legacy references to this path working unchanged.
#
# The dispatcher resolves the device via --device/NUXEL_DEVICE (the shared
# selector never guesses) and refuses non-mustang devices; this wrapper makes
# the device explicit so no environment is required.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# shellcheck disable=SC2310
exec bash "${ROOT}/images/build.sh" --device mustang "$@"

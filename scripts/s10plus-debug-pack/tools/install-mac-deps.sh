#!/usr/bin/env bash
set -euo pipefail
[ "$(uname -s)" = Darwin ] || { echo 'This installer targets macOS. No changes made.' >&2; exit 2; }
cat <<'PLAN'
Nuxel S10+ macOS diagnostics dependencies:
  Homebrew Android Platform Tools (adb)          required for TWRP capture
  Homebrew e2fsprogs (debugfs, e2fsck)           required for offline ext4 inspection
  Homebrew dtc (fdtget, dtc, fdtoverlay)         recommended for DTB inspection
  Homebrew lz4 / zstd / libusb                   optional analysis utilities

This installer NEVER flashes or writes to the Samsung.
By default it only previews commands. Pass --apply to install.
PLAN
if [ "${1:-}" != --apply ]; then
  cat <<'CMDS'
Preview commands:
  brew install --cask android-platform-tools
  brew install e2fsprogs dtc lz4 zstd libusb
CMDS
  exit 0
fi
command -v brew >/dev/null 2>&1 || { echo 'Homebrew missing: https://brew.sh' >&2; exit 1; }
brew install --cask android-platform-tools || { command -v adb >/dev/null 2>&1 || exit 1; }
brew install e2fsprogs dtc lz4 zstd libusb
printf 'Installed. Run: bash tools/doctor.sh\n'

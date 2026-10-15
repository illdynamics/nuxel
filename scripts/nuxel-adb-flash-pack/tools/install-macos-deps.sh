#!/usr/bin/env bash
set -euo pipefail
if [[ "$(uname -s)" != Darwin ]]; then
 echo 'This installer targets macOS. On Linux install Android platform-tools and Python >=3.9.' >&2
 exit 2
fi
if [[ "${1:-}" != '--apply' ]]; then
  echo 'DRY RUN: would run: brew install android-platform-tools python'
  echo 'Optional file inspectors: brew install e2fsprogs dtc'
  echo 'Run: bash tools/install-macos-deps.sh --apply to install'
  exit 0
fi
command -v brew >/dev/null || { echo 'Homebrew required: https://brew.sh/' >&2; exit 2; }
brew install android-platform-tools python
printf 'Optional: brew install e2fsprogs dtc\n'

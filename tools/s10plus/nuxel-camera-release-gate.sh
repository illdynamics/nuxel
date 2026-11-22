#!/usr/bin/env bash
# Fail-closed wrapper. See tools/s10plus/camera-release-gate.py --help.
# REQUIRES signed Prompt00 evidence and an explicit offline merged candidate.
# This script never performs a partition write, reboot or flash.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "$ROOT/tools/s10plus/camera-release-gate.py" "$@"

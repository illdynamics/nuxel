#!/usr/bin/env bash
# nuxel-live-ssh.sh — Nuxel Tri-Link console launcher (NUXEL-26000).
#
#   nuxel-live-ssh.sh --transport auto --discover
#   nuxel-live-ssh.sh --transport wlan --shell
#   nuxel-live-ssh.sh --transport wlan --exec 'id; exit 7'; echo $?   # 7
#   nuxel-live-ssh.sh --transport usb --diagnose
#   nuxel-live-ssh.sh --transport serial --run 'uname -a'
#
# Serial is delegated unchanged to ./nuxel-live.sh.  This wrapper never opens
# /dev/ttyACM* itself and never falls back from SSH to serial silently.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PY="${PY:-python3}"
exec "$PY" "$ROOT/tools/beta/live/nuxel-live-ssh.py" "$@"

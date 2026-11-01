#!/usr/bin/env bash
# nuxel-gui-tunnel.sh — pinned-key SSH local forwards for Jump Desktop.
#
# Opens 127.0.0.1:15900 -> phone 127.0.0.1:5900 (VNC) and
#        127.0.0.1:13389 -> phone 127.0.0.1:3389 (XRDP).
# The server listeners stay loopback-only; this tunnel is the authenticated,
# encrypted transport. Host key checking is strict and uses the Nuxel pin.
#
# Usage:
#   scripts/nuxel-gui-tunnel.sh [--host IP] [--user nuxel] [--key PATH] [--background]
#   scripts/nuxel-gui-tunnel.sh --stop
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST=""; USER_NAME="nuxel"; KEY="${HOME}/.ssh/wicked_wqn_id_rsa"
KNOWN="$ROOT/configs/nuxel/security/ssh/known_hosts"
BACKGROUND=0; STOP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --user) USER_NAME="$2"; shift 2 ;;
    --key) KEY="$2"; shift 2 ;;
    --background) BACKGROUND=1; shift ;;
    --stop) STOP=1; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
if [ "$STOP" = 1 ]; then
  pkill -f '15900:127.0.0.1:5900' 2>/dev/null || true
  echo "tunnel stopped (if it was running)"
  exit 0
fi
[ -n "$HOST" ] || { echo "ERROR: --host is required (use the current Wi-Fi address from the Nuxel VNC/XRDP app)" >&2; exit 2; }
[ -r "$KEY" ] || { echo "ERROR: SSH key not readable: $KEY" >&2; exit 2; }
[ -r "$KNOWN" ] || { echo "ERROR: pinned known_hosts missing: $KNOWN" >&2; exit 2; }
# Add a host-specific pin with the same key (never disable host checking).
PIN="$(mktemp "${TMPDIR:-/tmp}/nuxel-pin.XXXXXX")"
trap 'rm -f "$PIN"' EXIT
awk -v h="$HOST" '$1=="nuxel-s10plus"{print h" "$2" "$3}' "$KNOWN" > "$PIN"
[ -s "$PIN" ] || { echo "ERROR: no nuxel-s10plus pin in $KNOWN" >&2; exit 2; }
OPTS=(-N -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes
      -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$PIN"
      -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3
      -L 15900:127.0.0.1:5900 -L 13389:127.0.0.1:3389)
if [ "$BACKGROUND" = 1 ]; then
  ssh -f "${OPTS[@]}" "$USER_NAME@$HOST"
  echo "TUNNEL_READY vnc=127.0.0.1:15900 rdp=127.0.0.1:13389 host=$HOST"
else
  echo "TUNNEL_READY (foreground; Ctrl-C to stop) vnc=127.0.0.1:15900 rdp=127.0.0.1:13389"
  exec ssh "${OPTS[@]}" "$USER_NAME@$HOST"
fi

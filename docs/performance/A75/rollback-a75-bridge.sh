#!/bin/sh
# A75 bridge rollback helper — restore pre-A75 files and restart services.
# Usage from the host:  bash docs/performance/A75/rollback-a75-bridge.sh
# Set NUXEL_DEV=/dev/cu.usbmodemNNNN if the default node is wrong.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
LIVE="$ROOT/scripts/s10plus-debug-pack/nuxel-live.sh"
[ -x "$LIVE" ] || { echo "missing $LIVE" >&2; exit 1; }
DEVARG=""; [ -n "${NUXEL_DEV:-}" ] && DEVARG="--dev $NUXEL_DEV"
CMD='for pair in /usr/lib/nuxel/nuxel-bridge/bridge.py /usr/lib/nuxel/nuxel-bridge/api.py /etc/systemd/system/nuxel-bridge.service /etc/systemd/system/nuxel-http-bridge.service /etc/nuxel/bridge-version.json /usr/share/nuxel/pwa/nuxel-common/bridge-version.json /usr/share/nuxel/pwa/nuxel-common/bridge.js; do if [ -e "$pair.nuxel-rollback" ]; then cp -a "$pair.nuxel-rollback" "$pair" && echo "restored $pair"; else echo "NO-ROLLBACK $pair"; fi; done; systemctl daemon-reload; systemctl restart nuxel-bridge.service nuxel-http-bridge.service; echo A75-ROLLBACK-DONE'
exec "$LIVE" $DEVARG --run "$CMD"

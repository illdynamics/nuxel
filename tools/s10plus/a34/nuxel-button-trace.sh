#!/bin/sh
# nuxel-button-trace — bounded, read-only key/MT trace through the deployed
# button manager plus the journal actions it actually dispatched.
#
#   nuxel-button-trace.sh [SECONDS]
#
# The manager opens /dev/input/eventN read-only (no EVIOCGRAB), so this can run
# while Phoc keeps receiving the same contact stream.  It is evidence for the
# KEY_POWER / KEY_BIXBY / touch classification question, nothing else.
set -u
SECS="${1:-15}"
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
if [ -x /usr/lib/nuxel/nuxel-button-manager ]; then
  timeout "$SECS" /usr/lib/nuxel/nuxel-button-manager --capture "$SECS" 2>&1
fi
journalctl -u nuxel-button-manager --since "-${SECS}s" --no-pager 2>/dev/null | tail -80

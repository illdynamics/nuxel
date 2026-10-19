#!/bin/sh
# ExecCondition helper for nuxel-fallback.service.
#   wait up to N seconds for /run/nuxel-launcher-ready (written by nuxel-pwa-host
#   when the launcher page finished loading).
#   exit 0  -> the launcher did NOT become ready: systemd runs the fallback UI.
#   exit 1  -> the launcher is up: systemd skips the fallback, so the two never
#              fight over /dev/fb0.
SECS="${1:-60}"
i=0
while [ "$i" -lt "$SECS" ]; do
  [ -f /run/nuxel-launcher-ready ] && exit 1
  i=$((i + 1)); sleep 1
done
exit 0

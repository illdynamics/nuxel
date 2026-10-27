#!/bin/sh
# coalesced transaction-level activation plan
# daemon-reload: 1, reloads: 3, restarts: 1
( systemctl daemon-reload )
( python3 -c "import json;json.load(open('/usr/share/nuxel/pwa/nuxel-common/app-registry.json'))" && test -s /usr/share/nuxel/pwa/nuxel-apps/console/console.js && test -s /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js )
( test -x /usr/local/bin/nuxel-typec-diag.sh && test -x /usr/local/bin/nuxel-cast-diag.sh )
( systemctl restart nuxel-bridge nuxel-http-bridge )
systemctl restart nuxel-wayland.service && systemctl is-active nuxel-wayland.service

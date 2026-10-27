#!/bin/sh
# coalesced transaction-level activation plan
# daemon-reload: 0, reloads: 1, restarts: 2
( python3 -c "import json;json.load(open('/usr/share/nuxel/pwa/nuxel-apps/settings/app.json'))" && test -s /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js )
systemctl restart nuxel-http-bridge.service && systemctl is-active nuxel-http-bridge.service
systemctl restart nuxel-bridge.service && systemctl is-active nuxel-bridge.service

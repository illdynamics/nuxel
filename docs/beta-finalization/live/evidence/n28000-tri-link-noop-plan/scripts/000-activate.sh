#!/bin/sh
# coalesced transaction-level activation plan
# daemon-reload: 0, reloads: 1, restarts: 2
( python3 -c "import json;json.load(open('/usr/share/nuxel/pwa/nuxel-common/app-registry.json'))" )
systemctl restart nuxel-wayland.service && systemctl is-active nuxel-wayland.service
systemctl restart nuxel-http-bridge.service && systemctl is-active nuxel-http-bridge.service

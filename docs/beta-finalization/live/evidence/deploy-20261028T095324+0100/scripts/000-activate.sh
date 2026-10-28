#!/bin/sh
# coalesced transaction-level activation plan
# daemon-reload: 1, reloads: 2, restarts: 2
( systemctl daemon-reload )
( true )
( systemctl restart nuxel-bridge.service nuxel-http-bridge.service nuxel-web.service && systemctl is-active nuxel-bridge.service nuxel-http-bridge.service nuxel-web.service )
systemctl restart nuxel-wayland.service && systemctl is-active nuxel-wayland.service
systemctl restart nuxel-wl-fb.service && systemctl is-active nuxel-wl-fb.service

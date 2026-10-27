#!/bin/sh
# coalesced transaction-level activation plan
# daemon-reload: 0, reloads: 0, restarts: 2
systemctl restart nuxel-web.service && systemctl is-active nuxel-web.service
systemctl restart nuxel-http-bridge.service && systemctl is-active nuxel-http-bridge.service

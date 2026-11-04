#!/bin/sh
# coalesced transaction-level activation plan
# daemon-reload: 0, reloads: 0, restarts: 1
systemctl restart nuxel-http-bridge.service && systemctl is-active nuxel-http-bridge.service

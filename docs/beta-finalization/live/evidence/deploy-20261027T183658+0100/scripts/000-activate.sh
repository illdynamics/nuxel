#!/bin/sh
# coalesced transaction-level activation plan
# daemon-reload: 0, reloads: 0, restarts: 3
systemctl restart nuxel-http-bridge.service && systemctl is-active nuxel-http-bridge.service
systemctl restart nuxel-notifications.service && systemctl is-active nuxel-notifications.service
systemctl restart nuxel-portal.service && systemctl is-active nuxel-portal.service

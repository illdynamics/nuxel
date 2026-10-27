#!/bin/sh
# coalesced transaction-level activation plan
# daemon-reload: 1, reloads: 1, restarts: 1
( systemctl daemon-reload )
( systemctl restart nuxel-bridge nuxel-http-bridge nuxel-notifications nuxel-portal )
systemctl restart nuxel-web.service && systemctl is-active nuxel-web.service

#!/bin/sh
# coalesced transaction-level activation plan
# daemon-reload: 0, reloads: 1, restarts: 1
( true )
systemctl restart nuxel-wayland.service && systemctl is-active nuxel-wayland.service

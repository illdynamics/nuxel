#!/bin/sh
# coalesced transaction-level activation plan
# daemon-reload: 1, reloads: 1, restarts: 0
( systemctl daemon-reload )
( systemctl enable nuxel-preload-cinema.service )

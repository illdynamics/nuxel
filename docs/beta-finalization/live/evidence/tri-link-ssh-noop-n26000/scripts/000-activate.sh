#!/bin/sh
# coalesced transaction-level activation plan
# daemon-reload: 0, reloads: 0, restarts: 1
systemctl restart sshd.service && systemctl is-active sshd.service

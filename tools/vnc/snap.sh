#!/bin/bash
set -e
H="-i $HOME/.ssh/wicked_wqn_id_rsa root@192.168.178.167"
ssh $H 'export XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0; grim -t png /tmp/ui-snap.png' >/dev/null 2>&1
scp -q -i $HOME/.ssh/wicked_wqn_id_rsa root@192.168.178.167:/tmp/ui-snap.png "${1:-/tmp/ui-snap.png}"

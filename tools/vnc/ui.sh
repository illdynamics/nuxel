#!/bin/bash
# Thin wrapper: run a command on the phone with the session environment.
ssh -i "$HOME/.ssh/wicked_wqn_id_rsa" root@192.168.178.167 \
  "export XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 YDOTOOL_SOCKET=/tmp/.ydotool_socket DBUS_SESSION_BUS_ADDRESS=unix:path=/run/nuxel-wayland/bus; $*" 2>/dev/null \
  | sed '/█\|╗\|╝\|║\|╔\|╚\|══\|_\/\|(|\|o_o\|\\___)=\|Mobile Linux\|^$/d'

#!/bin/bash
# swipe.sh X0 Y0 X1 Y1 [steps]  — press, interpolate, release via ydotool.
X0=$1; Y0=$2; X1=$3; Y1=$4; N=${5:-14}
cmd="ydotool mousemove -a $X0 $Y0; ydotool click 0x40"
for i in $(seq 1 $N); do
  X=$(( X0 + (X1-X0)*i/N )); Y=$(( Y0 + (Y1-Y0)*i/N ))
  cmd="$cmd; ydotool mousemove -a $X $Y; sleep 0.04"
done
cmd="$cmd; ydotool click 0x00"
ssh -i "$HOME/.ssh/wicked_wqn_id_rsa" root@192.168.178.167 \
  "export XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 YDOTOOL_SOCKET=/tmp/.ydotool_socket; $cmd" >/dev/null 2>&1

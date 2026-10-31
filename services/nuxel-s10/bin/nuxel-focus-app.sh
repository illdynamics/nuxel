#!/bin/sh
# Wait for a just-launched native toplevel, then raise it above the fullscreen
# Home surface and keep the layer-shell top bar / nav dock visible.  The bridge
# starts this after a successful native launch; it never kills anything.
set -u
APP="${1:-}"
[ -n "$APP" ] || exit 2
export XDG_RUNTIME_DIR=/run/nuxel-wayland
export WAYLAND_DISPLAY=wayland-0
FT=/usr/lib/nuxel/nuxel-foreign-toplevel
i=0
while [ "$i" -lt 40 ]; do
  if "$FT" list 2>/dev/null | grep -q "app_id=$APP"; then
    "$FT" focus "$APP" >/dev/null 2>&1
    exit 0
  fi
  i=$((i + 1))
  sleep 0.25
done
exit 1

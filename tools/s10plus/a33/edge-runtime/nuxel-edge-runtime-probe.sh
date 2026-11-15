#!/bin/sh
# Run the EDGE runtime DOM probe inside the existing headless Wayland session.
# Read-only: no window is mapped for the owner, no setting/LED is touched.
exec env GDK_BACKEND=wayland \
  WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}" \
  XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/nuxel-wayland}" \
  python3 /usr/local/bin/nuxel-edge-runtime-probe.py "$@"

#!/bin/sh
# nuxel-display-frame-trace — sample the live presentation counter and (when
# available) the compositor frame hash.  Read-only: it never opens /dev/fb0.
#
#   nuxel-display-frame-trace.sh [--seconds N]
#
# FRAMES_OK is published by nuxel-wl-fb once per second.  A frozen glass while
# `total` still advances means the compositor is producing frames but the
# client is not changing; a frozen `total` means presentation itself stopped.
set -u
SECS=4
[ "${1:-}" = "--seconds" ] && SECS="${2:-4}"
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
read_total() {
  sed -n 's/^[0-9][0-9]* FRAMES_OK total=\([0-9][0-9]*\).*/\1/p' /run/nuxel-wl-fb.state 2>/dev/null
}
read_all() { cat /run/nuxel-wl-fb.state 2>/dev/null; }
printf '{"ts":"%s","kind":"frame","name":"start","value":"%s"}\n' "$(now)" "$(tr '\n' ';' </run/nuxel-wl-fb.state 2>/dev/null | tr -d '"')"
a=$(read_total); sleep "$SECS"; b=$(read_total)
if [ -n "$a" ] && [ -n "$b" ]; then
  printf '{"ts":"%s","kind":"frame","name":"delta","value":"total_before=%s total_after=%s delta=%s seconds=%s fps=%.2f"}\n' \
    "$(now)" "$a" "$b" "$((b-a))" "$SECS" "$(awk -v d="$((b-a))" -v s="$SECS" 'BEGIN{printf "%.2f", d/s}')"
else
  printf '{"ts":"%s","kind":"frame","name":"delta","value":"counter-missing"}\n' "$(now)"
fi
printf '{"ts":"%s","kind":"display","name":"state","value":"%s"}\n' "$(now)" "$(tr '\n' ';' </var/lib/nuxel/display 2>/dev/null)"
if command -v nuxel-wl-snapshot >/dev/null 2>&1; then
  tmp=/tmp/nuxel-frame-trace.$$.ppm
  XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 nuxel-wl-snapshot "$tmp" 2>&1 | while read -r l; do
    case "$l" in SNAPSHOT_OK*) printf '{"ts":"%s","kind":"frame","name":"snapshot","value":"%s"}\n' "$(now)" "$l";; esac
  done
  rm -f "$tmp"
fi

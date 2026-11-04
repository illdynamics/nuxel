#!/bin/sh
# Keep the last valid panel frame visible for a short, bounded interval when
# the owner requested a reboot.  This is an ExecStop for nuxel-wl-fb only; it
# never becomes a second framebuffer writer and never waits for an animation.
set -u
if [ -e /run/nuxel/reboot-request ]; then
  # The compositor stops in parallel; 2 s covers the measured userspace stop
  # window and leaves the last frame on the panel instead of a black dwell.
  sleep 2
fi
exit 0

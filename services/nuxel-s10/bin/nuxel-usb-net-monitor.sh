#!/usr/bin/env bash
# Nuxel USB network link monitor (thin shim).
#
# The physical-detach policy now lives in the single gadget owner
# (/usr/lib/nuxel/nuxel-usb-mode.sh monitor), together with the transition
# lock and journal.  A second detach algorithm is exactly how two owners drift
# apart, so this unit simply runs the owner's monitor loop.
#
# A77 model (implemented in the owner): UDC "configured" and Type-C data_role
# both stay stale after a cable pull; UDC current_speed=UNKNOWN and wired VBUS
# offline are the measured detach signals.  DWC3 link_state debugfs is never
# read (A74: hard lockup/watchdog reboot on that register read).
set -uo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
exec /usr/lib/nuxel/nuxel-usb-mode.sh monitor

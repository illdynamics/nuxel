#!/bin/sh
# Nuxel USB-network bring-up (owner SSH over the plugged-in USB cable).
#
# The S10+ live kernel has CONFIG_USB_CONFIGFS_ECM=y.  ECM is the safe,
# teardown-clean CDC data plane (the NCM function is the one with the recorded
# 4.14 teardown panic and is NEVER used here).  This script adds an ECM
# function next to the ACM live console, re-binds the UDC once, and gives the
# phone end of the link 10.15.19.1/24 (the Mac reaches it with 10.15.19.2/24,
# see scripts/s10plus-debug-pack/nuxel-usb-net-host.sh).
#
# It is idempotent: re-running with the function already present only makes
# sure the link is up and addressed.  It never removes the ACM console and
# never tears down ECM (no rmdir of a live function), so it cannot hit the
# vendor composite teardown bug.
set -u
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

GADGET=${NUXEL_USB_GADGET:-/sys/kernel/config/usb_gadget/nuxel}
CONFIG=${NUXEL_USB_CONFIG:-c.1}
FUNC=ecm.usb0
UDC=${NUXEL_UDC_NAME:-10c00000.dwc3}
ADDR=${NUXEL_USB_NET_ADDR:-10.15.19.1/24}
IFACE=${NUXEL_USB_NET_IFACE:-usb0}
STATE_DIR=${NUXEL_USB_RUN_DIR:-/run/nuxel}
MARKER="$STATE_DIR/usb-net.state"

log() { printf '%s nuxel-usb-net-up: %s\n' "$(date -u +%FT%TZ)" "$*" >&2; }
state() { printf '{"active":%s,"interface":"%s","address":"%s","error":%s}\n' "$1" "$IFACE" "$ADDR" "${2:-null}" > "$MARKER.tmp.$$" 2>/dev/null && mv -f "$MARKER.tmp.$$" "$MARKER" 2>/dev/null; }

[ -d "$GADGET" ] || { log "no gadget at $GADGET (ACM-only console?)"; state false '"no-gadget"'; exit 0; }

if [ ! -d "$GADGET/functions/$FUNC" ]; then
  mkdir -p "$GADGET/functions/$FUNC" || { log "cannot create $FUNC"; state false '"configfs-ecm"'; exit 1; }
  ln -sfn "$GADGET/functions/$FUNC" "$GADGET/configs/$CONFIG/$FUNC" || { log "cannot link $FUNC"; state false '"configfs-link"'; exit 1; }
  log "ECM function created next to acm.usb0; re-binding $UDC once"
  printf '\n' > "$GADGET/UDC" 2>/dev/null || true
  sleep 1
  printf '%s\n' "$UDC" > "$GADGET/UDC" 2>/dev/null || { log "cannot bind $UDC"; state false '"udc-bind"'; exit 1; }
  n=0
  while [ "$n" -lt 50 ]; do
    [ -e "/sys/class/net/$IFACE" ] && break
    n=$((n+1)); sleep 0.1
  done
fi

[ -e "/sys/class/net/$IFACE" ] || { log "$IFACE did not appear"; state false '"no-interface"'; exit 1; }
ip link set "$IFACE" up || true
ip addr replace "$ADDR" dev "$IFACE" || { log "cannot address $IFACE"; state false '"address"'; exit 1; }
# Directly-connected /24 only: no default route, no DNS change.
state true
log "USB network ready: $IFACE $ADDR (owner SSH: ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.15.19.1)"
exit 0

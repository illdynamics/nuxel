#!/bin/sh
# Nuxel USB-network bring-up (owner SSH over the plugged-in USB cable).
#
# The S10+ live kernel has CONFIG_USB_CONFIGFS_ECM=y.  ECM is the safe,
# teardown-clean CDC data plane (the NCM function is the one with the recorded
# 4.14 teardown panic and is NEVER used here).  This script adds an ECM
# function next to the ACM live console, re-binds the UDC once, and gives the
# phone end of the link 10.100.10.1/24 (the Mac reaches it with 10.100.10.2/24,
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
# The owner may change these three values in /etc/nuxel/usb-network.conf.
# Keep the safe defaults when the optional file is absent.
USB_NET_CONFIG=${NUXEL_USB_NET_CONFIG:-/etc/nuxel/usb-network.conf}
[ -r "$USB_NET_CONFIG" ] && . "$USB_NET_CONFIG"
ADDR=${NUXEL_USB_NET_ADDR:-10.100.10.1/24}
IFACE=${NUXEL_USB_NET_IFACE:-usb0}
STATE_DIR=${NUXEL_USB_RUN_DIR:-/run/nuxel}
MARKER="$STATE_DIR/usb-net.state"

log() { printf '%s nuxel-usb-net-up: %s\n' "$(date -u +%FT%TZ)" "$*" >&2; }
state() { printf '{"active":%s,"interface":"%s","address":"%s","error":%s}\n' "$1" "$IFACE" "$ADDR" "${2:-null}" > "$MARKER.tmp.$$" 2>/dev/null && mv -f "$MARKER.tmp.$$" "$MARKER" 2>/dev/null; }

mkdir -p "$STATE_DIR"
# Keep ACM and ECM descriptors alive on Stop; only remove the local IP link.
# Unbinding the composite gadget would interrupt the serial recovery console.
if [ "${1:-start}" = stop ]; then
  ip addr del "$ADDR" dev "$IFACE" 2>/dev/null || true
  state false
  exit 0
fi
exec 9>"$STATE_DIR/usb-network.lock"
flock -x 9
[ -d "$GADGET" ] || { log "no gadget at $GADGET (ACM-only console?)"; state false '"no-gadget"'; exit 1; }

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
ip addr flush dev "$IFACE" scope global 2>/dev/null || true
ip addr replace "$ADDR" dev "$IFACE" || { log "cannot address $IFACE"; state false '"address"'; exit 1; }
# Directly-connected /24 only: no default route, no DNS change.
state true
log "USB network ready: $IFACE $ADDR (owner SSH: ssh -i ~/.ssh/wicked_wqn_id_rsa -p 2022 root@10.100.10.1)"
exit 0

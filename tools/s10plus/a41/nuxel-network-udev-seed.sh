#!/bin/sh
# Seed the NetworkManager-facing udev records for the vendor BCM/DHD WLAN.
#
# The S10+ 4.14 userspace deliberately masks systemd-udevd: its workers hit
# ENOSYS on this kernel and previously caused a worker storm.  NetworkManager
# 1.54 will not manage a network device without the corresponding
# /run/udev/data/n<ifindex> initialization record, even though the actual
# bcmdhd/cfg80211 interface is present.  This one-shot service supplies only
# that missing runtime metadata.  It never loads a driver, toggles RFKill, or
# creates an interface.
set -eu

SYS_CLASS_NET="${NUXEL_SYS_CLASS_NET:-/sys/class/net}"
UDEV_DATA_DIR="${NUXEL_UDEV_DATA_DIR:-/run/udev/data}"

mkdir -p "$UDEV_DATA_DIR"

for netdev in "$SYS_CLASS_NET"/wlan*; do
    [ -d "$netdev" ] || continue
    [ -e "$netdev/phy80211" ] || continue

    ifindex=$(cat "$netdev/ifindex")
    case "$ifindex" in
        ''|*[!0-9]*)
            echo "nuxel-network-udev-seed: invalid ifindex for $netdev" >&2
            continue
            ;;
    esac

    ifname=$(basename "$netdev")
    record="$UDEV_DATA_DIR/n$ifindex"

    # Do not overwrite an actual udev record if a future kernel supports an
    # unmasked udevd.  The compatibility record is intentionally runtime-only.
    [ -e "$record" ] && continue

    tmp="$UDEV_DATA_DIR/.nuxel-$ifindex.$$"
    umask 022
    {
        # `wl` and the default link file are the measured properties emitted
        # by `udevadm test /sys/class/net/wlan[01]` on beyond2lte.
        printf 'E:ID_NET_DRIVER=wl\n'
        printf 'E:ID_NET_LINK_FILE=/usr/lib/systemd/network/99-default.link\n'
        printf 'E:ID_NET_NAME=%s\n' "$ifname"
        printf 'E:NM_UNMANAGED=0\n'
        printf 'I:%s000000\n' "$(date +%s)"
    } >"$tmp"
    mv -f "$tmp" "$record"
done

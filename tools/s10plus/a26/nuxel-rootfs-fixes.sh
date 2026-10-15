#!/bin/bash
# ============================================================================
# nuxel-rootfs-fixes.sh — A26 Fedora-on-Linux-4.14 compatibility repairs.
#
# WHY: the Fedora 43 userspace on the Exynos 9820 (Samsung Linux 4.14.253)
# stalls its systemd boot graph.  Measured live on A25/A26 (see
# docs/s10plus-autonomous-boot-repair/A26-SYSTEMD-BOOT-GRAPH-FIX.md).  There are
# THREE independent 4.14 gaps, all reporting ENOSYS ("Function not
# implemented"), plus one containment:
#
#   1. systemd-userdbd cannot start at all:
#        systemd-userdbd[...]: Failed to watch child 6182: Function not implemented
#        systemd-userdbd[...]: Failed to start up daemon: Function not implemented
#      systemd 258 removed the legacy waitid()-based child watcher, so any
#      component that uses sd_event_add_child() is unusable on a kernel without
#      pidfd_open (Linux < 5.3).
#
#   2. Because (1) leaves the AF_UNIX socket
#        /run/systemd/userdb/io.systemd.Multiplexer
#      present but unserved, EVERY user/group lookup that falls through to the
#      userdb varlink API blocks FOREVER instead of failing fast.  Measured:
#        systemd-tmpfiles --prefix=/dev --create --boot --graceful
#          -> "io.systemd.DropIn: Sending ... GetGroupRecord {groupName: audio}"
#          -> never returns  => systemd-tmpfiles-setup-dev-early.service, a
#             oneshot with TimeoutStartUSec=infinity ordered Before=sysinit.target,
#             blocked the whole transaction (45 of 46 jobs stuck in "waiting").
#        /etc/nsswitch.conf "group: files [SUCCESS=merge] systemd" also forced
#        the varlink module into *every* glibc lookup: `getent group audio`
#        hung (measured rc=124 with `timeout 10`) until this was removed.
#
#   3. dbus-broker cannot start:
#        dbus-broker-launch: ERROR launcher_fork @ launcher.c +400:
#                            Function not implemented
#      so polkitd (Type=dbus) could never acquire its bus name and
#      multi-user.target never became active.  dbus-daemon (the reference
#      implementation, also shipped by Fedora) uses glib and works.
#
#   4. CONTAINMENT: systemd-udevd spawns workers but cannot register them --
#        systemd-udevd[...]: Failed to create worker object: Function not implemented  (x17739)
#        systemd-udevd[...]: Received notify datagram of unknown process [N], ignoring. (x17739)
#      With an event storm on the device tree it forked 17,723 processes in 50 s
#      and the board watchdog-reset.  devtmpfs (CONFIG_DEVTMPFS=y) already
#      provides every node Nuxel needs (/dev/fb0, /dev/input/event*, /dev/ttyGS0,
#      /dev/null, /dev/urandom ...), and static /dev permissions are applied by
#      systemd-tmpfiles, which is proven to work.  So udevd is masked until
#      sd-event's child watcher is made 4.14-capable (tracked in the same doc).
#
# Everything here is idempotent and reversible; originals are kept as
# *.nuxel-orig and every mask is a plain symlink to /dev/null.
#
# Usage:  nuxel-rootfs-fixes.sh --root /mnt/newroot
#         nuxel-rootfs-fixes.sh --live          (the running phone, no --root)
# ============================================================================
set -Eeuo pipefail

R=""
case "${1:-}" in
  --root) R="$2" ;;
  --live) R="" ;;
  *) echo "usage: $0 --root <rootfs-dir> | --live" >&2; exit 2 ;;
esac

say() { printf '[a26-fixes] %s\n' "$*"; }
SYS="$R/etc/systemd/system"

# ---- 1+2. NSS: never consult the varlink userdb module ----------------------
# /etc/nsswitch.conf is a symlink into authselect; edit the target so the change
# survives and is visible to every process.
NSS="$R/etc/authselect/nsswitch.conf"
if [ -f "$NSS" ] || [ -L "$R/etc/nsswitch.conf" ]; then
  tgt="$NSS"; [ -f "$tgt" ] || tgt="$R/etc/nsswitch.conf"
  if [ -f "$tgt" ] && ! [ -f "$tgt.nuxel-orig" ]; then cp -a "$tgt" "$tgt.nuxel-orig"; fi
  if [ -f "$tgt" ]; then
    # Portable rewrite (no `sed -i`: BSD and GNU disagree on its syntax).
    awk 'BEGIN{FS=OFS=":"}
         /^(passwd|shadow|group|gshadow)[ \t]*:/{ printf "%s:\tfiles\n", $1; next }
         { print }' "$tgt" > "$tgt.nuxel-new"
    mv -f "$tgt.nuxel-new" "$tgt"
    say "nsswitch: dropped the systemd (varlink) NSS module for passwd/shadow/group/gshadow"
  fi
fi

# ---- 1. Mask the userdb daemon and its socket -------------------------------
mkdir -p "$SYS"
for u in systemd-userdbd.socket systemd-userdbd.service; do
  ln -sfn /dev/null "$SYS/$u"
  say "masked $u (userdbd needs pidfd child watching: ENOSYS on Linux 4.14)"
done

# ---- 3. System bus: dbus-daemon instead of the broken dbus-broker ----------
if [ -f "$R/usr/lib/systemd/system/dbus-daemon.service" ]; then
  # remove the broker's alias/enablement, then enable the reference daemon
  rm -f "$SYS/dbus.service" "$SYS/messagebus.service"
  rm -f "$SYS/multi-user.target.wants/dbus-broker.service"
  ln -sfn /usr/lib/systemd/system/dbus-broker.service "$SYS/dbus-broker.service.off" 2>/dev/null || true
  rm -f "$SYS/dbus-broker.service.off"
  ln -sfn /usr/lib/systemd/system/dbus-daemon.service "$SYS/dbus.service"
  ln -sfn /usr/lib/systemd/system/dbus-daemon.service "$SYS/messagebus.service"
  mkdir -p "$SYS/multi-user.target.wants"
  ln -sfn /usr/lib/systemd/system/dbus-daemon.service "$SYS/multi-user.target.wants/dbus-daemon.service"
  say "system bus: dbus-broker -> dbus-daemon (launcher_fork ENOSYS on Linux 4.14)"
fi

# ---- 4. Contain udevd (devtmpfs supplies /dev) ------------------------------
for u in systemd-udevd.service systemd-udevd-kernel.socket \
         systemd-udevd-control.socket systemd-udevd-varlink.socket; do
  ln -sfn /dev/null "$SYS/$u"
done
say "masked systemd-udevd + its 3 sockets (worker objects cannot be created: ENOSYS)"
mkdir -p "$R/etc/udev"
touch "$R/etc/udev/udev.conf"
if [ -f "$R/etc/udev/udev.conf" ]; then
  grep -v '^udev_log=' "$R/etc/udev/udev.conf" > "$R/etc/udev/udev.conf.nuxel-new" 2>/dev/null || : > "$R/etc/udev/udev.conf.nuxel-new"
  printf 'udev_log=err\n' >> "$R/etc/udev/udev.conf.nuxel-new"
  mv -f "$R/etc/udev/udev.conf.nuxel-new" "$R/etc/udev/udev.conf"
fi

say "done"

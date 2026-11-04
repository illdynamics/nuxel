#!/bin/sh
# Unit-specific, bounded stop for nuxel-audio-session.service (PWNAGE-62000).
#
# Measured 2026-11-03 reboot: the shell main process exited on SIGTERM but the
# PipeWire children ignored it, so systemd burned the full 4 s final-sigterm
# timeout.  Signal this unit's exact cgroup, give a short cooperative window,
# then KILL only what remains.  No global timeout and no forced reboot.
set -u
unit="nuxel-audio-session.service"
procs=""
for p in \
  "/sys/fs/cgroup/system.slice/$unit/cgroup.procs" \
  "/sys/fs/cgroup/systemd/system.slice/$unit/cgroup.procs" \
  "/sys/fs/cgroup/pids/system.slice/$unit/cgroup.procs"; do
  [ -r "$p" ] || continue
  procs=$(cat "$p" 2>/dev/null || true)
  [ -n "$procs" ] && break
done
[ -n "$procs" ] || procs="${MAINPID:-}"

signal_all() {
  sig="$1"
  for pid in $procs; do
    case "$pid" in
      ''|*[!0-9]*) continue ;;
    esac
    [ "$pid" = "$$" ] && continue
    [ "$pid" = "$PPID" ] && continue
    kill "-$sig" "$pid" 2>/dev/null || true
  done
}
signal_all TERM
i=0
while [ "$i" -lt 4 ]; do
  sleep 0.1
  i=$((i + 1))
done
signal_all KILL
exit 0

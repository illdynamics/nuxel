#!/bin/sh
# Unit-specific, bounded stop for nuxel-wayland.service (PWNAGE-62000).
#
# The measured PWNAGE-51000 ExecStop signalled only MAINPID/direct children.
# The wrapper shell exits first, phoc is reparented, and the unit then burns
# the full 3 s timeout (journal: "Failed with result 'timeout'").  Signal the
# exact unit cgroup membership instead, then KILL only what remains.
set -u
unit="nuxel-wayland.service"
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
# Give the compositor/WebKit a short cooperative window, then force only this
# unit's cgroup.  Never a global timeout and never another service.
i=0
while [ "$i" -lt 5 ]; do
  sleep 0.1
  i=$((i + 1))
done
signal_all KILL
exit 0

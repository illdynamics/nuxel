#!/bin/sh
# nuxel-shell-chrome — single owner for the native shell chrome supervisors.
#
# PWNAGE-62000: the top bar, Back/Penguin Home/Tabs dock and compositor-level
# lock enforcer must survive an individual client crash but must never be
# started twice (two OVERLAY surfaces would duplicate the bar/dock and two lock
# watchers would fight).  This script is launched exactly once from
# nuxel-session.sh, takes a per-boot owner lock, then restarts each child with a
# bounded backoff.  Every child is a Wayland layer-shell/foreign-toplevel client;
# none of them opens /dev/fb0.
set -u
RUNTIME=/run/nuxel
STATUS=$RUNTIME/shell-chrome.json
OWNER=$RUNTIME/shell-chrome.owner
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/nuxel-wayland}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
mkdir -p "$RUNTIME" 2>/dev/null || true

# Single owner.  The lock is a pid file because /run is per-boot and a crashed
# supervisor must not permanently prevent the next session from starting one.
if [ -e "$OWNER" ]; then
  old=$(cat "$OWNER" 2>/dev/null || true)
  case "$old" in
    ''|*[!0-9]*) old=0 ;;
  esac
  if [ "$old" -gt 1 ] && kill -0 "$old" 2>/dev/null; then
    echo "shell-chrome: already owned by pid $old" >&2
    exit 0
  fi
fi
echo $$ > "$OWNER"

log() { echo "$(date -u +%FT%TZ) $*" >> /run/nuxel-shell-chrome.log; }
state() {
  # Atomic small state contract for Home/bridge diagnostics.  This is not an
  # authority: lock state remains /run/nuxel/security/lock-state.json.
  tmp="$STATUS.$$"
  printf '{"schema_version":1,"supervisor_pid":%s,"navdock_pid":%s,"statusbar_pid":%s,"lock_watch_pid":%s,"updated_at":"%s"}\n' \
    "$$" "${navdock_pid:-0}" "${statusbar_pid:-0}" "${lock_watch_pid:-0}" \
    "$(date -u +%FT%TZ)" > "$tmp" 2>/dev/null && mv "$tmp" "$STATUS" 2>/dev/null || true
}

navdock_pid=0
statusbar_pid=0
lock_watch_pid=0

start_navdock() {
  failures=0
  while :; do
    /usr/lib/nuxel/nuxel-navdock >>/run/nuxel-navdock.out 2>&1
    rc=$?
    failures=$((failures + 1))
    log "navdock exited rc=$rc failures=$failures; restarting"
    [ "$failures" -gt 3 ] && sleep 5 || sleep 1
  done
}
start_statusbar() {
  failures=0
  while :; do
    if [ ! -x /usr/lib/nuxel/nuxel-statusbar ]; then
      log "statusbar binary missing; Home DOM bar remains the fallback"
      sleep 30
      continue
    fi
    /usr/lib/nuxel/nuxel-statusbar >>/run/nuxel-statusbar.log 2>&1
    rc=$?
    failures=$((failures + 1))
    log "statusbar exited rc=$rc failures=$failures; restarting"
    [ "$failures" -gt 3 ] && sleep 5 || sleep 1
  done
}
start_lock_watch() {
  failures=0
  while :; do
    if [ ! -x /usr/lib/nuxel/nuxel-foreign-toplevel ]; then
      log "lock-watch helper missing; lock is still fail-closed in Home/navdock"
      sleep 30
      continue
    fi
    /usr/lib/nuxel/nuxel-foreign-toplevel watch-lock \
      >>/run/nuxel-lock-enforcement.log 2>&1
    rc=$?
    failures=$((failures + 1))
    log "lock-watch exited rc=$rc failures=$failures; restarting"
    [ "$failures" -gt 3 ] && sleep 5 || sleep 1
  done
}

start_navdock & navdock_pid=$!
start_statusbar & statusbar_pid=$!
start_lock_watch & lock_watch_pid=$!
state
log "shell-chrome ready navdock=$navdock_pid statusbar=$statusbar_pid lock_watch=$lock_watch_pid"

trap 'kill "$navdock_pid" "$statusbar_pid" "$lock_watch_pid" 2>/dev/null; rm -f "$OWNER"; exit 0' TERM INT HUP
while :; do
  state
  sleep 10
done

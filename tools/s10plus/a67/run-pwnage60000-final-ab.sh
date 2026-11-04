#!/usr/bin/env bash
# Final matched A/B: idle Home + Settings scroll, software-safe vs GPU-SHM.
# 3 x 60 s per case, profile verified in the measured WebKit process.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HOST="${1:-root@10.20.30.16}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST")
SCP=(scp -i "$KEY" -o BatchMode=yes)
REMOTE=/root/pwnage-60000/final-bench
LOCAL="$ROOT/evidence/pwnage-60000/bench/final"
mkdir -p "$LOCAL"
"${SSH[@]}" "mkdir -p '$REMOTE'"
"${SCP[@]}" "$ROOT/tools/s10plus/a67/bench-pwnage60000.py" \
             "$ROOT/tools/s10plus/a67/nuxel-scroll-workload.c" \
             /tmp/wlr-virtual-pointer-unstable-v1.xml "$HOST:$REMOTE/" >/dev/null
"${SSH[@]}" "set -e; cd '$REMOTE'
  if [ ! -x nuxel-scroll-workload ]; then
    wayland-scanner client-header wlr-virtual-pointer-unstable-v1.xml wlr-virtual-pointer-unstable-v1-client-protocol.h
    wayland-scanner private-code wlr-virtual-pointer-unstable-v1.xml wlr-virtual-pointer-unstable-v1-protocol.c
    gcc -O2 -std=gnu11 -I. \$(pkg-config --cflags wayland-client) -o nuxel-scroll-workload \
      nuxel-scroll-workload.c wlr-virtual-pointer-unstable-v1-protocol.c \$(pkg-config --libs wayland-client)
  fi"

wait_ready() {
  local i
  for i in $(seq 1 60); do
    "${SSH[@]}" 'systemctl is-active --quiet nuxel-wayland && systemctl is-active --quiet nuxel-wl-fb && grep -q FRAMES_OK /run/nuxel-wl-fb.state 2>/dev/null' && return 0
    sleep 1
  done
  return 1
}
set_profile() {
  case "$1" in
    software-safe) "${SSH[@]}" 'touch /run/nuxel-gpu-fallback; rm -f /run/nuxel/graphics-gpu-probe.json; systemctl restart nuxel-wayland nuxel-wl-fb' ;;
    gpu-rendered-shm-presented) "${SSH[@]}" 'rm -f /run/nuxel-gpu-fallback /run/nuxel/graphics-gpu-probe.json; systemctl restart nuxel-wayland nuxel-wl-fb' ;;
  esac
  wait_ready
  sleep 18
  local active
  active=$("${SSH[@]}" '/usr/lib/nuxel/nuxel-graphics-profile env webkit | sed -n "s/^export NUXEL_GRAPHICS_PROFILE_ACTIVE=//p"')
  [ "$active" = "$1" ] || { echo "PROFILE_ASSERT_FAILED expected=$1 got=$active" >&2; exit 3; }
  echo "PROFILE_ASSERT_OK active=$active"
}
start_settings() {
  "${SSH[@]}" "set -e
    export XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0
    eval \"\$(/usr/lib/nuxel/nuxel-graphics-profile env webkit)\"
    NUXEL_HOME_URL=http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html \
      nohup /usr/lib/nuxel/nuxel-pwa-host >/tmp/p60000-final-settings-${1}.log 2>&1 &
    echo \$! > /run/nuxel-p60000-final-settings.pid
    sleep 7
    pid=\$(cat /run/nuxel-p60000-final-settings.pid)
    active=\$(tr '\\0' '\\n' < /proc/\$pid/environ | sed -n 's/^NUXEL_GRAPHICS_PROFILE_ACTIVE=//p')
    [ \"\$active\" = '$1' ] || { echo SETTINGS_PROFILE_MISMATCH expected=$1 got=\$active >&2; exit 3; }
    echo SETTINGS_READY pid=\$pid active=\$active"
}
stop_settings() {
  "${SSH[@]}" 'pid=$(cat /run/nuxel-p60000-final-settings.pid 2>/dev/null || true); [ -n "$pid" ] && kill "$pid" 2>/dev/null || true; rm -f /run/nuxel-p60000-final-settings.pid' || true
}
restore_gpu() {
  stop_settings
  "${SSH[@]}" 'rm -f /run/nuxel-gpu-fallback /run/nuxel/graphics-gpu-probe.json; systemctl restart nuxel-wayland nuxel-wl-fb' || true
  wait_ready || true
}
trap restore_gpu EXIT

for profile in software-safe gpu-rendered-shm-presented; do
  echo "===== PROFILE $profile ====="
  set_profile "$profile"
  "${SSH[@]}" "/usr/lib/nuxel/nuxel-gpu-status --json --no-probe" > "$LOCAL/status-$profile.json" 2>&1 || true
  for run in 1 2 3; do
    echo "-- idle run $run --"
    "${SSH[@]}" "cd '$REMOTE' && python3 bench-pwnage60000.py --label 'final-${profile}-idle' --run '$run' --seconds 60 --out '$REMOTE'"
    sleep 3
  done
  start_settings "$profile"
  for run in 1 2 3; do
    echo "-- settings-scroll run $run --"
    "${SSH[@]}" "cd '$REMOTE' && python3 bench-pwnage60000.py --label 'final-${profile}-settings-scroll' --run '$run' --seconds 60 --workload scroll --out '$REMOTE'"
    sleep 3
  done
  stop_settings
  sleep 2
done
echo "== restoring production GPU profile =="
restore_gpu
trap - EXIT
"${SCP[@]}" -r "$HOST:$REMOTE" "$LOCAL/" >/dev/null
echo "FINAL_AB_COMPLETE $LOCAL"

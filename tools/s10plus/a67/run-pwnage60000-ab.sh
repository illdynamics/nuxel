#!/usr/bin/env bash
# Matched A/B on the physical S10+: software-safe vs gpu-rendered-shm-presented.
# Restores the production GPU profile at the end, even on failure.
#
#   tools/s10plus/a67/run-pwnage60000-ab.sh [root@10.20.30.16] [runs] [seconds]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HOST="${1:-root@10.20.30.16}"
RUNS="${2:-3}"
SECS="${3:-60}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST")
SCP=(scp -i "$KEY" -o BatchMode=yes)
REMOTE_DIR=/root/pwnage-60000/bench
LOCAL_DIR="$ROOT/evidence/pwnage-60000/bench"
mkdir -p "$LOCAL_DIR"

"${SSH[@]}" "mkdir -p '$REMOTE_DIR'"
"${SCP[@]}" "$ROOT/tools/s10plus/a67/bench-pwnage60000.py" "$HOST:$REMOTE_DIR/" >/dev/null

wait_ready() {
  local i
  for i in $(seq 1 60); do
    if "${SSH[@]}" 'systemctl is-active --quiet nuxel-wayland && systemctl is-active --quiet nuxel-wl-fb && grep -q FRAMES_OK /run/nuxel-wl-fb.state 2>/dev/null'; then
      return 0
    fi
    sleep 1
  done
  return 1
}

verify_profile() { # expected
  local expected="$1" want_disable
  case "$expected" in
    software-safe) want_disable=1 ;;
    gpu-rendered-shm-presented) want_disable=0 ;;
    *) echo "bad profile $expected" >&2; return 2 ;;
  esac
  "${SSH[@]}" "set -e
    pid=\$(pgrep -f WebKitWebProcess | head -1)
    test -n \"\$pid\"
    tr '\0' '\n' < /proc/\$pid/environ | grep -q 'WEBKIT_DISABLE_COMPOSITING_MODE=$want_disable'
    if [ '$expected' = gpu-rendered-shm-presented ]; then
      grep -q libgallium /proc/\$pid/maps
      ls -l /proc/\$pid/fd | grep -q /dev/mali0
    else
      ! grep -q libgallium /proc/\$pid/maps
    fi
    echo PROFILE_OK expected=$expected pid=\$pid"
}

set_profile() {
  local profile="$1"
  case "$profile" in
    software-safe)
      "${SSH[@]}" 'touch /run/nuxel-gpu-fallback; rm -f /run/nuxel/graphics-gpu-probe.json; systemctl restart nuxel-wayland nuxel-wl-fb'
      ;;
    gpu-rendered-shm-presented)
      "${SSH[@]}" 'rm -f /run/nuxel-gpu-fallback /run/nuxel/graphics-gpu-probe.json; systemctl restart nuxel-wayland nuxel-wl-fb'
      ;;
  esac
  wait_ready
  sleep 20
  verify_profile "$profile"
}

restore_gpu() {
  "${SSH[@]}" 'rm -f /run/nuxel-gpu-fallback /run/nuxel/graphics-gpu-probe.json; systemctl restart nuxel-wayland nuxel-wl-fb' || true
  wait_ready || true
  verify_profile gpu-rendered-shm-presented || true
}
trap restore_gpu EXIT

for profile in software-safe gpu-rendered-shm-presented; do
  echo "== profile $profile =="
  set_profile "$profile"
  "${SSH[@]}" "/usr/lib/nuxel/nuxel-gpu-status --json --no-probe" > "$LOCAL_DIR/status-$profile.json" 2>&1 || true
  for run in $(seq 1 "$RUNS"); do
    echo "-- $profile run $run/$RUNS ($SECS s) --"
    "${SSH[@]}" "python3 '$REMOTE_DIR/bench-pwnage60000.py' --label '$profile' --run '$run' --seconds '$SECS' --out '$REMOTE_DIR'"
    sleep 5
  done
done

echo "== restoring production GPU profile =="
restore_gpu
trap - EXIT
"${SCP[@]}" -r "$HOST:$REMOTE_DIR" "$LOCAL_DIR/" >/dev/null
echo "PWN60000 A/B complete: $LOCAL_DIR"

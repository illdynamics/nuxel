#!/usr/bin/env bash
# PWNAGE-93000 bounded app-exit matrix (runs ON the S10+).
# Each cycle: unlock -> launch -> single host Back -> verify Home activation,
# no non-Home active/fullscreen toplevel, and a converged Home receipt.
set -u
export XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0
HOST_FIFO=/run/nuxel-pwa-host.cmd
LIST=/usr/lib/nuxel/nuxel-foreign-toplevel
unlock() {
  printf 'screen-on\n' > /run/nuxel-wl-fb.cmd 2>/dev/null || true
  sleep 0.4
  curl -s http://127.0.0.1:8080/api/v1/rpc -X POST -H 'Content-Type: application/json' \
    -d '{"app_id":"org.nuxel.Home","namespace":"security","verb":"unlock","params":{}}' >/dev/null
  sleep 0.4
}
snapshot() {
  "$LIST" list 2>/dev/null | grep '^WIN' || true
}
check_cycle() {
  local n="$1" app="$2" wait="$3"
  unlock
  printf 'action launch-app %s\n' "$app" > "$HOST_FIFO"
  sleep "$wait"
  printf 'action back\n' > "$HOST_FIFO"
  sleep 3
  local lines home_act app_act nonhome_active receipt
  lines=$(snapshot)
  home_act=$(printf '%s\n' "$lines" | awk '/app_id=nuxel-pwa-host/{for(i=1;i<=NF;i++) if($i=="act=1") print 1}')
  app_act=$(printf '%s\n' "$lines" | awk -v a="$app" 'index($0,"app_id=" a)>0 {for(i=1;i<=NF;i++) if($i=="act=1") print 1}')
  nonhome_active=$(printf '%s\n' "$lines" | awk 'index($0,"app_id=nuxel-pwa-host")==0 && /act=1/ {c++} END{print c+0}')
  receipt=$(python3 - <<'PY'
import json
try:
    d=json.load(open('/run/nuxel/home-transition.json'))
    print('1' if d.get('converged') else '0')
except Exception:
    print('0')
PY
)
  printf 'CYCLE %s app=%s home_act=%s app_act=%s nonhome_active=%s converged=%s fg=%s\n' \
    "$n" "$app" "${home_act:-0}" "${app_act:-0}" "$nonhome_active" "$receipt" \
    "$(tr '\n' ' ' </run/nuxel/foreground.state 2>/dev/null)"
}
for i in $(seq 1 7); do check_cycle "$i" org.nuxel.Calendar 4; done
for i in $(seq 8 14); do check_cycle "$i" org.gnome.SystemMonitor 5; done
for i in $(seq 15 20); do check_cycle "$i" org.gnome.TextEditor 6; done

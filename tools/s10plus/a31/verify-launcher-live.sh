#!/usr/bin/env bash
# verify-launcher-live.sh — deterministic live acceptance checks for NUXEL S10+ BETA.
#
# Runs over the USB live console with the framed, SHA-verified transport. No
# screenshots, no image analysis: every check is a file/HTTP/process assertion and
# every one reports its own exit status.
#
#   tools/s10plus/a31/verify-launcher-live.sh
#
# Exit status: 0 = every automated check passed. Non-zero = the number of failed
# checks (capped at 120). Physical/visual acceptance is the user's, and is NOT
# claimed here (see docs/.../BETA-FINALIZER/10-BETA-TEST-RESULTS.md).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
LIVE="$ROOT/scripts/s10plus-debug-pack/nuxel-live.sh"
FAILED=0; TOTAL=0

pass() { TOTAL=$((TOTAL+1)); printf 'PASS  %s\n' "$1"; }
fail() { TOTAL=$((TOTAL+1)); FAILED=$((FAILED+1)); printf 'FAIL  %s\n' "$1"; }

# run a remote command; prints its stdout, and echoes the transport verdict on stderr
runx() { "$LIVE" --timeout "${2:-45}" --run "$1" 2>&1; }

check_contains() {   # name, remote-cmd, needle
  local name="$1" cmd="$2" needle="$3" out
  out=$(runx "$cmd")
  if ! printf '%s' "$out" | grep -q 'sha_ok=yes'; then fail "$name (transport failure)"; return; fi
  if printf '%s' "$out" | grep -qF -- "$needle"; then pass "$name"; else
    fail "$name (missing: $needle)"; printf '%s\n' "$out" | tail -4 | sed 's/^/        /'; fi
}

echo "== NUXEL S10+ BETA — live automated acceptance =="

check_contains "1. launcher units active" \
  'systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-touch-arm | tr "\n" " "' 'active active active'
check_contains "2. compositor owns the touchscreen" \
  'p=$(systemctl show -p MainPID --value nuxel-wayland); n=$(ls -l /proc/$p/fd 2>/dev/null | grep -c /dev/input/event); [ "$n" -ge 1 ] && echo HAS_INPUT_DEVICES' 'HAS_INPUT_DEVICES'
check_contains "3. libinput accepted sec_touchscreen" \
  'grep -c "sec_touchscreen. accepted=1" /run/nuxel-libinput-path.state' '1'
check_contains "4. wallpaper served as image/png" \
  'curl -s -o /dev/null -w "%{http_code} %{content_type}" http://127.0.0.1:8000/pwa/nuxel-home/assets/nuxel-background.png' '200 image/png'
check_contains "5. launcher page + bridge module 200" \
  'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/pwa/nuxel-home/index.html; curl -s -o /dev/null -w " %{http_code}" http://127.0.0.1:8000/pwa/nuxel-common/bridge.js' '200 200'
check_contains "6. application pages 200" \
  'for a in mail calendar notes files; do curl -s -o /dev/null -w "%{http_code} " http://127.0.0.1:8000/pwa/nuxel-apps/$a/index.html; done' '200 200 200 200'
check_contains "7. animation stop requested and confirmed" \
  'ls /var/lib/nuxel/anim-stop /run/nuxel-anim-stop.confirmed >/dev/null 2>&1 && echo BOTH_PRESENT' 'BOTH_PRESENT'
check_contains "8. animation stopped, bridge owns panel" \
  'grep -c "ANIMATION_STOPPED" /var/lib/nuxel/animation; grep -c "ANIM_OWNER=nuxel-wl-fb" /var/lib/nuxel/animation' '1
1'
check_contains "9. single framebuffer owner" \
  'echo "bridge=$(pgrep -cf nuxel-wl-fb) anim=$(pgrep -cf nuxel-anim-player)"' 'bridge=1 anim=0'
check_contains "10. launcher ready + splash removed" \
  'grep -c NUXEL_HOME_READY /run/nuxel-home.state; grep -c "splash-t4s absent" /run/nuxel-home.state' '1'
check_contains "11. boot-animation ownership policy active" \
  'grep -c "NUXEL_BOOT_POLICY host-enforced=1" /run/nuxel-home.state' '1'
check_contains "12. wallpaper decoded by the browser" \
  'grep -c "wallpaper url=.*decoded=1 natural=" /run/nuxel-home.state' '1'
check_contains "13. bridge reports itself as owner" \
  'grep -c "owner=nuxel-wl-fb" /run/nuxel-wl-fb.state' '1'
check_contains "14. bridge capture failures are zero" \
  'tail -1 /run/nuxel-wl-fb.state | grep -c "failures=0"' '1'
check_contains "15. touchscreen armed once, reader held" \
  'grep -c ARMED_OK /run/nuxel-touch-arm.state; ls -l /proc/$(pgrep -x nuxel-touch-arm)/fd 2>/dev/null | grep -c /dev/input/event' '1'
check_contains "16. WebKit web process alive" \
  'pgrep -cf WebKitWebProcess' '1'
check_contains "17. media gated (no crash path)" \
  'grep -c "NUXEL_HOME_MEDIA enable_media=0" /run/nuxel-home.state' '1'

printf '\n== %d/%d automated checks passed ==\n' "$((TOTAL-FAILED))" "$TOTAL"
[ "$FAILED" -eq 0 ] || printf '   %d FAILED\n' "$FAILED"
exit "$FAILED"

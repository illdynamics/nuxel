#!/usr/bin/env bash
# nuxel-cast-diag.sh — S10+ (beyond2lte) wireless casting capability probe.
#
# READ-ONLY. Probes the three things a real Miracast / LAN screen-share needs,
# and reports each honestly. It NEVER starts a stream, joins a P2P group, or
# captures the screen — those are owner-started actions. A Miracast button must
# not exist unless the capture/transport/encode pipeline actually functions.
#
#   p2p       Wi-Fi P2P / Wi-Fi Display (iw phy + wpa_supplicant P2P)
#   capture   compositor screen capture (wlr-screencopy / PipeWire portal / grim)
#   encoder   a real H.264 encoder (GStreamer openh264/x264/vaapi)
#   networkd  gnome-network-displays reference (not a drop-in for Phoc)
#
# Verdicts: MIRACAST_CANDIDATE | LAN_SCREENSHARE_CANDIDATE | NO_CAPTURE |
#           NO_ENCODER | NO_P2P_NO_CAPTURE | NO_WIFI
set -uo pipefail
ROOT="${NUXEL_DIAG_ROOT:-/}"
ARGS=()
while [ $# -gt 0 ]; do case "$1" in
  --root) ROOT="${2:?}"; shift 2 ;; --root=*) ROOT="${1#--root=}"; shift ;; *) ARGS+=("$1"); shift ;; esac; done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true
JSON=0
for a in "$@"; do case "$a" in --json) JSON=1 ;; esac; done
abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
say() { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1 && printf '1' || printf '0'; }

# ---- read-only capability checks ------------------------------------------
p2p_evidence() {
  local iw out=""
  [ "$(have iw)" = 1 ] && out="$(iw phy 2>/dev/null | grep -i -m1 'P2P')"
  [ -n "$out" ] && printf 'iw-p2p'
}
wpa_p2p() {
  [ "$(have wpa_supplicant)" = 1 ] && wpa_supplicant -v 2>/dev/null | grep -qi 'p2p' && printf 'wpa-supplicant-p2p'
}
capture_evidence() {
  local ev=""
  [ "$(have grim)" = 1 ] && ev="grim"
  [ "$(have wf-recorder)" = 1 ] && ev="${ev:+$ev,}wf-recorder"
  # wlr-screencopy protocol file present (Phoc exposes screencopy, not PipeWire portal)
  [ -r "$(abs /usr/share/wayland-protocols/unstable/wlr-screencopy/wlr-screencopy-unstable-v1.xml)" ] && ev="${ev:+$ev,}wlr-screencopy"
  [ "$(have pipewire)" = 1 ] && ev="${ev:+$ev,}pipewire"
  printf '%s' "$ev"
}
encoder_evidence() {
  local ev=""
  [ "$(have gst-inspect-1.0)" = 1 ] || { printf '%s' ''; return; }
  for enc in openh264enc x264enc vah264enc av1enc vp8enc vp9enc; do
    gst-inspect-1.0 "$enc" >/dev/null 2>&1 && ev="${ev:+$ev,}$enc"
  done
  printf '%s' "$ev"
}
gnd_evidence() { [ "$(have gnome-network-displays)" = 1 ] && printf 'gnome-network-displays'; }
wifi_device() {
  [ -r "$(abs /sys/class/net)" ] || { printf ''; return; }
  for d in "$(abs /sys/class/net)"/*; do
    [ -d "$d" ] && [ -r "$d/operstate" ] && printf '%s' "${d#$ROOT} "
  done
}

cmd_status() {
  local p2p wpa cap enc gnd wifi
  p2p="$(p2p_evidence)"; wpa="$(wpa_p2p)"; cap="$(capture_evidence)"; enc="$(encoder_evidence)"; gnd="$(gnd_evidence)"; wifi="$(wifi_device)"

  if [ "$JSON" = 1 ]; then
    python3 - "$p2p" "$wpa" "$cap" "$enc" "$gnd" "$wifi" <<'PY'
import json, sys
p2p, wpa, cap, enc, gnd, wifi = sys.argv[1:7]
has_p2p = bool(p2p or wpa)
has_cap = bool(cap)
has_enc = bool(enc)
if has_p2p and has_cap and has_enc: verdict = "MIRACAST_CANDIDATE"
elif has_cap and has_enc: verdict = "LAN_SCREENSHARE_CANDIDATE"
elif not has_cap: verdict = "NO_CAPTURE"
elif not has_enc: verdict = "NO_ENCODER"
elif not has_p2p: verdict = "NO_P2P_NO_CAPTURE" if not has_cap else "NO_P2P"
else: verdict = "NO_WIFI"
print(json.dumps({
  "device": "beyond2lte", "tool": "nuxel-cast-diag", "read_only": True,
  "p2p": p2p, "wpa_p2p": wpa, "capture": cap, "encoders": enc,
  "gnome_network_displays": gnd, "wifi_interfaces": wifi.split(),
  "verdict": verdict, "owner_proof": "docs/A49/OWNER-TEST-CAST.md",
  "moving_picture_verified": False}, separators=(",", ":")))
PY
    return 0
  fi
  say "device: beyond2lte — wireless casting capability probe (READ-ONLY)"
  say "wifi p2p      : ${p2p:-none} ${wpa:-}"
  say "capture       : ${cap:-none}"
  say "encoders      : ${enc:-none}"
  say "gnome-netdisp : ${gnd:-absent} (reference only, not a Phoc drop-in)"
  say "wifi ifaces   : ${wifi:-none}"
  say ""
  if [ -n "$p2p" ] || [ -n "$wpa" ]; then
    if [ -n "$cap" ] && [ -n "$enc" ]; then say "verdict: MIRACAST_CANDIDATE (still needs a real capture pipeline on Phoc)"
    else say "verdict: NO_P2P_CAPTURE_ENCODER — P2P present but capture/encoder missing"; fi
  elif [ -n "$cap" ] && [ -n "$enc" ]; then
    say "verdict: LAN_SCREENSHARE_CANDIDATE — accurate label: 'Share screen' (WebRTC), not Miracast"
  elif [ -z "$cap" ]; then say "verdict: NO_CAPTURE — no compositor screen capture transport"
  elif [ -z "$enc" ]; then say "verdict: NO_ENCODER — no H.264 encoder found"
  else say "verdict: NO_WIFI"
  fi
  say "moving picture on a real receiver is NEEDS_OWNER_TEST (docs/A49/OWNER-TEST-CAST.md)"
}
cmd_selftest() {
  local here fixdir n=0 rc=0 f exp got
  here="$(cd "$(dirname "$0")" && pwd)"
  fixdir="$here/tests/hw-subsystems/fixtures"
  for f in "$fixdir"/cast-*; do
    [ -d "$f" ] || continue
    n=$((n+1))
    exp="$(sed -n 's/^expect=//p' "$f/EXPECTED" | head -1)"
    got="$(NUXEL_DIAG_ROOT="$f" PATH="$f/bin:$PATH" bash "$0" status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["verdict"])' 2>/dev/null)"
    if [ "$exp" = "$got" ]; then printf 'PASS %-28s verdict=%s\n' "$(basename "$f")" "$got"
    else printf 'FAIL %-28s expected=%s got=%s\n' "$(basename "$f")" "$exp" "$got"; rc=1; fi
  done
  [ "$n" -gt 0 ] || { printf 'FAIL selftest: zero fixtures\n'; rc=1; }
  printf '%d fixtures checked\n' "$n"; return $rc
}
case "$CMD" in
  status) cmd_status ;;
  selftest) cmd_selftest ;;
  help|-h|--help) sed -n '2,20p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) say "unknown command: $CMD (try help)"; exit 2 ;;
esac

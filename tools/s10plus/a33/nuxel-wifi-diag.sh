#!/usr/bin/env bash
# nuxel-wifi-diag.sh — S10+ (SM-G975F / beyond2lte) Wi-Fi bring-up diagnoser.
#
# WHAT THIS IS
#   A read-mostly diagnostic that reports what the LIVE system actually shows:
#   which netdevs exist, which Wi-Fi driver/module is bound, whether firmware
#   blobs are present, what the supplicant/NetworkManager report, and — only if
#   a real association with a real IP is observed — that the radio is up.
#
# WHAT THIS IS NOT
#   It never claims Wi-Fi works. A registered module is not proof of a working
#   radio; a scan that returns nothing is not proof of a broken one. The verdict
#   is derived from observable evidence only, and the terminal state for the
#   S10+ radio stays NEEDS_OWNER_TEST until an association is observed on the
#   physical handset (docs/beta-finalization/manual-proof/04-wifi.md).
#
#   The S10+ uses a Murata/Broadcom BCM4375-class part. docs/wifi-bcm4390-status.md
#   describes the Google Pixel BCM4390 and MUST NOT be applied to this device.
#
# Usage (also reachable as `nuxelctl wifi <sub>`):
#   nuxel-wifi-diag.sh status            # default: full evidence report + verdict
#   nuxel-wifi-diag.sh status --json     # machine-readable, for the bridge/apps
#   nuxel-wifi-diag.sh firmware          # blob inventory vs candidate names
#   nuxel-wifi-diag.sh scan              # nmcli scan (or `iw`, or `wpa_cli`)
#   nuxel-wifi-diag.sh connect <SSID>    # prompts for the PSK; never stored here
#   nuxel-wifi-diag.sh disconnect
#   nuxel-wifi-diag.sh regdom [CC]       # read or set the 802.11 regulatory domain
#   nuxel-wifi-diag.sh report [--json]   # status + write the evidence log
#   nuxel-wifi-diag.sh selftest          # run the bundled offline fixtures
#   nuxel-wifi-diag.sh help
#
# OFFLINE TESTABILITY
#   NUXEL_DIAG_ROOT=DIR (or --root DIR) prefixes every filesystem lookup (/sys, /proc, /lib/firmware,
#   /var, /run) and prefers "$DIR/usr/bin/<tool>" over the system tool. Tests
#   additionally set NUXEL_DIAG_NO_SYSTEM=1 so a fixture run can never silently
#   read the host's real state. This is what makes the parser testable on a
#   laptop with no radio at all.
set -uo pipefail

SELF="$(basename "$0")"
SELF_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
ROOT="${NUXEL_DIAG_ROOT:-/}"
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="${2:?--root needs a directory}"; shift 2 ;;
    --root=*) ROOT="${1#--root=}"; shift ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true

# NetworkManager conf-level ifname list, mirrored here so the report and the
# policy cannot drift: the first name that exists wins, none is assumed.
IFNAME_CANDIDATES="${NUXEL_WIFI_IF:-wlan0 wlp1s0 wifi0}"
EVIDENCE_LOG="${NUXEL_WIFI_LOG:-/var/log/nuxel/wifi-diag.log}"
# Candidate firmware names for this device class. Ordered most-likely first.
# Absence of ALL of them is what makes the verdict BLOCKED_FIRMWARE, and the
# list is evidence-gathering, not an assertion that these names are correct for
# the S10+ (the vendor blob names are read from the live vendor partition copy
# under /lib/firmware once the owner mounts it).
FW_CANDIDATES=(
  "brcm/BCM4375B1.hcd" "brcm/bcm4375b1.hcd"
  "brcm/brcmfmac4375-pcie.bin" "brcm/brcmfmac4375.bin" "brcm/brcmfmac4375_pcie.bin"
  "brcm/brcmfmac4375-pcie.clm_blob" "brcm/brcmfmac4375.clm_blob"
  "brcm/brcmfmac4375.nvm" "brcm/brcmfmac4375-sdio.bin" "brcm/brcmfmac4375-sdio.clm_blob"
  "brcm/brcmfmac4375-sdio.nvm" "bcmdhd_sta.bin" "bcmdhd_sta_bcm4375.bin"
  "fw_bcmdhd.bin" "nvram_.txt" "nvram.txt" "bcmdhd.cal"
)
MODULE_CANDIDATES=(bcmdhd brcmfmac brcmfmac4375 dhd cfg80211 mac80211 btbcm)

say() { printf '%s\n' "$*"; }
hdr() { printf '\n== %s ==\n' "$*"; }
# Absolute path inside the (possibly faked) root.
abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
exists() { [ -e "$(abs "$1")" ]; }

# run_tool TOOL ARGS...  -> prefers $ROOT/usr/bin/TOOL, then $ROOT/bin/TOOL, then
# the system tool unless NUXEL_DIAG_NO_SYSTEM=1. Prints nothing and returns 127
# when the tool is unavailable, which every caller must handle explicitly.
run_tool() {
  local t="$1"; shift
  local p
  for p in "$ROOT/usr/bin/$t" "$ROOT/bin/$t" "$ROOT/usr/sbin/$t" "$ROOT/sbin/$t"; do
    if [ -x "$p" ] && [ "$ROOT" != "/" ]; then "$p" "$@"; return $?; fi
  done
  if [ "${NUXEL_DIAG_NO_SYSTEM:-0}" = "1" ]; then return 127; fi
  command -v "$t" >/dev/null 2>&1 || return 127
  "$t" "$@"
}
have_tool() { run_tool "$1" --version >/dev/null 2>&1 || run_tool "$1" -v >/dev/null 2>&1; }

json_escape() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr -d '\r'; }

# ---------------------------------------------------------------------------
# collectors — each prints a key=value line so the verdict logic below is pure
# ---------------------------------------------------------------------------
collect_netdevs() {
  local d
  for d in "$(abs /sys/class/net)"/*; do
    [ -e "$d" ] || continue
    local n; n="$(basename "$d")"
    local wireless="no" phy="" drv="?" speed=""
    [ -d "$d/wireless" ] && wireless="yes"
    [ -L "$d/phy80211" ] && wireless="yes"
    phy="$(ls -l "$d/phy80211" 2>/dev/null | sed -e 's#.*/##')"
    [ -n "$phy" ] || phy="$(basename "$(readlink -f "$d/phy80211" 2>/dev/null)" 2>/dev/null)"
    if [ -L "$d/device/driver" ]; then drv="$(basename "$(readlink "$d/device/driver")")"; fi
    local op="down"
    [ -r "$d/operstate" ] && op="$(cat "$d/operstate" 2>/dev/null)"
    printf 'netdev name=%s wireless=%s driver=%s operstate=%s phy=%s\n' "$n" "$wireless" "$drv" "$op" "${phy:-none}"
  done
}

collect_modules() {
  local m
  say "modules_loaded:"
  if [ -r "$(abs /proc/modules)" ]; then
    while read -r name _size _use _deps _state _addr; do
      for m in "${MODULE_CANDIDATES[@]}"; do
        [ "$name" = "$m" ] && say "  loaded $name"
      done
    done < "$(abs /proc/modules)"
  else
    say "  (/proc/modules unreadable — cannot distinguish 'not loaded' from 'unknown')"
  fi
  say "modules_available_on_disk:"
  local base f
  for base in /lib/modules; do
    [ -d "$(abs $base)" ] || { say "  ($base absent)"; continue; }
    for m in "${MODULE_CANDIDATES[@]}"; do
      f="$(find "$(abs $base)" -name "$m.ko*" -print -quit 2>/dev/null)"
      [ -n "$f" ] && say "  present ${f#"$ROOT"}"
    done
  done
}

collect_firmware() {
  local found=0 listed=""
  say "firmware_candidates:"
  local n
  for n in "${FW_CANDIDATES[@]}"; do
    if [ -e "$(abs "/lib/firmware/$n")" ]; then
      local sz; sz="$(wc -c < "$(abs "/lib/firmware/$n")" 2>/dev/null | tr -d ' ')"
      say "  PRESENT /lib/firmware/$n bytes=${sz:-?}"
      found=$((found+1)); listed="$listed $n"
    else
      say "  absent  /lib/firmware/$n"
    fi
  done
  say "firmware_dirs:"
  local d
  for d in /lib/firmware/brcm /lib/firmware/updates/brcm /vendor/firmware /system/etc/firmware; do
    if [ -d "$(abs $d)" ]; then
      say "  $d: $(ls -1 "$(abs $d)" 2>/dev/null | wc -l | tr -d ' ') file(s)"
    else
      say "  $d: absent"
    fi
  done
  FW_FOUND="$found"
}

collect_dmesg() {
  local pat='bcmdhd|brcmfmac|dhd_|dhd |wl_cfg80211|BCM4375|4375|sdio|mmc1|wlan|firmware'
  say "dmesg_relevant (last 25):"
  local out
  out="$( { run_tool dmesg 2>/dev/null || cat "$(abs /var/log/dmesg)" 2>/dev/null || cat "$(abs /var/log/kern.log)" 2>/dev/null; } | grep -iE "$pat" | tail -25 )"
  if [ -n "$out" ]; then printf '  %s\n' "$out"; else say "  (no matching kernel messages)"; fi
  say "journal_relevant (last 15):"
  local jout
  jout="$(run_tool journalctl -k -b --no-pager 2>/dev/null | grep -iE "$pat" | tail -15)"
  if [ -n "$jout" ]; then printf '  %s\n' "$jout"; else say "  (none)"; fi
}

collect_supplicant() {
  say "supplicant:"
  local wpa; wpa="$(command -v wpa_supplicant 2>/dev/null || true)"
  if [ "$ROOT" != "/" ] && [ -x "$ROOT/usr/sbin/wpa_supplicant" ]; then wpa="$ROOT/usr/sbin/wpa_supplicant"; fi
  if [ -n "$wpa" ]; then
    say "  wpa_supplicant: $wpa ($("$wpa" -v 2>/dev/null | head -1))"
  else
    say "  wpa_supplicant: ABSENT (no Wi-Fi supplicant on this image — Wi-Fi cannot associate)"
  fi
  local iwd; iwd="$(command -v iwd 2>/dev/null || true)"
  say "  iwd: ${iwd:-absent}"
  say "  sockets:"
  local s
  for s in /var/run/wpa_supplicant /run/wpa_supplicant; do
    [ -d "$(abs $s)" ] && say "    $s present: $(ls -1 "$(abs $s)" 2>/dev/null | tr '\n' ' ')" || say "    $s absent"
  done
}

collect_nm() {
  say "networkmanager:"
  local nm; nm="$(run_tool nmcli -t -f RUNNING general 2>/dev/null)"
  if [ -z "$nm" ]; then
    say "  (nmcli unavailable or NetworkManager not answering)"
  else
    say "  nmcli RUNNING=$nm"
    if [ "$nm" = "running" ]; then
      say "  wifi radio: $(run_tool nmcli -t -f WIFI general 2>/dev/null)"
      local devs; devs="$(run_tool nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status 2>/dev/null | grep -E ':wifi' || true)"
      [ -n "$devs" ] && say "  wifi devices: $devs" || say "  wifi devices: none reported by NetworkManager"
      [ -n "${IFNAME:-}" ] && say "  device detail:" && run_tool nmcli device show "$IFNAME" 2>/dev/null | sed -n '1,40p' | sed 's/^/    /'
    fi
  fi
}

collect_rfkill() {
  say "rfkill:"
  local out; out="$(run_tool rfkill list 2>/dev/null)"
  if [ -n "$out" ]; then printf '  %s\n' "$out"; else say "  (rfkill unavailable or no kill switches — not proof of an enabled radio)"; fi
}

collect_iw() {
  say "iw:"
  local out
  out="$(run_tool iw dev 2>/dev/null | sed 's/^/  /')"
  [ -n "$out" ] && printf '%s\n' "$out" || say "  (no nl80211 device reported by iw, or iw absent)"
  out="$(run_tool iw reg get 2>/dev/null | sed 's/^/  /')"
  [ -n "$out" ] && printf '%s\n' "$out" || say "  (regulatory state unavailable)"
}

pick_ifname() {
  local n
  for n in $IFNAME_CANDIDATES; do
    [ -e "$(abs "/sys/class/net/$n")" ] && { printf '%s' "$n"; return 0; }
  done
  # Fall back to any netdev that the kernel marks wireless.
  local d
  for d in "$(abs /sys/class/net)"/*; do
    [ -e "$d" ] || continue
    if [ -d "$d/wireless" ] || [ -L "$d/phy80211" ]; then basename "$d"; return 0; fi
  done
  return 1
}

association_state() {
  # Prints: associated|disconnected|unknown  <ip>  <detail>
  local ifn="$1"
  if [ -z "$ifn" ]; then printf 'unknown - none'; return 0; fi
  local nmstate="" ip=""
  nmstate="$(run_tool nmcli -t -f GENERAL.STATE device show "$ifn" 2>/dev/null | cut -d: -f2)"
  ip="$(run_tool ip -4 -o addr show dev "$ifn" 2>/dev/null | awk '{print $4}' | head -1)"
  if [ "$nmstate" = "100 (connected)" ] || [ "$nmstate" = "100" ] || [ -n "$ip" ]; then
    printf 'associated %s NetworkManager=%s' "${ip:-none}" "${nmstate:-n/a}"
  else
    printf 'disconnected %s NetworkManager=%s' "${ip:-none}" "${nmstate:-n/a}"
  fi
}

# ---------------------------------------------------------------------------
# verdict — pure function of the collected evidence
# ---------------------------------------------------------------------------
verdict() {
  local ifn="$1" modules_ok="$2" fw_found="$3" wpa_ok="$4"
  local assoc; assoc="$(association_state "$ifn")"
  if [ "${assoc%% *}" = "associated" ]; then
    printf 'ASSOCIATED %s\n' "$assoc"
    printf 'meaning: a real association with an IPv4 address was observed on %s — the\n' "$ifn"
    printf 'meaning: owner must still confirm the *owner* test (a real page load) before this\n'
    printf 'meaning: is recorded as VERIFIED_ON_S10PLUS.\n'
    return 0
  fi
  if [ "$modules_ok" = "0" ]; then
    printf 'BLOCKED_DRIVER — no Wi-Fi driver module is bound (no wireless netdev, no matching module)\n'
  elif [ "$fw_found" = "0" ]; then
    printf 'BLOCKED_FIRMWARE — a Wi-Fi netdev/driver may exist but no candidate firmware blob is present\n'
  elif [ "$wpa_ok" = "0" ]; then
    printf 'BLOCKED_EXTERNAL_RESOURCE — no wpa_supplicant on this image: nothing can associate\n'
  elif [ -n "$ifn" ]; then
    printf 'BLOCKED_HARDWARE — wireless netdev %s exists with firmware present but has not associated\n' "$ifn"
  else
    printf 'BLOCKED_HARDWARE — no wireless netdev was created by the kernel\n'
  fi
  printf 'meaning: NOT a working-Wi-Fi claim. Terminal state stays NEEDS_OWNER_TEST until an\n'
  printf 'meaning: association + page load is observed on the physical S10+.\n'
  return 0
}

do_status() {
  local json="${1:-}"
  say "nuxel-wifi-diag — device=beyond2lte (SM-G975F)"
  say "NOTE: docs/wifi-bcm4390-status.md describes the Pixel BCM4390 and does NOT apply here."
  hdr "host"
  say "uname: $(run_tool uname -a 2>/dev/null || uname -a)"
  say "root_prefix: $ROOT"
  hdr "netdevices"
  collect_netdevs
  IFNAME="$(pick_ifname || true)"
  say "selected_wifi_ifname: ${IFNAME:-<none>}"
  hdr "driver modules"
  collect_modules
  hdr "firmware"
  collect_firmware
  hdr "kernel messages"
  collect_dmesg
  hdr "supplicant"
  collect_supplicant
  hdr "network manager"
  collect_nm
  hdr "rfkill"
  collect_rfkill
  hdr "nl80211 / regulatory"
  collect_iw

  # Derived evidence for the verdict.
  local modules_ok=0 m
  if [ -r "$(abs /proc/modules)" ]; then
    for m in "${MODULE_CANDIDATES[@]}"; do
      grep -q "^$m " "$(abs /proc/modules)" && modules_ok=1
    done
  fi
  local wireless_netdev=0
  [ -n "${IFNAME:-}" ] && wireless_netdev=1
  [ "$wireless_netdev" = "1" ] && modules_ok=1
  local wpa_ok=0
  { command -v wpa_supplicant >/dev/null 2>&1 || [ -x "$ROOT/usr/sbin/wpa_supplicant" ]; } && wpa_ok=1
  : "${FW_FOUND:=0}"; [ -z "${FW_FOUND:-}" ] && FW_FOUND=0

  hdr "verdict"
  local v; v="$(verdict "${IFNAME:-}" "$modules_ok" "$FW_FOUND" "$wpa_ok")"
  printf '%s\n' "$v" | grep -v '^meaning:' | sed 's/^/  /'
  printf '%s\n' "$v" | grep '^meaning:' | sed 's/^meaning: /  /'

  if [ "$json" = "--json" ]; then
    local state; state="$(printf '%s' "$v" | head -1 | cut -d' ' -f1)"
    printf '{"tool":"nuxel-wifi-diag","device":"beyond2lte","ifname":"%s","state":"%s","modules_ok":%s,"firmware_found":%s,"supplicant":%s,"associated":%s,"root":"%s"}\n' \
      "$(json_escape "${IFNAME:-}")" "$(json_escape "$state")" "$modules_ok" "$FW_FOUND" "$wpa_ok" \
      "$([ "${v%% *}" = ASSOCIATED ] && echo true || echo false)" "$(json_escape "$ROOT")"
  fi
  return 0
}

do_firmware() { collect_firmware; }

cmd_scan() {
  local out
  if have_tool nmcli; then
    say "# nmcli device wifi list"
    run_tool nmcli -f SSID,SIGNAL,SECURITY,CHAN device wifi list 2>&1 | sed 's/^/  /'
    return 0
  fi
  if have_tool iw; then
    local IFNAME; IFNAME="$(pick_ifname || true)"
    [ -z "$IFNAME" ] && { say "no wireless netdev: cannot scan"; return 1; }
    say "# iw dev $IFNAME scan"
    run_tool iw dev "$IFNAME" scan 2>&1 | sed 's/^/  /'
    return 0
  fi
  say "no scanning tool available (nmcli/iw absent); this is reported, not guessed"
  return 1
}

cmd_connect() {
  local ssid="${1:-}"
  [ -z "$ssid" ] && { say "usage: $SELF connect <SSID>"; return 2; }
  if ! have_tool nmcli; then
    say "nmcli is absent: association cannot be attempted from this image"
    say "owner path: docs/beta-finalization/manual-proof/04-wifi.md"
    return 1
  fi
  # --ask reads the PSK from the terminal; it is never written by this tool.
  run_tool nmcli --ask device wifi connect "$ssid"
  local rc=$?
  say "connect rc=$rc"
  local IFNAME; IFNAME="$(pick_ifname || true)"
  say "association state: $(association_state "${IFNAME:-}")"
  return $rc
}

cmd_disconnect() {
  local IFNAME; IFNAME="$(pick_ifname || true)"
  [ -z "$IFNAME" ] && { say "no wireless netdev"; return 1; }
  if have_tool nmcli; then run_tool nmcli device disconnect "$IFNAME"; return $?; fi
  say "nmcli absent"; return 1
}

cmd_regdom() {
  local cc="${1:-}"
  if [ -z "$cc" ]; then
    run_tool iw reg get 2>/dev/null | sed -n '1,12p'
    say "persistent option: add cfg80211.ieee80211_regdom=<CC> to the kernel cmdline"
    say "  (kernel cmdline changes are NOT applied by this tool — no partition is touched)"
    return 0
  fi
  case "$cc" in [A-Z][A-Z]|00) ;; *) say "country code must be an ISO-3166 alpha-2 code or 00"; return 2 ;; esac
  if ! have_tool iw; then say "iw absent: cannot set the regulatory domain at runtime"; return 1; fi
  run_tool iw reg set "$cc" && say "regulatory domain set to $cc (runtime only; not persistent)"
}

cmd_report() {
  local json="${1:-}"
  local dir; dir="$(dirname "$(abs "$EVIDENCE_LOG")")"
  mkdir -p "$dir" 2>/dev/null || true
  local out; out="$(do_status "$json")"
  printf '%s\n' "$out" >> "$(abs "$EVIDENCE_LOG")" 2>/dev/null || true
  say "evidence appended to $EVIDENCE_LOG (device root: $ROOT)"
  printf '%s\n' "$out" | sed -n '/== verdict ==/,$p'
}

cmd_selftest() {
  local fx="${NUXEL_WIFI_FIXTURES:-$(dirname "$SELF_PATH")/tests/fixtures-p3}"
  local fail=0 n
  if [ ! -d "$fx" ]; then
    say "FAIL fixtures directory not found: $fx"
    return 1
  fi
  for n in "$fx"/wifi-*/; do
    [ -d "$n" ] || continue
    local name exp got
    name="$(basename "$n")"
    exp="$(cat "$n/EXPECTED" 2>/dev/null || echo '')"
    got="$(NUXEL_DIAG_ROOT="$n" NUXEL_DIAG_NO_SYSTEM=1 "$SELF_PATH" status 2>&1 | sed -n '/== verdict ==/,+1p' | sed -n '2p' | sed 's/^ *//' | cut -d' ' -f1)"
    if [ -z "$exp" ]; then say "SKIP $name (no EXPECTED)"; continue; fi
    if [ "$got" = "$exp" ]; then
      say "PASS $name verdict=$got"
    else
      say "FAIL $name expected=$exp got=${got:-<none>}"
      fail=$((fail+1))
    fi
  done
  say "== $fail failing fixture(s) =="
  return "$fail"
}

case "$CMD" in
  status)      do_status "${1:-}" ;;
  firmware)    do_firmware ;;
  scan)        cmd_scan ;;
  connect)     cmd_connect "${1:-}" ;;
  disconnect)  cmd_disconnect ;;
  regdom)      cmd_regdom "${1:-}" ;;
  report)      cmd_report "${1:-}" ;;
  selftest)    cmd_selftest ;;
  help|-h|--help) sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) say "unknown command: $CMD (try: $SELF help)"; exit 2 ;;
esac

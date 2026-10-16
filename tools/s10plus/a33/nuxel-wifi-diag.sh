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
#   nuxel-wifi-diag.sh mark              # record the pre-reboot association
#   nuxel-wifi-diag.sh compare           # judge reconnection after ONE normal reboot
#   nuxel-wifi-diag.sh fallback          # no-cellular-fallback audit (policy evidence)
#   nuxel-wifi-diag.sh settings-spec     # the native Network Settings feature set
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
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
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
  # A FAKED root is evidence about THAT root and nothing else. Without this rule
  # a fixture run on a developer laptop borrows the laptop's wpa_supplicant /
  # NetworkManager and reports the workstation's state as the device's - which is
  # exactly how a "no supplicant on this image" fixture once read as "supplicant
  # present". Host tools are used only when the caller opts in explicitly.
  if [ "$ROOT" != "/" ] && [ "${NUXEL_DIAG_ALLOW_HOST_TOOLS:-0}" != "1" ]; then return 127; fi
  command -v "$t" >/dev/null 2>&1 || return 127
  "$t" "$@"
}
have_tool() { run_tool "$1" --version >/dev/null 2>&1 || run_tool "$1" -v >/dev/null 2>&1; }

# tool_path NAME -> prints the path of a tool that may legitimately be used for
# this root (fake-root tools first, the host only for a real root), or nothing.
# Every path this tool REPORTS must come from here, so the report and the
# execution path can never disagree about which supplicant was found.
tool_path() {
  local t="$1" p
  for p in "$ROOT/usr/bin/$t" "$ROOT/bin/$t" "$ROOT/usr/sbin/$t" "$ROOT/sbin/$t"; do
    if [ "$ROOT" != "/" ] && [ -x "$p" ]; then printf '%s' "$p"; return 0; fi
  done
  if [ "${NUXEL_DIAG_NO_SYSTEM:-0}" = "1" ]; then return 1; fi
  if [ "$ROOT" != "/" ] && [ "${NUXEL_DIAG_ALLOW_HOST_TOOLS:-0}" != "1" ]; then return 1; fi
  command -v "$t" 2>/dev/null || return 1
}
supplicant_path() { tool_path wpa_supplicant; }

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
  local wpa; wpa="$(supplicant_path || true)"
  if [ -n "$wpa" ]; then
    say "  wpa_supplicant: $wpa ($("$wpa" -v 2>/dev/null | head -1))"
  else
    say "  wpa_supplicant: ABSENT (no Wi-Fi supplicant on this image — Wi-Fi cannot associate)"
  fi
  local iwd; iwd="$(tool_path iwd || true)"
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
# mark / compare — the reboot-reconnection evidence pair
#
# Wi-Fi is not "working" until it comes back BY ITSELF after an ordinary reboot
# (briq-03a acceptance). This pair is the evidence: mark records the association
# that exists now, compare re-reads it after exactly one normal reboot and
# refuses to judge at all when the boot id did not change (a mark/compare pair
# with no reboot in between proves nothing and is reported as invalid).
# ---------------------------------------------------------------------------
WIFI_STATE_DIR_DEFAULT="/var/lib/nuxel/wifi"
state_dir() { printf '%s' "$(abs "${NUXEL_WIFI_STATE_DIR:-$WIFI_STATE_DIR_DEFAULT}")"; }
# The two record paths can be overridden so an operator (or the offline tests)
# can judge a pair of EXISTING records without touching the live state:
#   nuxelctl wifi compare <before.json> <after.json>
before_path() { printf '%s' "${NUXEL_WIFI_BEFORE:-$(state_dir)/last-associated.json}"; }
after_path()  { printf '%s' "${NUXEL_WIFI_AFTER:-$(state_dir)/after-reboot.json}"; }

boot_id_now() {
  local b; b="$(cat "$(abs /proc/sys/kernel/random/boot_id)" 2>/dev/null)"
  [ -z "$b" ] && b="$(run_tool cat /proc/sys/kernel/random/boot_id 2>/dev/null)"
  printf '%s' "$b"
}

# Prints: ssid<TAB>bssid<TAB>ipv4<TAB>gw   (fields may be empty; never invented)
wifi_identity() {
  local ifn="$1" ssid="" bssid="" ip="" gw="" nm="" link=""
  [ -z "$ifn" ] && { printf '\t\t\t'; return 0; }
  ip="$(run_tool ip -4 -o addr show dev "$ifn" 2>/dev/null | awk '{print $4}' | head -1)"
  gw="$(run_tool ip -4 route show default dev "$ifn" 2>/dev/null | awk '{print $3}' | head -1)"
  nm="$(run_tool nmcli -t -f active,ssid,bssid,signal device wifi list 2>/dev/null | awk -F: '$1=="yes"{print; exit}')"
  if [ -n "$nm" ]; then
    ssid="$(printf '%s' "$nm" | cut -d: -f2 | sed 's/\\:/:/g')"
    bssid="$(printf '%s' "$nm" | cut -d: -f3-5 | sed 's/\\:/:/g')"
  fi
  if [ -z "$ssid" ]; then
    link="$(run_tool iw dev "$ifn" link 2>/dev/null)"
    if [ -n "$link" ]; then
      ssid="$(printf '%s\n' "$link" | sed -n 's/^[[:space:]]*SSID: //p' | head -1)"
      bssid="$(printf '%s\n' "$link" | sed -n 's/^[[:space:]]*Connected to \([0-9a-fA-F:]*\).*/\1/p' | head -1)"
    fi
  fi
  printf '%s\t%s\t%s\t%s' "$ssid" "$bssid" "$ip" "$gw"
}

write_assoc_json() {   # write_assoc_json <path> <ifname> <associated|disconnected> <ssid> <bssid> <ip> <gw>
  python3 - "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$(boot_id_now)" <<'PY'
import json,os,sys,time
path,ifn,state,ssid,bssid,ip,gw,bid = sys.argv[1:9]
os.makedirs(os.path.dirname(path), exist_ok=True)
doc = {"schema_version": 1, "device": "beyond2lte", "ifname": ifn, "state": state,
       "ssid": ssid or None, "bssid": bssid or None, "ipv4": ip or None, "gateway": gw or None,
       "boot_id": bid or None, "recorded_at": time.strftime("%FT%TZ", time.gmtime())}
with open(path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
print("assoc record written: %s state=%s ssid=%s ip=%s" % (path, state, ssid or "-", ip or "-"))
PY
}

cmd_mark() {
  local ifn; ifn="$(pick_ifname || true)"
  local dir; dir="$(state_dir)"; mkdir -p "$dir" 2>/dev/null || { say "cannot create $dir"; return 1; }
  local assoc; assoc="$(association_state "${ifn:-}")"
  local id ssid bssid ip gw
  id="$(wifi_identity "${ifn:-}")"
  IFS=$'\t' read -r ssid bssid ip gw <<<"$id"
  write_assoc_json "$(before_path)" "${ifn:-}" "${assoc%% *}" "$ssid" "$bssid" "$ip" "$gw"
  say "ifname: ${ifn:-<none>}  association: $assoc"
  say "next: ONE ordinary userspace reboot (never a bootloader mode), then run: nuxelctl wifi compare"
  return 0
}

cmd_compare_quiet() {   # prints PASS/FAIL/UNKNOWN/REFUSED, always rc=0
  local b a
  b="$(before_path)"; a="$(after_path)"
  [ -r "$b" ] && [ -r "$a" ] || { printf 'NO_MARKS'; return 0; }
  python3 - "$b" "$a" <<'PY'
import json,sys
b=json.load(open(sys.argv[1])); a=json.load(open(sys.argv[2]))
if b.get("boot_id") and a.get("boot_id") and b["boot_id"]==a["boot_id"]:
    print("REFUSED same boot_id — no reboot happened between mark and compare; the pair is invalid")
    sys.exit(0)
if b.get("state")!="associated" or not b.get("ssid"):
    print("INVALID the pre-reboot mark was taken while not associated (ssid=%s) — re-mark while connected" % (b.get("ssid") or "-"))
    sys.exit(0)
if a.get("state")!="associated" or not a.get("ssid"):
    print("FAIL after boot_id %s the radio is %s (was associated to %s before the reboot)"
          % ((a.get("boot_id") or "?")[:8], a.get("state") or "unknown", b.get("ssid")))
    sys.exit(0)
if a["ssid"]!=b["ssid"]:
    print("FAIL reconnected to a DIFFERENT network: before=%s after=%s" % (b["ssid"], a["ssid"]))
    sys.exit(0)
if not a.get("ipv4"):
    print("FAIL re-associated to %s but no IPv4 address was obtained" % a["ssid"])
    sys.exit(0)
if b.get("bssid") and a.get("bssid") and b["bssid"]!=a["bssid"]:
    print("PASS reconnected to %s, ip=%s (different BSSID %s -> %s: a roam, not a failure)"
          % (a["ssid"], a["ipv4"], b["bssid"], a["bssid"]))
    sys.exit(0)
print("PASS reconnected to %s after the reboot, ip=%s gw=%s" % (a["ssid"], a["ipv4"], a.get("gateway") or "-"))
PY
}

cmd_compare() {
  local pair_before="${1:-}" pair_after="${2:-}"
  if [ -n "$pair_before" ] && [ -n "$pair_after" ]; then
    # judge two EXISTING records: no live read, no record written
    NUXEL_WIFI_BEFORE="$pair_before" NUXEL_WIFI_AFTER="$pair_after" cmd_compare_quiet
    return $?
  fi
  local b; b="$(before_path)"
  if [ ! -r "$b" ]; then
    say "no pre-reboot mark at $b: run 'nuxelctl wifi mark' BEFORE the reboot"; return 2
  fi
  local pdfn; pdfn="$(pick_ifname || true)"
  local assoc; assoc="$(association_state "${pdfn:-}")"
  local id ssid bssid ip gw
  id="$(wifi_identity "${pdfn:-}")"
  IFS=$'\t' read -r ssid bssid ip gw <<<"$id"
  write_assoc_json "$(after_path)" "${pdfn:-}" "${assoc%% *}" "$ssid" "$bssid" "$ip" "$gw" >/dev/null
  local verdict; verdict="$(cmd_compare_quiet)"
  hdr "reconnection across a normal reboot"
  say "$verdict"
  say "record this verdict in docs/beta-finalization/manual-proof/04-wifi.md (area 4)."
  case "$verdict" in PASS*) return 0 ;; FAIL*) return 1 ;; *) return 2 ;; esac
}

# ---------------------------------------------------------------------------
# fallback — the no-cellular-fallback audit
#
# The mission requires that Wi-Fi work must not silently be propped up by mobile
# data. This audit is POLICY EVIDENCE only: it looks for a NetworkManager profile
# that could bring up a cellular interface automatically. It never claims the
# modem works — on this device the Shannon LTE modem has no upstream
# ModemManager plugin support (briq-08i), so a cellular profile appearing at all
# is a finding for the owner, not a working fallback.
# ---------------------------------------------------------------------------
cmd_fallback() {
  local dir; dir="$(abs /etc/NetworkManager/system-connections)"
  local n=0 hits="" f t ac
  hdr "no-cellular-fallback audit"
  say "profile dir: ${dir#"$ROOT"}"
  if [ -d "$dir" ]; then
    for f in "$dir"/*; do
      [ -f "$f" ] || continue
      n=$((n+1))
      t="$(sed -n 's/^type=//p' "$f" 2>/dev/null | head -1)"
      ac="$(sed -n 's/^autoconnect=//p' "$f" 2>/dev/null | head -1)"
      [ -n "$t" ] || t="wifi"
      if [ "$t" = "gsm" ] || [ "$t" = "cdma" ]; then
        hits="$hits $(basename "$f")[type=$t autoconnect=${ac:-default}]"
      fi
    done
  else
    say "(no profile directory on this root: user-state profiles are not part of the image)"
  fi
  say "profiles_scanned: $n"
  if [ -n "$hits" ]; then
    say "CELLULAR_FALLBACK=present — review these profiles with the owner:$hits"
    say "note: presence is a policy finding, NOT proof that the modem can associate"
    say "      (Shannon LTE has no upstream ModemManager plugin on this kernel)"
    return 1
  fi
  say "CELLULAR_FALLBACK=absent — no gsm/cdma profile can auto-connect on this root"
  say "behavioural rule (owner test, area 4): with Wi-Fi associated, disable the AP"
  say "  and confirm no mobile-data interface takes over the default route:"
  say "    ip -4 route show default   # must lose the wlan default, gain no wwan/rmnet one"
  return 0
}

# ---------------------------------------------------------------------------
# settings-spec — the native Network Settings feature set (bg-06d append point)
# ---------------------------------------------------------------------------
cmd_settings_spec() {
  # Three candidates, in order: an explicit override, the installed device copy,
  # the repository copy. The first readable one wins; none of them is guessed.
  local cands=(
    "${NUXEL_NETWORK_SETTINGS_SPEC:-}"
    "/etc/nuxel/network/nuxel-network-settings.spec.json"
    "$SELF_DIR/../../../configs/networkmanager/nuxel-network-settings.spec.json"
  )
  local f="" p="" c
  for c in "${cands[@]}"; do
    [ -n "$c" ] || continue
    if [ -r "$c" ]; then f="$c"; p="$c"; break; fi
    if [ -r "$(abs "$c")" ]; then f="$c"; p="$(abs "$c")"; break; fi
  done
  [ -n "$f" ] || f="configs/networkmanager/nuxel-network-settings.spec.json"
  hdr "native Network Settings feature set"
  if [ -n "$p" ] && [ -r "$p" ]; then
    say "spec: $p"
    python3 - "$p" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
for sec in d.get("sections", []):
    print("  %-14s %-10s %s" % (sec.get("id"), sec.get("status", "?"), sec.get("title", "")))
print("  pages=%d  coordinator=%s" % (len(d.get("sections", [])), d.get("coordinator", "?")))
PY
  else
    say "spec not found at $f (the feature list below is the repository copy)"
  fi
  say "owner-facing page: Settings -> Network. Renderer owner: briq-06d"
  say "read API: nuxelctl wifi status --json | scan | fallback | mark/compare"
  return 0
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
  supplicant_path >/dev/null 2>&1 && wpa_ok=1
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
  mark)        cmd_mark ;;
  compare)     cmd_compare "${1:-}" "${2:-}" ;;
  fallback)    cmd_fallback ;;
  settings-spec) cmd_settings_spec ;;
  report)      cmd_report "${1:-}" ;;
  selftest)    cmd_selftest ;;
  help|-h|--help) sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) say "unknown command: $CMD (try: $SELF help)"; exit 2 ;;
esac

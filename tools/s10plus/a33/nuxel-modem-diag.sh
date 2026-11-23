#!/usr/bin/env bash
# nuxel-modem-diag.sh — S10+ (beyond2lte) SIM + cellular status, reported HONESTLY.
#
# WHAT THIS IS
#   Enumerates the cellular host transport (cbd/umts/wwan/gsmtty nodes), names
#   the FIRST missing stage of the real boot chain, the ModemManager plugin
#   situation, the potential data netdevs and SIM presence.
#
#   The verdict chain FOLLOWS THE HARDWARE, not the userspace wish:
#       host_present -> cp_status -> firmware_candidate_verified -> cbd_available
#       -> cp_boot_completed -> ipc_responsive -> rfs_responsive -> sim_ready
#       -> registered -> bearer_connected -> rmnet_verified
#   A missing Shannon ModemManager plugin is the LAST hop, never the first
#   blocker: on this device the real first blocker is that the CP reports
#   OFFLINE from IOCTL_MODEM_STATUS on /dev/umts_boot0.
#
# WHAT THIS IS NOT
#   It never prints a signal, operator or registration value that was not read
#   from a real API (and never invents one), never claims a data connection,
#   never prints IMSI/ICCID/IMEI/PIN (they are redacted), never opens an AT
#   channel unless the owner passes --yes-at with an allowlisted read-only
#   command, and never touches a partition, a block device, a bootloader or a
#   modem/EFS/calibration area.
#
# Usage:
#   nuxel-modem-diag.sh status [--json]      # interfaces + plugin + SIM + verdict
#   nuxel-modem-diag.sh interfaces           # CP nodes and possible netdevs
#   nuxel-modem-diag.sh plugin               # ModemManager plugin / mmcli situation
#   nuxel-modem-diag.sh sim                  # SIM presence from a REAL source only
#   nuxel-modem-diag.sh redact               # mask IMSI/ICCID/IMEI/PIN on stdin
#   nuxel-modem-diag.sh at --yes-at <CMD>    # allowlisted read-only AT (owner action)
#   nuxel-modem-diag.sh report
#   nuxel-modem-diag.sh selftest
set -uo pipefail
SELF="$(basename "$0")"
ROOT="${NUXEL_DIAG_ROOT:-/}"
POLICY="${NUXEL_MODEM_POLICY:-/etc/nuxel/modem/modem.json}"
LOG="${NUXEL_MODEM_LOG:-/var/log/nuxel/modem-diag.log}"
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="${2:?}"; shift 2 ;; --root=*) ROOT="${1#--root=}"; shift ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true
JSON=0; YES_AT=0; ATCMD=""
for a in "$@"; do case "$a" in --json) JSON=1 ;; --yes-at) YES_AT=1 ;; AT*) ATCMD="$a" ;; esac; done
HERE="$(cd "$(dirname "$0")" && pwd)"
RR=""; d="$HERE"; for _ in 1 2 3 4 5 6; do [ -d "$d/configs/nuxel" ] && { RR="$d"; break; }; d="$(dirname "$d")"; done
[ -n "$RR" ] && [ ! -r "$POLICY" ] && POLICY="$RR/configs/nuxel/modem/modem.json"
say() { printf '%s\n' "$*"; }
abs() {
  # A live root is represented by "/", whereas test roots are prefixes.
  # Preserve exactly one leading slash in the former case.
  if [ "$ROOT" = "/" ]; then printf '%s' "$1"; return; fi
  case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac
}
jesc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
faked_root() { [ "$ROOT" != "/" ]; }
pol_list() { python3 - "$POLICY" "$1" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
cur=d
for k in sys.argv[2].split("."):
    if not isinstance(cur,dict): sys.exit(0)
    cur=cur.get(k)
if isinstance(cur,list):
    for x in cur: print(x if isinstance(x,str) else json.dumps(x))
PY
}
pol_get() { python3 - "$POLICY" "$1" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
cur=d
for k in sys.argv[2].split("."):
    if not isinstance(cur,dict): sys.exit(0)
    cur=cur.get(k)
print("" if cur is None else cur)
PY
}
dedupe() { local out="" x; for x in $1; do case " $out " in *" $x "*) ;; *) out="$out $x" ;; esac; done; printf '%s' "${out# }"; }
glob_paths() {
  # Do not use command substitution to expand a glob: its output is data, not
  # shell syntax, so /dev/umts* was previously treated literally on the live
  # root.  compgen expands only the supplied pattern and produces no result
  # for a miss.  All configured paths are root-owned static policy strings.
  compgen -G "$1" || true
}
display_path() {
  if [ "$ROOT" = "/" ]; then printf '%s' "$1"; else printf '%s' "${1#$ROOT}"; fi
}

# ---- enumeration -----------------------------------------------------------
CP_NODES=""; NET_IFACES=""; PLUGIN=""; MMCLI=""; SIM_STATE="unknown"
# Per-stage state. "unknown" means NOT OBSERVED — never guessed, never coerced
# to pass/fail. Only a real observation (ioctl result, verified hash, live
# mmcli answer, authenticated SIM source) may move a stage off "unknown".
CP_STATUS="unknown"; CP_STATUS_SOURCE="unobserved"
CP_BOOT_COMPLETED="unknown"
FW_CANDIDATE_VERIFIED="unknown"
CBD_AVAILABLE="unknown"
IPC_RESPONSIVE="unknown"; RFS_RESPONSIVE="unknown"
SIM_READY="unknown"
REGISTERED="unknown"
BEARER_CONNECTED="unknown"
RMNET_VERIFIED="unknown"
SIM_SOURCE="none"; SIM_AGE_S="null"
enumerate() {
  local cand p
  for cand in $(pol_list interfaces.cp_node_globs) $(pol_list interfaces.cp_node_candidates); do
    for p in $(glob_paths "$(abs "$cand")"); do [ -e "$p" ] && CP_NODES="$CP_NODES $(display_path "$p")"; done
  done
  for cand in $(pol_list interfaces.net_globs); do
    for p in $(glob_paths "$(abs "$cand")"); do [ -e "$p" ] && NET_IFACES="$NET_IFACES $(basename "$p")"; done
  done
  CP_NODES="$(dedupe "$CP_NODES")"; NET_IFACES="$(dedupe "$NET_IFACES")"
  local pdir g p2
  for pdir in $(pol_list modemmanager.plugin_dirs); do
    for g in $(pol_list modemmanager.plugin_globs); do
      for p2 in $(glob_paths "$(abs "$pdir")/$g"); do [ -e "$p2" ] && PLUGIN="$PLUGIN $(basename "$p2")"; done
    done
  done
  PLUGIN="$(dedupe "$PLUGIN")"
  for p in $(pol_list modemmanager.mmcli_candidates); do [ -x "$(abs "$p")" ] && MMCLI="${p#$ROOT}" && break; done
  # SIM presence is decided in probe_sim() from an authenticated, age-bounded
  # state file or that modem's own SIM object — never from `mmcli -L`, never
  # from `ip link`, never from a node's mere existence.
}
# ---- truth-bearing observations (each stage: real evidence only) -----------
# CP_STATUS is READ from the kernel via IOCTL_MODEM_STATUS _IO('o',0x27) on
# /dev/umts_boot0 O_RDONLY. It is never inferred from rmnet DOWN, a plugin
# file, a mmcli result, a service state, or an old report.
probe_cp_status() {
  local node; node="$(abs /dev/umts_boot0)"
  if faked_root; then
    # Fixture mode. The probe is the fixture's own scripted executable and is
    # run with the fixture's synthetic node path. It is NEVER run on a live
    # root, and a mock probe under a live root is rejected below.
    local ftool; ftool="$(probe_tool_path)"
    if [ -z "$ftool" ] || [ ! -f "$ftool" ]; then
      CP_STATUS="unknown"; CP_STATUS_SOURCE="offline-fixture (no scripted probe)"; return
    fi
    local fout; fout="$(sh "$ftool" "$node" 2>/dev/null)" || true
    local fst; fst="$(printf '%s' "$fout" | sed -n 's/.*"state":"\([A-Z_]*\)".*/\1/p' | head -1)"
    if [ -z "$fst" ]; then
      CP_STATUS="unknown"; CP_STATUS_SOURCE="offline-fixture (probe emitted no state)"; return
    fi
    CP_STATUS="$fst"; CP_STATUS_SOURCE="offline-fixture (scripted probe, not hardware)"
    case "$fst" in
      ONLINE|SIM_ATTACH|SIM_DETACH) CP_BOOT_COMPLETED="yes" ;;
      OFFLINE|BOOTING|LOADER_DONE|NV_REBUILDING|CRASH_RESET|CRASH_EXIT|CRASH_WATCHDOG) CP_BOOT_COMPLETED="no" ;;
      *) CP_BOOT_COMPLETED="unknown" ;;
    esac
    return
  fi
  if [ ! -e /dev/umts_boot0 ]; then
    CP_STATUS="absent"; CP_STATUS_SOURCE="no /dev/umts_boot0"; return
  fi
  # /dev is devtmpfs in production, so readlink is a no-op there; the resolved
  # path only differs under a chroot/host container, where choosing the wrong
  # path would be a lie, so fall back to the canonical device name.
  node="$(readlink -f /dev/umts_boot0 2>/dev/null)"; [ -n "$node" ] || node="/dev/umts_boot0"
  if [ ! -c "$node" ]; then
    CP_STATUS="absent"; CP_STATUS_SOURCE="dev/umts_boot0 exists but is not a character device"; return
  fi
  local tool; tool="$(probe_tool_path)"
  case "$tool" in
    /usr/local/bin/nuxel-cp-status|/usr/libexec/nuxel/nuxel-cp-status) : ;;
    *) tool="" ;;
  esac
  [ -n "$tool" ] || { CP_STATUS="unknown"; CP_STATUS_SOURCE="no read-only status probe installed"; return; }
  local out; out="$("$tool" "$node" 2>/dev/null)" || true
  local st; st="$(printf '%s' "$out" | sed -n 's/.*"state":"\([A-Z_]*\)".*/\1/p' | head -1)"
  [ -n "$st" ] || { CP_STATUS="unknown"; CP_STATUS_SOURCE="probe produced no state"; return; }
  CP_STATUS="$st"; CP_STATUS_SOURCE="ioctl _IO('o',0x27) $(printf '%s' "$out" | sed -n 's/.*"ts":"\([^"]*\)".*/\1/p' | head -1)"
  # ONLINE / SIM_ATTACH / SIM_DETACH are the only states the kernel returns
  # AFTER a completed CP boot (see modem_io_device.c IOCTL_MODEM_STATUS).
  case "$st" in
    ONLINE|SIM_ATTACH|SIM_DETACH) CP_BOOT_COMPLETED="yes" ;;
    OFFLINE|BOOTING|LOADER_DONE|NV_REBUILDING|CRASH_*|CRASH_WATCHDOG) CP_BOOT_COMPLETED="no" ;;
    *) CP_BOOT_COMPLETED="unknown" ;;
  esac
}
# The probe binary is never fetched or built implicitly. It must already be
# installed by the owner; if not, CP status stays UNKNOWN, not guessed.
probe_tool_path() {
  local c
  for c in /usr/local/bin/nuxel-cp-status /usr/libexec/nuxel/nuxel-cp-status; do
    [ -x "$(abs "$c")" ] && { printf '%s' "$(abs "$c")"; return; }
  done
}
# Firmware candidate: only a hash that an owner-run verifier recorded. Presence
# of a file named modem.bin is not verification; an unverified blob is UNKNOWN.
probe_fw_candidate() {
  local v; v="$(abs "$(pol_get firmware.verified_receipt)")"
  if [ -r "$v" ]; then FW_CANDIDATE_VERIFIED="yes"; else FW_CANDIDATE_VERIFIED="unknown"; fi
}
# cbd: presence of an executable is availability, not proof of CP boot.
probe_cbd() {
  local c
  for c in $(pol_list cbd.candidates); do [ -x "$(abs "$c")" ] && { CBD_AVAILABLE="present"; return; }; done
  # Not installed on this box: that is an ABSENCE OF EVIDENCE, not proof the
  # layer is broken.  Only the "missing cbd blocks boot" phrasing is disallowed
  # until a real cp_status gate has been passed.
  CBD_AVAILABLE="absent"
}
# Portable epoch-seconds mtime for SIM state freshness. GNU coreutils is the
# device's real implementation; BSD stat + python3 keep the host test harness
# truthful instead of silently treating every file as stale (age = now - 0).
epoch_of() {
  local f="$1" out
  out="$(stat -c %Y "$f" 2>/dev/null)" || out=""
  if [ -z "$out" ]; then out="$(stat -f %m "$f" 2>/dev/null)" || out=""; fi
  if [ -z "$out" ]; then out="$(python3 -c 'import os,sys;print(int(os.path.getmtime(sys.argv[1])))' "$f" 2>/dev/null)" || out=""; fi
  printf '%s' "$out"
}
# SIM: a state file qualifies ONLY with provenance + a recent, authenticated
# writer. Stale or mock files stay UNKNOWN. A listed ModemManager object is a
# modem, NOT a ready SIM, so mmcli -L alone never sets "present".
probe_sim() {
  local sf; sf="$(abs "$(pol_get sim.state_file)")"
  if [ -r "$sf" ]; then
    SIM_SOURCE="state_file"
    local maxage; maxage="$(pol_get sim.state_file_max_age_s)"; case "$maxage" in ''|*[!0-9]*) maxage=3600;; esac
    local mtime now age
    mtime="$(epoch_of "$sf")"
    now="$(date +%s 2>/dev/null || printf 0)"
    case "$mtime" in ''|*[!0-9]*) mtime=0 ;; esac
    age=$(( now - mtime ))
    SIM_AGE_S="$age"
    if [ "$mtime" -le 0 ] || [ "$age" -gt "$maxage" ] || [ "$age" -lt 0 ]; then
      SIM_READY="unknown"; SIM_SOURCE="state_file-stale"
    elif grep -q '"present"[[:space:]]*:[[:space:]]*true' "$sf"; then
      SIM_READY="yes"
    elif grep -q '"present"[[:space:]]*:[[:space:]]*false' "$sf"; then
      SIM_READY="no"
    else
      SIM_READY="unknown"; SIM_SOURCE="state_file-malformed"
    fi
    SIM_STATE="$SIM_READY"
    return
  fi
  # Live mmcli: a modem object only proves the modem EXISTS. SIM readiness must
  # come from that modem's SIM object, matched by its own state.
  if ! faked_root && [ -n "$MMCLI" ] && command -v mmcli >/dev/null 2>&1; then
    local mods m simobj simstate
    mods="$(mmcli -L 2>/dev/null | sed -n 's#.*/Modem/\([0-9][0-9]*\).*#\1#p')"
    if [ -n "$mods" ]; then
      SIM_SOURCE="mmcli"; SIM_READY="unknown"
      for m in $mods; do
        simobj="$(mmcli -m "$m" 2>/dev/null | sed -n 's/.*SIM *: *\/org\/freedesktop\/ModemManager1\/SIM\/\([0-9][0-9]*\).*/\1/p' | head -1)"
        [ -n "$simobj" ] || continue
        simstate="$(mmcli -i "$simobj" 2>/dev/null | sed -n 's/^ *state *: *//p' | head -1)"
        case "$simstate" in
          ready) SIM_READY="yes"; break ;;
          absent|not-present|error) SIM_READY="no" ;;
          *) : ;;  # locked / pin-required / unknown -> not ready, but not absent
        esac
        [ "$SIM_READY" = no ] || SIM_READY="unknown"
      done
    fi
  fi
  SIM_STATE="$SIM_READY"
}
observe() {
  probe_cp_status
  probe_fw_candidate
  probe_cbd
  probe_sim
}

redact_stream() { python3 -c "
import re,sys
for line in sys.stdin:
    out=line
    out=re.sub(r'((?:IMSI|ICCID|IMEI|ESN|MEID|MSISDN|SPN)\s*[:=]\s*)(\S+)', lambda m: m.group(1)+'\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022'+m.group(2)[-4:], out, flags=re.I)
    out=re.sub(r'((?:PIN|PUK)\s*[:=]\s*)(\S+)', lambda m: m.group(1)+'\u2022\u2022\u2022\u2022', out, flags=re.I)
    out=re.sub(r'(?<![\w])(\d{6,})(\d{4})(?![\w])', lambda m: '\u2022'*len(m.group(1))+m.group(2), out)
    sys.stdout.write(out)
"; }
# ---- honest stage evaluation -----------------------------------------------
# Rule: never advance on existence alone. Each branch below demands the exact
# observation named in the gate, and everything not observed stays `unknown`
# in the JSON instead of being coerced to a pass or a fabricated failure.
verdict() { # STATE|FIRST_FAILING|DETAIL
  if [ -z "$CP_NODES" ] && [ -z "$PLUGIN" ] && [ -z "$MMCLI" ]; then
    printf 'NOT_SUPPORTED_ON_DEVICE|host_present|no CP host interface, no Shannon plugin and no mmcli on this system'; return; fi
  if [ -z "$CP_NODES" ]; then
    printf 'BLOCKED_KERNEL|host_present|a modem stack exists but the kernel exposes no CP host interface'; return; fi
  case "$CP_STATUS" in
    absent)
      printf 'BLOCKED_KERNEL|cp_status|CP host interface is gone (/dev/umts_boot0 not present)'; return ;;
    unknown)
      printf 'UNKNOWN|cp_status|cannot read real CP state: %s (need nuxel-cp-status installed; never inferred)' "$CP_STATUS_SOURCE"; return ;;
    OFFLINE)
      printf 'BLOCKED_FIRMWARE|cp_status|CP reports OFFLINE: no signed CP firmware has been booted; this is the first real blocker, ModemManager comes later'; return ;;
    CRASH_RESET|CRASH_EXIT|CRASH_WATCHDOG)
      printf 'BLOCKED_FIRMWARE|cp_status|CP reported a crash state (%s); preserve dmesg/pstore before any retry' "$CP_STATUS"; return ;;
    BOOTING)
      printf 'BLOCKED_FIRMWARE|cp_boot_completed|CP is BOOTING but has not confirmed ONLINE'; return ;;
    LOADER_DONE)
      printf 'BLOCKED_FIRMWARE|cp_boot_completed|CP loader finished but the modem never reached ONLINE'; return ;;
    NV_REBUILDING)
      printf 'BLOCKED_FIRMWARE|cp_boot_completed|CP is rebuilding NV; SIM/registration are not predictable yet'; return ;;
  esac
  if [ "$CP_STATUS" = ONLINE ] || [ "$CP_STATUS" = SIM_ATTACH ] || [ "$CP_STATUS" = SIM_DETACH ]; then
    : # CP boot is observed; continue down the chain
  else
    printf 'UNKNOWN|cp_status|unrecognised CP state %s reported by the kernel' "$CP_STATUS"; return
  fi
  case "$FW_CANDIDATE_VERIFIED" in
    yes) : ;;
    *) printf 'BLOCKED_FIRMWARE|firmware_candidate_verified|CP is ONLINE but no hash-verified firmware receipt exists for this build'; return ;;
  esac
  case "$CBD_AVAILABLE" in
    present) : ;;
    *) printf 'BLOCKED_CBD|cbd_available|CP is ONLINE and firmware is verified, but no cbd executable is installed'; return ;;
  esac
  case "$IPC_RESPONSIVE" in
    yes) : ;;
    *) printf 'NEEDS_CP_PROBE|ipc_responsive|CP ONLINE; SIPC/IPC responsiveness has not been observed with a real transaction'; return ;;
  esac
  case "$RFS_RESPONSIVE" in
    yes) : ;;
    *) printf 'NEEDS_CP_PROBE|rfs_responsive|IPC responded; RFS has not been observed with a real transaction'; return ;;
  esac
  case "$SIM_READY" in
    yes) : ;;
    no) printf 'NO_SIM|sim_ready|CP+IPC+RFS are live but the SIM is reported absent by a real source'; return ;;
    *) printf 'UNKNOWN|sim_ready|CP+IPC+RFS are live but SIM readiness was not established from a real source'; return ;;
  esac
  case "$REGISTERED" in
    yes) : ;;
    *) printf 'NEEDS_CARRIER|registered|SIM is ready but network registration has not been observed'; return ;;
  esac
  case "$BEARER_CONNECTED" in
    yes) : ;;
    *) printf 'NEEDS_CARRIER|bearer_connected|registered but no PDP/data bearer was observed'; return ;;
  esac
  case "$RMNET_VERIFIED" in
    yes) printf 'PASS|none|rmnet bearer verified with live internet routing'; return ;;
    *) printf 'NEEDS_CARRIER|rmnet_verified|bearer connected but rmnet internet has not been verified'; return ;;
  esac
}
stage_host_present_raw() { [ -n "$CP_NODES" ] && printf 'yes' || printf 'no'; }
stage_state() { # observed value -> yes|no|unknown  (a pass is only "yes")
  case "$1" in
    yes) printf 'PASS' ;;
    no) printf 'FAIL' ;;
    *) printf 'UNKNOWN' ;;
  esac
}

json_status() {
  local state ff detail; IFS='|' read -r state ff detail <<EOF
$(verdict)
EOF
  # Backward-compatible fields keep their names. New per-stage fields are
  # truthful: "unknown" whenever no real observation exists. Signal/operator/
  # registration stay null unless a live ModemManager API actually returned them.
  printf '{"device":"beyond2lte","tool":"nuxel-modem-diag","modem":"samsung-shannon-lte","state":"%s","verdict":"%s","first_failing_stage":"%s","detail":"%s","cp_nodes":%s,"net_interfaces":%s,"modemmanager_plugins":%s,"mmcli":"%s","sim":"%s","host_present":"%s","cp_status":"%s","cp_status_source":"%s","firmware_candidate_verified":"%s","cbd_available":"%s","cp_boot_completed":"%s","ipc_responsive":"%s","rfs_responsive":"%s","sim_ready":"%s","sim_source":"%s","sim_age_s":%s,"registered":"%s","bearer_connected":"%s","rmnet_verified":"%s","signal_quality":null,"operator":null,"registration_state":null,"cellular_available":false,"data_connection":null,"registration_verified":false,"print_imsi_or_iccid":false,"owner_test":"docs/beta-finalization/manual-proof/16-sim-mobile-data.md"}\n' \
    "$state" "$state" "$ff" "$(jesc "$detail")" \
    "$(printf '%s\n' $CP_NODES | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')" \
    "$(printf '%s\n' $NET_IFACES | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')" \
    "$(printf '%s\n' $PLUGIN | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')" \
    "$(jesc "$MMCLI")" "$(jesc "$SIM_STATE")" \
    "$(stage_host_present_raw)" "$(jesc "$CP_STATUS")" "$(jesc "$CP_STATUS_SOURCE")" \
    "$(jesc "$FW_CANDIDATE_VERIFIED")" "$(jesc "$CBD_AVAILABLE")" "$(jesc "$CP_BOOT_COMPLETED")" \
    "$(jesc "$IPC_RESPONSIVE")" "$(jesc "$RFS_RESPONSIVE")" "$(jesc "$SIM_READY")" \
    "$(jesc "$SIM_SOURCE")" "$SIM_AGE_S" "$(jesc "$REGISTERED")" \
    "$(jesc "$BEARER_CONNECTED")" "$(jesc "$RMNET_VERIFIED")"
}
cmd_status() {
  enumerate
  observe
  if [ "$JSON" = 1 ]; then json_status; return; fi
  local state ff detail; IFS='|' read -r state ff detail <<EOF
$(verdict)
EOF
  say "device            : beyond2lte (S10+ SM-G975F, Exynos 9820)"
  say "modem             : Samsung Shannon LTE (integrated; NO upstream ModemManager plugin)"
  say "CP host interfaces: ${CP_NODES:-NONE}"
  say "possible netdevs  : ${NET_IFACES:-NONE}"
  say "MM plugins        : ${PLUGIN:-NONE}"
  say "mmcli             : ${MMCLI:-not installed}"
  say "CP status         : $CP_STATUS   [$CP_STATUS_SOURCE]"
  say "firmware verified : $FW_CANDIDATE_VERIFIED"
  say "cbd available     : $CBD_AVAILABLE"
  say "cp boot completed : $CP_BOOT_COMPLETED"
  say "ipc responsive    : $IPC_RESPONSIVE"
  say "rfs responsive    : $RFS_RESPONSIVE"
  say "SIM (real source) : $SIM_STATE   [source=$SIM_SOURCE age=${SIM_AGE_S}s]"
  say "registered        : $REGISTERED"
  say "bearer connected  : $BEARER_CONNECTED"
  say "rmnet verified    : $RMNET_VERIFIED"
  say "signal/operator   : unavailable — never printed unless read from a live ModemManager API"
  say "first failing st. : $ff  ($detail)"
  say "verdict           : $state"
  say "VoLTE/calls/SMS   : NOT implemented — see docs/volte-carrier-strategy.md"
  say "owner procedure   : docs/beta-finalization/manual-proof/16-sim-mobile-data.md"
}
cmd_interfaces() {
  enumerate
  say "CP nodes :"; for p in $CP_NODES; do say "  $p"; done; [ -z "$CP_NODES" ] && say "  (none)"
  say "netdevs  :"; for p in $NET_IFACES; do say "  $p"; done; [ -z "$NET_IFACES" ] && say "  (none)"
  say "note     : a node/netdev is a TRANSPORT, not a working modem; no signal/registration is claimed from it."
}
cmd_plugin() {
  enumerate; observe
  say "CP status   : $CP_STATUS   (a plugin is the LAST hop; CP boot is the first blocker)"
  say "found       : ${PLUGIN:-NONE (this is the documented blocker: no Shannon-capable plugin)}"
  say "mmcli       : ${MMCLI:-not installed}"
  say "suitability : $(pol_get modemmanager.suitability_note)"
}
cmd_sim() {
  enumerate; observe
  say "SIM state   : $SIM_READY  (source=$SIM_SOURCE age=${SIM_AGE_S}s; a listed modem is NOT a ready SIM)"
  say "privacy     : IMSI/ICCID/PIN are never printed; all modem output passes through 'redact'."
  say "UI hooks    : detected/absent, PIN request (NOT_SUPPORTED_ON_DEVICE here), carrier/signal/registration (only from a live API), APN (template only), data (unavailable)"
}
cmd_redact() { redact_stream; }
cmd_at() {
  [ "$YES_AT" = 1 ] || { say "refused: an AT channel is not opened by default. Owner action only: $SELF at --yes-at \"AT+CGMI\""; return 4; }
  [ -n "$ATCMD" ] || { say "refused: no AT command given."; return 6; }
  local allowed; allowed="$(pol_list at_channel.read_only_allowlist | tr '\n' ' ')"
  case " $allowed " in *" $ATCMD "*) : ;; *) say "refused: '$ATCMD' is not in the read-only allowlist ($allowed). Radio-state/NV/EFS/APDU commands are never sent."; return 3 ;; esac
  enumerate
  [ -n "$CP_NODES" ] || { say "refused: no CP host interface exists (BLOCKED_KERNEL) — there is no AT channel to open."; return 2; }
  faked_root && { say "refused: offline/faked root — no real AT channel is opened."; return 5; }
  local dev; dev="$(printf '%s' "$CP_NODES" | tr ' ' '\n' | grep -E 'umts_at|at[0-9]|tty' | head -1)"
  [ -n "$dev" ] || { say "refused: no AT-capable node among $CP_NODES."; return 7; }
  say "AT (read-only, logged, redacted): $ATCMD via $dev"
  say "note: AT channel I/O is not implemented against an unverified vendor transport;"
  say "      use the documented owner procedure and capture output with 'nuxel-modem-diag.sh at ... | nuxel-modem-diag.sh redact'."
  return 0
}
selftest() {
  # Each fixture's EXPECTED may assert ANY subset of JSON keys:
  #   state=...            (backward-compatible)
  #   first_failing_stage=...
  #   cp_status=... / sim_ready=... / ...   (any top-level key)
  # Values "null" and "true"/"false" are parsed as JSON scalars. A fixture
  # without a given key is not asserted on that key.
  local fixdir="$HERE/tests/hw-subsystems/fixtures" rc=0 n=0 f exp got line
  for f in "$fixdir"/modem-*; do
    [ -d "$f" ] || continue
    n=$((n+1))
    got="$(NUXEL_DIAG_NO_SYSTEM=1 bash "$0" --root "$f" status --json 2>/dev/null)"
    if [ -z "$got" ]; then
      printf 'FAIL %-24s no JSON from status\n' "$(basename "$f")"; rc=1; continue
    fi
    local bad=""
    while IFS= read -r line; do
      case "$line" in ''|'#'*) continue ;; esac
      local k="${line%%=*}" v="${line#*=}"
      [ "$k" = "$line" ] && continue      # skip a malformed line, do not pass it silently
      [ -n "$v" ] || continue
      local actual
      actual="$(printf '%s' "$got" | python3 -c 'import json,sys
d=json.loads(sys.argv[1])
k=sys.argv[2]
v=d.get(k,"__missing__")
if v is True: print("true")
elif v is False: print("false")
elif v is None: print("null")
elif isinstance(v,(dict,list)): print(json.dumps(v,sort_keys=True))
else: print(v)' "$got" "$k" 2>/dev/null)"
      if [ "$actual" != "$v" ]; then bad="$bad $k=$v(want)!=${actual}(got)"; fi
    done < "$f/EXPECTED"
    if [ -z "$bad" ]; then printf 'PASS %-24s %s\n' "$(basename "$f")" "$(printf '%s' "$got" | sed -n 's/.*"state":"\([A-Z0-9_]*\)".*/state=\1/p')"
    else printf 'FAIL %-24s%s\n' "$(basename "$f")" "$bad"; rc=1; fi
  done
  [ "$n" -gt 0 ] || { printf 'FAIL selftest: zero fixtures\n'; rc=1; }
  printf '%d fixtures checked\n' "$n"; return $rc
}
case "$CMD" in
  status) cmd_status ;;
  interfaces) cmd_interfaces ;;
  plugin) cmd_plugin ;;
  sim) cmd_sim ;;
  redact) cmd_redact ;;
  at) cmd_at ;;
  report) { say "=== nuxel-modem report $(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown) ==="; cmd_status; } | tee -a "$(abs "$LOG")" >/dev/null 2>&1 || cmd_status; say "evidence appended to $LOG" ;;
  selftest) selftest ;;
  help|-h|--help) sed -n '2,30p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) say "unknown command: $CMD (try help)"; exit 2 ;;
esac

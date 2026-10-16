#!/usr/bin/env bash
# nuxel-modem-diag.sh — S10+ (beyond2lte) SIM + cellular status, reported HONESTLY.
#
# WHAT THIS IS
#   Enumerates the cellular host transport (cbd/umts/wwan/gsmtty nodes), the
#   ModemManager plugin situation, the potential data netdevs and SIM presence,
#   and names the FIRST missing stage. The default verdict for this device is
#   NOT_SUPPORTED_ON_DEVICE / BLOCKED_FIRMWARE because there is no upstream
#   ModemManager plugin for the Samsung Shannon LTE modem.
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
abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
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

# ---- enumeration -----------------------------------------------------------
CP_NODES=""; NET_IFACES=""; PLUGIN=""; MMCLI=""; SIM_STATE="unknown"
enumerate() {
  local cand p
  for cand in $(pol_list interfaces.cp_node_globs) $(pol_list interfaces.cp_node_candidates); do
    for p in $(abs "$cand"); do [ -e "$p" ] && CP_NODES="$CP_NODES ${p#$ROOT}"; done
  done
  for cand in $(pol_list interfaces.net_globs); do
    for p in $(abs "$cand"); do [ -e "$p" ] && NET_IFACES="$NET_IFACES $(basename "$p")"; done
  done
  CP_NODES="$(dedupe "$CP_NODES")"; NET_IFACES="$(dedupe "$NET_IFACES")"
  local pdir g p2
  for pdir in $(pol_list modemmanager.plugin_dirs); do
    for g in $(pol_list modemmanager.plugin_globs); do
      for p2 in "$(abs "$pdir")"/$g; do [ -e "$p2" ] && PLUGIN="$PLUGIN $(basename "$p2")"; done
    done
  done
  PLUGIN="$(dedupe "$PLUGIN")"
  for p in $(pol_list modemmanager.mmcli_candidates); do [ -x "$(abs "$p")" ] && MMCLI="${p#$ROOT}" && break; done
  # SIM presence: ONLY from a real source (state file written by a real run, or a live mmcli query)
  local sf; sf="$(abs "$(pol_get sim.state_file)")"
  if [ -r "$sf" ]; then
    if grep -q '"present"[[:space:]]*:[[:space:]]*true' "$sf"; then SIM_STATE="present"; else SIM_STATE="absent"; fi
  elif ! faked_root && [ -n "$MMCLI" ] && command -v mmcli >/dev/null 2>&1 && mmcli -L 2>/dev/null | grep -q '/Modem/'; then
    SIM_STATE="present"
  else
    for p in $(pol_list sim.sysfs_candidates); do [ -e "$(abs "$p")" ] && { SIM_STATE="unknown-maybe"; break; }; done
  fi
}
verdict() { # STATE|FIRST_FAILING|DETAIL
  if [ -z "$CP_NODES" ] && [ -z "$PLUGIN" ] && [ -z "$MMCLI" ]; then
    printf 'NOT_SUPPORTED_ON_DEVICE|host_transport|no CP host interface and no ModemManager plugin for the Samsung Shannon LTE modem'; return; fi
  if [ -z "$PLUGIN" ]; then
    printf 'BLOCKED_FIRMWARE|modemmanager_plugin|host transport present but the modem stack cannot talk to it: no Shannon-capable ModemManager plugin'; return; fi
  if [ -z "$CP_NODES" ]; then
    printf 'BLOCKED_KERNEL|host_transport|a modem-stack plugin exists but the kernel exposes no CP host interface'; return; fi
  if [ "$SIM_STATE" != present ]; then
    printf 'NO_SIM|sim|transport + plugin present but no SIM is reported by a real source (insert a SIM and re-check)'; return; fi
  printf 'NEEDS_OWNER_TEST|registration|transport + plugin + SIM present; registration/data are unproven and are only ever reported from a live API'
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
json_status() {
  local state ff detail; IFS='|' read -r state ff detail <<EOF
$(verdict)
EOF
  printf '{"device":"beyond2lte","tool":"nuxel-modem-diag","modem":"samsung-shannon-lte","state":"%s","verdict":"%s","first_failing_stage":"%s","detail":"%s","cp_nodes":%s,"net_interfaces":%s,"modemmanager_plugins":%s,"mmcli":"%s","sim":"%s","signal_quality":null,"operator":null,"registration_state":null,"cellular_available":false,"data_connection":null,"registration_verified":false,"print_imsi_or_iccid":false,"owner_test":"docs/beta-finalization/manual-proof/16-sim-mobile-data.md"}\n' \
    "$state" "$state" "$ff" "$(jesc "$detail")" \
    "$(printf '%s\n' $CP_NODES | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')" \
    "$(printf '%s\n' $NET_IFACES | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')" \
    "$(printf '%s\n' $PLUGIN | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')" \
    "$(jesc "$MMCLI")" "$(jesc "$SIM_STATE")"
}
cmd_status() {
  enumerate
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
  say "SIM (real source) : $SIM_STATE"
  say "signal/operator   : unavailable — never printed unless read from a live ModemManager API"
  say "data connection   : none (no supported modem stack)"
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
  enumerate
  say "plugin dirs : $(pol_list modemmanager.plugin_dirs | tr '\n' ' ')"
  say "found       : ${PLUGIN:-NONE (this is the documented blocker: no Shannon-capable plugin)}"
  say "mmcli       : ${MMCLI:-not installed}"
  say "suitability : $(pol_get modemmanager.suitability_note)"
}
cmd_sim() {
  enumerate
  say "SIM state   : $SIM_STATE  (source: $([ "$SIM_STATE" = present ] && echo 'real modem list / detection state file' || echo 'none — reported as unknown, never assumed') )"
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
  local fixdir="$HERE/tests/hw-subsystems/fixtures" rc=0 n=0 f exp got
  for f in "$fixdir"/modem-*; do
    [ -d "$f" ] || continue
    n=$((n+1)); exp="$(sed -n 's/^state=//p' "$f/EXPECTED" | head -1)"
    got="$(NUXEL_DIAG_NO_SYSTEM=1 bash "$0" --root "$f" status --json | sed -n 's/.*"state":"\([A-Z0-9_]*\)".*/\1/p' | head -1)"
    if [ "$exp" = "$got" ]; then printf 'PASS %-24s state=%s\n' "$(basename "$f")" "$got"
    else printf 'FAIL %-24s expected=%s got=%s\n' "$(basename "$f")" "$exp" "$got"; rc=1; fi
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

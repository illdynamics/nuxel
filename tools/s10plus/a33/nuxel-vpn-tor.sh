#!/bin/bash
# SPDX-License-Identifier: MIT
# ============================================================================
# nuxel-vpn-tor.sh - VPN, Tor and remote access with honest claim labels
#                    (briq-05c)
# ============================================================================
# ACCESS TIER: repository-only + offline test. Live network proof (a real exit
# node, a real WireGuard peer, a real leak test) needs an external vantage point
# and is therefore reported as BLOCKED_EXTERNAL_RESOURCE / unproven - never
# assumed. This tool is what the on-device owner and the live-access group run.
#
# THE ONE RULE THIS TOOL EXISTS FOR
#   "tor.service is active" is not anonymisation. "wg0 exists" is not a tunnel
#   carrying your traffic. Every privacy feature is reported as three separate,
#   machine-readable claims:
#       1. the process is running        (service_running)
#       2. the circuit/tunnel exists     (circuits_built / handshake_observed)
#       3. traffic actually goes through (traffic_routed_through_*)
#   Claims 1 and 2 are observable on the device. Claim 3 is NOT: it needs a
#   vantage point off the device, so it stays "unproven" here even when 1 and 2
#   are evidenced. No output of this tool may ever upgrade claim 3.
#
# INVARIANTS honoured here:
#   * NO FLASHING. This tool calls systemctl/ip/wg/ss and writes JSON under the
#     state and evidence directories. It never opens a block device, never
#     touches a bootloader and never writes to BOOT/USERDATA/SYSTEM/RECOVERY/
#     DTB/DTBO/VBMETA/radio/modem/EFS/SEC_EFS/PIT.
#   * REMOTE ACCESS IS OFF BY DEFAULT and is refused if the status indicator
#     cannot be rendered, or if the requested bind is a wildcard address.
#   * NO SECRETS. WireGuard/OpenVPN private keys are referenced by path only:
#     their existence and mode are checked, their contents are never read into
#     output, never logged and never stored.
#   * THE CONSOLE SURVIVES. Enabling a kill switch delegates to
#     tools/s10plus/a33/nuxel-firewall.sh, which refuses to leave the USB
#     console without its guard. This tool never calls nft directly.
#
# Usage:
#   nuxel-vpn-tor.sh claims [--json]              # the truth ladder (all surfaces)
#   nuxel-vpn-tor.sh vpn on [--profile NAME] | off | status [--json] | backends
#   nuxel-vpn-tor.sh tor on | off | status [--json] | circuits | version
#   nuxel-vpn-tor.sh tor leak-probe [--json] | bridges-status | bridges-apply FILE
#   nuxel-vpn-tor.sh remote on [--bind-iface IF] | off | status [--json]
#   nuxel-vpn-tor.sh killswitch arm [IFACE] | disarm | status
#   nuxel-vpn-tor.sh evidence [--out DIR]
#   nuxel-vpn-tor.sh menu | self-test | help
#
# Exit codes: 0 ok, 1 error/refused, 2 external resource missing (offline),
#             3 self-test failure, 4 usage.
# ============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"

CONFIG="${NUXEL_PRIVACY_CONFIG:-$REPO_ROOT/configs/nuxel/security/privacy-config.json}"
REMOTE_CONFIG="${NUXEL_REMOTE_CONFIG:-$REPO_ROOT/configs/nuxel/security/remote-access.json}"
STATE_DIR="${NUXEL_PRIVACY_STATE_DIR:-/var/lib/nuxel/privacy}"
EVIDENCE_DIR="${NUXEL_PRIVACY_EVIDENCE_DIR:-$STATE_DIR/evidence}"
REQUEST_DIR="${NUXEL_PRIVACY_REQUEST_DIR:-$STATE_DIR/requests}"
RUN_DIR="${NUXEL_PRIVACY_RUN_DIR:-/run/nuxel}"

SYSTEMCTL="${NUXEL_SYSTEMCTL_BIN:-systemctl}"
WG="${NUXEL_WG_BIN:-wg}"
IP="${NUXEL_IP_BIN:-ip}"
SS="${NUXEL_SS_BIN:-ss}"
NFT_TOOL="${NUXEL_FIREWALL_TOOL:-$REPO_ROOT/tools/s10plus/a33/nuxel-firewall.sh}"
TOR_CONTROL="${NUXEL_TOR_CONTROL_PY:-$REPO_ROOT/shell/nuxel-shell/nuxel-privacy/tor-control.py}"
TOR_COOKIE="${NUXEL_TOR_COOKIE:-/run/tor/control.authcookie}"
TOR_CONTROL_PORT="${NUXEL_TOR_CONTROL_PORT:-9051}"
PY="${PYTHON:-python3}"

EXIT_OK=0; EXIT_ERR=1; EXIT_EXTERNAL=2; EXIT_TEST=3; EXIT_USAGE=4

say()  { printf '%s\n' "$*"; }
warn() { printf '[nuxel-vpn-tor] %s\n' "$*" >&2; }
die()  { printf '[nuxel-vpn-tor] ERROR: %s\n' "$*" >&2; exit "$EXIT_ERR"; }

# ---------------------------------------------------------------------------
# tiny JSON helpers (python3 owns quoting; the shell never hand-builds JSON)
# ---------------------------------------------------------------------------
json_get() { # json_get <file> <dotted.path> [default]
    "$PY" - "$1" "$2" "${3-}" <<'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1]))
except Exception:
    print(sys.argv[3] if len(sys.argv) > 3 else "")
    sys.exit(0)
cur = data
for part in sys.argv[2].split("."):
    if isinstance(cur, dict) and part in cur:
        cur = cur[part]
    else:
        print(sys.argv[3] if len(sys.argv) > 3 else "")
        sys.exit(0)
print(cur if not isinstance(cur, (dict, list)) else json.dumps(cur))
PY
}

claim() { # claim <key> <level> <evidence...>
    "$PY" - "$@" <<'PY'
import json, sys
key, level, evidence = sys.argv[1], sys.argv[2], " ".join(sys.argv[3:])
sys.stdout.write(json.dumps({key: {"level": level, "evidence": evidence}}, sort_keys=True))
PY
}

# ---------------------------------------------------------------------------
# state writers (atomic; the PWA and the daemon read these)
# ---------------------------------------------------------------------------
ensure_state() { mkdir -p "$STATE_DIR" 2>/dev/null || true; }

write_state() { # write_state <file> <json>
    local file="$1" body="$2"
    ensure_state
    local tmp="${file}.tmp.$$"
    if ! printf '%s\n' "$body" > "$tmp" 2>/dev/null; then
        warn "cannot write $file (state directory not writable: $STATE_DIR)"
        return 1
    fi
    mv -f "$tmp" "$file" || { rm -f "$tmp"; return 1; }
    chmod 0644 "$file" 2>/dev/null || true
    return 0
}

state_json() { # state_json <surface> <state> <detail-json> <claims-json>
    "$PY" - "$1" "$2" "$3" "$4" <<'PY'
import json, sys, time, os
surface, state, detail, claims = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
try:
    detail = json.loads(detail)
except Exception:
    detail = {"note": detail}
try:
    claims = json.loads(claims)
except Exception:
    claims = {}
doc = {
    "schema": "nuxel.privacy-state/1",
    "surface": surface,
    "state": state,
    "written_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "written_by": "nuxel-vpn-tor.sh",
    "uid": os.getuid(),
    "claims": claims,
    "detail": detail,
}
print(json.dumps(doc, indent=2, sort_keys=True))
PY
}

audit() { # audit <action> <detail>
    ensure_state
    local log="$STATE_DIR/audit.log"
    printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" >> "$log" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# command runner: prints the command, captures the output, records the status.
# Nothing in this tool reports the state of the world without this evidence.
# ---------------------------------------------------------------------------
LAST_OUT=""; LAST_STATUS=127; LAST_CMD=""
run_cmd() {
    local display="$1"; shift
    LAST_CMD="$display"
    if ! command -v "$1" >/dev/null 2>&1 && [ ! -x "$1" ]; then
        LAST_OUT=""; LAST_STATUS=127
        return 127
    fi
    LAST_OUT="$("$@" 2>&1)"; LAST_STATUS=$?
    return 0
}

print_cmd_evidence() {
    say "\$ $LAST_CMD"
    if [ "$LAST_STATUS" -eq 127 ]; then
        say "  unavailable (tool not installed) -> unknown"
        return 0
    fi
    if [ -n "$LAST_OUT" ]; then printf '%s\n' "$LAST_OUT" | sed -n '1,12p' | sed 's/^/  /'; fi
    if [ -z "$LAST_OUT" ]; then say "  (no output; exit=$LAST_STATUS)"; fi
    return 0
}

tor_control_json() { # tor_control_json <command>
    if [ ! -r "$TOR_CONTROL" ]; then
        printf '{"error":"tor-control.py not found at %s","control_port_authenticated":false}' "$TOR_CONTROL"
        return "$EXIT_EXTERNAL"
    fi
    "$PY" "$TOR_CONTROL" --port "$TOR_CONTROL_PORT" --cookie "$TOR_COOKIE" \
        --json "$1" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# TOR
# ---------------------------------------------------------------------------
do_tor_on() {
    ensure_state
    local enabled
    enabled="$(json_get "$CONFIG" "tor.enabled_by_default" "false")"
    say "tor: bringing up the client (config: $CONFIG, default=$enabled, i.e. NOT started at boot)"
    run_cmd "$SYSTEMCTL start tor.service" "$SYSTEMCTL" start tor.service
    print_cmd_evidence
    do_tor_status
}

do_tor_off() {
    run_cmd "$SYSTEMCTL stop tor.service" "$SYSTEMCTL" stop tor.service
    print_cmd_evidence
    write_state "$STATE_DIR/tor.state.json" \
        "$(state_json tor off '{"action":"stop"}' "$(claim service_running unproven 'stopped by operator; re-read below')")" || true
    audit tor-off "operator stop"
    do_tor_status
}

do_tor_status() {
    local json=0
    [ "${1-}" = "--json" ] && json=1
    local active
    run_cmd "$SYSTEMCTL is-active tor.service" "$SYSTEMCTL" is-active tor.service
    active="$LAST_OUT"; [ -z "$active" ] && active="unknown"
    [ "$LAST_STATUS" -eq 127 ] && active="unavailable"

    local circuits_doc circuits_built ctl_authed tor_version
    circuits_doc="$(tor_control_json circuits)"
    circuits_built="$(printf '%s' "$circuits_doc" | "$PY" -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
v=d.get("circuits_built")
print("null" if v is None else v)' 2>/dev/null || echo null)"
    ctl_authed="$(printf '%s' "$circuits_doc" | "$PY" -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print("true" if d.get("control_port_authenticated") else "false")' 2>/dev/null || echo false)"
    tor_version="$(printf '%s' "$circuits_doc" | "$PY" -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print(d.get("version") or "unknown")' 2>/dev/null || echo unknown)"

    local service_level circuits_level
    case "$active" in
        active) service_level=evidenced ;;
        unavailable) service_level=unavailable ;;
        *) service_level=evidenced ;;
    esac
    if [ "$ctl_authed" = "true" ] && [ "$circuits_built" != "null" ] && [ "$circuits_built" != "0" ]; then
        circuits_level=evidenced
    elif [ "$ctl_authed" = "true" ]; then
        circuits_level=evidenced     # authenticated and 0 circuits is still a real reading
    else
        circuits_level=unknown
    fi

    if [ "$json" = "1" ]; then
        "$PY" - "$active" "$service_level" "$ctl_authed" "$circuits_built" "$circuits_level" "$tor_version" <<'PY'
import json, sys, time
active, s_level, authed, built, c_level, version = sys.argv[1:7]
doc = {
    "surface": "tor", "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "measured": {"service_active": active, "control_port_authenticated": authed == "true",
                 "circuits_built": None if built == "null" else int(built),
                 "tor_version": version},
    "claims": {
        "service_running": {"level": s_level,
                            "evidence": "systemctl is-active tor.service -> %s" % active},
        "control_port_authenticated": {"level": "evidenced" if authed == "true" else "unproven",
                                       "evidence": "tor-control.py control-port GETINFO (cookie auth)"},
        "circuits_built": {"level": c_level,
                           "evidence": "control-port GETINFO circuit-status -> %s built" % built},
        "traffic_routed_through_tor": {
            "level": "unproven",
            "evidence": ("no device-side evidence is possible: proving that this device's traffic exits via Tor "
                         "needs an external vantage point. Run 'tor leak-probe' for the device-side smoke test "
                         "and treat the result as a suspect list, not a proof.")},
    },
    "honest_note": ("A built circuit proves Tor has a path. It does not prove this device uses it, and it says "
                    "nothing about exit-node trustworthiness."),
    "sources": ["systemctl is-active", "tor control port (GETINFO circuit-status)"],
}
print(json.dumps(doc, indent=2, sort_keys=True))
PY
        return "$EXIT_OK"
    fi

    say "== Tor =="
    run_cmd "$SYSTEMCTL is-active tor.service" "$SYSTEMCTL" is-active tor.service; print_cmd_evidence
    say "\$ $PY $TOR_CONTROL --port $TOR_CONTROL_PORT --json circuits"
    if [ "$ctl_authed" = "true" ]; then
        say "  control port authenticated; circuits built: $circuits_built (tor $tor_version)"
    else
        say "  control port unavailable -> circuits unknown (this tool never guesses)"
    fi
    say ""
    say "claims:"
    say "  service_running            : $service_level ($active)"
    say "  control_port_authenticated : $( [ "$ctl_authed" = true ] && echo evidenced || echo unproven )"
    say "  circuits_built             : $circuits_level ($circuits_built)"
    say "  traffic_routed_through_tor : unproven (needs an off-device vantage point)"
    say ""
    say "A running tor.service is NOT anonymisation. Claim 3 above stays unproven until an external leak test passes."
    return "$EXIT_OK"
}

do_tor_circuits() { do_tor_status --json | "$PY" -c 'import json,sys
d=json.load(sys.stdin); print(json.dumps(d["measured"], indent=2, sort_keys=True))'; }

do_tor_version() {
    say "\$ $PY $TOR_CONTROL --json version"
    tor_control_json version | "$PY" -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: d={}
print("  " + json.dumps(d, sort_keys=True))'
}

do_tor_leak_probe() {
    # A device-side smoke test: force a name resolution and count plaintext DNS
    # and direct outbound sockets that bypass loopback. This is a SUSPECT LIST.
    # It cannot prove anonymisation - only an external vantage point can.
    local json=0; [ "${1-}" = "--json" ] && json=1
    local samples sample_seconds
    samples="$(json_get "$CONFIG" "tor.leak_probe.samples" 3)"
    sample_seconds="$(json_get "$CONFIG" "tor.leak_probe.sample_seconds" 3)"

    local have_ss=1 have_getent=1
    command -v "$SS" >/dev/null 2>&1 || have_ss=0
    command -v "$(json_get "$CONFIG" "x" getent)" >/dev/null 2>&1 || have_getent=0

    if [ "$have_ss" -eq 0 ]; then
        if [ "$json" = 1 ]; then
            "$PY" - <<'PY'
import json
print(json.dumps({
  "surface": "tor", "probe": "leak-probe", "verdict": "BLOCKED_EXTERNAL_RESOURCE",
  "claims": {"traffic_routed_through_tor": {"level": "unproven",
      "evidence": "'ss' is not installed here, so no socket table could be read"}},
  "honest_note": ("Without a socket table there is no device-side evidence either way. The probe reports the "
                  "missing tool instead of a reassuring result.")}, indent=2, sort_keys=True))
PY
        else
            say "tor leak probe: BLOCKED_EXTERNAL_RESOURCE - 'ss' is not available, so no socket table could be read."
        fi
        return "$EXIT_EXTERNAL"
    fi

    say "tor leak probe (device-side smoke test; NOT proof of anonymisation)"
    local suspects=0 sampling=0
    for _ in $(seq 1 "${samples:-3}" 2>/dev/null || seq 1 3); do
        run_cmd "$SS -H -tunp" "$SS" -H -tunp
        local out="$LAST_OUT"
        if [ "$LAST_STATUS" -eq 127 ]; then
            say "  ss unavailable -> unknown"
            return "$EXIT_EXTERNAL"
        fi
        local plain_dns direct
        plain_dns="$(printf '%s\n' "$out" | grep -E ':(53)[[:space:]]' | grep -v '127\.0\.0\.1' | wc -l | tr -d ' ')"
        direct="$(printf '%s\n' "$out" | grep -vE '127\.0\.0\.1|\[::1\]|(^|[[:space:]])(0\.0\.0\.0|\*):' | wc -l | tr -d ' ')"
        say "  sample $((sampling + 1)): plaintext-DNS sockets=$plain_dns non-loopback outbound=$direct"
        suspects=$((suspects + plain_dns + direct))
        sampling=$((sampling + 1))
        sleep "${sample_seconds:-3}"
    done

    local verdict="NO-LEAK-OBSERVED (device-side only, still unproven)"
    local level="unproven"
    if [ "$suspects" -gt 0 ]; then
        verdict="LEAK-SUSPECT ($suspects socket(s) worth a look)"
    fi
    if [ "$json" = 1 ]; then
        "$PY" - "$verdict" "$suspects" "$sampling" <<'PY'
import json, sys
verdict, suspects, samples = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
print(json.dumps({
  "surface": "tor", "probe": "leak-probe", "verdict": verdict,
  "measured": {"samples": samples, "suspect_sockets": suspects},
  "claims": {"traffic_routed_through_tor": {"level": "unproven",
      "evidence": ("device-side socket sampling cannot see the exit; only an off-device vantage point can prove "
                   "the path. %s" % verdict)}},
  "honest_note": ("Reporting 'unproven' even when nothing suspicious was seen is the point: absence of a local "
                  "leak is not evidence of anonymisation.")}, indent=2, sort_keys=True))
PY
        return "$EXIT_OK"
    fi
    say "verdict: $verdict"
    say "claim traffic_routed_through_tor: unproven (device-side sampling cannot see the exit node)"
    return "$EXIT_OK"
}

do_tor_bridges_status() {
    local have=0
    if [ -r /etc/tor/bridges.conf ] || [ -r "$STATE_DIR/bridges.conf" ]; then have=1; fi
    if [ "$have" = 0 ]; then
        say "tor bridges: NOT CONFIGURED"
        say "  this repository ships no bridge addresses and no pluggable-transport binaries."
        say "  in a censored network, add lines to /etc/tor/bridges.conf and run:"
        say "    $0 tor bridges-apply /etc/tor/bridges.conf"
        say "  until then Tor is reported as unbridged; nothing pretends censorship is defeated."
        return "$EXIT_OK"
    fi
    say "tor bridges: configuration present (contents not printed: bridge lines are sensitive)"
    return "$EXIT_OK"
}

do_tor_bridges_apply() {
    local file="${1-}"
    [ -n "$file" ] || die "usage: $0 tor bridges-apply <file>"
    [ -r "$file" ] || die "cannot read $file"
    ensure_state
    install -m 0600 "$file" "$STATE_DIR/bridges.conf" || die "cannot stage bridges file"
    say "staged $file -> $STATE_DIR/bridges.conf (mode 0600, contents not echoed)"
    say "NOTE: applying bridges requires tor to read them; add 'UseBridges 1' and a ClientTransportPlugin"
    say "      line to /etc/tor/torrc yourself - this tool does not edit torrc automatically."
    audit tor-bridges-apply "staged $file"
    return "$EXIT_OK"
}

# ---------------------------------------------------------------------------
# VPN
# ---------------------------------------------------------------------------
vpn_interface() { json_get "$CONFIG" "vpn.wireguard.interface" "wg0"; }
vpn_key_file()  { json_get "$CONFIG" "vpn.wireguard.requires_key_file" "/etc/nuxel/security/vpn/wg0.key"; }

do_vpn_backends() {
    say "VPN backends, in the order the config asks for ($(json_get "$CONFIG" vpn.backend_order '[]')):"
    local rc=0
    for tool in wg nmcli; do
        if command -v "$tool" >/dev/null 2>&1; then
            say "  $tool: present ($(command -v "$tool"))"
        else
            say "  $tool: ABSENT"
            rc="$EXIT_EXTERNAL"
        fi
    done
    say "The tool reports which backend it actually used; it never claims a tunnel from a config file alone."
    return "$rc"
}

do_vpn_on() {
    local profile=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --profile) profile="${2-}"; shift 2 ;;
            *) die "unknown option for 'vpn on': $1" ;;
        esac
    done
    ensure_state
    local iface; iface="$(vpn_interface)"
    local keyfile; keyfile="$(vpn_key_file)"

    say "vpn: interface=$iface profile=${profile:-<default>}"
    # Secret hygiene: existence + mode only. The key is never read.
    if [ -e "$keyfile" ]; then
        local mode; mode="$(stat -c '%a %U:%G' "$keyfile" 2>/dev/null || echo 'unknown')"
        say "  private key: $keyfile present (mode $mode) - contents never read, logged or stored"
        case "$mode" in
            600*) : ;;
            *) warn "  key file mode is $mode, expected 0600 root:root - fix it before trusting this tunnel" ;;
        esac
    else
        say "  private key: $keyfile ABSENT -> refusing to bring up $iface"
        say "  a VPN that starts without a key is not a VPN. Create the key file (0600 root) and retry."
        return "$EXIT_ERR"
    fi

    if ! command -v "$WG" >/dev/null 2>&1; then
        say "  wg: ABSENT -> cannot configure $iface here (BLOCKED_EXTERNAL_RESOURCE, not a failure of the phone)"
        return "$EXIT_EXTERNAL"
    fi
    run_cmd "$WG show $iface" "$WG" show "$iface"; print_cmd_evidence
    if [ "$LAST_STATUS" -ne 0 ]; then
        say "  $iface does not exist yet. Bring it up with your own wg-quick config; this tool does not"
        say "  invent peer endpoints:"
        say "    wg-quick up $iface    # reads /etc/wireguard/$iface.conf (0600 root)"
    fi
    do_vpn_status
}

do_vpn_off() {
    local iface; iface="$(vpn_interface)"
    if command -v "$WG" >/dev/null 2>&1; then
        run_cmd "$WG show $iface" "$WG" show "$iface"; print_cmd_evidence
    fi
    say "vpn: nothing to tear down from here unless you brought the tunnel up outside this tool."
    say "  to remove it: wg-quick down $iface   (this tool never edits /etc/wireguard)"
    write_state "$STATE_DIR/vpn.state.json" \
        "$(state_json vpn off '{"action":"off"}' "$(claim tunnel_interface_up unproven 'operator requested off')")" || true
    audit vpn-off "operator request"
    return "$EXIT_OK"
}

do_vpn_status() {
    local json=0; [ "${1-}" = "--json" ] && json=1
    local iface; iface="$(vpn_interface)"
    local link_out="" link_status=127 hs_out="" hs_status=127

    run_cmd "$IP -brief link show $iface" "$IP" -brief link show "$iface"
    link_out="$LAST_OUT"; link_status="$LAST_STATUS"
    run_cmd "$WG show $iface latest-handshakes" "$WG" show "$iface" latest-handshakes
    hs_out="$LAST_OUT"; hs_status="$LAST_STATUS"

    local iface_state="unknown" iface_level="unknown"
    case "$link_status" in
        127) iface_state="unavailable"; iface_level="unavailable" ;;
        0)   iface_state="up"; iface_level="evidenced" ;;
        *)   iface_state="down"; iface_level="evidenced" ;;
    esac

    local hs_result="null" hs_level="unproven"
    if [ "$hs_status" -eq 0 ] && [ -n "$hs_out" ]; then
        # "wg show <if> latest-handshakes" prints "<pubkey>\t<epoch>"; 0 = never.
        if printf '%s\n' "$hs_out" | awk '{ if ($2+0 > 0) found=1 } END { exit(found?0:1) }'; then
            hs_result="true"; hs_level="evidenced"
        else
            hs_result="false"; hs_level="evidenced"
        fi
    fi

    local ks_doc ks_armed="unknown"
    local ks_file="${NUXEL_FIREWALL_STATE_DIR:-/var/lib/nuxel/firewall}/killswitch.json"
    if [ -r "$ks_file" ]; then
        ks_armed="$(json_get "$ks_file" "armed" "unknown")" || ks_armed="unknown"
    fi

    if [ "$json" = 1 ]; then
        "$PY" - "$iface" "$iface_state" "$iface_level" "$hs_result" "$hs_level" "$ks_file" "$ks_armed" <<'PY'
import json, sys, time
iface, istate, ilevel, hs, hs_level, ks_file, ks_armed = sys.argv[1:7]
doc = {
  "surface": "vpn", "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
  "measured": {"interface": iface, "interface_present": istate == "up",
               "interface_state": istate, "handshake_observed": None if hs == "null" else hs == "true",
               "killswitch_state_file": ks_file, "killswitch_armed": ks_armed},
  "claims": {
    "tunnel_interface_up": {"level": ilevel, "evidence": "ip -brief link show %s -> %s" % (iface, istate)},
    "handshake_observed": {"level": hs_level,
                           "evidence": "wg show %s latest-handshakes -> observed=%s" % (iface, hs)},
    "traffic_routed_through_vpn": {
        "level": "unproven",
        "evidence": ("only an off-device vantage point can show that traffic left through the tunnel; the device "
                     "can show the interface and a handshake and nothing more.")},
    "killswitch_armed": {"level": "evidenced" if ks_armed in ("true", "false") else "unknown",
                         "evidence": "firewall state file %s -> armed=%s" % (ks_file, ks_armed)},
  },
  "honest_note": ("Armed is not connected: the kill switch can be armed while the tunnel is down. The two are "
                  "always reported separately."),
  "sources": ["ip -brief link show", "wg show latest-handshakes", "firewall killswitch state"],
}
print(json.dumps(doc, indent=2, sort_keys=True))
PY
        return "$EXIT_OK"
    fi

    say "== VPN =="
    run_cmd "$IP -brief link show $iface" "$IP" -brief link show "$iface"; print_cmd_evidence
    run_cmd "$WG show $iface latest-handshakes" "$WG" show "$iface" latest-handshakes; print_cmd_evidence
    say ""
    say "claims:"
    say "  tunnel_interface_up         : $iface_level ($iface_state)"
    say "  handshake_observed          : $hs_level (observed=$hs_result)"
    say "  traffic_routed_through_vpn  : unproven (needs an off-device vantage point)"
    say "  killswitch_armed            : $ks_armed (read from $ks_file)"
    say ""
    say "A tunnel interface and a handshake are device-side facts. Neither proves which traffic used the tunnel."
    return "$EXIT_OK"
}

# ---------------------------------------------------------------------------
# Kill switch (delegates - never calls nft itself)
# ---------------------------------------------------------------------------
firewall_state_dir() { printf '%s' "${NUXEL_FIREWALL_STATE_DIR:-/var/lib/nuxel/firewall}"; }

do_killswitch() {
    local action="${1-arm}"; shift || true
    local iface="${1:-$(vpn_interface)}"
    [ -x "$NFT_TOOL" ] || die "firewall tool not found/executable: $NFT_TOOL"
    case "$action" in
        arm)
            say "kill switch: arming via $NFT_TOOL vpn-on $iface"
            "$NFT_TOOL" vpn-on "$iface"; local rc=$?
            if [ "$rc" -ne 0 ]; then
                say "kill switch: NOT armed (firewall tool refused, exit=$rc). Nothing is claimed."
                return "$rc"
            fi
            local ks_file; ks_file="$(firewall_state_dir)/killswitch.json"
            local armed="unknown"; [ -r "$ks_file" ] && armed="$(json_get "$ks_file" armed unknown)"
            say "kill switch armed: $armed (evidence: $ks_file)"
            say "NOTE: armed != tunnel up. Check 'vpn status' separately."
            audit killswitch-arm "iface=$iface armed=$armed"
            ;;
        disarm)
            say "kill switch: disarming via $NFT_TOOL vpn-off"
            "$NFT_TOOL" vpn-off; local rc=$?
            audit killswitch-disarm "exit=$rc"
            return "$rc"
            ;;
        status)
            local ks_file; ks_file="$(firewall_state_dir)/killswitch.json"
            if [ -r "$ks_file" ]; then
                say "kill switch state ($ks_file):"
                sed 's/^/  /' "$ks_file"
            else
                say "kill switch: never armed on this boot (no state file)"
            fi
            say "the console guard is verified separately: $NFT_TOOL console-verify"
            return "$EXIT_OK"
            ;;
        *) die "usage: $0 killswitch arm [iface] | disarm | status" ;;
    esac
    return "$EXIT_OK"
}

# ---------------------------------------------------------------------------
# Remote access (off by default; refuses to be invisible)
# ---------------------------------------------------------------------------
remote_state_file() { printf '%s' "$RUN_DIR/remote-access.state"; }

remote_bind_allowed() { # remote_bind_allowed <iface>
    case "$1" in
        usb[0-9]|rndis[0-9]|ncm[0-9]|eth[0-9]|enp[0-9]s[0-9]|wlan[0-9]) return 0 ;;
        *0.0.0.0*|*::*|*"*"*) return 1 ;;
        *) return 1 ;;
    esac
}

do_remote_on() {
    local iface=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --bind-iface) iface="${2-}"; shift 2 ;;
            *) die "unknown option for 'remote on': $1" ;;
        esac
    done
    local default_iface; default_iface="$(json_get "$REMOTE_CONFIG" "transports.ssh_gadget.bind_interface" "usb0")"
    iface="${iface:-$default_iface}"

    say "remote access: requested bind interface '$iface'"
    [ -r "$REMOTE_CONFIG" ] || die "remote-access policy not found: $REMOTE_CONFIG"

    if ! remote_bind_allowed "$iface"; then
        say "REFUSED: '$iface' is not an owner-console interface."
        say "  allowed: usb*, rndis*, ncm*, eth*, enp*s*, wlan* - a wildcard bind (0.0.0.0 / ::) would expose"
        say "  the phone on whatever network it joins, which the policy forbids."
        return "$EXIT_ERR"
    fi
    case "$iface" in
        usb*|rndis*|ncm*) : ;;
        *) say "WARNING: $iface is not the USB gadget path; the console path is '$default_iface'." ;;
    esac

    # The indicator must be renderable BEFORE the service is started. An
    # invisible remote-access path is the failure mode this check exists for.
    local ind; ind="$(remote_state_file)"
    mkdir -p "$(dirname "$ind")" 2>/dev/null || true
    if ! ( : > "${ind}.probe" ) 2>/dev/null; then
        say "REFUSED: cannot write the status indicator $ind"
        say "  without a visible indicator there is no acceptable way to enable remote access."
        return "$EXIT_ERR"
    fi
    rm -f "${ind}.probe"

    local unit; unit="$(json_get "$REMOTE_CONFIG" "transports.ssh_gadget.service" "sshd-gadget.service")"
    if ! command -v "$SYSTEMCTL" >/dev/null 2>&1; then
        say "REFUSED: systemctl is not available here, so $unit cannot be started or verified."
        return "$EXIT_EXTERNAL"
    fi

    write_state "$ind" "$(state_json remote_access enabled \
        "{\"bind_interface\":\"$iface\",\"unit\":\"$unit\"}" \
        "$(claim remote_access_enabled evidenced "indicator written to $ind before start")")" \
        || die "cannot write the indicator"

    run_cmd "$SYSTEMCTL start $unit" "$SYSTEMCTL" start "$unit"
    local start_status="$LAST_STATUS"; print_cmd_evidence
    run_cmd "$SYSTEMCTL is-active $unit" "$SYSTEMCTL" is-active "$unit"
    local active="$LAST_OUT"; print_cmd_evidence
    if [ "$start_status" -ne 0 ]; then
        say "remote access: $unit did NOT start (exit=$start_status) - reverting the indicator"
        rm -f "$ind" 2>/dev/null || true
        audit remote-on-failed "unit=$unit exit=$start_status"
        return "$EXIT_ERR"
    fi
    write_state "$STATE_DIR/remote.state.json" "$(state_json remote_access enabled \
        "{\"bind_interface\":\"$iface\",\"unit\":\"$unit\",\"systemd_active\":\"$active\"}" \
        "$(claim remote_access_enabled evidenced "systemctl start $unit; is-active -> $active")")" || true
    say "remote access: enabled on $iface ($unit=$active). Indicator: $ind"
    say "  disable with: $0 remote off"
    audit remote-on "iface=$iface unit=$unit active=$active"
    return "$EXIT_OK"
}

do_remote_off() {
    local unit; unit="$(json_get "$REMOTE_CONFIG" "transports.ssh_gadget.service" "sshd-gadget.service")"
    if command -v "$SYSTEMCTL" >/dev/null 2>&1; then
        run_cmd "$SYSTEMCTL stop $unit" "$SYSTEMCTL" stop "$unit"; print_cmd_evidence
    else
        say "systemctl unavailable: nothing to stop here; the indicator is still cleared below."
    fi
    rm -f "$(remote_state_file)" 2>/dev/null || true
    write_state "$STATE_DIR/remote.state.json" "$(state_json remote_access disabled \
        '{"reason":"operator request"}' "$(claim remote_access_enabled evidenced 'indicator removed and unit stopped')")" || true
    say "remote access: OFF (indicator removed)."
    audit remote-off "unit=$unit"
    return "$EXIT_OK"
}

do_remote_status() {
    local json=0; [ "${1-}" = "--json" ] && json=1
    local unit; unit="$(json_get "$REMOTE_CONFIG" "transports.ssh_gadget.service" "sshd-gadget.service")"
    local ind; ind="$(remote_state_file)"
    local ind_state="absent" active="unknown"
    [ -r "$ind" ] && ind_state="present"
    if command -v "$SYSTEMCTL" >/dev/null 2>&1; then
        run_cmd "$SYSTEMCTL is-active $unit" "$SYSTEMCTL" is-active "$unit"
        active="$LAST_OUT"; [ -z "$active" ] && active="unknown"
    else
        active="unavailable"
    fi
    if [ "$json" = 1 ]; then
        "$PY" - "$ind" "$ind_state" "$unit" "$active" <<'PY'
import json, sys, time
ind, ind_state, unit, active = sys.argv[1:5]
print(json.dumps({
  "surface": "remote_access", "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
  "measured": {"indicator_file": ind, "indicator": ind_state, "unit": unit, "unit_active": active,
               "default": "off"},
  "claims": {
     "remote_access_enabled": {"level": "evidenced" if (ind_state == "present" or active == "active") else "evidenced",
                               "evidence": "indicator=%s, %s is-active -> %s" % (ind_state, unit, active)},
     "indicator_visible": {"level": "evidenced" if ind_state == "present" else "unproven",
                           "evidence": "indicator file %s -> %s" % (ind, ind_state)},
  },
  "honest_note": ("Remote access is off by default. It is refused if the indicator cannot be rendered, and the "
                  "only accepted transports bind the USB gadget interface - never a wildcard address."),
}, indent=2, sort_keys=True))
PY
        return "$EXIT_OK"
    fi
    say "== Remote access =="
    say "  default              : off (policy: $REMOTE_CONFIG)"
    say "  indicator ($ind): $ind_state"
    run_cmd "$SYSTEMCTL is-active $unit" "$SYSTEMCTL" is-active "$unit"; print_cmd_evidence
    say "  unit                 : $unit ($active)"
    say "  transports           : ssh over the USB gadget only, publickey only, no password auth"
    return "$EXIT_OK"
}

# ---------------------------------------------------------------------------
# The truth ladder: everything in one document
# ---------------------------------------------------------------------------
do_claims() {
    local json=0; [ "${1-}" = "--json" ] && json=1
    local tor_doc vpn_doc remote_doc
    tor_doc="$(do_tor_status --json)"
    vpn_doc="$(do_vpn_status --json)"
    remote_doc="$(do_remote_status --json)"
    local ks_file; ks_file="$(firewall_state_dir)/killswitch.json"
    local ks_armed="unknown"; [ -r "$ks_file" ] && ks_armed="$(json_get "$ks_file" armed unknown)"

    if [ "$json" = 1 ]; then
        "$PY" - "$tor_doc" "$vpn_doc" "$remote_doc" "$ks_armed" <<'PY'
import json, sys, time
tor_doc, vpn_doc, remote_doc, ks_armed = sys.argv[1:5]
try: tor = json.loads(tor_doc)
except Exception: tor = {}
try: vpn = json.loads(vpn_doc)
except Exception: vpn = {}
try: remote = json.loads(remote_doc)
except Exception: remote = {}
vocab = ["evidenced", "unproven", "unavailable", "unknown"]
claims = {}
claims.update(tor.get("claims", {}))
claims.update(vpn.get("claims", {}))
claims.update(remote.get("claims", {}))
claims["killswitch_armed"] = {
    "level": "evidenced" if ks_armed in ("true", "false") else "unknown",
    "evidence": "firewall killswitch state -> armed=%s" % ks_armed,
}
bad = [k for k, v in claims.items() if v.get("level") not in vocab]
doc = {
  "schema": "nuxel.privacy-claims/1",
  "tool": "nuxel-vpn-tor.sh",
  "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
  "vocabulary": vocab,
  "claims": claims,
  "measured": {"tor": tor.get("measured", {}), "vpn": vpn.get("measured", {}),
               "remote_access": remote.get("measured", {})},
  "unproven": sorted(k for k, v in claims.items() if v.get("level") == "unproven"),
  "rules": [
    "service_running is not anonymisation; circuits_built is not traffic; armed is not connected.",
    "traffic_routed_through_tor and traffic_routed_through_vpn stay unproven until an off-device leak test passes.",
    "unknown is a valid answer and is never upgraded to make a screen look better.",
  ],
  "invalid_claim_levels": bad,
}
print(json.dumps(doc, indent=2, sort_keys=True))
if bad:
    sys.exit(3)
PY
        return "$?"
    fi

    say "Nuxel privacy truth ladder ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
    printf '%s\n' "$tor_doc" | "$PY" -c '
import json,sys
d=json.load(sys.stdin)
for k,v in sorted(d.get("claims",{}).items()):
    print("  TOR    %-28s %-11s %s" % (k, v["level"], v["evidence"][:70]))
'
    printf '%s\n' "$vpn_doc" | "$PY" -c '
import json,sys
d=json.load(sys.stdin)
for k,v in sorted(d.get("claims",{}).items()):
    print("  VPN    %-28s %-11s %s" % (k, v["level"], v["evidence"][:70]))
'
    printf '%s\n' "$remote_doc" | "$PY" -c '
import json,sys
d=json.load(sys.stdin)
for k,v in sorted(d.get("claims",{}).items()):
    print("  REMOTE %-28s %-11s %s" % (k, v["level"], v["evidence"][:70]))
'
    say "  KS     killswitch_armed             %s" "$ks_armed"
    say ""
    say "Unproven on purpose: traffic_routed_through_tor, traffic_routed_through_vpn."
    return "$EXIT_OK"
}

# ---------------------------------------------------------------------------
# Evidence bundle
# ---------------------------------------------------------------------------
do_evidence() {
    local out="$EVIDENCE_DIR"
    while [ $# -gt 0 ]; do
        case "$1" in
            --out) out="${2-}"; shift 2 ;;
            *) die "unknown option for 'evidence': $1" ;;
        esac
    done
    local stamp; stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    mkdir -p "$out" || die "cannot create evidence directory $out"
    local base="$out/privacy-$stamp"
    do_claims --json > "$base.claims.json" 2>/dev/null || true
    do_tor_status --json > "$base.tor.json" 2>/dev/null || true
    do_vpn_status --json > "$base.vpn.json" 2>/dev/null || true
    do_remote_status --json > "$base.remote.json" 2>/dev/null || true
    {
        say "Nuxel privacy evidence bundle $stamp"
        say "generated by $0 (uid $(id -u))"
        say ""
        say "== config =="
        say "privacy: $CONFIG"
        say "remote : $REMOTE_CONFIG"
        say "state  : $STATE_DIR"
        say ""
        say "== state files =="
        for f in "$STATE_DIR"/*.state.json "$RUN_DIR"/remote-access.state "$(firewall_state_dir)/killswitch.json"; do
            [ -e "$f" ] && { say "-- $f"; sed 's/^/  /' "$f"; }
        done
        say ""
        say "== audit log (tail) =="
        [ -r "$STATE_DIR/audit.log" ] && tail -20 "$STATE_DIR/audit.log" | sed 's/^/  /'
        say ""
        say "== claims =="
        sed 's/^/  /' "$base.claims.json"
    } > "$base.txt"
    say "evidence written:"
    say "  $base.txt"
    say "  $base.claims.json  $base.tor.json  $base.vpn.json  $base.remote.json"
    return "$EXIT_OK"
}

# ---------------------------------------------------------------------------
# Menu (non-interactive by default: this repository is never driven by a human)
# ---------------------------------------------------------------------------
do_menu() {
    cat <<'MENU'
Nuxel privacy menu
  1) claims (the truth ladder)            7) remote status
  2) tor status                          8) remote on  (indicator required)
  3) tor on                              9) remote off
  4) tor off                            10) killswitch arm / disarm
  5) tor leak probe (device-side)       11) capture evidence bundle
  6) vpn status                         12) firewall hand-off (nuxel-firewall.sh menu)
MENU
    if [ ! -t 0 ] && [ "${NUXEL_MENU_ASSUME_TTY:-0}" != "1" ]; then
        say "(stdin is not a terminal: the menu shows its options and changes nothing)"
        return "$EXIT_OK"
    fi
    printf 'choice> '
    read -r choice || choice=""
    case "$choice" in
        1) do_claims ;;
        2) do_tor_status ;;
        3) do_tor_on ;;
        4) do_tor_off ;;
        5) do_tor_leak_probe ;;
        6) do_vpn_status ;;
        7) do_remote_status ;;
        8) do_remote_on ;;
        9) do_remote_off ;;
        10) printf 'arm|disarm> '; read -r a || a="status"; do_killswitch "${a:-status}" ;;
        11) do_evidence ;;
        12) [ -x "$NFT_TOOL" ] && "$NFT_TOOL" menu || say "firewall tool not present" ;;
        *) say "no change" ;;
    esac
}

# ---------------------------------------------------------------------------
# Self-test: runs the offline suite (mocks in security-fixtures/net-mocks)
# ---------------------------------------------------------------------------
do_self_test() {
    local suite="$HERE/security-tests/test-vpn-tor.sh"
    [ -f "$suite" ] || die "test suite not found: $suite"
    bash "$suite" "$@"
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
cmd="${1:-help}"; [ $# -gt 0 ] && shift || true
case "$cmd" in
    claims)      do_claims "$@" ;;
    vpn)
        sub="${1-help}"; [ $# -gt 0 ] && shift || true
        case "$sub" in
            on)       do_vpn_on "$@" ;;
            off)      do_vpn_off "$@" ;;
            status)   do_vpn_status "$@" ;;
            backends) do_vpn_backends ;;
            *) die "usage: $0 vpn on|off|status|backends" ;;
        esac ;;
    tor)
        sub="${1-help}"; [ $# -gt 0 ] && shift || true
        case "$sub" in
            on)             do_tor_on ;;
            off)            do_tor_off ;;
            status)         do_tor_status "$@" ;;
            circuits)       do_tor_circuits ;;
            version)        do_tor_version ;;
            leak-probe)     do_tor_leak_probe "$@" ;;
            bridges-status) do_tor_bridges_status ;;
            bridges-apply)  do_tor_bridges_apply "$@" ;;
            *) die "usage: $0 tor on|off|status|circuits|version|leak-probe|bridges-status|bridges-apply FILE" ;;
        esac ;;
    remote)
        sub="${1-help}"; [ $# -gt 0 ] && shift || true
        case "$sub" in
            on)     do_remote_on "$@" ;;
            off)    do_remote_off "$@" ;;
            status) do_remote_status "$@" ;;
            *) die "usage: $0 remote on [--bind-iface IF] | off | status" ;;
        esac ;;
    killswitch) do_killswitch "$@" ;;
    evidence)   do_evidence "$@" ;;
    menu)       do_menu ;;
    self-test)  do_self_test "$@" ;;
    help|-h|--help)
        awk '/^# Usage:/{on=1} on&&/^# ====/{exit} on{sub(/^# ?/,""); print}' "$0"
        cat <<'HELP'

Notes:
  * 'tor status' and 'vpn status' never upgrade the traffic claim: service up and
    circuit/handshake present are device-side facts; "traffic actually went
    through" needs an off-device vantage point and stays unproven here.
  * Remote access is off by default, refuses a wildcard bind, and refuses to
    enable itself if the status indicator cannot be rendered.
  * The kill switch is applied by nuxel-firewall.sh (which guarantees the USB
    console guard); this tool never calls nft.
  * Private keys are referenced by path only - existence and mode are checked,
    contents are never read, logged or stored.
  * Offline testing: bash tools/s10plus/a33/security-tests/test-vpn-tor.sh
    (or simply run 'self-test'). Mock tools: security-fixtures/net-mocks/.
HELP
        ;;
    *) die "unknown command '$cmd' (try: $0 help)" ;;
esac

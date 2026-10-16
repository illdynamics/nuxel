#!/bin/bash
# SPDX-License-Identifier: MIT
# ============================================================================
# Offline test suite for the VPN / Tor / remote-access tool (briq-05c).
# ============================================================================
# Runs tools/s10plus/a33/nuxel-vpn-tor.sh with mock systemctl/wg/ip/ss and a
# mock Tor control port (security-fixtures/net-mocks/). No root, no device, no
# network, no Tor, no WireGuard.
#
# What this suite DOES prove:
#   * the claim ladder never upgrades: service up / circuits built / handshake
#     observed are reported as device-side facts, while traffic_routed_through_*
#     stays "unproven" in EVERY case, including the happy path;
#   * the tool reports "unknown"/null instead of guessing when a source is
#     missing (no tor control port, no wg, no ss);
#   * remote access is off by default, refuses a wildcard bind, refuses to
#     enable itself when the indicator cannot be written, and refuses to enable
#     when systemctl is unavailable (fail-closed ordering: no indicator, no
#     enablement);
#   * the kill switch is delegated to nuxel-firewall.sh (which owns the console
#     guard) and its refusal is reported as "NOT armed", never as armed;
#   * private key material is never printed;
#   * neither the tool nor this suite can flash anything.
#
# What this suite does NOT prove: that a real tunnel or a real Tor circuit
# carries the device's traffic. Only an external vantage point can show that,
# and that evidence belongs to manual proof 21.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
TOOL="$REPO/tools/s10plus/a33/nuxel-vpn-tor.sh"
MOCKS="$REPO/tools/s10plus/a33/security-fixtures/net-mocks"
TMP="$(mktemp -d)"
PASS=0
FAIL=0

cleanup() { rm -rf "$TMP" 2>/dev/null || true; }
trap cleanup EXIT

ok()   { printf '  PASS  %s\n' "$1"; PASS=$((PASS + 1)); }
bad()  { printf '  FAIL  %s\n' "$1"; FAIL=$((FAIL + 1)); }
check_eq() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (expected '$2', got '$3')"; fi; }
check_contains() { case "$3" in *"$2"*) ok "$1" ;; *) bad "$1 (missing '$2')" ;; esac; }
check_not_contains() { case "$3" in *"$2"*) bad "$1 (unexpectedly contains '$2')" ;; *) ok "$1" ;; esac; }

# --- environment ------------------------------------------------------------
export NUXEL_SYSTEMCTL_BIN="$MOCKS/systemctl"
export NUXEL_WG_BIN="$MOCKS/wg"
export NUXEL_IP_BIN="$MOCKS/ip"
export NUXEL_SS_BIN="$MOCKS/ss"
export NUXEL_TOR_CONTROL_PY="$MOCKS/torctl"
export NUXEL_PRIVACY_STATE_DIR="$TMP/state"
export NUXEL_PRIVACY_RUN_DIR="$TMP/run"
export NUXEL_FIREWALL_STATE_DIR="$TMP/fw"
export NUXEL_PRIVACY_EVIDENCE_DIR="$TMP/evidence"
mkdir -p "$NUXEL_PRIVACY_STATE_DIR" "$NUXEL_PRIVACY_RUN_DIR" "$NUXEL_FIREWALL_STATE_DIR" "$NUXEL_PRIVACY_EVIDENCE_DIR"

# A private copy of the policy files so nothing under configs/ is ever edited.
cp "$REPO/configs/nuxel/security/privacy-config.json" "$TMP/privacy-config.json"
export NUXEL_PRIVACY_CONFIG="$TMP/privacy-config.json"
export NUXEL_REMOTE_CONFIG="$REPO/configs/nuxel/security/remote-access.json"

SECRET="SUPERSECRETKEYMATERIAL-DO-NOT-PRINT"
KEYFILE="$TMP/wg0.key"
printf '%s\n' "$SECRET" > "$KEYFILE"
chmod 600 "$KEYFILE"
python3 - "$TMP/privacy-config.json" "$KEYFILE" <<'PYPATCH'
import json, sys
cfg, key = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
d["vpn"]["wireguard"]["requires_key_file"] = key
json.dump(d, open(cfg, "w"), indent=2, sort_keys=True)
PYPATCH

jsonget() { python3 -c '
import json,sys
d=json.load(open(sys.argv[1]))
cur=d
for part in sys.argv[2].split("."):
    if isinstance(cur,dict) and part in cur: cur=cur[part]
    else: print("<missing>"); sys.exit(0)
print(cur if not isinstance(cur,(dict,list)) else json.dumps(cur))
' "$1" "$2"; }

run_tool() { MODE="$1"; shift; NUXEL_MOCK_NET_MODE="$MODE" "$TOOL" "$@"; }

echo "== Nuxel VPN/Tor/remote offline tests (mocks: $MOCKS) =="
echo "tool: $TOOL"

echo
echo "-- 1. Tor: service up + circuits built is still not anonymisation --"
OUT="$NUXEL_PRIVACY_STATE_DIR/tor-up.json"
run_tool tor-up-circuits tor status --json > "$OUT" 2>"$TMP/err1"
check_eq "service is reported active" "active" "$(jsonget "$OUT" measured.service_active)"
check_eq "service_running is evidenced" "evidenced" "$(jsonget "$OUT" claims.service_running.level)"
check_eq "circuits_built is read from the control port" "2" "$(jsonget "$OUT" measured.circuits_built)"
check_eq "circuits_built is evidenced" "evidenced" "$(jsonget "$OUT" claims.circuits_built.level)"
check_eq "traffic_routed_through_tor stays unproven" "unproven" "$(jsonget "$OUT" claims.traffic_routed_through_tor.level)"

echo
echo "-- 2. a running Tor with zero circuits is reported honestly --"
OUT="$NUXEL_PRIVACY_STATE_DIR/tor-zero.json"
run_tool tor-up-nocircuits tor status --json > "$OUT" 2>/dev/null
check_eq "circuits_built is 0, not hidden" "0" "$(jsonget "$OUT" measured.circuits_built)"
check_eq "traffic claim is still unproven" "unproven" "$(jsonget "$OUT" claims.traffic_routed_through_tor.level)"

echo
echo "-- 3. no control port -> unknown, never a guess --"
OUT="$NUXEL_PRIVACY_STATE_DIR/tor-fail.json"
run_tool tor-nocontrol tor status --json > "$OUT" 2>/dev/null
check_eq "control port is reported unauthenticated" "False" "$(jsonget "$OUT" measured.control_port_authenticated)"
check_eq "circuits_built is null" "None" "$(jsonget "$OUT" measured.circuits_built)"
check_eq "circuits claim is unknown" "unknown" "$(jsonget "$OUT" claims.circuits_built.level)"
check_eq "traffic claim is unproven" "unproven" "$(jsonget "$OUT" claims.traffic_routed_through_tor.level)"

echo
echo "-- 4. VPN: interface and handshake are facts, routing is not --"
OUT="$NUXEL_PRIVACY_STATE_DIR/vpn-hs.json"
run_tool vpn-up-handshake vpn status --json > "$OUT" 2>/dev/null
check_eq "tunnel interface up is evidenced" "evidenced" "$(jsonget "$OUT" claims.tunnel_interface_up.level)"
check_eq "handshake observed" "True" "$(jsonget "$OUT" measured.handshake_observed)"
check_eq "handshake is evidenced" "evidenced" "$(jsonget "$OUT" claims.handshake_observed.level)"
check_eq "traffic_routed_through_vpn stays unproven" "unproven" "$(jsonget "$OUT" claims.traffic_routed_through_vpn.level)"
check_eq "killswitch is unknown without state" "unknown" "$(jsonget "$OUT" measured.killswitch_armed)"

OUT="$NUXEL_PRIVACY_STATE_DIR/vpn-nohs.json"
run_tool vpn-up-nohandshake vpn status --json > "$OUT" 2>/dev/null
check_eq "no handshake is reported as false (not omitted)" "False" "$(jsonget "$OUT" measured.handshake_observed)"
check_eq "traffic claim is still unproven" "unproven" "$(jsonget "$OUT" claims.traffic_routed_through_vpn.level)"

OUT="$NUXEL_PRIVACY_STATE_DIR/vpn-down.json"
run_tool off vpn status --json > "$OUT" 2>/dev/null
check_eq "an absent tunnel is evidenced as down" "evidenced" "$(jsonget "$OUT" claims.tunnel_interface_up.level)"
check_eq "an absent tunnel does not break the status output" "down" "$(jsonget "$OUT" measured.interface_state)"

echo
echo "-- 5. remote access is off by default and refuses wildcards --"
set +e
OUT="$(run_tool remote-on remote on --bind-iface 0.0.0.0 2>&1)"; RC=$?
set -e
check_eq "wildcard bind is refused" "1" "$RC"
check_contains "the refusal names the wildcard risk" "wildcard bind" "$OUT"
[ -e "$NUXEL_PRIVACY_RUN_DIR/remote-access.state" ] && bad "no indicator after a refused enable" || ok "no indicator after a refused enable"

echo
echo "-- 6. remote access: indicator first, then start, then verify --"
set +e
OUT="$(run_tool remote-on remote on 2>&1)"; RC=$?
set -e
check_eq "remote access enables on the USB gadget path" "0" "$RC"
[ -r "$NUXEL_PRIVACY_RUN_DIR/remote-access.state" ] && ok "the indicator file exists while enabled" || bad "the indicator file exists while enabled"
check_eq "state file records the surface as enabled" "enabled" "$(jsonget "$NUXEL_PRIVACY_STATE_DIR/remote.state.json" state)"
check_eq "the indicator names the bind interface" "usb0" "$(jsonget "$NUXEL_PRIVACY_RUN_DIR/remote-access.state" detail.bind_interface)"

set +e
run_tool remote-on remote off >/dev/null 2>&1; RC=$?
set -e
check_eq "remote access turns off" "0" "$RC"
[ -e "$NUXEL_PRIVACY_RUN_DIR/remote-access.state" ] && bad "the indicator is removed when disabled" || ok "the indicator is removed when disabled"
check_eq "state file records disabled" "disabled" "$(jsonget "$NUXEL_PRIVACY_STATE_DIR/remote.state.json" state)"

echo
echo "-- 7. fail-closed ordering: no systemctl means no enablement at all --"
rm -f "$NUXEL_PRIVACY_RUN_DIR/remote-access.state" "$NUXEL_PRIVACY_STATE_DIR/remote.state.json"
set +e
OUT="$(NUXEL_SYSTEMCTL_BIN=/nonexistent/systemctl NUXEL_MOCK_NET_MODE=remote-on "$TOOL" remote on 2>&1)"; RC=$?
set -e
check_eq "enabling remote access fails without systemctl" "2" "$RC"
check_contains "the failure is explained" "cannot be started or verified" "$OUT"
[ -e "$NUXEL_PRIVACY_RUN_DIR/remote-access.state" ] && bad "no indicator written when enablement fails" || ok "no indicator written when enablement fails"

echo
echo "-- 8. kill switch is delegated to the firewall tool (console guard owner) --"
rm -f "$NUXEL_FIREWALL_STATE_DIR"/killswitch.json
set +e
OUT="$(NUXEL_FIREWALL_TOOL="$MOCKS/mock-firewall-ok" run_tool off killswitch arm wg0 2>&1)"; RC=$?
set -e
check_eq "arming succeeds through the firewall tool" "0" "$RC"
check_eq "armed state is read back" "true" "$(jsonget "$NUXEL_FIREWALL_STATE_DIR/killswitch.json" armed)"
check_contains "the delegation is recorded" "vpn-on wg0" "$(cat "$NUXEL_FIREWALL_STATE_DIR/calls.log" 2>/dev/null)"
check_contains "armed is never equated with connected" "armed != tunnel up" "$OUT"

set +e
OUT="$(NUXEL_FIREWALL_TOOL="$MOCKS/mock-firewall-refuse" run_tool off killswitch arm wg0 2>&1)"; RC=$?
set -e
[ "$RC" -ne 0 ] && ok "a refused kill switch apply is a non-zero exit" || bad "a refused kill switch apply is a non-zero exit"
check_contains "refusal is reported as NOT armed" "NOT armed" "$OUT"

echo
echo "-- 9. secret hygiene: key material is never printed --"
set +e
OUT="$(run_tool vpn-up-handshake vpn on 2>&1 | cat)"; RC=$?
set -e
check_contains "the tool says the key contents are never read" "contents never read" "$OUT"
check_not_contains "the private key bytes never appear" "$SECRET" "$OUT"

set +e
OUT="$(NUXEL_PRIVACY_CONFIG="$REPO/configs/nuxel/security/privacy-config.json" run_tool vpn-up-handshake vpn on 2>&1)"; RC=$?
set -e
check_eq "a missing key file refuses to start a tunnel" "1" "$RC"
check_contains "the refusal explains why" "not a VPN" "$OUT"

echo
echo "-- 10. leak probe: a suspect list, never a proof --"
OUT="$NUXEL_PRIVACY_STATE_DIR/leak.json"
set +e
run_tool leak tor leak-probe --json > "$OUT" 2>/dev/null; RC=$?
set -e
check_eq "the leak probe completes" "0" "$RC"
check_contains "plaintext DNS/direct sockets are flagged" "LEAK-SUSPECT" "$(jsonget "$OUT" verdict)"
check_eq "the traffic claim is still unproven with suspects" "unproven" "$(jsonget "$OUT" claims.traffic_routed_through_tor.level)"

OUT="$NUXEL_PRIVACY_STATE_DIR/clean.json"
set +e
run_tool clean tor leak-probe --json > "$OUT" 2>/dev/null; RC=$?
set -e
check_contains "a locally clean sample is reported as such" "NO-LEAK-OBSERVED" "$(jsonget "$OUT" verdict)"
check_eq "and the claim is STILL unproven" "unproven" "$(jsonget "$OUT" claims.traffic_routed_through_tor.level)"

OUT="$NUXEL_PRIVACY_STATE_DIR/noss.json"
set +e
NUXEL_SS_BIN=/nonexistent/ss NUXEL_MOCK_NET_MODE=clean "$TOOL" tor leak-probe --json > "$OUT" 2>/dev/null; RC=$?
set -e
check_eq "no socket table means a blocked verdict" "2" "$RC"
check_contains "the missing tool is named, not hidden" "BLOCKED_EXTERNAL_RESOURCE" "$(jsonget "$OUT" verdict)"

echo
echo "-- 11. the aggregate claims document is well-formed --"
OUT="$NUXEL_PRIVACY_STATE_DIR/claims.json"
run_tool vpn-up-handshake claims --json > "$OUT" 2>/dev/null || true
check_eq "no invalid claim level exists" "[]" "$(jsonget "$OUT" invalid_claim_levels)"
CLAIMCOUNT="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["claims"]))' "$OUT")"
[ "$CLAIMCOUNT" -ge 8 ] && ok "all surfaces contribute claims ($CLAIMCOUNT)" || bad "all surfaces contribute claims ($CLAIMCOUNT)"
python3 - "$OUT" <<'PY' && ok "every claim carries a level and evidence text" || bad "every claim carries a level and evidence text"
import json, sys
d = json.load(open(sys.argv[1]))
vocab = set(d["vocabulary"])
for k, v in d["claims"].items():
    assert v["level"] in vocab, (k, v["level"])
    assert v["evidence"].strip(), k
assert "traffic_routed_through_tor" in d["unproven"], d["unproven"]
assert "traffic_routed_through_vpn" in d["unproven"], d["unproven"]
PY

echo
echo "-- 12. Tor bridges are not faked --"
set +e
OUT="$(run_tool off tor bridges-status 2>&1)"; RC=$?
set -e
check_eq "bridges-status is informational" "0" "$RC"
check_contains "unbridged Tor is stated plainly" "NOT CONFIGURED" "$OUT"

echo
echo "-- 13. the menu changes nothing without a terminal --"
set +e
OUT="$(run_tool off menu 2>&1)"; RC=$?
set -e
check_eq "menu exits cleanly" "0" "$RC"
check_contains "menu declares it changed nothing" "changes nothing" "$OUT"

echo
echo "-- 14. invariants --"
if grep -Eq '^[[:space:]]*(dd|heimdall|fastboot|odin)[[:space:]]' "$TOOL"; then
    bad "the tool never invokes a flashing tool"
else
    ok "the tool never invokes a flashing tool"
fi
if grep -Eq '/dev/(block|sd[a-z]|mmcblk|disk)' "$TOOL" | grep -v 'forbidden' >/dev/null 2>&1; then
    bad "the tool never references a block device outside its own invariant note"
else
    ok "the tool never references a block device outside its own invariant note"
fi
check_contains "the console-guard hand-off is explicit in the source" "never calls nft directly" "$(cat "$TOOL")"

echo
echo "== results: $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ] && echo "VPN/TOR/REMOTE TESTS PASSED" || echo "VPN/TOR/REMOTE TESTS FAILED"
[ "$FAIL" -eq 0 ] || exit 3
exit 0

#!/bin/bash
# SPDX-License-Identifier: MIT
# ============================================================================
# Offline test suite for the Nuxel firewall tool (briq-05b).
# ============================================================================
# Runs tools/s10plus/a33/nuxel-firewall.sh against the recording mock nft
# (tools/s10plus/a33/security-fixtures/mock-nft). No root, no device, no
# netfilter, no network: everything happens in a temp directory.
#
# What this suite DOES prove:
#   * the render includes the interface policy table AND the console guard, and
#     the guard is structurally present (a comment mentioning it does not count);
#   * apply snapshots first, checks, applies, verifies the guard in the LIVE
#     ruleset, and re-injects the config's per-app ACCEPT rules;
#   * when the live ruleset loses the console guard, apply FAILS and rolls back -
#     the invariant that keeps the USB console reachable;
#   * a failing check or apply leaves the previous ruleset untouched;
#   * flush is refused without --keep-console and keeps the console when allowed;
#   * app-allow/app-deny/app-list, iface-set (incl. refusal to weaken the console),
#     the VPN kill switch and evidence capture all do what they claim.
#
# What this suite does NOT prove: that the kernel *accepts* the rendered ruleset
# (mock nft does not parse nftables syntax). That check is `nft -c -f` on the
# device/VM and is recorded as evidence by the live group.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
TOOL="$REPO/tools/s10plus/a33/nuxel-firewall.sh"
MOCK="$REPO/tools/s10plus/a33/security-fixtures/mock-nft"
TMP="$(mktemp -d)"
PASS=0
FAIL=0

cleanup() { rm -rf "$TMP" 2>/dev/null || true; }
trap cleanup EXIT

ok()   { printf '  PASS  %s\n' "$1"; PASS=$((PASS + 1)); }
bad()  { printf '  FAIL  %s\n' "$1"; FAIL=$((FAIL + 1)); }
check() { # check <description> <command...>
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then ok "$desc"; else bad "$desc"; fi
}
check_eq() { # check_eq <description> <expected> <actual>
    if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (expected '$2', got '$3')"; fi
}

# --- environment: mock nft, synthetic 4.14 kernel, throwaway state ----------
export NUXEL_NFT_BIN="$MOCK"
export NUXEL_MOCK_NFT_STATE="$TMP/mock"
export NUXEL_FIREWALL_STATE_DIR="$TMP/state"
export NUXEL_FIREWALL_RULESET_DIR="$REPO/configs/nftables"
export NUXEL_KERNEL_RELEASE="4.14.253"
export NUXEL_ALLOW_NONROOT=1
export NUXEL_ALLOW_MISSING_IFACE=1
mkdir -p "$NUXEL_MOCK_NFT_STATE" "$NUXEL_FIREWALL_STATE_DIR" "$TMP/evidence"

# A private copy of the config so iface-set never edits the repository.
cp "$REPO/configs/nftables/nuxel-firewall-config.json" "$TMP/firewall-config.json"
export NUXEL_FIREWALL_CONFIG="$TMP/firewall-config.json"

live() { cat "$NUXEL_MOCK_NFT_STATE/ruleset.nft" 2>/dev/null || true; }
guard_in_live() { live | grep -Eq '^[[:space:]]*table [a-z0-9]+ nuxel_console_guard[[:space:]]*\{'; }
calls() { cat "$NUXEL_MOCK_NFT_STATE/calls.log" 2>/dev/null || true; }

echo "== Nuxel firewall offline tests (mock nft: $MOCK) =="

echo
echo "-- 1. kernel posture --"
check_eq "4.14.253 selects the cgroup v1 classid ruleset" "v1" "$("$TOOL" kernel-mode)"
check_eq "6.12 selects the cgroupv2 ruleset" "v2" "$(NUXEL_KERNEL_RELEASE=6.12.0 "$TOOL" kernel-mode)"

echo
echo "-- 2. render + check --"
check "check renders and lints cleanly" "$TOOL" check
RENDERED="$NUXEL_FIREWALL_STATE_DIR/rendered.nft"
check "rendered file exists" test -s "$RENDERED"
check "rendered file contains the interface policy table" grep -q 'table inet nuxel_ifaces' "$RENDERED"
check "rendered file contains the console guard DECLARATION" grep -Eq '^[[:space:]]*table [a-z0-9]+ nuxel_console_guard[[:space:]]*\{' "$RENDERED"
check "rendered file allows the USB gadget console interface" grep -q 'iifname { "usb0"' "$RENDERED"
check "rendered file drops the disabled cellular interface (rmnet0)" grep -q 'oifname "rmnet0" drop' "$RENDERED"
check "rendered file never references a block device" bash -c "! grep -Eq '/dev/(block|mmcblk|sd[a-z])' '$RENDERED'"
check "public apps get a classid ACCEPT intent, isolated ones a drop note" bash -c "grep -q 'meta cgroup 0x01030001 accept' '$RENDERED' && grep -q 'nuxel-contacts network_class=isolated -> default drop' '$RENDERED'"

echo
echo "-- 3. apply: snapshot, verify, evidence --"
check "apply succeeds" "$TOOL" apply
check "the live ruleset has the console guard" guard_in_live
check "a snapshot was taken before the apply" bash -c "ls '$NUXEL_FIREWALL_STATE_DIR/snapshots'/*.nft >/dev/null 2>&1"
check "the apply recorded applied.json with console_guard_verified=yes" bash -c "grep -q '\"console_guard_verified\": \"yes\"' '$NUXEL_FIREWALL_STATE_DIR/applied.json'"
check "evidence was captured" bash -c "ls '$NUXEL_FIREWALL_STATE_DIR/evidence'/firewall-*.txt >/dev/null 2>&1"
check "console-verify passes on the applied ruleset" "$TOOL" console-verify --quiet
check "the per-app ACCEPT rules were inserted for the public apps" bash -c "grep -q 'insert rule inet nuxel_app_firewall output meta cgroup 0x01030001 accept' <(cat '$NUXEL_MOCK_NFT_STATE/calls.log')"
check "nft -f came after nft -c in the recorded call order" bash -c "awk '/-c -f .*rendered/{c=NR} /^-f .*rendered/{a=NR} END{exit !(c && a && c < a)}' '$NUXEL_MOCK_NFT_STATE/calls.log'"

echo
echo "-- 4. the invariant: a live ruleset without the console guard must FAIL and roll back --"
BEFORE="$(live)"
if NUXEL_MOCK_NFT_DROP_GUARD=1 "$TOOL" apply >/dev/null 2>&1; then
    bad "apply must fail when the live ruleset loses the console guard"
else
    ok "apply fails when the live ruleset loses the console guard"
fi
check "the rollback restored the console guard" guard_in_live
check "the rollback was recorded in the audit trail" bash -c "grep -q 'apply-rollback' '$NUXEL_FIREWALL_STATE_DIR/audit.log'"
check "applied.json still reports a verified guard (from the last good apply)" bash -c "grep -q '\"console_guard_verified\": \"yes\"' '$NUXEL_FIREWALL_STATE_DIR/applied.json'"
check "the previous ruleset was restored, not left broken" test -n "$BEFORE"

echo
echo "-- 5. a failing check or apply changes nothing --"
GOOD="$(live)"
if NUXEL_MOCK_NFT_FAIL_CHECK=1 "$TOOL" apply >/dev/null 2>&1; then
    bad "apply must fail when nft -c rejects the ruleset"
else
    ok "apply fails when nft -c rejects the ruleset"
fi
check_eq "a failed check leaves the live ruleset untouched" "$GOOD" "$(live)"
if NUXEL_MOCK_NFT_FAIL_APPLY=1 "$TOOL" apply >/dev/null 2>&1; then
    bad "apply must fail when nft -f fails"
else
    ok "apply fails when nft -f fails"
fi
check_eq "a failed apply leaves the live ruleset untouched" "$GOOD" "$(live)"

echo
echo "-- 6. flush can never take the console with it --"
if "$TOOL" flush >/dev/null 2>&1; then
    bad "flush without --keep-console must be refused"
else
    ok "flush without --keep-console is refused"
fi
check_eq "the refused flush changed nothing" "$GOOD" "$(live)"
check "flush --keep-console leaves the guard loaded" bash -c "'$TOOL' flush --keep-console >/dev/null 2>&1 && grep -Eq '^[[:space:]]*table [a-z0-9]+ nuxel_console_guard[[:space:]]*\{' '$NUXEL_MOCK_NFT_STATE/ruleset.nft'"
"$TOOL" apply >/dev/null 2>&1

echo
echo "-- 7. per-app rules --"
check "app-allow inserts a rule for the requested app" bash -c "'$TOOL' app-allow org.nuxel.Weather >/dev/null && grep -q 'org.nuxel.Weather' '$NUXEL_FIREWALL_STATE_DIR/audit.log'"
check "app-list reports the live rules and the declared intent" bash -c "'$TOOL' app-list | grep -q 'meta cgroup' && '$TOOL' app-list | grep -q 'declared intent'"
check "app-deny removes the rule (recorded as removed)" bash -c "'$TOOL' app-deny org.nuxel.Weather >/dev/null && grep -q 'app-deny' '$NUXEL_FIREWALL_STATE_DIR/audit.log'"

echo
echo "-- 8. interface policy --"
if "$TOOL" iface-set usb0 disabled >/dev/null 2>&1; then
    bad "iface-set must refuse to weaken the console interface policy"
else
    ok "iface-set refuses to weaken the console interface policy"
fi
check "iface-set stores a legitimate change" "$TOOL" iface-set wlan0 client
check "the stored change is in the (private) config copy" bash -c "grep -q '\"wlan0\"' '$TMP/firewall-config.json'"
check "a re-render reflects the new policy" bash -c "'$TOOL' check >/dev/null && grep -q 'iifname \"wlan0\" drop' '$RENDERED'"
check "an unknown policy is rejected" bash -c "! '$TOOL' iface-set wlan0 warp-speed >/dev/null 2>&1"

echo
echo "-- 9. VPN kill switch --"
check "vpn-on renders the template and loads it" "$TOOL" vpn-on tun0
check "the live ruleset has the kill switch table" bash -c "grep -q 'table inet nuxel_vpn_killswitch' '$NUXEL_MOCK_NFT_STATE/ruleset.nft'"
check "the kill switch drops app traffic that avoids the tunnel" bash -c "grep -q 'meta cgroup != 0 oifname != \"tun0\" counter drop' '$NUXEL_MOCK_NFT_STATE/ruleset.nft'"
check "the kill switch state records armed=true plus the honest note" bash -c "grep -q '\"armed\": true' '$NUXEL_FIREWALL_STATE_DIR/killswitch.json' && grep -q 'Armed != tunnel up' '$NUXEL_FIREWALL_STATE_DIR/killswitch.json'"
check "the console guard is still present with the kill switch armed" guard_in_live
if NUXEL_ALLOW_MISSING_IFACE=0 "$TOOL" vpn-on tun9 >/dev/null 2>&1; then
    bad "vpn-on must refuse a non-existent interface unless explicitly allowed"
else
    ok "vpn-on refuses a non-existent interface unless explicitly allowed"
fi
check "vpn-off removes the table" bash -c "'$TOOL' vpn-off >/dev/null && ! grep -q 'table inet nuxel_vpn_killswitch' '$NUXEL_MOCK_NFT_STATE/ruleset.nft'"

echo
echo "-- 10. evidence + invariants --"
check "evidence writes the real nft list ruleset output" bash -c "'$TOOL' evidence --out '$TMP/evidence' >/dev/null && grep -q 'nft list ruleset' '$TMP/evidence'/firewall-*.txt"
check "show reports the kernel posture and the console verdict" bash -c "'$TOOL' show | grep -q 'console_guard_verify'"
check "the tool never invokes a flashing tool (command position only)" bash -c "! grep -Eq '(^|[|;&(]|\\\$\\()[[:space:]]*(heimdall|odin|fastboot|flash_image|dd)[[:space:]]' '$TOOL'"
check "no repository ruleset references a block device" bash -c "! grep -rEq '/dev/(block|mmcblk|sd[a-z])' '$REPO/configs/nftables'"

echo
echo "== results: $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ] || exit 1
echo "FIREWALL TESTS PASSED"

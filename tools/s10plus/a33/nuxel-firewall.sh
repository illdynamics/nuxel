#!/bin/bash
# SPDX-License-Identifier: MIT
# ============================================================================
# nuxel-firewall.sh - Nuxel firewall control, staging, rollback and evidence
#                     (briq-05b)
# ============================================================================
# ACCESS TIER: repository-only + offline test. Live rule enforcement on the
# handset is performed (and evidenced) by the live-access group; this tool is
# what they run, and it is fully testable offline against a mock `nft`.
#
# INVARIANTS honoured here:
#   * NO FLASHING. This tool only ever calls `nft` (netlink) and writes files
#     under the snapshot/evidence directories. It never opens a block device.
#     An explicit guard refuses to proceed if a rendered ruleset contains a
#     device path, and refuses if `nft` is not resolvable.
#   * THE CONSOLE MUST SURVIVE. The console guard table is rendered from
#     configs/nftables/nuxel-console-guard.nft, loaded LAST (so the app ruleset's
#     `flush ruleset` cannot delete it) and verified after every apply by
#     re-reading the live ruleset. If the guard is missing afterwards, the tool
#     restores the previous ruleset immediately and exits non-zero.
#   * NO BLIND APPLY. Rules are rendered to a temp file, checked with
#     `nft -c -f`, snapshotted, applied atomically with `nft -f`, then verified.
#     Any failure reverts to the snapshot.
#   * NO UNPROVEN ENFORCEMENT. `show`/`evidence` print the REAL `nft list
#     ruleset` output; the tool never summarises a rule it could not list.
#
# Usage:
#   nuxel-firewall.sh kernel-mode
#   nuxel-firewall.sh classid <app-id>
#   nuxel-firewall.sh show | status
#   nuxel-firewall.sh check [--ruleset FILE]
#   nuxel-firewall.sh apply [--ruleset FILE] [--rollback-after SECONDS] [--dry-run]
#   nuxel-firewall.sh confirm
#   nuxel-firewall.sh rollback [SNAPSHOT]
#   nuxel-firewall.sh flush --keep-console
#   nuxel-firewall.sh console-verify
#   nuxel-firewall.sh app-allow <app-id> | app-deny <app-id> | app-list
#   nuxel-firewall.sh iface-list | iface-set <iface> <policy>
#   nuxel-firewall.sh vpn-on [iface] | vpn-off
#   nuxel-firewall.sh evidence [--out DIR]
#   nuxel-firewall.sh probe
#   nuxel-firewall.sh menu
#   nuxel-firewall.sh self-test
# ============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"

NFT_BIN="${NUXEL_NFT_BIN:-nft}"
NFT_STATE="${NUXEL_NFT_STATE:-}"           # mock nft live state dir
CONFIG="${NUXEL_FIREWALL_CONFIG:-$REPO_ROOT/configs/nftables/nuxel-firewall-config.json}"
STATE_DIR="${NUXEL_FIREWALL_STATE_DIR:-${NUXEL_FIREWALL_SNAPSHOT_DIR:-/var/lib/nuxel/firewall}}"
RULESET_DIR="${NUXEL_FIREWALL_RULESET_DIR:-$REPO_ROOT/configs/nftables}"
GUARD_FILE="$RULESET_DIR/nuxel-console-guard.nft"
CLASSID_RULESET="$RULESET_DIR/nuxel-app-firewall.nft"
CGROUPV2_RULESET="$RULESET_DIR/nuxel-app-firewall-cgroupv2.nft"
DRY_RUN="${NUXEL_DRY_RUN:-0}"

log()  { printf '[nuxel-firewall] %s\n' "$*" >&2; }
die()  { printf '[nuxel-firewall] ERROR: %s\n' "$*" >&2; exit 1; }
ok()   { printf '[nuxel-firewall] OK: %s\n' "$*"; }

# ---------------------------------------------------------------------------
# nft wrapper: every rule operation goes through here, and nowhere else.
# ---------------------------------------------------------------------------
nft_run() {
    if [ "$DRY_RUN" = "1" ]; then
        log "DRY-RUN: $NFT_BIN $*"
        return 0
    fi
    command -v "$NFT_BIN" >/dev/null 2>&1 || die "nft binary '$NFT_BIN' not found (install nftables or set NUXEL_NFT_BIN)"
    "$NFT_BIN" "$@"
}

nft_list_ruleset() {
    nft_run list ruleset 2>/dev/null || true
}

nft_list_table() {
    nft_run list table "$1" "$2" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Safety guards
# ---------------------------------------------------------------------------
assert_safe_ruleset() {
    local file="$1"
    [ -f "$file" ] || die "ruleset file not found: $file"
    # INVARIANT: no block-device writes, ever. A ruleset is a netfilter
    # description; a device path in it means somebody concatenated the wrong
    # file into it, which is exactly how a "firewall script" turns into a
    # flashing accident.
    if grep -Eq '/dev/(block|sd[a-z]|mmcblk|disk)' "$file"; then
        die "refusing to load $file: it references a block device path"
    fi
    if grep -Eq '^[[:space:]]*(dd|heimdall|fastboot|flash)[[:space:]]' "$file"; then
        die "refusing to load $file: it contains a device command"
    fi
    if ! grep -q 'flush ruleset\|table ' "$file"; then
        die "refusing to load $file: no nftables table found"
    fi
}

assert_guard_present() {
    local rendered="$1"
    # Structural, not textual: a comment that merely mentions the table name
    # must not satisfy this check (that is exactly how a guard goes missing
    # while the tool still reports success).
    grep -Eq '^[[:space:]]*table [a-z0-9]+ nuxel_console_guard[[:space:]]*\{' "$rendered" \
        || die "rendered ruleset $rendered has no console guard table - refusing to apply"
    grep -q 'type filter hook input priority -200' "$rendered" \
        || die "rendered ruleset $rendered has no console guard chain at priority -200 - refusing to apply"
    grep -Eq 'iifname \{ "usb0"' "$rendered" \
        || die "rendered ruleset $rendered does not allow the USB gadget console interface"
}

# ---------------------------------------------------------------------------
# Kernel posture
# ---------------------------------------------------------------------------
kernel_release() {
    # NUXEL_KERNEL_RELEASE lets the offline tests exercise the real 4.14 code
    # path (v1 classid matching) on a workstation whose uname says something
    # else. It is never set on the device.
    if [ -n "${NUXEL_KERNEL_RELEASE:-}" ]; then
        printf '%s' "$NUXEL_KERNEL_RELEASE"
        return
    fi
    uname -r 2>/dev/null || echo "unknown"
}

kernel_mode() {
    # v2 = socket cgroupv2 matches available (>= 5.13); v1 = net_cls classid.
    local rel major minor
    rel="$(kernel_release)"
    major="${rel%%.*}"; minor="${rel#*.}"; minor="${minor%%.*}"
    if [[ "$major" =~ ^[0-9]+$ ]] && [[ "$minor" =~ ^[0-9]+$ ]]; then
        if [ "$major" -gt 5 ] || { [ "$major" -eq 5 ] && [ "$minor" -ge 13 ]; }; then
            echo "v2"
            return
        fi
    fi
    echo "v1"
}

kernel_report() {
    local rel mode
    rel="$(kernel_release)"; mode="$(kernel_mode)"
    echo "kernel_release:   $rel"
    echo "per_app_match:    $([ "$mode" = v2 ] && echo 'socket cgroupv2 (level 2 path match)' || echo 'meta cgroup (cgroup v1 net_cls classid)')"
    echo "ruleset:          $([ "$mode" = v2 ] && echo "$CGROUPV2_RULESET" || echo "$CLASSID_RULESET")"
    echo "nft_binary:       $NFT_BIN"
    if [ -r /proc/sys/kernel/yama/ptrace_scope ]; then
        echo "landlock_abi:     $([ -e /proc/sys/kernel/landlock/abi_version ] && cat /proc/sys/kernel/landlock/abi_version || echo 'absent (no path-level filesystem confinement)')"
    fi
    if [ -r /sys/kernel/security/lsm ]; then
        echo "lsm_list:         $(cat /sys/kernel/security/lsm)"
    else
        echo "lsm_list:         unknown"
    fi
    echo "console_guard:    $GUARD_FILE"
    echo "dry_run:          $DRY_RUN"
}

# ---------------------------------------------------------------------------
# Deterministic per-app classid (must equal nuxel-permd.py _classid_for())
# ---------------------------------------------------------------------------
app_classid() {
    local app_id="$1"
    python3 - "$REPO_ROOT" "$app_id" << 'PY'
import json, os, sys, zlib
root, app_id = sys.argv[1], sys.argv[2]
reg = os.path.join(root, "configs/nuxel/app-registry/app_registry.json")
cid = None
if os.path.isfile(reg):
    try:
        with open(reg) as fh:
            for app in json.load(fh).get("apps", []):
                if app.get("app_id") == app_id:
                    cid = app.get("cgroup_classid")
                    break
    except Exception:
        cid = None
if not cid:
    cid = 0x01030000 | ((zlib.crc32(app_id.encode("utf-8")) % 0xFFFD) + 1)
print(int(cid))
PY
}

# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
render_ruleset() {
    local mode outfile
    mode="$(kernel_mode)"
    outfile="$1"
    {
        if [ "$mode" = "v2" ]; then
            cat "$CGROUPV2_RULESET"
        else
            cat "$CLASSID_RULESET"
        fi
        echo
        echo "# ---- interface policy table (rendered from $CONFIG) ----"
        render_iface_table
        echo
        echo "# ---- console guard (loaded after the flush above on purpose) ----"
        cat "$GUARD_FILE"
        echo
        echo "# ---- per-app ACCEPT *intent* from $CONFIG (see the note below) ----"
        echo "#      The live ACCEPT rules are inserted into the running output chain by"
        echo "#      'apply'/'app-allow'; a re-render therefore cannot duplicate them."
        if [ "$mode" = "v2" ]; then
            render_app_rules_v2
        else
            render_app_rules_v1
        fi
    } > "$outfile"
    assert_safe_ruleset "$outfile"
    assert_guard_present "$outfile"
}

cfg_apps() {
    python3 - "$CONFIG" << 'PY'
import json, sys
with open(sys.argv[1]) as fh:
    cfg = json.load(fh)
reg = {}
reg_path = sys.argv[1].replace("nftables/nuxel-firewall-config.json",
                               "nuxel/app-registry/app_registry.json")
try:
    with open(reg_path) as fh:
        for app in json.load(fh).get("apps", []):
            reg[app["app_id"]] = app
except Exception:
    pass
apps = dict(cfg.get("apps", {}))
apps.pop("_comment", None)
# merge registry entries that the config does not already pin down
for app_id, app in reg.items():
    apps.setdefault(app_id, {"network_class": app.get("network_class", "isolated"),
                             "classid": app.get("cgroup_classid")})
for app_id in sorted(apps):
    entry = apps[app_id]
    cls = entry.get("network_class", "isolated")
    cid = entry.get("classid") or 0
    print("%s %s %s" % (app_id, cls, cid))
PY
}


# ---------------------------------------------------------------------------
# Interface policy (rendered from $CONFIG into table inet nuxel_ifaces).
#
# Honesty rules encoded here:
#   * An interface whose policy is unknown or missing is rendered as DROP
#     ("fail closed") and a comment says so - never silently accepted.
#   * rmnet0 (cellular) is 'disabled' because the S10+ modem is not up; saying
#     so in the render means the file shows the truth instead of implying
#     cellular data is filtered when it simply does not exist.
#   * The console guard sits at priority -200, i.e. BEFORE this table (-150), so
#     no interface policy can lock the owner out of the USB gadget console.
# ---------------------------------------------------------------------------
render_iface_table() {
    python3 - "$CONFIG" << 'PY'
import json, sys

with open(sys.argv[1]) as fh:
    cfg = json.load(fh)
ifaces = {k: v for k, v in cfg.get("interfaces", {}).items() if not k.startswith("_")}

in_accept, in_client, in_drop = [], [], []
out_accept, out_drop = [], []

for name in sorted(ifaces):
    entry = ifaces[name] or {}
    policy = (entry.get("policy") or "disabled").strip().lower()
    note = entry.get("note", "")
    if policy in ("allow", "console"):
        in_accept.append((name, policy, note))
        out_accept.append((name, policy, note))
    elif policy == "client":
        in_client.append((name, policy, note))
        out_accept.append((name, policy, note))
    elif policy == "vpn":
        in_client.append((name, policy, note))
        out_accept.append((name, policy, note))
    elif policy == "disabled":
        in_drop.append((name, policy, note))
        out_drop.append((name, policy, note))
    else:
        # Unknown policy: fail closed and say so.
        in_drop.append((name, "unknown->drop", note))
        out_drop.append((name, "unknown->drop", note))

print("table inet nuxel_ifaces {")
print("    chain input {")
print("        type filter hook input priority -150; policy accept;")
for name, policy, note in in_accept:
    print('        # %s policy=%s%s' % (name, policy, (" - " + note) if note else ""))
    print('        iifname "%s" accept' % name)
for name, policy, note in in_client:
    print('        # %s policy=%s%s' % (name, policy, (" - " + note) if note else ""))
    print('        iifname "%s" ct state established,related accept' % name)
    print('        iifname "%s" udp dport { 67, 68 } accept' % name)
    print('        iifname "%s" icmp type { echo-reply, destination-unreachable, time-exceeded } accept' % name)
    print('        iifname "%s" drop' % name)
for name, policy, note in in_drop:
    print('        # %s policy=%s%s' % (name, policy, (" - " + note) if note else ""))
    print('        iifname "%s" drop' % name)
print("    }")
print("    chain output {")
print("        type filter hook output priority -150; policy accept;")
for name, policy, note in out_accept:
    print('        # %s policy=%s%s' % (name, policy, (" - " + note) if note else ""))
    print('        oifname "%s" accept' % name)
for name, policy, note in out_drop:
    print('        # %s policy=%s%s' % (name, policy, (" - " + note) if note else ""))
    print('        oifname "%s" drop' % name)
print("    }")
print("}")
PY
}

# ---------------------------------------------------------------------------
# Intent rendering: what the config SAYS each app is allowed. The live ACCEPT
# rules are injected into the running output chain by `apply` / `app-allow`
# (nft insert), never textually spliced into the base ruleset - that is how a
# firewall file ends up half-applied.
# ---------------------------------------------------------------------------
render_app_rules_v1() {
    local app_id cls cid
    while read -r app_id cls cid; do
        [ -n "$app_id" ] || continue
        if [ "$cls" != "public" ]; then
            printf '# %s network_class=%s -> default drop (no ACCEPT rule)\n' "$app_id" "$cls"
            continue
        fi
        if [ -z "$cid" ] || [ "$cid" = "0" ]; then
            cid="$(app_classid "$app_id")"
        fi
        printf '# %s network_class=%s -> meta cgroup 0x%08x accept\n' "$app_id" "$cls" "$cid"
    done < <(cfg_apps)
}

render_app_rules_v2() {
    local app_id cls cid cg
    while read -r app_id cls cid; do
        [ -n "$app_id" ] || continue
        cg="app-$(printf '%s' "$app_id" | tr '[:upper:]' '[:lower:]' | sed -e 's/[^a-z0-9-]/-/g' -e 's/--*/-/g' -e 's/^-//' -e 's/-$//')"
        if [ "$cls" = "public" ]; then
            printf '# %s network_class=%s -> socket cgroupv2 level 2 "%s" accept\n' "$app_id" "$cls" "$cg"
        else
            printf '# %s network_class=%s -> default drop\n' "$app_id" "$cls"
        fi
    done < <(cfg_apps)
}

# ===========================================================================
# Runtime helpers
# ===========================================================================
nft_available() { command -v "$NFT_BIN" >/dev/null 2>&1; }

# Mutating nft call. Refuses (loudly) when the binary is absent instead of
# pretending a rule was applied.
nft_run() {
    if [ "$DRY_RUN" = "1" ]; then
        log "DRY-RUN: $NFT_BIN $*"
        return 0
    fi
    nft_available || die "nft binary '$NFT_BIN' not found (install nftables or set NUXEL_NFT_BIN)"
    "$NFT_BIN" "$@"
}

# Read-only nft call: never fatal, returns 127 when nft is unavailable so the
# caller can say "unknown" rather than "empty".
nft_read() {
    nft_available || return 127
    "$NFT_BIN" "$@" 2>/dev/null
}

nft_list_ruleset() { nft_read list ruleset || true; }

require_root() {
    if [ "$DRY_RUN" = "1" ]; then return 0; fi
    if [ "${NUXEL_ALLOW_NONROOT:-0}" = "1" ]; then return 0; fi
    if [ "$(id -u)" != "0" ]; then
        die "this operation needs root (CAP_NET_ADMIN); run it as root or set NUXEL_ALLOW_NONROOT=1 for a dry run"
    fi
}

state_dir() { printf '%s' "$STATE_DIR"; }
snapshot_dir() { printf '%s/snapshots' "$STATE_DIR"; }
evidence_dir() { printf '%s/evidence' "$STATE_DIR"; }
ensure_dirs() { mkdir -p "$STATE_DIR" "$(snapshot_dir)" "$(evidence_dir)" 2>/dev/null || true; }

timestamp() { date -u +%Y%m%dT%H%M%SZ; }

write_applied_state() {
    # $1 = rendered file, $2 = guard_verified(yes/no), $3 = rollback_deadline
    local rendered="$1" guard="$2" deadline="$3" sha mode
    sha="$( (sha256sum "$rendered" 2>/dev/null || shasum -a 256 "$rendered" 2>/dev/null) | awk '{print $1}')"
    mode="$(kernel_mode)"
    ensure_dirs
    python3 - "$STATE_DIR/applied.json" << PY
import json, os, sys, time
path = sys.argv[1]
rec = {
    "applied_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "kernel_release": "$(kernel_release)",
    "per_app_match": "$mode",
    "rendered_ruleset": "$rendered",
    "rendered_sha256": "$sha",
    "console_guard_verified": "$guard",
    "rollback_deadline": "$deadline",
    "applied_by_uid": os.getuid(),
    "note": "Written by nuxel-firewall.sh. 'console_guard_verified=no' means the ruleset is NOT in a state we would call applied.",
}
try:
    old = json.load(open(path))
except Exception:
    old = {}
rec["previous_applied_at"] = old.get("applied_at")
with open(path + ".tmp", "w") as fh:
    json.dump(rec, fh, indent=2, sort_keys=True)
    fh.write("\n")
os.replace(path + ".tmp", path)
PY
}

# ===========================================================================
# Commands
# ===========================================================================
do_kernel_report() { kernel_report; }

# Rejection of a rendered ruleset on structural grounds that do not need the
# kernel: balanced braces, at least one table, no device paths. This is a real
# check that runs everywhere; `nft -c` is the authoritative syntax check and is
# additionally attempted whenever an nft binary is present.
lint_ruleset() {
    local file="$1" opens closes tables
    opens="$(grep -o '{' "$file" | wc -l | tr -d ' ')"
    closes="$(grep -o '}' "$file" | wc -l | tr -d ' ')"
    tables="$(grep -c '^table ' "$file" || true)"
    if [ "$opens" != "$closes" ]; then
        printf 'LINT FAIL: unbalanced braces in %s (%s open / %s close)\n' "$file" "$opens" "$closes"
        return 1
    fi
    if [ "${tables:-0}" -lt 1 ]; then
        printf 'LINT FAIL: %s declares no table\n' "$file"
        return 1
    fi
    if grep -Eq '/dev/(block|sd[a-z]|mmcblk|disk|mapper)' "$file"; then
        printf 'LINT FAIL: %s references a block device path (INVARIANT violation)\n' "$file"
        return 1
    fi
    printf 'LINT PASS: %s (%s tables, braces balanced)\n' "$file" "$tables"
    return 0
}

do_check() {
    local file=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --ruleset) file="${2:-}"; shift 2 ;;
            *) shift ;;
        esac
    done
    if [ -z "$file" ]; then
        ensure_dirs
        file="$STATE_DIR/rendered.nft"
        render_ruleset "$file"
    else
        [ -f "$file" ] || die "ruleset not found: $file"
    fi
    local rc=0
    lint_ruleset "$file" || rc=1
    if nft_available; then
        if nft_run -c -f "$file"; then
            ok "nft -c accepted $file"
        else
            log "nft -c REJECTED $file"
            rc=1
        fi
    else
        log "nft binary '$NFT_BIN' not available: structural lint only (nft -c is authoritative and runs on-device)"
    fi
    if [ -f "$file" ] && grep -Eq '^[[:space:]]*table [a-z0-9]+ nuxel_console_guard[[:space:]]*\{' "$file"; then
        echo "console guard present in $file"
    else
        log "console guard MISSING from $file"
        rc=1
    fi
    return $rc
}

do_apply() {
    local file="" rollback_after=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --ruleset) file="${2:-}"; shift 2 ;;
            --rollback-after) rollback_after="${2:-0}"; shift 2 ;;
            --no-rollback-timer) rollback_after=0; shift ;;
            --dry-run) DRY_RUN=1; shift ;;
            *) shift ;;
        esac
    done
    require_root
    ensure_dirs
    if [ -z "$file" ]; then
        file="$STATE_DIR/rendered.nft"
        render_ruleset "$file"
    fi
    lint_ruleset "$file" || die "refusing to apply: structural lint failed"
    assert_safe_ruleset "$file"
    assert_guard_present "$file"

    # Snapshot the current ruleset BEFORE touching anything (baseline discipline).
    local snap
    snap="$(snapshot_dir)/$(timestamp).nft"
    if nft_read list ruleset > "$snap" 2>/dev/null && [ -s "$snap" ]; then
        ok "snapshot of the live ruleset: $snap"
    else
        : > "$snap"
        log "no live ruleset to snapshot (first apply or nft unavailable) - wrote empty $snap"
    fi

    if ! do_check --ruleset "$file"; then
        die "refusing to apply: check failed (previous ruleset left untouched)"
    fi

    if ! nft_run -f "$file"; then
        log "nft -f FAILED; restoring snapshot $snap"
        nft_run -f "$snap" || log "snapshot restore also failed - device may be without app rules (console path unaffected)"
        return 1
    fi
    ok "ruleset applied from $file"

    # Inject the per-app ACCEPT rules from the config (idempotent: the base
    # ruleset just flushed everything).
    apply_config_app_rules

    # The one thing that must never fail silently.
    if ! do_console_verify --quiet; then
        log "CONSOLE GUARD MISSING after apply: rolling back immediately"
        nft_run -f "$snap" || log "rollback failed - inspect with '$0 show'"
        record_audit "apply-rollback" "console guard missing after apply"
        if do_console_verify --quiet; then
            log "rollback restored the console guard (verify with '$0 console-verify')"
        else
            log "STILL NO CONSOLE GUARD after rollback - fix now: nft -f $GUARD_FILE"
        fi
        return 1
    fi
    ok "console guard verified in the live ruleset"

    local deadline=""
    if [ "$rollback_after" != "0" ]; then
        arm_rollback_timer "$rollback_after" "$snap"
        deadline="$(date -u -v+${rollback_after}S +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d "+${rollback_after} seconds" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
        printf '\nAPPLY IS UNCONFIRMED. Run "%s confirm" within %ss or the previous ruleset is restored.\n\n' "$0" "$rollback_after"
    fi

    write_applied_state "$file" "yes" "$deadline"
    record_audit "apply" "ruleset=$file rollback_after=${rollback_after}s"
    do_evidence --quiet || true
    echo
    echo "--- evidence: nft list ruleset (as applied) ---"
    nft_list_ruleset | sed -n '1,80p'
    return 0
}

arm_rollback_timer() {
    local secs="$1" snap="$2" pidfile="$STATE_DIR/rollback.timer"
    [ -f "$STATE_DIR/confirm.token" ] && rm -f "$STATE_DIR/confirm.token"
    (
        sleep "$secs"
        if [ -f "$STATE_DIR/confirm.token" ]; then
            exit 0
        fi
        "$NFT_BIN" -f "$snap" 2>/dev/null || true
        printf 'ROLLED BACK after %ss without confirmation (snapshot %s)\n' "$secs" "$snap" \
            >> "$STATE_DIR/rollback.log" 2>/dev/null || true
    ) >/dev/null 2>&1 &
    echo "$!" > "$pidfile"
    ok "rollback timer armed (pid $(cat "$pidfile"), ${secs}s, snapshot $snap)"
}

do_confirm() {
    ensure_dirs
    : > "$STATE_DIR/confirm.token"
    if [ -f "$STATE_DIR/rollback.timer" ]; then
        kill "$(cat "$STATE_DIR/rollback.timer")" 2>/dev/null || true
        rm -f "$STATE_DIR/rollback.timer"
    fi
    ok "apply confirmed; rollback timer disarmed"
    record_audit "confirm" "operator confirmed the applied ruleset"
}

do_rollback() {
    local snap="${1:-}"
    require_root
    ensure_dirs
    if [ -z "$snap" ]; then
        snap="$(ls -1t "$(snapshot_dir)"/*.nft 2>/dev/null | sed -n 1p || true)"
    fi
    [ -n "$snap" ] && [ -f "$snap" ] || die "no snapshot to roll back to (looked in $(snapshot_dir))"
    nft_run -f "$snap" || die "rollback load failed"
    ok "rolled back to $snap"
    record_audit "rollback" "ruleset=$snap"
    do_console_verify --quiet || log "console guard missing after rollback - investigate now"
}

do_flush() {
    local keep_console=0
    for arg in "$@"; do
        [ "$arg" = "--keep-console" ] && keep_console=1
    done
    if [ "$keep_console" != "1" ]; then
        die "flush without --keep-console is refused: the USB console path must always survive (invariant)"
    fi
    require_root
    ensure_dirs
    local snap="$STATE_DIR/pre-flush.nft"
    nft_read list ruleset > "$snap" 2>/dev/null || true
    nft_run flush ruleset || die "nft flush ruleset failed"
    if ! nft_run -f "$GUARD_FILE"; then
        log "guard re-load failed after flush; restoring $snap"
        nft_run -f "$snap" || log "restore failed"
        return 1
    fi
    ok "ruleset flushed; console guard re-loaded from $GUARD_FILE (console path intact)"
    record_audit "flush" "keep-console=1 snapshot=$snap"
}

do_console_verify() {
    local quiet=0
    [ "${1:-}" = "--quiet" ] && quiet=1
    local live
    live="$(nft_read list ruleset || true)"
    if [ -z "$live" ]; then
        if [ "$quiet" = "1" ]; then return 1; fi
        echo "console-verify: UNKNOWN - no live ruleset readable (nft missing or empty ruleset)"
        return 2
    fi
    local rc=0
    # Structural checks: the table DECLARATION, the guard chain priority, and the
    # gadget-interface accept. Comments that mention these strings must not be
    # able to satisfy the verifier.
    printf '%s' "$live" | grep -Eq '^[[:space:]]*table [a-z0-9]+ nuxel_console_guard[[:space:]]*\{' || rc=1
    printf '%s' "$live" | grep -q 'type filter hook input priority -200' || rc=1
    printf '%s' "$live" | grep -Eq 'iifname \{ "usb0"' || rc=1
    if [ "$quiet" != "1" ]; then
        if [ "$rc" = "0" ]; then
            echo "console-verify: PASS - nuxel_console_guard is loaded and the USB gadget interface is accepted"
            printf '%s' "$live" | grep -A4 'chain guard' | head -8
        else
            echo "console-verify: FAIL - console guard table or USB gadget accept is missing from the live ruleset"
            echo "                 fix with: $0 rollback   (or: nft -f $GUARD_FILE)"
        fi
    fi
    return $rc
}

# --- per-app rules ---------------------------------------------------------
live_app_rules() {
    # Only the injected per-app ACCEPT rules. The base ruleset's own
    # 'meta cgroup 0' (unclassified/system traffic) lines must not be reported
    # as an app rule, so match the classid form explicitly.
    nft_read -a list chain inet nuxel_app_firewall output 2>/dev/null \
        | grep -E 'meta cgroup 0x[0-9a-fA-F]+ accept|socket cgroupv2 level 2 "app-[^"]*" accept' \
        || true
}

app_rule_spec() {
    # Emits nothing; sets globals APP_RULE_MATCH. Kept as a function so the v1/v2
    # difference lives in exactly one place.
    local app_id="$1" cid
    if [ "$(kernel_mode)" = "v2" ]; then
        local cg
        cg="app-$(printf '%s' "$app_id" | tr '[:upper:]' '[:lower:]' | sed -e 's/[^a-z0-9-]/-/g' -e 's/--*/-/g' -e 's/^-//' -e 's/-$//')"
        APP_RULE_MATCH=("socket" "cgroupv2" "level" "2" "$cg")
    else
        cid="$(app_classid "$app_id")"
        APP_RULE_MATCH=("meta" "cgroup" "0x$(printf '%08x' "$cid")")
    fi
}

apply_config_app_rules() {
    local app_id cls cid
    while read -r app_id cls cid; do
        [ -n "$app_id" ] || continue
        [ "$cls" = "public" ] || continue
        APP_RULE_MATCH=()
        app_rule_spec "$app_id"
        nft_run insert rule inet nuxel_app_firewall output "${APP_RULE_MATCH[@]}" accept \
            && ok "network allowed: $app_id (${APP_RULE_MATCH[*]})" \
            || log "could not insert ACCEPT rule for $app_id"
    done < <(cfg_apps)
}

do_app_allow() {
    local app_id="${1:-}"
    [ -n "$app_id" ] || die "usage: $0 app-allow <app-id>"
    require_root
    APP_RULE_MATCH=()
    app_rule_spec "$app_id"
    nft_run insert rule inet nuxel_app_firewall output "${APP_RULE_MATCH[@]}" accept
    ok "ACCEPT rule inserted for $app_id (${APP_RULE_MATCH[*]})"
    record_audit "app-allow" "$app_id ${APP_RULE_MATCH[*]}"
    echo "NOTE: this is a runtime rule. To make it survive a re-apply, add to $CONFIG:"
    echo "      \"$app_id\": {\"network_class\": \"public\"}"
}

do_app_deny() {
    local app_id="${1:-}"
    [ -n "$app_id" ] || die "usage: $0 app-deny <app-id>"
    require_root
    APP_RULE_MATCH=()
    app_rule_spec "$app_id"
    local needle="${APP_RULE_MATCH[*]}" removed=0 handle
    while :; do
        # '|| true' matters: with `set -e -o pipefail`, a grep that finds no
        # remaining rule would abort the whole command instead of ending the loop.
        handle="$(nft_read -a list chain inet nuxel_app_firewall output 2>/dev/null \
                  | grep -F "$needle" | sed -n 1p | awk '{print $NF}' || true)"
        [ -n "${handle:-}" ] || break
        nft_run delete rule inet nuxel_app_firewall output handle "$handle" || break
        removed=$((removed + 1))
    done
    ok "removed $removed ACCEPT rule(s) for $app_id (default drop now applies)"
    record_audit "app-deny" "$app_id removed=$removed"
}

do_app_list() {
    echo "=== per-app network rules (live) ==="
    local live
    live="$(live_app_rules)"
    if [ -z "$live" ]; then
        if nft_available; then
            echo "  (no classid ACCEPT rules in the live output chain)"
        else
            echo "  UNKNOWN - nft is not available, so no live rule can be shown"
        fi
    else
        printf '%s\n' "$live" | sed 's/^[[:space:]]*/  /'
    fi
    echo
    echo "=== declared intent (from $CONFIG + the app registry) ==="
    cfg_apps | while read -r app_id cls cid; do
        printf '  %-24s %-9s classid=%s\n' "$app_id" "$cls" "${cid:-auto}"
    done
}

do_iface_list() {
    python3 - "$CONFIG" << 'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print("=== interface policy (config: %s) ===" % sys.argv[1])
for name in sorted(cfg.get("interfaces", {})):
    entry = cfg["interfaces"][name] or {}
    print("  %-10s %-9s %s" % (name, entry.get("policy", "?"), entry.get("note", "")))
print()
print("console_protection.enabled =", cfg.get("console_protection", {}).get("enabled"))
print("console interfaces          =", ", ".join(cfg.get("console_protection", {}).get("interfaces", [])))
PY
}

do_iface_set() {
    local iface="${1:-}" policy="${2:-}"
    [ -n "$iface" ] && [ -n "$policy" ] || die "usage: $0 iface-set <iface> <allow|console|client|vpn|disabled>"
    case "$policy" in
        allow|console|client|vpn|disabled) ;;
        *) die "unknown policy '$policy' (allow|console|client|vpn|disabled)" ;;
    esac
    if [ "$iface" = "usb0" ] || [ "$iface" = "rndis0" ] || [ "$iface" = "ncm0" ]; then
        [ "$policy" = "console" ] || [ "$policy" = "allow" ] \
            || die "refusing to set policy '$policy' on the console interface $iface (INVARIANT: the console path must survive)"
    fi
    [ -w "$CONFIG" ] || die "config $CONFIG is not writable (on-device it lives in /etc/nftables; re-run as root)"
    ensure_dirs
    cp -f "$CONFIG" "$(snapshot_dir)/config-$(timestamp).json"
    python3 - "$CONFIG" "$iface" "$policy" << 'PY'
import json, sys
path, iface, policy = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as fh:
    cfg = json.load(fh)
cfg.setdefault("interfaces", {})[iface] = dict(cfg.get("interfaces", {}).get(iface) or {}, policy=policy)
with open(path + ".tmp", "w") as fh:
    json.dump(cfg, fh, indent=2, sort_keys=True)
    fh.write("\n")
import os
os.replace(path + ".tmp", path)
print("config updated: %s -> %s" % (iface, policy))
PY
    ok "interface policy stored. Re-render and apply to enforce it:"
    echo "  $0 check && $0 apply"
}

# --- VPN kill switch -------------------------------------------------------
killswitch_table() { printf 'nuxel_vpn_killswitch'; }  # table name used by vpn-off / status

do_vpn_on() {
    local iface="${1:-tun0}"
    local tmpl="$RULESET_DIR/nuxel-vpn-killswitch.nft"
    require_root
    ensure_dirs
    [ -f "$tmpl" ] || die "kill switch template not found: $tmpl"
    # NUXEL_ALLOW_MISSING_IFACE exists so an owner can pre-arm the switch before
    # the tunnel exists (e.g. at boot, when wg0 is created later). Without it a
    # missing interface is refused, because "armed" would then silently mean
    # "all app traffic blocked".
    if [ "${NUXEL_ALLOW_MISSING_IFACE:-0}" != "1" ] && ! ip link show "$iface" >/dev/null 2>&1; then
        die "interface '$iface' does not exist: refusing to arm the kill switch (set NUXEL_ALLOW_MISSING_IFACE=1 to arm anyway, which blocks app traffic until the tunnel appears)"
    fi
    local match
    if [ "$(kernel_mode)" = "v2" ]; then
        match='socket cgroupv2 level 2 "app-"'
    else
        match='meta cgroup != 0'
    fi
    local rendered="$STATE_DIR/killswitch-rendered.nft"
    sed -e "s|__IFACE__|$iface|g" -e "s|__MATCH__|$match|g" "$tmpl" > "$rendered"
    lint_ruleset "$rendered" >/dev/null || die "rendered kill switch failed lint"
    if ! nft_run -f "$rendered"; then
        die "could not load the kill switch table (previous state unchanged)"
    fi
    ok "kill switch armed: app traffic may only leave via $iface (table inet nuxel_vpn_killswitch, priority -110)"
    python3 - "$STATE_DIR/killswitch.json" "$iface" "$rendered" << 'PY'
import json, os, sys, time
rec = {
    "armed": True,
    "iface": sys.argv[2],
    "rendered_from": sys.argv[3],
    "armed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "scope": "app-classified traffic only (classid != 0 on 4.14 / app-* cgroups on >= 5.13); system traffic and the console are unaffected",
    "honest_note": "Armed != tunnel up. Evidence: nft list table inet nuxel_vpn_killswitch; tunnel state: nuxel-vpn-tor.sh vpn status.",
}
tmp = sys.argv[1] + ".tmp"
with open(tmp, "w") as fh:
    json.dump(rec, fh, indent=2, sort_keys=True)
    fh.write("\n")
os.replace(tmp, sys.argv[1])
PY
    record_audit "vpn-on" "iface=$iface rendered=$rendered"
    echo "--- live kill switch table (evidence) ---"
    nft_read list table inet nuxel_vpn_killswitch || echo "  (nft unavailable: rule not shown)"
}

do_vpn_off() {
    require_root
    ensure_dirs
    nft_run delete table inet "$(killswitch_table)" 2>/dev/null || true
    python3 - "$STATE_DIR/killswitch.json" << 'PY'
import json, os, sys, time
rec = {"armed": False, "disarmed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
tmp = sys.argv[1] + ".tmp"
with open(tmp, "w") as fh:
    json.dump(rec, fh, indent=2, sort_keys=True)
    fh.write("\n")
os.replace(tmp, sys.argv[1])
PY
    ok "kill switch disarmed"
    record_audit "vpn-off" ""
}

do_evidence() {
    local quiet=0 out=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --quiet) quiet=1; shift ;;
            --out) out="${2:-}"; shift 2 ;;
            *) shift ;;
        esac
    done
    ensure_dirs
    [ -z "$out" ] && out="${NUXEL_FIREWALL_EVIDENCE_DIR:-$(evidence_dir)}"
    mkdir -p "$out" 2>/dev/null || true
    local ts; ts="$(timestamp)"
    {
        echo "## nuxel-firewall evidence $ts"
        echo "## kernel: $(kernel_release)  per_app_match: $(kernel_mode)"
        echo
        echo "\$ nft list ruleset"
        nft_list_ruleset || echo "(nft unavailable)"
    } > "$out/firewall-$ts.txt"
    if nft_available; then
        nft_read list table inet nuxel_console_guard >> "$out/firewall-$ts.txt" 2>/dev/null || true
    fi
    echo "$out/firewall-$ts.txt"
    if [ "$quiet" != "1" ]; then
        echo "--- live ruleset (truncated to 60 lines; full copy in $out/firewall-$ts.txt) ---"
        sed -n '1,60p' "$out/firewall-$ts.txt"
    fi
}

do_probe() {
    echo "=== kernel capability probe (what this kernel can actually enforce) ==="
    echo "kernel_release: $(kernel_release)"
    if ! nft_available; then
        echo "nft:            NOT AVAILABLE - cannot probe; run on the device/VM"
        echo "verdict:        UNKNOWN (no nft binary)"
        return 2
    fi
    local tmp; tmp="$(mktemp)"
    printf 'table inet probe { chain c { meta cgroup 0x01030001 accept } }\n' > "$tmp"
    if nft -c -f "$tmp" 2>/dev/null; then
        echo "meta cgroup:     SUPPORTED (cgroup v1 net_cls classid match works)"
    else
        echo "meta cgroup:     NOT SUPPORTED by this kernel/nft -> per-app network control is BLOCKED_KERNEL"
    fi
    printf 'table inet probe { chain c { socket cgroupv2 level 2 "app-x" accept } }\n' > "$tmp"
    if nft -c -f "$tmp" 2>/dev/null; then
        echo "socket cgroupv2: SUPPORTED (needs Linux >= 5.13)"
    else
        echo "socket cgroupv2: not supported here (expected on 4.14)"
    fi
    printf 'table inet probe { chain c { log prefix "probe" limit rate 1/minute } }\n' > "$tmp"
    if nft -c -f "$tmp" 2>/dev/null; then
        echo "log+limit:       SUPPORTED"
    else
        echo "log+limit:       NOT SUPPORTED"
    fi
    nft -c -f "$GUARD_FILE" 2>/dev/null && echo "console guard:   parses cleanly" || echo "console guard:   DOES NOT PARSE - fix before applying"
    rm -f "$tmp"
}

record_audit() {
    local action="$1" detail="$2"
    ensure_dirs
    python3 - "$STATE_DIR/audit.log" "$action" "$detail" << 'PY'
import json, sys, time, os
path, action, detail = sys.argv[1], sys.argv[2], sys.argv[3]
rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "action": action, "detail": detail, "uid": os.getuid(), "tool": "nuxel-firewall.sh"}
try:
    with open(path, "a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
except Exception:
    pass
PY
}

do_show() {
    echo "=== Nuxel firewall status ==="
    kernel_report
    echo
    echo "console_guard_verify: $(do_console_verify --quiet >/dev/null 2>&1 && echo PASS || echo 'FAIL/UNKNOWN')"
    if [ -f "$STATE_DIR/killswitch.json" ]; then
        echo "killswitch:"
        python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1])), indent=2, sort_keys=True))' \
            "$STATE_DIR/killswitch.json" | sed 's/^/  /'
    else
        echo "killswitch:           never armed on this boot"
    fi
    if [ -f "$STATE_DIR/applied.json" ]; then
        echo "last_applied:"
        python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1])), indent=2, sort_keys=True))' \
            "$STATE_DIR/applied.json" | sed 's/^/  /'
    else
        echo "last_applied:         no apply recorded in $STATE_DIR"
    fi
    echo
    do_app_list
    echo
    do_iface_list
    echo
    echo "=== live ruleset (first 40 lines) ==="
    nft_list_ruleset | sed -n '1,40p'
}

do_menu() {
    cat << 'MENU'
Nuxel firewall menu
  1) status / show
  2) kernel capability probe
  3) render + check (no change)
  4) apply (with 60s confirmation window)
  5) confirm current apply
  6) rollback to the newest snapshot
  7) per-app rules
  8) interface policy
  9) VPN kill switch on/off
 10) capture evidence
MENU
    if [ ! -t 0 ] && [ "${NUXEL_MENU_ASSUME_TTY:-0}" != "1" ]; then
        echo "(stdin is not a terminal: the menu is non-interactive on purpose and does nothing without an operator)"
        return 0
    fi
    printf 'choice> '
    read -r choice || choice=""
    case "$choice" in
        1) do_show ;;
        2) do_probe ;;
        3) do_check ;;
        4) do_apply --rollback-after 60 ;;
        5) do_confirm ;;
        6) do_rollback ;;
        7) do_app_list ;;
        8) do_iface_list ;;
        9) printf 'iface (default tun0)> '; read -r i || i=""; do_vpn_on "${i:-tun0}" ;;
        10) do_evidence ;;
        *) echo "no change" ;;
    esac
}

do_self_test() {
    # Offline self-test: runs the tool against the mock nft that ships in the
    # repository, so the staging/rollback/guard logic is executable with no
    # device, no root and no network.
    local mock="$REPO_ROOT/tools/s10plus/a33/security-fixtures/mock-nft"
    [ -x "$mock" ] || die "mock nft not found/executable: $mock"
    local tmp; tmp="$(mktemp -d)"
    local rc=0
    export NUXEL_NFT_BIN="$mock"
    export NUXEL_MOCK_NFT_STATE="$tmp/mock-state"
    export NUXEL_FIREWALL_STATE_DIR="$tmp/state"
    export NUXEL_ALLOW_NONROOT=1
    mkdir -p "$NUXEL_MOCK_NFT_STATE" "$NUXEL_FIREWALL_STATE_DIR"
    echo "== self-test (mock nft: $mock) =="
    "$REPO_ROOT/tools/s10plus/a33/security-tests/test-firewall.sh" --in-place || rc=1
    rm -rf "$tmp"
    if [ "$rc" = "0" ]; then ok "self-test PASSED"; else log "self-test FAILED"; fi
    return $rc
}

# ===========================================================================
# Dispatch
# ===========================================================================
cmd="${1:-help}"
[ $# -gt 0 ] && shift || true
case "$cmd" in
    kernel-mode)   kernel_mode ;;
    kernel-report) do_kernel_report ;;
    classid)       app_classid "${1:-}" ;;
    probe)         do_probe ;;
    show|status)   do_show ;;
    check)         do_check "$@" ;;
    apply)         do_apply "$@" ;;
    confirm)       do_confirm ;;
    rollback)      do_rollback "$@" ;;
    flush)         do_flush "$@" ;;
    console-verify) do_console_verify "$@" ;;
    app-allow)     do_app_allow "$@" ;;
    app-deny)      do_app_deny "$@" ;;
    app-list)      do_app_list ;;
    iface-list)    do_iface_list ;;
    iface-set)     do_iface_set "$@" ;;
    vpn-on)        do_vpn_on "$@" ;;
    vpn-off)       do_vpn_off ;;
    evidence)      do_evidence "$@" ;;
    menu)          do_menu ;;
    self-test)     do_self_test ;;
    help|-h|--help)
        sed -n '27,43p' "$0" | sed 's/^# \{0,1\}//'
        cat << 'HELP'

Notes:
  * Nothing here touches a block device, a bootloader or a partition - this tool
    only calls nft (netlink) and writes under the state/evidence directories.
  * 'apply' snapshots the live ruleset, renders, lints, 'nft -c's, applies,
    re-injects the config's per-app ACCEPT rules, then verifies the console
    guard in the LIVE ruleset and rolls back if it is missing.
  * Offline testing: NUXEL_NFT_BIN=tools/s10plus/a33/security-fixtures/mock-nft
    (or simply run 'self-test').
HELP
        ;;
    *)
        die "unknown command '$cmd' (try: $0 help)"
        ;;
esac

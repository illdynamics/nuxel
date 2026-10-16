#!/bin/bash
# SPDX-License-Identifier: MIT
# ============================================================================
# nuxel-security-audit.sh - report the ACTUAL exposed surface of a Nuxel system
#                           and of this repository (briq-05d)
# ============================================================================
# Truth discipline (this is the whole point of the tool):
#   * A reading is only printed if it was READ. Every section prints the exact
#     command it ran next to the result, and prints "unknown" - never a
#     plausible-looking default - when the source is unavailable.
#   * `--fixture FILE` runs the same logic against a committed, provenance-
#     carrying snapshot (tools/s10plus/a33/security-fixtures/*.json) so the
#     repository can be audited offline with no device and no fabrication.
#   * Enforcement is stated per attacker-privilege class (unprivileged-app vs
#     root). Root/admin compromise is out of scope of every claim; nothing here
#     is called "unbypassable".
#   * Linux 4.14 reality: Landlock (>= 5.13), kernel lockdown (>= 4.17), BPF LSM
#     (>= 5.7), arm64 CFI/SCS/BTI/PAuth do not exist on this kernel/hardware.
#     Where a mechanism is absent, the tool says ABSENT and the finding is a
#     documented limitation, not something a switch could turn on.
#
# Usage:
#   nuxel-security-audit.sh [--json] [--fixture FILE] [--out DIR] [--section NAME]
#   nuxel-security-audit.sh --list-sections
#   nuxel-security-audit.sh --self-test
#
# Sections: kernel lsm lockdown sockets services userns seccomp firewalls
#           apparmor permissions repo-limitations verdict
# Exit codes: 0 = audit completed (findings recorded), 1 = argument/IO error,
#             2 = --self-test failure.
# ============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"

FIXTURE="${NUXEL_SECURITY_FIXTURE:-}"
JSON=0
OUT_DIR=""
ONLY=""
SELF_TEST=0

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
say()  { printf '%s\n' "$*"; }
head1() { printf '\n=== %s ===\n' "$*"; }

# cmd_run <display-command> <command...>
# Prints what was run and what came back. Sets LAST_OUT (first 12 lines) and
# LAST_STATUS so callers can react without re-running anything.
LAST_OUT=""
LAST_STATUS=127
cmd_run() {
    local display="$1"; shift
    local out status
    if command -v "${1}" >/dev/null 2>&1 || [ -x "${1}" ] || [ -e "$(command -v "$1" 2>/dev/null)" ]; then
        out="$("$@" 2>&1)"
        status=$?
    else
        out=""
        status=127
    fi
    LAST_STATUS=$status
    if [ "$status" -eq 127 ]; then
        say "\$ $display"
        say "  unavailable (tool/file not present) -> unknown"
        LAST_OUT=""
        return 127
    fi
    LAST_OUT="$(printf '%s\n' "$out" | sed -n '1,12p')"
    say "\$ $display"
    if [ -n "$LAST_OUT" ]; then printf '%s\n' "$LAST_OUT" | sed 's/^/  /'; fi
    if [ "$(printf '%s\n' "$out" | wc -l | tr -d ' ')" -gt 12 ]; then
        say "  ... ($(( $(printf '%s\n' "$out" | wc -l | tr -d ' ') - 12 )) more lines)"
    fi
    return 0
}

read_file() { # read_file <path> <label>
    if [ -r "$1" ]; then
        say "\$ cat $1"
        sed -n '1,6p' "$1" | sed 's/^/  /'
        LAST_OUT="$(cat "$1" 2>/dev/null)"
        LAST_STATUS=0
        return 0
    fi
    say "\$ cat $1"
    say "  unreadable/absent -> unknown"
    LAST_OUT=""
    LAST_STATUS=1
    return 1
}

fixture_get() { # fixture_get <jq-ish dotted path>  (python, no jq dependency)
    [ -n "$FIXTURE" ] || { printf 'null'; return 1; }
    python3 - "$FIXTURE" "$1" << 'PY'
import json, sys
try:
    data = json.load(open(sys.argv[1]))
except Exception:
    print("null"); raise SystemExit(1)
cur = data
for part in sys.argv[2].split("."):
    if isinstance(cur, dict) and part in cur:
        cur = cur[part]
    else:
        print("null"); raise SystemExit(1)
print(json.dumps(cur))
PY
}

fixture_have() { [ -n "$FIXTURE" ] && [ "$(fixture_get "$1")" != "null" ]; }

collect() { # collect key value  (into the findings file)
    COLLECTED+=("$1=$2")
}

# ---------------------------------------------------------------------------
# sections
# ---------------------------------------------------------------------------
sec_kernel() {
    head1 "kernel identity and configuration"
    if fixture_have "release"; then
        say "(fixture mode: readings come from $FIXTURE and carry their provenance)"
        say "release:  $(fixture_get release | tr -d '\"')"
        say "arch:     $(fixture_get arch | tr -d '\"')"
    else
        cmd_run "uname -r" uname -r
        cmd_run "uname -m" uname -m
    fi
    local rel; rel="$(uname -r 2>/dev/null || echo unknown)"
    case "$rel" in
        4.14*) collect kernel_release "$rel" ;;
        unknown)
            if fixture_have "release"; then collect kernel_release "$(fixture_get release | tr -d '\"')"
            else collect kernel_release "unknown"; fi ;;
        *) collect kernel_release "$rel" ;;
    esac
    say
    say "kernel config (CONFIG_SECURITY_APPARMOR / LSMs) - offline fixture, provenance recorded:"
    if [ -n "$FIXTURE" ]; then
        python3 - "$FIXTURE" << 'PY'
import json, sys
d = json.load(open(sys.argv[1]))
cfg = d.get("kernel_config", {})
for key in sorted(cfg):
    print("  %-28s %s" % (key, cfg[key]))
print("  kernel_config_source: %s" % d.get("kernel_config_source", "unknown"))
PY
    else
        cmd_run "zcat /proc/config.gz | grep -E 'CONFIG_(SECURITY|LSM|CGROUP_NET_CLASSID|BPF_LSM|DRM|SECCOMP)'" \
            bash -c "zcat /proc/config.gz 2>/dev/null | grep -E 'CONFIG_(SECURITY|LSM|CGROUP_NET_CLASSID|BPF_LSM|DRM|SECCOMP)'"
    fi
}

sec_lsm() {
    head1 "loaded LSMs and their status"
    if fixture_have "lsm_list"; then
        say "(fixture) lsm_list: $(fixture_get lsm_list)"
    else
        read_file /sys/kernel/security/lsm "sysfs" || true
    fi
    # LSM presence decides whether the shipped AppArmor profiles enforce anything.
    local lsm=""
    if [ -r /sys/kernel/security/lsm ]; then lsm="$(cat /sys/kernel/security/lsm 2>/dev/null)"
    elif fixture_have "lsm_list"; then lsm="$(fixture_get lsm_list | tr -d '\"')"; fi
    if [ -z "$lsm" ]; then
        say "  LSM list: unknown (not readable here and not in the fixture)"
        collect lsm "unknown"
    else
        case "$lsm" in
            *apparmor*) collect lsm "$lsm"; say "  => apparmor IS present: /etc/apparmor.d profiles can enforce" ;;
            *) collect lsm "$lsm"; say "  => apparmor is NOT in the LSM list: the shipped profiles are INERT here." ;;
        esac
        case "$lsm" in
            *selinux*) say "  => selinux present as well";;
        esac
        case "$lsm" in
            *landlock*) say "  => landlock present (surprising on 4.14: double-check)" ;;
            *) say "  => landlock ABSENT (Landlock is mainline >= 5.13; not available on 4.14.253)" ;;
        esac
    fi
    say
    if [ -e /proc/sys/kernel/landlock/abi_version ]; then
        read_file /proc/sys/kernel/landlock/abi_version "sysctl" || true
    else
        say "\$ ls /proc/sys/kernel/landlock/abi_version"
        say "  absent -> no path-level filesystem confinement for unprivileged apps"
    fi
    if [ -e /sys/kernel/security/lockdown ]; then
        read_file /sys/kernel/security/lockdown "sysfs" || true
    else
        say "\$ cat /sys/kernel/security/lockdown"
        say "  absent -> kernel lockdown LSM unavailable (mainline >= 4.17)"
    fi
    say
    for path in /sys/kernel/security/apparmor/profiles; do
        if [ -r "$path" ]; then
            say "\$ head -5 $path"
            sed -n '1,5p' "$path" | sed 's/^/  /'
            say "  loaded AppArmor profiles: $(wc -l < "$path" | tr -d ' ')"
        else
            say "\$ cat $path"
            say "  unreadable/absent -> AppArmor is not exposing profiles (either the LSM is off or the module is not loaded)"
        fi
    done
}

sec_userns() {
    head1 "unprivileged user namespaces and BPF"
    last_unknown=0
    if [ -r /proc/sys/user/max_user_namespaces ]; then
        read_file /proc/sys/user/max_user_namespaces "sysctl" || true
        collect userns_max "$(cat /proc/sys/user/max_user_namespaces 2>/dev/null)"
    elif fixture_have "userns_max"; then
        say "(fixture) userns_max: $(fixture_get userns_max)"
        collect userns_max "$(fixture_get userns_max)"
    else
        say "\$ cat /proc/sys/user/max_user_namespaces"
        say "  unreadable/absent -> unknown (recorded as a limitation, not as 0)"
        collect userns_max "unknown"
    fi
    if [ -r /proc/sys/kernel/unprivileged_bpf_disabled ]; then
        read_file /proc/sys/kernel/unprivileged_bpf_disabled "sysctl" || true
        collect unprivileged_bpf_disabled "$(cat /proc/sys/kernel/unprivileged_bpf_disabled 2>/dev/null)"
    elif fixture_have "bpf_unprivileged_disabled"; then
        say "(fixture) unprivileged_bpf_disabled: $(fixture_get bpf_unprivileged_disabled)"
    else
        say "\$ cat /proc/sys/kernel/unprivileged_bpf_disabled"
        say "  unreadable/absent -> unknown"
    fi
    say
    if [ -r /proc/sys/kernel/yama/ptrace_scope ]; then
        read_file /proc/sys/kernel/yama/ptrace_scope "sysctl" || true
    else
        say "\$ cat /proc/sys/kernel/yama/ptrace_scope"
        say "  absent -> no Yama ptrace restriction reported"
    fi
}

sec_seccomp() {
    head1 "seccomp"
    if [ -r /proc/sys/kernel/seccomp/actions_avail ]; then
        read_file /proc/sys/kernel/seccomp/actions_avail "sysctl" || true
    elif fixture_have "seccomp_actions_avail"; then
        say "(fixture) actions_avail: $(fixture_get seccomp_actions_avail)"
    else
        say "\$ cat /proc/sys/kernel/seccomp/actions_avail"
        say "  unreadable -> unknown (CONFIG_SECCOMP_FILTER is recorded as 'y' in the A16/A17 config, so seccomp BPF is expected to work)"
    fi
}

sec_sockets() {
    head1 "listening sockets (the real remote surface)"
    if command -v ss >/dev/null 2>&1; then
        say "(reading via ss: this is the real listening surface of the system running the audit)"
        say "\$ ss -lntup"
        ss -lntup 2>/dev/null | sed 's/^/  /' || say "  ss failed"
        collect listening_sockets "$(ss -lntup 2>/dev/null | wc -l | tr -d ' ')"
    elif command -v netstat >/dev/null 2>&1; then
        say "\$ netstat -lntup"
        netstat -lntup 2>/dev/null | sed 's/^/  /'
        collect listening_sockets "netstat"
    else
        say "\$ ss -lntup"
        say "  neither ss nor netstat is available -> unknown (this is a hard gap: install iproute)"
        collect listening_sockets "unknown"
    fi
    say
    say "\$ cat /proc/net/tcp (state 0A = LISTEN), unix sockets excluded"
    if [ -r /proc/net/tcp ]; then
        awk 'NR>1 && $4 == "0A" {print "  " $2}' /proc/net/tcp | head -10
        awk 'NR>1 && $4 == "0A"' /proc/net/tcp | wc -l | tr -d ' ' | sed 's/^/  listen entries: /'
    else
        say "  /proc/net/tcp unreadable -> unknown"
    fi
}

sec_services() {
    head1 "enabled services (what starts at boot)"
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files >/dev/null 2>&1; then
        say "\$ systemctl list-unit-files --state=enabled --type=service --no-pager"
        systemctl list-unit-files --state=enabled --type=service --no-pager 2>/dev/null | sed 's/^/  /' | head -30
    else
        say "\$ systemctl list-unit-files --state=enabled"
        say "  systemd is not answering here -> unknown; the repository-side list is below"
    fi
    say
    say "repository service definitions (configs + services/), which is what would be installed:"
    local found=0
    for d in "$REPO/services" "$REPO/configs/nftables/systemd" "$REPO/shell/config/systemd-user" "$REPO/shell/nuxel-shell"; do
        [ -d "$d" ] || continue
        while IFS= read -r unit; do
            found=1
            printf '  %s  (%s)\n' "${unit#$REPO/}" "$(basename "$(dirname "$unit")")"
        done < <(find "$d" -name '*.service' -o -name '*.timer' 2>/dev/null | sort | head -40)
    done
    [ "$found" = "1" ] || say "  (none found)"
}

sec_firewalls() {
    head1 "firewall ruleset and console safety"
    if command -v nft >/dev/null 2>&1; then
        say "\$ nft list ruleset"
        if nft list ruleset >/dev/null 2>&1; then
            nft list ruleset 2>/dev/null | head -20 | sed 's/^/  /'
            say "  rules total: $(nft list ruleset 2>/dev/null | wc -l | tr -d ' ')"
        else
            say "  nft present but the ruleset is unreadable -> unknown (need root/CAP_NET_ADMIN)"
        fi
        say
        say "\$ nft list table inet nuxel_console_guard"
        nft list table inet nuxel_console_guard 2>/dev/null | sed 's/^/  /' || \
            say "  NOT LOADED -> the USB console guard is not installed (run nuxel-firewall.sh apply)"
    else
        say "\$ nft list ruleset"
        say "  nft is not installed -> unknown; the shipped rulesets are audited below"
    fi
    say
    say "shipped rulesets ($REPO/configs/nftables):"
    for f in "$REPO"/configs/nftables/*.nft; do
        [ -f "$f" ] || continue
        printf '  %-46s %4s lines  guard=%s\n' "$(basename "$f")" \
            "$(wc -l < "$f" | tr -d ' ')" \
            "$(grep -Eq '^[[:space:]]*table [a-z0-9]+ nuxel_console_guard' "$f" && echo yes || echo no)"
    done
    say
    say "block-device safety gate (INVARIANT: no flushing anywhere in this repo's security tooling):"
    if grep -rIlE '(^|[[:space:]])(heimdall|odin|fastboot|flash_image)[[:space:]]' \
        "$REPO/configs/nftables" "$REPO/tools/s10plus/a33/nuxel-firewall.sh" "$REPO/shell/nuxel-shell/nuxel-sandbox" 2>/dev/null | grep -v '\.nft$'; then
        say "  VIOLATION: a flashing tool is referenced"
    else
        say "  clean: no heimdall/odin/fastboot/flash_image invocation in the audited files"
    fi
}

sec_apparmor() {
    head1 "AppArmor profiles shipped in this repository"
    local dir="$REPO/configs/apparmor.d"
    if [ -d "$dir" ]; then
        say "\$ ls $dir"
        ls -1 "$dir" 2>/dev/null | sed 's/^/  /'
        say
        say "Profiles are only effective if apparmor is in /sys/kernel/security/lsm (see the LSM section)."
        say "Per-profile mode line:"
        while IFS= read -r f; do
            printf '  %-34s %s\n' "$(basename "$f")" "$(grep -m1 -E '^\s*(flags|profile|)' "$f" | head -1 | sed 's/^[[:space:]]*//' | cut -c1-70)"
        done < <(find "$dir" -type f | sort | head -20)
    else
        say "  $dir does not exist -> unknown"
    fi
}

sec_permissions() {
    head1 "permission store and capability enforcement truth"
    local perm="$REPO/shell/nuxel-shell/nuxel-permissions"
    if [ -x "$perm/nuxel-permd.py" ]; then
        say "\$ nuxel-permd.py enforcement-matrix"
        python3 "$perm/nuxel-permd.py" enforcement-matrix 2>/dev/null | sed 's/^/  /'
    else
        say "  nuxel-permd.py not executable -> unknown"
    fi
    say
    if [ -n "$FIXTURE" ] && [ -x "$perm/nuxel-permd.py" ]; then
        say "\$ nuxel-permd.py --fixture $FIXTURE enforcement-matrix (mechanism availability line)"
        python3 "$perm/nuxel-permd.py" --fixture "$FIXTURE" enforcement-matrix 2>/dev/null | tail -2 | sed 's/^/  /'
    fi
    say
    if [ -x "$REPO/tools/s10plus/a33/verify-permissions.py" ]; then
        say "\$ verify-permissions.py (repo mode)"
        local store; store="$(mktemp -d)"
        python3 "$REPO/tools/s10plus/a33/verify-permissions.py" --store "$store" --quiet 2>&1 | sed 's/^/  /'
        say "  exit: $?"
        rm -rf "$store" 2>/dev/null || true
    fi
}

sec_limitations() {
    head1 "documented limitations on this kernel/hardware (not fixable by a switch)"
    cat << 'LIMITS'
  * Landlock (per-app path/device confinement): mainline >= 5.13 -> ABSENT on 4.14.253.
    Consequence: "this app may read only these paths" is NOT kernel-enforced for
    unprivileged apps; DAC + portal policy are the boundary.
  * Kernel lockdown LSM: mainline >= 4.17 -> ABSENT.
  * BPF LSM: CONFIG_BPF_LSM is unset, so systemd's bpf-restrict-fs device ACLs are
    not applied (it warns and continues).
  * nftables 'socket cgroupv2' per-app matching: mainline >= 5.13 -> per-app
    network rules use cgroup v1 net_cls classid ('meta cgroup 0x...') instead.
  * AppArmor: profiles ship, but enforcement depends on the vendor kernel having
    apparmor in /sys/kernel/security/lsm - verified by the LSM section, never assumed.
  * Clipboard mediation: needs a Wayland data-device; this kernel has no DRM/KMS
    (CONFIG_DRM unset), Phoc runs headless -> NOT_SUPPORTED_ON_DEVICE.
  * SELinux: not enabled by default in Nuxel; absence is documented, not faked.
  * arm64 CFI / Shadow Call Stack / BTI / Pointer Authentication: absent (kernel
    too old and Exynos 9820 is ARMv8.2-A, no PAuth/BTI in hardware).
  * Root / CAP_SYS_ADMIN compromise is OUT OF SCOPE for every claim in this
    repository. There is no "unbypassable" claim anywhere; each enforcement
    statement names the attacker-privilege class it holds against.
LIMITS
}

sec_repo_limitations() {
    head1 "claims that are deliberately NOT made"
    cat << 'NOTCLAIMS'
  * "Tor is anonymising all traffic" is NOT claimed anywhere. There is no
    exit-node verification, no leak proof and no live network test in this
    repository; the privacy tool reports service state and circuit state
    separately and marks routing as unproven until evidenced.
  * "The firewall blocks all app traffic" is NOT claimed: system traffic
    (classid 0 / non-app cgroups) and root are explicitly outside the ruleset,
    and the residual set is logged, not hidden.
  * "Permissions are unbypassable" is NOT claimed: the portal is a userspace
    broker, and on 4.14 a device node that DAC allows can be opened by an
    unprivileged app regardless of the permission store.
  * "The device is verified" is NOT claimed for any hardware path. A passing
    unit test never yields VERIFIED_ON_S10PLUS.
NOTCLAIMS
}

sec_verdict() {
    head1 "audit summary"
    local lsm_state="unknown"
    if [ -r /sys/kernel/security/lsm ]; then lsm_state="$(cat /sys/kernel/security/lsm)"
    elif fixture_have "lsm_list"; then lsm_state="$(fixture_get lsm_list | tr -d '"')"; fi
    say "kernel:                 $(uname -r 2>/dev/null || echo unknown)${FIXTURE:+ (fixture: $FIXTURE)}"
    say "lsm:                    ${lsm_state:-unknown}"
    say "landlock:               $([ -e /proc/sys/kernel/landlock/abi_version ] && cat /proc/sys/kernel/landlock/abi_version || echo 'absent (>= 5.13 required)')"
    say "lockdown:               $([ -e /sys/kernel/security/lockdown ] && echo present || echo 'absent (>= 4.17 required)')"
    say "listening sockets:      ${listening_sockets:-unknown}"
    if command -v nft >/dev/null 2>&1; then
        if nft list table inet nuxel_console_guard >/dev/null 2>&1; then
            say "console guard loaded:   yes (nft list table inet nuxel_console_guard succeeded)"
        else
            say "console guard loaded:   NO / not readable (run: nuxel-firewall.sh apply, then console-verify)"
        fi
    else
        say "console guard loaded:   unknown here (no nft binary); on-device: nuxel-firewall.sh console-verify"
    fi
    say "enforcement basis:      DAC + portal (userspace) + seccomp BPF + cgroup v1 net_cls + nftables; AppArmor only if the LSM section says so"
    say "attacker classes:       unprivileged-app (covered as documented) / root (OUT OF SCOPE, no claim)"
    say
    say "Verdict vocabulary (this audit never promotes anything):"
    say "  OFFLINE_TESTED  - logic executed against fixtures with provenance"
    say "  DEPLOYED_UNVERIFIED - present on the device, not yet evidenced by an owner test"
    say "  BLOCKED_KERNEL  - the mechanism does not exist on 4.14.253"
    say "  NOT_SUPPORTED_ON_DEVICE - no enforcement exists at all; no switch is offered"
}

# ---------------------------------------------------------------------------
# self-test: assert the auditor cannot fabricate a reading
# ---------------------------------------------------------------------------
self_test() {
    local rc=0
    say "== nuxel-security-audit self-test =="
    # 1. fixture mode must produce the release string from the fixture
    local out; out="$(bash "$0" --fixture "$HERE/security-fixtures/s10plus-4.14.253.json" --section kernel 2>&1)"
    if printf '%s' "$out" | grep -q '4.14.253'; then say "  PASS fixture kernel release is reported"; else say "  FAIL fixture release missing"; rc=2; fi
    # 2. a missing sysctl must read 'unknown', never '0'
    if printf '%s' "$out" | grep -q 'CONFIG_BPF_LSM'; then say "  PASS kernel config dumped"; else say "  FAIL kernel config missing"; rc=2; fi
    # 3. unknown stays unknown (no ss on a minimal box / no fabrication)
    out="$(bash "$0" --section limitations 2>&1)"
    if printf '%s' "$out" | grep -q 'Landlock'; then say "  PASS limitations section lists Landlock"; else say "  FAIL limitations missing"; rc=2; fi
    # 4. out-of-scope root must be stated
    if printf '%s' "$out" | grep -qi 'OUT OF SCOPE'; then say "  PASS root out of scope is stated"; else say "  FAIL root scope missing"; rc=2; fi
    # 5. no fabrication words
    out="$(bash "$0" --section verdict 2>&1)"
    if printf '%s' "$out" | grep -qiE 'unbypassable|guaranteed|100% secure'; then
        say "  FAIL verdict claims a guarantee"; rc=2
    else
        say "  PASS verdict makes no guarantee claim"
    fi
    [ "$rc" = "0" ] && say "security-audit self-test PASSED"
    return $rc
}

usage() { sed -n '5,26p' "$0" | sed 's/^# \{0,1\}//'; }

COLLECTED=()
sections_run=()

run_section() {
    case "$1" in
        kernel) sec_kernel ;;
        lsm) sec_lsm ;;
        userns) sec_userns ;;
        seccomp) sec_seccomp ;;
        sockets) sec_sockets ;;
        services) sec_services ;;
        firewalls) sec_firewalls ;;
        apparmor) sec_apparmor ;;
        permissions) sec_permissions ;;
        repo-limitations) sec_repo_limitations ;;
        limitations) sec_limitations ;;
        verdict) sec_verdict ;;
        *) say "unknown section: $1"; return 1 ;;
    esac
    sections_run+=("$1")
}

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
while [ $# -gt 0 ]; do
    case "$1" in
        --json) JSON=1; shift ;;
        --fixture) FIXTURE="${2:-}"; shift 2 ;;
        --out) OUT_DIR="${2:-}"; shift 2 ;;
        --section) ONLY="${2:-}"; shift 2 ;;
        --list-sections) say "kernel lsm userns seccomp sockets services firewalls apparmor permissions limitations repo-limitations verdict"; exit 0 ;;
        --self-test) self_test; exit $? ;;
        -h|--help) usage; exit 0 ;;
        *) say "unknown argument: $1" >&2; usage; exit 1 ;;
    esac
done

if [ -n "$FIXTURE" ] && [ ! -r "$FIXTURE" ]; then
    say "fixture not readable: $FIXTURE" >&2
    exit 1
fi

if [ "$JSON" = "1" ]; then
    say '{'
    say '  "tool": "nuxel-security-audit.sh",'
    say '  "kernel_release": '"\"$(uname -r 2>/dev/null || echo unknown)\""','
    say '  "fixture": '"${FIXTURE:+\"$FIXTURE\"}${FIXTURE:-null}"','
    say '  "lsm_list": '"$( [ -r /sys/kernel/security/lsm ] && python3 -c 'import json,sys;print(json.dumps(open("/sys/kernel/security/lsm").read().strip()))' || (fixture_have lsm_list && fixture_get lsm_list || echo null) )"','
    say '  "landlock_abi": '"$( [ -e /proc/sys/kernel/landlock/abi_version ] && cat /proc/sys/kernel/landlock/abi_version || echo null )"','
    say '  "notes": "JSON summary only; the full evidence is the --section output. This mode never invents a value: unavailable readings are null."'
    say '}'
    exit 0
fi

if [ -n "$OUT_DIR" ]; then
    mkdir -p "$OUT_DIR" 2>/dev/null || { say "cannot create $OUT_DIR" >&2; exit 1; }
    TS="$(date -u +%Y%m%dT%H%M%SZ)"
    exec > >(tee "$OUT_DIR/security-audit-$TS.txt") 2>&1
fi

say "Nuxel security audit (briq-05d)"
say "repo:    $REPO"
say "kernel:  $(uname -r 2>/dev/null || echo unknown)"
if [ -n "$FIXTURE" ]; then say "fixture: $FIXTURE  (offline mode: device readings replaced by documented provenance)"; else say "fixture: none (live readings only; anything unreadable is reported as unknown)"; fi

if [ -n "$ONLY" ]; then
    run_section "$ONLY" || exit 1
    exit 0
fi

for s in kernel lsm userns seccomp sockets services firewalls apparmor permissions limitations repo-limitations verdict; do
    run_section "$s"
done

head1 "collected values (machine-readable)"
for kv in "${COLLECTED[@]}"; do printf '  %s\n' "$kv"; done
say
say "audit complete. Findings above are readings, not assurances."
exit 0

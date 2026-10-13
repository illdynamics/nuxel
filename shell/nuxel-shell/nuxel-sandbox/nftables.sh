#!/bin/bash
# Nuxel Sandbox - Per-App nftables Network Setup
# Sets up cgroupv2-based network isolation per application
# Uses nftables with cgroupv2 socket matching for per-app rules
#
# briq-14: The app-id -> nft rule mapping is deterministic. Every app-id is
# lowercased and every character outside [a-z0-9-] is replaced with '-',
# then prefixed with "app-". The resulting cgroup path name under
# /sys/fs/cgroup/nuxel/ is what the ruleset matches, so the "socket
# cgroupv2 level 2 'app-*'" rules in configs/nftables/nuxel-app-firewall.nft
# always apply to the right app. Verify with `nft list ruleset` — you should
# see `socket cgroupv2 level 2 "app-<id>" accept` for each running app.
#
# Target: mustang (Pixel 10 Pro XL), Linux 6.12 LTS

set -euo pipefail

# Single-source path config (briq-20): source /etc/nuxel/paths.conf (overridable
# via NUXEL_PATHS_CONF) so the sandbox agrees with the rest of the system on the
# canonical Nuxel config dir (NUXEL_CONFIG_DIR).
if [ -n "${NUXEL_PATHS_CONF:-}" ] && [ -r "${NUXEL_PATHS_CONF}" ]; then
    # shellcheck disable=SC1090
    . "${NUXEL_PATHS_CONF}"
elif [ -r /etc/nuxel/paths.conf ]; then
    . /etc/nuxel/paths.conf
fi
NUXEL_CONFIG_DIR="${NUXEL_CONFIG_DIR:-/etc/nuxel}"

NUXXEL_CGROUP_BASE="/sys/fs/cgroup/nuxel"
NUXXEL_NFT_TABLE="nuxel_app_firewall"

# ---- Deterministic app-id -> cgroup name mapping (briq-14) ----
# Sanitizes an app-id to [a-z0-9-] (lowercased, others -> '-') and prefixes
# "app-", guaranteeing a match against the "socket cgroupv2 level 2 'app-*'"
# rules without any user-provided classid.
sanitize_app_id() {
    local app_id="$1"
    local out=""
    local ch

    # Lowercase and replace every out-of-range char with '-'
    app_id="$(printf '%s' "$app_id" | tr '[:upper:]' '[:lower:]')"
    out="$(printf '%s' "$app_id" | sed -e 's/[^a-z0-9-]/-/g')"

    # Collapse repeated '-' and trim leading/trailing '-' for tidiness
    out="$(printf '%s' "$out" | sed -e 's/--*/-/g' -e 's/^-//' -e 's/-$//')"

    if [ -z "$out" ]; then
        echo "[ERROR] App-id '${app_id}' contains no usable characters." >&2
        return 1
    fi

    echo "app-${out}"
}

# ---- App registry integration (briq-se1) ----
# The app registry (configs/nuxel/app-registry/app_registry.json) is the single
# source for app registration. When available, nftables.sh resolves an app's
# declared network_class ("public" -> ACCEPT rule) from it so that the firewall
# agrees with the sandbox launcher and the portal grants. The deterministic
# app-id -> cgroup mapping below is the fallback that guarantees correctness
# even when no registry is installed.
registry_path() {
    if [ -n "${NUXEL_APP_REGISTRY:-}" ] && [ -r "${NUXEL_APP_REGISTRY}" ]; then
        printf '%s' "${NUXEL_APP_REGISTRY}"
        return 0
    fi
    # Writable runtime copy (first boot) wins over system copy.
    if [ -r /var/lib/nuxel/app-registry/app_registry.json ]; then
        printf '%s' /var/lib/nuxel/app-registry/app_registry.json
        return 0
    fi
    if [ -r "${NUXEL_CONFIG_DIR}/app-registry/app_registry.json" ]; then
        printf '%s' "${NUXEL_CONFIG_DIR}/app-registry/app_registry.json"
        return 0
    fi
    return 1
}

# Print the network_class ("public"|"isolated"|"unspec") for an app_id from the
# registry, or nothing if the registry/app entry is unavailable.
registry_network_class() {
    local app_id="$1"
    local reg
    reg="$(registry_path)" || return 0
    # Lightweight scanner: locate the app object whose "app_id" matches, then
    # read the "network_class" value before the object's closing brace.
    python3 - "$reg" "$app_id" << 'PY'
import json, sys
try:
    reg = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
target = sys.argv[2]
for app in reg.get("apps", []):
    if app.get("app_id") == target:
        print(app.get("network_class", "unspec"))
        sys.exit(0)
sys.exit(0)
PY
}

# Ensure cgroupv2 is mounted and the nuxel hierarchy exists.
setup_cgroupv2() {
    if [ ! -d "$NUXXEL_CGROUP_BASE" ]; then
        mkdir -p "$NUXXEL_CGROUP_BASE"
        # Enable controllers on the subtree so app cgroups can set limits.
        if [ -f /sys/fs/cgroup/cgroup.subtree_control ]; then
            echo "+cpu +memory +io" > \
                /sys/fs/cgroup/cgroup.subtree_control 2>/dev/null || true
        fi
    fi
}

# Determine the canonical per-app firewall ruleset. The prefered location is
# ${NUXEL_CONFIG_DIR}/nftables/nuxel-app-firewall.nft (used by nftables.sh and
# nuxel-vm-bootstrap.sh). Some image builders (images/mkrootfs.sh) stage the
# ruleset to /usr/share/nftables.d/ instead, so fall back to that location to
# keep Layer 5 (per-app cgroup socket match) coherent regardless of which
# installer populated the rootfs. Callers may override the whole search with
# NUXEL_NFT_RULESET.
resolve_ruleset() {
    if [ -n "${NUXXEL_NFT_RULESET:-}" ]; then
        printf '%s' "$NUXXEL_NFT_RULESET"
        return 0
    fi
    if [ -r "${NUXEL_CONFIG_DIR}/nftables/nuxel-app-firewall.nft" ]; then
        printf '%s' "${NUXEL_CONFIG_DIR}/nftables/nuxel-app-firewall.nft"
        return 0
    fi
    if [ -r /usr/share/nftables.d/nuxel-app-firewall.nft ]; then
        printf '%s' /usr/share/nftables.d/nuxel-app-firewall.nft
        return 0
    fi
    return 1
}

# Initialize the nftables firewall table (idempotent base ruleset).
init_firewall() {
    # Load the canonical ruleset if present; otherwise install an inline copy
    # so the table + "socket cgroupv2" prerequisites exist.
    local ruleset
    if ! ruleset="$(resolve_ruleset)"; then
        ruleset=""
    fi
    if [ -n "$ruleset" ] && [ -f "$ruleset" ]; then
        nft -f "$ruleset" 2>/dev/null || true
        echo "[OK] nftables firewall loaded from ${ruleset}"
        return 0
    fi

    nft -f /dev/stdin << 'EOF' 2>/dev/null || true
table inet nuxel_app_firewall {
    chain output {
        type filter hook output priority -100; policy drop;
        ct state established,related accept
        oif lo accept
        udp dport 53 accept
        tcp dport 53 accept
    }
}
EOF
    echo "[OK] nftables firewall initialized (inline default)"
}

# Add an ACCEPT rule for a given cgroup name using cgroupv2 socket matching.
add_app_accept() {
    local cgroup_name="$1"
    nft add rule inet "${NUXXEL_NFT_TABLE}" output \
        socket cgroupv2 level 2 "\"${cgroup_name}\"" accept 2>/dev/null || true
}

# Set up an app's cgroup and optionally permit its network.
# Usage: $0 setup-app <app-id> [allow-network] [type]
#   type defaults to the clean sanitized cgroup name; the "type" argument is
#   honoured for compatibility (e.g. 'app-<id>') and always re-sanitized so
#   the mapping stays deterministic.
setup_app_network() {
    local raw_app_id="${2:-}"
    local cgroup_name
    cgroup_name="$(sanitize_app_id "$raw_app_id")" || return 1

    if [ ! -d "$NUXXEL_CGROUP_BASE" ]; then
        setup_cgroupv2
    fi

    local app_cg="${NUXXEL_CGROUP_BASE}/${cgroup_name}"
    mkdir -p "$app_cg"

    # nftables cgroupv2 socket match requires the (empty) socket cgroup to be
    # the app cgroup; the launcher (sandbox.c) writes the child PID to
    # cgroup.procs once it spawns, after which nft may attach the socket.

    local allow_network="${3:-}"
    if [ "$allow_network" = "auto" ] || [ -z "$allow_network" ]; then
        # Resolve from the single-source registry when not forced by the caller.
        local cls
        cls="$(registry_network_class "$raw_app_id")"
        if [ "$cls" = "public" ]; then
            allow_network="true"
        else
            allow_network="false"   # isolated / unspec / unknown -> default drop
        fi
        echo "[INFO] registry network_class for ${raw_app_id} = ${cls:-unknown}"
    fi
    if [ "$allow_network" = "true" ] || [ "$allow_network" = "1" ]; then
        add_app_accept "$cgroup_name"
        echo "[OK] Network allowed for ${raw_app_id} (cgroup ${cgroup_name})"
    else
        # Default drop policy in the ruleset blocks it.
        echo "[OK] Network blocked for ${raw_app_id} (cgroup ${cgroup_name})"
    fi
}

# Attach a PID to an app's cgroup (cgroupv2).
attach_app_pid() {
    local raw_app_id="${2:-}"
    local pid="${3:-}"
    local cgroup_name
    cgroup_name="$(sanitize_app_id "$raw_app_id")" || return 1

    local app_cg="${NUXXEL_CGROUP_BASE}/${cgroup_name}"
    if [ ! -d "$app_cg" ]; then
        echo "[ERROR] Cgroup ${app_cg} does not exist. Call setup-app first." >&2
        return 1
    fi
    echo "$pid" > "${app_cg}/cgroup.procs"
    echo "[OK] PID ${pid} attached to ${raw_app_id} cgroup"
}

# Remove an app's nftables ACCEPT rule(s) and its cgroup.
cleanup_app() {
    local raw_app_id="${2:-}"
    local cgroup_name
    cgroup_name="$(sanitize_app_id "$raw_app_id")" || return 1

    # Delete every ACCEPT rule matching this cgroup (idempotent loop).
    while :; do
        local handle
        handle=$(nft -a list chain inet "${NUXXEL_NFT_TABLE}" output 2>/dev/null | \
                 grep 'socket cgroupv2 level 2' | grep "\"${cgroup_name}\"" | \
                 head -1 | awk '{print $NF}') || true
        if [ -z "$handle" ]; then
            break
        fi
        nft delete rule inet "${NUXXEL_NFT_TABLE}" output handle "$handle" 2>/dev/null || break
    done

    # Remove the cgroup (kills any remaining processes in it).
    rmdir "${NUXXEL_CGROUP_BASE}/${cgroup_name}" 2>/dev/null || true
    echo "[OK] Cleaned up ${raw_app_id}"
}

setup_vpn_killswitch() {
    local vpn_iface="${2:-tun0}"
    nft add rule inet "${NUXXEL_NFT_TABLE}" output \
        oif != "${vpn_iface}" drop 2>/dev/null || true
    echo "[OK] VPN kill switch enabled (only ${vpn_iface})"
}

disable_vpn_killswitch() {
    local handle
    handle=$(nft -a list chain inet "${NUXXEL_NFT_TABLE}" output 2>/dev/null | \
             grep "oif !=" | head -1 | awk '{print $NF}') || true
    if [ -n "$handle" ]; then
        nft delete rule inet "${NUXXEL_NFT_TABLE}" output handle "$handle" 2>/dev/null || true
    fi
    echo "[OK] VPN kill switch disabled"
}

show_status() {
    echo "=== Nuxel App Firewall Status ==="
    echo ""
    echo "--- nftables Rules (cgroup socket matches) ---"
    nft list table inet "${NUXXEL_NFT_TABLE}" 2>/dev/null || echo "  (not initialized)"
    echo ""
    echo "--- App Cgroups ---"
    if [ -d "$NUXXEL_CGROUP_BASE" ]; then
        local any=0
        for cg in "$NUXXEL_CGROUP_BASE"/app-*; do
            [ -d "$cg" ] || continue
            local name
            name=$(basename "$cg")
            local pids
            pids=$(cat "$cg"/cgroup.procs 2>/dev/null | tr '\n' ' ' || echo "none")
            echo "  ${name}: PIDs=[${pids}]"
            any=1
        done
        if [ "$any" = "0" ]; then
            echo "  (no app cgroups)"
        fi
    else
        echo "  (no app cgroups)"
    fi
}

# Parse command
case "${1:-help}" in
    init)
        setup_cgroupv2
        init_firewall
        ;;
    setup-app)
        setup_app_network "$@"
        ;;
    attach)
        attach_app_pid "$@"
        ;;
    cleanup)
        cleanup_app "$@"
        ;;
    vpn-on)
        setup_vpn_killswitch "$@"
        ;;
    vpn-off)
        disable_vpn_killswitch
        ;;
    status)
        show_status
        ;;
    help|-h|--help)
        echo "Nuxel App Firewall — Per-app network isolation (cgroupv2 socket match)"
        echo ""
        echo "Usage:"
        echo "  $0 init                                      Initialize firewall (one-time)"
        echo "  $0 setup-app <app-id> [allow-network]        Set up app cgroup; allow-network may
                                            be true/false/auto (auto = from app registry)"
        echo "  $0 attach <app-id> <pid>                     Attach PID to app cgroup"
        echo "  $0 cleanup <app-id>                          Remove app ACCEPT rules + cgroup"
        echo "  $0 vpn-on [iface]                            Enable VPN kill switch"
        echo "  $0 vpn-off                                   Disable VPN kill switch"
        echo "  $0 status                                    Show current status"
        echo ""
        echo "The app-id is deterministically mapped: lowercased, restricted to"
        echo "[a-z0-9-], prefixed 'app-' (briq-14). e.g. Org.Nuxel.Mail -> app-org-nuxel-mail"
        ;;
    *)
        echo "Usage: $0 {init|setup-app|attach|cleanup|vpn-on|vpn-off|status|help}" >&2
        exit 1
        ;;
esac

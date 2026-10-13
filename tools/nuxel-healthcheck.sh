#!/usr/bin/env bash
#==============================================================================
# Nuxel Health Check — Reports status of all Phase 3 system/user services.
#
# Also asserts *real build-artifact truth* (briq-ci1), so the same check that
# reports running services also confirms the kernel image, boot artifact, and
# notification persistence path that the built system is supposed to ship.
#
# Artifact checks are read-only and reflect actual repo state — they do NOT
# hardcode success. If the kernel is not (yet) built, those checks FAIL, which
# is the correct signal for "artifact missing".
#==============================================================================
set -euo pipefail

# Resolve repo root regardless of invocation cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NUXEL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Device selection: this health check historically asserted the mustang build
# artifacts, so it defaults to mustang when no explicit --device/NUXEL_DEVICE
# is given (the shared selector itself never silently guesses). Per-device
# build paths are resolved via ${NUXEL_DEVICE_DIR}.
if [ -z "${NUXEL_DEVICE:-}" ] && [[ "$*" != *--device* ]]; then
    export NUXEL_DEVICE="mustang"
fi
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" "$@"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

PASS=0; FAIL=0

# Runtime service/endpoint check.
check() {
    local label="$1"; shift
    if "$@" &>/dev/null; then
        echo -e "  ${GREEN}[✓]${NC} $label"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}[✗]${NC} $label"
        FAIL=$((FAIL + 1))
    fi
}

# Build-artifact assertion (file existence + size/path/content truth).
file_check() {
    local label="$1"; local cond="$2"
    if eval "$cond" &>/dev/null; then
        echo -e "  ${GREEN}[✓]${NC} $label"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}[✗]${NC} $label"
        FAIL=$((FAIL + 1))
    fi
}

MIN_KERNEL_IMG=1048576        # 1MB
MIN_BOOT_IMG=4194304          # 4MB

echo "=== Nuxel System Services ==="
check "nuxel-bridge      " sudo systemctl is-active --quiet nuxel-bridge.service
check "nuxel-portal      " sudo systemctl is-active --quiet nuxel-portal.service
check "nuxel-notifications" sudo systemctl is-active --quiet nuxel-notifications.service
check "nuxel-http-bridge " sudo systemctl is-active --quiet nuxel-http-bridge.service 2>/dev/null || echo "  ${YELLOW}[?]${NC} nuxel-http-bridge (not running)"

echo ""
echo "=== User Services ==="
check "nuxel-home-native " systemctl --user is-active --quiet nuxel-home-native.service
check "nuxel-home-kiosk  " systemctl --user is-active --quiet nuxel-home-kiosk.service
check "nuxel-phosh-agent " systemctl --user is-active --quiet nuxel-phosh-agent.service

echo ""
echo "=== Port Availability ==="
check "port 8000 (PWA)   " ss -tlnp 'sport = :8000' 2>/dev/null | grep -q LISTEN
check "port 8080 (API)   " ss -tlnp 'sport = :8080' 2>/dev/null | grep -q LISTEN

echo ""
echo "=== Health Endpoints ==="
check "/api/v1/health    " curl -sf -o /dev/null -H "Authorization: Bearer dev" http://127.0.0.1:8080/api/v1/health
check "/api/v1/ping      " curl -sf -o /dev/null -H "Authorization: Bearer dev" http://127.0.0.1:8080/api/v1/ping

echo ""
echo "=== Build Artifact Truth (briq-ci1) ==="
KBUILD="${NUXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/.build/out"
KCFG="${NUXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/.build/linux-6.12/.config"

file_check "kernel Image.gz exists > 1MB"   "[ -f \"${KBUILD}/Image.gz\" ] && [ \"\$(stat -f%z \"${KBUILD}/Image.gz\" 2>/dev/null || stat -c%s \"${KBUILD}/Image.gz\" 2>/dev/null)\" -ge \"${MIN_KERNEL_IMG}\" ]"
file_check "kernel build exit-code == 0"    "[ -f \"${KBUILD}/exit-code\" ] && [ \"\$(cat \"${KBUILD}/exit-code\" 2>/dev/null)\" = \"0\" ]"
file_check "kernel .config is valid"        "[ -s \"${KCFG}\" ] && [ \"\$(grep -c '^CONFIG_' \"${KCFG}\" 2>/dev/null)\" -gt 0 ]"

BOOT_IMG=""
for cand in \
    "${NUXEL_ROOT}/build/output/boot.img" \
    "${NUXEL_ROOT}/build/boot-artifact/boot.img" \
    "${NUXEL_ROOT}/boot/boot.img"; do
    if [ -f "${cand}" ]; then BOOT_IMG="${cand}"; break; fi
done
file_check "packaged boot.img > 4MB"        "[ -n \"${BOOT_IMG}\" ] && [ \"\$(stat -f%z \"${BOOT_IMG}\" 2>/dev/null || stat -c%s \"${BOOT_IMG}\" 2>/dev/null)\" -ge \"${MIN_BOOT_IMG}\" ]"

NOTIF_PY="${NUXEL_ROOT}/services/nuxel-notifications/src/notifications.py"
file_check "notifications persists to /var/lib/nuxel" "[ -f \"${NOTIF_PY}\" ] && grep -q 'var/lib/nuxel' \"${NOTIF_PY}\""

echo ""
echo "================================="
echo -e "  ${GREEN}Passed: $PASS${NC}  ${RED}Failed: $FAIL${NC}"
echo "================================="
exit $FAIL

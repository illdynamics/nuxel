#!/usr/bin/env bash
#==============================================================================
# Phase 3 Validation Script
# - py_compile all Python files in services/ and shell/
# - bash -n all shell scripts
# - JSON parse all .json files
# - Grep for banned GTK3/legacy patterns (fail if found)
# - Check required service files exist
# - Check kiosk service preserved
# - Check system portal does NOT import GTK
# - Check phosh-agent DOES import GTK/Adw
# - Check notifications uses org.nuxel.Notifications
# - Check api.py has no api_logger import
# - Count passes/fails and exit with appropriate code
#==============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Device selection: this phase-3 validator historically validated the mustang
# build, so it defaults to mustang when no explicit --device/NUXEL_DEVICE is
# given (the shared selector itself never silently guesses). Per-device build
# paths are resolved via ${NUXEL_DEVICE_DIR}.
if [ -z "${NUXEL_DEVICE:-}" ] && [[ "$*" != *--device* ]]; then
    export NUXEL_DEVICE="mustang"
fi
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" "$@"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0

pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; FAIL=$((FAIL + 1)); }

# ── Python syntax compilation ────────────────────────────────────
echo "=== Python syntax compilation ==="
PY_FILES=$(find "$NUXEL_ROOT/services" "$NUXEL_ROOT/shell" \
    -name '*.py' -not -path '*__pycache__*' 2>/dev/null)

for f in $PY_FILES; do
    if python3 -m py_compile "$f" 2>/dev/null; then
        pass "$(basename "$f")"
    else
        fail "$(basename "$f") — syntax error"
    fi
done

# ── Shell script syntax checks ──────────────────────────────────
echo ""
echo "=== Shell script syntax checks ==="
SH_FILES=$(find "$NUXEL_ROOT" \
    \( -name '*.sh' -o -name 'nuxel-home-kiosk' -o -name 'nuxel-home-launcher' \) \
    -not -path '*/.git/*' -not -path '*/.codeseeq/*' -not -path '*/__pycache__/*' 2>/dev/null)

for f in $SH_FILES; do
    if bash -n "$f" 2>/dev/null; then
        pass "$(basename "$f")"
    else
        fail "$(basename "$f") — syntax error"
    fi
done

# ── JSON parse all .json files ──────────────────────────────────
echo ""
echo "=== JSON file validation ==="
JSON_FILES=$(find "$NUXEL_ROOT" -name '*.json' \
    -not -path '*/.git/*' -not -path '*/.codeseeq/*' -not -path '*/__pycache__/*' 2>/dev/null)

for f in $JSON_FILES; do
    if python3 -c "import json; json.load(open('$f'))" 2>/dev/null; then
        pass "$(basename "$f")"
    else
        fail "$(basename "$f") — invalid JSON"
    fi
done

# ── Banned GTK3/legacy patterns ─────────────────────────────────
echo ""
echo "=== Banning GTK3/legacy patterns ==="
FAIL_GTK3=0
for pattern in 'pack_start' 'pack_end' 'show_all' 'set_no_show_all' \
    'get_children' 'drag_source_set' 'drag_dest_set' \
    'Gtk\.ShortcutAction' 'Gtk\.ShortcutTrigger' 'ShortcutController' \
    'Gtk\.TargetEntry' 'Gtk\.DestDefaults' 'DropTarget\.new(type=' \
    'Gtk-3.0' 'Gtk_MAJOR_VERSION=3' \
    'google-play-services' 'libhybris' 'halium' 'waydroid' \
    'pmbootstrap' 'alpine' 'postmarketOS'; do
    if grep -rq "$pattern" "$NUXEL_ROOT/services/" "$NUXEL_ROOT/shell/nuxel-home-native/" \
        --include='*.py' --include='*.c' --include='*.json' 2>/dev/null; then
        failed_files=$(grep -rl "$pattern" "$NUXEL_ROOT/services/" "$NUXEL_ROOT/shell/nuxel-home-native/" \
            --include='*.py' --include='*.c' --include='*.json' 2>/dev/null | head -3 | tr '\n' ' ')
        fail "Banned pattern '$pattern' found in: $failed_files"
        FAIL_GTK3=1
    else
        pass "No '$pattern' found"
    fi
done

if [ "$FAIL_GTK3" -eq 1 ]; then
    echo -e "  ${RED}✗ Banned patterns detected — FAIL${NC}"
    FAIL=$((FAIL + 1))
fi

# ── Required service files ───────────────────────────────────────
echo ""
echo "=== Required service files ==="
REQUIRED=(
    "services/nuxel-portal/src/portal.py"
    "services/nuxel-portal/dbus/org.nuxel.Portal.conf"
    "services/nuxel-portal/systemd/nuxel-portal.service"
    "services/nuxel-bridge/src/bridge.py"
    "services/nuxel-bridge/src/api.py"
    "services/nuxel-bridge/src/capabilities.py"
    "services/nuxel-bridge/dbus/org.nuxel.Bridge.conf"
    "services/nuxel-bridge/systemd/nuxel-bridge.service"
    "services/nuxel-bridge/systemd/nuxel-http-bridge.service"
    "services/nuxel-notifications/src/notifications.py"
    "services/nuxel-notifications/dbus/org.nuxel.Notifications.conf"
    "services/nuxel-notifications/systemd/nuxel-notifications.service"
)

for f in "${REQUIRED[@]}"; do
    if [ -f "$NUXEL_ROOT/$f" ]; then
        pass "$f exists"
    else
        fail "$f MISSING"
    fi
done

# ── Kiosk service preserved ──────────────────────────────────────
echo ""
echo "=== Kiosk service preservation ==="
KIOSK_SVC="$NUXEL_ROOT/shell/config/systemd-user/nuxel-home-kiosk.service"
if [ -f "$KIOSK_SVC" ]; then
    pass "nuxel-home-kiosk.service preserved"
else
    fail "nuxel-home-kiosk.service MISSING"
fi

# ── System portal does NOT import GTK ────────────────────────────
echo ""
echo "=== System portal GTK isolation ==="
PORTAL_PY="$NUXEL_ROOT/services/nuxel-portal/src/portal.py"
if grep -q 'from gi.repository import Gtk\|from gi.repository import Gdk\|Gtk\.\|Gdk\.' "$PORTAL_PY"; then
    fail "portal.py imports GTK/Gdk — VIOLATION"
else
    pass "portal.py has NO GTK/Gdk imports"
fi

# ── Phosh agent DOES import GTK/Adw ──────────────────────────────
echo ""
echo "=== Phosh agent GTK verification ==="
PHOSH_PY="$NUXEL_ROOT/shell/nuxel-phosh-agent/nuxel-phosh-agent.py"
if grep -q 'from gi.repository import Gtk\|Adw' "$PHOSH_PY"; then
    pass "phosh-agent.py DOES import GTK/Adw (correct)"
else
    fail "phosh-agent.py missing GTK/Adw imports"
fi

# ── Notifications uses org.nuxel.Notifications ───────────────────
echo ""
echo "=== Notifications D-Bus contract ==="
NOTIF_PY="$NUXEL_ROOT/services/nuxel-notifications/src/notifications.py"
if grep -q "BUS_NAME = 'org.nuxel.Notifications'" "$NOTIF_PY"; then
    pass "notifications.py uses org.nuxel.Notifications"
else
    fail "notifications.py does NOT use org.nuxel.Notifications"
fi

if grep -q 'org\.freedesktop\.Notifications' "$NOTIF_PY"; then
    fail "notifications.py still references org.freedesktop.Notifications"
else
    pass "notifications.py has NO freedesktop.Notifications references"
fi

if grep -q 'SystemBus' "$NOTIF_PY"; then
    pass "notifications.py uses SystemBus (correct)"
else
    fail "notifications.py missing SystemBus usage"
fi

# ── api.py has no api_logger import ──────────────────────────────
echo ""
echo "=== api.py hardening ==="
API_PY="$NUXEL_ROOT/services/nuxel-bridge/src/api.py"
if grep -q 'from api_logger import api_logger' "$API_PY"; then
    fail "api.py imports api_logger — VIOLATION"
else
    pass "api.py has NO api_logger import"
fi

if grep -q "import logging" "$API_PY"; then
    pass "api.py has standard logging import"
else
    fail "api.py missing logging import"
fi

if grep -q "/api/v1/health" "$API_PY"; then
    pass "api.py has /api/v1/health endpoint"
else
    fail "api.py missing /api/v1/health endpoint"
fi

if grep -q "MAX_REQUEST_SIZE\|1_000_000" "$API_PY"; then
    pass "api.py has request size cap"
else
    fail "api.py missing request size cap"
fi

if grep -q "NUXEL_HTTP_BIND\|NUXEL_HTTP_PORT\|NUXEL_HTTP_MODE" "$API_PY"; then
    pass "api.py reads env vars for configuration"
else
    fail "api.py missing env var configuration"
fi

# ── VM deliverables: image artifact + D-Bus policy + units + ELF (briq-12/13) ─
echo ""
echo "=== VM deliverables (briq-12/13 preflight) ==="

# Bootable VM disk image artifact
VM_IMG="${NUXEL_ROOT}/vm/build-vm-image.sh"
UTM_STATE="${NUXEL_ROOT}/vm/utm-state-report.md"
if [ -f "$VM_IMG" ]; then
    pass "vm/build-vm-image.sh exists"
else
    fail "vm/build-vm-image.sh MISSING"
fi
if [ -f "$UTM_STATE" ]; then
    pass "vm/utm-state-report.md exists (bootstrap failures + 5-VM audit)"
else
    fail "vm/utm-state-report.md MISSING"
fi
if [ -d "$NUXEL_ROOT/artifacts/vm/nuxel-aarch64.utm" ]; then
    pass "artifacts/vm/nuxel-aarch64.utm image bundle exists"
else
    fail "artifacts/vm/nuxel-aarch64.utm MISSING (must be produced on the Apple Silicon UTM host via vm/build-vm-image.sh)"
fi

# D-Bus policy files shipped in the repo
DBUS_POLICY_MISSING=0
for dpol in \
    "services/nuxel-bridge/dbus/org.nuxel.Bridge.conf" \
    "services/nuxel-portal/dbus/org.nuxel.Portal.conf" \
    "services/nuxel-notifications/dbus/org.nuxel.Notifications.conf"; do
    if [ -f "$NUXEL_ROOT/$dpol" ]; then
        pass "D-Bus policy $dpol exists"
    else
        fail "D-Bus policy $dpol MISSING"
        DBUS_POLICY_MISSING=1
    fi
done

# Service unit files
UNIT_MISSING=0
for unit in \
    "services/nuxel-bridge/systemd/nuxel-bridge.service" \
    "services/nuxel-bridge/systemd/nuxel-http-bridge.service" \
    "services/nuxel-portal/systemd/nuxel-portal.service" \
    "services/nuxel-notifications/systemd/nuxel-notifications.service" \
    "services/nuxel-web.service"; do
    if [ -f "$NUXEL_ROOT/$unit" ]; then
        pass "service unit $unit exists"
    else
        fail "service unit $unit MISSING"
        UNIT_MISSING=1
    fi
done

# Native binaries are ELF aarch64 (cross-compiled apps). We cannot compile the
# aarch64 toolchain inside CI, so this validates any committed ELF-aarch64
# binaries or the build scaffolding that must produce them.
if [ -f "$NUXEL_ROOT/build/native-shell/nuxel-sandbox" ]; then
    FILE_OUT=$(file "$NUXEL_ROOT/build/native-shell/nuxel-sandbox" 2>/dev/null || true)
    if echo "$FILE_OUT" | grep -q 'ARM aarch64'; then
        pass "nuxel-sandbox is ELF aarch64"
    else
        fail "nuxel-sandbox is NOT ELF aarch64: $FILE_OUT"
    fi
else
    fail "build/native-shell/nuxel-sandbox missing — run shell/nuxel-shell/build-native-apps.sh on an aarch64 host/sysroot"
fi

# Bootstrap script idempotence + cross-scaffolding present
if grep -q 'set -euo pipefail' "$NUXEL_ROOT/vm/nuxel-vm-bootstrap.sh"; then
    pass "nuxel-vm-bootstrap.sh uses set -euo pipefail"
else
    fail "nuxel-vm-bootstrap.sh missing set -euo pipefail"
fi
for cross in \
    "shell/nuxel-shell/build-native-apps.sh" \
    "shell/nuxel-shell/aarch64-cross.ini" \
    "shell/nuxel-shell/README-cross.md" \
    "shell/nuxel-shell/meson.build"; do
    if [ -f "$NUXEL_ROOT/$cross" ]; then
        pass "$cross exists"
    else
        fail "$cross MISSING (needed for aarch64 cross-compile)"
    fi
done



# ── Real build-artifact assertions (briq-ci1) ───────────────────
# Mirrors ci/validate-build.sh: asserts actual repo/kernel/build state and
# reflects REAL artifact truth (no hardcoded success). Kernel artifacts live
# under kernel/${NUXEL_DEVICE_DIR}/.build/out and are produced by bg-kernel; the packaged boot
# artifact is a *built* image, so these checks FAIL until a real build exists.
echo ""
echo "=== Real build-artifact assertions (briq-ci1) ==="

MIN_KERNEL_IMG=1048576        # 1MB
MIN_BOOT_IMG=4194304          # 4MB
KBUILD="$NUXEL_ROOT/kernel/${NUXEL_DEVICE_DIR}/.build/out"
KCFG="$NUXEL_ROOT/kernel/${NUXEL_DEVICE_DIR}/.build/linux-6.12/.config"

# kernel Image.gz exists and > 1MB
if [ -f "$KBUILD/Image.gz" ]; then
    ksize=$(stat -f%z "$KBUILD/Image.gz" 2>/dev/null || stat -c%s "$KBUILD/Image.gz" 2>/dev/null || echo 0)
    if [ "$ksize" -ge "$MIN_KERNEL_IMG" ]; then
        pass "kernel Image.gz present (${ksize} bytes >= ${MIN_KERNEL_IMG})"
    else
        fail "kernel Image.gz too small: ${ksize} bytes (min ${MIN_KERNEL_IMG})"
    fi
else
    fail "kernel Image.gz missing at $KBUILD/Image.gz (kernel build incomplete/failed)"
fi

# kernel build exit-code == 0
if [ -f "$KBUILD/exit-code" ]; then
    ec=$(cat "$KBUILD/exit-code")
    if [ "$ec" = "0" ]; then
        pass "kernel build exit-code == 0"
    else
        fail "kernel build exit-code == ${ec} (expected 0) — build FAILED"
    fi
else
    fail "kernel build exit-code file missing at $KBUILD/exit-code"
fi

# valid .config
if [ -f "$KCFG" ]; then
    ncfg=$(grep -c '^CONFIG_' "$KCFG" 2>/dev/null || echo 0)
    if [ "$ncfg" -gt 0 ]; then
        pass ".config present with ${ncfg} CONFIG_ entries"
    else
        fail ".config exists but has no CONFIG_ entries"
    fi
else
    fail "kernel .config missing at $KCFG"
fi

# packaged boot artifact > MIN_BOOT_IMG_SIZE (4MB)
BOOT_IMG=""
for cand in     "$NUXEL_ROOT/build/output/boot.img"     "$NUXEL_ROOT/build/boot-artifact/boot.img"     "$NUXEL_ROOT/build/out/flashable/boot.img"     "$NUXEL_ROOT/boot/boot.img/boot.img"; do
    if [ -f "$cand" ]; then BOOT_IMG="$cand"; break; fi
done
if [ -n "$BOOT_IMG" ]; then
    bsize=$(stat -f%z "$BOOT_IMG" 2>/dev/null || stat -c%s "$BOOT_IMG" 2>/dev/null || echo 0)
    if [ "$bsize" -ge "$MIN_BOOT_IMG" ]; then
        pass "packaged boot.img present (${bsize} bytes >= ${MIN_BOOT_IMG})"
    else
        fail "packaged boot.img too small: ${bsize} bytes (min ${MIN_BOOT_IMG})"
    fi
else
    fail "packaged boot.img NOT FOUND under build/output or build/boot-artifact"
fi

# all 6 PWAs import bridge.js from nuxel-common
if [ -x "$NUXEL_ROOT/pwa/nuxel-common/verify-wiring.js" ] || [ -f "$NUXEL_ROOT/pwa/nuxel-common/verify-wiring.js" ]; then
    if command -v node >/dev/null 2>&1 &&        ( cd "$NUXEL_ROOT" && node pwa/nuxel-common/verify-wiring.js ) >/dev/null 2>&1; then
        pass "all 6 PWAs resolve bridge.js from nuxel-common (verify-wiring.js)"
    else
        fail "PWA bridge wiring FAILED (run: node pwa/nuxel-common/verify-wiring.js)"
    fi
else
    fail "pwa/nuxel-common/verify-wiring.js missing"
fi

# all PWA asset copies byte-match assets/nuxel-background.png
canon="$NUXEL_ROOT/assets/nuxel-background.png"
if [ ! -f "$canon" ]; then
    fail "canonical assets/nuxel-background.png missing"
else
    for d in nuxel-home calendar camera-gallery files mail notes; do
        dest="$NUXEL_ROOT/pwa/nuxel-apps/$d/assets/nuxel-background.png"
        [ "$d" = "nuxel-home" ] && dest="$NUXEL_ROOT/pwa/nuxel-home/assets/nuxel-background.png"
        if [ -f "$dest" ] && cmp -s "$canon" "$dest"; then
            pass "asset $d: byte-identical to canonical nuxel-background.png"
        else
            fail "asset $d: diverges from / missing canonical nuxel-background.png (run tools/dedupe-assets.sh)"
        fi
    done
fi

# notifications persist to /var/lib/nuxel
if [ -f "$NUXEL_ROOT/services/nuxel-notifications/src/notifications.py" ] &&    grep -q 'var/lib/nuxel' "$NUXEL_ROOT/services/nuxel-notifications/src/notifications.py"; then
    pass "notifications.py persists under /var/lib/nuxel"
else
    fail "notifications.py does not persist under /var/lib/nuxel"
fi


# ── Summary ──────────────────────────────────────────────────────
echo ""
echo "=============================================="
echo -e "  ${GREEN}Passed: $PASS${NC}  ${RED}Failed: $FAIL${NC}"
echo "=============================================="
exit $FAIL

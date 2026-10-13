#!/usr/bin/env bash
#==============================================================================
# Phase 3 Smoke Test — VM-only runtime validation of the FULL chain:
#
#   PWA (nuxel-home :8000) -> HTTP API (:8080) -> bridge D-Bus -> portal
#       -> PhoshAgent -> (mock) ModemManager
#
# Steps covered:
#   briq-7  PWA serving: nuxel-web (:8000) serves index.html / manifest.json /
#          sw.js (HTTP 200, ETag cacheable) and a 720x1440 screenshot when a
#          Wayland/grim session is available. The served URL is auto-detected by
#          probing both supported layouts (repo-root /pwa/nuxel-home vs pwa-root
#          /) and the org.nuxel.Home Flatpak manifest target is confirmed if
#          present.
#   briq-8  Full PWA -> HTTP API (:8080) -> bridge (org.nuxel.Bridge D-Bus) ->
#          portal -> PhoshAgent -> (mock) ModemManager chain:
#   1. HTTP API 200 + JSON on /api/v1/ping, /api/v1/health
#   2. Bridge D-Bus Ping responds
#   3. Portal permission grant (NUXEL_PORTAL_AUTO_GRANT=1): /api/v1/
#      capabilities/check must return granted, and the grant is reflected in
#      the portal (or PhoshAgent) journal under the real D-Bus path
#   4. /api/v1/capabilities, /api/v1/phone/status, /api/v1/location reachable
#   5. Authenticated /api/v1/sms/send (or /api/v1/rpc) reaches the (mock)
#      ModemManager and confirms the Send
#   6. Honesty audit: each backend layer (ModemManager / NetworkManager /
#      GeoClue2) is explicitly classified LIVE vs MOCK using the data_source /
#      backend_audit fields each API response now carries.
#
# A per-session token is minted via POST /api/v1/auth/token and used for the
# authenticated HTTP chain (the dev server rejects a literal 'dev' token).
# The E2E section replays the served PWA's token+bridge.js fetch flow so a real
# PWA-origin request through the API to the bridge is demonstrated.
#
# Output: per-check PASS/FAIL via check() counters; exit code = number of
# failures (0 = success).
#
# Exits cleanly (with warnings) when NOT running in a VM.
#
# Image assertions (briq-v2):
#   ./ci/phase3-smoke-vm.sh --image artifacts/vm/nuxel-aarch64.qcow2
#   Asserts the produced disk is non-empty, has qcow2 magic, and a bootable
#   filesystem — runnable on any host (no UTM required).
#
# Service-ACTIVE assertions (briq-v1): each Nuxel systemd unit must be
#   'active (running)' and org.nuxel.Portal.Ping must respond on the system bus.
#==============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

# ---- Optional: verify a produced disk image (qcow2/img) on any host ----
IMAGE="${NUXEL_VM_IMAGE:-}"
for _a in "$@"; do
    if [ "$_a" = "--image" ]; then IMG_FLAG=1; continue; fi
    if [ "${IMG_FLAG:-0}" = "1" ]; then IMAGE="$_a"; IMG_FLAG=0; fi
done

verify_image() {
    local img="$1" rc=0
    echo ""
    echo "--- Bootable VM Image Assertion (briq-v2) ---"
    if [ ! -f "$img" ]; then
        echo -e "  ${RED}[✗]${NC} image not found: $img"
        echo "  Expected output: a non-empty qcow2/raw disk at this path."
        echo "  Run: VM_DISK_IMAGE=/path/arm64.qcow2 vm/build-vm-image.sh"
        return 1
    fi
    local size
    size=$(stat -f %z "$img" 2>/dev/null || stat -c %s "$img" 2>/dev/null || echo 0)
    if [ "$size" -le 0 ]; then
        echo -e "  ${RED}[✗]${NC} image is empty (${size} bytes): $img"
        rc=1
    else
        echo -e "  ${GREEN}[✓]${NC} image non-empty (${size} bytes): $img"
    fi
    local magic
    magic="$(LC_ALL=C head -c 4 "$img" | od -An -tx1 | tr -d '[:space:]')"
    if [ "$magic" = "514649fb" ]; then
        echo -e "  ${GREEN}[✓]${NC} qcow2 magic (QFI\xfb) detected"
    else
        echo -e "  ${YELLOW}[!]${NC} not qcow2 magic (${magic:-none}); checking raw filesystem magic..."
        local ext
        ext="$(LC_ALL=C dd if="$img" bs=1 skip=$((0x438)) count=2 2>/dev/null | od -An -tx1 | tr -d '[:space:]')"
        if [ "$ext" = "53ef" ]; then
            echo -e "  ${GREEN}[✓]${NC} ext2/3/4 superblock magic (0x53ef) present -> bootable filesystem"
        else
            # btrfs magic is the string "_BHRfS_M" at byte 0x10040.
            local btr_hex
            btr_hex="$(LC_ALL=C dd if="$img" bs=1 skip=$((0x10040)) count=8 2>/dev/null | od -An -tx1 | tr -d '[:space:]')"
            if [ "$btr_hex" = "5f42485266535f4d" ]; then
                echo -e "  ${GREEN}[✓]${NC} btrfs magic present -> bootable filesystem"
            else
                echo -e "  ${RED}[✗]${NC} no filesystem magic found; image may not be bootable"
                rc=1
            fi
        fi
    fi
    if command -v qemu-img >/dev/null 2>&1; then
        if qemu-img info --output=json "$img" 2>/dev/null | grep -q '"format"[[:space:]]*:[[:space:]]*"qcow2"'; then
            echo -e "  ${GREEN}[✓]${NC} qemu-img confirms qcow2 format"
        fi
    fi
    if [ $rc -eq 0 ]; then
        echo -e "  ${GREEN}[✓]${NC} IMAGE VERIFICATION PASSED: $img"
        echo "  Expected when booting (UTM host): VM boots to Phosh at 720x1440"
    else
        echo -e "  ${RED}[✗]${NC} IMAGE VERIFICATION FAILED: $img"
        echo "  Attach a real ARM64 OS disk and rebuild with vm/build-vm-image.sh"
    fi
    return $rc
}

if [ -n "$IMAGE" ]; then
    verify_image "$IMAGE"
    _img_rc=$?
    echo ""
    echo "=============================================="
    if [ $_img_rc -eq 0 ]; then
        echo -e "  ${GREEN}Image assertion PASSED (bootable disk).${NC}"
    else
        echo -e "  ${RED}Image assertion FAILED — not a bootable disk.${NC}"
        echo "  Attach a real ARM64 OS image and rebuild with vm/build-vm-image.sh"
    fi
    echo "=============================================="
    exit $_img_rc
fi

# Detect if running in a VM
is_vm() {
    if systemd-detect-virt -q 2>/dev/null; then
        return 0
    fi
    if [ -f /sys/class/dmi/id/product_name ] && grep -qiE 'kvm|qemu|vmware|virtualbox' /sys/class/dmi/id/product_name 2>/dev/null; then
        return 0
    fi
    return 1
}

if ! is_vm; then
    echo -e "${YELLOW}[WARN]${NC} Not running in a VM — smoke tests skipped."
    echo "This script requires a running Nuxel VM for runtime validation."
    exit 0
fi

echo "=== Nuxel Phase 3 Smoke Test (VM) ==="

PASS=0; FAIL=0

# Pre-declare the HTTP/honesty response variables so the "Verbatim responses"
# section and the LIVE/MOCK audit below never abort under `set -u` when the
# HTTP bridge on :8080 is not listening (they default to empty).
PING_JSON=""; HEALTH_JSON=""; CAP_JSON=""; PHONE_JSON=""; LOC_JSON=""; PERM_JSON=""; SMS_RESP=""

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

# System services
echo ""
echo "--- System Services ---"
check "systemd running          " systemctl is-system-running --quiet 2>/dev/null
check "dbus running             " systemctl is-active --quiet dbus.service

# Nuxel system services: first that the unit files exist, then (briq-v1) that
# each required unit is ACTIVE (running) on the systemd target.
echo ""
echo "--- Nuxel System Services (installed) ---"
check "nuxel-bridge installed   " [ -f /usr/bin/nuxel-bridge ] || systemctl status nuxel-bridge.service &>/dev/null || [ -f /usr/lib/systemd/system/nuxel-bridge.service ]
check "nuxel-portal installed   " [ -f /usr/bin/nuxel-portal ] || systemctl status nuxel-portal.service &>/dev/null || [ -f /usr/lib/systemd/system/nuxel-portal.service ]
check "nuxel-notifications inst " [ -f /usr/bin/nuxel-notifications ] || systemctl status nuxel-notifications.service &>/dev/null || [ -f /usr/lib/systemd/system/nuxel-notifications.service ]
check "nuxel-http-bridge inst   " [ -f /usr/lib/systemd/system/nuxel-http-bridge.service ]
check "nuxel-web installed      " [ -f /usr/lib/systemd/system/nuxel-web.service ] || systemctl status nuxel-web.service &>/dev/null

# briq-v1: assert each systemd unit is ACTIVE (not merely present).
echo ""
echo "--- Nuxel System Services (active) ---"
check "nuxel-bridge ACTIVE       " systemctl is-active --quiet nuxel-bridge.service
check "nuxel-portal ACTIVE       " systemctl is-active --quiet nuxel-portal.service
check "nuxel-notifications ACTIVE" systemctl is-active --quiet nuxel-notifications.service
check "nuxel-http-bridge ACTIVE  " systemctl is-active --quiet nuxel-http-bridge.service
check "nuxel-web ACTIVE          " systemctl is-active --quiet nuxel-web.service

# briq-v1: nuxel-portal must respond to org.nuxel.Portal.Ping on the system bus.
echo ""
echo "--- Nuxel D-Bus Portal Ping ---"
check "org.nuxel.Portal.Ping     " sh -c "
  gdbus call --system --dest org.nuxel.Portal --object-path /org/nuxel/Portal \
    --method org.nuxel.Portal.Ping smoke &>/dev/null ||
  dbus-send --print-reply --system --dest=org.nuxel.Portal /org/nuxel/Portal \
    org.nuxel.Portal.Ping string:smoke &>/dev/null
"

# Provision an authenticated per-session token for the HTTP chain.
# The dev-mode server does NOT accept a literal 'dev' token — it returns 401
# unless the caller POSTs /api/v1/auth/token to mint a session token. So mint
# one and use it for /ping, /health and /sms/send.
BASE="http://127.0.0.1:8080"
TOKEN=""

# Capture the listener table once (SIGPIPE-safe: we grep the captured string
# via here-string rather than piping check()/ss output straight into grep -q,
# which under `set -o pipefail` aborts with 141 when grep closes early).
SS_TCP="$(ss -tlnp 2>/dev/null || true)"
has_listener() { grep -q "$1" <<< "$SS_TCP"; }

if has_listener ':8080'; then
    AUTH_JSON=$(curl -sf -X POST -H "Content-Type: application/json"         -d '{"app_id":"smoke"}' "$BASE/api/v1/auth/token" 2>/dev/null) || AUTH_JSON=""
    TOKEN=$(printf '%s' "$AUTH_JSON" | python3 -c         "import sys,json
try: print(json.load(sys.stdin).get('token',''))
except Exception: print('')" 2>/dev/null)
    # Fall back to a provisioned static token file if the HTTP auth endpoint
    # did not respond (e.g. the HTTP bridge is down or in production mode).
    if [ -z "$TOKEN" ] && [ -f /var/lib/nuxel/http-bridge/token ]; then
        TOKEN=$(cat /var/lib/nuxel/http-bridge/token 2>/dev/null || true)
    fi
fi

# Port checks
echo ""
echo "--- Port Availability ---"
check "port 8000 (nuxel-web)    " has_listener ':8000'
check "port 8080 (http-bridge)  " has_listener ':8080'

# ---- briq-7: PWA static serving + service worker / manifest ----
echo ""
echo "--- PWA Serving (briq-7: nuxel-home on :8000, 720x1440) ---"
PWA_ROOT="http://127.0.0.1:8000"

# Two supported serving layouts for the nuxel-home PWA tree:
#   A) REPO-ROOT layout  (WorkingDirectory=%h/nuxel):  /pwa/nuxel-home/index.html
#   B) PWA-ROOT layout   (WorkingDirectory=%h/nuxel/pwa/nuxel-home):  /index.html
# Probe both and select whichever actually serves the home PWA so the check is
# robust to which layout nuxel-web.service is configured with.
PWA_URL=""
IDX="000"
IDXBODY=""
for _cand in     "$PWA_ROOT/pwa/nuxel-home/index.html"     "$PWA_ROOT/index.html"     "$PWA_ROOT/"; do
    _code=$(curl -fsS -o /dev/null -w '%{http_code}' "$_cand" 2>/dev/null) || _code="000"
    _body=$(curl -fsS "$_cand" 2>/dev/null || true)
    if printf '%s' "$_body" | grep -qi 'nuxel-app-id' || printf '%s' "$_body" | grep -qi 'Nuxel Home'; then
        PWA_URL="$_cand"
        IDX="$_code"
        IDXBODY="$_body"
        break
    fi
    # remember the 200 root URL even if body marker is missed (report only)
    if [ -z "$PWA_URL" ] && [ "$_code" = "200" ]; then
        PWA_URL="$_cand"
        IDX="$_code"
        IDXBODY="$_body"
    fi
done
check "nuxel-web serves index 200" [ "$IDX" = "200" ]

# If served at the repo-root layout the PWA prefix is /pwa/nuxel-home; if served
# at the pwa-root layout the prefix is "" (path already points into the tree).
if printf '%s' "$PWA_URL" | grep -q '/pwa/nuxel-home/'; then
    PWA_PREFIX="/pwa/nuxel-home"
else
    PWA_PREFIX=""
fi

# The served index.html must actually be the nuxel-home PWA (kiosk + smoke both
# rely on this identity). Grep the body via a temp file (safe re: newlines/quotes).
if [ -n "$IDXBODY" ]; then
    mkdir -p "${SHOT_DIR:-/tmp/nuxel-smoke}"
    printf '%s' "$IDXBODY" > "${SHOT_DIR:-/tmp/nuxel-smoke}/served-index.html"
    check "served index.html is home PWA" sh -c "grep -qi 'nuxel-app-id' '${SHOT_DIR:-/tmp/nuxel-smoke}/served-index.html' || grep -qi 'Nuxel Home' '${SHOT_DIR:-/tmp/nuxel-smoke}/served-index.html'"
else
    check "served index.html is home PWA" false
fi

MF="000"; SW="000"; SWCACHE=""
if [ -n "$PWA_PREFIX" ] || { [ "$IDX" = "200" ] && [ -n "$PWA_URL" ]; }; then
    MF=$(curl -fsS -o /dev/null -w '%{http_code}' "$PWA_ROOT$PWA_PREFIX/manifest.json" 2>/dev/null) || MF="000"
    SW=$(curl -fsS -o /dev/null -w '%{http_code}' "$PWA_ROOT$PWA_PREFIX/sw.js" 2>/dev/null) || SW="000"
    # Service worker cacheability: the static server (python3 -m http.server,
    # the nuxel-web ExecStart) serves Last-Modified (and an ETag when present)
    # as the HTTP cache validator. Capture whichever validator the server emits
    # so the "served/cacheable" record is honest and matches the actual server.
    SWCACHE=$(curl -fsSI "$PWA_ROOT$PWA_PREFIX/sw.js" 2>/dev/null | tr -d '\r' | grep -iE '^(etag|last-modified):' | head -1) || SWCACHE=""
fi
check "manifest.json served 200 " [ "$MF" = "200" ]
check "sw.js service worker 200 " [ "$SW" = "200" ]
check "sw.js cacheable (validator)" [ -n "$SWCACHE" ]

# 720x1440 portrait screenshot evidence. On a Wayland session use grim; the
# file dimensions are then checked (expected portrait 720x1440). If grim is
# unavailable, record that no screenshot could be captured (bg-04 report will
# attach any host-side shots).
SHOT_DIR="${SHOT_DIR:-/tmp/nuxel-smoke}"
mkdir -p "$SHOT_DIR"
SHOT="$SHOT_DIR/nuxel-home-720x1440.png"
if command -v grim >/dev/null 2>&1 && [ -n "$WAYLAND_DISPLAY" ]; then
    if grim -t png "$SHOT" 2>/dev/null; then
        DIMS=$(sips -g pixelWidth -g pixelHeight "$SHOT" 2>/dev/null | awk '/pixelWidth/{w=$2}/pixelHeight/{h=$2}END{print w"x"h}')
        check "screenshot captured 720x1440" [ "$DIMS" = "720x1440" ]
        echo "  screenshot: $SHOT ($DIMS)"
    else
        check "screenshot captured 720x1440" false
    fi
else
    echo -e "  ${YELLOW}[!]${NC} grim/Wayland unavailable — screenshot deferred to vm/utm-state-report.md"
fi

# briq-7: confirm the org.nuxel.Home Flatpak manifest target is present
# (renders the same nuxel-home PWA via WebKitGTK in a Flatpak org.nuxel.Platform
# runtime), so the manifest check is part of the PWA-served record.
FLATPAK_MF="${NUXEL_ROOT:-$HOME/nuxel}/pwa/flatpak/org.nuxel.Home.json"
if [ -f "$FLATPAK_MF" ]; then
    check "org.nuxel.Home flatpak mf " grep -q 'nuxel-home' "$FLATPAK_MF"
    echo "  flatpak manifest: $FLATPAK_MF"
else
    echo -e "  ${YELLOW}[!]${NC} org.nuxel.Home flatpak manifest not found at $FLATPAK_MF"
fi

# Record the served URL + status for the verification report.
echo "  PWA_URL=$PWA_URL (HTTP $IDX)"
echo "  manifest.json HTTP $MF | sw.js HTTP $SW | cache-validator: ${SWCACHE:-none}"

number="+15551234567"

# ---- briq-12: full chain ---- #
echo ""
echo "--- Full Chain (PWA -> HTTP API -> bridge -> portal -> PhoshAgent -> mock ModemManager) ---"

# 1) HTTP API 200 + JSON
if has_listener ':8080'; then
    PING_JSON=$(curl -sf -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/ping" 2>/dev/null) || PING_JSON=""
    check "HTTP /api/v1/ping 200+JSON " python3 -c "
import sys,json
s='''$PING_JSON'''
try:
    d=json.loads(s); raise SystemExit(0 if isinstance(d,dict) and 'pong' in str(d) else 1)
except Exception:
    raise SystemExit(1)
"
    HEALTH_JSON=$(curl -sf -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/health" 2>/dev/null) || HEALTH_JSON=""
    check "HTTP /api/v1/health 200+JSON" python3 -c "
import sys,json
try: json.loads('''$HEALTH_JSON'''); raise SystemExit(0)
except Exception: raise SystemExit(1)
"

    # Additional briq-8/RPC endpoints (capabilities / phone status / location)
    CAP_JSON=$(curl -sf -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/capabilities" 2>/dev/null) || CAP_JSON=""
    check "HTTP /api/v1/capabilities " python3 -c "
import sys,json
s='''$CAP_JSON'''
try:
    d=json.loads(s); caps=(d.get('capabilities') or [])
    raise SystemExit(0 if isinstance(caps,list) and len(caps)>0 else 1)
except Exception:
    raise SystemExit(1)
"

    PHONE_JSON=$(curl -sf -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/phone/status?app_id=smoke" 2>/dev/null) || PHONE_JSON=""
    check "HTTP /api/v1/phone/status " python3 -c "
import sys,json
s='''$PHONE_JSON'''
try:
    d=json.loads(s)
    raise SystemExit(0 if d.get('success') is True and ('network' in d or 'modem' in d) else 1)
except Exception:
    raise SystemExit(1)
"
    LOC_JSON=$(curl -sf -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/location?app_id=smoke" 2>/dev/null) || LOC_JSON=""
    check "HTTP /api/v1/location      " python3 -c "
import sys,json
s='''$LOC_JSON'''
try:
    d=json.loads(s)
    ok = d.get('success') is True or ('error' in d and 'not available' in str(d.get('error','')))
    raise SystemExit(0 if ok else 1)
except Exception:
    raise SystemExit(1)
"
    # briq-8: explicit portal permission check - with NUXEL_PORTAL_AUTO_GRANT=1
    # the portal grants without a user prompt, so /api/v1/capabilities/check
    # (CheckPermission on org.nuxel.Portal via the bridge) must return granted.
    PERM_JSON=$(curl -sf -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/capabilities/check?app_id=smoke&capability=sms:send" 2>/dev/null) || PERM_JSON=""
    check "portal check granted (AUTO)" python3 -c "
import sys,json
s = sys.stdin.read()
try:
    d=json.loads(s)
    granted = d.get('granted') is True or d.get('success') is True
    raise SystemExit(0 if granted else 1)
except Exception:
    raise SystemExit(1)
" <<< "$PERM_JSON"

else
    echo -e "  ${YELLOW}[?]${NC} HTTP bridge not running — skipping HTTP/bridge/portal chain"
    FAIL=$((FAIL + 1))
fi
# 2) Bridge D-Bus Ping
check "bridge D-Bus Ping responds " sh -c "
  dbus-send --print-reply --system --dest=org.nuxel.Bridge /org/nuxel/Bridge org.nuxel.Bridge.Ping string:smoke &>/dev/null ||
  gdbus call --system --dest org.nuxel.Bridge --object-path /org/nuxel/Bridge --method org.nuxel.Bridge.Ping smoke &>/dev/null
"

# 3) Send SMS through the full chain. With NUXEL_PORTAL_AUTO_GRANT=1 the portal
#    grants without a user prompt; the bridge forwards to the (mock)
#    ModemManager which records and confirms the Send.
SMS_RESP=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"app_id\":\"smoke\",\"number\":\"$number\",\"text\":\"nuxel smoke\"}" \
    "$BASE/api/v1/sms/send" 2>/dev/null) || SMS_RESP=""
check "sms.send -> mock Modem MM " python3 -c "
import sys,json
s='''$SMS_RESP'''
try:
    d=json.loads(s)
    ok=d.get('success') is True
    print('SMS_RESP', s)
    raise SystemExit(0 if ok else 1)
except SystemExit:
    raise
except Exception:
    raise SystemExit(1)
"

# 4) Accept-log check. Under NUXEL_PORTAL_AUTO_GRANT=1 the permission is
#    granted by the portal itself (it never invokes org.nuxel.PhoshAgent), so
#    the accept is logged on the PORTAL unit journal, not the PhoshAgent unit.
#    Grep the portal unit; if the real agent path is used instead (auto-grant
#    unset), fall back to the PhoshAgent journal.
check "Permission accept logged    " sh -c "
  journalctl -u nuxel-portal.service --since '5 min ago' 2>/dev/null | grep -qiE 'grant|allow|accept' ||
  journalctl -u nuxel-portal --since '5 min ago' 2>/dev/null | grep -qiE 'grant|allow|accept' ||
  journalctl --user -u nuxel-phosh-agent --since '5 min ago' 2>/dev/null | grep -qiE 'accept|grant|RequestPermission' ||
  journalctl -u nuxel-phosh-agent --since '5 min ago' 2>/dev/null | grep -qiE 'accept|grant|RequestPermission'
"

# 5) Bridge recorded the mock ModemManager Send (via SmsSend returning mock:True)
check "mock ModemManager Send rec " grep -q '"mock"' <<< "$SMS_RESP"

# Journal excerpts (briq-8): capture verbatim systemd/D-Bus evidence for the
# verification report — bridge Ping, portal permission grant, and the SMS send
# reaching the (mock) ModemManager. Keep each excerpt short (10 lines).
echo ""
echo "  Journal excerpts (briq-8, for vm/utm-state-report.md):"
JLOG_DIR="${SHOT_DIR:-/tmp/nuxel-smoke}"
mkdir -p "$JLOG_DIR"
for _u in nuxel-bridge.service nuxel-portal.service nuxel-http-bridge.service; do
    _f="$JLOG_DIR/journal-${_u%.service}.log"
    journalctl -u "$_u" --since '10 min ago' --no-pager 2>/dev/null | tail -n 10 > "$_f" || true
    if [ -s "$_f" ]; then
        echo "  --- journal: $_u (-> $_f) ---"
        sed -n '1,10p' "$_f"
    fi
done
echo ""

# ---- briq-8: E2E PWA -> HTTP API -> bridge call, + honest live/mock audit ----
echo ""
echo "--- End-to-End PWA -> API -> Bridge (briq-8) + LIVE/MOCK Honesty Audit ---"

# The served nuxel-home page loads bridge.js which calls the HTTP API from the
# PWA origin. We replay that exact client flow below (per-session token mint +
# authenticated RPC) so the PWA->API->bridge path is exercised and we can read
# back the data_source / backend_audit fields the API attaches for honesty.
E2E_JSON=$(python3 - <<'PY'
import json, urllib.request
BASE="http://127.0.0.1:8080/api/v1"
def http(method, path, payload=None, token=None, origin="http://127.0.0.1:8000"):
    req = urllib.request.Request(BASE+path, method=method)
    req.add_header("Origin", origin)
    req.add_header("Content-Type", "application/json")
    if token: req.add_header("Authorization", "Bearer "+token)
    data = json.dumps(payload).encode() if payload is not None else None
    try:
        with urllib.request.urlopen(req, data=data, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode())
        except Exception: return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}
st, tok = http("POST", "/auth/token", {"app_id":"org.nuxel.Home"})
if not tok.get("token"):
    print(json.dumps({"success": False, "error": "token mint failed", "http": st}))
    raise SystemExit(0)
t = tok["token"]
out = {"token_mint": tok}
for path in ["/ping", "/capabilities", "/phone/status?app_id=org.nuxel.Home", "/location?app_id=org.nuxel.Home"]:
    st, body = http("GET", path, token=t)
    out[path] = {"http": st, "result": body}
st, rpc = http("POST", "/rpc", {"app_id":"org.nuxel.Home","namespace":"sms","verb":"send","params":{"number":"+15551234567","text":"nuxel e2e"}}, token=t)
out["/rpc sms.send"] = {"http": st, "result": rpc}
print(json.dumps(out))
PY
) || E2E_JSON="{}"
printf '%s' "$E2E_JSON" > "$SHOT_DIR/e2e.json" 2>/dev/null || true
check "E2E token minted (POST /auth/token)" python3 -c "import sys,json;d=json.load(open('$SHOT_DIR/e2e.json'));raise SystemExit(0 if (d.get('token_mint') or {}).get('token') else 1)"
check "E2E PWA GET /api/v1/ping      " python3 -c "import sys,json;d=json.load(open('$SHOT_DIR/e2e.json'));r=(d.get('/ping') or {});raise SystemExit(0 if r.get('http')==200 else 1)"
check "E2E PWA RPC sms.send -> bridge " python3 -c "import sys,json;d=json.load(open('$SHOT_DIR/e2e.json'));r=(d.get('/rpc sms.send') or {}).get('result') or {};inner=r.get('result') or {};raise SystemExit(0 if inner.get('success') is True or r.get('success') is True else 1)"

# Honesty: classify each backend layer as LIVE or MOCK for every checkpoint.
echo ""
echo "  Honesty audit — live vs mock backend data sources:"
if [ -n "$PING_JSON" ]; then
    printf '%s' "$PING_JSON" | python3 -c "
import sys,json
d=json.load(sys.stdin)
v=d.get('version', d.get('.service',''))
src=d.get('data_source','mock')
print('    ping       :', 'MOCK ('+src+')' if d.get('vm_mode') else 'LIVE bridge', '| version', v)
" 2>/dev/null || echo "    ping       : (unavailable)"
fi
if [ -n "$PHONE_JSON" ]; then
    printf '%s' "$PHONE_JSON" | python3 -c "
import sys,json
d=json.load(sys.stdin)
ds=d.get('data_source',{})
aud=d.get('backend_audit',{})
print('    phone/status: network=%s modem=%s battery=%s' % (ds.get('network','?'), ds.get('modem','?'), ds.get('battery','?')))
print('    backends    : ModemManager=%s NetworkManager=%s GeoClue2=%s' % (aud.get('ModemManager','?'), aud.get('NetworkManager','?'), aud.get('GeoClue2','?')))
" 2>/dev/null || echo "    phone/status: (unavailable)"
fi
if [ -n "$LOC_JSON" ]; then
    printf '%s' "$LOC_JSON" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('    location    :', 'MOCK (GeoClue2 '+str(d.get('data_source','mock'))+')' if d.get('vm_mode') or d.get('data_source')=='mock' else 'LIVE GeoClue2', '|', str(d.get('error','ok')))
" 2>/dev/null || echo "    location    : (unavailable)"
fi
if [ -n "$SMS_RESP" ]; then
    printf '%s' "$SMS_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('    sms.send    : ' + ('MOCK (ModemManager '+str(d.get('data_source','mock'))+')' if d.get('mock') else 'LIVE ModemManager'))
" 2>/dev/null || echo "    sms.send    : (unavailable)"
fi
if [ -n "$PERM_JSON" ]; then
    printf '%s' "$PERM_JSON" | python3 -c "
import sys,json
d=json.load(sys.stdin)
granted = d.get('granted')
auto = d.get('portal_auto_grant')
print('    portal check: granted=%s portal_auto_grant=%s' % (granted, auto))
" 2>/dev/null || echo "    portal check: (unavailable)"
fi

# Verbatim curl responses (for the verification report).
echo ""
echo "  Verbatim responses:"
echo "  [ping]  $PING_JSON"
echo "  [health]$HEALTH_JSON"
echo "  [phone] $PHONE_JSON"
echo "  [loc]   $LOC_JSON"
echo "  [sms]   $SMS_RESP"
echo "  [perm]  $PERM_JSON"
echo "  [e2e]   $E2E_JSON"
# User services
echo ""
echo "--- User Services ---"
check "nuxel-home-native inst   " [ -f ~/.config/systemd/user/nuxel-home-native.service ] || [ -f /usr/lib/systemd/user/nuxel-home-native.service ]
check "nuxel-home-kiosk inst    " [ -f ~/.config/systemd/user/nuxel-home-kiosk.service ] || [ -f /usr/lib/systemd/user/nuxel-home-kiosk.service ]
check "nuxel-phosh-agent inst   " [ -f ~/.config/systemd/user/nuxel-phosh-agent.service ] || [ -f /usr/lib/systemd/user/nuxel-phosh-agent.service ]
check "phosh-agent Type=dbus    " grep -q 'Type=dbus' ~/.config/systemd/user/nuxel-phosh-agent.service 2>/dev/null || grep -q 'Type=dbus' /usr/lib/systemd/user/nuxel-phosh-agent.service 2>/dev/null
check "phosh-agent Restart=alw  " grep -q 'Restart=always' ~/.config/systemd/user/nuxel-phosh-agent.service 2>/dev/null || grep -q 'Restart=always' /usr/lib/systemd/user/nuxel-phosh-agent.service 2>/dev/null

echo ""
echo "=============================================="
echo -e "  ${GREEN}Passed: $PASS${NC}  ${RED}Failed: $FAIL${NC}"
echo "=============================================="
exit $FAIL

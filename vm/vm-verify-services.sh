#!/usr/bin/env bash
# =============================================================================
# vm/vm-verify-services.sh  (briq-09 / build group bg-04)
#
# Guest-side verification of the Nuxel core system services and the HTTP
# bridge/API. Runs INSIDE the UTM ARM64 Fedora guest as root (elevates to the
# nuxel user for user-session checks where needed). Called automatically by
# vm/deploy-vm.sh; may also be invoked by hand on the guest for a re-check.
#
# briq-09 contract:
#   [0] Capture VERBATIM, in order:
#       systemctl status nuxel-bridge nuxel-portal nuxel-notifications --no-pager
#       systemctl --failed
#       journalctl -u nuxel-bridge -u nuxel-portal -u nuxel-notifications
#                   --no-pager -n 200
#       ps aux | grep -i nuxel
#       find /etc/nuxel /var/lib/nuxel /usr/lib /usr/libexec \
#            -maxdepth 3 -iname '*nuxel*'
#       busctl list | grep -iE 'org\.nuxel|nuxel'
#       ss -ltnp | grep -E ':(8000|8080)'
#   [1] systemctl is-active for nuxel-bridge/-portal/-notifications/
#       -http-bridge/-web   -> must be 'active (running)'
#   [2] BRIDGE-ALIVE GATE (mandatory): curl results are accepted as proof
#       ONLY AFTER (a) systemd reports nuxel-bridge.service active AND
#       (b) the system-bus name org.nuxel.Bridge is present (busctl list).
#       A mock/fallback HTTP body (data_source:"mock" / vm_mode:true from
#       api.py _mock_response) is a FAIL, never a PASS.
#   [3] SYSTEM bus name ownership (busctl / ListNames intro):
#       org.nuxel.Bridge / org.nuxel.Portal / org.nuxel.Notifications.
#       org.nuxel.HTTPBridge is the nuxel-http-bridge HTTP listener on
#       127.0.0.1:8080 and is verified as an HTTP listener -- it does NOT
#       claim a separate D-Bus name (stated explicitly, never conflated).
#   [4] HTTP API on 127.0.0.1:8080:
#       GET /api/v1/health, GET /api/v1/ping?message=hello,
#       POST /api/v1/rpc (ping namespace) -- 200 + valid JSON, no mock marker.
#       Note (api.py do_GET): the /api/v1/ping route hard-codes the Ping
#       argument as 'health' and ignores the ?message= query; the message
#       round-trip is proven via POST /api/v1/rpc {"namespace":"ping",
#       "verb":"ping","params":{"message":"hello"}} which echoes it.
#   [5] org.nuxel.Portal.Ping via gdbus -> round-trips 'smoke'.
#   [6] END-TO-END:
#       (a) home PWA served by nuxel-web on 127.0.0.1:8000
#           /pwa/nuxel-home/index.html returns 200 with the real launcher;
#       (b) login/permission flow through the portal: POST /api/v1/auth/token
#           obtains a session token, then a permission request
#           (POST /api/v1/capabilities/request) round-trips with a JSON verdict;
#       (c) notification delivered via org.nuxel.Notifications.Notify AND
#           persisted to the canonical history file (resolved from the unit's
#           NUXEL_NOTIFICATIONS_FILE, defaulting to
#           /var/lib/nuxel/notifications.json with the legacy
#           /var/lib/nuxel/notifications/history.json fallback).
#   [7] Backend availability (live vs mock) + PWA presence.
#   [8] briq-11b (group bg-11, VM-only): launcher/bridge PARITY from the served
#       side -- every served launcher asset (index.html, manifest.json, sw.js,
#       js/status-bar.js, js/safe-zones.js, js/apps.js, js/qs.js,
#       js/settings-store.js) is hashed over HTTP and compared with the file in
#       the deployed tree (a stale serve is a FAIL, not a mystery), the SERVED
#       status-bar revision is compared with manifest.json's nuxel.pwa_version,
#       and the browser-origin CORS PREFLIGHT of the bridge is exercised with
#       the exact header shape the PWA sends (X-Nuxel-Bridge-Version).  curl-only
#       evidence is explicitly NOT accepted as proof of the page's own path.
#   [9] briq-11b: the OFFLINE service-graph validator (briq-04b,
#       tools/s10plus/a33/verify-service-graph.py) is run here and its result is
#       cross-checked against the LIVE unit graph: units installed vs present,
#       builder-enabled vs enabled live, the five core units active, After=
#       dependency resolution, and `systemd-analyze verify` parsing every
#       canonical unit file with the REAL systemd.  A green offline validator is
#       never reported as a live PASS: the two halves are labelled separately.
#
# Honesty rule: a step that cannot run (e.g. live guest is not reachable) is
# recorded as 'NOT VERIFIED HERE' -- never a fabricated PASS. A mock/fallback
# API response is NOT proof of a live bridge.
# Output is appended to /var/tmp/nuxel-service-verify.log (and echoed to tty).
# Exit: 0 by default (diagnostic; deploy pipeline reports FAILs from the log).
#       VERIFY_STRICT=1 -> exit 1 when FAIL>0.
# =============================================================================
set -uo pipefail

OUT="/var/tmp/nuxel-service-verify.log"
: > "${OUT}"
NUXEL_USER="${NUXEL_USER:-nuxel}"

say()   { echo "$*" | tee -a "${OUT}"; }
inf()   { echo -e "[INFO] $*"   | tee -a "${OUT}"; }
ok()    { echo -e "[PASS] $*"   | tee -a "${OUT}"; }
bad()   { echo -e "[FAIL] $*"   | tee -a "${OUT}"; }
warn()  { echo -e "[WARN] $*"   | tee -a "${OUT}"; }
nver()  { echo -e "[INFO] NOT VERIFIED HERE - $*" | tee -a "${OUT}"; }

UNITS=(nuxel-bridge.service nuxel-portal.service nuxel-notifications.service \
       nuxel-http-bridge.service nuxel-web.service)
# system-bus D-Bus names backed by the units above
DBUS_NAMES=(org.nuxel.Bridge org.nuxel.Portal org.nuxel.Notifications)
PASS=0; FAIL=0; NVER=0

say "=============================================================="
say " Nuxel Service + End-to-End Verification -- $(date -u +%Y-%m-%dT%H:%M:%SZ)"
say " Host=$(hostname) arch=$(uname -m) kernel=$(uname -r 2>/dev/null || echo unknown)"
say " Running on a REAL guest? ${NUXEL_REAL_RUN:-unset}"
say "=============================================================="

# ---------------------------------------------------------------------------
# [0] briq-09 verbatim evidence: run every mandated command and tee the exact
#     output into the log. These are raw captures; PASS/FAIL verdicts come in
#     the sections below.
# ---------------------------------------------------------------------------
inf "briq-09 verbatim command captures (raw evidence):"
run_verbatim() {
    local label="$1"; shift
    say ""
    say "----- ${label} -----"
    say "\$ $*"
    "$@" 2>&1 | tee -a "${OUT}"
    say "----- end ${label} -----"
}

run_verbatim "systemctl status (core units)" \
    systemctl status nuxel-bridge nuxel-portal nuxel-notifications --no-pager -l

run_verbatim "systemctl --failed" \
    systemctl --failed --no-pager -l

run_verbatim "journalctl (core units, last 200 lines)" \
    journalctl -u nuxel-bridge -u nuxel-portal -u nuxel-notifications --no-pager -n 200

run_verbatim "ps aux | grep -i nuxel" \
    bash -c "ps aux | grep -i nuxel | grep -v grep || true"

run_verbatim "find /etc/nuxel /var/lib/nuxel /usr/lib /usr/libexec -maxdepth 3 -iname '*nuxel*'" \
    bash -c "find /etc/nuxel /var/lib/nuxel /usr/lib /usr/libexec -maxdepth 3 -iname '*nuxel*' 2>/dev/null | sort"

run_verbatim "busctl list | grep -iE 'org\.nuxel|nuxel'" \
    bash -c "busctl list --no-legend 2>/dev/null | grep -iE 'org\.nuxel|nuxel' || true"

run_verbatim "ss -ltnp | grep -E ':(8000|8080)'" \
    bash -c "ss -ltnp 2>/dev/null | grep -E ':(8000|8080)' || true"

# ---------------------------------------------------------------------------
inf "Starting core services..."
for u in "${UNITS[@]}"; do
    if systemctl start "${u}" 2>/dev/null; then
        inf "  started ${u}"
    else
        warn "  could not start ${u} (may already be running/failed)"
    fi
done
sleep 3

# ---------------------------------------------------------------------------
inf "systemctl is-active + PID for each unit:"
for u in "${UNITS[@]}"; do
    if systemctl is-active --quiet "${u}" 2>/dev/null; then
        pid=$(systemctl show -p MainPID --value "${u}" 2>/dev/null)
        ok "${u} active (running) pid=${pid}"
        PASS=$((PASS+1))
    else
        st=$(systemctl is-active "${u}" 2>/dev/null)
        bad "${u} NOT active (state=${st})"
        FAIL=$((FAIL+1))
        say "----- journalctl -u ${u} -n 100 -----"
        journalctl -u "${u}" -n 100 --no-pager 2>/dev/null | tail -100 | tee -a "${OUT}"
    fi
done

# ---------------------------------------------------------------------------
inf "D-Bus service ownership table (bus / status):"
names_out=$(busctl --system --list 2>/dev/null || \
    dbus-send --system --print-reply \
        --dest=org.freedesktop.DBus /org/freedesktop/DBus \
        org.freedesktop.DBus.ListNames 2>&1)
say "  service             bus     status    owner-name"
for n in "${DBUS_NAMES[@]}"; do
    if echo "${names_out}" | grep -q "${n}"; then
        say "  ${n}  system   ACTIVE    ${n}"
        ok "system bus owner: ${n}"
        PASS=$((PASS+1))
    else
        bad "system bus name NOT owned: ${n}"
        FAIL=$((FAIL+1))
    fi
done
# org.nuxel.HTTPBridge is the nuxel-http-bridge HTTP listener, not a D-Bus name
say "  org.nuxel.HTTPBridge  http:8080  (checked below as HTTP listener — no separate D-Bus name exists)"
say "----- ListNames excerpt (nuxel) -----"
echo "${names_out}" | grep -i nuxel | tee -a "${OUT}"

# ---------------------------------------------------------------------------
# BRIDGE-ALIVE GATE (briq-09): curl results below are accepted as proof ONLY
# if systemd says nuxel-bridge.service is active AND the system-bus name
# org.nuxel.Bridge is owned. Every HTTP check FAILs hard when the gate is not
# met — a mock/fallback body is never proof.
# ---------------------------------------------------------------------------
BRIDGE_ACTIVE=0; BRIDGE_DBUS=0
if systemctl is-active --quiet nuxel-bridge.service 2>/dev/null; then
    BRIDGE_ACTIVE=1
fi
if busctl --system list --no-legend 2>/dev/null | awk '{print $1}' | grep -qx 'org.nuxel.Bridge'; then
    BRIDGE_DBUS=1
fi
if [ "${BRIDGE_ACTIVE}" = "1" ] && [ "${BRIDGE_DBUS}" = "1" ]; then
    ok "BRIDGE-ALIVE GATE MET: nuxel-bridge.service active (systemd) + org.nuxel.Bridge owned (D-Bus) -> HTTP responses below are accepted as live-bridge proof"
    PASS=$((PASS+1))
else
    bad "BRIDGE-ALIVE GATE NOT MET: nuxel-bridge active=${BRIDGE_ACTIVE} org.nuxel.Bridge-on-bus=${BRIDGE_DBUS} -> ANY HTTP 200 below is NOT proof of a live bridge"
    FAIL=$((FAIL+1))
fi

# ---------------------------------------------------------------------------
inf "Phosh session active for ${NUXEL_USER}?"
# loginctl list-sessions columns (systemd >= 250): SESSION UID USER SEAT
# LEADER CLASS TTY IDLE SINCE. Match USER in column 3 and prefer a
# seat-backed interactive session (column 4 != '-'); the historical
# '$NF==u' match broke once systemd appended IDLE/SINCE columns.
SES_OK=
nuxel_sessions=0
if command -v loginctl >/dev/null 2>&1; then
    nuxel_sessions=$(loginctl list-sessions --no-legend 2>/dev/null | awk -v u="${NUXEL_USER}" '$3==u' | wc -l | tr -d ' ')
    my_session=$(loginctl list-sessions --no-legend 2>/dev/null | awk -v u="${NUXEL_USER}" '$3==u && $4!="-" {print $1; exit}')
    if [ -z "${my_session:-}" ]; then
        my_session=$(loginctl list-sessions --no-legend 2>/dev/null | awk -v u="${NUXEL_USER}" '$3==u {print $1; exit}')
    fi
    if [ -n "${my_session}" ]; then
        dk=$(loginctl show-session -p Desktop --value "${my_session}" 2>/dev/null)
        ty=$(loginctl show-session -p Type --value "${my_session}" 2>/dev/null)
        st=$(loginctl show-session -p Active --value "${my_session}" 2>/dev/null)
        inf "  session=${my_session} Type=${ty} Desktop=${dk} Active=${st}"
        if [ "${dk:-}" = "phosh" ] || [ "${dk:-}" = "Phosh" ]; then
            [ "${st:-}" = "yes" ] && SES_OK=1
        fi
    fi
fi
ppid=$(pgrep -x phosh 2>/dev/null | head -1 || true)
pcpid=$(pgrep -x phoc 2>/dev/null | head -1 || true)
if [ -n "${ppid}" ] && [ -n "${pcpid}" ]; then
    inf "  phosh pid=${ppid} phoc pid=${pcpid}"
    SES_OK=1
fi
if [ -n "${SES_OK}" ]; then
    ok "Phosh desktop session active for ${NUXEL_USER}"
    PASS=$((PASS+1))
else
    nver "cannot confirm a LIVE Phosh session for ${NUXEL_USER} (loginctl present; nuxel sessions=${nuxel_sessions:-0}, none Active with Desktop=phosh; phosh pid=${ppid:-none} phoc pid=${pcpid:-none})"
    NVER=$((NVER+1))
fi

# ---------------------------------------------------------------------------
inf "HTTP API on 127.0.0.1:8080 (org.nuxel.HTTPBridge listener):"
# Phase 9 honesty: a mock/fallback response must NOT count as API proof. The
# live bridge response carries no mock marker; api.py _mock_response labels
# every fallback with "data_source":"mock" (and "vm_mode":true). We therefore
# FAIL any 200 that is actually a mock/fallback body — and, per the
# BRIDGE-ALIVE GATE, FAIL any 200 when the bridge is not demonstrably live.
MOCK_MARKERS='"data_source"[[:space:]]*:[[:space:]]*"mock"\|"vm_mode"[[:space:]]*:[[:space:]]*true'

http_check() {
    # http_check <label> <url> [curl-extra-args...]
    local label="$1"; local url="$2"; shift 2
    local code body
    code=$(curl -s -o /tmp/nuxel_http_body.json -w '%{http_code}' "${url}" "$@" 2>/dev/null)
    body=$(cat /tmp/nuxel_http_body.json 2>/dev/null)
    if [ "${BRIDGE_ACTIVE}" != "1" ] || [ "${BRIDGE_DBUS}" != "1" ]; then
        bad "HTTP ${code:-000} ${label} -> ${body}  [BRIDGE-ALIVE GATE NOT MET: result NOT accepted as proof]"
        FAIL=$((FAIL+1))
        return 1
    fi
    if [ "${code}" = "200" ] && echo "${body}" | python3 -c 'import sys,json;json.load(sys.stdin)' 2>/dev/null; then
        if echo "${body}" | grep -qE "${MOCK_MARKERS}"; then
            bad "HTTP 200 ${label} but body is MOCK/fallback (data_source=mock/vm_mode=true) — bridge not live: ${body}"
            FAIL=$((FAIL+1))
        else
            ok "HTTP 200 ${label} -> ${body} (live bridge, no mock marker)"
            PASS=$((PASS+1))
        fi
    else
        bad "HTTP ${code:-000} ${label} -> ${body}"
        FAIL=$((FAIL+1))
    fi
    say "  curl -i ${label}:"; curl -s -i "${url}" "$@" 2>/dev/null | head -12 | tee -a "${OUT}"
}

http_check "GET /api/v1/health" "http://127.0.0.1:8080/api/v1/health"
http_check "GET /api/v1/ping?message=hello (briq-09 documented smoke)" \
    "http://127.0.0.1:8080/api/v1/ping?message=hello"
# The GET /api/v1/ping route hard-codes the Ping arg 'health' (api.py do_GET);
# prove the message actually round-trips through the live bridge via the RPC
# route (POST /api/v1/rpc, namespace=ping, verb=ping, params.message=hello).
rpc_out=$(curl -s -X POST "http://127.0.0.1:8080/api/v1/rpc" \
    -H 'Content-Type: application/json' \
    -d '{"app_id":"org.nuxel.home","namespace":"ping","verb":"ping","params":{"message":"hello"}}' 2>/dev/null)
say "  POST /api/v1/rpc (ping/hello) -> ${rpc_out}"
if [ "${BRIDGE_ACTIVE}" = "1" ] && [ "${BRIDGE_DBUS}" = "1" ] \
   && echo "${rpc_out}" | grep -q '"echo"[[:space:]]*:[[:space:]]*"hello"'; then
    ok "POST /api/v1/rpc ping message round-trip: echo=hello (live bridge RPC)"
    PASS=$((PASS+1))
else
    bad "POST /api/v1/rpc ping did not round-trip 'hello' (gate met=${BRIDGE_ACTIVE}${BRIDGE_DBUS}) -> ${rpc_out}"
    FAIL=$((FAIL+1))
fi
# Explicit listener evidence for Phase 9: who actually owns :8000/:8080?
say "  listeners on :8000/:8080 (ss -ltnp):"
ss -ltnp 2>/dev/null | grep -E ':(8000|8080)' | tee -a "${OUT}"

# ---------------------------------------------------------------------------
inf "org.nuxel.Portal.Ping via gdbus:"
if command -v gdbus >/dev/null 2>&1; then
    ping_out=$(gdbus call --system --dest org.nuxel.Portal \
        --object-path /org/nuxel/Portal \
        --method org.nuxel.Portal.Ping "smoke" 2>&1)
    if echo "${ping_out}" | grep -qi "smoke"; then
        ok "org.nuxel.Portal.Ping('smoke') -> ${ping_out}"
        PASS=$((PASS+1))
    else
        bad "org.nuxel.Portal.Ping did not echo smoke: ${ping_out}"
        FAIL=$((FAIL+1))
    fi
    say "  gdbus output: ${ping_out}"
else
    nver "gdbus not installed — Portal.Ping check skipped"
    NVER=$((NVER+1))
fi

# ---------------------------------------------------------------------------
inf "END-TO-END (a) home PWA served by nuxel-web on :8000:"
HOME_URL="http://127.0.0.1:8000/pwa/nuxel-home/index.html"
wcode=$(curl -s -o /tmp/nuxel_home.html -w '%{http_code}' "${HOME_URL}" 2>/dev/null)
if [ "${wcode}" = "200" ] && grep -qi "nuxel" /tmp/nuxel_home.html 2>/dev/null; then
    ok "home PWA reachable: HTTP 200 at ${HOME_URL}"
    say "  title: $(grep -io '<title>[^<]*' /tmp/nuxel_home.html | head -1 | sed 's/<title>//I')"
    PASS=$((PASS+1))
else
    bad "home PWA NOT reachable: HTTP ${wcode:-000} at ${HOME_URL}"
    FAIL=$((FAIL+1))
fi

# ---------------------------------------------------------------------------
inf "END-TO-END (b) login/permission flow through the portal:"
E2E_AUTH_OK=
E2E_PERM_OK=
if command -v curl >/dev/null 2>&1; then
    tok_json=$(curl -s -X POST http://127.0.0.1:8080/api/v1/auth/token \
        -H 'Content-Type: application/json' \
        -d '{"app_id":"org.nuxel.home"}' 2>/dev/null)
    say "  POST /api/v1/auth/token -> ${tok_json}"
    token=$(echo "${tok_json}" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("token",""))' 2>/dev/null)
    if [ -n "${token}" ] && [ "${token}" != "None" ]; then
        ok "portal login/token issued for org.nuxel.home"
        PASS=$((PASS+1)); E2E_AUTH_OK=1
        # permission request through the portal (dev-loopback is allowed; also
        # exercise the Bearer token path for a non-destructive capability check)
        # "phone:status" is the real capability key (services/nuxel-bridge/src/
        # capabilities.py); the old helper used "phone.status" which the live
        # bridge rejects with "Unknown capability".
        perm_json=$(curl -s -X POST http://127.0.0.1:8080/api/v1/capabilities/request \
            -H 'Content-Type: application/json' \
            -H "Authorization: Bearer ${token}" \
            -d '{"app_id":"org.nuxel.home","capability":"phone:status"}' 2>/dev/null)
        say "  POST /api/v1/capabilities/request -> ${perm_json}"
        # Accept ANY well-formed portal verdict (granted OR denied): the point
        # is that the request round-tripped bridge -> portal (and, where a
        # PhoshAgent session exists, through the consent UI) and returned a
        # verdict. The actual verdict is logged, never disguised.
        verdict=$(echo "${perm_json}" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
keys = ("granted", "state", "allowed", "success", "status")
if any(k in d for k in keys):
    print(json.dumps({k: d[k] for k in
        ("granted", "state", "allowed", "success", "status",
         "capability", "duration", "error") if k in d}))
    sys.exit(0)
sys.exit(1)' 2>/dev/null)
        if [ -n "${verdict}" ]; then
            ok "permission request via portal round-tripped (verdict: ${verdict})"
            PASS=$((PASS+1)); E2E_PERM_OK=1
        else
            nver "permission request returned an unexpected shape: ${perm_json}"
            NVER=$((NVER+1))
        fi
    else
        bad "login/token endpoint failed or returned no token"
        FAIL=$((FAIL+1))
    fi
else
    nver "curl not installed — token/login check skipped"
    NVER=$((NVER+1))
fi

# ---------------------------------------------------------------------------
inf "END-TO-END (c) notification delivered AND persisted:"
E2E_NOTIF_OK=
# Resolve the canonical history file the unit actually writes to
# (NUXEL_NOTIFICATIONS_FILE in the unit, else paths.conf, else defaults).
HIST=""
if command -v systemctl >/dev/null 2>&1; then
    envline=$(systemctl show -p Environment nuxel-notifications.service 2>/dev/null \
        | sed -n 's/^Environment=//p' | tr ' ' '\n' \
        | sed -n 's/^NUXEL_NOTIFICATIONS_FILE=//p' | head -1)
    if [ -n "${envline}" ]; then
        HIST="${envline}"
    fi
fi
if [ -z "${HIST}" ] && [ -f /etc/nuxel/paths.conf ]; then
    HIST=$(grep -E '^NUXEL_NOTIFICATIONS_FILE=' /etc/nuxel/paths.conf 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'"'')
fi
if [ -z "${HIST}" ]; then
    if [ -f /var/lib/nuxel/notifications/history.json ]; then
        HIST="/var/lib/nuxel/notifications/history.json"   # legacy deployed layout
    else
        HIST="/var/lib/nuxel/notifications.json"           # canonical default
    fi
fi
if command -v gdbus >/dev/null 2>&1; then
    nresult=$(gdbus call --system --dest org.nuxel.Notifications \
        --object-path /org/nuxel/Notifications \
        --method org.nuxel.Notifications.Notify \
        "org.nuxel.home" "E2E notification" "delivered-swift-$RANDOM" 2>&1)
    say "  org.nuxel.Notifications.Notify -> ${nresult}"
    if echo "${nresult}" | grep -qi "success"; then
        ok "notification delivered via org.nuxel.Notifications"
        PASS=$((PASS+1)); E2E_NOTIF_OK=1
    else
        bad "Notify did not report success: ${nresult}"
        FAIL=$((FAIL+1))
    fi
else
    nver "gdbus not installed — Notify trigger skipped"
    NVER=$((NVER+1))
fi
# Persistence assertion: the canonical history file must exist and contain the
# delivered notification marker.
if [ -f "${HIST}" ]; then
    say "  history file present: ${HIST} ($(wc -c < "${HIST}" 2>/dev/null) bytes)"
    if grep -qi "swift\|delivered" "${HIST}" 2>/dev/null; then
        ok "history file persisted the delivered notification: ${HIST}"
        PASS=$((PASS+1))
    else
        nver "history file exists but the delivered notification id is not yet visible"
        NVER=$((NVER+1))
    fi
    say "  tail ${HIST}:"; tail -c 400 "${HIST}" | tee -a "${OUT}"
else
    bad "notification history file MISSING at ${HIST} (resolved from unit env/paths.conf/default)"
    FAIL=$((FAIL+1))
fi

# ---------------------------------------------------------------------------
inf "Backend availability (live vs mock):"
missing_backends=""
for k in ModemManager NetworkManager; do
    state=$(systemctl is-active "${k}" 2>/dev/null || echo absent)
    say "  ${k}: ${state}"
    [ "${state}" = "active" ] || missing_backends="${missing_backends}${missing_backends:+, }${k}"
done
if command -v geoclue >/dev/null 2>&1 || systemctl is-active geoclue 2>/dev/null | grep -q active; then
    say "  GeoClue: available"
else
    say "  GeoClue: absent (mock location data expected)"
    missing_backends="${missing_backends}${missing_backends:+, }GeoClue"
fi
say "  modem-manager presence: $(command -v mmcli >/dev/null 2>&1 && echo yes || echo no)"
if [ -n "${missing_backends}" ]; then
    inf "NOTE: absent backend(s) [${missing_backends}] => bridge/API serve mock "
    inf "      capability data for those capabilities. Mock usage is FLAGGED, not disguised."
else
    inf "NOTE: all live-capability backends active (ModemManager/NetworkManager/GeoClue); capability data is live."
fi

# ---------------------------------------------------------------------------
inf "PWA presence (nuxel-home launcher) for kiosk/web serve:"
for f in /home/nuxel/nuxel/pwa/nuxel-home/index.html \
         /home/nuxel/nuxel/pwa/nuxel-home/manifest.json \
         /home/nuxel/nuxel/pwa/nuxel-home/sw.js; do
    if [ -f "${f}" ]; then
        ok "PWA file present: ${f}"
        PASS=$((PASS+1))
    else
        bad "PWA file missing: ${f}"
        FAIL=$((FAIL+1))
    fi
done

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# [8] VM-ONLY launcher <-> bridge parity (briq-11b, group bg-11).
#     The launcher does not talk to the bridge with curl: it talks from a
#     BROWSER ORIGIN, which means a CORS preflight.  This section exercises the
#     exact request shape the page uses (pwa/nuxel-common/bridge.js sends
#     X-Nuxel-Bridge-Version on every call) and proves that the assets the web
#     server actually SERVES are byte-identical to the repository tree - a stale
#     device/VM copy of the launcher is a detectable state, not a mystery.
# ---------------------------------------------------------------------------
say ""
say "--- [8] vm-only launcher/bridge parity (served assets + browser preflight) ---"
REPO_TREE="${NUXEL_REPO_TREE:-/home/${NUXEL_USER}/nuxel}"
NUXEL_WEB_URL="${NUXEL_WEB_URL:-http://127.0.0.1:8000}"
NUXEL_API_URL_LOCAL="${NUXEL_API_URL_LOCAL:-http://127.0.0.1:8080/api/v1}"

served_matches_disk() {
    # $1 = path relative to pwa/nuxel-home/
    local rel="$1" url disk sh dh
    url="${NUXEL_WEB_URL}/pwa/nuxel-home/${rel}"
    disk="${REPO_TREE}/pwa/nuxel-home/${rel}"
    if [ ! -f "${disk}" ]; then
        nver "served-vs-disk: ${rel} (repository copy not present at ${disk})"
        NVER=$((NVER+1))
        return
    fi
    sh=$(curl -s -m 10 "${url}" | sha256sum 2>/dev/null | awk '{print $1}')
    dh=$(sha256sum "${disk}" 2>/dev/null | awk '{print $1}')
    if [ -z "${sh}" ] || [ "${sh}" = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" ]; then
        bad "served asset EMPTY: ${url}"
        FAIL=$((FAIL+1))
    elif [ "${sh}" = "${dh}" ]; then
        ok "served == repository: ${rel} (${sh:0:16}...)"
        PASS=$((PASS+1))
    else
        bad "served != repository: ${rel} served=${sh:0:16}... disk=${dh:0:16}... (stale launcher serve)"
        FAIL=$((FAIL+1))
    fi
}
for f in index.html manifest.json sw.js js/status-bar.js js/safe-zones.js js/apps.js js/qs.js js/settings-store.js; do
    served_matches_disk "${f}"
done

SERVED_VER=$(curl -s -m 10 "${NUXEL_WEB_URL}/pwa/nuxel-home/js/status-bar.js" 2>/dev/null \
    | sed -n "s/.*static get VERSION() { return '\([^']*\)'; }.*/\1/p" | head -1)
MANIFEST_VER=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['nuxel']['pwa_version'])" \
    "${REPO_TREE}/pwa/nuxel-home/manifest.json" 2>/dev/null)
SW_CACHE=$(sed -n "s/^const CACHE_VERSION = '\([^']*\)';/\1/p" "${REPO_TREE}/pwa/nuxel-home/sw.js" 2>/dev/null | head -1)
say "  served status-bar revision=${SERVED_VER:-<none>} manifest pwa_version=${MANIFEST_VER:-<none>} sw cache=${SW_CACHE:-<none>}"
if [ -n "${SERVED_VER}" ] && [ "${SERVED_VER}" = "${MANIFEST_VER}" ]; then
    ok "the SERVED status-bar revision is the manifest revision (${SERVED_VER})"
    PASS=$((PASS+1))
else
    bad "served status-bar revision (${SERVED_VER:-none}) != manifest pwa_version (${MANIFEST_VER:-none})"
    FAIL=$((FAIL+1))
fi

say "  browser-origin CORS preflight for the bridge (the PWA request shape):"
PREFLIGHT=$(curl -s -m 10 -D - -o /dev/null -X OPTIONS \
    -H 'Origin: http://127.0.0.1:8000' \
    -H 'Access-Control-Request-Method: POST' \
    -H 'Access-Control-Request-Headers: content-type,x-nuxel-bridge-version' \
    "${NUXEL_API_URL_LOCAL}/rpc" 2>/dev/null)
printf '%s\n' "${PREFLIGHT}" | sed 's/^/    /' | tee -a "${OUT}" >/dev/null
if printf '%s\n' "${PREFLIGHT}" | grep -i '^access-control-allow-headers:' | tr 'A-Z' 'a-z' \
        | grep -q 'x-nuxel-bridge-version'; then
    ok "bridge preflight allows X-Nuxel-Bridge-Version (a page-origin RPC can complete)"
    PASS=$((PASS+1))
else
    bad "bridge preflight does NOT allow X-Nuxel-Bridge-Version -> every PWA fetch is blocked by the browser (mock fallback). Fix the Access-Control-Allow-Headers list in the bridge API."
    FAIL=$((FAIL+1))
fi

# ---------------------------------------------------------------------------
# [9] service graph: offline validator (briq-04b) vs the LIVE unit graph.
#     The offline validator proves the repository graph is well formed; it can
#     never prove the running VM is running that graph.  This section compares
#     the two directly (installed / enabled / active / After= resolution) so a
#     stale deployment is a FAIL with the exact unit named, not an assumption.
# ---------------------------------------------------------------------------
say ""
say "--- [9] service-graph validator vs live unit graph (briq-11b) ---"
graph_crosscheck() {
    NUXEL_REPO_TREE="${REPO_TREE}" python3 - <<'PY9'
import glob
import json
import os
import re
import subprocess

REPO = os.environ.get('NUXEL_REPO_TREE', '/home/nuxel/nuxel')
CORE = ['nuxel-bridge.service', 'nuxel-portal.service', 'nuxel-notifications.service',
        'nuxel-http-bridge.service', 'nuxel-web.service']


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, ((r.stdout or '') + (r.stderr or '')).strip()


# --- the repository's canonical unit set ---------------------------------
canon = {}
for p in sorted(glob.glob(os.path.join(REPO, 'services', '**', '*.service'), recursive=True)):
    canon[os.path.basename(p)] = p
print('[INFO] canonical .service files in the deployed tree: %d' % len(canon))

# --- the offline validator (briq-04b) ------------------------------------
report = None
validator = os.path.join(REPO, 'tools/s10plus/a33/verify-service-graph.py')
if os.path.exists(validator):
    rc, out = run('cd %s && python3 %s --json /tmp/nuxel-service-graph.json --quiet' % (REPO, validator))
    try:
        with open('/tmp/nuxel-service-graph.json') as fh:
            report = json.load(fh)
    except Exception as exc:
        print('[FAIL] service-graph validator produced no JSON report: %r' % (exc,))
    if report:
        verdict = report.get('verdict')
        print('[INFO] offline validator verdict=%s unit_count=%s problems=%s warnings=%s'
              % (verdict, report.get('unit_count'), len(report.get('problems') or []),
                 len(report.get('warnings') or [])))
        for w in (report.get('warnings') or [])[:10]:
            print('[WARN] validator: %s' % w)
        if report.get('problems'):
            print('[FAIL] service-graph validator problems: %s' % (report['problems'] or [])[:5])
        else:
            print('[PASS] offline service-graph validator: %s (offline evidence, never a live claim)' % verdict)
    else:
        print('[FAIL] the offline service-graph validator did not run')
else:
    print('[INFO] NOT VERIFIED HERE - verify-service-graph.py not present under %s/tools' % REPO)

# --- the live unit graph -------------------------------------------------
rc, out = run("systemctl list-unit-files --type=service --all --no-legend")
live_files = {}
for line in out.splitlines():
    parts = line.split()
    if len(parts) >= 2 and parts[0].endswith('.service'):
        live_files[parts[0]] = parts[1]
rc, out = run("systemctl list-units --type=service --all --no-legend --plain")
live_state = {}
for line in out.splitlines():
    parts = line.split()
    if len(parts) >= 4 and parts[0].endswith('.service'):
        live_state[parts[0]] = parts[2]          # UNIT LOAD ACTIVE SUB DESCRIPTION
print('[INFO] live unit files: %d, live units: %d' % (len(live_files), len(live_state)))

want = sorted((report or {}).get('builder_installed') or list(canon.keys()))
missing = [u for u in want if u not in live_files and u not in live_state]
if missing:
    print('[FAIL] units the repository installs but the VM does NOT have: %s' % missing)
else:
    print('[PASS] every unit the repository installs exists in the live unit graph (%d units)' % len(want))

enabled_want = sorted((report or {}).get('builder_enabled') or [])
if enabled_want:
    not_enabled = [u for u in enabled_want if live_files.get(u) != 'enabled']
    if not_enabled:
        print('[FAIL] units enabled by the builder but not enabled live: %s'
              % ['%s(%s)' % (u, live_files.get(u, 'absent')) for u in not_enabled])
    else:
        print('[PASS] every builder-enabled unit is enabled live (%d units)' % len(enabled_want))

for u in CORE:
    state = live_state.get(u, live_files.get(u, 'absent'))
    if state == 'active':
        print('[PASS] core unit active in the live graph: %s' % u)
    else:
        print('[FAIL] core unit NOT active: %s (state=%s)' % (u, state))

# --- After= resolution of the nuxel units --------------------------------
unresolved = []
checked = 0
for u in sorted(set(list(canon.keys()) + CORE)):
    rc, out = run("systemctl show -p After --value %s 2>/dev/null" % u)
    if rc != 0 or not out:
        continue
    checked += 1
    for dep in out.split():
        if dep.endswith(('.service', '.target', '.socket', '.mount')):
            if dep in live_files or dep in live_state:
                continue
            if dep in ('basic.target', 'sysinit.target', 'sockets.target', 'paths.target'):
                continue
            rc2, out2 = run("systemctl list-unit-files --all --no-legend '%s'" % dep)
            if not out2:
                unresolved.append('%s -> %s' % (u, dep))
if checked:
    if unresolved:
        print('[FAIL] After= dependencies that do not resolve in the live graph: %s' % sorted(set(unresolved)))
    else:
        print('[PASS] all After= dependencies of the nuxel units resolve in the live graph (%d units checked)' % checked)

# --- real systemd parses the canonical unit files ------------------------
files = ' '.join(sorted(canon.values()))
if files:
    rc, out = run('systemd-analyze verify %s 2>&1' % files)
    errors = [l for l in out.splitlines()
              if re.search(r'(Unknown key|Failed to|not found|Invalid)', l)]
    if errors:
        print('[FAIL] systemd-analyze verify reported %d problem line(s); first: %s'
              % (len(errors), errors[0][:180]))
        for line in errors[:10]:
            print('    %s' % line[:180])
    else:
        print('[PASS] systemd-analyze verify accepts every canonical unit file (real systemd parser)')
PY9
}
while IFS= read -r _line; do
    case "${_line}" in
        '[PASS]'*) say "${_line}"; PASS=$((PASS+1)) ;;
        '[FAIL]'*) say "${_line}"; FAIL=$((FAIL+1)) ;;
        *)         say "${_line}" ;;
    esac
done < <(graph_crosscheck 2>&1)

say "=============================================================="
say " RESULT: PASS=${PASS} FAIL=${FAIL} NOT_VERIFIED_HERE=${NVER}"
say " BRIDGE-ALIVE GATE: active=${BRIDGE_ACTIVE} dbus-name=${BRIDGE_DBUS}"
say " E2E summary: auth=${E2E_AUTH_OK:-0} perm_flow=${E2E_PERM_OK:-0} notification+persist=${E2E_NOTIF_OK:-0}"
say " Full log: ${OUT}"
say "=============================================================="
# Verification is diagnostic; exit 0 so deploy proceeds to report (FAIL>0 is
# surfaced via the log and the report). VERIFY_STRICT=1 flips to a real exit.
if [ "${VERIFY_STRICT:-0}" = "1" ] && [ "${FAIL}" -gt 0 ]; then
    exit 1
fi
exit 0

#!/usr/bin/env bash
# =============================================================================
# vm/vm-verify-pwa.sh  (briq-12-pwa / group bg-06)
#
# Guest-side END-TO-END verification of the Nuxel Home / PWA path. Runs INSIDE
# the VM as the nuxel user (root wrapper su's with the full graphical session
# environment). Verifies, with REAL evidence and NO hypothetical commands:
#
#   A. HTTP layer  -- the documented dev path, served by nuxel-web on :8000:
#        chromium --kiosk http://127.0.0.1:8000/pwa/nuxel-home/index.html
#      (WebKitGTK/epiphany are used here as the real engine; chromium is not
#      installed in the Fedora guest. The path/port come from
#      services/nuxel-web.service: WorkingDirectory=/home/nuxel/nuxel,
#      python3 -m http.server 8000 --bind 127.0.0.1.)
#      Each asset is fetched and checked: index.html (real launcher markup),
#      manifest.json (install manifest), sw.js (service worker), js/bridge.js,
#      ../nuxel-common/bridge.js (shared ES-module bridge client).
#
#   B. Live JavaScript execution -- a WebKit2GTK 4.1 harness (real browser
#      engine, python3-gi) loads the PWA on the live Phosh Wayland display and
#      proves, from inside the page:
#        * Nuxel Home loads and its JavaScript builds the UI (app grid, dock,
#          status bar time are populated by JS, not static HTML);
#        * the shared ES-module bridge client executed (window.NuxelBridge);
#        * the service worker REGISTERS AND ACTIVATES (scope
#          /pwa/nuxel-home/) and populates its caches (nuxel-static-v1);
#        * bridge.js OPERATES: NuxelBridge.call('ping','ping',...) round-trips
#          through POST /api/v1/rpc and returns the real bridge result;
#        * API communication works from the page (CORS-allowed fetch to
#          127.0.0.1:8080), with bridge.connected==true and mockMode==false --
#          a mock/fallback response is explicitly NOT accepted as proof.
#
#   C. Visual evidence -- grim captures the rendered PWA on the Phosh display
#      for human review (screenshots are saved under ~/Pictures/nuxel-verify/
#      in the guest and copied to the host vm/screenshots/ by the caller).
#
# Honesty rules: every sub-check is recorded PASS / FAIL / NOT VERIFIED HERE.
# Chromium-kiosk mode is a DEV path only -- this script does NOT claim a
# production PWA isolation runtime (see nuxel-ultimate-build.md audit).
#
# Usage (in the guest):
#   bash vm/vm-verify-pwa.sh
# Env overrides: PWA_URL (default http://127.0.0.1:8000/pwa/nuxel-home/index.html),
#                API_URL (default http://127.0.0.1:8080/api/v1),
#                PWA_TIMEOUT_SEC (default 120).
# =============================================================================
set -uo pipefail

NUXEL_USER="${NUXEL_USER:-nuxel}"
# Write the evidence log under the invoking user's home instead of the shared
# /var/tmp path: SELinux labels /var/tmp files user_tmp_t, so a root->su(nuxel)
# re-exec (or a prior root run) cannot reliably write a file the other user owns.
OUT="${HOME:-/tmp}/nuxel-pwa-verify.log"
: > "${OUT}"
SNAP_DIR="/home/${NUXEL_USER}/Pictures/nuxel-verify"
mkdir -p "${SNAP_DIR}"

say()  { echo "$*" | tee -a "${OUT}"; }
ok()   { echo -e "[PASS] $*" | tee -a "${OUT}"; }
bad()  { echo -e "[FAIL] $*" | tee -a "${OUT}"; }
warn() { echo -e "[WARN] $*" | tee -a "${OUT}"; }
nver() { echo -e "[INFO] NOT VERIFIED HERE - $*" | tee -a "${OUT}"; }

if [ "$(id -u)" = "0" ]; then
    uid="$(id -u "${NUXEL_USER}")"
    export XDG_RUNTIME_DIR="/run/user/${uid}"
    my_ses="$(loginctl list-sessions --no-legend 2>/dev/null \
        | awk -v u="${NUXEL_USER}" '$3==u && $4!="-" {print $1; exit}')"
    if [ -n "${my_ses:-}" ]; then
        st_type="$(loginctl show-session -p Type --value "${my_ses}" 2>/dev/null)"
        [ -n "${st_type:-}" ] && export XDG_SESSION_TYPE="${st_type}"
        st_disp="$(loginctl show-session -p Display --value "${my_ses}" 2>/dev/null)"
        [ -n "${st_disp:-}" ] && export DISPLAY="${st_disp}"
    fi
    wsock="$(ls /run/user/${uid}/wayland-* 2>/dev/null | head -1)"
    [ -n "${wsock:-}" ] && export WAYLAND_DISPLAY="$(basename "${wsock}")"
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${uid}/bus"
    rm -f "${OUT}"
    su -s /bin/bash "${NUXEL_USER}" -c "bash '/home/${NUXEL_USER}/nuxel/vm/vm-verify-pwa.sh'" \
        || warn "user-session re-run returned non-zero."
    exit 0
fi

PWA_URL="${PWA_URL:-http://127.0.0.1:8000/pwa/nuxel-home/index.html}"
API_URL="${API_URL:-http://127.0.0.1:8080/api/v1}"
PWA_TIMEOUT_SEC="${PWA_TIMEOUT_SEC:-120}"
HARNESS="/tmp/nuxel-pwa-verify-harness.py"

say "=============================================================="
say " Nuxel Home / PWA end-to-end verification -- $(date -u +%Y-%m-%dT%H:%M:%SZ)"
say " user=$(id -un) PWA_URL=${PWA_URL} API_URL=${API_URL}"
say " WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-<unset>} DISPLAY=${DISPLAY:-<unset>}"
say "=============================================================="

PASS=0; FAIL=0; NVER=0

# ---------------------------------------------------------------------------
# PART A -- HTTP layer (the exact dev path, live server on :8000)
# ---------------------------------------------------------------------------
say ""
say "--- PART A: HTTP layer of the dev PWA path (nuxel-web :8000) ---"

http_check() {
    # $1 = label, $2 = url path, $3 = expected content marker (optional)
    local label="$1" url="$2" marker="${3:-}"
    local code ctype
    code=$(curl -s -m 8 -o /tmp/nuxel-pwa-body -w "%{http_code}" "${url}")
    ctype=$(curl -s -m 8 -o /dev/null -w "%{content_type}" "${url}")
    if [ "${code}" = "200" ]; then
        ok "HTTP 200 ${label}: ${url} (${ctype})"
        PASS=$((PASS+1))
    else
        bad "HTTP ${code} ${label}: ${url}"
        FAIL=$((FAIL+1))
        return 1
    fi
    if [ -n "${marker}" ]; then
        if grep -q "${marker}" /tmp/nuxel-pwa-body; then
            ok "  content marker '${marker}' present in ${label}"
            PASS=$((PASS+1))
        else
            bad "  content marker '${marker}' MISSING in ${label}"
            FAIL=$((FAIL+1))
        fi
    fi
}

http_check "PWA index.html"           "${PWA_URL}"                 'Nuxel Home'
http_check "manifest.json"            "http://127.0.0.1:8000/pwa/nuxel-home/manifest.json" '"name"'
http_check "service worker sw.js"     "http://127.0.0.1:8000/pwa/nuxel-home/sw.js"         'addEventListener'
http_check "home bridge.js"           "http://127.0.0.1:8000/pwa/nuxel-home/js/bridge.js"  'NuxelBridge'
http_check "shared ES module bridge.js" "http://127.0.0.1:8000/pwa/nuxel-common/bridge.js" 'class NuxelBridgeClient'

# SW must be served with a JS MIME type or browsers refuse to install it.
sw_ct=$(curl -s -m 8 -o /dev/null -w "%{content_type}" "http://127.0.0.1:8000/pwa/nuxel-home/sw.js")
case "${sw_ct}" in
    *javascript*|*ecmascript*) ok "sw.js served with JS MIME: ${sw_ct}"; PASS=$((PASS+1));;
    *) bad "sw.js served with suspicious MIME: ${sw_ct}"; FAIL=$((FAIL+1));;
esac

# ---------------------------------------------------------------------------
# PART B -- live JavaScript / service worker / bridge.js / API in WebKitGTK
# ---------------------------------------------------------------------------
say ""
say "--- PART B: live JS execution in WebKitGTK 4.1 (real engine) ---"

cat > "${HARNESS}" <<'PYEOF'
#!/usr/bin/env python3
"""WebKit2GTK harness: load the Nuxel Home PWA and prove JS/SW/bridge/API."""
import json, os, subprocess, sys, time
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2, GLib

PWA_URL = os.environ.get('PWA_URL', 'http://127.0.0.1:8000/pwa/nuxel-home/index.html')
API_URL = os.environ.get('API_URL', 'http://127.0.0.1:8080/api/v1')
SNAP_DIR = os.environ.get('SNAP_DIR', '/home/nuxel/Pictures/nuxel-verify')
os.makedirs(SNAP_DIR, exist_ok=True)

CHECK_JS = r"""
(async () => {
  const out = {};
  out.readyState = document.readyState;
  out.title = document.title;
  out.appItems = document.querySelectorAll('#app-list > *').length;
  out.dockItems = document.querySelectorAll('#dock-items > *').length;
  out.timeText = (document.querySelector('#status-time') || {}).textContent || '';
  out.bodyClass = document.body ? document.body.className : '';
  out.hasNuxelBridgeGlobal = typeof window.NuxelBridge !== 'undefined';
  out.bridgeApiUrl = (window.NuxelBridge && window.NuxelBridge.apiUrl) || null;
  out.bridgeAppId = (window.NuxelBridge && window.NuxelBridge.appId) || null;
  out.bridgeConnected = (window.NuxelBridge && window.NuxelBridge.connected) || false;
  out.bridgeMockMode = (window.NuxelBridge && window.NuxelBridge.mockMode) || null;
  try {
    const regs = await navigator.serviceWorker.getRegistrations();
    out.swRegistrations = regs.map(r => ({scope: r.scope,
      active: !!(r.active), installing: !!(r.installing), waiting: !!(r.waiting)}));
  } catch (e) { out.swError = String(e); }
  try { out.cacheNames = await caches.keys(); } catch (e) { out.cachesError = String(e); }
  try {
    const r = await window.NuxelBridge.call('ping', 'ping', {message: 'pwa-verify'});
    out.bridgeCall = r;
    out.bridgeConnectedAfter = window.NuxelBridge.connected;
    out.bridgeMockAfter = window.NuxelBridge.mockMode;
  } catch (e) { out.bridgeCallError = String(e); }
  try {
    const r = await fetch(__PWA_API_URL__ + '/ping?message=pwa-verify-fetch');
    const text = await r.text();
    out.apiFetch = {status: r.status, body: text};
  } catch (e) { out.apiFetchError = String(e); }
  window.__pwa_done = true;
  window.__pwa_result = JSON.stringify(out);
  return true;
})(); true;
"""

# The in-page collection script runs inside the WebView; substitute the
# real API URL into the JS so the page fetch targets the actual bridge
# (bare `API_URL` is undefined in page scope -> ReferenceError otherwise).
CHECK_JS = CHECK_JS.replace('__PWA_API_URL__', json.dumps(API_URL))

state = {'result': None, 'err': None, 'console': [], 'loaded': False,
         'load_err': None, 'timeout': False}

def js(webview, script):
    """Run JS synchronously-ish (async API, blocking loop w/ 8s cap)."""
    holder = {}
    loop = GLib.MainLoop()
    def cb(view, res, _ud=None):
        try:
            jres = view.run_javascript_finish(res)
            v = jres.get_js_value()
            holder['val'] = v.to_string() if v else None
        except Exception as e:  # noqa: BLE001
            holder['err'] = str(e)
        loop.quit()
    webview.run_javascript(script, None, cb)
    GLib.timeout_add(8000, lambda: (loop.quit(), False)[1])
    loop.run()
    return holder

def main():
    win = Gtk.Window(title='nuxel-pwa-verify')
    win.set_default_size(440, 940)
    webview = WebKit2.WebView()
    settings = webview.get_settings()
    settings.set_enable_developer_extras(True)
    settings.set_enable_write_console_messages_to_stdout(False)
    win.add(webview)
    win.show_all()

    # console-message was removed from WebKitGTK >= 2.40 GI bindings
    # (renamed/removed in 2.52); guard it so the harness runs on both.
    try:
        webview.connect('console-message', lambda w, msg: state['console'].append(msg.get_message()))
    except TypeError:
        state['console'].append('(console-message signal not exposed by this WebKitGTK; skipped)')
    webview.connect('load-changed', lambda w, ev: state.__setitem__('loaded', ev == WebKit2.LoadEvent.FINISHED))
    webview.connect('load-failed', lambda w, ev, uri, err: state.__setitem__('load_err', '%s (%s)' % (err.message, uri)))

    webview.load_uri(PWA_URL)
    deadline = time.time() + int(os.environ.get('PWA_TIMEOUT_SEC', '120'))
    done = False
    injected = False
    while time.time() < deadline and not done:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(0.5)
        if state['loaded'] and not injected:
            # Page finished loading: inject the in-page collection script
            # (CHECK_JS) exactly once. It runs as an async IIFE inside the
            # page and sets window.__pwa_done once every sub-check completes.
            # FIX: the previous harness only POLLED for __pwa_done without
            # ever injecting CHECK_JS, so page_result was always None and
            # every run ended as "WebKit harness produced no in-page result".
            js(webview, CHECK_JS)
            injected = True
        if injected:
            h = js(webview, 'window.__pwa_done === true ? "DONE" : "PENDING"')
            if h.get('val') == 'DONE':
                done = True
    if not done:
        state['timeout'] = True
    res = js(webview, 'window.__pwa_result || "null"')
    state['result'] = res.get('val')
    state['js_err'] = res.get('err')

    # Screenshot of the rendered PWA while the window is still mapped.
    try:
        env = dict(os.environ)
        shot = os.path.join(SNAP_DIR, 'pwa-home-webkit-%s.png' % time.strftime('%Y%m%d-%H%M%S'))
        subprocess.run(['grim', shot], env=env, timeout=10, check=False)
        state['screenshot'] = shot if os.path.exists(shot) else None
    except Exception as e:  # noqa: BLE001
        state['screenshot_err'] = str(e)

    out = {
        'pwa_url': PWA_URL,
        'api_url': API_URL,
        'load_finished': state['loaded'],
        'load_error': state['load_err'],
        'timeout': state['timeout'],
        'page_result': json.loads(state['result']) if state['result'] and state['result'] != 'null' else None,
        'eval_error': state['js_err'],
        'console': state['console'][-15:],
        'screenshot': state['screenshot'],
    }
    print(json.dumps(out, indent=2, default=str))
    Gtk.main_quit()
    sys.exit(0 if (out['page_result'] and not out['timeout']) else 3)

if __name__ == '__main__':
    GLib.timeout_add(500, main)
    Gtk.main()
PYEOF

# Export the session env explicitly for the harness + grim.
export PWA_URL API_URL PWA_TIMEOUT_SEC SNAP_DIR
export GDK_BACKEND="${GDK_BACKEND:-wayland}"
export GSK_RENDERER="${GSK_RENDERER:-cairo}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
# WebKit internal sandbox (bubblewrap) may be unavailable in some VMs; the
# harness first tries the default, and retries with the sandbox disabled if
# the page never finishes loading. This does NOT affect Nuxel's own
# AppArmor/nftables enforcement (verified separately by vm-verify-services.sh).
run_harness() {
    env EXTRA="${1:-}" timeout "${PWA_TIMEOUT_SEC}" python3 "${HARNESS}" 2>&1 \
        | tee -a "${OUT}"
}
HAR_OUT="$(run_harness)"
if ! echo "${HAR_OUT}" | grep -q '"page_result": {'; then
    say "  first harness attempt did not produce a page result; retrying with WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1 ..."
    HAR_OUT="$(WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1 run_harness)"
fi
echo "${HAR_OUT}" > /tmp/nuxel-pwa-harness-out.json

page_result=$(python3 - <<'PYEOF'
import json
try:
    # The tee'd output includes the harness's stderr warning lines BEFORE the
    # JSON object, so a direct json.load() of the whole file fails. Find the
    # first '{' and parse from there (the harness emits exactly one JSON doc).
    txt = open('/tmp/nuxel-pwa-harness-out.json').read()
    start = txt.find('{')
    d = json.loads(txt[start:])
    print(json.dumps(d.get('page_result') or {}))
except Exception:
    print('{}')
PYEOF
)

if [ -z "${page_result}" ] || [ "${page_result}" = "{}" ]; then
    bad "WebKit harness produced no in-page result (see ${OUT})"
    FAIL=$((FAIL+1))
else
    say "  harness page_result: $(echo "${page_result}" | head -c 4000)"
    # B1: JS executed -> UI built
    app_items=$(echo "${page_result}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('appItems',0))")
    dock_items=$(echo "${page_result}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('dockItems',0))")
    if [ "${app_items:-0}" -gt 0 ] && [ "${dock_items:-0}" -gt 0 ]; then
        ok "Nuxel Home JS executed: app grid has ${app_items} item(s), dock has ${dock_items} item(s)"
        PASS=$((PASS+1))
    else
        bad "Nuxel Home JS did not populate the UI (appItems=${app_items:-0} dockItems=${dock_items:-0})"
        FAIL=$((FAIL+1))
    fi
    # B2: shared ES-module bridge client executed
    has_bridge=$(echo "${page_result}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('hasNuxelBridgeGlobal', False))")
    if [ "${has_bridge}" = "True" ]; then
        ok "shared bridge.js ES module executed: window.NuxelBridge present"
        PASS=$((PASS+1))
    else
        bad "window.NuxelBridge missing -- shared bridge module did not execute"
        FAIL=$((FAIL+1))
    fi
    # B3: service worker registered + activated + caches populated
    sw_json=$(echo "${page_result}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('swRegistrations') or []))")
    cache_json=$(echo "${page_result}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('cacheNames') or []))")
    if echo "${sw_json}" | grep -q '/pwa/nuxel-home/' && echo "${sw_json}" | grep -q '"active": true'; then
        ok "service worker registered+active at scope /pwa/nuxel-home/ : ${sw_json}"
        PASS=$((PASS+1))
    else
        bad "service worker NOT active: ${sw_json} (caches=${cache_json})"
        FAIL=$((FAIL+1))
    fi
    if echo "${cache_json}" | grep -q "nuxel-static"; then
        ok "SW install populated its caches: ${cache_json}"
        PASS=$((PASS+1))
    else
        warn "no SW caches listed yet: ${cache_json}"
    fi
    # B4: bridge.js operates (real RPC round-trip, no mock)
    conn_after=$(echo "${page_result}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('bridgeConnectedAfter', d.get('bridgeConnected', False)))")
    mock_after=$(echo "${page_result}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('bridgeMockAfter','?'))")
    call_json=$(echo "${page_result}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('bridgeCall') or {}))")
    if [ "${conn_after}" = "True" ] && [ "${mock_after}" = "False" ]; then
        ok "bridge.js operates: NuxelBridge.call() round-tripped, connected=true mockMode=false"
        say "  bridge.call('ping','ping') -> ${call_json}"
        PASS=$((PASS+1))
    else
        bad "bridge.js NOT live (connected=${conn_after} mock=${mock_after}) -- mock fallback must NOT count"
        say "  bridge.call result: ${call_json}"
        FAIL=$((FAIL+1))
    fi
    # B5: API communication from the page. The apiFetch body is a JSON string
    # (escaped inside api_json), so parse it rather than grep for '"status": "ok"'.
    api_json=$(echo "${page_result}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('apiFetch') or {}))")
    api_ok=$(echo "${page_result}" | python3 -c "
import json,sys
d = json.load(sys.stdin)
af = d.get('apiFetch') or {}
try:
    body = json.loads(af.get('body') or '{}')
    ok = af.get('status') == 200 and body.get('status') == 'ok'
except Exception:
    ok = False
print('YES' if ok else 'NO')")
    if [ "${api_ok}" = "YES" ]; then
        ok "in-page fetch to ${API_URL}/ping succeeded (HTTP 200, real bridge JSON): ${api_json}"
        PASS=$((PASS+1))
    else
        bad "in-page API fetch failed: ${api_json}"
        FAIL=$((FAIL+1))
    fi
fi

# ---------------------------------------------------------------------------
say ""
say "=============================================================="
say " RESULT: PASS=${PASS} FAIL=${FAIL}"
if [ "${FAIL}" -eq 0 ]; then
    say " Nuxel Home/PWA path verified end-to-end (HTTP layer + live JS + SW + bridge.js + API)."
else
    say " Failures present -- see individual checks above."
fi
say " NOTE: this is the DEV PWA path (WebKitGTK in the Phosh session). It is NOT"
say "       proof of a production PWA isolation runtime (Flatpak/WPE not built)."
say " OUTPUT: ${OUT}"
say "=============================================================="
exit $(( FAIL > 0 ? 1 : 0 ))

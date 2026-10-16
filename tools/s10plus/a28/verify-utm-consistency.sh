#!/bin/sh
# ============================================================================
# verify-utm-consistency.sh — measure the UTM launcher and compare it with the
# S10+ port, NUMERICALLY.
#
# The launcher's DOM is measured inside the running UTM guest (WebKitGTK 4.1,
# the real engine, on the live Phosh display) and every value that the phone's
# adapter compiles in is compared against it:
#
#   app count / grid order / dock order   vs pwa/nuxel-home/js/apps.js
#   per-app glyph + colour + background    vs apps.js (and the tint rule in
#                                          js/launcher.js)
#   icon rect / radius / font sizes        vs css/style.css + css/launcher.css
#   grid display / gaps, dock height+bg,   vs the same CSS
#   status-bar height, body background
#
# No screenshots are taken and no image is interpreted: these are computed
# styles and bounding boxes, i.e. the launcher's own numbers.
#
# Usage: sh tools/s10plus/a28/verify-utm-consistency.sh [--vm-user nuxel] [--ip IP]
# Exit: 0 consistent, 1 a mismatch, 2 a required tool/input is missing.
# ============================================================================
set -eu
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
A28="$ROOT/tools/s10plus/a28"
VM_USER=${VM_USER:-nuxel}
UTMCTL=${UTMCTL_BIN:-/Applications/UTM.app/Contents/MacOS/utmctl}
VM_NAME=${VM_NAME:-nuxel-aarch64-phosh}
IP=""
while [ $# -gt 0 ]; do
    case "$1" in
        --vm-user) VM_USER="$2"; shift 2 ;;
        --ip) IP="$2"; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 required" >&2; exit 2; }
if [ -z "$IP" ]; then
    IP="$( { "$UTMCTL" ip-address "$VM_NAME" 2>/dev/null || true; } \
        | awk '/^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/{print; exit}' )"
fi
[ -n "$IP" ] || IP=192.168.64.3
SSH="ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=6"
OUT="$ROOT/build/out/s10plus/a28/utm-geometry.json"
mkdir -p "$(dirname "$OUT")"

echo "== UTM launcher geometry (guest $IP, WebKitGTK on the live display) =="
$SSH "$VM_USER@$IP" 'mkdir -p /tmp/nuxel-a28' >/dev/null 2>&1 || true
$SSH "$VM_USER@$IP" 'cat > /tmp/nuxel-a28/pwa-geometry-harness.py' <"$A28/pwa-geometry-harness.py"
$SSH "$VM_USER@$IP" 'export XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-0 \
    GDK_BACKEND=wayland WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1 PWA_TIMEOUT_SEC=90; \
    python3 /tmp/nuxel-a28/pwa-geometry-harness.py' >"$OUT" 2>"$OUT.err" || {
    echo "   harness failed:"; tail -5 "$OUT.err"; exit 2; }

python3 - "$OUT" "$A28/generated/nuxel-launcher.json" <<'PYEOF'
import json, sys
geo_path, reg_path = sys.argv[1], sys.argv[2]
try:
    geo = json.load(open(geo_path))["geometry"]
except Exception as e:
    print("   could not parse the guest geometry: %s" % e)
    sys.exit(1)
reg = json.load(open(reg_path))
apps = {a["name"]: a for a in reg["apps"]}
fails = []

def rgb(s):
    if not s: return None
    if s.startswith("rgb("):
        return tuple(int(x) for x in s[4:-1].split(","))
    if s.startswith("rgba("):
        return tuple(int(float(x)) for x in s[5:-1].split(",")[:3])
    return None

def ck(cond, what):
    print("   %s %s" % ("PASS" if cond else "FAIL", what))
    if not cond: fails.append(what)

grid = geo["grid"]; dock = geo["dock"]; bar = geo["statusBar"]; body = geo["body"]
ck(geo["registryCount"] == 9, "the VM's own registry holds 9 apps")
ck(geo["order"] == [a["name"] for a in sorted(reg["apps"], key=lambda a: a["name"])],
   "getAllApps() order == the generated registry order")
ck(geo["dockOrder"] == reg["dock"], "getDockedApps() order == the port's dock order %s" % (reg["dock"],))
ck(grid["itemCount"] == reg["grid"].__len__() and
   [apps[n]["id"] for n in reg["grid"]] == [i for i in grid["items"]],
   "grid DOM order == the port's grid order %s" % (reg["grid"],))
ck(dock["count"] == len(reg["dock"]) and [apps[n]["id"] for n in reg["dock"]] == dock["items"],
   "dock DOM order == the port's dock order")
ck(grid["display"] == "grid" and grid["columnGap"] == "8px" and grid["rowGap"] == "16px",
   "grid is display:grid with gap 16px 8px (port: 4 columns, 16/8 design px)")
ck(grid["columns"].count("px") == 4, "grid has 4 columns (%s)" % grid["columns"])
ck(dock["height"] == 80, "dock height 80px (port: --dock-height)")
ck(rgb(dock["background"]) == (13, 31, 60), "dock background is --bg-secondary #0d1f3c")
ck(dock["gap"] == "20px", "dock item gap 20px (port: 20 design px)")
ck(bar["height"] == 36, "status bar height 36px (port: --status-bar-height)")
ck(rgb(body["backgroundColor"]) == (26, 26, 46), "body background-color #1a1a2e (port fallback)")
ck("nuxel-background.png" in (body["backgroundImage"] or ""), "body loads the Nuxel wallpaper asset")
ck(geo["title"]["fontSize"] == "28px", "app-grid title 28px (port: 28 design px)")
icon_token = int(reg["tokens"]["--app-icon-size"].rstrip("px"))
pad_token = int(reg["tokens"]["--grid-padding"].rstrip("px"))
ck(round(grid["rect"]["x"]) == pad_token,
   "app-grid left padding %dpx == the EFFECTIVE --grid-padding (media <=480px)" % pad_token)
ck(round(bar["height"]) == int(reg["tokens"]["--status-bar-height"].rstrip("px")),
   "status bar height == --status-bar-height")
ck(round(dock["height"]) == int(reg["tokens"]["--dock-height"].rstrip("px")),
   "dock height == --dock-height")
for name in [x["name"] for x in reg["apps"]]:
    a = apps[name]
    key = a["id"]
    g = geo["apps"].get(key)
    if g is None:
        ck(False, "the VM renders %s (%s)" % (name, key)); continue
    want = a["color"]
    wr, wg, wb = int(want[1:3], 16), int(want[3:5], 16), int(want[5:7], 16)
    ck(rgb(g["color"]) == (wr, wg, wb), "%s icon colour == apps.js %s" % (name, want))
    ck(rgb(g["background"]) == (wr, wg, wb, 0x33) if len(rgb(g["background"]) or ()) == 4
       else rgb(g["background"])[:3] == (wr, wg, wb),
       "%s icon background is <colour>@0x33 (launcher.js tint rule)" % name)
    ck(g["glyph"] == a["icon"], "%s glyph == the registry emoji %r" % (name, a["icon"]))
    want_icon = icon_token
    ck(round(g["rect"]["w"]) == want_icon and round(g["rect"]["h"]) == want_icon,
       "%s icon is %dx%d CSS px (port: %d design px)" % (name, want_icon, want_icon, want_icon))
    ck(g["radius"] == "16px", "%s icon radius 16px (port: --app-icon-radius)" % name)
    if not a["docked"]:
        ck(g["labelFontSize"] == "11px", "%s label 11px (port: 11 design px)" % name)
        ck((g["name"] or "") == name, "%s label text == the registry name" % name)
if fails:
    print("A28_UTM_CONSISTENCY_FAILED (%d)" % len(fails))
    sys.exit(1)
print("A28_UTM_CONSISTENCY_OK — the S10+ adapter and the UTM launcher agree on "
      "the registry, the order, the tint rule, the icons and every geometry token")
PYEOF

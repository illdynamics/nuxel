#!/bin/sh
# Nuxel phone session — runs INSIDE the phoc compositor (phoc -E ...).
#
# Composition (identical to the UTM VM, minus the VM's browser that is not
# installed on the handset - nuxel-pwa-host takes that role):
#   1. the static PWA server.  nuxel-web.service is the single owner of
#      127.0.0.1:8000.  This session only starts a development fallback on
#      127.0.0.1:8001 when nuxel-web is not reachable, so a later nuxel-web
#      restart can always bind :8000 instead of failing with EADDRINUSE;
#   2. the real launcher (WebKitGTK view) through nuxel-pwa-host.
#
# DOCROOT LAYOUT (fixed A29b, measured): services/nuxel-web.service does NOT
# serve pwa/nuxel-home.  It serves the repository root so that the launcher's own
# relative reference `../nuxel-common/bridge.js` (index.html line 125, enforced
# by pwa/nuxel-common/verify-wiring.js) resolves.  The launcher URL is therefore
# /pwa/nuxel-home/index.html and BOTH pwa/nuxel-home and pwa/nuxel-common must
# exist under the docroot.  The first phone image staged only /usr/share/nuxel/
# nuxel-home (no pwa/ level, no nuxel-common), which 404'd the index and the
# bridge module; this script now resolves the layout and says which one it used.
#
# Software rendering is forced because this kernel has no DRM/EGL device.
set -eu
export XDG_SESSION_TYPE=wayland
export GDK_BACKEND=wayland
export WEBKIT_DISABLE_COMPOSITING_MODE=1
export LIBGL_ALWAYS_SOFTWARE=1
export GSK_RENDERER=cairo
LOG=/run/nuxel-session.log
say() { echo "$(date -u +%FT%TZ) $*" >>"$LOG"; }

DOCROOT=/usr/share/nuxel
WEB_PORT=8000
FALLBACK_PORT=8001
# Layout A = the VM's (and the image builder's) pwa/ tree; layout B = the flat
# copy the first handset image shipped.  Chosen by the launcher's own index.html.
HOME_REL=""
for c in /pwa/nuxel-home /nuxel-home; do
  if [ -f "$DOCROOT$c/index.html" ]; then HOME_REL="$c"; break; fi
done
if [ -z "$HOME_REL" ]; then
  say "FATAL launcher index.html not found under $DOCROOT (looked for /pwa/nuxel-home, /nuxel-home)"
  exit 1
fi
[ -n "${NUXEL_HOME_URL:-}" ] || NUXEL_HOME_URL="http://127.0.0.1:$WEB_PORT$HOME_REL/index.html"
# the ES module the launcher imports by relative path
BRIDGE="$DOCROOT${HOME_REL%/*}/nuxel-common/bridge.js"
if [ -f "$BRIDGE" ]; then BRIDGE_OK=yes; else BRIDGE_OK=no; fi

say() { echo "$(date -u +%FT%TZ) $*" >>"$LOG"; }
say "session start WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-?} layout=$HOME_REL bridge_ok=$BRIDGE_OK url=$NUXEL_HOME_URL"

if ! curl -fsS -o /dev/null "$NUXEL_HOME_URL" 2>/dev/null; then
  # nuxel-web.service owns :8000.  Never bind that port here: a fallback on
  # the same port makes every later `systemctl restart nuxel-web` fail with
  # OSError EADDRINUSE.  The launcher can still load from :8001 in this case.
  FALLBACK_URL="http://127.0.0.1:$FALLBACK_PORT$HOME_REL/index.html"
  ( cd "$DOCROOT" && exec python3 -m http.server "$FALLBACK_PORT" --bind 127.0.0.1 ) >/run/nuxel-web.log 2>&1 &
  WEB_PID=$!
  for i in $(seq 1 40); do
    curl -fsS -o /dev/null "$FALLBACK_URL" && break
    sleep 0.25
  done
  if curl -fsS -o /dev/null "$FALLBACK_URL"; then
    READY=yes
    NUXEL_HOME_URL="$FALLBACK_URL"
  else
    READY=no
  fi
  say "web fallback pid=$WEB_PID port=$FALLBACK_PORT ready=$READY url=$NUXEL_HOME_URL"
else
  say "web server already serving on :$WEB_PORT"
fi
# A45 KEYBOARD: the persistent Back/Home/Recents dock is a native
# zwlr_layer_shell_v1 OVERLAY surface with an exclusive zone, so the native
# Stevia OSK (the working keyboard) stops above it instead of covering it.
# Start both as session Wayland clients, before the launcher host takes the
# foreground.  Stevia is started inside a session D-Bus so its OSK provider
# registration succeeds.
say "starting A45 nav dock + Stevia OSK"
nohup /usr/lib/nuxel/nuxel-navdock </dev/null >/run/nuxel-navdock.out 2>&1 &
if [ -x /usr/bin/phosh-osk-stevia ]; then
  nohup dbus-run-session -- /usr/bin/phosh-osk-stevia </dev/null >/run/stevia.out 2>&1 &
fi

say "starting launcher host url=$NUXEL_HOME_URL"
exec /usr/lib/nuxel/nuxel-pwa-host

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
# Native communication apps run as the real session user (see the HTTP bridge's
# NATIVE_AS_SESSION_USER list), so the compositor runtime directory must be
# traversable.  The Wayland socket itself is already 0755.
chmod 0755 /run/nuxel-wayland 2>/dev/null || true
# Native communication apps run as the session user.  Give that user access to
# the compositor socket (write permission is required to connect to a Unix
# socket); the runtime directory itself stays non-world-writable.
if getent group nuxel >/dev/null 2>&1; then
  chgrp nuxel /run/nuxel-wayland 2>/dev/null || true
  chmod 0750 /run/nuxel-wayland 2>/dev/null || true
  if [ -S /run/nuxel-wayland/wayland-0 ]; then
    chgrp nuxel /run/nuxel-wayland/wayland-0 2>/dev/null || true
    chmod 0660 /run/nuxel-wayland/wayland-0 2>/dev/null || true
    chgrp nuxel /run/nuxel-wayland/wayland-0.lock 2>/dev/null || true
    chmod 0640 /run/nuxel-wayland/wayland-0.lock 2>/dev/null || true
  fi
  # GTK/dconf writes $XDG_RUNTIME_DIR/dconf/user; give the session user that
  # per-user scratch directory, not root ownership.
  mkdir -p /run/nuxel-wayland/dconf 2>/dev/null || true
  chown -R nuxel:nuxel /run/nuxel-wayland/dconf 2>/dev/null || true
  chmod 0700 /run/nuxel-wayland/dconf 2>/dev/null || true
fi
export GDK_BACKEND=wayland
export WEBKIT_DISABLE_COMPOSITING_MODE=1
export LIBGL_ALWAYS_SOFTWARE=1
export GSK_RENDERER=cairo
LOG=/run/nuxel-session.log
# Native GUI applications run as the real nuxel user (uid 1000) so Firefox,
# VLC and the GNOME tools do not refuse a root session.  They need the
# compositor socket and a user-owned XDG_RUNTIME_DIR; create that runtime view
# without ever copying the socket or weakening the compositor directory.
mkdir -p /run/user/1000 2>/dev/null || true
chown 1000:1000 /run/user/1000 2>/dev/null || true
chmod 0700 /run/user/1000 2>/dev/null || true
chgrp nuxel /run/nuxel-wayland 2>/dev/null || true
chmod 0750 /run/nuxel-wayland 2>/dev/null || true
if [ -S /run/nuxel-wayland/wayland-0 ]; then
  chgrp nuxel /run/nuxel-wayland/wayland-0 /run/nuxel-wayland/wayland-0.lock 2>/dev/null || true
  chmod 0660 /run/nuxel-wayland/wayland-0 2>/dev/null || true
  chmod 0640 /run/nuxel-wayland/wayland-0.lock 2>/dev/null || true
  ln -sfn /run/nuxel-wayland/wayland-0 /run/user/1000/wayland-0 2>/dev/null || true
  ln -sfn /run/nuxel-wayland/wayland-0.lock /run/user/1000/wayland-0.lock 2>/dev/null || true
fi
# Claim the boot overlay before the systemd fallback unit can write the
# one-shot marker.  The controller yields to this marker; it is per-boot
# because /run is a tmpfs.
: > /run/nuxel-preload-session.owner 2>/dev/null || true
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

# PWNAGE-36000: the preload controller publishes its first-frame state as a
# regular file under the PWA docroot (nuxel-web refuses symlink escapes from
# the docroot, so /run cannot be linked in).  Remove any status file
# unconditionally BEFORE this boot's controller starts.  A previous controller
# (or the old systemd unit) can leave a current-boot-id "fallback" document
# behind; the launcher would then release the cover immediately and expose the
# lockscreen for the first second.  The session controller owns this file for
# the whole boot and rewrites it atomically from "starting" onward.
PRELOAD_STATUS_FILE="$DOCROOT$HOME_REL/preload-status.json"
rm -f "$PRELOAD_STATUS_FILE" 2>/dev/null || true
[ -L "$PRELOAD_STATUS_FILE" ] && rm -f "$PRELOAD_STATUS_FILE" 2>/dev/null || true

say() { echo "$(date -u +%FT%TZ) $*" >>"$LOG"; }
say "session start WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-?} layout=$HOME_REL bridge_ok=$BRIDGE_OK url=$NUXEL_HOME_URL"
if [ -x /usr/lib/nuxel/nuxel-home-layout.sh ]; then
  /usr/lib/nuxel/nuxel-home-layout.sh >>"$LOG" 2>&1 || say "home layout setup failed"
fi
if [ -x /usr/lib/nuxel/nuxel-gstreamer-guard.sh ]; then
  /usr/lib/nuxel/nuxel-gstreamer-guard.sh >>"$LOG" 2>&1 || say "gstreamer guard failed"
fi

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
# PWNAGE-31000 PRE-LOCKSCREEN CINEMA (early): map the preloading video BEFORE
# the launcher host constructs the lockscreen, so the first composited frame
# shows the video rather than a one-second lockscreen flash.  The controller is
# a fail-open presentation overlay: it never blocks the launcher and falls back
# to the normal lockscreen on every failure path.
if [ -x /usr/lib/nuxel/nuxel-preload-cinema ]; then
  # The early controller waits for /run/nuxel-launcher-ready, then maps mpv
  # above the launcher.  Give that marker a generous bound: the cover is
  # opaque until the controller publishes its first presented frame, so a
  # slower audio/navdock startup can never expose the lockscreen.
  NUXEL_PRELOAD_EARLY=1 \
  NUXEL_PRELOAD_EARLY_WAIT_LAUNCHER_MS="${NUXEL_PRELOAD_EARLY_WAIT_LAUNCHER_MS:-6000}" \
  NUXEL_PRELOAD_EARLY_MAP_DELAY_MS="${NUXEL_PRELOAD_EARLY_MAP_DELAY_MS:-800}" \
  NUXEL_PRELOAD_WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}" \
  nohup /usr/lib/nuxel/nuxel-preload-cinema --early \
      </dev/null >/run/nuxel-preload-cinema.out 2>&1 &
  say "starting pre-lockscreen cinema overlay pid=$!"
fi

# PWNAGE-32000 KEYBOARD: the persistent Back/Home/Recents dock is a native
# zwlr_layer_shell_v1 OVERLAY surface with an exclusive zone, so the native
# Stevia OSK (the working grey/black/white keyboard) stops above it instead
# of covering it.  Start both as session Wayland clients before the launcher
# host takes the foreground.  Stevia is started inside a session D-Bus so its
# OSK provider registration succeeds.
say "starting A45 nav dock + Stevia OSK"
nohup /usr/lib/nuxel/nuxel-navdock </dev/null >/run/nuxel-navdock.out 2>&1 &
# Persistent top status strip over fullscreen native clients (Firefox/VLC/...).
# It has an empty input region, so Home's DOM status-bar gestures still work.
if [ -x /usr/lib/nuxel/nuxel-statusbar ]; then
  nohup /usr/lib/nuxel/nuxel-statusbar </dev/null >/run/nuxel-statusbar.out 2>&1 &
fi
if [ -x /usr/bin/phosh-osk-stevia ]; then
  nohup dbus-run-session -- /usr/bin/phosh-osk-stevia </dev/null >/run/stevia.out 2>&1 &
fi

# PWNAGE-43000 AUDIO: PipeWire runs in its own systemd cgroup, not inside the
# phoc/WebKit cgroup.  The ABOX core-firmware reload can therefore drop the
# ALSA runtime-PM reference by stopping only the audio unit, without tearing
# down the compositor, framebuffer bridge or launcher (the old cold-boot storm).
# Session D-Bus for GTK/Qt/Flatpak-independent native apps.  It never owns
# audio and never starts/stops with the ABOX reload, so this restores the bus
# that the old in-session audio block used to create without re-coupling them.
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
  BUS_SOCKET=/run/nuxel-wayland/bus
  [ -S "$BUS_SOCKET" ] && rm -f "$BUS_SOCKET" 2>/dev/null || true
  if dbus-daemon --session --fork --address="unix:path=$BUS_SOCKET" --nopidfile >/run/nuxel-dbus.out 2>&1; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=$BUS_SOCKET"
    say "session dbus $BUS_SOCKET"
  else
    say "session dbus unavailable"
  fi
fi
say "starting standalone audio session"
systemctl --no-block start nuxel-audio-session.service 2>/dev/null || \
  say "audio session service unavailable; audio route retry remains"
chgrp -R audio /dev/snd 2>/dev/null || true
chmod -R g+rw /dev/snd 2>/dev/null || true

say "starting launcher host url=$NUXEL_HOME_URL"
exec /usr/lib/nuxel/nuxel-pwa-host

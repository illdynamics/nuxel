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
# phoc may create the Wayland socket just AFTER it starts this session command.
# A one-shot chmod at startup raced that creation and left the socket 0755
# root:root, so Firefox/VLC/GTK apps running as nuxel could not connect.  Watch
# briefly for the socket and grant only the nuxel group access.
if getent group nuxel >/dev/null 2>&1; then
  (
    i=0
    while [ "$i" -lt 100 ]; do
      if [ -S /run/nuxel-wayland/wayland-0 ]; then
        chgrp nuxel /run/nuxel-wayland /run/nuxel-wayland/wayland-0 /run/nuxel-wayland/wayland-0.lock 2>/dev/null || true
        chmod 0750 /run/nuxel-wayland 2>/dev/null || true
        chmod 0660 /run/nuxel-wayland/wayland-0 2>/dev/null || true
        chmod 0640 /run/nuxel-wayland/wayland-0.lock 2>/dev/null || true
        mkdir -p /run/user/1000 /run/user/1000/dconf 2>/dev/null || true
        chown 1000:1000 /run/user/1000 /run/user/1000/dconf 2>/dev/null || true
        chmod 0700 /run/user/1000 /run/user/1000/dconf 2>/dev/null || true
        # The root PWA host can recreate dconf under the compositor runtime;
        # never leave it root-owned while a session-user app needs it.
        mkdir -p /run/nuxel-wayland/dconf 2>/dev/null || true
        chown -R nuxel:nuxel /run/nuxel-wayland/dconf 2>/dev/null || true
        ln -sfn /run/nuxel-wayland/wayland-0 /run/user/1000/wayland-0 2>/dev/null || true
        ln -sfn /run/nuxel-wayland/wayland-0.lock /run/user/1000/wayland-0.lock 2>/dev/null || true
        break
      fi
      i=$((i + 1))
      sleep 0.1
    done
  ) &
fi
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
# PWNAGE-60000: one validated policy owns the graphics environment.  The
# measured GPU-rendered/SHM-presented profile is the production default for
# Home, Settings and the launcher's WebKit web process.  The helper runs a
# bounded kbase EGL probe once per boot (cached under /run) and returns the
# software-safe environment if the device, libraries or EGL path are unhealthy.
# The compositor wrapper writes /run/nuxel-gpu-fallback before this script runs,
# so a phoc GPU failure also forces the matching software policy.  Never global:
# native apps resolve their own profile through `env native:<id>`.
if [ -x /usr/lib/nuxel/nuxel-graphics-profile ]; then
  # Pre-warm the bounded probe so the first WebKit launch does not pay for it.
  timeout 8 /usr/lib/nuxel/nuxel-graphics-profile probe       >/run/nuxel-gpu-session-probe.json 2>&1 || true
  eval "$(/usr/lib/nuxel/nuxel-graphics-profile env webkit)" || true
else
  export WEBKIT_DISABLE_COMPOSITING_MODE=1
  export LIBGL_ALWAYS_SOFTWARE=1
fi
# PWNAGE-60000: GTK4's probe passes with the kbase Mesa GL renderer.  Only use
# it when the validated graphics profile is active; a GPU fallback keeps GTK4
# on the known-good cairo renderer.  GTK 4.20.4 rejects the literal "auto".
if [ "${NUXEL_GRAPHICS_PROFILE_ACTIVE:-software-safe}" = "software-safe" ]; then
  export GSK_RENDERER="${GSK_RENDERER:-cairo}"
else
  export GSK_RENDERER="${GSK_RENDERER:-gl}"
fi
LOG=/run/nuxel-session.log
# Native GUI applications run as the real nuxel user (uid 1000) so Firefox,
# VLC and the GNOME tools do not refuse a root session.  They need the
# compositor socket and a user-owned XDG_RUNTIME_DIR; create that runtime view
# without ever copying the socket or weakening the compositor directory.
# The Flatpak X11 socket path is shared by native X11 clients.  A
# root-owned 0755 directory makes bwrap fail with EACCES even though the
# app has the x11 socket permission; keep the standard 1777 mode.
mkdir -p /tmp/.X11-unix 2>/dev/null || true
chmod 1777 /tmp/.X11-unix 2>/dev/null || true
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

# PWNAGE-93000: native GTK and Flatpak/portal apps publish notifications as
# org.freedesktop.Notifications on their SESSION bus.  The authoritative Nuxel
# hub lives on the system bus, so start one small FDO relay per real session bus
# (root compositor bus + uid 1000 user bus).  Relays only forward; they never
# create a second notification store.
start_notification_relay() {
  _bus="$1"; _runas="$2"; _label="$3"; _pidfile="/run/nuxel-notif-relay-$_label.pid"
  [ -r /usr/lib/nuxel/nuxel-notifications/notifications.py ] || return 0
  if [ -f "$_pidfile" ]; then
    _old=$(cat "$_pidfile" 2>/dev/null || true)
    case "$_old" in ''|*[!0-9]*) _old=0;; esac
    if [ "$_old" -gt 1 ] && kill -0 "$_old" 2>/dev/null; then
      say "notification relay $_label already running pid=$_old"
      return 0
    fi
  fi
  if [ "$_runas" = root ]; then
    DBUS_SESSION_BUS_ADDRESS="$_bus" nohup /usr/bin/python3       /usr/lib/nuxel/nuxel-notifications/notifications.py --session       </dev/null >>"/run/nuxel-notif-relay-$_label.log" 2>&1 &
  else
    nohup runuser -u "$_runas" -- env DBUS_SESSION_BUS_ADDRESS="$_bus"       XDG_RUNTIME_DIR=/run/user/1000 HOME=/home/nuxel       /usr/bin/python3 /usr/lib/nuxel/nuxel-notifications/notifications.py --session       </dev/null >>"/run/nuxel-notif-relay-$_label.log" 2>&1 &
  fi
  echo $! >"$_pidfile"
  say "started notification relay $_label pid=$!"
}

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
  # PWNAGE-62000: the JSON config is the single authoritative timing source.
  # Only the launch-mode and display are set here; explicit operator overrides
  # already present in the environment are inherited untouched.  Never repeat
  # a different default here (the old 6000/800 shell fallbacks silently beat
  # the checked-in 4000/1200 values).
  NUXEL_PRELOAD_EARLY=1 \
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
# PWNAGE-62000: one supervised owner starts the native nav dock, the native
# top bar and the compositor-level lock enforcer.  The native bar hides itself
# on Home and while locked, so it never duplicates Home's DOM bar; the dock is
# the single Back/Penguin Home/Tabs surface over native and Flatpak apps.
say "starting supervised shell chrome (navdock + statusbar + lock enforcement)"
if [ -x /usr/lib/nuxel/nuxel-shell-chrome.sh ]; then
  nohup /usr/lib/nuxel/nuxel-shell-chrome.sh </dev/null >/run/nuxel-shell-chrome.out 2>&1 &
else
  say "shell-chrome supervisor missing; starting navdock only (degraded)"
  nohup /usr/lib/nuxel/nuxel-navdock </dev/null >/run/nuxel-navdock.out 2>&1 &
fi
# The native OSD is a separate, transparent overlay used only for volume and
# power-menu feedback; it is not part of the top bar contract.
if [ -x /usr/lib/nuxel/nuxel-osd ]; then
  nohup /usr/lib/nuxel/nuxel-osd </dev/null >/run/nuxel-osd.out 2>&1 &
fi
# Apply the keyboard document before Stevia starts.  Besides the gsettings the
# applier normally owns, this writes the opt-in /run/nuxel-text-input-v1.enabled
# marker phoc polls for the Electron/Chromium v1 compatibility global.  The
# long-running path unit also re-runs the applier when Settings rewrites the
# document; this early call makes the marker deterministic on every boot.
if [ -x /usr/local/bin/nuxel-keyboard-apply.sh ]; then
  XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}" \
    timeout 20 /usr/local/bin/nuxel-keyboard-apply.sh apply >>"$LOG" 2>&1 || say "keyboard apply failed"
elif [ -x /usr/libexec/nuxel/nuxel-keyboard-apply ]; then
  XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}" \
    timeout 20 /usr/libexec/nuxel/nuxel-keyboard-apply apply >>"$LOG" 2>&1 || say "keyboard apply failed"
fi
if [ -x /usr/bin/phosh-osk-stevia ]; then
  # ydotoold creates a uinput keyboard that Stevia would otherwise treat as a
  # real hardware keyboard and suppress the OSK for.  A phone must always be
  # able to raise the touch keyboard, so ignore attached keyboard devices.
  XDG_RUNTIME_DIR=/run/nuxel-wayland gsettings set mobi.phosh.osk ignore-hw-keyboards true 2>/dev/null || true
  # Publish the OSK's private session-bus address so phoc can re-assert
  # sm.puri.OSK0.SetVisible(TRUE) when an already-focused text field is tapped
  # after the keyboard was folded.  dbus-run-session creates the bus first.
  rm -f /run/nuxel-osk.bus
  nohup dbus-run-session -- sh -c 'printf "%s\n" "$DBUS_SESSION_BUS_ADDRESS" > /run/nuxel-osk.bus; exec /usr/bin/phosh-osk-stevia' </dev/null >/run/stevia.out 2>&1 &
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
    # PWNAGE-63000: publish the session environment to D-Bus activation so the
    # gnome-keyring-daemon starts in THIS session (HOME=/root, XDG_RUNTIME_DIR
    # and the Wayland display), not in an unrelated or root-system context.
    if [ -x /usr/bin/dbus-update-activation-environment ]; then
      dbus-update-activation-environment \
        DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR WAYLAND_DISPLAY \
        GDK_BACKEND XDG_SESSION_TYPE HOME >/dev/null 2>&1 || true
    fi
    # Warm up the Secret Service name once, in the background and bounded: the
    # bootstrap must never wait for a first-time user to create a keyring.
    if [ -x /usr/bin/busctl ]; then
      ( timeout 8 busctl --address="unix:path=$BUS_SOCKET" \
          call org.freedesktop.secrets /org/freedesktop/secrets \
          org.freedesktop.Secret.Service ReadAlias s default \
          >/dev/null 2>&1 || true ) &
    fi
  else
    say "session dbus unavailable"
  fi
fi
if [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
  start_notification_relay "$DBUS_SESSION_BUS_ADDRESS" root root
fi
# PWNAGE-56000: Flatpak needs a REAL per-user session bus and portals.  The
# root-owned /run/nuxel-wayland/bus is for the compositor/native host; Flatpak
# apps and xdg-desktop-portal must talk on /run/user/1000/bus so the document
# portal and GTK dialogs run as the same uid as the app.  No desktop is pulled
# in: only xdg-desktop-portal + xdg-desktop-portal-gtk are used.
USER_RUNTIME=/run/user/1000
USER_BUS=$USER_RUNTIME/bus
install -d -m 0700 -o nuxel -g nuxel "$USER_RUNTIME" 2>/dev/null || true
if ! pgrep -u nuxel -f "dbus-daemon.*$USER_BUS" >/dev/null 2>&1; then
  [ -S "$USER_BUS" ] && rm -f "$USER_BUS" 2>/dev/null || true
  if runuser -u nuxel -- dbus-daemon --session --fork --address="unix:path=$USER_BUS" --nopidfile >/run/nuxel-user-dbus.log 2>&1; then
    say "user session dbus $USER_BUS"
  else
    say "user session dbus unavailable"
  fi
fi
if [ -S "$USER_BUS" ]; then
  chown nuxel:nuxel "$USER_BUS" 2>/dev/null || true
  chmod 0600 "$USER_BUS" 2>/dev/null || true
  start_notification_relay "unix:path=$USER_BUS" nuxel user
fi
PORTAL_ENVV="XDG_RUNTIME_DIR=$USER_RUNTIME DBUS_SESSION_BUS_ADDRESS=unix:path=$USER_BUS XDG_CURRENT_DESKTOP=Nuxel XDG_DATA_DIRS=/var/lib/flatpak/exports/share:/usr/local/share:/usr/share WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0} GDK_BACKEND=wayland GSK_RENDERER=cairo LIBGL_ALWAYS_SOFTWARE=1 PIPEWIRE_RUNTIME_DIR=/run/nuxel-wayland HOME=/home/nuxel"
if [ -S "$USER_BUS" ] && [ -x /usr/libexec/xdg-desktop-portal-gtk ]; then
  if ! pgrep -u nuxel -f "/usr/libexec/xdg-desktop-portal-gtk" >/dev/null 2>&1; then
    nohup runuser -u nuxel -- env $PORTAL_ENVV /usr/libexec/xdg-desktop-portal-gtk       </dev/null >/run/nuxel-portal-gtk.log 2>&1 &
    say "started xdg-desktop-portal-gtk uid=nuxel pid=$!"
  fi
  # PWNAGE-96000: the Nuxel FileChooser backend must be running before the
  # frontend parses portals.conf.  It has ONE request/response contract and
  # exposes Gallery + Files; it is not org.nuxel.Portal (hardware broker).
  if [ -x /usr/libexec/nuxel/nuxel-portal-chooser ]; then
    if ! pgrep -u nuxel -f "/usr/libexec/nuxel/nuxel-portal-chooser" >/dev/null 2>&1; then
      nohup runuser -u nuxel -- env $PORTAL_ENVV /usr/libexec/nuxel/nuxel-portal-chooser \
        </dev/null >/run/nuxel-portal-chooser.out 2>&1 &
      say "started Nuxel FileChooser backend uid=nuxel pid=$!"
    fi
  fi
  sleep 1
  if ! pgrep -u nuxel -f "^/usr/libexec/xdg-desktop-portal$" >/dev/null 2>&1; then
    nohup runuser -u nuxel -- env $PORTAL_ENVV /usr/libexec/xdg-desktop-portal       </dev/null >/run/nuxel-portal.log 2>&1 &
    say "started xdg-desktop-portal uid=nuxel pid=$!"
  fi
  # PWNAGE-94000: pre-start the DOCUMENT portal.  D-Bus activation of
  # org.freedesktop.portal.Documents could leave the first caller waiting the
  # full 30 s GetMountPoint timeout (measured: every `flatpak run` took 30.7 s,
  # even with --command=/bin/true).  The standard portal is not a sandbox
  # relaxation; it is the same portal Flatpak expects, started before the first
  # app.  Wait for its real fuse mount with a bounded readiness check.
  if [ -x /usr/libexec/xdg-document-portal ] && ! pgrep -u nuxel -f "^/usr/libexec/xdg-document-portal$" >/dev/null 2>&1; then
    nohup runuser -u nuxel -- env $PORTAL_ENVV /usr/libexec/xdg-document-portal \
      </dev/null >/run/nuxel-document-portal.log 2>&1 &
    say "started xdg-document-portal uid=nuxel pid=$!"
  fi
  i=0
  while [ "$i" -lt 50 ]; do
    grep -q " $USER_RUNTIME/doc " /proc/mounts && break
    i=$((i + 1)); sleep 0.1
  done
  if grep -q " $USER_RUNTIME/doc " /proc/mounts; then
    say "document portal mount ready $USER_RUNTIME/doc"
  else
    say "document portal mount not ready; Flatpak may pay the bounded D-Bus timeout"
  fi
  (
    sleep 2
    GTK=0; FRONT=0; WLR=0; NUXEL=0
    NAMES=$(runuser -u nuxel -- env $PORTAL_ENVV busctl --user list --no-pager 2>/dev/null || true)
    # Require an ACTIVE PID, not merely an activatable name.  The wlr backend
    # appears as activatable but exits when it cannot reach PipeWire.
    echo "$NAMES" | awk '$1=="org.freedesktop.impl.portal.desktop.gtk" && $2 ~ /^[0-9]+$/ {f=1} END{exit !f}' && GTK=1
    echo "$NAMES" | awk '$1=="org.freedesktop.portal.Desktop" && $2 ~ /^[0-9]+$/ {f=1} END{exit !f}' && FRONT=1
    echo "$NAMES" | awk '$1=="org.freedesktop.impl.portal.desktop.wlr" && $2 ~ /^[0-9]+$/ {f=1} END{exit !f}' && WLR=1
    echo "$NAMES" | awk '$1=="org.freedesktop.impl.portal.desktop.nuxel" && $2 ~ /^[0-9]+$/ {f=1} END{exit !f}' && NUXEL=1
    printf '{"portal":%s,"gtk":%s,"wlr":%s,"nuxel_filechooser":%s,"screencast":"%s","bus":"%s","updated":%s}\n' \
      "$FRONT" "$GTK" "$WLR" "$NUXEL" \
      "$([ "$WLR" = 1 ] && echo available || echo 'unavailable (wlr backend cannot reach PipeWire)')" \
      "$USER_BUS" "$(date +%s)" > /run/nuxel-portal-ready.json 2>/dev/null || true
  ) &
fi

say "starting standalone audio session"
systemctl --no-block start nuxel-audio-session.service 2>/dev/null || \
  say "audio session service unavailable; audio route retry remains"
chgrp -R audio /dev/snd 2>/dev/null || true
chmod -R g+rw /dev/snd 2>/dev/null || true
# PWNAGE-56000: Flatpak --socket=pulseaudio needs a user-visible Pulse socket.
# The audio session runs as root; make only the socket directory traversable by
# nuxel and expose the same socket through the standard per-user runtime path.
for _i in $(seq 1 50); do
  [ -S /run/nuxel-wayland/pulse/native ] && break
  sleep 0.2
done
if [ -S /run/nuxel-wayland/pulse/native ]; then
  chgrp nuxel /run/nuxel-wayland/pulse 2>/dev/null || true
  chmod 0750 /run/nuxel-wayland/pulse 2>/dev/null || true
  chgrp nuxel /run/nuxel-wayland/pulse/native 2>/dev/null || true
  chmod 0770 /run/nuxel-wayland/pulse/native 2>/dev/null || true
  ln -sfn /run/nuxel-wayland/pulse /run/user/1000/pulse 2>/dev/null || true
  chown -h nuxel:nuxel /run/user/1000/pulse 2>/dev/null || true
  say "flatpak pulse socket linked for nuxel"
fi

# PWNAGE-45000: a real graphical polkit agent for GNOME Software/PackageKit.
# It runs as the session user (uid 1000) on the shared session bus and Wayland
# socket, so authorization prompts appear above the client and can be touched.
mkdir -p /run/nuxel-wayland/dconf 2>/dev/null || true
chown -R nuxel:nuxel /run/nuxel-wayland/dconf 2>/dev/null || true
chmod 0700 /run/nuxel-wayland/dconf 2>/dev/null || true
POLKIT_AGENT=""
# xfce-polkit is GTK3 and can use the Wayland backend; lxpolkit is GTK2/X11
# only and cannot open a display on this image.
for _pa in /usr/libexec/xfce-polkit /usr/bin/xfce-polkit; do
  [ -x "$_pa" ] && { POLKIT_AGENT="$_pa"; break; }
done
if [ -n "$POLKIT_AGENT" ] && [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
  # polkit agents need a real logind subject.  This root-owned Phoc session has
  # no logind session on the 4.14 image; starting the agent anyway leaves an
  # empty window and a false impression of authorization.  Do not start it
  # until a nuxel logind session exists.
  if ! loginctl list-sessions --no-legend 2>/dev/null | awk '$3 == "nuxel" {found=1} END {exit !found}'; then
    say "no nuxel logind session; polkit agent not started (privileged prompts unavailable)"
    POLKIT_AGENT=""
  fi
fi
if [ -n "$POLKIT_AGENT" ] && [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
  if command -v runuser >/dev/null 2>&1; then
    nohup runuser -u nuxel -- env \
      XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}" \
      DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" \
      GDK_BACKEND=wayland GSK_RENDERER=cairo LIBGL_ALWAYS_SOFTWARE=1 \
      HOME=/home/nuxel "$POLKIT_AGENT" \
      </dev/null >/run/nuxel-polkit-agent.out 2>&1 &
    say "polkit graphical agent started ($POLKIT_AGENT uid=nuxel pid=$!)"
    # Agent registration needs a logind session.  Record the real outcome so
    # the UI/evidence does not claim an authorization prompt that cannot appear.
    sleep 1
    if ! pgrep -f "$(basename "$POLKIT_AGENT")" >/dev/null 2>&1; then
      say "polkit agent exited: no graphical authorization prompt available (logind session absent)"
    fi
  else
    say "polkit agent present but runuser unavailable; no graphical agent"
  fi
else
  say "no Wayland-capable polkit agent; Software transactions will report the blocker"
fi

say "starting launcher host url=$NUXEL_HOME_URL"
exec /usr/lib/nuxel/nuxel-pwa-host

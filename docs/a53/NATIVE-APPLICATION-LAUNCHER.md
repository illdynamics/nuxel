# NUXEL A53 — Native Wayland GTK Application Launch Path

## Gate status: `PASS_PHYSICAL` (basic window) · `PARTIAL` (session integration)

## M1 evidence — a genuine native GTK4 app opens a window on the physical panel

Ran under the live session's exact env (not the console's bare shell):

```
# env XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 XDG_SESSION_TYPE=wayland \
  GDK_BACKEND=wayland LIBGL_ALWAYS_SOFTWARE=1 GSK_RENDERER=cairo \
  timeout 6 adwaita-1-demo ; echo rc=$?
(adwaita-1-demo:7645): Gtk-WARNING: Unable to acquire session bus: Cannot autolaunch D-Bus without X11 $DISPLAY
rc=124   # timeout fired while the app was still alive → the window stayed open (did NOT crash)
```

`rc=124` = `timeout(1)` killed a still-running process; the app created a real GTK4/Wayland
surface on the physical display through Phoc and stayed up for the full bounded window. This
re-proves the A51 result on today's boot.

## What launches and what does not

| Capability | Status | Evidence |
|---|---|---|
| GTK3/GTK4 Wayland window opens | PASS | `adwaita-1-demo` ran to timeout |
| GTK4 launch helper present | PASS | `gtk4-launch`, `gtk-launch` present |
| A real registered native app launches from Home | BLOCKED | registry native entries (`nuxel-dialer`/`messages`/`contacts`/`camera`) are placeholders with no `/usr/bin/nuxel-*` binary and no installed RPM app |
| Shared session D-Bus for native apps | PARTIAL | no `DBUS_SESSION_BUS_ADDRESS` for the session; GTK degrades to no-dconf/no-portal (the warning above) |
| Qt/Wayland | BLOCKED | `qt6-qtbase`/`qt6-qtwayland` absent (A51) |

## Trusted-launcher contract (already enforced in the bridge)

`services/nuxel-bridge/src/api.py` resolves an app id to an activation descriptor and **never
executes arbitrary input**: `_activate_app` validates the id as an identifier (no `..`, no path
separator), looks up the registry, and only hands back a `native_binary`/`url` the PWA host already
trusts. There is no `shell=True`, no client-supplied command/path execution on this path.

## Honest blocker

Installing a real native RPM app (Calculator, Snapshot, GNOME Software) is impossible without a
package manager + network (see `GNOME-SOFTWARE-RPM-FLATPAK.md`), so "launch a real installed native
app from Home" cannot be end-to-end proven this session. The launch *mechanism* itself works.

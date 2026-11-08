# A75 — OSK re-show on an already-focused text field

## Problem

Stevia's own swipe-down gesture folds the on-screen keyboard **without**
disabling the client's `zwp_text_input_v3`.  Tapping the same text field again
therefore produces no new `enable`/`activate` event, so the keyboard stayed
folded.  This affected native GTK apps and the Nuxel PWA host (WebKitGTK).

## Fix

1. `nuxel-session.sh` starts Stevia through a tiny `dbus-run-session` shell
   wrapper that publishes its private session-bus address to
   `/run/nuxel-osk.bus`.
2. `phoc-osk-reshow.patch` adds a small hook to
   `phoc_input_method_relay_im_submit()`: every touch/button press on the
   surface that owns an enabled, focused text input calls
   `sm.puri.OSK0.SetVisible(TRUE)` over that bus.  Calls are throttled to one
   per 250 ms.  Touches on the keyboard itself target the OSK surface, not the
   text-input surface, so typing does not re-trigger the hook.
3. The bridge also applies an app's configured rotation **before** spawning a
   new native app, so the app is born in the correct orientation and no resize
   race is introduced.

## Build and install (on the phone, as root)

```sh
/usr/lib/nuxel/a75-build-phoc-osk-reshow.sh
```

The script downloads phoc 0.54.0, applies the patch, builds it with the system
wlroots 0.19, backs up `/usr/sbin/phoc`, installs the new binary, and restarts
`nuxel-wayland`.

## Verification

With a GTK app such as Text Editor focused:

```sh
ADDR=$(cat /run/nuxel-osk.bus)
gdbus call --address "$ADDR" --dest sm.puri.OSK0 \
  --object-path /sm/puri/OSK0 \
  --method sm.puri.OSK0.SetVisible false
# tap the already-focused editor: Visible must become true again
gdbus call --address "$ADDR" --dest sm.puri.OSK0 \
  --object-path /sm/puri/OSK0 \
  --method org.freedesktop.DBus.Properties.Get sm.puri.OSK0 Visible
```

## Known boundary

Caprine 2.61 bundles Electron 29 / Chromium 122.  That Chromium only speaks
the removed `zwp_text_input_v1` protocol, while Phoc/wlroots 0.19 exposes
`zwp_text_input_v3`.  Consequently Chromium 122 cannot bind the OSK's text
input path; this is an upstream Electron/Chromium limitation, not a Phoc or
Stevia bug.  GTK apps and the Nuxel PWA host use v3 and are fully covered.

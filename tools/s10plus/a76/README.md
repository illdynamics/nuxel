# A76 — opt-in `zwp_text_input_v1` compatibility shim

## Problem

Caprine 2.61 bundles Electron 29 / Chromium 122. That Chromium only implements
the removed `zwp_text_input_v1` protocol. Phoc/wlroots 0.19 exposes
`zwp_text_input_v3`, so Caprine could not bind text input and Stevia never
received an activate request. Rotation worked; the keyboard did not.

## What this adds

Phoc now has an **opt-in** `zwp_text_input_manager_v1` global. When enabled, the
new adapter translates the small v1 subset used by Chromium onto the **same**
`zwp_input_method_v2` relay that Stevia already serves for v3:

- `activate` / `deactivate` → enter/leave + input-method activate/deactivate
- `show_input_panel` / `hide_input_panel` → Stevia `sm.puri.OSK0.SetVisible`
- surrounding text, content type, serial/commit state → input-method-v2 state
- preedit / commit / delete events from Stevia → v1 events
- tap-to-re-show on an already-focused v1 field, using the A75 OSK hook

The v3 path is untouched. GTK apps, WebKitGTK/PWAs and all normal keyboard
behavior continue to use `zwp_text_input_v3`.

## Turning it on and off

The global is **not** created unless `/run/nuxel-text-input-v1.enabled` contains
`1`/`true`/`yes`. Phoc polls that marker every 500 ms, so Settings changes apply
without a compositor restart. The marker is written by
`nuxel-keyboard-apply.sh` from the document key:

```json
"keyboard.text_input_v1": false
```

Enable it in **Settings → Keyboard → Legacy text-input v1 compatibility**
(needed by Caprine / Electron 29). Newly launched apps pick up the global
immediately; an already-running Electron app may need to be restarted before it
re-binds text input.

## Build and install (on the phone, as root)

```sh
/usr/lib/nuxel/a76-build-phoc-text-input-v1.sh
```

The script downloads phoc 0.54.0, applies `phoc-text-input-v1.patch`, builds it
with the system wlroots 0.19.3, backs up both phoc paths, installs the new
binary, and restarts `nuxel-wayland`.

## Verification

```sh
# enabled: both globals are advertised; disabled: only v3
wayland-info | grep -E 'zwp_text_input_manager_v[13]'

# marker + applier verdict
cat /run/nuxel-text-input-v1.enabled
grep text_input_v1 /run/nuxel-keyboard.state

# v3 must still be present and working regardless of the setting
wayland-info | grep zwp_text_input_manager_v3
```

## Honest limits

- This is a compatibility shim, not a full v1 implementation. `invoke_action`
  has no input-method-v2 equivalent and is ignored. Cursor-rectangle and
  preferred-language requests are recorded but input-method-v2 has no API to
  forward them.
- The shim is deliberately opt-in. If it is disabled while an Electron app is
  already running, that app keeps its old v1 binding until it exits; new apps see
  no v1 global.

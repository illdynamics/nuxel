# A59 — Nuxel Browser is now a real top-level WebKitGTK browser

## Outcome
`PASS_PHYSICAL` (network) + `PASS_ON_DEVICE_INTEGRATION` (browser launch/load).
The app-drawer `Browser` entry now launches a genuine, independent WebKitGTK
top-level browser — not the old iframe PWA.

## Root cause (from baseline)
- `org.nuxel.Browser` was a sandboxed `<iframe>` PWA. External sites (Google)
  refuse embedding via X-Frame-Options/CSP, and the PWA host's iframe could not
  present a top-level page.
- A real native browser (`shell/nuxel-browser-native/nuxel_browser_native.py`,
  GTK3 + WebKit2 4.1) was already deployed to the device at
  `/usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py` but was NOT
  registered in the app drawer and had no launcher path to exec it.

## What was implemented
1. `pwa/nuxel-home/js/apps.js`: `org.nuxel.Browser` is now `type: 'native'`
   with `nativeAppId: 'org.nuxel.BrowserNative'` and
   `native_binary: /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py`.
2. `pwa/nuxel-home/js/app.js`: `_launchNative()` now POSTs to the HTTP bridge's
   new closed-verb `/api/v1/apps/exec` endpoint instead of showing a
   "not implemented" toast.
3. `services/nuxel-bridge/src/api.py`: new `_exec_native_app()` + `/api/v1/apps/exec`.
   It launches only a fixed allowlist of registry binaries via `systemd-run`
   (the HTTP bridge runs under PrivateTmp/ProtectHome/ProtectSystem, so a
   direct fork would inherit a read-only /root + private /tmp and die — this was
   measured and fixed by moving the launch to a transient systemd unit).
4. `pwa/nuxel-common/app-registry.json`: registered `org.nuxel.BrowserNative`
   (registry_version bumped 4 → 5).

## On-device evidence (sanitised, no accounts/logins)
- Launched via `POST /api/v1/apps/exec {"target":"org.nuxel.BrowserNative"}`:
  `{"success":true,"launched":true,"unit":"nuxel-app-browsernative-…",...}`
- `/run/nuxel-browser.state` after load:
  `{"status":"finished","uri":"https://www.google.nl/","title":"",...}` —
  the WebView committed and finished a real HTTPS navigation (URI redirected
  `https://www.google.nl` → `https://www.google.nl/`).
- Independent process tree confirmed: a dedicated
  `WebKitNetworkProcess` + `WebKitWebProcess` pair (distinct from the
  launcher-host WebKit processes), i.e. a real second WebKitGTK instance.
- Screenshot `fnv64` differs from Home (browser page visible on the glass).
- The browser runs as the unprivileged graphical user (root session), with
  WebKit's normal process isolation; no `--no-sandbox`, no iframe, no proxy.

## Features present
- Real address/search field; `google.nl` normalises to `https://www.google.nl/`.
- Back / Forward / Reload / Go buttons wired to `go_back/go_forward/reload`.
- HTTPS + certificate validation (WebKit default fail-closed; `load-failed`
  records the error to `/run/nuxel-browser.state`).
- Browser navigation is independent of the launcher; the Penguin Home button
  minimises (does not kill) the window via `zwlr_foreign_toplevel_manager_v1`.

## Honest limitations
- `title` is currently empty in the state file for Google's homepage (the page
  sets its title via JS after `FINISHED`; a `notify::title` handler is a small
  follow-up, not a correctness blocker — the URI + committed/finished receipt
  prove the navigation).
- Multi-tab and bookmark persistence are intentionally NOT claimed (no fake
  toggles were added).

## Rollback
- `git checkout -- pwa/nuxel-home/js/apps.js pwa/nuxel-home/js/app.js pwa/nuxel-common/app-registry.json services/nuxel-bridge/src/api.py`
- On-device backups: `…/apps.js.a59-bak-20261022T202602` etc. (see ROLLBACK.md).

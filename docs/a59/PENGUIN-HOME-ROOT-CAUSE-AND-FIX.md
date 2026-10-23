# A59 — Penguin Home button: root cause and authoritative fix

## Root cause (architectural, not a DOM bug)
The Home action was owned by the launcher DOM (`app.js home()`). A DOM handler
can hide a PWA `<iframe>`, but it CANNOT lower/focus a separate native Wayland
toplevel (browser/camera/Snapshot/Firefox). The pre-A59 code also had
`_launchNative` as a "not implemented" toast, and `nuxel-pwa-host` only knew
how to destroy the Terminal surface — so "Home" could not reliably return to
Home Desktop 1 without killing native apps.

## Fix — one authoritative compositor-level Home
1. New trusted helper `tools/s10plus/a59/nuxel-foreign-toplevel.c`
   (cross-compiled aarch64, dlopen'd libwayland-client, no wayland headers on
   the Mac). It uses `zwlr_foreign_toplevel_manager_v1`, which phoc/wlroots
   actually exposes (verified: global `zwlr_foreign_toplevel_manager_v1 v3`).
2. `mode=home`: `set_minimized` on every non-Home toplevel (identified by
   `app_id == "nuxel-pwa-host"` / `title == "Nuxel"`) and `unset_minimized`
   (raise) on Home. This minimises — it does NOT kill — the app.
3. `services/nuxel-bridge/src/api.py` adds a closed-verb `/api/v1/apps/home`
   that runs that helper in the Wayland session env.
4. `pwa/nuxel-home/js/app.js home()` now, after
   `_closeOverlays()` + `launcher.mainDesktop()`, POSTs `/api/v1/apps/home`.

## On-device proof (physical display state)
- With the Nuxel Browser window open (`app_id=nuxel_browser_native.py`) and
  active, executing the Home action produced:
  `WIN title=Nuxel app_id=nuxel-pwa-host min=0 act=1`  (Home raised/active)
  `WIN title=Nuxel Browser app_id=nuxel_browser_native.py min=1 act=0` (minimised)
  and `pgrep` confirmed the browser process was STILL RUNNING (not killed).
- Same result verified for the Nuxel Camera window and the Snapshot window.

## What still works / is preserved
- Back/Recents remain the existing system navigation dock (no duplication).
- Terminal's existing close-on-Home path (pwa-host) is unchanged.
- Lockscreen hides the nav dock; screen-off does not emit ghost nav events.
- SnekByte pause/resume and native-app launcher integrations are untouched.

## Integration note
`apps/exec` and `apps/home` are CLOSED-verb endpoints: a client supplies only a
registry id (or the fixed word `home`); the program run is resolved from a fixed
allowlist/canonical registry — a compromised PWA cannot turn these into
arbitrary execution. The offline `test-launcher-activation.py` still passes its
"no execution primitive on the activation path" assertion.

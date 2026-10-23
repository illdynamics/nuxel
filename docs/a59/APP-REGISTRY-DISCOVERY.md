# A59 — App registry / discovery architecture

## One registry, no duplicates
- Canonical registry: `pwa/nuxel-common/app-registry.json` (bumped to
  registry_version 5). Consumed by:
  - the PWA launcher (`pwa/nuxel-home/js/apps.js`),
  - the HTTP bridge (`services/nuxel-bridge/src/api.py` → `/api/v1/apps/registry`),
  - the native shell consumer (`shell/nuxel-home-native/…/app_registry.json`).
- The HTTP bridge reads `NUXEL_APP_REGISTRY=/usr/share/nuxel/pwa/nuxel-common/app-registry.json`
  (deployed copy), and the launcher's `apps.js` is the drawer source of truth.

## What changed
- `org.nuxel.Browser` → native (real WebKitGTK browser).
- `nuxel-camera` → native (custom Nuxel Camera), `native_binary` set.
- Added `org.nuxel.BrowserNative`, `org.nuxel.CameraNative` native entries.
- Added previously-missing authored PWAs: Calculator, Clock, Photos, Weather,
  Maps, NuxTore, Recorder, SnekByte.
- Added `org.gnome.Snapshot` (native; shown with an unavailable/broken state
  until `installed` flips true).

## Dedup / integrity rules (honoured)
- One canonical id per app; the drawer's `Map` keying prevents duplicate
  Browser/Camera/SnekByte icons.
- Helper/no-display desktop entries are NOT surfaced as user apps; only the
  canonical user-facing set is registered.
- Native launch is a CLOSED-verb (`/api/v1/apps/exec`), resolved from a fixed
  allowlist + the registry — never a client-supplied path/command/shell text.
- `test-launcher-activation.py` passes: descriptors are registry-derived; the
  activation path contains no execution primitive; unknown/path ids are refused.

## Verification
- `POST /api/v1/apps/registry` returns version 5 with 14 apps, including both
  native browser/camera entries.
- Launcher drawer launch of `org.nuxel.Calculator` (PWA) and
  `org.nuxel.Browser` (native) both observed reaching ACTIVE/LAUNCHING state in
  the launcher diagnostics (no more "App not found").

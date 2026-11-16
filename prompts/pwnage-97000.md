# PWNAGE-97000 — KICKSTARTER

Execute **`full-pwnage-97000.md`** completely in the current Nuxel repository. This is an implementation mission, not a planning-only review.

## Mission

Fix system-wide file attachment selection and add Settings → File Handlers. Ferdium, WhatsApp (including a Ferdium service/wrapper if applicable), Signal and other compatible apps must be able to select real files from Nuxel **Gallery** or **Files**, then receive those files back in the original attachment composer.

## Mandatory first actions

1. Read `full-pwnage-97000.md` completely.
2. Inspect the current repo revision, `VERSION`, working tree and existing changes. Do not overwrite unrelated/user changes.
3. Re-verify these source paths:
   - `configs/nuxel/portals.conf`
   - `services/nuxel-portal/src/portal.py`
   - `docs/a53/FLATPAK-SANDBOX-PORTALS.md`
   - `images/s10plus/packages-manifest.json`
   - `pwa/nuxel-apps/photos/` (Gallery, app ID `org.nuxel.Photos`)
   - `pwa/nuxel-apps/files/` (Files, app ID `org.nuxel.Files`)
   - `pwa/nuxel-apps/settings/index.html`, `settings.js` and feature modules
   - `services/nuxel-bridge/src/api.py` and `pwa_store.py`
4. Prove the actual live file dialog route for Ferdium, Signal and WhatsApp. Determine whether WhatsApp is a Ferdium service or a separate installed app. Inventory package format, app IDs, Electron/GTK versions and logs.

## Critical architecture rule

Do not confuse:

- the **XDG FileChooser portal**, which returns selected file URIs/access to the requesting app; and
- **MIME file handlers**, which choose which app opens an existing file.

The repo's `org.nuxel.Portal` is a private Nuxel hardware-permission broker, not the freedesktop `org.freedesktop.portal.FileChooser` implementation. Keep it intact.

The supplied repo has a `portals.conf` mapping FileChooser to GTK, but its A53 portal report says the XDG portal frontend/backend were absent, and the S10+ package manifest does not list them. Re-check live state. A config file alone is not a working portal.

## Required implementation

1. Install/activate the XDG portal frontend and a real FileChooser backend if missing.
2. Implement a Nuxel FileChooser backend selected through a valid `.portal` descriptor and desktop-specific `portals.conf`, or deliver an equally standards-compliant implementation with evidence.
3. Provide a Nuxel picker with two sources:
   - **Gallery:** re-use `org.nuxel.Photos`, `photos.js`, `storage.media-list` and `camera.list-captures` in a safe read-only selection mode.
   - **Files:** re-use `org.nuxel.Files`, `files.js` and its real storage provider in an external selection mode.
4. Preserve the request handle, calling app, title, filters, multiple/directory options, current folder and cancellation lifecycle. Return valid file URIs and ensure selected files are actually accessible to the requester, including through the Documents portal for sandboxed apps.
5. Support `OpenFile`; implement `SaveFile` and `SaveFiles` correctly or return a standards-compliant error where the supported backend/version contract permits. No hung requests or fake success.
6. Add a Settings → **File Handlers** tab using the existing Settings app/host architecture. Include global Ask/Gallery/Files preference, per-app overrides, MIME Open-with defaults, portal health and a real test picker.
7. Add valid Gallery/Files desktop entries and MIME declarations only where their actual capabilities justify them. Gallery handles supported media; Files naturally handles directories and file browsing, not every file type.
8. Update package manifests, portal descriptors, DBus activation, user services, security policies, release manifests and deployment scripts.

## Security constraints

- No `--filesystem=host`, `--device=all`, `--no-sandbox` or broad app filesystem permission workaround.
- Enforce approved roots, canonical paths, symlink/`..` protections, URI encoding, per-request grants and correct read/write rights.
- Do not return fake file URIs for camera-store/base64-only media. Materialize a real managed file safely if required.
- Keep `org.nuxel.Portal` and the Nuxel Permission Manager unchanged except for deliberate, tested shared integration contracts.
- Never mark success until the requesting app can actually preview the chosen file.

## Execute and verify

- Add focused tests under `tests/pwnage97000/` plus portal backend unit/integration tests.
- Test actual frontend → backend dispatch, not only a direct backend method call.
- Exercise Gallery and Files, single/multi-select, image filters, generic files, Unicode/space-containing names, cancellation, save/directory flows and access-grant behaviour.
- On the physical S10+, test attachment selection in Ferdium/WhatsApp and Signal without sending a message. Confirm the preview appears in the original app.
- If Flatpak cannot run because the current kernel/user-namespace state blocks it, state that exact limitation and test available native clients; do not claim Flatpak success.
- Deploy through the existing `./scripts` workflow after inspecting the supported mechanism. Capture pre-deploy hashes and preserve rollback.
- Run relevant existing Settings, app registry, permission, bridge and portal tests as well as the new suite.

## Required evidence and completion

Create `PWNAGE-97000-REPORT.md` and `docs/pwnage-97000/evidence/<timestamp>/` with root cause per app, package/service state, active backend, portal config, app IDs, MIME defaults, security tests, deployment hashes, screenshots/logs and a PASS/FAIL/BLOCKED matrix distinguishing physical tests from harness tests.

**Do not stop at a plan.** Implement the mission end-to-end. If a specific app cannot be integrated, prove why, leave the general portal path correct, document a safe fallback and continue with the other apps. Do not claim DONE until the original app receives and previews the selected real file.

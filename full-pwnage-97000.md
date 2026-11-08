# FULL-PWNAGE-97000 — NUXEL FILE HANDLERS + SYSTEM FILE PICKER

**Mission:** Implement a complete, reliable, system-wide Nuxel File Handler and File Chooser system, including a new Settings → File Handlers section, proper Gallery/Files routing, and working file attachment selection in Ferdium, WhatsApp integrations/wrappers, Signal and other native/Flatpak applications.

**Target repository:** `nuxel-main` (the supplied archive identifies itself as `VERSION=v0.8.1-beta`; always inspect the live checkout and current revision before changing anything).  
**Primary device:** Samsung Galaxy S10+ / `beyond2lte`, Fedora-based Nuxel session, Phoc/Wayland.  
**Mission ID:** `97000`  
**Execution:** This is the complete implementation specification. Read it fully before editing. Do not stop after writing a plan or report; implement, test, deploy through the repository's supported scripts, and verify on the actual phone wherever possible.

---

## 0. Executive objective

Fix the broken file-selection experience across Nuxel.

When the user presses an attachment button inside Ferdium, WhatsApp (including a Ferdium service/wrapper if that is how it is installed), Signal, or another compatible application, the user must receive a working Nuxel file picker with two clear sources:

1. **Gallery** — the real Nuxel Gallery (`org.nuxel.Photos`) for images and videos from the shared media store and supported user media directories.
2. **Files** — the real Nuxel Files app (`org.nuxel.Files`) for general filesystem browsing and arbitrary files.

The selected file(s) must be returned to the requesting application using the correct system contract. A pretty chooser that merely opens Gallery or Files but does not return usable files to the original application is not a solution.

Additionally, add a first-class **Settings → File Handlers** section. It must let the user inspect and configure:

- Default attachment picker source: Ask every time / Gallery / Files.
- Per-application picker source overrides, including installed Ferdium, Signal and other relevant apps discovered at runtime.
- Default “Open with” applications for supported MIME types.
- Gallery and Files associations, with correct semantics (Gallery handles supported image/video media; Files is the file manager and directory browser, not a universal image decoder).
- Current portal/backend health and a real test action.

This is a system integration task, not just a PWA UI change. Implement the relevant XDG Desktop Portal, D-Bus/session integration, MIME associations, desktop entries, launcher/host plumbing, picker UI and file access contract.

## 1. Repository audit — facts to preserve and verify

The supplied repository has already been inspected. These findings should guide the work, but **re-check them against the current live checkout and physical phone** because historical reports may be stale.

### 1.1 There are three distinct Nuxel components

- **Nuxel Gallery** is the PWA at `pwa/nuxel-apps/photos/`. Its app ID is `org.nuxel.Photos`, display name `Gallery`, and app entry is `pwa/nuxel-apps/photos/app.json`. It uses the shared media store through `storage.media-list`, plus camera captures through `camera.list-captures` / `camera.open`. It browses real user media directories such as `~/Gallery`, `~/Pictures`, `~/Videos`, and `~/DCIM`, plus real camera captures. It is a media gallery, not the general file manager.
- **Nuxel Files** is the PWA at `pwa/nuxel-apps/files/`. Its app ID is `org.nuxel.Files`, display name `Files`, and app entry is `pwa/nuxel-apps/files/app.json`. It browses the PWA-visible storage tree through bridge operations such as `storage.list-dir`, read/write and file operations. It currently has normal browse/manage selection behaviour, but no complete externally initiated file-chooser return contract has been demonstrated.
- **Nuxel Camera** is separate (`org.nuxel.Camera` / `pwa/nuxel-apps/camera-gallery/`). Do not mistake the camera application for Gallery. Gallery is `org.nuxel.Photos` under `pwa/nuxel-apps/photos/`.

### 1.2 The existing Nuxel portal is not the XDG FileChooser portal

- `services/nuxel-portal/src/portal.py` exports the private D-Bus service `org.nuxel.Portal` and mediates Nuxel hardware/privacy permissions through the Nuxel/PhoshAgent flow.
- Its methods include Nuxel-specific requests for camera, microphone, contacts, location, USB, Bluetooth, clipboard, etc. It does **not** implement `org.freedesktop.portal.FileChooser`, nor the XDG portal `OpenFile`, `SaveFile` or `SaveFiles` contract.
- Do not rename this service, overload it with a second incompatible D-Bus API, or treat it as a drop-in implementation of `org.freedesktop.portal.Desktop`.
- Keep hardware permission decisions and filesystem selection as separate responsibilities. They may share authenticated host infrastructure, but must have separate API contracts and policy.

### 1.3 Existing portal configuration is not proof that a portal exists

- `configs/nuxel/portals.conf` contains a `[preferred]` section and maps `org.freedesktop.impl.portal.FileChooser=gtk`.
- The repository document `docs/a53/FLATPAK-SANDBOX-PORTALS.md` reports that `xdg-desktop-portal` and `xdg-desktop-portal-gtk` were absent in the audited image, and that no FileChooser/OpenURI portal was available at that time.
- `images/s10plus/packages-manifest.json` does not list `xdg-desktop-portal` or `xdg-desktop-portal-gtk` in the supplied snapshot.
- This makes a configuration-only fix inadequate: a `portals.conf` entry cannot provide the portal frontend or backend if the packages/services are not installed and correctly activated.
- Verify the actual S10+ package state, session-bus name ownership, portal service activation, backend descriptors and selected backend. Report actual live state; do not assume the historical report is still current.

### 1.4 Existing storage/bridge surface

- `services/nuxel-bridge/src/api.py` contains the HTTP/bridge API, storage/media routes and mappings for storage and camera operations.
- `services/nuxel-bridge/src/pwa_store.py` and the media-store implementations provide file-backed data access.
- `pwa/nuxel-apps/photos/js/photos.js` obtains user media via `storage.media-list` and camera captures via `camera.list-captures`; it currently constructs local media endpoints for content/thumbnail viewing.
- `pwa/nuxel-apps/files/js/files.js` calls the bridge for actual directory listings and file operations. Its existing selection mode is for file-manager operations, not automatically a portal selection session.
- `pwa/nuxel-apps/settings/index.html` has a tab navigation and panels, with Apps and Permissions tabs near the end. `settings.js` handles tab navigation and talks to `NuxelHost`; `apps-permissions-settings.js` contains the Apps/Permissions UI. Follow the existing settings architecture rather than creating another settings application.

### 1.5 Existing config

- `configs/nuxel/portals.conf` is intended to select portal backends, but inspect where/how it is deployed and whether it is at a standard path recognized by the installed XDG portal version.
- The standard `portals.conf` search paths are under `xdg-desktop-portal/` in XDG config/data locations. Make sure the final generated config is in a path and desktop-specific filename the running session actually reads.
- Do not assume any `.desktop` entry currently exists for `org.nuxel.Photos` or `org.nuxel.Files`. Inspect all launcher-generated desktop entries, installed app registry IDs, and package output. If XDG MIME activation needs `.desktop` files, add correct launchers through the current registry/launcher architecture.

## 2. Critical conceptual distinction: picker vs file handler

Do not conflate these mechanisms:

### 2.1 File chooser / attachment picker

This is what an application asks for when the user presses Attach, Upload, Open, Browse or Select file. The requesting application is asking the system to let the user choose a file and return it to that same application.

The correct system-wide Linux integration is normally the **XDG Desktop Portal FileChooser** contract (`org.freedesktop.portal.FileChooser` via the portal frontend and an `org.freedesktop.impl.portal.FileChooser` backend). This must return selected file URIs and preserve the calling app's request semantics. It is not controlled by `mimeapps.list`.

### 2.2 File handler / MIME “Open with” association

This decides which application opens an existing file when a user activates that file in a file manager, launcher, browser download list or `xdg-open`-like pathway. Defaults/associations are represented by the freedesktop MIME applications specification (`mimeapps.list`) and valid `.desktop` entries.

This does not implement an attachment dialog. A correct MIME association cannot fix a broken FileChooser portal by itself.

### 2.3 Required result

Implement both:

- **Picker routing:** Gallery and Files are selectable sources in the system file chooser, used by Ferdium/Signal/other portal clients.
- **Open-with routing:** Gallery is available/default for supported image/video MIME classes; Files is available for directories and as an explicit browse/manage app. Do not make Files the default opener for every image or document simply because it can browse directories.

## 3. Hard requirements

1. A working selection flow must be available from Ferdium, its WhatsApp service if applicable, Signal and normal GTK/portal-aware apps.
2. The chooser must be system-level and reusable by any compatible client, not a hardcoded special case for WhatsApp.
3. It must offer Gallery and Files as distinct sources. Respect app-provided title, filters, multiple-selection flag, directory flag and accept label where applicable.
4. Selected files must be returned to the original app using a valid portal response and accessible URI/document grant. Do not merely open the selected item in another window.
5. Cancellation must return the correct cancelled response, not an empty-success response or timeout.
6. File selection must work with filenames containing spaces, Unicode, parentheses, emoji and non-ASCII paths.
7. Support multi-select when requested. Never force multiple selection when the caller requested a single file.
8. Gallery mode must show actual media only. It must not fabricate items or silently substitute a sample image.
9. Files mode must expose only the approved user-visible storage roots and file access policy. Do not grant host filesystem access globally.
10. Settings controls must persist real state through the correct backend/configuration store, not just localStorage labels.
11. Per-app overrides must use the actual installed app IDs/package identities discovered from the registry and desktop files.
12. Keep the existing Nuxel permissions broker intact. Picker selection does not imply blanket `storage` permission for the app.
13. No `--filesystem=host`, `--device=all`, `--no-sandbox`, host-wide D-Bus access, or permission bypasses.
14. No fake success. Unsupported app integrations must be marked unsupported with exact evidence and a safe fallback.
15. The final report must state which apps were tested with actual physical attachment selection and which were only tested by protocol harness.

## 4. Target architecture

Implement a proper **Nuxel File Picker** with the XDG portal contract as the system-wide front door.

Preferred architecture:

```text
Ferdium / Signal / other GTK/Electron/Flatpak clients
              │
              ▼
 org.freedesktop.portal.FileChooser
              │  (xdg-desktop-portal frontend)
              ▼
 org.freedesktop.impl.portal.FileChooser
              │  (Nuxel FileChooser backend)
              ▼
 Nuxel Picker UI / session host
       ┌──────┴───────┐
       ▼              ▼
  Gallery source   Files source
 org.nuxel.Photos org.nuxel.Files
       │              │
       └──────┬───────┘
              ▼
 Selection result + authorized document access
              │
              ▼
 Requesting application receives valid file URI/access
```

The implementation may use a separate Nuxel FileChooser backend service and a Nuxel-hosted UI, or a native GTK4 surface integrated with the shell, provided it is reliable, conforms to the API, works on the phone's screen and can select from the actual Gallery/Files data sources. Choose the least complex architecture compatible with the existing Nuxel host and XDG portal stack.

The backend must be a real XDG portal backend selected through a `.portal` descriptor and `portals.conf`, not a service that merely happens to have “portal” in its name.

If the currently deployed `xdg-desktop-portal` frontend is missing, add it through the repository's package/build/install mechanism and provide its user-session DBus/systemd activation. Select the Nuxel backend for FileChooser while retaining GTK as an explicit fallback for other portal interfaces where it is already intended. Do not claim capability until `org.freedesktop.portal.Desktop` owns the expected session-bus name and a real client call succeeds.

### 4.1 Backend interface

Implement the version supported by the installed XDG portal frontend and conform to the official backend interface. At minimum evaluate and implement:

- `OpenFile(handle, app_id, parent_window, title, options)`
- `SaveFile(handle, app_id, parent_window, title, options)`
- `SaveFiles(handle, app_id, parent_window, title, options)`

For `OpenFile`, correctly support and/or safely handle:

- `multiple` boolean;
- `directory` boolean;
- `filters` and `current_filter`;
- `current_folder`;
- `accept_label`;
- `modal`;
- `choices` where supplied;
- calling app ID and parent-window metadata.

Return a portal response with the correct success/cancel/error semantics and results containing `uris` using valid `file://` URIs. Preserve supported choices/current filter results. Normalize URIs correctly; discard invalid paths rather than returning malformed URIs.

For `SaveFile` and `SaveFiles`, implement the actual save contract rather than routing these calls through an open-only picker. Honor suggested name, current folder, filters, overwrite/collision rules and safe creation semantics. If a method cannot be safely implemented in the first iteration, explicitly return an honest unsupported/error response only where the standard permits it; do not hang or fake completion. Aim to support all three for mainstream Linux application compatibility.

Use the versioned API documentation and installed D-Bus introspection XML for exact signatures, variant typing, request object lifecycle, response codes and signals. Do not copy signatures from memory if they differ from the installed frontend version.

### 4.2 Portal activation and configuration

- Inspect `/usr/share/xdg-desktop-portal/portals/`, D-Bus activation directories and user services.
- Add the Nuxel backend descriptor with the correct DBus service name, interfaces and implementation metadata.
- Add a Nuxel desktop-specific portal config using the desktop identity actually exported by the session (`XDG_CURRENT_DESKTOP`).
- Ensure `org.freedesktop.impl.portal.FileChooser=nuxel` (or the exact installed backend ID) is resolved by the actual frontend. Keep `gtk` as a documented fallback only where intended.
- Preserve existing non-FileChooser mappings (Settings, Notification, Inhibit, Print, Access, Account, Email, DynamicLauncher) unless live evidence proves a correction is needed. Do not accidentally advertise Screenshot/ScreenCast if their backends remain unavailable.
- Add DBus service activation or a user systemd service with correct session-bus user/permissions. The UI must run in the logged-in Nuxel graphical session, not as an unrelated root process.
- Do not merge this implementation into `services/nuxel-portal/src/portal.py`; that daemon remains the private hardware-permission broker.

### 4.3 Documents portal / access handoff

A file URI alone does not guarantee a sandboxed application can access the underlying host file.

- Use the XDG portal frontend's supported Documents portal integration (or another standards-compliant grant mechanism) to make selected files accessible to the requesting sandboxed app.
- Verify the selected document is actually visible/readable to the calling Flatpak sandbox after selection.
- Do not expose `/home`, `/`, or the entire media directory to every app.
- Apply grants only to the selected files/folders and only for the requested operation/rights.
- Respect read vs write semantics. An `OpenFile` request is normally read access; `SaveFile` needs correct write access.
- Do not persist grants longer than the portal's intended policy without clear user-visible policy and a correct revocation path.
- Test how the current image's XDG document portal/FUSE service is installed, configured and started. Add the required supported components if missing; if no document portal is used for native non-sandbox apps, still preserve per-client sandbox access.

## 5. Nuxel Picker UI: Gallery and Files sources

The visual chooser must feel like a Nuxel phone surface, not an empty desktop file-manager window.

### 5.1 Initial source selection

Default UI when user preference is Ask every time:

- Title follows the application request, e.g. “Attach file”, “Open image” or “Select a file”.
- A prominent source switcher with **Gallery** and **Files**.
- Gallery is the natural first view for `image/*` or `video/*` filters when Gallery is available; Files remains one tap away.
- Files is the natural first view for generic files, folders or non-media filters.
- The backend may use request filters to choose the initial tab, but it must never restrict the user's ability to switch to the other source unless the caller's contract specifically requires a directory-only selection.

### 5.2 Gallery source

Use the existing Gallery app and store, not a second unrelated index.

- Integrate with `pwa/nuxel-apps/photos/js/photos.js` and its current shared sources (`storage.media-list`, `camera.list-captures`).
- Add a clean selection mode distinct from the normal Gallery viewer mode.
- Support single and multiple selections according to the portal request.
- Respect MIME filters: image requests show supported still images; video requests show supported video; `image/*` should not unexpectedly include arbitrary documents.
- Reuse existing thumbnail/preview generation and caches. Do not load full-resolution originals just to render the grid.
- Show album/folder/date/search controls only where useful on the phone; keep the picker fast and touch-friendly.
- Preserve actual source paths/IDs; do not invent paths from media labels.
- Camera-store captures must be translated to a real accessible file/document URI or copied safely to a stable managed file when the source is not directly addressable. Never return a fake `file://` URI for an in-memory/base64-only capture.
- Selection mode must not expose normal delete actions. Choosing an attachment cannot delete or modify the source.
- On Confirm, return the exact selected media records to the portal backend. On Cancel/Back, close the picker and return cancelled.

### 5.3 Files source

Reuse the Files app's real storage browser and bridge APIs.

- Integrate with `pwa/nuxel-apps/files/js/files.js` and the storage provider; do not create a second inconsistent root listing.
- Add an externally initiated picker mode with read-only open selection and separate save/directory modes.
- Respect requested filters, multi-select and directory selection.
- Provide breadcrumbs, folder navigation, filename search, file type/size metadata and touch-sized actions.
- Selecting a folder in normal OpenFile mode must not occur unless `directory=true`.
- In save mode, allow filename entry and collision handling; do not overwrite silently.
- Do not reuse file manager's destructive selection actions in picker mode.
- Restrict roots to the existing Nuxel user-visible storage policy. Symlink resolution must remain inside allowed roots unless an explicit supported policy authorizes otherwise.

### 5.4 Reuse without app-window hacks

The XDG backend must not simply launch `org.nuxel.Photos` or `org.nuxel.Files` as a normal top-level app and hope the requesting app receives the selection. Implement an explicit picker-session contract that binds:

- portal request handle/token;
- requesting application ID;
- title/parent metadata;
- filters and selection constraints;
- selected media/file identity;
- cancellation and timeout;
- final URI/document grant result.

Use Nuxel host APIs/overlay infrastructure to display the chooser. Do not create an unrelated window or lose the original request when the user navigates.

## 6. Settings → File Handlers

Add a new Settings section and tab in the existing Settings application.

### 6.1 UI placement and integration

- Add a tab/button labelled **File Handlers** near Apps and Permissions in `pwa/nuxel-apps/settings/index.html`.
- Add a matching section such as `id="tab-file-handlers"` with semantic headings, loading/error states and save/reset controls.
- Extend the existing tab mechanism in `settings.js` without breaking other tabs.
- Prefer a dedicated `file-handlers-settings.js` module loaded from `settings/index.html`, matching the existing feature-module pattern (`apps-permissions-settings.js`, `appearance-settings.js`, etc.).
- Use `NuxelHost`/existing host RPC patterns. Do not write config files directly from browser JavaScript, shell out from the UI or store authoritative settings in localStorage.
- The panel must work in the current PWA iframe and use the same styling/responsive conventions.

### 6.2 Global picker preference

Provide:

- `Ask every time` (recommended default);
- `Prefer Gallery for images and videos`;
- `Prefer Files for all file selections`.

If a specific application has an override, that override wins over global preference. If the requested MIME filter is image/video and Gallery is preferred, open Gallery first but keep Files available. Generic documents must open Files first.

### 6.3 Per-application picker handlers

- Enumerate installed applications from the authoritative Nuxel app registry and installed desktop/package inventory.
- Show app name, app ID, type/package format (PWA, RPM/native, Flatpak/Electron when known) and current picker policy.
- Include Ferdium, Signal, and any separately installed WhatsApp app/wrapper when they actually exist. WhatsApp may be a Ferdium service, not a distinct desktop app; do not fabricate a second app identity.
- Options: Inherit global / Ask every time / Prefer Gallery / Prefer Files.
- Store overrides by stable app ID, not display name.
- Unknown/calling app IDs should inherit global policy and still get a working generic picker.
- Provide a “Reset to system defaults” action.

### 6.4 MIME Open-with defaults

Add a separate settings group for default handlers with categories such as:

- Images (`image/*`) → Gallery (`org.nuxel.Photos`) by default where its launcher/desktop entry is valid.
- Videos (`video/*`) → Gallery if Gallery supports the selected format; allow a different installed player (e.g. VLC/Media Player) where appropriate.
- Directories (`inode/directory`) → Files (`org.nuxel.Files`).
- Other MIME types → show valid installed candidates; do not assign Gallery/Files when they do not declare/implement the capability.

For each MIME type/category:
- show the actual current default and available installed apps;
- set a default only when the selected desktop entry is installed and declares that MIME type (or the system intentionally adds an association);
- offer reset/restore defaults;
- show unsupported/no handler honestly.

Do not make `org.nuxel.Files` the default opener for every file MIME. It is the file manager and picker source; it should naturally handle `inode/directory` and may expose “Browse in Files” as a separate action.

### 6.5 Persisted schema

Use a versioned Nuxel-owned settings document, for example:

```json
{
  "schema_version": 1,
  "global_picker_policy": "ask",
  "app_picker_overrides": {
    "org.signal.Signal": "inherit",
    "com.getferdi.Ferdium": "inherit"
  },
  "mime_defaults": {
    "image/png": "org.nuxel.Photos.desktop",
    "image/jpeg": "org.nuxel.Photos.desktop",
    "image/webp": "org.nuxel.Photos.desktop",
    "video/mp4": "org.nuxel.Photos.desktop",
    "inode/directory": "org.nuxel.Files.desktop"
  }
}
```

This is an example schema, not an instruction to hardcode guessed installed IDs. Confirm actual IDs and `.desktop` filenames. Use an appropriate per-user config path (`$XDG_CONFIG_HOME/nuxel/…` or the repository's established config management). Provide migration/default generation, validation and atomic writes. Keep `mimeapps.list` in sync with the user's configured MIME defaults using the freedesktop specification; do not let the JSON settings become a conflicting second source of truth.

### 6.6 Portal health panel

Display truthful information:
- XDG portal frontend available/running;
- active FileChooser backend ID;
- backend D-Bus name owned/reachable;
- current desktop identity and portal config file loaded;
- Documents portal availability when needed;
- last successful chooser test and error details.

Add **Test File Picker** which opens the actual Nuxel chooser. Require selection of a harmless sample/test file and verify it returns to the requesting test client. Do not fake success based on service status alone.

## 7. MIME associations and desktop entries

### 7.1 Desktop integration

Ensure Gallery and Files are launchable through standard desktop activation if they are to appear in MIME handler lists.

- Add valid desktop entries for Gallery and Files if missing, or integrate with the repository's generator so it produces the exact stable desktop IDs.
- `Exec=` must call a safe Nuxel launcher/host verb with properly quoted/escaped arguments. Avoid shell concatenation or `eval`.
- Declare correct `MimeType=` associations and desktop `Categories`/`Icon` fields.
- Gallery should advertise only supported image/video MIME types confirmed by its actual implementation.
- Files should advertise directory handling (`inode/directory`) and any explicitly supported file-management/open action.
- Use `TryExec=` where appropriate and validate launchability at install time.
- Ensure generated desktop entries are installed in an XDG application directory and run `update-desktop-database` where required.

### 7.2 `mimeapps.list`

- Read and write according to the freedesktop MIME applications specification.
- Respect the user's XDG lookup precedence; use the recommended per-user `$XDG_CONFIG_HOME/mimeapps.list` location for UI-managed defaults.
- Preserve unrelated groups, MIME mappings and comments as safely as the chosen parser permits.
- Do not blindly replace the entire file.
- Use `Default Applications`, `Added Associations` and `Removed Associations` correctly.
- Verify the chosen app is associated with the MIME type; add the association if required.
- Never update system-wide defaults when the user asked for a per-user preference.
- Do not use guessed `.desktop` filenames; query the installed desktop database.

## 8. App integration: Ferdium, WhatsApp and Signal

### 8.1 Inventory first

Determine on the phone and build image:
- Is Ferdium a Flatpak, RPM, AppImage or custom wrapper?
- Is WhatsApp used as a Ferdium service, separate web app, or separate desktop app?
- Is Signal a Flatpak, RPM or other package?
- Which Electron/GTK versions and file-dialog APIs are in use?
- What exact D-Bus method or toolkit call is triggered by the attachment button?
- Does each app use XDG FileChooser, GTK native chooser, Electron native dialog or a direct launcher invocation?

Capture package IDs, desktop IDs, executable/wrapper paths, environment and logs. Do not assume all three apps use the same dialog mechanism.

### 8.2 Prefer standard portal integration

- For apps that support the XDG portal FileChooser, make sure their session environment and toolkit choose the portal path.
- Test the actual versions installed in Nuxel. Some Electron versions/apps may need portal preference/feature configuration; use only supported documented settings for the installed version.
- Do not set an unverified global environment variable that breaks all GTK dialogs.
- If an app bypasses the portal, use a narrowly scoped, documented app wrapper/configuration adjustment to make it use the portal where supported.
- If a given app cannot use XDG portals, implement an app-specific compatibility adapter only after the actual call path is proven. Keep it isolated and documented.
- No app-specific patch may bypass sandboxing or expose the host filesystem to the entire app.

### 8.3 Required end-to-end cases

For each installed app (Ferdium, WhatsApp through Ferdium if applicable, Signal):
1. Open a conversation/chat without sending a message.
2. Tap attachment/photo/file.
3. Verify the Nuxel picker is shown, not an empty external Linux file manager.
4. Select a real JPG/PNG/WebP image from Gallery.
5. Confirm the requesting app receives it and displays its attachment preview.
6. Cancel once and verify the dialog closes cleanly and the chat remains usable.
7. Repeat using Files to choose a non-media file and an image.
8. Test multiple images when the app/request allows multiple selection.
9. Verify no upload/send occurs automatically. Stop at attachment preview unless explicitly conducting a controlled local test.
10. Confirm selected paths are not readable by unrelated apps after the request; grants follow the portal/document policy.

## 9. Security and correctness

- Validate every path against allowed roots using canonical path resolution and safe file descriptor operations.
- Defend against `..`, absolute-path escape, symlink escape, mount changes, TOCTOU races and path names crafted to confuse parsers.
- Do not trust file extensions as MIME truth. Use shared-mime-info/content sniffing where appropriate, but respect portal filters as user guidance rather than a security boundary.
- Do not follow symlinks outside allowed roots.
- For SaveFile, use safe create/replace semantics, never overwrite silently, and verify the resulting file remains inside an allowed destination.
- Keep URI encoding/decoding correct for Unicode and special characters. Use standard URI libraries, not string concatenation.
- Bound number of selected files, maximum displayed metadata, thumbnail sizes, open requests and active picker sessions.
- Handle requesting-app disconnect, user cancellation, picker process restart and session shutdown without leaking requests or grants.
- Authenticate app identity from D-Bus/portal context, not a UI-provided string.
- Avoid logging full sensitive filenames/paths unnecessarily; redact or minimize logs.
- Do not widen filesystem permissions for Ferdium/Signal globally.
- File selection is user-authorized per operation; it is not an automatic grant of permanent `storage` permission through Nuxel Permission Manager.

## 10. Implementation sequence

### Phase A — Baseline and root-cause proof

1. Inspect live repository and current phone package/service state.
2. Record current XDG environment (`XDG_CURRENT_DESKTOP`, `XDG_DATA_DIRS`, `XDG_CONFIG_HOME`, DBus session address), portal D-Bus owners and installed `.portal` descriptors.
3. Trace actual file dialog request from each target application.
4. Prove whether `org.freedesktop.portal.Desktop` exists and which backend is selected.
5. Confirm Gallery/Files app registry metadata, storage routes and installed launcher entries.
6. Save logs/evidence under `docs/pwnage-97000/evidence/<timestamp>/`.

### Phase B — Portal frontend/backend availability

1. Add the XDG portal frontend and required backend packages through image/package manifests if absent.
2. Implement Nuxel FileChooser backend and descriptor/service activation.
3. Wire the correct `portals.conf` file for Nuxel's desktop identity.
4. Keep `org.nuxel.Portal` unchanged.
5. Add DBus introspection and protocol conformance tests.
6. Validate portal `OpenFile`/`SaveFile`/`SaveFiles` from a tiny test client before connecting PWA UI.

### Phase C — Nuxel picker UI and selection return

1. Implement a picker-session API connecting the D-Bus backend to the Nuxel UI/host.
2. Add Gallery selection mode based on `org.nuxel.Photos` sources.
3. Add Files selection mode based on `org.nuxel.Files` storage provider.
4. Return selected file identity/URI and produce correct portal result/document grant.
5. Implement cancellation, multi-select, filters, directory and save modes.
6. Keep normal Gallery/Files use unchanged.

### Phase D — Settings File Handlers

1. Add File Handlers tab/panel to current Settings.
2. Add global and per-app picker-source policies.
3. Add MIME open-with defaults and correct Gallery/Files associations.
4. Add portal health and real test controls.
5. Persist through host/service/config backend and atomically update `mimeapps.list`.
6. Add reset/migration/invalid-app handling.

### Phase E — app integration and deployment

1. Verify/adjust Ferdium/Signal and WhatsApp wrapper portal usage.
2. Add only narrowly scoped compatibility wrappers where needed.
3. Update package manifests, image build, release manifests, portal config, DBus activation, user services, desktop entries and AppArmor/SELinux policy.
4. Deploy through existing `./scripts`/device deployment workflow after inspecting the correct scripts.
5. Restart only the necessary user-session services or log out/in if service ownership/config loading requires it; avoid an unnecessary reboot.

## 11. Testing requirements

Create a new focused suite, e.g. `tests/pwnage97000/`, plus backend unit tests.

### 11.1 Unit tests

- MIME defaults parsing/writing preserves unrelated associations.
- Desktop ID validation refuses missing or non-associated handlers.
- Per-app policy resolves override > global > default.
- App registry identities are stable; duplicate display names do not collide.
- URI encoding/decoding works with spaces, Unicode, emoji, parentheses, `#`, `%` and `?`.
- Path canonicalization blocks traversal and symlink escapes.
- Multiple/single selection and filter matching.
- Request lifecycle covers success, cancel, error, timeout, requester disconnect and picker restart.
- SaveFile collision/overwrite logic and safe creation.
- Camera-store items without a stable real file do not return fabricated URIs.

### 11.2 Portal protocol tests

- Start a private D-Bus test session (`dbus-run-session` or project's equivalent).
- Register the portal frontend and Nuxel backend with test config.
- Invoke frontend FileChooser.OpenFile as a real test client.
- Assert request/response handle lifecycle and response code.
- Assert `uris` are correctly typed and accessible through the intended document grant mechanism.
- Test OpenFile multiple, filters/current_filter, directory mode, current_folder and cancellation.
- Test SaveFile and SaveFiles if implemented.
- Verify the frontend selected the Nuxel backend from its loaded `portals.conf`, not a direct backend-only test that bypasses frontend dispatch.

### 11.3 Integration tests

- GTK application with portal preference enabled.
- Electron/Ferdium installed version with portal path if supported.
- Signal installed version and actual attachment control.
- Native non-sandboxed app as a control case.
- Flatpak/sandbox client if Flatpak is actually installed and runnable on this kernel. The repository previously documented `CONFIG_USER_NS`/Flatpak blockers; re-check live state and do not claim Flatpak integration if sandbox cannot run.
- Gallery JPG/PNG/WebP and supported video.
- Files PDF/ZIP/TXT/unknown file and directories where requested.
- Unicode/spaces/large file/read-only permissions.

### 11.4 Physical acceptance criteria

- No empty Linux file manager launches from the tested attachment buttons.
- Gallery displays real existing images/videos and allows selection.
- Files can browse real directories and select arbitrary allowed files.
- The original requesting app receives the selected file and renders an attachment preview.
- Multi-select obeys the caller's option.
- Cancel returns to the caller without hanging/crashing.
- No send/upload occurs without the user's separate send action.
- No cross-app filesystem access appears after picker close.
- Settings changes survive app restart/session restart and match effective portal/MIME behavior.
- Existing camera, Gallery, Files, app launcher, Permission Manager and other portal functions remain operational.

## 12. Deployment, recovery and release

- Inspect `./scripts` and current release/image pipeline; do not invent a deployment path.
- Add every new file/package/service/desktop entry to the relevant package/image/release manifests.
- Make deployment idempotent and verify installed hashes.
- Capture pre-deploy copies and hashes of portal config, DBus service files, user services, desktop entries and app data.
- If portal frontend/backend activation fails, revert to the last working GTK backend or direct toolkit chooser. Do not break native app file dialogs as a side effect.
- Do not disable the existing `org.nuxel.Portal` permission service.
- Do not leave both a broken Nuxel backend and GTK backend competing for FileChooser. Explicitly record backend selection.
- A rollback must restore prior portal config and stop/disable only the new backend, while leaving unrelated portal interfaces untouched.
- No kernel or bootloader changes are expected for this mission.

## 13. Required final report

Write `PWNAGE-97000-REPORT.md` and evidence in `docs/pwnage-97000/evidence/<timestamp>/` containing:

1. Root cause established for each target app, with exact toolkit/portal path.
2. Before/after package and service inventory.
3. Actual portal frontend, backend D-Bus name, backend descriptor and loaded `portals.conf`.
4. File handler schema and effective MIME defaults.
5. Installed desktop IDs for Gallery and Files.
6. Per-app picker policy and actual calling app identity.
7. Test matrix with PASS/FAIL/BLOCKED and physical vs harness status.
8. Selected file URI/document access proof from the requesting client.
9. Security tests and rejected escape attempts.
10. Screenshots or UI evidence of the Nuxel Gallery/Files source picker and Settings section where possible.
11. Deployment files, hashes and rollback instructions.
12. Any true blockers with exact logs, not vague “portal issue” statements.

## 14. Definition of done

This mission is DONE only when:

- Settings has a working File Handlers section with global/per-app picker policy and MIME handler controls.
- The XDG FileChooser portal frontend is installed/active and dispatches to the Nuxel backend (or an explicitly documented, equally standards-compliant implementation).
- Nuxel backend correctly handles actual `OpenFile` requests and the supported save/directory/multi-select semantics.
- Gallery and Files work as selectable sources and return real accessible files to the original requesting application.
- Ferdium/WhatsApp and Signal attachment workflows are tested end-to-end on the phone, or each unsupported client is explicitly documented with proof and the general portal path still passes.
- MIME Open-with defaults are valid and persist.
- No broad sandbox/filesystem permissions were added.
- Existing Permission Manager, private `org.nuxel.Portal`, Gallery, Files and all unrelated apps continue working.
- Automated tests pass and the report contains reproducible evidence.

Do not mark this mission done because a dialog appears. The requesting application must actually receive and preview the selected file.

**Final principle:** One system-wide file-selection contract, two first-class Nuxel sources (Gallery and Files), configurable real file handlers, and no unsafe filesystem shortcuts.

## 15. Technical references

Use the current installed versions and verify their interface definitions against these authoritative specifications:

- XDG Desktop Portal FileChooser frontend: https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.FileChooser.html
- XDG Desktop Portal FileChooser backend: https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.impl.portal.FileChooser.html
- XDG `portals.conf` backend selection: https://flatpak.github.io/xdg-desktop-portal/docs/portals.conf.html
- Freedesktop MIME applications specification: https://specifications.freedesktop.org/mime-apps/latest-single/
- Freedesktop default application semantics: https://specifications.freedesktop.org/mime-apps/latest/default

The repo is the implementation source of truth for Nuxel-specific interfaces. Official standards are the source of truth for XDG portal and MIME contracts.

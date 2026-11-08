# Nuxel Permission Manager — Full Implementation Build Prompt

**Target repository:** the supplied `nuxel-main` repository (current tree from `nuxel-main (12).zip`).  
**Target device:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820, vendor Linux 4.14.253, unless the implementation is deliberately kept portable.  
**Primary outcome:** one trustworthy, persistent, per-app permission system, fully manageable from **Settings → Permissions**, used by every Nuxel app and every permission-sensitive service.

---

## Instructions to the implementation agent

You are working in the real Nuxel repository. **Implement this feature in the repository; do not merely write a design document, list suggestions, or create mock UI.** Start by auditing the current branch and the source files named below. Preserve existing working functionality, adapt to the repository's actual APIs, and prove the changes with tests. Do not assume this prompt perfectly describes the latest checkout: verify each path, current interface, service ownership, and app manifest before editing. Where the checkout differs, follow the architecture and security invariants in this prompt and document the difference.

Do not flash, re-partition, factory-reset, or reboot the phone as part of unattended development. Do not run destructive package, storage, database, or permission-reset commands against a connected handset. Build and test locally first; produce a clearly described, reversible deployment/migration step for the owner. Do not leave a test auto-grant, debug bypass, mock permission provider, development token, or permissive fallback enabled in production.

The feature is complete only when the **same permission state** is visible in Settings, consulted by the portal/bridge, enforced at each sensitive operation, persisted across reboot, and covered by automated tests. A switch that only changes a label, CSS class, localStorage value, or JSON file not read by the enforcement path is not an implementation.

## 1. Repository audit: existing building blocks and defects to address

The supplied tree already contains a useful but incomplete foundation. Reuse it; do not introduce a second permission database or an unrelated permission framework.

### Existing files and components to inspect and update

- `shell/nuxel-shell/nuxel-permissions/capabilities.json` — current canonical capability registry (schema v2, currently 27 registered IDs).
- `shell/nuxel-shell/nuxel-permissions/nuxel-permd.py` — policy store, discover/review/sync logic, grant/revoke logic and local HTTP API.
- `shell/nuxel-shell/nuxel-permissions/main.c` — standalone GTK permission viewer.
- `shell/nuxel-shell/nuxel-permissions/systemd/nuxel-permd.service` — daemon deployment.
- `shell/nuxel-shell/nuxel-permissions/tests/test-permissions.py` — current permission tests.
- `services/nuxel-portal/src/portal.py` and `services/nuxel-portal/test-portal-policy.py` — current D-Bus portal and tests.
- `services/nuxel-bridge/src/bridge.py`, `services/nuxel-bridge/src/capabilities.py`, and `services/nuxel-bridge/src/api.py` — current bridge permission checks and PWA RPC routing.
- `pwa/nuxel-apps/settings/index.html`, `settings.js`, `settings-model.js`, and `settings.css` — actual Settings app and tab system.
- `pwa/nuxel-common/app-registry.json` — current PWA/native launcher registry (registry version 14 in the supplied archive).
- `configs/nuxel/app-registry/app_registry.json` — older system registry; currently only six entries and materially out of sync with the launcher registry.
- `configs/nuxel/permissions/README.md`, `configs/nuxel/permissions/nuxel-settings.json`, `configs/nuxel/permissions/org.nuxel.Home.json`, and related permission seed/config files.
- `docs/security-model.md` and `docs/security-defaults.md` — documented security model and desired portal flow.
- `shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-permissions.json` and all relevant per-app sandbox profiles.
- `pwa/nuxel-home/js/immersive.js`, `apps.js`, `gestures.js`, `bridge.js`, and `host-bridge.js` — foreground app lifecycle, gestures and trusted host boundary.
- `pwa/nuxel-apps/recorder/manifest.json`, `index.html`, and `js/recorder.js` — microphone user and current local authorization path.
- `tools/s10plus/a45/nuxel-pwa-host.c` — native PWA host, including the present `media.mic-authorize` shortcut and fullscreen window behavior.
- `NUXEL-063-BLOCKER-REPAIR-PROMPTS/prompts/31-gestures-zoom-performance.md` and app-specific zoom implementations, especially Maps.
- All PWA manifests, native app launchers, app-install metadata and all sources that touch camera, microphone, storage, contacts, telephony, location, notifications, Bluetooth, NFC, USB, display capture, screen mirroring, fullscreen or background execution.

### Confirmed problems in the supplied repository

1. **There is no Permissions tab in the Settings PWA.** The current tabs include Screen, Bluetooth, Displays, Wi-Fi, Camera, Sensors, Location & Maps, Notifications, Security, Software and Developer. Security is primarily screen-lock UI, not an app-permission manager.
2. **The separate GTK `nuxel-permissions` app is not a complete manager.** It scans grant files rather than the installed-app registry, so apps with no grants are omitted. It can revoke but does not provide a complete grant/toggle interface. Its Revoke All path calls the wrong portal method/signature. Keep it compatible with the new policy service, but make Settings the main user-facing control surface.
3. **There are parallel permission paths.** The portal writes legacy grant JSON; bridge code has its own grant cache and writes files; permd has a richer state store and API. These paths can disagree or race. Consolidate all policy mutation and authoritative reads in permd.
4. **The bridge currently has a fail-open fallback.** In `bridge.py`, `request_permission()` can auto-grant a session permission if `nuxel-portal` is unavailable. Remove this behavior. Any unavailable broker, malformed state, unknown identity, missing grant, timeout, or error must deny access.
5. **The portal's documented interactive prompt is unavailable on this handset.** `configs/nuxel/permissions/README.md` records that the handset has no `systemd --user` / PhoshAgent. A permission request must not depend on a nonexistent PhoshAgent and must not silently auto-approve. Implement a real Nuxel-owned consent surface or return deny when that surface cannot be displayed.
6. **Caller-supplied app identity is not trustworthy.** Current portal/bridge D-Bus methods accept an `app_id` argument. An app must never be allowed to claim another app's ID. Resolve the caller identity from trusted process/host/launcher context and bind it to the request server-side.
7. **The old system app registry is stale.** `pwa/nuxel-common/app-registry.json` has the broader app set; `configs/nuxel/app-registry/app_registry.json` is an older six-entry registry with legacy `default_capabilities`. Establish one canonical installed-app identity/capability source and generate or validate secondary representations from it. Do not let two registries independently define grants.
8. **PWA IDs can drift.** Some manifests omit `nuxel.app_id`, causing directory-name fallback IDs such as `recorder`, while the launcher uses `org.nuxel.Recorder`. All PWA manifests must map to the exact canonical app ID.
9. **Recorder's microphone integration bypasses policy.** Its manifest currently declares storage but not microphone. Its host `media.mic-authorize` method can create a short-lived local microphone authorization without consulting the canonical manager. Remove the bypass. Recorder must declare/request `microphone` and use the central service before opening the device.
10. **Old global privacy settings are not a per-app manager.** Existing `privacy.camera`, `privacy.microphone`, `privacy.location` settings are read-through/global controls. Preserve useful global kill-switch semantics, but add real app-specific grants and make every control call the central policy service.
11. **Fullscreen and zoom are not permission-mediated today.** `immersive.js` applies shell immersive presentation globally and accepts app `nuxel:immersive` messages from the active iframe. Doom includes explicit Fullscreen API requests. Separate normal shell-managed app presentation from app-requested exclusive fullscreen and gate the latter. The Maps app has its own internal map zoom; do not confuse that with whole-app two-finger zoom.
12. **Target-kernel enforcement must remain honest.** The capability registry documents the S10+ Linux 4.14.253 limits: no Landlock, no BPF LSM, no modern cgroup-v2 socket matching, and AppArmor only if actually enabled. The portal is a userspace broker and only mediates an operation if the app/service really uses it. Do not claim a permission is kernel-enforced merely because a JSON grant exists.

## 2. Non-negotiable security and product rules

### 2.1 One permission authority

`nuxel-permd` is the **sole policy authority and sole writer** of permission grants, denials, defaults, leases, and permission audit records. It owns `/var/lib/nuxel/permissions` and any versioned subdirectories below it.

- The portal becomes a D-Bus front end to permd. It authenticates the requester, asks permd for the decision, and brokers only approved access. It must not maintain an independent grant store.
- The bridge becomes a trusted transport/API to permd. It must not keep an authoritative shadow grant dictionary, write grant JSON itself, or override decisions with `always_ok` sets.
- Settings calls the bridge/host API, which calls permd. Settings must never edit files under `/var/lib/nuxel/permissions`, write permission state to `localStorage`, or use `/etc/nuxel/privacy/privacy.json` as the grant database.
- The native GTK Permissions app, if retained, must use the same permd API and display the same state. Prefer to make it a secondary entry point or launch Settings → Permissions rather than maintain a second implementation.
- The capability registry is the source of truth for capability definitions and enforcement metadata. The canonical installed-app registry is the source of truth for installed app identity and declared capability needs. Permission grants remain a separate owner-controlled state.
- A capability declaration means “this app may need this capability”; it is **not** a grant.

### 2.2 Default decisions and explicitly authorized initial exceptions

Implement these exact initial decisions. These are policy defaults, not UI suggestions:

| Capability | Initial default | Rule |
|---|---:|---|
| `mirroring` | **ALLOW for every installed app** | This is the one global allow-by-default permission. The owner can turn it off per app. New apps inherit allow unless an explicit per-app deny is set. |
| `zoom` | **DENY for every app** | Off for all existing and newly installed apps. Only the owner can enable per app. |
| `casting` | **DENY for every app** | No app is pre-authorized. Owner can set a future grant, but the UI must distinguish a stored policy from an active, implemented casting backend. |
| `fullscreen` | **ALLOW only for currently implemented apps that genuinely request explicit fullscreen** | Audit real call paths. Seed an allowlist only for apps whose actual code/launcher requests exclusive fullscreen. All other apps deny. Do not infer from a PWA `display: fullscreen` manifest value or from the shell's generic GTK window being fullscreen. |
| `microphone` | **ALLOW for `org.nuxel.Recorder` only** | This is the explicit app-specific exception requested by the owner. Recorder must still use the central grant and can be revoked in Settings. Every other app starts denied. |
| Every other grant-required capability | **DENY** | No grants are inherited from old `default_capabilities`, old `always` records, manifest declarations, or app category. The owner must enable them. |
| Capabilities that are not sensitive and do not need a user grant | No permission prompt | Keep genuinely non-sensitive capabilities such as ordinary audio output and app-private sandbox storage as intrinsic baseline functionality. Do not mislabel these as granted privacy permissions. |
| Unsupported / not enforceable capabilities | **Unavailable, not a cosmetic toggle** | Display the measured limitation. Do not present a switch that claims to protect something the target cannot protect. |

**Important migration rule:** the Recorder microphone grant, mirroring defaults, and audited fullscreen compatibility allowlist are the only intentional initial grants. Old generic grants must not survive merely because they were present in old seed files or `default_capabilities`. If preserving an existing grant is considered essential for data safety or system operation, do not silently preserve it: classify it as a system-owner action or ask for explicit owner confirmation in the migration report. Do not break Home/Settings hardware controls; give those narrowly scoped system-owner operations a separate trusted role rather than granting broad user-app capabilities.

For `fullscreen`, inspect the actual source and native launcher path. The supplied tree contains explicit Fullscreen API use in the Nuxel Doom WebAssembly engine and describes native fullscreen behavior for Chocolate Doom and UZDoom. Verify whether each launcher actually enters fullscreen before seeding it. The generic `gtk_window_fullscreen()` calls used by the host/window wrapper are not, by themselves, proof that every PWA deserves the app-level fullscreen entitlement.

### 2.3 Fail closed, always

All of the following mean **DENY**:

- no grant exists;
- the app is unknown, uninstalled, unsupported, or cannot be identified;
- requested capability is unknown or unsupported;
- permd, portal, bridge, host or consent UI is offline;
- permission state is corrupt, malformed, stale, expired or inconsistent;
- the user denies or dismisses a consent prompt;
- a global privacy kill switch blocks the resource;
- device hardware or an enforcement mechanism is unavailable;
- the requester is asking on behalf of a different app;
- a process cannot be mapped to the registered app identity;
- a grant has expired or a one-time grant was already consumed.

Never auto-grant on exceptions, timeouts, offline mode, test-mode flags or an unrecognized app. Remove all production paths that set `NUXEL_PORTAL_AUTO_GRANT=1` or otherwise bypass the owner's decision. Tests may inject a fake policy explicitly, but production startup must reject or ignore test-only auto-grant configuration.

### 2.4 Permission state survives reboot

- A normal owner-enabled toggle is a persistent `always` allow and must survive reboot.
- An explicit persistent deny also survives reboot.
- The missing-record default is deny, except for the explicit mirroring allow default and the narrowly seeded fullscreen/Recorder bootstrap grants above.
- `once` grants are consumed atomically by the first successful protected operation and never survive reboot.
- `session` grants are kept in runtime state and cleared at boot/session teardown. Do not serialize a session grant as a permanent allow.
- Reboot must not turn a denial into an allow or silently reset an owner choice.
- Use atomic write/replace, restrictive ownership/modes, fsync where appropriate, locking/transactions, schema versioning and safe recovery. Do not write policy JSON concurrently from portal, bridge and permd.

### 2.5 Distinguish app-private storage from user files

Every app may retain a private, sandbox-owned data directory required for basic app operation. This is not blanket permission to read shared storage, photos, contacts, downloads or other apps' data. Use file chooser / scoped URI grants for selected files. Shared media and external storage reads/writes require their own capability and must be mediated.

### 2.6 Do not overstate device security

The current S10+ kernel is Linux 4.14.253. Preserve the target facts in `capabilities.json`. Use the strongest mechanisms actually available and mark partial enforcement honestly. A userspace policy check can protect operations that route through it; it cannot stop a malicious unprivileged process that has direct device-node access unless DAC/AppArmor/other measured controls also block it. It cannot constrain root. Do not claim that a permission UI has created a kernel boundary where no such boundary exists.

## 3. Capability catalogue: normal phone permissions plus Nuxel-specific controls

Extend the existing capability registry rather than creating a second enum in the UI. Keep stable IDs and aliases for all existing capabilities, map legacy portal tokens consistently, and add a documented schema migration. Capability definitions need at least: `id`, aliases, title, description, group, risk/severity, `grant_required`, supported status, enforcement mechanisms, enforcement strength/limitations, request behavior, and whether the UI can expose an active toggle on the target.

### 3.1 Existing capabilities to retain and rationalize

Keep and audit all current registry IDs, including:

`audio`, `background`, `bluetooth`, `calendar`, `call`, `camera`, `clipboard`, `clock_status`, `contacts`, `display`, `location`, `microphone`, `network`, `notifications`, `phone_status`, `sms`, `sms_send_raw` (reserved/unsupported), `storage`, `usb`, `input_devices`, `local_shell`, `system_inspect`, `downloads`, `media_library`, `catalog_read`, `app_install`, and `app_remove`.

Do not silently change the meaning of existing IDs. Add explicit aliases/migration mappings where old app declarations use tokens such as `camera:capture`, `audio:capture`, `storage:persistent`, `network:outbound`, `contacts:read`, `phone`, `sms:send`, `download:queue`, `media:library`, `shell:local-pty`, `catalog:install` and related variants. Invalid or ambiguous aliases must produce a migration diagnostic, not an automatic broad grant.

### 3.2 Add standard mobile capabilities where meaningful on Nuxel

Implement a coherent catalog (some items may be unavailable if the service/hardware is not yet present):

- **Camera:** camera capture/preview, with front/rear sensor details where supported.
- **Microphone:** audio capture/recording, distinct from speaker playback.
- **Location:** approximate/coarse and precise/fine semantics, plus background location as a separately reviewable capability if background tracking is implemented.
- **Contacts:** read and write as separately grantable scopes if the data API supports that split.
- **Calendar:** read and write separately if the provider supports the split.
- **Phone:** initiate/end calls and read call/phone status; do not conflate raw modem control with ordinary call actions.
- **SMS:** send and receive separately; never add hidden raw modem access.
- **Notifications:** post notifications and read/access notification content as separate capabilities if read access exists. Posting notifications should still default deny under the requested policy.
- **Network:** outbound Internet and listening/inbound service exposure should be separate where the implementation can distinguish them. A declaration for outbound network must not imply inbound listening.
- **Bluetooth / nearby devices:** scan, pair/connect and manage should be distinct scopes where possible. Keep Bluetooth hardware/system control separate from an ordinary app's nearby-device access.
- **NFC:** access NFC tags/reader/writer only when the NFC stack is available. No fake toggle if it is absent.
- **USB / external devices:** enumerate, read/write or claim a device only through the actual brokered operation and supported driver interface.
- **Photos and videos / media library:** selected-item access versus broad media-library access. Prefer scoped picker grants.
- **Files and storage:** scoped file access, shared folders and external storage; keep app-private storage intrinsic and isolated.
- **Downloads:** enqueue or retrieve downloads only via the download broker; do not let it imply arbitrary filesystem write.
- **Sensors / motion / physical activity:** accelerometer, gyroscope, proximity, light, orientation and activity/motion APIs only where available and consumed. Avoid inventing sensors that the device does not expose.
- **Background execution:** separately authorize ongoing background operation; do not treat app foreground execution as background permission.
- **Clipboard:** read and write separately. On the supplied target registry clipboard is currently marked not enforceable (`mechanisms: none`). Until a real enforceable broker is implemented and tested, mark it unavailable/unsupported and expose no misleading grant switch. Do not claim a permission toggle protects clipboard contents if apps can access the global clipboard directly.
- **Screen capture / screen recording:** protect capture of the local display through the actual capture service. Do not confuse this with mirror output policy.
- **Biometric authentication:** an app may request a platform biometric *verification result* through a trusted API; never expose raw fingerprint templates or raw sensor data to apps. Only add this when the fingerprint service supports it.
- **App installation/removal and system inspection:** privileged actions must go through owner-confirmed services/polkit-like authorization. A generic permission does not hand an app root.

Do not add permissions for IMEI/serial disclosure, SIM PIN/PUK, raw modem commands, arbitrary root, kernel modules, ptrace, unrestricted `/` filesystem access, or other dangerous operations merely to make a list look like Android. Explicitly mark unsupported capabilities as unavailable, and keep reserved tokens such as `sms_send_raw` unsupported.

### 3.3 Nuxel-specific capabilities — mandatory

Add these exact capability IDs to the canonical registry and backend enums:

#### `zoom`

Controls **whole-app UI zoom initiated by Nuxel's two-finger pinch/drag gesture**, not zoom inside an app's own content. Default DENY for every app, including all current apps. When enabled, the owner can use two fingers moving apart/together to scale that app's content. It must not silently zoom the Home launcher, lockscreen, status bar or system chrome. Do not interfere with Maps' own pinch-to-zoom, Browser page controls, game controls or normal two-finger app interactions when the permission is off. While enabled, use a clear gesture policy and avoid stealing touches from an app unless a deliberate two-finger gesture is recognized. Provide a reset-to-100% affordance and sane scale bounds. Persist the app's scale preference independently from the permission grant. Revoking `zoom` immediately returns the app to normal scale and prevents further host zoom gestures.

#### `fullscreen`

Allows an app to request **app-controlled exclusive fullscreen/immersive mode**, such as using the Fullscreen API or asking Nuxel to suppress system chrome beyond ordinary shell presentation. It is not permission to draw outside the app surface or cover critical system safety UI. Preserve Nuxel's normal shell-managed app viewport/chrome contract where appropriate; do not break the current full-glass shell UX merely to rename it. However, every app-originated fullscreen request, including `nuxel:immersive` messages and native helper requests, must be checked against this capability. Deny unauthorized calls and keep system navigation/lockscreen/recovery gestures available. Only seed the compatibility allowlist for currently implemented apps whose code path really requests explicit fullscreen. All other apps deny by default. Revocation exits app-requested fullscreen immediately.

#### `casting`

Controls whether an app may initiate or control the **future Nuxel casting feature** (sending selected app/media content to an external display/receiver). Default DENY for all. Create the policy, API and authorization hook now so the future casting broker must call it. Do not claim casting works if the casting transport is not implemented. The UI may let the owner store a future allow/deny decision, but it must label the grant accurately as “saved for future casting; casting service not available” until a real broker is registered and can enforce it. A stored future grant must not imply that the screen is currently being shared.

#### `mirroring`

Controls whether an app's visible content may appear on **screen mirroring / cloned external display output**. Default ALLOW for every installed app and for new apps. The owner can switch it off for a specific app. When mirroring is active and the foreground app has `mirroring` denied, the **external mirrored output** must be covered by a black privacy curtain / blank frame with an optional clear “This app is hidden on the external display” indicator. The phone's local display must remain visible and usable; do not black out the phone panel as a side effect. When the app becomes allowed again, external output may resume without requiring app restart. Enforce this at the actual display-mirror/compositor/capture output path, not merely in a PWA overlay. Do not confuse mirroring with the future app-initiated `casting` capability: mirroring is duplication of the current screen; casting is an app initiating a separate outbound content session.

## 4. Canonical app identity, registry and declarations

### 4.1 One installed-app inventory

Use `pwa/nuxel-common/app-registry.json` as the current launcher registry baseline, then reconcile it with actual installed packages, PWA manifests, native launchers, service units and package state. This archive's PWA registry is version 14 and contains substantially more apps than the old six-entry `configs/nuxel/app-registry/app_registry.json`.

Establish one authoritative app inventory/API that returns at least:

- canonical `app_id`;
- user-facing app name and icon;
- app type (PWA/native/system);
- installed/available/unsupported/template status;
- executable/launcher or PWA origin identity;
- declared capabilities (not grants);
- version/package source where available;
- whether it is a system-owner component;
- whether it may request permissions.

Generate or validate the legacy system registry from the canonical registry. Update `verify-app-registry.py` or add equivalent validation so registry drift fails tests. Templates, uninstalled packages and unsupported apps must not appear as normal installed app rows. Installed apps with zero declared capabilities **must** appear in Settings.

### 4.2 Canonical app IDs

- Every PWA manifest must contain `nuxel.app_id` and `nuxel.capabilities` and the pinned bridge version.
- `nuxel.app_id` must exactly match the canonical launcher registry ID (case-sensitive).
- Remove directory-name fallbacks when an authoritative app registry mapping exists. A manifest with an unknown or conflicting ID is rejected/quarantined and cannot receive permission grants.
- Add validation for duplicate IDs, duplicate origins, conflicting manifests, invalid capability IDs and undeclared app capabilities.
- The Registry is for app identity and requested capability declarations only. It must never silently grant permissions.

### 4.3 Baseline app declaration audit

Audit the entire current registry and every installed app's actual operations. At minimum, reconcile these supplied-tree cases:

| App / canonical identity | Declaration and implementation work |
|---|---|
| `nuxel-dialer` | Declare call actions/status and contacts read only if the corresponding operations are used. Keep them denied initially; owner enables them. Do not grant raw modem access. |
| `nuxel-messages` | Declare SMS send/receive and contacts read as needed. Denied initially. |
| `nuxel-contacts` | Declare contacts read/write according to actual screens/actions. Denied initially. |
| `nuxel-camera` and any camera-gallery PWA | Declare camera capture/preview against the correct canonical identity. Verify which one is actually installed/used and avoid duplicate identities. Denied initially. |
| `org.nuxel.Mail` | Declare notifications and network only for code paths that actually use them. App-private storage is intrinsic, not a shared-storage grant. |
| `org.nuxel.Calendar` | Declare calendar read/write only if it accesses a calendar provider; separate notification access. |
| `org.nuxel.Notes`, `org.nuxel.Files` | No blanket shared-storage access. App-private files work; selected-file picker grants are scoped. |
| `nuxel-settings` | Uses a privileged owner/system role for settings operations, not blanket user-app grants. Keep the Settings app's permission-manager admin API owner-authenticated. |
| `org.nuxel.Terminal` | Declare `local_shell`; keep it denied until the owner enables it. It must not be granted just because the app exists. |
| Live Console / USB SSH / Wi-Fi SSH apps | Declare only the concrete USB/network capabilities their current flows use. Do not add broad `system_inspect` or shell grants by assumption. |
| XRDP / VNC / scrcpy remote apps | Audit their real remote-display/network/device operations. Do not automatically equate remote desktop with local screen mirroring or future casting. |
| `org.nuxel.Browser` / Firefox | Outbound network is a requested capability; shared-file access should be picker-scoped. Do not allow inbound listening unless needed and separately granted. |
| Calculator | No sensitive capability required unless real code proves otherwise. |
| Clock | Notifications/alarms only where used; ordinary local time reading is not a sensitive permission. |
| Photos / Gallery | Selected photos/files should use scoped picker; broad media-library access is separate and denied initially. |
| Weather | Network access only if it fetches remote data; denied until enabled. |
| Maps | Location and network declarations match actual locate/tiles features; denied initially. Do not auto-grant location from old seed files. |
| NuxTore | Declare catalog read/install/remove only for operations actually exposed and route install/remove through owner confirmation. |
| `org.nuxel.Recorder` | **Add `microphone`** and the storage need it truly has. Seed its persistent microphone allow as the explicit owner instruction; the runtime must still check it centrally before capture. Remove `media.mic-authorize` local bypass. |
| SnekByte / Doom variants | Add only real input/display/network requirements. Explicit fullscreen allowlist only after verifying live fullscreen call paths. |
| Media Player | Audio output is intrinsic/non-sensitive. Declare media-library access only when broad library scanning occurs; use picker for selected files. |
| Downloader | Declare download broker and network only if actual downloader needs it. |
| Authenticator / Vault | Use protected secrets/credential service. Never expose the secret store through generic filesystem permissions. Require explicit owner/device authentication where supported. |
| Safe Cleanup | Declare scoped cleanup operations. Do not give broad filesystem write or root access. |
| DevMgmt / PenguInterface / System Monitor | Read-only `system_inspect` only for the exact diagnostic data they need; deny initially. No arbitrary command/root execution. |
| GNOME Software | App install/remove must use the package service's own owner authorization. Do not assume a registry declaration itself grants installation. |
| Clipper | Existing clipboard capability is marked unenforceable on this target. Show unavailable until a real clipboard broker/access boundary is implemented and verified; no cosmetic toggles. |
| Signal / Stremio marked unsupported | Do not show as installed/grantable unless the package is actually installed and supported. |

This matrix is a starting audit guide, not a license to grant every declared capability. Validate each declaration against code and package installation. **Only the explicit Recorder microphone grant, mirroring defaults and verified fullscreen allowlist are initially granted.**

## 5. Identity authentication and service architecture

### 5.1 Trusted requester identity

Permission calls must use a server-verified app identity. Never trust an `app_id` string supplied by arbitrary app JavaScript or a D-Bus method argument.

Implement the strongest identity binding the target architecture supports:

- For native D-Bus callers, obtain the unique bus sender from the D-Bus invocation context and resolve UID/PID using the bus daemon's credential APIs (`GetConnectionUnixUser`, `GetConnectionUnixProcessID` or equivalent). Map the PID to its service/cgroup/launcher metadata and canonical app registry entry. Validate that the process is still alive and belongs to the mapped app. Reject missing, ambiguous or forged identity.
- For PWA apps, the native `nuxel-pwa-host`/launcher creates a host-owned session binding the iframe/webview to the canonical app ID at launch. Permission requests from the iframe travel over the existing authenticated host bridge, but the host supplies the bound identity. Do not let page JavaScript override it by adding `app_id` to its payload.
- Settings management calls are different from app requests: authenticate them as the trusted foreground system Settings principal/owner session. Check that the caller is allowed to administer grants. A normal app must not call the admin grant/revoke API for itself or another app.
- When a PWA runs in a shared host process, do not rely on PID alone. Bind requests to the host-managed per-app frame/session token and validate that the sender is the exact active frame/origin. Revalidate after app switches and on host restart.
- Record both the authenticated principal and target app in audit entries.

If a platform identity mechanism is unavailable for a particular app type, fail closed and report that the identity binding still needs implementation. Do not weaken identity checks by trusting the app's own declaration.

### 5.2 Per-asset broker checks

A grant must be checked at the operation boundary, not only when a page opens. For example:

- Microphone: check `microphone` before `getUserMedia`, before native audio capture opens, and at any capture route change; stop active capture immediately on revoke.
- Camera: check `camera` before opening a device or starting preview/capture; stop stream on revoke.
- Location: check precise/coarse/background scope before every provider subscription/read as appropriate; stop active update on revoke.
- Contacts/calendar/SMS/call: broker checks the correct read/write/send/receive action on every API call.
- Network: mediate the app's actual network route or clearly state whether only an app API request (not arbitrary sockets) is gated. On 4.14 use the measured cgroup-v1 `net_cls`/nftables mechanisms where configured; never claim full network isolation if traffic can bypass the cgroup.
- Bluetooth/NFC/USB: broker access to BlueZ/NFC/USB APIs and enforce D-Bus/device-node ACLs where available.
- Notifications: validate sender identity/capability before posting or exposing notification content.
- Background execution: check before creating/keeping an app background unit.
- App install/remove/system inspect: route to the privileged service with owner confirmation and narrow action allowlists.
- Fullscreen: check each explicit app request, not just app launch.
- Zoom: check the capability before enabling the host gesture layer for that active app.
- Mirroring: check the currently mirrored foreground app before each mirrored frame/session transition at the actual mirror output surface.
- Casting: the future casting broker must check `casting` before creating a session and on subsequent control operations.

Build an operation-to-capability coverage map and a test that ensures each registered sensitive operation is mediated. Do not count a manifest declaration as enforcement.

### 5.3 Policy decision API

Refactor permd into a well-defined policy engine with typed functions, for example:

- `resolve_app_identity(caller_context) -> AppIdentity | Deny`
- `list_installed_apps() -> AppSummary[]`
- `get_app_permissions(app_id, include_unrequested=true) -> AppPermissionSnapshot`
- `get_capabilities() -> CapabilityDefinition[]`
- `check(app_identity, capability, operation_context) -> Decision`
- `request(app_identity, capability, purpose, operation_context) -> Request/Decision`
- `grant(app_id, capability, duration, actor, reason) -> result`
- `deny(app_id, capability, actor, reason) -> result`
- `revoke(app_id, capability, actor, reason) -> result`
- `revoke_all(app_id, actor, reason) -> result`
- `get_audit(filters) -> AuditEvent[]`
- `get_enforcement_status() -> target and per-capability mechanism facts`
- `set_global_kill_switch(resource, blocked, actor) -> result`

The API schema may differ, but all consumers must share the same behavior and structured decision object. Include: `decision` (`allow`/`deny`), reason, canonical app ID, capability, grant source, duration/expiry, enforcement level, and audit event ID. Separate “policy says allowed” from “resource is available/enforcement is deployed”.

### 5.4 D-Bus and host API

- Expose a narrow manager interface backed by permd. A D-Bus facade may be provided by `nuxel-portal` or permd, but it must be one authoritative implementation.
- Keep app-facing APIs separate from admin management APIs. Apps can check/request their own permissions only; only trusted Settings/system owner can list/manage all apps and edit grants.
- Extend `services/nuxel-bridge/src/api.py` RPC map with manager operations. Proposed names (adapt to existing naming style but keep full functionality):
  - `permissions.apps`
  - `permissions.capabilities`
  - `permissions.get-app`
  - `permissions.grant`
  - `permissions.deny`
  - `permissions.revoke`
  - `permissions.revoke-all`
  - `permissions.request`
  - `permissions.audit`
  - `permissions.enforcement`
  - `permissions.set-global-kill-switch`
- Keep the existing `permissions.list/request/revoke` compatibility routes if clients already depend on them, but map them to the same policy engine and correct identity checks. Add versioned schemas and update PWA bridge clients.
- The Settings PWA must never receive the permd root token. Host/bridge service authenticates to permd. Protect manager endpoints from app-originated RPC calls.
- Do not bind the permd write API to a publicly reachable network interface. Prefer a private Unix socket or D-Bus; if retaining the loopback HTTP API, require a root-owned secret held only by the bridge/service, strict local-only bind, request size/schema limits, authentication, origin restrictions and tests. A webview must not be able to read the secret.

## 6. Permission request and consent UX

The phone does not have a PhoshAgent session. Design a real Nuxel consent path that works with the handset's actual shell architecture:

1. App asks the portal for a capability with a short user-facing purpose string and requested action (e.g. “Record audio for this recording”).
2. Portal authenticates the app and forwards the request to permd.
3. If already allowed and no global kill-switch blocks it, return allow and continue.
4. If denied or blocked, return denial without touching the resource.
5. If not yet decided, the shell-owned consent controller displays a trusted Nuxel permission sheet/notification above the app. It must show app name/icon, exact permission, requested purpose, risk, and grant scope.
6. User choices: **Allow once**, **Allow while using this session** (only if meaningful), **Always allow**, **Deny**. “Always allow” is the persistent choice that survives reboot. Deny is persistent unless the user later changes it in Settings. The default highlighted/action focus must be Deny or neutral, never Allow.
7. If app is backgrounded, lockscreen is active, no safe consent surface is available, request times out, or app identity cannot be shown reliably, deny and log it. Do not display deceptive app names.
8. Do not prompt on every API call after a persistent grant. Do recheck the grant and kill-switch on every protected operation.
9. A sensitive permission can be revoked while an app is running. Send a policy-changed signal, stop active protected resources and show a non-blocking reason to the app.

Keep prompts concise and touch-friendly for the S10+ portrait display. Avoid multiple stacked prompts for the same app/capability. Coalesce duplicate simultaneous requests. Add a cooldown to prevent prompt spam. Ensure lockscreen/privacy rules are respected.

## 7. Settings → Permissions: actual complete manager UI

Add a first-class **Permissions** tab to `pwa/nuxel-apps/settings/index.html` and wire it into the existing `settings.js` tab system, `settings.css`, and the host bridge. Do not make it a separate dashboard or ask the user to open the old standalone GTK app.

### 7.1 Main Permissions screen

Provide a touch-first, legible screen consistent with Nuxel Settings styling. It should contain:

- Header: **Permissions** and a short explanation (“Control what each installed app can access”).
- Search/filter field by app name or capability.
- Filter chips or compact controls: All apps, Needs review, Has access, Blocked, System apps (if useful). Do not make a dense desktop table the only interaction.
- An actual row/card for **every installed, supported app**, including apps that have zero grants. Each row shows icon/name, app type, current status summary (e.g. “2 allowed · 4 blocked”), and a clear way to open its permission details.
- Visual distinction for unsupported/unavailable capabilities and system-owner services.
- An unobtrusive refresh action and clear loading/offline/error states.
- A “Permission history” entry/button leading to the audit list.
- A compact explanation of global privacy kill switches if any are active.

Do not present unsupported or uninstalled apps as though they are usable. App entries marked `unsupported`, `template` or not installed in package state must not be given active grant toggles.

### 7.2 Per-app permission detail view

Selecting an app opens a dedicated view/panel with:

- App name, icon, canonical app ID, package/source and installed state.
- A clear summary of what is currently allowed and denied.
- Capability sections grouped logically: Privacy & sensors, Personal data, Connectivity & devices, Display & sharing, System/background, App management (only relevant groups for that app).
- Each permission row includes friendly name, concise description, why this app declared it, current state, enforcement status and a touch-friendly switch/button.
- State vocabulary must distinguish `Allowed`, `Denied`, `Not requested`, `Unavailable on this device`, `Not enforced`, `Future feature`, `Temporarily allowed`, and `Blocked by global kill switch`. Do not compress all states into a green/red boolean.
- A granted permission shows scope and permanence: “Always (survives restart)”, “This session”, or “One time”. The normal Settings switch sets/clears persistent allow/deny.
- The owner must be able to turn permissions on and off individually without shell commands or editing JSON.
- A revoke action stops active use as soon as the backend can safely stop it. A Revoke all button should genuinely revoke all app-level grants, preserve the app's declarations, preserve the global mirroring default unless the owner explicitly changes it, and confirm before applying.
- Include capabilities the app declares and relevant platform controls such as zoom/fullscreen/casting/mirroring. It is acceptable to collapse unrequested generic capabilities to “Other permissions” rather than overwhelming the user, but the four Nuxel-specific controls must be easy to find for every installed app.
- For app-private storage or ordinary audio playback, show an explanatory “Not a sensitive permission” info row rather than a misleading toggle.

**Switch behavior:**

- Switch ON: issue an authenticated persistent `grant(... duration=always ...)` request. Do not optimistically leave it ON. Wait for the authoritative response and show ON only if the service confirms the grant is saved and usable. If the service is offline or returns an error, restore the old state and show the reason.
- Switch OFF: issue a persistent deny/revoke according to the policy model; it must immediately block future operations and stop active streams. Do not just remove the UI row.
- Re-render from server state after every mutation. No localStorage/local JSON as authority.
- Prevent double taps/races; disable the row while the mutation is pending.
- Make the switch accessible and usable on touch, keyboard and screen readers.
- If enforcement is partial, show a clear warning/explanation accessible from the row. Do not mark the capability “securely blocked” without proof.

### 7.3 Nuxel-specific controls must be prominent

For every installed app, show these four controls with the exact semantics:

- **Zoom with two fingers** — OFF by default. Description: “Allow two-finger pinch/drag to zoom this app's whole interface.” Clarify that app-internal zoom (e.g. map zoom) is separate.
- **Fullscreen** — ON only for the verified compatibility allowlist; OFF otherwise. Description: “Allow this app to request exclusive fullscreen / hide system chrome.”
- **Casting** — OFF by default. Description: “Allow this app to initiate future Nuxel casting.” If the casting service is not available, label it “Future feature — no casting service installed”; a saved preference is not a claim that casting is operational.
- **Mirroring** — ON by default for every app. Description: “Show this app on a connected mirrored display.” Turning OFF shows a clear preview/explanation that the external mirror will show a privacy blank while this app is in front; the phone screen stays normal.

### 7.4 Permission history

Implement a read-only, filterable history view backed by permd audit events:

- app, capability, allow/deny/revoke/consume/expire action, actor, timestamp, requested purpose, decision reason, grant duration, and enforcement result;
- filter by app/capability/action/date range;
- newest first, paginated or bounded;
- export JSON through a safe host action if export is implemented;
- never place secrets, tokens, file contents, coordinates or captured media in audit payloads.

The docs already describe Settings → Privacy → Permission History; this Settings implementation may place it under Permissions while preserving a discoverable link from any privacy page.

### 7.5 Global privacy controls

Keep global camera/microphone/location kill switches where appropriate, but define them as **global deny gates**:

- When a global kill switch blocks a resource, it overrides all per-app allows.
- Turning a kill switch OFF must not grant any app a permission; each app still requires its own allow.
- State must be persistent and visible in Settings.
- If the global switch cannot physically disconnect the resource, label it accurately as a software block and verify all relevant broker paths obey it.
- Do not confuse global hardware privacy controls with per-app permission grants.

## 8. Zoom, fullscreen, casting and mirroring implementation details

### 8.1 Whole-app zoom

Audit current Home gestures and app frame architecture before implementing. Keep existing Home launcher zoom suppression and app-specific gestures intact. Implement a host-owned, per-app whole-surface zoom controller that:

- is enabled only when the active app's `zoom` decision is ALLOW;
- recognizes a two-pointer pinch gesture and scales the app surface, with a configurable safe range (for example 1.0×–2.0×; use device testing to pick bounds);
- does not zoom the system bars, lockscreen or Home UI;
- does not hijack single-finger input, D-pad/game controls, scroll, text selection or a deliberate app gesture;
- coexists with app-native pinch zoom. Prefer an explicit system gesture zone or a gesture recognizer that activates only after a clear threshold and can hand control back safely. If it cannot distinguish safely, do not steal gestures in that app; report the limitation;
- resets to 1.0× when permission is revoked, the app closes, or the user hits Reset; app scale preference may persist per app separately;
- is covered by automated tests for allowed/denied gestures and app switching.

Do not change Maps pinch zoom or Browser page zoom when the whole-app zoom permission is denied; those are application features, not the new Nuxel `zoom` permission.

### 8.2 Fullscreen compatibility and gating

- Search the full tree for `requestFullscreen`, prefixed Fullscreen APIs, `nuxel:immersive`, `setImmersive`, native `gtk_window_fullscreen`, launch flags and other explicit fullscreen requests.
- Classify each call as (a) shell-managed normal app presentation, (b) explicit app-requested fullscreen, or (c) host implementation detail.
- Keep ordinary shell app presentation working. Gate category (b) by `fullscreen`.
- Ensure a denied app receives a structured refusal; it must not hide system recovery/navigation UI or trap the owner.
- Gate the WebKit Fullscreen API in the host where possible, and gate `nuxel:immersive` messages in `pwa/nuxel-home/js/immersive.js` using the active frame's trusted app identity and policy response.
- A same-origin message is not sufficient authorization; verify `event.source` and bound app ID from the launcher session.
- On revocation, exit app-requested fullscreen and restore safe system chrome.
- Seed only the verified currently implemented apps, not every manifest with `display: fullscreen`.

### 8.3 Casting policy hook

- Add `casting` to the central registry, bridge enums and app manifest validation.
- Add an authorization API with operations such as `casting.create`, `casting.control`, `casting.stop` (or equivalent). Every future transport/receiver implementation must call it.
- Keep default deny.
- If no casting implementation is present, show the state as unavailable/future and do not return an “active” success to an app.
- Do not reuse `mirroring` as a substitute for casting authorization.

### 8.4 Mirroring privacy enforcement

Trace the actual S10+ mirror pipeline(s) in this repository: external display/capture, scrcpy, VNC, XRDP, USB-C display, compositor/framebuffer copy and any future screen-share service. Find the exact point where the current app's frame is sent to an external destination.

- Apply `mirroring` at that output point and at session changes.
- If ALLOW, stream the correct app frame.
- If DENY, emit a black/blank frame or compositor privacy surface to the external output, not the phone panel. Prevent stale previously captured frames from being replayed after denial; flush buffers and stop/blank the stream.
- When the app changes, re-evaluate before forwarding its first frame. Avoid a one-frame leak during app switch or revoke.
- When the app is allowed again, resume safely.
- Handle app switch, lockscreen, screen-off, disconnect/reconnect, rotation, suspend/resume and service restart.
- If multiple external display/mirroring implementations exist, inventory and gate all supported routes. If one route cannot be safely gated, mark it unsupported/disabled rather than falsely claiming privacy protection.
- Add an integration test around the mirror-output broker using synthetic frames, verifying denied app output is black and allowed app output is unchanged.

## 9. Data model and persistence

Evolve the current permd schema with explicit schema versioning and a migration path. Preserve backward compatibility only where it is safe and unambiguous.

A recommended conceptual model (adapt to actual code style):

```json
{
  "schema_version": 3,
  "app_id": "org.nuxel.Recorder",
  "revision": 12,
  "permissions": {
    "microphone": {
      "decision": "allow",
      "duration": "always",
      "granted_at": "<ISO-8601 UTC>",
      "granted_by": "owner",
      "reason": "Owner-approved Recorder microphone access",
      "expires_at": null
    },
    "zoom": {
      "decision": "deny",
      "duration": "always",
      "updated_at": "<ISO-8601 UTC>",
      "updated_by": "policy-default"
    },
    "mirroring": {
      "decision": "allow",
      "duration": "always",
      "updated_by": "policy-default"
    }
  }
}
```

The actual implementation may store defaults globally and sparse per-app overrides. Prefer explicit semantics over implicit truthiness. It must be possible to tell apart:

- no explicit record (apply capability default);
- explicit deny;
- persistent allow;
- session allow;
- one-time allow/consumed;
- unavailable/unsupported;
- blocked by a global kill switch;
- declared/requested by app but not granted.

### 9.1 Atomicity and recovery

- Ensure only permd writes the store.
- Use a process-wide lock or robust file/database transaction to prevent lost updates.
- Write a temporary file in the same filesystem, fsync it, atomically replace the target, and fsync the directory where appropriate.
- Restrict directory and file ownership/modes to the service owner/root as required; do not expose grant files to normal apps.
- Validate app IDs before path construction; reject slashes, traversal, NULs and unexpected Unicode/control characters.
- Validate schema, capability IDs, grant durations and timestamps.
- On corrupt/unknown schema, fail closed, preserve a copy for diagnosis with restrictive permissions, and write a redacted audit error. Do not silently treat malformed JSON as an empty allow set and later overwrite the only evidence.
- Add state revision numbers to detect stale UI mutations.
- Store an append-only audit log with bounded rotation and clear retention policy. Make audit writes durable enough that a grant/revoke cannot succeed while its security audit is silently lost.

### 9.2 Boot behavior

- On daemon startup, expire/clear one-time and session grants.
- Load persistent allow/deny and global privacy controls.
- Reconcile app registry changes without granting anything except mirroring default and the explicitly approved seed grants.
- Do not delete a user's explicit deny when an app updates or changes manifest ordering.
- If a previously installed app is removed, retain a bounded tombstone/audit history but remove live grants or mark them inactive; reinstall must not silently restore old sensitive allows unless the owner deliberately chose a persistent app policy and the identity/package signer/source still matches. Prefer revoking on uninstall and requiring re-approval after reinstall for high-risk permissions.
- Ensure the mirror default applies to new app identities without overriding an explicit deny.

## 10. Migration from current repository state

Implement a versioned migration command or service startup migration that is safe, idempotent and testable. Do not run it destructively on the connected phone during development.

Migration requirements:

1. Back up the existing `/var/lib/nuxel/permissions` state and relevant config files with secure permissions. Do not print secrets/tokens.
2. Normalize all known app IDs from old directory fallbacks and manifests to canonical registry IDs. Example: `recorder` → `org.nuxel.Recorder`, only when the mapping is unique and verified.
3. Convert legacy token names to canonical IDs using an explicit alias table. Record every conversion and every unrecognized token.
4. Stop the portal and bridge from writing old grant files independently before migrating live data.
5. Clear old implicit `default_capabilities` grants. They are declarations/config leftovers, not owner consent.
6. Apply the new initial policies:
   - `mirroring=allow` for all installed/supported apps and the default for new apps;
   - `zoom=deny` for all;
   - `casting=deny` for all;
   - `fullscreen=allow` only for the source-audited explicit-fullscreen compatibility allowlist, deny for all others;
   - `microphone=allow` for `org.nuxel.Recorder` as explicitly requested; deny for all other apps;
   - all other grant-required capabilities deny unless the owner explicitly confirmed a migration exception. No automatic preservation of an old allow.
7. Reclassify system-surface requirements (Home/Settings network, Bluetooth, location management) as narrowly scoped system-owner actions with an authenticated owner principal. Do not give the Settings app generic access to every user's private data merely because it manages settings.
8. Preserve app-private data and user content. This is a permission migration, not an app-data cleanup.
9. Write a dry-run report listing proposed app identity changes, old grant removals, new defaults, initial seed grants, unsupported capabilities, and apps needing owner review.
10. Provide `--dry-run`, `--apply`, `--rollback` or equivalent, with clear refusal if backups or schema validation fail. Make migration idempotent.
11. Add tests that create synthetic old state files and verify the expected new state and rollback.

## 11. Global privacy gates and active-session revocation

- Retain the global camera, microphone and location privacy settings if those are real system capabilities. Name them clearly as global kill switches.
- The decision function is effectively: `allow only if app grant allows AND global gate permits AND capability is supported AND requester identity is valid AND enforcement path is available for the requested operation`.
- Global kill switches override app grants and must be reflected in every query and UI state.
- On revoke/deny/kill-switch activation, publish a policy-changed event to bridge/host clients. Stop active mic/camera/location streams, stop background work, close sensitive handles, terminate display-capture or mirror forwarding, and prevent new opens.
- A revoked app must not regain access merely by reloading its iframe or restarting its webview.
- If a resource cannot be forcibly revoked after a file descriptor or device handle is handed out, do not pretend it can. Keep the broker holding the handle, add a revocation-capable proxy, or explicitly label the limitation and prevent new sessions.

## 12. Testing requirements

Build an automated test suite around the central policy engine and its consumers. Add tests; do not only update snapshots.

### 12.1 Policy engine tests

- Missing permission record denies all grant-required capabilities except explicit defaults.
- Every new app starts with `mirroring=allow`, `zoom=deny`, `casting=deny`, all other grant-required permissions denied.
- Verified fullscreen allowlist is seeded only for exact approved IDs; arbitrary app with `display: fullscreen` remains denied.
- Recorder microphone is persistent allow; another recorder-like or unknown app does not inherit it.
- Explicit per-app mirroring deny overrides allow-by-default; new apps do not override that explicit deny.
- Explicit deny persists across restarts/reboots.
- Persistent allow persists across restarts/reboots.
- `once` grant is consumed exactly once, under concurrency.
- Session grants clear at startup and cannot be read as permanent.
- `revoke`, `deny`, `revoke-all` actually remove/override grants and emit events/audit entries.
- Unsupported capabilities such as current clipboard implementation cannot be granted through API or UI.
- Unknown capabilities, unknown apps, malformed identity and corrupt state fail closed.
- Concurrent grant/revoke operations do not lose updates.
- App registry identity conflicts and path traversal IDs are rejected.
- Global kill switch overrides an app grant; re-enabling the hardware gate does not grant an app.

### 12.2 Portal and bridge tests

- Portal has no independent grant writer.
- Bridge offline fallback denies; test explicitly asserts no auto-grant.
- No `always_ok` bypass for sensitive capabilities. Intrinsic non-sensitive behavior is represented in registry, not in arbitrary hardcoded allow lists.
- D-Bus caller-supplied `app_id` cannot impersonate another app.
- PWA host binds frame to canonical app ID; a page cannot alter `app_id` in its RPC payload.
- Settings manager API is inaccessible to an ordinary app and works for the authenticated owner Settings session.
- Portal/bridge timeout, disconnected daemon and unavailable consent UI all deny.
- `NUXEL_PORTAL_AUTO_GRANT` or similar test bypass is rejected in production configuration.
- Legacy RPC routes resolve to the same permd policy and audit path.

### 12.3 Settings UI tests

- Permissions tab exists in the real Settings PWA and is reachable through the normal tab navigation.
- Installed apps with zero permission files/records still appear.
- Unsupported/uninstalled/template apps are not grantable.
- Per-app switch ON persists through reload and backend restart.
- Switch OFF revokes and remains OFF after reload/reboot simulation.
- Offline/errors restore the previous switch state and explain why.
- Revoke all actually revokes, updates count/state and preserves declarations.
- Filters/search work and permission history is visible.
- Mirroring is initially ON, zoom/casting OFF, fullscreen defaults match the compatibility allowlist, Recorder microphone is ON.
- Other grant-required permissions are OFF by default.
- Global kill-switch state is shown and correctly overrides grants.
- UI state is rendered from backend results, not localStorage.
- Touch-sized controls work at target phone resolution and do not overflow/clip.

### 12.4 Feature-specific tests

- **Microphone:** Recorder's mic call checks the permd grant; revoke stops/blocks capture; the host no longer has a standalone 15-second auto-authorization path; mic permission denied means `getUserMedia`/native capture fails with a user-actionable message.
- **Zoom:** with permission OFF, two-finger host pinch does not change whole-app scale; with it ON, app surface scales; it resets on revoke/close; Maps' own map zoom still works.
- **Fullscreen:** an app without permission cannot enter explicit Fullscreen API or Nuxel immersive request; authorized compatibility apps can; revocation exits app-requested fullscreen; system recovery/navigation remains accessible.
- **Casting:** permission API denies by default; with no casting service, Settings reports not available and no fake active session can be created.
- **Mirroring:** synthetic allowed frame reaches mirror output; denied frame produces black/blank mirror output; local phone display remains normal; switching/revoking app cannot leak a stale frame.

### 12.5 Target integration and enforcement proofs

- Extend `tools/s10plus/a33/verify-permissions.py` or add a reproducible permission verification script.
- Validate the actual running kernel, LSM list, cgroup mode, AppArmor state and nftables/net_cls configuration before claiming enforcement.
- Test at least microphone, camera, location, notification, network, Bluetooth, USB, fullscreen, zoom and mirroring paths at the level actually supported by target hardware/software.
- Separate “unit test passed”, “service integration passed”, “target hardware verified”, and “kernel-enforced” verdicts. Do not collapse them.
- Keep an evidence report of limitations, expected logs and manual owner-only hardware tests.

## 13. Documentation and developer tooling

Update the existing documentation rather than adding conflicting security claims:

- `docs/security-model.md`: single authority, trusted caller identity, manager path, consent UX, per-app controls, audit history, mirroring semantics, fullscreen distinction, revocation behavior.
- `docs/security-defaults.md`: exact defaults table and migration semantics, including the explicit Recorder microphone exception.
- `configs/nuxel/permissions/README.md`: remove the obsolete assumption that PhoshAgent is available; document the new shell-owned consent surface and system-owner principal.
- Capability registry documentation: enforcement honesty for Linux 4.14.253, unsupported controls, future casting status.
- App registry docs: canonical registry and generation/validation pipeline; manifests' canonical app ID requirement.
- Developer docs: how to declare a capability, how to request it, how to test it, and why a declaration is not a grant.
- Add a diagnostic CLI/report for app-to-capability declaration coverage, grants, denials and enforcement limitations. The CLI must read the same permd API/store and must not mutate permissions unless an explicit owner subcommand is used.

## 14. Suggested implementation phases and gates

Work in small, coherent commits or staged changes. Run targeted tests after each phase and the repository's applicable full quality gates at the end.

### Phase A — audit and schema

- Re-read the actual checkout and map every current permission store, caller, capability enum, app registry and consumer.
- Add/extend canonical capability definitions and alias mappings, including `zoom`, `fullscreen`, `casting`, `mirroring` and supported standard phone capabilities.
- Define the canonical app registry source and identity validation.
- Gate A: registry validation and policy-schema tests pass; no runtime behavior changed yet.

### Phase B — central authority and identity

- Refactor permd as sole writer/decision-maker.
- Add authenticated identity binding for native D-Bus and PWA host requests.
- Convert portal to a façade and remove all independent writes.
- Remove bridge fail-open auto-grant and arbitrary `always_ok` sensitive bypasses.
- Add manager/app API separation and a real consent controller path.
- Gate B: all policy, identity, portal and bridge fail-closed tests pass.

### Phase C — migration and persistent defaults

- Add schema migration/dry-run/backup/rollback.
- Apply default-deny rules plus mirroring allow, Recorder microphone allow and verified fullscreen allowlist.
- Correct all PWA IDs and reconcile app registries.
- Gate C: synthetic migration, reboot persistence and app inventory tests pass.

### Phase D — Settings manager

- Add Permissions tab, installed-app list, per-app details, individual switches, Nuxel-specific controls, global kill-switch status and permission history.
- Connect every control to the authenticated backend API and render confirmed server state.
- Fix the GTK app to consume the same API or make it a Settings deep-link.
- Gate D: UI and end-to-end Settings tests pass.

### Phase E — operation enforcement and Nuxel features

- Replace Recorder's local mic authorization bypass with policy calls.
- Gate all currently used camera/mic/location/contacts/call/SMS/network/device/notification/file operations.
- Implement whole-app zoom permission and gesture logic.
- Gate explicit fullscreen and native request paths while preserving normal shell behavior.
- Add casting policy API and honest not-yet-available UI.
- Gate every mirrored display output route with external-only privacy blanking.
- Gate E: feature-specific tests and source-to-operation coverage pass.

### Phase F — verification, docs and release readiness

- Run formatting, unit tests, service tests, PWA checks, registry validation, packaging/build and relevant repository gates.
- Run the target enforcement diagnostic without claiming unverified hardware paths.
- Produce an implementation report listing files changed, APIs added, migration behavior, default grant matrix, apps and their declarations, enforcement coverage, test commands/results, unimplemented/unsupported items and safe owner deployment instructions.
- Gate F: no open fail-open paths, no duplicate store writers, no UI-only switches, no unsupported cosmetic toggles, no unresolved app identity drift.

## 15. Definition of done

The work is **not finished** until all of the following are true:

1. Settings contains a real Permissions tab and a working list of every currently installed supported app, including apps with zero grants.
2. Every app has an individually configurable permission page. A normal owner can allow/revoke each supported permission with touch controls and without editing config files or using a shell.
3. All permission requests from apps and sensitive system operations pass through one central policy authority.
4. Per-app identity is verified by trusted system/host context; caller-supplied app IDs cannot impersonate other apps.
5. Missing grants and every broker/service/identity error deny access. The portal-unavailable auto-grant is gone.
6. No bridge/portal/UI component writes an independent permission store or bypasses permd.
7. Permission grants and denies persist across reboot; one-time/session grants expire correctly.
8. Initial policy matches the exact defaults: mirroring allowed for all; zoom denied for all; casting denied for all; fullscreen allowed only for verified existing explicit-fullscreen apps; microphone allowed for Recorder only as explicitly requested; every other grant-required capability denied.
9. App declarations are correct and aligned with actual installed apps. Recorder declares microphone and uses the central broker.
10. Permission toggles change actual enforcement, not merely UI state.
11. Zoom controls whole-app two-finger scaling and leaves app-specific zoom alone.
12. Fullscreen authorization gates explicit app requests without breaking ordinary Nuxel shell presentation or emergency navigation.
13. Casting is permission-gated and honestly shown as unavailable until the service exists.
14. Mirroring denial produces a black/blank external output while the handset screen remains normal, and does not leak stale frames.
15. Global privacy kill switches override app grants and never create grants.
16. Unsupported permissions are visibly unavailable and cannot be accidentally represented as protected.
17. Audit history records permission requests, decisions, changes, revokes, expiries and system actors without leaking secrets.
18. Automated tests cover policy, identity, persistence, migration, Settings, operation-level enforcement and the four Nuxel-specific controls.
19. Documentation and target enforcement claims match the actual S10+ Linux 4.14.253 capabilities.
20. Final implementation report includes test results and honest outstanding hardware/enforcement limitations.

**Final instruction:** implement the complete permission manager now, reusing the repository's policy daemon and bridge architecture. Do not stop after creating the Settings tab or updating JSON declarations. Trace each sensitive operation to its actual runtime boundary, connect it to the central authority, make the owner controls functional, migrate safely, and prove the behavior with tests. When an operation cannot yet be enforced on the target device, say so in the UI and report; never replace missing enforcement with a fake switch.

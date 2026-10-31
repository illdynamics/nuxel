# FULL-PWNAGE-45000
# NUXEL — USB MTP, SOFTWARE CENTER, NATIVE APP LAUNCH, NUXTORE APP REGISTRY, NATIVE NAVDOCK ART, NFC, BIOMETRICS, SECURITY LOCK, DND, FLASHLIGHT & COLORED LED NOTIFICATIONS

## Complete source-level implementation, integration, regression testing and safe S10+ deployment mission

**Mission ID:** PWNAGE-45000  
**Target device:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel — custom Fedora-based ARM64 mobile Linux  
**Primary UI:** Nuxel Home PWA + Settings PWA + app PWAs + native Wayland dock  
**Bridge:** `services/nuxel-bridge`  
**Hardware services:** `services/nuxel-session`, `services/nuxel-s10`, S10+ native tools  
**Image builder:** `images/s10plus/build-phone-rootfs-inside-fedora.sh`  
**Store scope:** Local/offline NuxTore catalog only; no remote repository connection or publishing in this mission  
**Mission type:** actual implementation, package/build integration, security review, regression tests, physical device validation and safe deployment

---

# 0. MISSION OBJECTIVE

The Nuxel S10+ is already a booting Fedora-based Linux phone with a Wayland/Pixman presentation path, a native layer-shell navigation dock, a PWA Home shell, Python hardware/API services, a native button manager, a local app catalog and several partially implemented hardware providers.

This mission closes the gaps between those components. It must not add decorative controls that claim functionality without a real provider. It must discover what the current S10+ kernel and installed system can actually do, finish supported paths, implement missing app lifecycle integration and give honest blocker/unsupported results for features that require kernel/firmware/TEE work outside the current userspace.

The mission includes all requested work:

1. Reorder the lockscreen's primary USB-connected and Live Console icons so the active console penguin is in the middle.
2. Lower and modestly enlarge the secondary console transport penguin indicators for Serial, USB, WLAN and File Transfer.
3. Make USB File Transfer genuinely enumerate as an MTP device on the connected computer while preserving the current USB console.
4. Install/integrate a Software application for native GTK and RPM apps, with Flatpak only when all sandbox prerequisites are met.
5. Fix Firefox, VLC, Signal and native application launch failures / no-visible-window behavior.
6. Repair NuxTore app discovery and installation state; make all local catalog applications actually appear, launch, install and remove; finish incomplete applications rather than showing fake entries.
7. Repair the native Back / Penguin Home / Tabs artwork so it is polished and not cut off.
8. Investigate NFC, add accurate top-bar state/toggle and a dedicated NFC Settings panel with diagnostics and test.
9. Investigate the fingerprint reader; add secure enrollment/test/management only if supported by the actual sensor/driver/TEE path.
10. Add a Security Settings panel to choose Swipe, Pattern, PIN and Fingerprint with mandatory PIN fallback for Fingerprint, enforced by the actual session lock.
11. Implement actual DND and Flashlight behavior, eliminating generic “not in this build” and policy dead ends without weakening the LED safety policy.
12. Make colored LED notifications work using real color channels or provide a separately labelled display-overlay fallback when hardware LED classes are absent.

**Implement the complete code path and test it. Do not stop after describing what should be done.**

---

# 1. REPOSITORY BASELINE AND ACTIVE-PATH RULES

## 1.1 Start by resolving the actual deployed code paths

Inspect the entire current repository and the active build script before editing. Do not assume directory naming or older A33/A34/A45/A69 source variants are equivalent. Determine which exact source is compiled and installed into the current S10+ image.

Start with:

```text
README.md
VERSION
Makefile
images/s10plus/build-phone-rootfs-inside-fedora.sh
images/s10plus/packages-manifest.json
pwa/nuxel-home/
pwa/nuxel-common/app-registry.json
pwa/nuxel-apps/settings/
pwa/nuxel-apps/nuxtore/
pwa/nuxel-apps/{snekbyte,media,downloader,authenticator,cleanup,devmgmt,penguinterface}/
services/nuxel-bridge/src/
services/nuxel-session/systemd/
services/nuxel-notifications/
services/nuxel-s10/
configs/nuxel/{usb,nfc,leds,haptics,app-registry}/
tools/s10plus/a33/
tools/s10plus/a45/
docs/a51-wifi-to-web/
docs/a53/
docs/beta-finalization/
```

Build and package integration is part of the feature. A Python service or C helper that works in a developer checkout but is absent from the generated ARM64 rootfs is not done.

## 1.2 Establish a read-only live baseline

When the existing configured SSH target is available, collect read-only evidence before changing anything. Do not guess an IP, scan networks or invent credentials.

Capture:

- Git branch, commit, working-tree status and source archive version.
- Nuxel version, active rootfs/build identifier and PWA cache versions.
- Kernel release, architecture and relevant kernel config symbols.
- Active gadget/UDC/configfs state, USB descriptors and current CDC-ACM console.
- Active Wayland display, PWA host, native navdock and framebuffer owner.
- Installed RPMs, Flatpak installation list, available package managers, PackageKit, polkit agents and portals.
- `/usr/share/applications`, `/usr/local/share/applications`, `/home/nuxel/.local/share/applications` desktop entries and their actual Exec/TryExec/Icon targets.
- Native app binary existence, architecture and dynamic-library dependencies.
- NuxTore catalog, bundle signatures, app registry and installed/staged app directories.
- NFC diagnostic output (do not start writes or firmware changes in this baseline).
- Fingerprint sensor/device/driver evidence (read-only only).
- LED class inventory, torch policy status, notification color channels and active owners.
- Notification daemon/API behavior and current DND capability state.
- User data locations, file ownership, permissions and SSH access needed for rollback.

Store the baseline in:

`docs/beta-finalization/live/evidence/pwnage-45000/baseline/`

Never place credentials, signing private keys, authenticator secrets, PINs, fingerprints or other user secrets in the evidence archive.

## 1.3 Canonical active build integration

Use `images/s10plus/build-phone-rootfs-inside-fedora.sh` as the authoritative answer for which tools/services/configs ship. Existing examples include the Bridge, portal and notification daemon installation and the copy of `pwa/nuxel-common/app-registry.json` to `/etc/nuxel/app-registry/app_registry.json`.

For every new service, helper, package or asset:

- Add it to the correct manifest/build script.
- Install the systemd unit with correct user/group, permissions, dependencies and ordering.
- Add config/schema/default policy to the image.
- Add an active-build test proving it exists at the exact runtime path.
- Ensure the rootfs install does not erase existing user data.
- Verify the ARM64 binary architecture and dependencies.
- Ensure clean image generation reproduces the installed state.

Do not patch a live image only. Source and rootfs generation must agree.

---

# 2. LOCKSCREEN INDICATORS — REORDER PRIMARY ART AND IMPROVE TRANSPORT PENGUINS

## 2.1 Current markup

In `pwa/nuxel-home/index.html`, the primary row is `#lockscreen-indicators`. It currently contains:

- Charging indicator (`#lockscreen-indicator-charging`).
- USB-connected-to-PC artwork (`#lockscreen-indicator-usb`, currently using `nuxel-connected-pc.png`).
- Live-console artwork (`#lockscreen-indicator-live`, currently using `nuxel-live-console-active.png`).

The separate secondary row is `#lockscreen-transports`; it displays independent transport icons such as Serial, USB console, WLAN, File Transfer and Bluetooth.

The CSS currently places the primary row around `top:184px`, with approximately 68px icon boxes; the secondary transport row is at `top:252px`, has approximately 40px icons and wraps when necessary.

## 2.2 Required visual order

Reorder the primary DOM to:

1. Charging.
2. Live Console active.
3. USB connected to PC.

The Live Console penguin must be visually in the middle when all three indicators are visible. Prefer DOM order to CSS `order` unless existing animation logic requires another arrangement. Preserve stable IDs and the JS references in `lockscreen-indicators.js`.

Do not swap the meaning/state data. Only change the visual order. The PC-connected indication must still depend on real USB/host state and Live Console on its own real provider fields.

## 2.3 Lower transport row: slightly lower, somewhat larger

The request concerns the secondary console-transport penguins, not the primary three large status illustrations.

- Move `#lockscreen-transports` downward modestly from its current 252px position. A first candidate is +6 to +10 CSS pixels, but use actual device screenshots and measure overlap before choosing the final offset.
- Increase 40px transport icons modestly, targeting approximately 44–46px for common square artwork. Preserve individual aspect ratios. Keep the File Transfer artwork proportionally balanced rather than forcing every image to a square crop.
- Keep enough vertical separation from the primary row; avoid covering the lockhead, clock, connection-mode selector or touch-warning display.
- Keep the row centered, legible and able to wrap on portrait layout.
- Update the `@media (orientation: landscape) and (max-height:500px)` sizing/position rules to avoid a layout regression.
- Use the same alpha-aware painted-size logic that existing primary-row CSS comments describe. Enlarging a transparent parent while the visible alpha artwork remains tiny is not sufficient.
- Preserve `display:none` for inactive indicators; do not leave dim inactive ghost icons.
- Preserve reduced-motion behavior and avoid adding expensive blur/saturate filters. The S10+ renders software paths; static artwork is preferable to continuous effects.

## 2.4 Regression verification

Test every combination of charging, live console, USB PC and secondary transports. Confirm the active row order with all three primary states on. Check 360×760 portrait, normal lock state, active connection-mode selector, low-height landscape diagnostics and all icon combinations. Save screenshots before/after and record any small-screen exception.

---

# 3. USB FILE TRANSFER — COMPLETE REAL MTP DEVICE ENUMERATION

## 3.1 Confirmed immediate reason it does not work

The current selector and provider architecture can select `file_transfer`, but the actual helper is unfinished.

Relevant source:

- `services/nuxel-bridge/src/usb_mode.py`
- `services/nuxel-s10/bin/nuxel-usb-mode.sh`
- current USB gadget systemd/service/configfs ownership
- `services/nuxel-bridge/src/system_indicators.py`
- Quick Settings and lockscreen connection-mode UI
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`

The current shell helper checks whether a userspace responder such as `umtprd` or `mtp-server` exists and looks for relevant configfs MTP or FunctionFS entries. Even when it detects a possible responder/function, it currently ends with a message equivalent to:

`endpoint detected but activation helper is not configured; file transfer was not activated`

It writes `active:false`, `endpoint_state:not_activated` and returns failure. This is an intentional placeholder, not a successful device-mode implementation. Do not change only the JSON state to `active:true`.

## 3.2 MTP is required; mass-storage is forbidden

The user wants the phone to appear as a device on a computer. Implement MTP (Media Transfer Protocol) or another supported file-level protocol with a real host-visible descriptor/responder. Do not export the live Nuxel storage as USB Mass Storage.

Forbidden approaches:

- Creating a mass-storage LUN over `/home/nuxel`, the live rootfs, an active block device or mounted filesystem.
- Exposing the live filesystem raw to a host OS.
- Using a USB disk image and pretending it is live file sharing.
- Disabling SELinux or file permissions to make files “show up”.
- Replacing the existing USB serial/CDC-ACM gadget with MTP-only mode.
- Using USB NCM networking as a substitute. The Samsung 4.14.253 device/kernel has a documented NCM teardown hazard; do not experiment with NCM in this mission.

## 3.3 Preflight kernel and gadget audit

Before activating anything, inspect the actual device:

- Active UDC name and state under `/sys/class/udc`.
- Existing configfs gadget directory, functions, symlinks, strings, descriptors, configurations and bound UDC.
- Whether an existing owner/service creates or tears down the composite gadget.
- USB controller/role and cable/host attach state.
- Kernel config/modules for at least:
  - `CONFIG_USB_CONFIGFS`
  - `CONFIG_USB_CONFIGFS_F_FS`
  - `CONFIG_USB_F_FS`
  - `CONFIG_USB_CONFIGFS_F_MTP` or any supported native MTP function
  - USB gadget composite/configuration dependencies
  - FunctionFS mount support and required descriptors
- FunctionFS availability and mount path/permissions.
- Compatible MTP responder candidates and whether they support the actual gadget FunctionFS API on this kernel.
- Existing CDC-ACM function ownership and host serial access.
- Device VID/PID, manufacturer/product strings and interface descriptors as seen by the current host.

Do not infer MTP support from a `mtp.*` string or an installed binary alone. A helper binary, kernel function, FunctionFS descriptor and a live USB interface must all work together.

## 3.4 Implement one USB gadget owner

There must be one owner of the composite gadget/UDC lifecycle. Integrate MTP alongside the existing serial console under that owner or extend the existing owner without creating a competing service.

Required transaction design:

1. Verify a physical USB host/cable path and a valid UDC.
2. Snapshot the current gadget configuration and current CDC-ACM state for rollback.
3. Validate kernel MTP/FunctionFS capability and responder availability.
4. Stage the MTP interface/function and its descriptors without removing the working CDC-ACM interface.
5. Start or prepare the MTP responder with restricted access to the intended user media/document roots only.
6. Bind/rebind the composite gadget in one controlled operation. Do not leave the UDC unbound on an error path.
7. Wait for host enumeration and responder readiness.
8. Verify that the host actually sees an MTP interface/device and that a bounded MTP session can enumerate allowed folders.
9. Atomically publish `active:true` only after activation proof. Otherwise restore the previous CDC-ACM-only configuration and publish the precise failure stage.

If the kernel has no MTP or FunctionFS support, do not hack around it with raw storage. Report `BLOCKED_KERNEL`/`NOT_SUPPORTED_ON_DEVICE` and provide the exact kernel config/driver work required as a separate future task. This mission does not authorize kernel flashing.

## 3.5 Host-visible file scope and security

- Expose only intentional user-facing roots, e.g. `/home/nuxel/Gallery`, `Downloads`, and explicitly approved shared folders.
- Do not expose `/etc`, `/var`, service sockets, rootfs, SSH keys, browser profile, authenticator secrets, application credentials or arbitrary `/home` internals.
- Resolve symlinks and reject any path escaping the export root.
- Do not allow delete/format/rename outside the user-approved MTP scope.
- Keep file ownership and permissions intact. MTP should operate through the user session or tightly scoped helper, not unrestricted root filesystem access.
- Ensure file changes made over MTP are reflected in Files/Gallery using normal cache invalidation/refresh.
- Handle concurrent access by local Gallery/Files app safely.

## 3.6 Preserve USB console

The current `system_indicators.py` distinguishes console transports and file-transfer state. Preserve USB CDC-ACM console while MTP is activated wherever composite-device support permits it. The user should not lose the terminal connection when selecting File Transfer.

If a specific host/USB configuration cannot expose both interfaces, document the limitation and design a user-visible controlled switch with a guaranteed serial fallback/recovery path. Never silently kill the existing console.

## 3.7 Bridge and state semantics

Keep `usb_mode.py` as the high-level API owner, but move actual gadget lifecycle into one bounded privileged helper/service.

Return structured state such as:

```json
{
  "selected": "file_transfer",
  "active": false,
  "endpoint_state": "waiting_for_host",
  "provider": "mtp-functionfs",
  "error_code": null,
  "detail": "MTP function staged; waiting for enumeration"
}
```

Use actual state names supported by the implementation; examples above are illustrative only.

- `selected` is user intent.
- `active` means real host-visible MTP activation, not merely selected mode.
- `endpoint_state` distinguishes not-supported, staged, waiting, active, failed and stopped.
- A cable attach or host power connection is not proof of MTP enumeration.
- File Transfer label `file` on lockscreen/top bar is allowed only after active provider state.
- Disconnect must clear active state and return to the safe default without stale MTP gadget functions.
- If activation fails, restore the prior working configuration and show a human-readable reason.

## 3.8 Rootfs integration

- Install the chosen responder and its dependencies in the rootfs manifest.
- Install the new/updated systemd unit, policy/config and helper under stable paths.
- Verify the binary is ARM64 and runs under the intended user.
- Set USB gadget/configfs permissions narrowly.
- Ensure dependencies/order place gadget owner after required configfs/UDC setup and before the Bridge exposes the capability.
- Ensure service stop preserves safe USB state and cannot leave a partially bound gadget.
- Add a clean-image test proving all required binaries/configs exist.

## 3.9 Tests and physical proof

Unit/integration tests:

- No UDC present.
- No FunctionFS/MTP kernel support.
- Responder missing/crashes.
- FunctionFS cannot mount.
- Existing CDC-ACM function present.
- Configfs partially populated.
- Gadget rebind error and rollback.
- Cable detach during activation.
- Host refuses MTP or disconnects.
- Stale state file after service crash.
- Path traversal/symlink attack.
- File read/write permission enforcement.
- MTP active with console interface still present.

Physical test:

1. Connect S10+ to a real computer using a known-good USB data cable.
2. Select File Transfer on the phone.
3. Observe actual host USB enumeration, not just a phone toast.
4. Verify the host shows a portable/MTP device with Nuxel's allowed shared folders.
5. Copy a small test file from phone to computer and compare SHA-256.
6. Copy a test file from computer to phone into an allowed folder and compare SHA-256.
7. Verify Files/Gallery can see the changes.
8. Verify the USB console remains accessible if composite interface is supported.
9. Unplug/replug and confirm state recovers without stale active labels.

No physical host test means the feature remains `NEEDS_OWNER_TEST`, not fully done.

---

# 4. SOFTWARE APP — NATIVE GTK/RPM MANAGEMENT AND CONDITIONAL FLATPAK

## 4.1 User requirement

The user wants a Software app that installs native GTK applications and Flatpak applications. Implement a genuine software-management surface, not a static mock list.

Prefer GNOME Software where it is available for the actual Fedora release and ARM64 architecture. It can be exposed through its real desktop entry/GTK UI and integrated with Nuxel's session. If GNOME Software is not practical on this minimal Phoc session, implement the smallest safe Nuxel Software manager using the real package backend and portal/polkit transaction flow; do not imitate a store without a backend.

## 4.2 Recheck package-management prerequisites

The repository's prior evidence in `docs/a53/GNOME-SOFTWARE-RPM-FLATPAK.md` recorded:

- No `dnf`, `dnf5`, `microdnf` or usable PackageKit client/service.
- No PackageKit service/backend.
- No Flatpak executable/installation.
- No `xdg-desktop-portal`/GTK portal.
- A polkit daemon was present but no verified graphical authentication agent was wired into the Phoc session.
- Network/package-repository availability was blocked at the time of the audit.

Recheck all of these on the current live image and clean rootfs build. Do not assume an older blocker is still present or resolved.

## 4.3 Native GTK/RPM path

Implement a supported, auditable path for native RPM packages:

- Confirm `rpm` database and Fedora release/repository configuration.
- Verify ARM64/aarch64 package availability and signatures.
- Choose a real package transaction backend: PackageKit with the matching DNF backend, or a carefully controlled DNF5 transaction provider if supported by the target image.
- Install the GUI (`gnome-software` or approved alternative), PackageKit service/backend, AppStream metadata provider and GTK libraries required by that UI.
- Add a working graphical polkit agent to the actual Phoc user session. Make sure authorization prompts appear above the correct client and can be interacted with using touch/keyboard.
- Route install/remove/update operations through a backend that previews package, version, repository, dependencies, disk impact and removals before prompting for authorization.
- Require user confirmation for each privileged transaction. Never silently run arbitrary package installs because a user opened a package card.
- Verify package signatures and repository metadata. Do not disable GPG checking.
- Restrict repo configuration to trusted, owner-approved Fedora/Nuxel repositories; show repository origin and architecture.
- Do not run GUI package manager as root.
- Do not pass an arbitrary package string to a shell. Backend accepts validated package IDs and invokes safe argument arrays or DBus APIs.
- Handle transaction cancellation, error, no network, dependency conflict, insufficient disk, offline state and rollback information.

The Software app must have a real launcher entry and an actual installed binary. If dependencies cannot be downloaded due to no network, prepare the source/build integration and mark runtime installation blocked by network, not successful.

## 4.4 Flatpak path — kernel security gate

The repository's previous readiness documents state that the S10+ Samsung 4.14.253 kernel was built without `CONFIG_USER_NS` and `unshare -U` returned `Invalid argument`. Flatpak normally relies on Bubblewrap and user namespaces for its sandbox.

This is a real security dependency. Recheck the live kernel config and runtime behavior. If user namespaces remain unavailable, Flatpak install/run is blocked on this kernel.

Forbidden workarounds:

- `--no-sandbox` or disabling Bubblewrap isolation.
- Broad `--filesystem=host`, `--device=all`, unrestricted host filesystem access or unrestricted sockets.
- Disabling SELinux/AppArmor/security policy to force app startup.
- Running Flatpak GUI applications as root.
- Displaying “Installed” or “Supported” when the actual app cannot launch safely.

Only enable Flatpak in Software when all of the following are verified:

1. User namespace support is enabled and functional for the unprivileged app user.
2. Bubblewrap version and required kernel features work.
3. Flatpak daemon/runtime and repo configuration are installed and supported on aarch64.
4. XDG Desktop Portal and GTK portal backends are running in the Nuxel session and required file picker/open URI/screenshot portals work.
5. Correct Wayland socket/session environment is available to sandboxed apps.
6. SELinux and filesystem/device permissions remain appropriately restricted.
7. A real ARM64 Flatpak app installs and launches in a functioning sandbox and cannot access forbidden host paths.

If any prerequisite fails, show Flatpak as “Not available on this kernel/build” with the precise missing prerequisite, while allowing the native RPM section to work independently.

Kernel migration/user-namespace enablement is a separate kernel mission; do not flash or rebuild/install a kernel here. It is acceptable for this feature to ship native RPM Software first and Flatpak disabled pending a kernel update.

## 4.5 Software app user experience

Minimum requirements:

- Browse installed apps and supported catalog sources.
- Search by app name, summary and package ID.
- Show native RPM vs Flatpak type clearly.
- Show architecture, version, publisher/repo and required disk space.
- Install/remove/update with transaction preview and polkit confirmation.
- Display progress and accurate final status.
- Open app after installation only when a valid desktop entry/launch ID exists.
- Never install automatically just because an icon was clicked in NuXTore.
- Provide clear network/repository/package-backend unavailable state.
- Keep NuxTore's local bundles distinct from Fedora RPM/Flatpak sources.

---

# 5. NATIVE APPLICATIONS — FIX FIREFOX, VLC, SIGNAL AND “NOTHING HAPPENS”

## 5.1 User-visible bug

The user reports that Mozilla Firefox, VLC, “native apps” and Signal show no visible result when tapped, although Firefox was observed running earlier. This may mean the process starts but the Wayland surface is invisible, wrong user/session/D-Bus environment is used, app registry IDs do not resolve, or launch errors are swallowed. Some apps may also be absent or unsupported on aarch64.

Do not assume the cause is the same for every app. Diagnose each exact app independently.

## 5.2 Current launcher/Bridge path

Relevant pieces:

- `pwa/nuxel-home/js/apps.js` — static `NUXEL_APPS` definitions and app metadata.
- `pwa/nuxel-home/js/app.js` — `_launchNative()` and `_launchPwa()`.
- `pwa/nuxel-common/app-registry.json` — shared canonical registry.
- `services/nuxel-bridge/src/api.py` — `/api/v1/apps/exec`, native allowlist/registry lookup and execution.
- `images/s10plus/build-phone-rootfs-inside-fedora.sh` — installs the canonical app registry at `/etc/nuxel/app-registry/app_registry.json`.

The current native launch client calls the Bridge `/api/v1/apps/exec` endpoint with an application ID. The Bridge resolves a fixed native allowlist or registered native entry and starts the process using a systemd transient unit with a Wayland/session environment.

This design is preferable to allowing JavaScript to specify arbitrary commands, but it needs proper diagnostics and a unified application registry.

## 5.3 Inventory installed native applications

On the live phone and clean image, inspect:

- `rpm -qa` for Firefox, Mozilla Firefox, VLC, Signal and related packages.
- `flatpak list` only when Flatpak is installed and functional.
- Desktop entries in `/usr/share/applications`, `/usr/local/share/applications`, `/home/nuxel/.local/share/applications`.
- `TryExec`, `Exec`, `DBusActivatable`, `StartupWMClass`, `Icon`, `Path`, `Terminal`, desktop ID and action groups.
- Executable existence, ELF architecture (must be aarch64/ARM64), dynamic linker/libs and executable permissions.
- For Flatpak, real application ID, installation scope, architecture and launch command.
- D-Bus activation registration and whether the app already has a running process/window.

Do not guess an executable name from the product brand. Desktop entries may use wrapper scripts or D-Bus activation.

## 5.4 Instrument process start versus visible surface

For each launch request record a unique request ID and the stages:

```text
requested
  -> app_id_resolved
  -> desktop_entry_validated / native_binary_validated
  -> session_context_resolved
  -> process_or_dbus_activation_started
  -> process_alive
  -> Wayland_surface_seen (where detectable)
  -> focused/visible OR truthful failure
```

Return structured errors for unknown app ID, not installed, unsupported architecture, desktop file invalid, binary missing, permission denied, service start failure, missing display socket, missing D-Bus, application exited early, or startup timeout.

The UI should show “Opening Firefox…” and then a meaningful outcome. Do not leave the app tile looking like it opened if process startup failed.

Capture relevant transient unit journal output and child exit code; do not dump secrets/environment credentials into logs.

## 5.5 Correct session context

Ensure native apps launch as the intended `nuxel` interactive session user, not as root, with the actual current environment:

- `XDG_RUNTIME_DIR`.
- `WAYLAND_DISPLAY`.
- `DBUS_SESSION_BUS_ADDRESS`.
- `XDG_CURRENT_DESKTOP` / desktop/session identifiers if required.
- `HOME`.
- runtime/pulse/audio environment as actually provided.
- valid `PATH` for desktop app wrappers.
- working directory if the desktop entry requires it.

Do not assume a stale hard-coded environment variable is valid after a session restart. Discover the active session/socket and validate it. Ensure GTK theme/icon runtime data is available but do not make theme errors fatal if the app can launch.

Use GIO/GDesktopAppInfo or another robust desktop-entry-aware launcher where practical, so `Exec` field quoting, field codes, D-Bus activation and desktop actions are interpreted correctly. Do not execute raw desktop `Exec` text through `shell=True`; parse/validate safely. Never accept arbitrary client-provided `Exec` strings or paths.

## 5.6 ARM64 support and truthful app availability

- Firefox: launch if actual ARM64 package/desktop entry exists and is valid. If absent, show a real install option only through a working Software backend or NuxTore package.
- VLC: same; verify package architecture, binary, dependencies and video output compatibility before advertising Installed.
- Signal: verify whether an official/maintained ARM64 Linux client exists in the installed trusted sources. Do not assume official Signal Desktop supports aarch64. If the installed item is absent or unsupported, show “Not installed / no compatible ARM64 package in configured sources” rather than a broken icon.
- Other native apps: use the same verified inventory and launcher contract.

## 5.7 App registration unification

The static JS app list must not contradict the canonical JSON registry or on-device installed app inventory. The app launcher should consume one canonical runtime registry/Bridge result (with safe cached fallback only where necessary). Preserve stable IDs and explicit PWA/native/Flatpak types.

Tests must cover a successful Wayland native app, process exit at startup, missing binary, bad desktop entry, absent D-Bus activation, unsupported architecture, service failure, invalid session environment and process already running.

---

# 6. NUXTORE — CANONICAL INSTALLED-APP DISCOVERY, INSTALL, REMOVE AND HOME ICONS

## 6.1 User-visible problem and current source truth

The user has NuxTore and SnekByte installed and has also installed or expects to see:

- Media Player (`org.nuxel.Media`)
- Media Downloader (`org.nuxel.Downloader`)
- Authenticator (`org.nuxel.Authenticator`)
- Safe Cleanup (`org.nuxel.Cleanup`)
- DevMgmt (`org.nuxel.DevMgmt`)
- PenguInterface (`org.nuxel.PenguInterface`)

Not all icons appear in Home. Some may have source files/bundles without being activated in the canonical launcher registry, or their catalog state may say Available despite their files already existing.

The local catalog resides in:

```text
pwa/nuxel-apps/nuxtore/
  js/nuxtore.js
  js/nuxtore-catalog.js
  catalog/package-sources.json
  catalog/nuxtore-catalog.json
  catalog/bundles/
```

Application source directories exist under `pwa/nuxel-apps/` and the common registry is `pwa/nuxel-common/app-registry.json`.

## 6.2 Concrete ID mismatch

Current catalog/source policy uses:

`org.nuxel.NuxTore`

while Home/common registry contains:

`org.nuxel.Nuxtore`

Application IDs are case-sensitive. Reconcile this without losing existing install records, app layout references, saved state or older catalog references.

Create one canonical ID and an explicit migration alias table for the legacy case variant. Do not create two Home icons for the same application. Preserve incoming legacy IDs during migration, then rewrite them to the canonical identity in a versioned, atomic migration.

## 6.3 Confirmed install/remove weakness

`pwa/nuxel-apps/nuxtore/js/nuxtore.js` currently:

- Loads state from localStorage key `nuxtore-state-v1` and optionally a host config key.
- Attempts an optional Bridge `apps/register` call on install.
- Treats that call as best-effort and stores install flags locally.
- Calls local catalog state changes (`Cat.applyInstall` / `Cat.applyRemove`).
- Its removal path deliberately leaves staged files and does not unregister the app from the actual launcher registry.

The Bridge currently does not expose a working canonical `apps/register` RPC route equivalent to the call expected by NuXTore. A local “installed” flag is not proof that Home knows the app or that its `start_url` exists.

`state_hint` in catalog JSON is descriptive package metadata, not runtime evidence. SnekByte's catalog state hint currently says `available`, even though SnekByte exists in the common launcher registry and has its own PWA.

## 6.4 Build a truthful installed-app inventory

The Bridge or one trusted app-registry service must combine:

1. Canonical app-registry entries.
2. Installed/staged NuxTore packages and valid manifests.
3. Existing PWA `app.json` / `manifest.json` / `index.html` paths.
4. Installed native `.desktop`/RPM app inventory (from section 5).
5. Flatpak inventory only when functional.
6. Package bundle integrity/signature/provenance records.

Expose explicit states, e.g.:

- `installed_and_launchable`
- `installed_but_disabled`
- `staged_not_registered`
- `available_local_bundle`
- `missing_files`
- `invalid_manifest`
- `signature_invalid`
- `unsupported_architecture`
- `backend_unavailable`

Do not label an app Installed because a catalog file says so or an app source directory exists. Check the actual install mode and exact start path.

## 6.5 One canonical app registry

Use a single source of truth, preferably the versioned Bridge-managed registry persisted under the system's canonical `/etc/nuxel/app-registry/app_registry.json` or another documented root-owned registry store, with a controlled service/API for mutations.

Requirements:

- Home queries this authoritative registry; `apps.js` must not maintain a conflicting handwritten subset.
- NuxTore install calls the Bridge's real authenticated install/register operation.
- Bridge validates app ID, package signature/digest, package root, manifest schema, start URL and capabilities before registration.
- Registration is atomic and preserves existing user customizations where appropriate.
- Home receives an app-registry-changed event or refreshes after install/remove.
- Launch is permitted only for registered, valid, installed app entries.
- Apps with required capabilities not granted remain correctly gated.
- Duplicate IDs and case-only duplicates are rejected or migrated explicitly.
- A bad package cannot inject `Exec`, filesystem paths, HTML/JS outside its bundle root or arbitrary bridge methods.

Do not let an unprivileged PWA write directly to `/etc` or execute package scripts as root. A narrow Bridge RPC and privileged manager own those operations.

## 6.6 Install lifecycle

Implement actual local bundle installation:

1. User taps Install.
2. Display bundle metadata, version, app ID, required capabilities, source/provenance and signature status.
3. Verify the bundle digest and Ed25519 signature using the trusted public key set. Never put a private signing key in the deployed web root or rootfs image.
4. Preserve current policy: local-bundle only; no remote fetch/publish; unsigned packages refused by default and only considered under the existing explicit manual confirmation policy.
5. Validate archive member paths; reject absolute paths, `..`, symlink escapes, duplicate/case-colliding IDs and unexpected executable permissions.
6. Stage to a temporary directory on the same filesystem.
7. Validate app manifest, start URL, required files, assets and capabilities.
8. Install atomically to the managed app directory.
9. Register the app in the canonical Bridge-managed registry.
10. Notify Home and NuXTore so the icon appears without a reboot.
11. Launch app once as an optional user action; do not auto-launch just because installation succeeded.
12. Mark Installed only after both payload and launcher registration are verified.

For existing apps already present, run reconciliation/repair rather than reinstalling over app data.

## 6.7 Remove lifecycle

- Remove launcher registration and app code only if NuXTore owns those installed files.
- Default removal preserves user data, preferences, downloaded files, authenticator secrets and other app data.
- If the user explicitly chooses “Remove app data too”, show a separate clear warning and exact affected path/size; require confirmation.
- Never remove shared libraries or other package dependencies blindly.
- Do not delete source catalog bundles when removing an installed copy.
- Remove app icon immediately from Home after successful unregistration.
- Keep the app available for reinstall from the local catalog.
- Handle app currently running: request clean exit or warn; do not kill random PIDs.
- Record uninstall result and rollback on registry update failure.

## 6.8 Ensure all listed apps are complete enough to use

Inventory each existing PWA directory:

- `pwa/nuxel-apps/snekbyte/`
- `pwa/nuxel-apps/media/`
- `pwa/nuxel-apps/downloader/`
- `pwa/nuxel-apps/authenticator/`
- `pwa/nuxel-apps/cleanup/`
- `pwa/nuxel-apps/devmgmt/`
- `pwa/nuxel-apps/penguinterface/`
- `pwa/nuxel-apps/nuxtore/`

For every app, verify:

- Valid app ID and version.
- `index.html`/entrypoint exists.
- JS/CSS/assets load under the actual hosted path.
- Manifest/icons are valid and included in image.
- Registry record exists and `start_url` matches real location.
- App has a useful working minimum feature set rather than a blank placeholder.
- Bridge calls and capabilities are actually implemented and authorized.
- It works on a 360 CSS-pixel touchscreen and software-rendered S10+ UI.

Where an app is incomplete, implement a minimum honest, functional first version rather than an empty stub:

- **Media Player:** play local audio/video with actual playback backend/output state; browse allowed media; accurate codec errors.
- **Media Downloader:** real bounded queue and downloader only when a network provider exists; validate URLs, legal-use notice, checksums, resume/error states. Do not fake downloads.
- **Authenticator:** secure encrypted TOTP storage, time correctness, backup semantics, no plaintext secret logs. This is sensitive user data; do not remove it during uninstall.
- **Safe Cleanup:** preview-only initial scan, explicit allowlist, exact reclaimable paths/sizes, confirmation before deletion; never clean arbitrary filesystem.
- **DevMgmt:** read-only system/device diagnostics by default. Privileged actions require explicit capability.
- **PenguInterface:** real device compatibility profile display, validated schema, strict profile isolation; no fake changing hardware state.
- **SnekByte:** keep existing working game and verify launcher open.
- **NuXTore:** actual install/remove/catalog state and signature/integrity flow.

If full functionality depends on another unresolved provider, show a useful status and disabled action with reason rather than a misleading button.

## 6.9 Local/offline store policy

For this mission:

- Do not connect NuXTore to a remote repository.
- Do not publish packages.
- Do not add network fetches to local package install.
- Preserve local bundles, checksums, provenance and signature verification.
- Verify the public verification key is used correctly.
- Ensure any development/private signing key is not shipped as a trust anchor. If a private key is present in source or build output, do not print it; move the signing operation offline and create a remediation note/rotation plan.
- Do not allow silent unsigned install.
- Keep the unsigned demo refusal path covered by tests.

---

# 7. NATIVE NAVIGATION DOCK ARTWORK — BACK, PENGUIN HOME, TABS

## 7.1 Active render path matters

The active S10+ dock is the native Wayland layer-shell app:

`tools/s10plus/a45/nuxel-navdock.c`

It creates an overlay-layer surface so it remains above the Phosh OSK keyboard and reserves the bottom 62 logical pixels. It draws three image arrays from `navdock-art.h`.

The generated artwork header is produced by:

`tools/s10plus/a45/gen-navdock-art.py`

The generator reads root assets:

- `assets/button-left.png`
- `assets/button-middle.png`
- `assets/button-right.png`

It currently converts each to a 48×48 logical ARGB array. The PWA fallback has separate 96×96 files under `pwa/nuxel-home/assets/`. The DOM dock may be hidden when the native dock is present; editing only DOM CSS will not fix the active phone image.

## 7.2 Diagnose the bad crop/appearance before modifying

Inspect both the original root artwork and packaged PWA copies. Record:

- Image dimensions, color mode and alpha channel.
- Alpha bounding box, transparent padding and painted bounds at multiple alpha thresholds.
- Whether one icon has a very different content scale/vertical centre from the other two.
- Whether downsampling a large source to 48px loses important silhouette/pixel detail.
- Whether content is clipped by the generated 48×48 canvas or by the Wayland surface.
- Whether the output buffer coordinates, scale factor, destination dimensions or baseline are incorrect.
- Whether premultiplied alpha is correct for `WL_SHM_FORMAT_ARGB8888`.
- Whether the dock's physical panel/output scale is actually 2 and whether the native buffer scale is consistent.
- Whether the `navdock-art.h` built into the current image matches the source files, or is stale.

Current generator comments say it creates premultiplied ARGB and `nuxel-navdock.c` uses integer nearest-neighbour upscale. Verify the implementation; do not assume an old alpha bug still exists or blindly add another premultiplication pass.

The source PNGs have very large transparent margins and non-square source dimensions. The generator uses `thumbnail((48,48))` and centres the full original canvas into a square. This may leave the painted artwork visually small or uneven even though the source file is high resolution. Use measured alpha bounds to determine if an alpha-aware crop with a small safe transparent pad is needed.

## 7.3 Required visual repair

- Keep the three original button concepts and visual identity: Back arrow, Penguin Home, Tabs/Recents.
- Make all three look like complete, intentional UI controls rather than chopped-out fragments.
- Preserve source alpha and fine edge/glow quality.
- Crop only transparent padding, never crop actual opaque artwork or glow needed for the silhouette.
- Use a consistent perceived visual size and vertical centre across all three, taking differing original aspect ratios into account.
- Avoid stretching non-square icons into squares. Contain each painted silhouette in a consistent logical safe box.
- Consider modestly increasing `NAV_ART_SIZE` from 48 only if the 62px nav height keeps clear top/bottom margins; measure before selecting a final size.
- If pixel art requires integer scale, keep exact integer nearest-neighbour upscale after the high-quality source-to-logical conversion. For smooth vector-like/glow source art, consider generating the final physical-scale art once rather than applying a poor second resampling pass; compare on device.
- Generate native `navdock-art.h` from sources; do not hand-edit header arrays.
- Update fallback PWA copies from the same normalized source artwork or create a shared generation step so native and DOM paths cannot diverge.
- Preserve Wayland premultiplied-alpha correctness. Fully transparent pixels remain transparent; partially transparent RGB is correctly premultiplied exactly once.
- Check actual button tap regions remain three equal cells and taps continue to invoke Back/Home/Recents correctly.
- Verify dock appearance above the OSK, on the home screen, during app windows and after display wake.

## 7.4 Visual acceptance

Capture the native dock from the real S10+ display at native scale and compare all three buttons. Confirm no cut silhouette, edge halo, colored fringe, inconsistent perceived size, clipped glow, black rectangular background or touch-cell mismatch. Also test fallback DOM dock in a browser with `native-nav-present` disabled.

---

# 8. NFC — PROVIDER, TOP-BAR ICON, TOGGLE AND SETTINGS TEST

## 8.1 Existing evidence and diagnostic support

The repository already has:

- `configs/nuxel/nfc/nfc.json`
- `configs/nuxel/nfc/README.md`
- `tools/s10plus/a33/nuxel-nfc-diag.sh`
- `tools/s10plus/a33/tests/hw-subsystems/test-nfc-diag.py`

The S10+ configuration identifies a Samsung `sec-nfc` / S3FWRN5-family controller at I2C address `0x27`, with possible embedded secure element. This identification is not proof the currently running kernel has a bound driver.

The diagnostic explicitly separates:

1. Controller enumeration.
2. Kernel driver/module.
3. Firmware presence/load.
4. NFC subsystem/userspace stack.
5. Physical tag read.

Possible verdicts include `READY_FOR_TAG`, `BLOCKED_KERNEL`, `BLOCKED_FIRMWARE`, `BLOCKED_EXTERNAL_RESOURCE`, `NOT_SUPPORTED_ON_DEVICE` and `PARTIAL`. A physical tag read is required for full proof.

## 8.2 Read-only preflight

Run the existing status diagnostic first and capture its output. Inspect only read-only state initially:

- I2C device enumeration and address `0x27`.
- Relevant kernel driver binding and `/proc/modules`.
- NFC character devices and sysfs class.
- Kernel config/driver availability.
- Firmware candidate presence and load errors.
- `neard`/NFC daemon and client availability.
- RF/antenna state and safe power-control interface.
- systemd units and permissions.

Do not write guessed sysfs values or load an unverified binary blob. Firmware must have valid provenance/license and match the chip/driver.

## 8.3 Implement a single NFC owner/provider

If the driver and userspace stack are functional, add a single provider/service owning NFC enable/disable and reader mode. The Settings/Home PWA calls it through authenticated Bridge APIs; JavaScript must not write I2C/sysfs/device nodes.

API should expose:

- `supported`.
- `enabled` (true/false/unknown).
- controller/driver/firmware/stack status.
- current mode (off/reader/other supported mode).
- busy/transition state.
- error/blocker code and detail.
- last physical tag test result (do not keep sensitive/payment data unless explicitly required).

State must be grounded in real provider output. A config file existing is not proof of controller support.

## 8.4 Top-bar NFC icon and toggle

- Add an NFC status glyph to the top bar using the existing status-bar safe-zone/layout system.
- Add an explicit touch toggle only when the hardware provider supports the requested state change.
- Show clear ON, OFF, UNKNOWN, unsupported, busy and error state. Do not map unknown to off.
- Avoid overlap with signal/Wi-Fi/Bluetooth/battery/USB/sound/Location icons and safe zones.
- Use one shared state provider/poll stream. Do not add duplicate frequent polls.
- Update icon after provider confirms the state, not optimistically before it does.
- If unsupported, show a diagnostics tooltip/panel and disable the toggle rather than pretending NFC is OFF.

## 8.5 Dedicated Settings NFC tab

Add a real `NFC` tab to `pwa/nuxel-apps/settings/index.html` with JS handlers and CSS. Include:

- Support/driver/firmware/stack status summary.
- Enable/disable control, only when supported.
- Refresh/diagnostics.
- Reader-mode status.
- “Test tag” action that instructs the user to place a real tag at the phone's NFC antenna location and runs a bounded real read.
- Display the read UID in a temporary diagnostic field only if appropriate; do not upload or persist arbitrary personal tag data.
- Clearly separate a successful tag UID read from payment, secure-element, card emulation or write capability. Do not claim those features unless separately implemented and tested.
- If `READY_FOR_TAG`, ask the owner to present a tag; require a second different tag to prove the reader changes UID correctly.
- When blocked, display exact blocker stage and required follow-up (kernel driver, firmware, userspace service or external tag).

## 8.6 NFC tests

- Unit fixture tests for every diagnostic verdict.
- API status and toggle tests for supported/unsupported/busy/error states.
- No UI optimistic-on state before provider success.
- State event updates top bar without duplicate poller.
- Physical tag test with known UID; second tag produces different UID.
- Verify disabled state really disables the controller only through supported provider operation.

If the shipped kernel does not expose the controller, leave hardware disabled and provide a precise blocker report. Do not flash a different kernel in this task.

---

# 9. FINGERPRINT — SECURE HARDWARE INVESTIGATION AND SETTINGS ONLY WHEN SUPPORTED

## 9.1 Important capability reality

The S10+ uses an ultrasonic under-display fingerprint sensor. This repository currently has no demonstrated fingerprint enrollment, fingerprint verification, `fprintd`/libfprint driver integration, secure template manager or verified TEE communication path. Existing string matches for “fingerprint” are unrelated to host SSH key fingerprints or boot/touch paths.

Do not treat the existence of the sensor in the phone hardware as proof Linux can access it. Secure enrollment may depend on Samsung vendor kernel interfaces, firmware and a trusted execution environment.

## 9.2 Read-only capability investigation

Inspect:

- Device tree and driver bindings for the exact S10+ sensor.
- Kernel config/modules and actual bound device nodes.
- Input/biometric subsystem interfaces.
- TEE/secure-world drivers and whether the required trusted application/secure service exists.
- Available fprintd/libfprint providers and whether any support the exact sensor.
- Logs for driver probe/firmware errors.
- Android vendor interface only as documentation/evidence; do not copy Android fingerprint templates or bypass secure-world authentication.

Do not brute-force sensor protocols or issue undocumented register writes. No raw sensor capture or template dumps.

## 9.3 Safe biometric architecture

If a supported secure provider is actually available, implement a minimal biometric broker that exposes only:

- Sensor supported/ready state.
- Whether the current user has enrolled templates.
- Opaque enrollment handles/IDs and user labels.
- Enrollment start/cancel result.
- Verification success/fail/timeout/lockout result.
- Delete enrollment action.

The provider must keep biometric templates in the secure hardware/TEE/provider-controlled storage. Nuxel must not read or export raw templates.

### “Import fingerprints” requirement — safe interpretation

Raw fingerprint templates must not be imported from Android, from a file, from a backup archive or from another device. Biometrics are not portable credentials and raw template import would defeat secure sensor enrollment and can compromise authentication.

Implement instead:

- Enroll fingerprints directly on this device through the secure provider.
- Allow multiple on-device enrollment slots with user labels (e.g. “Left index”, “Right thumb”) only as labels, not inferred identity.
- List/remove/re-enroll by opaque provider handle.
- Back up only safe enrollment metadata (slot labels, created timestamps, provider state) if desired; metadata backup must not include biometric templates or verification secrets.
- On reset/restore, require fresh on-device enrollment.

If no secure provider exists, display “Fingerprint sensor not supported by this Linux build” and keep the feature disabled. Never simulate a successful scan.

## 9.4 Fingerprint Settings tab

Add a dedicated `Fingerprint` or `Biometrics` tab containing:

- Real support/driver/TEE/provider state.
- Enrolled slot list from provider metadata only.
- Enroll new fingerprint flow with cancel and timeout.
- Remove enrollment flow with confirmation.
- Test verification flow with accurate pass/fail/timeout.
- PIN fallback status.
- Clear explanation if hardware is blocked.

No enrollment button should be enabled until a secure provider is initialized and validated.

## 9.5 Fingerprint tests

- No sensor/driver provider → unsupported, no fake enrollment.
- Provider present but TEE unavailable → blocked secure storage.
- Enroll success returns opaque ID only.
- Cancel/timeouts cleanly abort.
- Invalid scan fails without revealing template detail.
- Lockout/rate limiting works.
- Enrollment removal affects provider state.
- No raw template bytes are returned in logs/API/storage.
- PIN fallback remains functional after sensor/provider failure.
- Physical owner test on the actual device is required before claiming supported.

---

# 10. SECURITY SETTINGS AND REAL SCREEN-LOCK POLICY

## 10.1 User choices

Add a `Security` Settings tab allowing the user to select:

1. Swipe (current no-credential behavior).
2. Pattern.
3. PIN.
4. Fingerprint with mandatory PIN fallback.

The screen lock must protect the real phone session, not only cover the Home web page with a JavaScript element.

## 10.2 Security architecture

Inspect current lockscreen state in `pwa/nuxel-home/js/lockscreen.js`, host/session, PWA host, Bridge and physical key flow. Determine how the lock state is enforced across:

- Home PWA reload/restart.
- app switching and active native application windows.
- lock/unlock hardware actions.
- screen off/wake.
- native app launch requests.
- application PWA deep links.
- WebKit renderer crash/reload.
- system sleep/resume and service restart.

A secure lock implementation needs one session-level authentication owner. UI screens may collect a PIN/pattern and display feedback, but the credential verifier and authoritative locked/unlocked state must not live solely in browser JavaScript/localStorage.

Protect all app surfaces behind the session lock or compositor/session-level layer. When locked, prevent launch/open requests from displaying protected app contents until the host authorizes unlock. Ensure the lockscreen remains on top through native app transitions or block app surfaces until unlock.

## 10.3 Credential storage

- Do not store PIN/pattern in plain text, localStorage, app config JSON, logs, URLs or crash dumps.
- Use a vetted password hashing/KDF implementation already available in the OS, preferably Argon2id or scrypt with per-credential random salt and appropriate cost; use PBKDF2 only if no suitable alternative and document the choice.
- Never invent a custom cryptographic hash scheme.
- Compare derived verifiers in constant time.
- Lock file/credential state to the intended service user/root, mode 0600 or stricter as appropriate; use atomic writes and safe backups.
- Keep key material out of PWA/static assets and service logs.
- Do not reuse Bluetooth/SSH/account credentials as device lock secrets.

## 10.4 PIN policy

- Minimum PIN length appropriate to device policy (recommend at least 6 digits; allow longer alphanumeric passcode if supported).
- Reject trivial sequences/repeats or at minimum warn.
- Use a secure keypad with randomized layout only if it does not make accessibility unusable; never log pressed digits.
- Rate-limit wrong attempts with increasing delays and a persistent lockout counter that does not reset simply by restarting Home.
- Make fallback reachable during fingerprint failure.
- Do not leak whether a specific PIN prefix/credential is correct.
- Support deliberate credential change with old credential verification unless an authorized recovery procedure is used.

## 10.5 Pattern policy

- Pattern must have minimum complexity/points and reject trivial patterns.
- Convert the pattern to a derived verifier with a salted KDF; do not store raw pattern path.
- Provide accessible fallback and a clearly offered PIN alternative.
- Do not allow a pattern that is trivially bypassed by UI state or direct route navigation.

## 10.6 Fingerprint selection and fallback

Fingerprint selection is allowed only if:

- The secure fingerprint provider reports supported and ready.
- At least one enrollment has completed successfully.
- A PIN fallback has been configured and verified.

If the sensor fails, driver stops, TEE is unavailable, the user has not enrolled, or verification times out, show PIN fallback. Never fall back automatically to Swipe. Fingerprint must not become the only credential.

## 10.7 Swipe/current behavior

- Preserve current swipe-only behavior as a configurable choice.
- Make selecting Swipe an explicit action that confirms removal of the current credential and shows the security consequence.
- Do not silently downgrade from PIN/Pattern/Fingerprint to Swipe after provider failure.

## 10.8 Security Settings UI

Add a Security tab with:

- Current screen-lock method/status.
- Choose Swipe/Pattern/PIN/Fingerprint.
- Set/change PIN.
- Set/change Pattern.
- Configure fingerprint only when secure provider exists.
- Confirm PIN fallback when selecting Fingerprint.
- Test current lock method.
- Rate-limit/lockout status without exposing secret values.
- Clear note about unavailable hardware features.

All changes should be persisted by the secure lock manager with an atomic versioned config, not a browser preference alone.

## 10.9 Security regression tests

- Direct PWA URL while locked remains blocked.
- Native app launch while locked remains blocked.
- Home renderer reload while locked does not unlock.
- Wrong PIN/pattern does not unlock; repeated failures trigger persistent backoff.
- Correct credential unlocks the session.
- Fingerprint failure/timeout correctly prompts PIN.
- PIN fallback works when fingerprint daemon is unavailable.
- Fingerprint cannot be enabled without enrollment and tested PIN fallback.
- Credential change requires authentication.
- No secrets in logs/browser storage/URLs.
- Lock persists across Home restart, host restart and device reboot.
- Swipe mode works only after an explicit policy change.

---

# 11. DND — IMPLEMENT SYSTEM-WIDE DO NOT DISTURB

## 11.1 Existing missing implementation

`pwa/nuxel-home/js/qs.js` includes a DND tile in its registration list but `_toggle()` currently has no DND implementation. It falls through to the generic unavailable response. The initial JS state includes `dnd:false` but does not have an authoritative provider.

`services/nuxel-notifications` runs a custom D-Bus notification service with notification history/storage. It currently supports notification delivery/listing but does not implement a complete persistent DND policy. The haptics bridge has quiet-hours data, but quiet hours for haptics are not the same as full system Do Not Disturb.

## 11.2 Implement one persistent DND manager

Add a system-owned persistent DND policy/provider and Bridge API. Define a stable config/schema, e.g. `/etc/nuxel/notifications/dnd.json` for default policy and a safe state store under `/var/lib/nuxel/notifications/` for current/scheduled state.

The single DND state must be consumed by:

- Nuxel custom notification daemon.
- Desktop notification/popup surfaces.
- Sound/audio notification path.
- Haptics notifications.
- LED notification path.
- Lock-screen notification badges/history where relevant.

DND should normally suppress interruption, not destroy incoming notifications. Keep notifications in history and mark them as silenced/suppressed with reason.

## 11.3 Policy semantics

Minimum controls:

- DND On/Off.
- Optional schedule/quiet hours.
- Optional critical/alarm/emergency exceptions, with explicitly defined priority levels.
- Optional whether incoming calls/alarms may bypass DND if those providers exist.
- Optional visual badge-only notification behavior.

When active:

- Suppress ordinary notification popups.
- Suppress notification sounds.
- Suppress notification haptics.
- Suppress notification LED/edge-light effects, except explicitly allowed priority notifications.
- Keep notification records/history, counters and app IDs.
- Do not suppress alarms/emergency alerts unless the owner explicitly configures that behavior and understands the consequence.

Be explicit about what DND controls and what it does not. DND should not disable radio hardware or prevent a message from being received.

## 11.4 Quick Settings and Settings

- Replace generic unavailable handling with `dnd.get-status` / `dnd.set-enabled` or a consistent equivalent Bridge contract.
- Update QS toggle only after backend acknowledgement.
- Refresh actual state on open; subscribe to change events or bounded poll while visible.
- Do not keep duplicate pollers alive while QS is closed.
- Add a Notifications/Do Not Disturb section in Settings with enable, schedule and priority exceptions.
- Show whether DND is currently active because of manual toggle or schedule.
- Handle unknown provider state as UNKNOWN rather than false/off.

## 11.5 Tests

- DND on/off persisted across restart.
- Scheduled activation/deactivation and timezone change.
- Normal notification stored but popup/sound/haptic/LED suppressed.
- Critical notification exception behaves as configured.
- DND toggle state syncs across Quick Settings and Settings.
- Bridge unavailable does not paint a fake OFF state.
- DND disable restores ordinary delivery without replaying a storm of stale popups.
- Notification history remains intact.

---

# 12. FLASHLIGHT — REAL HARDWARE OWNER AND POLICY-COMPLIANT TOGGLE

## 12.1 Existing state and why the tile is blocked

`pwa/nuxel-home/js/qs.js` contains a flashlight tile but `_toggle()` currently falls through to an unavailable message. The hardware side has an explicit LED/torch policy in `configs/nuxel/leds/leds.json` and diagnostic helper `tools/s10plus/a33/nuxel-led-diag.sh`.

The LED policy records:

- Rear camera flash/torch candidates under `/sys/class/leds`.
- `max_on_ms:60000`.
- `require_explicit_yes:true`.
- `auto_on_boot:false`.
- `off_on_exit:true`.
- State file `/var/lib/nuxel/leds/state.json`.

The policy warning “bounded by LED policy” is intentional protection. Do not remove the bound. Implement the approved controlled action.

## 12.2 One torch owner

There must be one privileged provider/service owning the camera flash LED. PWA JavaScript must never write directly to sysfs or call arbitrary shell.

First discover:

- Actual `/sys/class/leds` classes and candidate path.
- Real `brightness`, `max_brightness`, `flash_strobe` support.
- Whether the kernel driver exposes a torch mode or only strobe/flash.
- Existing camera application/service ownership and arbitration.
- Whether a camera is recording or using flash.
- Battery/thermal constraints and time limits.
- Permission model and cleanup path.

Then implement one provider endpoint that owns ON/OFF and state. Reuse or safely extend the existing LED diagnostic/policy implementation. If a native camera/PMIC driver owns torch, use its supported control interface.

## 12.3 Required behavior

- OFF is safe default and explicit at service start/exit.
- Require an authenticated owner request to turn ON.
- Enforce max 60 seconds or stricter canonical policy value.
- Schedule an automatic OFF and use a monotonic clock.
- Always turn OFF on timeout, service crash, shutdown, lost ownership or error.
- Respect camera busy state and do not compete with a capture/flash sequence.
- Enforce thermal/battery limits where supported.
- Repeated ON requests do not extend timeout indefinitely unless policy explicitly allows a bounded extension.
- No torch auto-enable on boot.
- Return actual provider state and reason: OFF, ON, UNKNOWN, UNSUPPORTED, BLOCKED_CAMERA, THERMAL_LIMIT, POLICY_DENIED or ERROR.
- The UI displays “ON” only after provider acknowledges actual output.

## 12.4 Quick Settings and button integration

- Implement QS `flashlight.get-status` and `flashlight.set-enabled` (or matching established contract).
- Replace generic “unavailable” branch only when provider is installed and capability is true.
- Wire the existing physical button shortcut only through the same owner; do not maintain a second code path.
- Keep UI responsive with in-flight request locking and backend error handling.
- Turning ON in QS and OFF from the physical button must update all surfaces.
- If hardware path is absent, tile shows unsupported with diagnostic reason and never shows ON.

## 12.5 Tests and hardware proof

- No LED class → unsupported/refused.
- Existing LED but not writable → permission/driver error.
- Valid LED → bounded ON, explicit OFF.
- Max-on timeout forces OFF.
- Service stop/crash/shutdown cleanup.
- Camera busy blocks torch.
- Thermal/battery block behavior.
- Concurrent requests and race tests.
- Physical brief torch ON, visibly verify light, then OFF.

Do not mark the physical flashlight solved based only on a fixture test or a request file.

---

# 13. COLORED LED NOTIFICATIONS — RED/GREEN/BLUE AND SAFE DISPLAY FALLBACK

## 13.1 Existing policy

`configs/nuxel/leds/leds.json` describes three distinct concepts:

1. Rear flashlight/torch (camera/PMIC LED; not for notifications).
2. Front notification LED, if the running kernel binds a usable class.
3. AMOLED edge-lighting, which is a software display overlay, not a separate hardware LED.

Notification class candidates include:

- `/sys/class/leds/led:notification`
- `/sys/class/leds/notification`
- `/sys/class/leds/led:rgb`
- `/sys/class/leds/sec_led`
- `/sys/class/leds/led:red`
- `/sys/class/leds/led:green`
- `/sys/class/leds/led:blue`

The config's intended channel mapping is red → `led:red`, green → `led:green`, blue → `led:blue`.

The current diagnostic helper has a `notify` command, but audit its actual implementation: a generic `brightness=255` toggle is not enough to implement color selection for separate RGB channels. The implementation must drive the channel(s) that correspond to the requested color.

## 13.2 Discover hardware accurately

- Enumerate LED class names, triggers, brightness, max_brightness, blink/delay files, device symlinks and driver ownership.
- Determine whether a class is a true RGB LED, one single-color LED, camera flash or unrelated indicator.
- Determine channel polarity/range and whether `brightness` accepts integer values.
- Check whether multiple channels share a single controller that must not be driven concurrently by separate processes.
- Do not infer color capability merely because a class name contains `rgb`.
- Never use the rear torch LED as a notification LED unless an explicitly safe, intended driver path supports low-power use and the owner policy permits it.

## 13.3 One LED notification owner

Implement a single notification-light service/provider with:

- Set color, duration/blink pattern and priority.
- Clear/off.
- Read status/capability.
- DND suppression/priority integration.
- Preemption and restoration of prior state.
- Safe-off on service stop/restart and timeout.
- Bounded max duration and low notification brightness.
- Per-channel correct max brightness scaling.
- Explicit cleanup of every RGB channel, including channels that were not selected.

Suggested color semantics:

- Red: red channel only.
- Green: green only.
- Blue: blue only.
- Yellow/amber: red + green at a calibrated lower level if hardware supports mixing.
- Cyan: green + blue.
- Magenta: red + blue.
- White: all three only if the actual LED hardware supports mixing and heat/power policy allows it.

These are requested colors, not proof the hardware can render them. Report only tested colors as supported.

## 13.4 Notification integration

Integrate with the Nuxel notification daemon/provider rather than having each app write LEDs. Map app/category/priority to colors through a configurable policy. DND rules apply before the LED is activated. When notification is dismissed/cleared or the duration expires, reset all channels.

## 13.5 Software edge-light fallback

If no true front notification LED exists, the S10+ config explicitly models edge lighting as a display overlay via the display bridge `nuxel-wl-fb` command channel. It must be described as `display_edge_lighting`, not a hardware LED.

Only implement this fallback if the existing display owner has a safe, bounded overlay/notification mechanism. Do not let the notifier become a second `/dev/fb0` writer. Send a narrow command to the single display owner and have it render/dismiss a bounded software edge effect. It must stop when:

- Notification expires/dismisses.
- DND suppresses it.
- Screen/session state makes it inappropriate.
- Display bridge is unavailable.

No direct framebuffer access from PWA or LED daemon.

## 13.6 UI and tests

- Add color test controls in Settings/Developer or Notifications Settings, with clear “Test red/green/blue” buttons and bounded duration.
- Do not expose a camera torch test here.
- Show physical LED capability separately from edge-light fallback.
- Test each real RGB channel individually, all supported mixtures, OFF cleanup, timeouts, DND behavior, concurrent notification priority and service restart.
- Physical owner visually verifies each color. If no front LED class exists, use and label the display overlay only when proven.

---

# 14. SETTINGS INFORMATION ARCHITECTURE

Existing Settings is a PWA with tabs in `pwa/nuxel-apps/settings/index.html`, tab routing in `settings.js` and hardware provider helpers in `hardware-settings.js`.

Existing tabs currently include Screen, Bluetooth, Displays, Wi-Fi, Sound, Buttons & Gestures, Location & Maps, Power and Developer.

Add distinct, properly implemented panels:

- **NFC** — provider/controller/firmware/stack state, enable/disable, reader test.
- **Fingerprint / Biometrics** — secure provider state, on-device enrollment/deletion, verification test and PIN-fallback state; disabled with explicit blocker when unsupported.
- **Security** — choose Swipe/Pattern/PIN/Fingerprint+PIN fallback and manage credentials through the lock manager.
- **Notifications / DND** — DND toggle, schedule, exception policy, notification LED/edge-light color policy/test.
- **Software** — may launch the native GNOME Software app or provide a true integration link; do not create a duplicate fake package-manager surface.

Requirements:

- Use the existing Settings tab routing and style system.
- Each panel has real provider state, loading, unavailable, error and success states.
- Do not enable controls before provider capability is verified.
- Keep touch sizes and vertical scrolling appropriate for the S10+ viewport.
- Avoid loading all diagnostics synchronously on initial Settings open; load each provider on tab selection and cancel stale requests when leaving.
- Do not keep multiple pollers active after the panel is hidden.
- Add cache/version updates for the Settings PWA.

---

# 15. TOP-BAR NFC STATUS AND SHARED INDICATOR ARCHITECTURE

The requested NFC icon belongs in the Home top bar. Inspect the existing status-bar layout/safe zones and its provider contract before adding the new item.

- Add a stable NFC icon element and accessible label.
- Use the same NFC Bridge state provider as NFC Settings.
- Distinguish enabled, disabled, unknown, transitioning, blocked and unsupported.
- Toggle only through the privileged provider; no sysfs writes in JS.
- Do not display NFC active until the provider confirms it.
- Avoid collision with Location, sound mode, battery, signal, Wi-Fi, Bluetooth, USB and other existing indicators.
- Update status bar safe-zone/overlap assertions and 360 CSS-pixel viewport tests.
- Ensure lockscreen/top-bar/Settings do not create separate conflicting state caches.

---

# 16. SECURITY AND DATA PRESERVATION REQUIREMENTS

This mission adds package installation, hardware control and credential handling. Preserve strict privilege boundaries.

## 16.1 Privileged actions

- PWA calls a typed Bridge method.
- Bridge validates schema, origin/session, capability and arguments.
- Privileged service executes a fixed action through a constrained API.
- Never accept arbitrary shell commands/paths from the UI.
- Use argument arrays, `shell=False`, fixed helper paths, bounded timeouts and explicit user confirmation.
- Log action IDs and outcomes, not passwords, authenticator secrets, file contents or biometric data.
- Root-owned service/config must have correct restrictive modes.

## 16.2 Package management and app bundles

- Verify repository/bundle signatures and metadata.
- Never disable GPG/signature verification for convenience.
- Preserve NuxTore's offline-only scope and unsigned-package refusal.
- Use atomic staging and rollback on failed registration.
- Remove only app-owned code/registration; preserve user data by default.
- Never expose private signing keys in the deployed image or PWA webroot.

## 16.3 Credential and biometric handling

- Use a vetted KDF for PIN/pattern verifier.
- No plaintext secrets in JSON/localStorage/browser logs.
- Biometric templates remain inside secure sensor/TEE provider.
- No raw template import/export or template dumps.
- Fingerprint enable requires verified PIN fallback.
- Persist lockout/rate-limit state across Home restarts.

## 16.4 USB and LEDs

- Preserve CDC-ACM console.
- No USB raw mass storage exposure of the live root/home filesystem.
- No UDC teardown without rollback.
- No torch use outside configured limits.
- No notification service writing to camera flash path.
- No second framebuffer writer for edge lighting.

## 16.5 No bootloader/kernel flashing

This is a userspace integration mission. Do not use Heimdall, Odin, fastboot, Recovery, Download Mode, block device writes, `dd`, sysrq reboot or forced reset. If NFC/fingerprint/Flatpak/MTP support needs a different kernel, report the precise build requirement as a separate future kernel task. Do not flash it now.

---

# 17. REQUIRED SOURCE CHANGES AND BUILD INTEGRATION

The agent must inspect and update, where relevant:

```text
pwa/nuxel-home/index.html
pwa/nuxel-home/js/lockscreen-indicators.js
pwa/nuxel-home/js/status-bar.js
pwa/nuxel-home/js/qs.js
pwa/nuxel-home/js/apps.js
pwa/nuxel-home/js/app.js
pwa/nuxel-home/css/lockscreen.css
pwa/nuxel-home/css/status-bar.css
pwa/nuxel-home/assets/

pwa/nuxel-apps/settings/index.html
pwa/nuxel-apps/settings/settings.js
pwa/nuxel-apps/settings/hardware-settings.js
pwa/nuxel-apps/settings/settings.css

pwa/nuxel-apps/nuxtore/
pwa/nuxel-apps/{snekbyte,media,downloader,authenticator,cleanup,devmgmt,penguinterface}/
pwa/nuxel-common/app-registry.json

services/nuxel-bridge/src/api.py
services/nuxel-bridge/src/bridge.py
services/nuxel-bridge/src/hw_providers.py
services/nuxel-bridge/src/system_indicators.py
services/nuxel-notifications/src/notifications.py
services/nuxel-s10/bin/nuxel-usb-mode.sh
services/nuxel-session/systemd/

configs/nuxel/nfc/nfc.json
configs/nuxel/leds/leds.json
configs/nuxel/app-registry/
configs/nuxel/notifications/
configs/nuxel/security/

assets/button-left.png
assets/button-middle.png
assets/button-right.png
tools/s10plus/a45/gen-navdock-art.py
tools/s10plus/a45/navdock-art.h (generated)
tools/s10plus/a45/nuxel-navdock.c

images/s10plus/build-phone-rootfs-inside-fedora.sh
images/s10plus/packages-manifest.json
```

The list is a guide, not an instruction to edit every file. Follow the actual active build path and avoid duplicate implementations.

For new units/provider services:

- Add source and tests.
- Add unit, config and package dependencies to the rootfs builder.
- Set correct user/group and systemd hardening options where compatible.
- Add bounded restart behavior and clean shutdown/off.
- Confirm a service failure produces an UNKNOWN/unsupported UI state, not an ON state.
- Add image verification to ensure the unit, helper and config are present.

For modified PWAs:

- Update service-worker cache versions and manifests according to project conventions.
- Ensure assets are included and the exact current image serves the updated files.
- Avoid duplicate registry lists and stale app manifests.

---

# 18. TEST STRATEGY AND EXPECTED REGRESSION SUITES

## 18.1 Baseline suites

Run the existing relevant tests before and after changes. Inspect current script names first; do not assume an A33 test validates an A45/native build. At minimum run the existing NFC and LED diagnostic unit tests and the project’s app registry/package verification suites:

```bash
python3 tools/s10plus/a33/tests/hw-subsystems/test-nfc-diag.py
python3 tools/s10plus/a33/tests/hw-subsystems/test-led-diag.py
```

Also run all relevant NuxTore/catalog/bundle verification, app-registry, Bridge, notification, settings, Quick Settings, native host and rootfs build tests that exist in this checked-out repository.

## 18.2 New USB tests

- Capability preflight for configfs/FunctionFS/MTP.
- No UDC and no supported MTP kernel function.
- Responder missing and startup timeout.
- UDC bind/unbind failure rollback.
- Preserve CDC-ACM.
- Active state only after real enumeration/session.
- Host detach clears active state.
- Allowed roots and symlink traversal.
- MTP file copy hashes.

## 18.3 Software manager tests

- Package manager unavailable.
- Native RPM backend ready.
- Polkit agent visible/authorized/denied.
- Signed package/repo required.
- Cancellation, network failure, dependency conflict and insufficient disk.
- Flatpak user namespace missing and sandbox refuse path.
- With a supported test kernel/runtime, a sample ARM64 Flatpak launches confined and cannot access forbidden paths.

## 18.4 Native app launch tests

- App registry resolution.
- Desktop entry parsing with field codes and DBus activation.
- Correct Wayland/D-Bus user session.
- Missing binary.
- Wrong architecture.
- Process exits early.
- Surface/visible window success.
- Firefox/VLC actual installed state.
- Signal absent/unsupported state does not show broken launch.
- Bridge returns actionable error details.

## 18.5 NuxTore tests

- Canonical ID and legacy case alias migration.
- SnekByte and NuxTore recognized as installed from real registry/files.
- Catalog `state_hint` cannot override runtime reality.
- Install verifies hash/signature/provenance and start path.
- Atomic staging and Bridge registration.
- Home icon appears without reboot.
- Launch registered app works.
- Remove unregisters and removes owned code only.
- User data retained by default.
- Reinstall works from local bundle.
- Unsigned demo refused by default.
- Zip path traversal, symlink escape, duplicate ID and bad signature refused.

## 18.6 Navigation art tests

- Generator succeeds from root assets.
- Correct 48/selected logical size output.
- ARGB channel values premultiplied once.
- Transparent pixels do not overwrite the Wayland buffer.
- Source content alpha bounds preserved.
- Three icons visually aligned and not cropped.
- Native and fallback copies remain consistent.
- C build includes regenerated header.

## 18.7 NFC tests

- Every diagnostic verdict.
- Provider unavailable/unknown/error.
- Toggle success/failure.
- Settings refresh and top bar state.
- Physical first and second tag read.

## 18.8 Fingerprint/Security tests

- No fingerprint provider → unsupported and disabled.
- Fake/mocked secure provider only for unit tests, never claimed as physical success.
- Enrollment creates opaque metadata only.
- No template bytes returned/logged.
- PIN KDF, salt, permissions and lockout tests.
- Swipe/Pattern/PIN flow.
- Fingerprint requires real enrollment and PIN fallback.
- Wrong auth attempts/rate limit survive restart.
- Locked native/PWA routes cannot bypass the lock.

## 18.9 DND/LED/Flashlight tests

- DND state persistence and notification suppression.
- Critical notification exceptions.
- Notification history retained.
- Flashlight unsupported/block, ON/OFF, timeout, camera busy and cleanup.
- LED channel mapping red/green/blue and tested color mixtures.
- All notification channels forced OFF after timeout/restart.
- DND suppresses LED/haptics/popups/sound as configured.
- Display-overlay fallback uses one display owner only.

---

# 19. PHYSICAL S10+ ACCEPTANCE PLAN

Perform only when the already-configured SSH and physical handset are available. Never infer physical hardware success from a mock or shell fixture.

## 19.1 Lockscreen

- Lock and observe primary order: Charging (if active), Live Console (middle), USB PC.
- Enable Serial/USB/WLAN/file-transfer combinations and confirm secondary icons are slightly lower and larger, readable, not overlapping.
- Verify connection mode selector and lockhead remain accessible.

## 19.2 USB MTP

- Use a known-good USB data cable and a real computer.
- Select File Transfer.
- Confirm a new MTP/portable device appears on the computer.
- Open only intended shared folders.
- Copy file phone → computer and computer → phone; compare SHA-256.
- Confirm USB console CDC-ACM remains usable if composite mode is supported.
- Disconnect/reconnect and confirm active labels clear/reappear accurately.
- Confirm no mass-storage LUN exports the root/home filesystem.

## 19.3 Software app

- Open native Software UI.
- Browse/search app metadata.
- Preview one safe test package transaction.
- Confirm polkit prompt appears and denial cancels cleanly.
- Install one harmless native GTK app from a verified configured repo only with owner authorization.
- Launch it visibly.
- Check Flatpak status; if kernel user namespaces are unavailable, confirm Flatpak stays disabled with the exact blocker.

## 19.4 Native app launch

- Launch each installed supported app from Home.
- Confirm Firefox/VLC window actually appears, can receive touch input and returns to Home correctly.
- Confirm unsupported/missing apps explain why and do not spin forever.
- Confirm logs show start/surface/error stage without secrets.

## 19.5 NuXTore

- Open NuXTore and confirm it detects its own installed state and SnekByte.
- Confirm Media Player, Downloader, Authenticator, Safe Cleanup, DevMgmt and PenguInterface accurately show installed/staged/available state.
- Install one local bundle, confirm Home icon appears and app opens.
- Remove it, confirm icon disappears but user data remains.
- Reinstall from local bundle.
- Verify no external network fetch occurs.

## 19.6 Native navigation dock

- Capture actual dock with all three images on physical panel.
- Inspect Back, Penguin Home and Tabs at normal viewing distance.
- Verify art has complete silhouette/alpha, no clipping or black background and consistent sizing.
- Verify touch actions still work.
- Open OSK and ensure dock remains above keyboard.

## 19.7 NFC

- Run status diagnostic.
- If READY_FOR_TAG, use a real known NFC tag and compare UID.
- Read a second different tag and confirm different UID.
- Toggle NFC off/on through the provider and ensure state changes.
- If unsupported, confirm the UI accurately shows blocker and does not claim NFC enabled.

## 19.8 Fingerprint and lock security

- Only if secure provider reports supported and ready: enroll a real finger on the handset, perform test verification and confirm opaque enrollment metadata only.
- Configure and verify PIN fallback before enabling fingerprint as screen-lock method.
- Lock and unlock with configured method.
- Test wrong PIN/pattern, lockout, fingerprint failure and PIN fallback.
- Reboot/restart Home and confirm lock remains enforced.
- If hardware provider is unsupported, verify Fingerprint is disabled and PIN/Pattern lock still work.

## 19.9 DND and flashlight

- Turn DND on in QS; send a normal test notification and confirm history records it while popup/sound/haptics/LED are suppressed.
- Test any configured critical exception.
- Turn DND off and verify normal delivery resumes.
- Turn flashlight on briefly only if supported, visibly confirm light, then turn it off. Verify auto-off bound.
- Confirm camera busy/unsupported path refuses safely.

## 19.10 Colored notification LED

- Test red, green and blue separately; then test supported mixtures.
- Confirm correct color, bounded duration and clean OFF after each test.
- Trigger a real notification and verify configured color mapping.
- Turn DND on and confirm LED is suppressed.
- If there is no physical notification LED class, verify the explicit software edge-lighting path and label it display effect, not hardware LED.

---

# 20. DEPLOYMENT, ROLLBACK AND DATA SAFETY

## 20.1 Before deployment

- Verify git status/branch and create a checkpoint/commit.
- Back up modified live binaries, units and configs before replacement.
- Back up the app registry and NuxTore installed-state metadata.
- Preserve app data, media, authenticator encrypted data, settings, credentials and saved layouts.
- Record current service versions, hashes, ownership, permissions and SELinux labels if applicable.
- Record current USB gadget config so safe rollback is deterministic.
- Record current UDC and CDC-ACM state.
- Record current lock policy before changing it.
- Keep the SSH/network route active throughout deployment.

## 20.2 Deployment

- Build ARM64 artifacts from the repository's real build scripts.
- Verify hashes and file architecture before transfer.
- Stage updated binaries/assets/configs/units before atomic replacement.
- Restart only the specific services affected.
- Do not stop the network/SSH path.
- Do not reboot simply to claim completion.
- If a reboot is required, use the existing safe user-space process and only when the owner explicitly approves; never bypass any existing reboot gate.
- For USB gadget testing, preserve a recovery path if the serial interface is temporarily unavailable.

## 20.3 Rollback

Document exact rollback order for:

- Bridge/API changes.
- USB gadget/MTP service and previous CDC-ACM config.
- Native application registry.
- NuxTore state migrations.
- Software manager/polkit integration.
- NFC provider/unit.
- Fingerprint/security lock service (must not strand the owner outside the device; retain recovery through verified PIN).
- DND/notification/LED provider.
- Native dock artwork and generated header.

Never roll back by deleting user app data or credentials.

---

# 21. REQUIRED DELIVERABLES

Create/update:

1. `docs/beta-finalization/live/PWNAGE-45000-TODO.md` — each feature, code owner, status, blocker, test and evidence path.
2. `docs/beta-finalization/live/evidence/pwnage-45000/` — baseline, test output, device screenshots, USB host enumeration/copy hashes, package/launch logs, NFC/LED/fingerprint physical proofs where supported and deployment record.
3. Actual source changes in active PWA, Bridge, system services, native dock artwork generator, assets, config and image builder.
4. New tests for all API/UI/backend/provider contracts and active build paths.
5. Updated app catalog/registry schema and safe migration, with no case-only duplicate IDs.
6. Updated PWA cache versions and rootfs package/systemd integration.
7. Deployment/rollback instructions with exact installed paths and hashes.
8. Final report including:
   - Confirmed cause per issue.
   - Source files changed.
   - What now works on target device.
   - Test commands and exact PASS/FAIL/SKIP counts.
   - USB MTP host enumeration and copy evidence.
   - Package-manager and Flatpak readiness results.
   - Native app launch inventory, including Signal support truth.
   - NuxTore install/remove evidence.
   - NFC/fingerprint hardware verdicts.
   - DND/torch/LED physical behavior.
   - Any `BLOCKED_KERNEL`, `BLOCKED_FIRMWARE`, `NOT_SUPPORTED_ON_DEVICE` or `NEEDS_OWNER_TEST` items.
   - Exact deployment and rollback commands.

If a full drop-in source archive is produced, verify its contents, exclude caches/venvs/object files/secrets/private signing keys, and ensure it includes every required source/config/test/build file. Do not call a source-only archive a ready-to-flash image.

---

# 22. FINAL DEFINITION OF DONE

## Lockscreen and visual polish

- [ ] Primary status row is Charging → Live Console → USB-connected PC.
- [ ] Console transport penguins are visibly slightly lower and larger/readable.
- [ ] No overlap/crop on the portrait S10+ display or short landscape diagnostic viewport.
- [ ] Native Back/Home/Tabs art is complete, consistent and polished; fallback DOM dock matches.

## USB and Software

- [ ] File Transfer enumerates as a real MTP device on a physical computer.
- [ ] Actual bidirectional file copy succeeds with hash verification.
- [ ] Existing USB console is retained or any unavoidable limitation has a controlled, explicit switch/fallback.
- [ ] No mass-storage export of live root/home.
- [ ] Native Software app is installed and can preview/authorize/manage a real native GTK/RPM transaction.
- [ ] Flatpak only reports working after user namespace, Bubblewrap, portals and a real ARM64 sandbox app all pass; otherwise it is explicitly blocked.

## Apps and NuXTore

- [ ] Firefox/VLC supported installed apps launch visible windows.
- [ ] Signal is shown as available only if actual ARM64 package/desktop entry is installed and launchable.
- [ ] Launch errors are actionable; no silent no-op.
- [ ] NuXTore's app identity is canonicalized safely.
- [ ] NuxTore and SnekByte recognition matches real installed state.
- [ ] Media, Downloader, Authenticator, Cleanup, DevMgmt and PenguInterface have working registered entries or a clearly documented blocker.
- [ ] Install registers app and produces Home icon without reboot.
- [ ] Remove unregisters app and preserves user data by default.
- [ ] Local-only signature/hash/provenance rules remain enforced.

## NFC and fingerprint/security

- [ ] NFC icon, toggle and Settings panel reflect real provider state; tag test passes physically if supported.
- [ ] Fingerprint status/enrollment/test is secure and physical only if the actual provider/TEE supports it.
- [ ] Raw biometric templates are never imported/exported/stored in normal app storage.
- [ ] Security tab offers Swipe, Pattern, PIN and Fingerprint+PIN fallback where supported.
- [ ] Actual lock session prevents PWA/native bypass, persists across restarts and uses secure KDF/rate limiting.
- [ ] PIN fallback remains available whenever fingerprint is selected.

## DND, flashlight and colored LED

- [ ] DND persists, controls notifications across popup/sound/haptic/LED and preserves history.
- [ ] Flashlight works through one hardware owner within 60-second policy or is clearly unsupported/refused.
- [ ] Red/green/blue notification channels map to correct physical colors where available.
- [ ] All notification LEDs turn off after clear/timeout/restart and DND suppresses them.
- [ ] Display edge lighting, if used, is explicitly labelled a display effect and uses only the single display owner.

## Quality and delivery

- [ ] Tests cover actual active image/service paths, not only stale source generations.
- [ ] Clean ARM64 rootfs build includes all needed binaries, configs and services.
- [ ] Physical device checks are documented; no fixture test is presented as physical proof.
- [ ] Existing user data, app data, authenticator secrets, security credentials and SSH remain intact.
- [ ] No raw partition/bootloader operations or weakened sandbox/security controls occurred.
- [ ] Final TODO, evidence, blocker matrix, deployment notes and rollback procedure are complete.

**PWNAGE-45000 is complete only when each working feature is backed by a real source path and test, each hardware feature is physically verified where possible, and every unsupported dependency is reported honestly. No fake green state, no mock implementation masquerading as hardware, and no “installed” label without a launchable app.**

🐧 **NUXEL — REAL DEVICES. REAL APPS. REAL CONTROL.**

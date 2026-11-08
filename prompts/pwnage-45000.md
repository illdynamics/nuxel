# PWNAGE-45000 — NUXEL DEVICE INTEGRATION KICKSTARTER

**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel, custom Fedora-based ARM64 Linux  
**UI:** `pwa/nuxel-home`, Settings and app PWAs  
**Hardware/service layer:** Nuxel Bridge, systemd session services, S10+ native helpers  
**Store policy:** Local/offline NuxTore bundles for this mission; no repository/network publishing yet

## MISSION

Implement the following end-to-end in the actual source and active S10+ image. Do not stop at a UI mockup, capability claim or written audit.

1. **Lockscreen indicators:** reorder the primary status art to Charging → Live Console → USB connected, so the Live Console penguin is in the middle. Move the secondary Serial/USB/WLAN/File Transfer transport-penguin row slightly lower and make those icons modestly larger and easier to read. Preserve responsive layout and avoid overlap with the clock, lockhead and connection-mode controls.
2. **USB File Transfer:** selecting File Transfer currently does not enumerate an MTP device on the computer. Complete a real USB MTP gadget/responder path while preserving the existing USB CDC-ACM console. Never substitute USB mass storage or export the mounted Nuxel root/home filesystem as a raw disk. Detect the actual kernel/configfs/FunctionFS capabilities, build and package a compatible MTP responder, activate the composite gadget safely, report `active` only after real endpoint/session evidence, and physically verify host enumeration and file transfer.
3. **Software app:** add a real native GTK software center (prefer GNOME Software if its dependencies and ARM64 package availability are verified) for installing/removing native Fedora RPM/GTK applications through a supported PackageKit/DNF backend with polkit authorization. Add Flatpak UI/backend only if the current S10+ kernel genuinely supports Flatpak's sandbox prerequisites. Existing repository evidence says `CONFIG_USER_NS` is missing and `unshare -U` fails; do not bypass this with weakened sandboxing. The UI must distinguish native RPM support from blocked Flatpak support.
4. **Native app launching:** diagnose why Firefox, VLC, Signal and other native apps sometimes appear to launch but show no window. Inspect actual installed packages, desktop entries, binaries, D-Bus activation, session environment and host launch logs. Make the real installed desktop applications launch visibly and report errors honestly. Do not create launch buttons for packages that are absent or unsupported on ARM64.
5. **NuXTore:** reconcile NuXTore, SnekByte, Media Player, Media Downloader, Authenticator, Safe Cleanup, DevMgmt and PenguInterface with the actual installed/staged app registry. The source currently has a case-sensitive ID drift (`org.nuxel.Nuxtore` vs `org.nuxel.NuxTore`) and NuXTore install/remove state is largely local metadata. Make installs create a valid launcher registration and make removal unregister the app cleanly. Preserve package bundles and user data by default. Ensure each existing app appears in Home and actually opens. Where a catalog app is only a stub/incomplete, complete its minimum useful functionality rather than presenting an empty icon. Keep the catalog local/offline and signature-verified; remote repository work is explicitly out of scope.
6. **Bottom navigation artwork:** repair the Back arrow, Penguin Home and Tabs artwork so it looks clean and complete rather than chopped. The active S10+ path is the native A45 Wayland layer-shell dock (`tools/s10plus/a45/nuxel-navdock.c`) using generated `navdock-art.h` from root `assets/button-left.png`, `button-middle.png` and `button-right.png`; the DOM dock is only a fallback. Inspect original alpha bounds, transparent padding, downsampling, fit, premultiplication and physical output. Regenerate the native header from the corrected source assets and keep the fallback visually consistent. Do not hand-edit generated C arrays.
7. **NFC:** run the existing staged NFC diagnostics for controller, driver/kernel, firmware, userspace stack and physical tag read. Add an NFC top-bar status/toggle icon and a dedicated Settings NFC tab with state, diagnostics and a real tag-read test only when the provider is supported. No fake ON state and no unsupported payment/emulation claims.
8. **Fingerprint and Security:** investigate the S10+ ultrasonic under-display sensor, kernel driver and secure/TEE interface. Add a Fingerprint Settings tab with provider status, enrollment/deletion and a real test only if secure enrollment is supported. Do not import/export raw biometric templates; fingerprints must be enrolled on-device and remain in the secure provider/TEE. Add a Security tab to choose Swipe, Pattern, PIN or Fingerprint, with mandatory PIN fallback for Fingerprint. Enforce the selected lock in the real session/host lock path, not just a JavaScript overlay. If the sensor is inaccessible, report unsupported and retain PIN fallback.
9. **DND and flashlight:** wire DND to a persistent notification policy that suppresses popups/sound/haptics/LED according to settings without deleting notifications. Wire Flashlight through one safe hardware owner, respect `configs/nuxel/leds/leds.json` including the 60-second maximum, camera arbitration and explicit OFF. Replace the current generic unavailable response with a real result or honest hardware refusal.
10. **Colored LED notifications:** implement true per-color channel selection using the available LED classes/policy. Test red, green, blue and supported mixtures; restore OFF after each event. If the phone exposes no physical notification LED class, report that and use a display-overlay fallback only if the existing display bridge supports it. Never fake a hardware LED.

## REPOSITORY FACTS THE IMPLEMENTATION MUST RESPECT

- `pwa/nuxel-home/index.html` contains the primary lockscreen charging/USB/live row and secondary `#lockscreen-transports` row. Current CSS places primary indicators at `top:184px`, secondary row at `top:252px` with 40px transport icons. Reorder the USB and live nodes so Live Console is second; tune lower-row offset/size only after checking portrait and short-viewport geometry.
- `services/nuxel-bridge/src/usb_mode.py` deliberately marks File Transfer active only after the helper proves activation. `services/nuxel-s10/bin/nuxel-usb-mode.sh` currently detects possible `umtprd`/`mtp-server` and configfs MTP functions, then explicitly exits with “activation helper is not configured”; it writes `active:false`. This is the immediate reason selecting the mode is not enough.
- Preserve the USB console CDC-ACM function. Never tear it down just to expose MTP. Do not use NCM as a shortcut; the Samsung 4.14.253 kernel has a documented NCM teardown panic. Probe MTP/FunctionFS independently.
- `docs/a53/GNOME-SOFTWARE-RPM-FLATPAK.md`, `docs/a53/FLATPAK-SANDBOX-PORTALS.md` and `docs/a51-wifi-to-web/FLATPAK-ARM64-READINESS.md` record missing package-management/session prerequisites and a kernel without `CONFIG_USER_NS`. Recheck the live kernel; do not evade missing sandbox support with `--no-sandbox`, broad filesystem/device permissions or disabled security.
- `pwa/nuxel-home/js/app.js` uses the Bridge `/api/v1/apps/exec` path for native applications. `services/nuxel-bridge/src/api.py` checks a fixed native allowlist/registered app and launches with a systemd transient unit/session environment. Instrument failures and surface visibility rather than silently starting a process.
- `pwa/nuxel-home/js/apps.js` has a static app list; the canonical common registry is `pwa/nuxel-common/app-registry.json`, copied to `/etc/nuxel/app-registry/app_registry.json` by the S10+ image builder. Avoid another divergent registry.
- NuxTore catalog source is `pwa/nuxel-apps/nuxtore/catalog/package-sources.json`; packages are local bundles, not remote downloads. `nuxtore.js` currently calls a best-effort `apps/register` RPC and stores install/remove flags locally; the Bridge does not currently provide the needed canonical registration flow. `doRemove()` leaves staged files and does not implement real launcher unregistration. Catalog `state_hint` is not proof of current installation.
- Current catalog IDs include `org.nuxel.NuxTore`, while Home/common registry uses `org.nuxel.Nuxtore`; treat IDs as case-sensitive and provide a safe migration alias. SnekByte is in the launcher registry but its catalog state hint says `available`.
- Settings tabs are in `pwa/nuxel-apps/settings/index.html`; tab handling is in `settings.js`, hardware controls in `hardware-settings.js`. Existing tabs include Screen, Bluetooth, Displays, Wi-Fi, Sound, Buttons, Location, Power and Developer. Add NFC, Fingerprint/Biometrics and Security as real panels with real Bridge providers.
- NFC already has `configs/nuxel/nfc/nfc.json`, `tools/s10plus/a33/nuxel-nfc-diag.sh` and `test-nfc-diag.py`. The expected controller is Samsung sec-nfc/S3FWRN5 family at I2C `0x27`; diagnostics distinguish kernel, firmware, stack and tag test. Only a physical tag UID test proves reader behavior.
- Fingerprint has no demonstrated sensor/provider/enrollment implementation in this repository. S10+ sensor is ultrasonic under-display. Treat sensor driver/TEE support as an investigation, not an assumed Linux/libfprint feature.
- `pwa/nuxel-home/js/qs.js` currently routes both `dnd` and `flashlight` to the generic unavailable response. The LED policy is in `configs/nuxel/leds/leds.json`, with `max_on_ms:60000`, `require_explicit_yes:true`, `auto_on_boot:false`, `off_on_exit:true`. `tools/s10plus/a33/nuxel-led-diag.sh` is the existing hardware diagnostic path.
- LED policy distinguishes rear torch, front notification LED and AMOLED edge-lighting (a display overlay, not a dedicated LED). The notification helper must resolve per-color red/green/blue channels rather than simply toggling one generic brightness value.
- The active dock is native A45 Wayland layer-shell. `gen-navdock-art.py` reads root `assets/button-*.png`, creates 48×48 premultiplied ARGB arrays, and `nuxel-navdock.c` nearest-neighbor scales them to output scale. PWA copies under `pwa/nuxel-home/assets` are separate fallback images. Inspect both paths.

## EXECUTION ORDER

1. Inventory the active build path, source tree, running services, installed packages, live kernel config, UDC/configfs, NFC/LED/fingerprint devices, app registry and session environment. Save read-only baseline evidence.
2. Repair lockscreen icon order and transport row visual sizing. Fix native dock artwork generation and fallback consistency.
3. Complete USB MTP activation while preserving USB serial console; physically verify host enumeration and a real copy in both directions where supported.
4. Diagnose native app launch failures and build one canonical installed-app discovery/registry/launch path.
5. Repair NuxTore install-state reconciliation and register all current local apps; finish incomplete catalog apps where feasible.
6. Add Software app for native GTK/RPM package management. Report Flatpak blocked until kernel sandbox support and portals are proven; do not weaken security.
7. Implement NFC provider, top-bar status/toggle and Settings NFC test only to the capability level proved by diagnostics.
8. Implement Fingerprint provider/Settings only if secure sensor access exists; implement Security lock framework with PIN fallback independently of fingerprint support.
9. Implement persistent DND and a single safe flashlight owner.
10. Implement color-aware notification LED behavior or a truthful display-overlay fallback.
11. Update rootfs packages/systemd units, app registry, asset generation, PWA cache versions and docs. Add regression tests for every feature.
12. Build the S10+ ARM64 image/artifacts, deploy over the already-configured SSH path if available, and complete physical verification.

## SAFETY / SECURITY

- No Heimdall, Odin, fastboot, bootloader entry, raw partition writes, `dd` to block devices or forced reboot. No kernel flash as a shortcut.
- No USB mass-storage export of the live root/home filesystem. No UDC rebind that drops the CDC-ACM console. Never disable USB safety gates.
- Do not weaken Flatpak sandboxing, turn off SELinux, grant `--filesystem=host` or `--device=all`, or run all GUI apps as root.
- Never trust client-supplied `Exec`, binary path or desktop-file path. Native launches must resolve a validated desktop ID/registry entry to a verified executable/desktop file; use argv APIs or GIO, never shell interpolation.
- Do not expose raw fingerprint templates. No importing Android templates or storing biometric data in browser/localStorage/plain JSON. Enroll and manage templates only through a verified secure biometric provider/TEE. Store only safe metadata/opaque IDs.
- PINs and patterns must never be stored in plaintext or logged. Use a vetted password KDF (Argon2id or scrypt where available), constant-time verification, rate limits/lockout, secure permissions and a real session lock enforcement path.
- Keep an accessible PIN fallback before enabling fingerprint unlock. Do not make fingerprint the only unlock credential.
- No UI state may claim NFC, fingerprint, torch or notification LED is working until a real provider reports it and the physical test is complete.
- Preserve all user files, app data, notes, photos, downloads, authenticator data, credentials and SSH access. App removal defaults to removing the launcher registration/app code but retaining user data; data purge requires explicit separate confirmation.
- Keep NuxTore local/offline and preserve bundle hashes/signature/provenance checks. Do not publish or fetch external packages in this mission.

## DEFINITION OF DONE

- Lockscreen primary order is Charging → Live Console → USB PC; transport penguins are slightly lower/larger and readable without clipping/overlap.
- File Transfer enumerates as a real MTP device on a physical computer while USB console remains usable; `active` only means the real endpoint is active.
- Software app can manage verified native GTK/RPM apps through authorized transactions. Flatpak is only enabled if kernel sandbox, Bubblewrap, portals, repository and package support all pass; otherwise the limitation is visible and explicit.
- Firefox/VLC/other installed native apps launch a visible surface or display a truthful install/unsupported/failure reason. Signal is not advertised as installed unless package/desktop entry and ARM64 support are real.
- NuXTore, SnekByte and all other installed local catalog apps are recognized accurately, have Home icons, launch, and can be installed/removed through NuXTore. No false installed state from `state_hint`.
- Back/Home/Tabs native dock art and fallback art appear clean, complete, correctly proportioned and not clipped.
- NFC icon/toggle/Settings panel reflect real hardware state; a tag read is recorded if supported.
- Fingerprint enrollment/test only appears as supported after secure hardware/driver/TEE proof. Security modes work; fingerprint mode has PIN fallback.
- DND actually suppresses configured notification effects without losing history. Flashlight is a real bounded action or a clear unsupported/refused state.
- Colored LED alerts use correct physical color channels or a clearly labelled software edge-lighting fallback. All channels turn off correctly.
- Tests, build logs, hardware evidence, deployment record and rollback instructions are saved. Unsupported hardware is reported honestly rather than marked complete.

**Do the work in the repository. A plan-only answer, mock UI, fake device state or unverified green checkmark is not completion.**

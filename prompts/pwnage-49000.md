# PWNAGE-49000 — NUXEL SYSTEM CHROME, NAVIGATION, APPS, USB, SOFTWARE, AUTHENTICATOR & DEVICE SECURITY

**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel, custom Fedora-based ARM64 mobile Linux  
**Primary UI:** `pwa/nuxel-home` + app PWAs + Settings + native Wayland navigation dock  
**Native app path:** Nuxel PWA host + Bridge `/api/v1/apps/*` + canonical app registry + Phoc/Wayland toplevels  
**Display path:** Phoc/Wayland + Pixman/software-rendered path + `nuxel-wl-fb` as the single `/dev/fb0` owner  
**USB path:** existing USB gadget owner + CDC-ACM recovery console + Nuxel connection-mode helper  
**Mission:** implement and physically verify the requested fixes in the active S10+ source/build path. This is not a UI mock-up exercise.

## MISSION

Deeply inspect the repository and current running S10+ before changing anything. Repair the real system paths, preserve the current working phone, and prove each feature through source tests and physical device tests.

### Required outcomes

1. Replace the current ambiguous Wi-Fi and Bluetooth status glyphs with immediately recognizable, polished icons. Add a recognizable Location/GPS-state icon using the real Location provider. Do not claim a satellite fix merely because Location services are enabled.
2. Make the top status bar visible on the lockscreen. Keep clock, battery, radio and connectivity information visible without allowing lockscreen gestures or the status strip to conflict.
3. Repair the native three-button navigation dock (Back arrow / Penguin Home / Tabs). Restore distinct haptic feedback when Back is held.
4. Restore long-hold Back termination of the foreground app. It must close only the foreground app, not kill Nuxel Home, the compositor, system services or unrelated applications.
5. Make a short Back press navigate backward inside the current app where a real app history/navigation action exists. Home remains the distinct action that backgrounds/minimizes the app and returns to the Home desktop.
6. Make Back, Home and Tabs/Recents work with PWA, native GTK and Flatpak apps. Do not make the Home button depend on whether a WebKit iframe exists.
7. Diagnose the “unlock the phone first to use apps” error. Fix the state/authority mismatch without removing the genuine lock gate or weakening authentication. Compare a working Archive Manager launch against a failing native launch.
8. Keep the system top bar and three-button navigation chrome visible over native/Flatpak app surfaces as well as Home. Use real Wayland layer-shell/system chrome; a status bar inside the covered Home WebView is not enough.
9. Complete USB File Transfer so a Mac can browse the phone storage and removable SD card through a real MTP endpoint. Preserve the serial recovery console. Never export the live root/home filesystem as raw USB mass storage.
10. Make the lockscreen and app drawer responsive on the software-rendered fbdev/Pixman path. Fix swipe-down drawer opening so the opening gesture does not immediately scroll the newly opened drawer. Scrolling the app grid must never launch an app; only a genuine tap should launch.
11. Repair the Software application as one coherent manager for native Fedora/RPM/GTK apps and Flatpak apps. Flatpak must remain explicitly disabled if the kernel sandbox prerequisites are missing; never weaken sandboxing to make the UI appear functional.
12. Fix NuXtore's Live Console installed-state recognition. The current catalog calls it `org.nuxel.Console` / `available`, while the canonical Home registry contains `org.nuxel.LiveConsole`. Reconcile aliases and source ownership; do not create duplicate icons or allow removal of a built-in recovery app without explicit safe policy.
13. Make Nuxel Authenticator operational after vault unlock: add accounts from manual Base32 secrets, pasted `otpauth://` URIs, QR scanning by camera and QR-image import. Generate and copy TOTP codes correctly. Keep the existing encrypted-vault security model and fix its integration defects. Add an Entra-compatible standard OATH/TOTP workflow where the tenant permits third-party software OATH.
14. Investigate “Microsoft Authenticator” support accurately. Native Nuxel can provide standard TOTP/OATH codes but cannot implement Microsoft Authenticator proprietary push/number matching, passwordless broker, device-registration or compliance functions by simply adding a button. Provide a clear Entra setup guide and truthful feature labels.
15. Re-run the existing NFC diagnostics and prove a physical tag read, or report the exact kernel/firmware/stack blocker. Add/repair the actual NFC settings/status integration only where supported.
16. Verify fingerprint support on the physical ultrasonic under-display sensor. Add secure enrollment/verification only if the driver and secure provider/TEE genuinely support it; otherwise show unsupported and retain PIN fallback.
17. Audit the screen-lock implementation. Provide Swipe, PIN, Pattern and Fingerprint-with-PIN-fallback only where the real session lock manager enforces them. Face recognition may be evaluated as an optional future/convenience method, but never presented as secure unlock without credible liveness/anti-spoof and trusted local handling.

## IMPORTANT FINDINGS IN THE PROVIDED REPOSITORY SNAPSHOT

The following were confirmed in `nuxel-main (10)(1).zip`; verify against the current working tree and live device before editing:

- `pwa/nuxel-home/index.html` contains `#status-bar` with Time, Signal, Wi-Fi, Bluetooth, Battery and percentage. There is no `#status-location` element in this snapshot. `status-bar.js` has Wi-Fi and Bluetooth provider logic but no top-bar Location renderer.
- `pwa/nuxel-home/css/status-bar.css` gives `.status-bar` `z-index:100`. `pwa/nuxel-home/css/lockscreen.css` gives the full-screen `#lockscreen` overlay `z-index:500`. The status bar is therefore covered by the lockscreen. This is a direct, testable reason the top bar is missing while locked.
- The Wi-Fi glyph in `status-bar.css` is drawn as a circular arc/ring plus a dot. The Bluetooth glyph is also custom CSS pseudo-art. Replace them with recognizable vector/local icon artwork, not emoji and not duplicated CSS+SVG glyphs.
- The active three-button dock is native Wayland layer-shell source `tools/s10plus/a45/nuxel-navdock.c`, not only the Home PWA's DOM. It sends actions through `/run/nuxel-pwa-host.cmd` and haptic requests through `/run/nuxel-haptics/haptics.cmd`.
- `nuxel-navdock.c:tap_at()` treats a Back hold of at least 700 ms as `back-long`. However `forward()` currently sends the ordinary `navigation` haptic for every action, including long Back. The haptics daemon already supports a distinct `long` command/pattern; use it for the hold, exactly once.
- The A45 PWA host currently maps `back-long` to a `nuxel:action` event, and `pwa/nuxel-home/js/app.js` maps it to `terminateForeground()`. `terminateForeground()` calls `/api/v1/apps/close-foreground`, whose Bridge helper asks the compositor's `nuxel-foreign-toplevel close-foreground` command to close the active non-Home toplevel. Keep this specific foreground-only contract. Verify the actual installed A45 host and dock match these sources; do not rely on old comments that describe a previous bad action map.
- Short `NuxelHome.back()` already handles launcher overlays, the drawer, keyboard, PWA iframe history and then calls `/api/v1/apps/back` for native apps. But `NuxelBridge._native_back_action()` only knows how to handle the native browser's `/run/nuxel-browser.state` + `/run/nuxel-browser.cmd` history. For other native apps it currently reports `handled:false/at_root:true`; Home then backgrounds the app. There is no common native/Flatpak in-app Back contract yet.
- `NuxelHome.home()` already calls `/api/v1/apps/home`, and the Bridge uses `nuxel-foreign-toplevel home` to minimize non-Home toplevels. Preserve this distinct minimize behavior.
- `NuxelHome._isLocked()` is based on the local LockScreen instance. `_openPwa()` and `_launchNative()` both refuse launches while that instance says locked. The supplied source tree does not contain the exact user-reported text “unlock the phone first to use apps”; it may come from a stale deployed bundle, a native helper, an app/vault lock or another runtime copy. Trace the exact message and live state before modifying the gate. Do not remove the lock check.
- The native app launch endpoint is in `services/nuxel-bridge/src/api.py`. `_activate_app()` handles `pwa` and `native` entries. The app-registry schema currently lists `native`, `pwa`, `system`, and `template` types; it does not yet define a first-class Flatpak type. `_exec_native_app()` uses a fixed allowlist/registry and `systemd-run`, with a hard-coded software-rendering environment. Add a validated Flatpak descriptor/launcher rather than passing arbitrary shell commands or package refs from the browser.
- The Nuxel status bar is part of the Home WebKit document. It cannot remain above an unrelated top-level native GTK/Flatpak Wayland window. The bottom dock is already an overlay-layer Wayland surface. A persistent global top bar for native apps needs a native Wayland layer-shell status surface (or an equivalent compositor-owned shell surface), with the DOM status bar hidden only while the native overlay owns presentation to avoid doubles.
- The USB helper `services/nuxel-s10/bin/nuxel-usb-mode.sh` deliberately refuses File Transfer after probing because its MTP activation helper is not configured. `services/nuxel-bridge/src/usb_mode.py` correctly reports active only if the helper writes an actual active endpoint state. Finish this real activation path; do not change the JSON to `active:true` without host enumeration.
- The current catalog lists Live Console as `org.nuxel.Console`, name “Live Console”, `state_hint: available`, and bundle `org.nuxel.Console-1.0.0.bundle.json`. Home's canonical registry includes `org.nuxel.LiveConsole` for `/pwa/nuxel-apps/console/index.html`. These two identities refer to the same built-in console tree but are currently not reconciled.
- The existing Software readiness document `docs/a53/GNOME-SOFTWARE-RPM-FLATPAK.md` records a prior image with no `dnf`/`dnf5`/PackageKit/Flatpak/portals, no working network at test time, and Flatpak blocked by `CONFIG_USER_NS` not set. Re-probe; do not assume this changed. Do not enable Flatpak unless user namespaces, Bubblewrap, portals, ARM64 runtimes and an actual sandboxed app all pass.
- Authenticator already contains `js/totp.js` with RFC 4226/6238 primitives and `js/vault.js` with AES-256-GCM encryption and PBKDF2-derived vault keys. The `authenticator.js` UI currently offers pasted `otpauth://totp/` URI and manual Base32 entry, but no real QR camera/image decoding control. The app says it is local-only and no-network. Preserve that property.
- The Authenticator UI's clipboard fallback currently displays the raw OTP in a toast if clipboard access fails; remove this secret-leaking fallback. Review its per-account event closures: `var a` is reused in the rendering loop, so Copy/Delete listeners must be bound to the correct immutable account ID rather than accidentally closing over the last loop item.
- The current vault saves an encrypted envelope in app localStorage. It does not yet use the OS Secret Service/keyring. Add a secure Nuxel storage adapter if available, and retain the encrypted envelope as the portable encrypted backup. Never migrate to plaintext storage.
- NFC already has `configs/nuxel/nfc/nfc.json`, `tools/s10plus/a33/nuxel-nfc-diag.sh` and `test-nfc-diag.py`. The documented controller family is Samsung sec-nfc / S3FWRN5 at I2C `0x27`. The manual proof still marks the physical tag read `NEEDS_OWNER_TEST`; only a physical UID read from a real tag proves functionality.
- No working fingerprint enrolment/provider, secure biometric broker or face-authentication implementation was found in the supplied archive. Do not infer Linux support merely because the S10+ contains an ultrasonic sensor.
- The current lockscreen implementation is the penguin drag-to-unlock state machine in `pwa/nuxel-home/js/lockscreen.js`; the Settings panel in the inspected snapshot has no complete PIN/Pattern/Fingerprint Security tab. A swipe gesture is not credential authentication.

## EXECUTION ORDER

1. Capture build/live baseline, exact toast source, lock state, top-level windows, service state, USB gadget state and current app catalog/registry. Verify active source/build generation.
2. Fix global chrome first: recognizable Wi-Fi/Bluetooth/Location icons, lockscreen top bar and status source state. Add native status chrome for foreground native/Flatpak apps without DOM duplication.
3. Repair Back/Home/Tabs native dock, haptic long-hold, short Back navigation, long Back foreground termination and Home minimize semantics across PWA/native/Flatpak.
4. Fix the lock-state/native-launch false refusal by reconciling the authoritative lock state. Keep real pre-unlock gating intact. Test native apps and the working Archive Manager through one consistent launch path.
5. Complete USB MTP activation and physical Mac host testing using a real MTP client such as OpenMTP. Preserve CDC-ACM. Do not promise Finder mount semantics for MTP.
6. Optimize lockscreen/drawer and repair gesture arbitration so drawer-opening swipes do not scroll immediately and app tiles never launch from a scroll.
7. Complete unified Software UI/backend for native RPM and Flatpak with honest capability gates. Do not weaken Flatpak isolation.
8. Reconcile Nuxtore Live Console ID/state with the canonical app registry and real installed files.
9. Repair Authenticator QR/manual add and secure vault persistence. Verify RFC 6238 vectors and a real owner-provided test account without collecting/exporting its secret in logs.
10. Run NFC diagnostics and physical tag test; investigate fingerprint and screen-lock provider capability; implement supported options only. Treat face recognition as optional and disabled until security proof exists.
11. Update rootfs build, units, registries, cache versions, tests and docs. Deploy staged over the existing safe path; physically verify each item.

## SAFETY RULES

- Preserve the working boot, Wi-Fi SSH, USB CDC-ACM recovery console, touchscreen, Phoc compositor, native dock and the single `/dev/fb0` owner.
- No second framebuffer writer, raw block-device export, live-root mass-storage LUN, kernel flash or bootloader operation in this mission.
- Keep a real lock gate. Never fix “unlock first” by removing all locked-state checks.
- Short Back navigates; Home backgrounds/minimizes; long Back closes only the exact foreground app. Never kill Home, the host, compositor, Bridge or service daemons.
- Only stop/terminate an app process when it is tied to a validated app-owned systemd unit/cgroup. Prefer the Wayland close request; use bounded TERM and a final KILL only for that app-owned process group after a failed graceful close. Record the escalation.
- Native and Flatpak launch descriptors are registry-derived, validated and shell-free. No browser-supplied `Exec` strings or arbitrary commands.
- Keep MTP limited to explicit user media/storage roots. Preserve CDC-ACM. If MTP is unsupported by the current kernel, report the precise blocker instead of making state fake.
- Keep secrets in the encrypted Authenticator vault / OS keyring; never print OTPs, shared secrets, QR payloads, vault passphrases, PINs or biometric data to logs.
- Fingerprints stay inside the secure provider/TEE. No raw template import/export. Face recognition is not a secure unlock method without robust liveness and anti-spoof protection.
- Do not claim NFC, fingerprint, Face ID, Flatpak, MTP, app installation or app launch works until the real provider/host/device confirms it.
- Back up modified files and persistent configuration before live deployment. Do not guess a phone IP or credentials. Do not stop the only SSH/network path.

## DEFINITION OF DONE

- Wi-Fi, Bluetooth and Location have clearly recognizable, non-duplicated status icons with truthful states.
- Top bar is visible on lockscreen and remains available over native/Flatpak windows through real native system chrome.
- Native Back/Home/Tabs buttons work on PWA, native GTK and Flatpak surfaces; Back navigates within app, Home minimizes, held Back closes only foreground app, and long-hold haptic is distinct and physically felt if vibrator hardware is supported.
- False “unlock first” refusal is corrected without weakening the real lock. Native apps and Archive Manager launch consistently after successful unlock.
- MTP File Transfer enumerates on a Mac MTP client and supports real copy/list of internal storage and mounted SD card, while serial console remains intact. Finder is not falsely described as natively mounting MTP.
- Lock screen and drawer are measurably smoother; drawer-opening swipes do not immediately scroll; scroll never launches an app.
- Software handles real native RPM transactions; Flatpak is enabled only with verified secure sandbox prerequisites.
- Nuxtore accurately recognizes Live Console as system-installed/built-in and does not label the registered app as available.
- Authenticator adds TOTP accounts by QR camera, QR image, URI and manual secret, stores them encrypted, computes/copies correct codes and passes RFC vectors. Microsoft Authenticator push is not falsely claimed; Entra third-party OATH setup is documented.
- NFC has a physical tag-read verdict; fingerprint and lock methods are enabled only when real providers exist; PIN fallback works; face unlock is not faked.
- Tests, physical evidence, package/build integration, cache version changes, deployment and rollback report are complete.

**Implement the features, not merely the audit. If a hardware/security capability is not available, report the precise reason and leave a safe, useful UI state rather than faking success.**

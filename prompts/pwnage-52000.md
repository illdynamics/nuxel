# PWNAGE-52000 — NUXEL PHONE UX, LPM BOOT, PRIVACY CONTROLS & GRAPHICS STATUS KICKSTARTER

**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel — Fedora-based ARM64 Linux phone OS  
**UI:** Home PWA, Settings PWA, installed PWAs, native GTK and supported Flatpak apps  
**Display:** Phoc/Wayland → `nuxel-wl-fb` → single `/dev/fb0` owner → DECON/AMOLED  
**Bridge:** `services/nuxel-bridge`  
**Metrics:** `services/nuxel-metrics/nuxel-metricsd.c` + `pwa/nuxel-home/js/system-monitor.js`  
**Mission:** real source repairs, accurate providers, safe boot/kernel work if required, and physical S10+ verification.

## MISSION

Inspect the current repository, active S10+ image and live device first. Implement all requested changes end-to-end; do not add mock controls, fake status or CSS-only fixes for system-level problems.

### Required outcomes

1. **Settings cannot pan sideways.** Every Settings panel fits the phone viewport; vertical scrolling works. The tab selector may remain its own horizontal scroller so all tabs remain reachable, but the page/content itself must not drift sideways.
2. **All apps are phone-responsive.** Inventory every installed/registered PWA, native GTK app and supported Flatpak app. Make layouts, dialogs, forms, keyboard handling and scrolling usable at S10+ portrait/landscape sizes. Do not stop after fixing Settings.
3. **Eliminate charger-only cold boot.** When powered fully off, connecting a charger and powering on must lead to a normal interactive Nuxel session with touch. Preserve battery/thermal protections. The existing LPM bug is kernel/early-boot related; userspace cannot revive a built-in driver that returned `-ENODEV` before binding.
4. **Lockscreen must never show the top bar or three-button dock.** Hide `#status-bar`, DOM `#system-navigation` and the separate native Wayland layer-shell dock. No startup, wake, lock-transition or process-restart flash.
5. **Status icons reflect actual state and user choice.** Hide icons for radios/features that are OFF or unsupported. Add a Screen Settings card that lets the user individually show/hide every top-bar icon without changing the underlying radio/service state.
6. **Expanded Quick Settings gets a third row** below the existing two rows: NFC, Fingerprint, Camera privacy and Microphone mute. These must control real providers; unsupported hardware must be shown as disabled/unsupported, not fake ON.
7. **GPU meters are accurate.** Correct GPU utilization, MHz frequency and GPU memory accounting. The Mali uses shared system RAM, not dedicated VRAM; label it accordingly. Append `(ACC)`/`(A)` to GPU only when the real GUI path represented by the meter is actually accelerated. Show partial Phoc-vs-WebKit status honestly.
8. **Graphics status in Settings → Displays.** Add a Graphics Acceleration block before external connector discovery. It independently reports GPU/driver/EGL/GLES, Phoc renderer, WebKitGTK/GTK GL, DMA-BUF/udmabuf, `nuxel-wl-fb` and fbdev/DRM path. It must not hang while external connector refresh is loading.

## CONFIRMED SOURCE FINDINGS — USE THESE AS STARTING POINTS, REVALIDATE LIVE

- Settings: `pwa/nuxel-apps/settings/index.html`, `settings.css`, `settings.js`, `hardware-settings.js`. `.tabs` intentionally uses `overflow-x:auto`; keep that isolated tab strip but constrain `html/body/main/.panel/.card` and nested flex/grid children with `min-width:0`, `max-width:100%`, responsive grid tracks and safe wrapping.
- The Settings HTML has duplicate `id="display-state"` elements: one for Screen on/off and one for external Displays. `getElementById()` resolves only the first. `settings.js:refreshDev()` and `hardware-settings.js:renderDisplays()` both write through that duplicate. Rename to unique IDs and add a uniqueness test.
- `DisplayProvider` in `services/nuxel-bridge/src/hw_providers.py` is specifically external DRM/Type-C/Extcon connector inventory. Keep it separate from the new GPU/graphics provider. Its refresh currently has no independent UI timeout/cancel path.
- Quick Settings in `pwa/nuxel-home/index.html` has two rows: Wi-Fi/Bluetooth/Mobile/Location, then DND/Flashlight/Rotate/Settings. Preserve both and add the privacy row below them only when fully expanded. Implement providers in `pwa/nuxel-home/js/qs.js` and Bridge.
- `status-bar.js:_renderBluetooth()` already hides Bluetooth unless powered ON. `_renderWifi()` currently dims Wi-Fi in disabled/unavailable states rather than hiding it. Add a distinct radio-powered state and hide Wi-Fi when known OFF/unsupported.
- Top-bar markup: `#status-bar`; DOM nav: `#system-navigation`, `#nav-back`, `#nav-home`, `#nav-recents`. Lock overlay `#lockscreen` has z-index 500 while status bar has 100, but CSS cannot hide the native dock. Active native dock is `tools/s10plus/a45/nuxel-navdock.c`; coordinate with native host/session lock state and fail closed while locked/unknown.
- LPM root cause is documented in `docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md` and `configs/nuxel/power/power.json`: S-Boot passes `androidboot.mode=charger`; `sec_bat_is_lpm_check()` sets `lpcharge=1`; `sec_ts_init()` returns `-ENODEV` before `i2c_add_driver()`. Touch, fingerprint (`qbt2000`) and Wacom paths have related LPM gates. Driver is built-in; no `/lib/modules/4.14.253`; `CONFIG_KEXEC` unset. The existing guard is `tools/s10plus/a33/nuxel-bootmode-guard.py`; its reboot is gated and `allow_reboot` defaults false.
- Candidate kernel patch: `tools/s10plus/a33/kernel-patches/sec_ts-lpm-initcall-deferred-bind.patch`. It is documented `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED`; context is reconstructed and must be matched to exact kernel source. It proposes deferred touchscreen binding but does not prove a full normal charger-attached boot or resolve all LPM-gated drivers. Audit every `lpcharge` consumer before any change; do not globally clear LPM or bypass battery/thermal safety.
- Metrics collector already exists and is installed by `images/s10plus/build-phone-rootfs-inside-fedora.sh`: `services/nuxel-metrics/nuxel-metricsd.c`, `.service`, `.socket`. Current paths are Mali utilization `/sys/devices/platform/18500000.mali/utilization`, fallback `/sys/kernel/gpu/gpu_busy`, Mali clock `/sys/devices/platform/18500000.mali/clock`, allocation table `/sys/kernel/gpu/gpu_memory`, RAM `/proc/meminfo`. Verify actual live units/table format; do not blindly trust old assumptions.
- `system-monitor.js` uses utilization for the GPU meter, MHz for its detail and tracked allocation bytes vs system RAM for GPU memory. The SoC has shared memory, not dedicated VRAM. Rename the UI to `GPU MEM (shared)` or `VRAM*` and explain the reference budget.
- Owner's latest PWNAGE-48000 report: Phoc holds `/dev/mali0` and `/dev/udmabuf`, kbase debugfs lists Phoc GPU context, Wayland/wl-fb/web active, Bridge `FRAMES_OK`, no DECON pan failures, GPU fallback marker absent. But WebKitGTK/GTK GL still falls back to software because EGL/Wayland DMA-BUF path is not working. Preserve the working Phoc/kbase path and do not claim all GUI layers are accelerated.

## EXECUTION ORDER

### 1. Baseline

Record git state, active builder paths, live kernel/cmdline, current boot mode, touch-device registration, installed service hashes, Phoc/kbase/wl-fb state, GPU metrics raw data, Settings DOM, app registry, current icon preferences and screen captures. Back up all changed configs. Preserve SSH/USB console and user data.

### 2. Settings and apps

Fix horizontal page overflow while keeping the tab rail independently scrollable. Test at 320, 360, 384, 393 and 430 CSS-pixel widths in portrait/landscape. Audit every installed app from the canonical registry and actual package inventory. Ensure responsive controls/dialogs, keyboard-safe layout, no document horizontal overflow, readable text and usable touch targets. Produce an app responsiveness matrix.

### 3. Charger/LPM

Audit exact Samsung kernel source and initramfs, all `lpcharge`/charger-mode consumers and charger safety behavior. Review the candidate patch against exact source; do not blindly apply its reconstructed context. Implement a board-specific safe interactive Nuxel boot path that preserves charge/thermal limits, registers touch correctly and handles fingerprint/Wacom truthfully. The acceptance test is power OFF → charger connected → power ON → normal interactive Nuxel with touchscreen.

If a BOOT/kernel update is required, use the established TWRP recovery agreement: confirm phone actually visible in TWRP over USB; verify exact model/partition; read back current working BOOT and hash it off-device; build one exact ARM64 candidate; write only the authorized BOOT target; verify boot/touch/display/GPU/SSH. If it hangs, bootloops, returns to TWRP or loses core functionality, stop and restore the verified prior BOOT image immediately. No EFS/modem/PIT/vendor/userdata writes; no partition guessing; no blind flash if TWRP is absent.

Keep the existing LPM guard fail-safe: no blind reboot loops, preserve owner locks, uptime/cooldown and charger/charging checks. A one-time normal reboot is a fallback, not the permanent cold-boot fix.

### 4. Lock-screen privacy

Hide status bar and DOM navigation before revealing lockscreen. Add host/session IPC to hide/unmap the native layer-shell dock; start native dock hidden until authoritative lock state is known. Restore only after authentication succeeds and Home is ready. Test cold boot, lock from apps, wake, PWA/native-host restart and lock/unlock races. No top bar or Back/Home/Tabs visible at any point while locked.

### 5. Status bar preferences

Create a durable per-icon visibility document, separate from safe-zone geometry. The final visibility rule combines user preference, provider capability/state and lock state. Hide NFC when off, Location when off, Wi-Fi when radio off, Bluetooth when powered off, etc. User-hidden icons stay hidden without disabling the service. Hidden icons reserve no layout width. Add per-icon toggles, live preview, defaults and schema migration to Screen Settings.

### 6. Quick Settings privacy row

Preserve first two rows. Add NFC, Fingerprint, Camera and Microphone below them only when expanded. NFC uses real NFC provider. Fingerprint tile toggles permission to use biometrics for unlock, not arbitrary sensor power; preserve PIN fallback. Camera must use a real global privacy gate/provider and handle already-open capture streams. Microphone must mute real capture through PipeWire/WirePlumber/ALSA policy, including new streams. Provider unsupported/unknown/error states must remain honest. UI updates only after backend acknowledgement; visible-only bounded polling; no stale response after close.

### 7. GPU metrics + Graphics Settings

Extend existing `nuxel-metricsd`; do not add a duplicate collector. Validate utilization values, clock units, allocation table semantics, PID duplication/shared allocations, sample age and missing/stale state. Show utilization %, clock MHz and tracked GPU memory allocation. This is shared RAM, not dedicated VRAM. Add `graphics.status`/`graphics.test` provider separate from external `display.status`.

GPU status should separately report kbase driver/device, EGL/GLES, Phoc renderer, GTK GL, WebKitGTK acceleration, DMA-BUF/udmabuf and final `nuxel-wl-fb`/DECON/fbdev path. The owner reports Phoc accelerated but WebKitGTK software; preserve that distinction. GPU label gains `(ACC)` only when relevant live GUI acceleration is proved; if only Phoc is accelerated while WebKit is software, use `PARTIAL` or omit `(ACC)` and explain.

Add Graphics Acceleration block first in Settings → Displays, then External Display connector block below. Give each unique DOM IDs, independent API requests, independent timeout/cancellation and visible failure states. Connector enumeration must not block GPU status. The Graphics Test button may run a bounded real GLES/Wayland rendering test in the same session, must retrieve renderer strings and clean up without crashing Phoc. Never auto-run expensive tests every refresh.

### 8. Tests and deployment

Run existing tests plus new layout, app responsiveness, LPM guard/kernel, lockscreen native dock, status icon, QS privacy, GPU metrics, graphics provider, unique DOM ID and timeout tests. Build clean ARM64 rootfs and verify exact installed binaries/assets/configs. Deploy staged deltas over existing configured SSH/USB console. Restart only necessary services; do not restart the working display owner gratuitously. Record before/after evidence and rollback instructions.

## SAFETY

- No false state, no fake GPU acceleration, no simulated hardware pass.
- No global `lpcharge=0` hack until every consumer and safety impact is audited.
- No raw sysfs/driver writes from JS.
- No second `/dev/fb0` writer; preserve single `nuxel-wl-fb` ownership.
- Preserve working kbase/Phoc GPU acceleration.
- Any kernel write only under verified TWRP/BOOT backup/partition gates above.
- No EFS/modem/PIT/vendor/userdata changes.
- Preserve charging/thermal/PMIC protections, credentials, authenticator data, notes and all user files.

## DEFINITION OF DONE

- Settings content cannot scroll sideways; all tabs remain accessible.
- Every installed app works responsively on the phone.
- Cold boot with charger attached reaches interactive Nuxel with touchscreen, not LPM-only UI.
- Lock screen never shows top bar or native/DOM Back/Home/Tabs dock.
- Off/unsupported feature icons are hidden; every icon is independently hideable in Screen Settings.
- Expanded Quick Settings adds real NFC, fingerprint-auth, camera-privacy and microphone-mute controls below rows 1–2.
- GPU metrics use verified units and honest shared-memory accounting; `(ACC)` appears only with renderer proof.
- Graphics Acceleration block renders before external connector status and never spins indefinitely.
- Existing kbase/Phoc/`nuxel-wl-fb`/DECON stack remains working.
- Automated tests, physical checks, build/deployment evidence and rollback instructions are recorded.

**Do the actual source integration and prove it on the S10+. No fake status, no broad CSS band-aid, no LPM half-fix presented as full boot, no false VRAM and no graphics status hidden behind a hanging connector query.**

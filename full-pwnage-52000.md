# FULL-PWNAGE-52000
# NUXEL — RESPONSIVE PHONE UI, SETTINGS OVERFLOW, TRUE NORMAL CHARGER BOOT, LOCKSCREEN UI PRIVACY, STATUS-BAR ICON CONTROLS, EXPANDED QUICK SETTINGS PRIVACY ROW, GPU METRICS AND GRAPHICS ACCELERATION SETTINGS

## Full source-level implementation, system integration, safe kernel work, physical S10+ validation and release-quality regression mission

**Mission ID:** PWNAGE-52000  
**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel — Fedora-based ARM64 Linux phone OS  
**UI:** Nuxel Home PWA, Settings PWA, installed Nuxel PWAs, native GTK and supported Flatpak applications  
**Compositor/session:** Phoc / Wayland  
**Display path:** Phoc Wayland screencopy → `nuxel-wl-fb` → single `/dev/fb0` owner → Samsung DECON / AMOLED panel  
**GPU:** Mali-G76 MP12, current vendor kbase path where verified  
**Bridge:** `services/nuxel-bridge`  
**Metrics:** `services/nuxel-metrics/nuxel-metricsd.c` and `pwa/nuxel-home/js/system-monitor.js`  
**Canonical build:** `images/s10plus/build-phone-rootfs-inside-fedora.sh` plus the exact live kernel/boot build path  
**Mission type:** source repair, UX/layout correction, boot/kernel policy repair, capability-provider integration, safe live deployment, automated and physical regression validation.

---

# 0. EXECUTIVE MISSION DIRECTIVE

The objective is to make the current Nuxel S10+ behave consistently as a modern phone OS across its Home shell, Settings, application PWAs, native GTK applications, supported Flatpak applications, lockscreen, status bar, Quick Settings, physical charger boot and graphics status.

This is not a decorative pass. Every control must operate a genuine provider, every status label must describe real state, and every claim must be backed by source/test/device evidence.

The owner has asked for the following exact outcomes:

1. No sideways page scroll in Settings.
2. All installed applications respond to the real phone screen and touch layout.
3. Charger-connected cold boot should no longer strand Nuxel in a reduced low-power charging mode; it should reach a complete interactive phone session with working touchscreen.
4. While locked, there must never be a top status bar or the Back/Home/Tabs three-button dock visible. This includes the native layer-shell dock, not only DOM CSS.
5. Status icons for inactive radios/features must not be shown as active. The user must also be able to individually hide any status-bar icon in Screen Settings.
6. Fully expanded Quick Settings adds a third row below the existing two rows with NFC, Fingerprint, Camera privacy and Microphone mute controls.
7. GPU frequency/utilization and GPU memory meters must be accurate and honest. The GPU label gains `(ACC)`/`(A)` only when the relevant graphics stack actually uses hardware acceleration.
8. Settings → Displays gains a Graphics Acceleration block above external display/connector discovery. It must load independently, have a bounded refresh and remain readable when connector enumeration fails or hangs.

The final result must work on the physical Samsung Galaxy S10+. Do not mark a feature complete solely because a checkbox toggles, a JSON setting persists, a device node exists or a test fixture passes.

---

# 1. REPOSITORY AUDIT — AUTHORITATIVE SOURCE PATHS AND CONFIRMED DEFECTS

The current prompt is based on the supplied `nuxel-main (10)(1).zip` archive dated 30 October 2026, together with the owner's later PWNAGE-48000 report. Live device/source state may have advanced; revalidate before changes.

## 1.1 Main paths

```text
pwa/nuxel-home/
  index.html
  js/status-bar.js
  js/lockscreen.js
  js/lockscreen-indicators.js
  js/qs.js
  js/system-monitor.js
  js/safe-zones.js
  js/settings-store.js
  css/status-bar.css
  css/lockscreen.css

pwa/nuxel-apps/settings/
  index.html
  settings.js
  settings-model.js
  hardware-settings.js
  settings.css

services/nuxel-bridge/src/
  api.py
  bridge.py
  hw_providers.py
  system_indicators.py

services/nuxel-metrics/
  nuxel-metricsd.c
  nuxel-metrics.service
  nuxel-metrics.socket

services/nuxel-session/systemd/
  nuxel-bootmode-oneshot.service
  nuxel-wl-fb.service
  other session/boot services

configs/nuxel/
  bootmode/bootmode-guard.json
  bootmode/README.md
  power/power.json
  power/nuxel-power-mode.service
  display/statusbar-safezones.json
  other existing hardware/privacy configuration

tools/s10plus/a33/
  nuxel-bootmode-guard.py
  kernel-patches/sec_ts-lpm-initcall-deferred-bind.patch
  tests/test-bootmode-guard.py

 tools/s10plus/a45/
  nuxel-navdock.c
  nuxel-pwa-host.c

 images/s10plus/
  build-phone-rootfs-inside-fedora.sh
```

Also inspect all registered apps, their manifests, CSS, native desktop entries and the actual installed runtime app registry. Do not restrict responsiveness testing to the Home and Settings PWAs.

## 1.2 Settings page sideways scrolling — current evidence

`pwa/nuxel-apps/settings/settings.css` currently has:

```css
.tabs { display: flex; gap: 6px; padding: 0 12px 8px; overflow-x: auto; }
```

This horizontal scroll on the tab rail is intentional because Settings has more tabs than fit on a 360-pixel screen. The problem to fix is sideways movement of the **page content**, not the ability to swipe the tab selector to reach later tabs.

Other current style risks include:

- `.zones` uses a 10-column CSS grid with fixed count of tracks.
- `.theme-card` has `min-width:120px`.
- cards and nested flex/grid children do not all establish `min-width:0`.
- state/debug `<pre>` elements have internal scrolling and long values, which must remain contained rather than widen the panel.
- Inputs, selects, buttons and labels can contribute intrinsic width.

Implement a robust responsive width contract for `html`, `body`, `main`, `.panel`, `.card` and children. Use `min-width:0`, `max-width:100%`, responsive grid tracks, `overflow-wrap:anywhere` for long diagnostics and an explicit no-horizontal-page-pan rule. The `.tabs` rail can remain an isolated horizontal scroller. Do not disable vertical touch scrolling or use `touch-action:none` globally.

Test actual page geometry using `scrollWidth` vs `clientWidth` and screenshot/physical touch checks. Do not infer success from one CSS declaration.

## 1.3 Concrete duplicate DOM ID in Display Settings

`pwa/nuxel-apps/settings/index.html` currently defines `id="display-state"` twice:

- in the Screen tab, for Screen on/off status;
- in the Displays tab, for external DRM/Type-C connector status.

`settings.js:refreshDev()` also writes developer display status to `document.getElementById('display-state')`. `hardware-settings.js:renderDisplays()` uses the same lookup. `getElementById()` returns only the first matching element. This can cause:

- the Screen status to be overwritten by developer state;
- external display status to remain at “Checking display path…”;
- refresh results to appear in the wrong panel;
- confusing interactions when the Display panel and Developer refresh run at the same time.

Rename the IDs explicitly and update every selector. Suggested IDs:

- `screen-state` — Screen on/off panel;
- `graphics-acceleration-state` and `graphics-acceleration-detail` — new GPU panel;
- `external-display-state` and `external-display-detail` — external connector provider;
- `dev-state` and `dev-input` — developer diagnostics.

Add a DOM unit test that rejects duplicate IDs in every Settings document. Do not solve a duplicate-ID code defect with CSS.

## 1.4 Existing external DisplayProvider

`services/nuxel-bridge/src/hw_providers.py:DisplayProvider` scans:

- `/sys/class/drm`;
- `/sys/class/typec` and each `port*-partner/type`;
- `/sys/class/extcon`;
- `/proc/config.gz` for `CONFIG_DRM`, `CONFIG_TYPEC`, `CONFIG_EXYNOS_DISPLAYPORT`.

It returns connector/Type-C/Extcon details and `drm_present`, `mirror_supported`, `desktop_supported`, plus a blocker list. Its purpose is **external monitor/USB-C DisplayPort capability**, not Mali GPU acceleration.

Keep that provider separate. Do not reuse `display.status` for the new graphics state. Add a separate graphics status contract and render the graphics card first.

`hardware-settings.js:refreshDisplays()` currently writes a spinner and calls `call('display','status',{})`, with no explicit per-request deadline/cancel handling. Fix it so a failed or slow connector read cannot block the entire Displays tab or obscure the graphics block.

## 1.5 Quick Settings current structure

`pwa/nuxel-home/index.html` has two `.qs-row` containers:

- Row 1: Wi-Fi, Bluetooth, Mobile, Location.
- Row 2: DND, Flashlight, Rotate, Settings.

`pwa/nuxel-home/js/qs.js` handles panel state and provider integration. The panel has separate compact/expanded states; CSS in `pwa/nuxel-home/css/status-bar.css` gives `.quick-settings.expanded` a full-screen/vertical-scroll treatment.

Add a third row after the existing two. Keep the existing order and behavior of rows 1 and 2. Reveal row 3 only when fully expanded. It contains NFC, Fingerprint, Camera and Microphone privacy actions.

## 1.6 Status bar current behavior

Status markup:

- `#status-signal`
- `#status-wifi`
- `#status-bluetooth`
- `#status-battery`
- `#status-battery-pct`

`status-bar.js:_renderBluetooth()` already hides Bluetooth unless the provider confirms `powered === true`. Preserve this honest behavior.

`status-bar.js:_renderWifi()` currently clears its glyph, sets a state label and changes opacity/color, but it does not set `hidden` for `disabled`, `unavailable` or `unmanaged`. A Wi-Fi icon can therefore remain on the top bar even when Wi-Fi is not enabled. Add an explicit `wifiRadioOn`/capability state separate from connection state.

The current UI includes `safe-zones.js` and `statusbar-safezones.json`, but no user-facing per-icon visibility preference. Implement a separate durable user preference document; don't overload safe-zone coordinates with icon preferences.

## 1.7 Lock screen and system navigation are separate rendering layers

The Home index contains `#status-bar` and `#system-navigation` as DOM siblings, plus `#lockscreen` as a full-screen element. CSS currently gives the lockscreen `z-index:500` and the status bar `z-index:100`. This is not sufficient to guarantee invisibility throughout lock transitions, and it does not control the native dock.

The DOM navigation has:

- `#nav-back`
- `#nav-home`
- `#nav-recents`

The active native dock source in this archive is `tools/s10plus/a45/nuxel-navdock.c`. It is a Wayland layer-shell surface. Its window stacking is independent of DOM z-index. If it remains mapped, it can be seen over the lockscreen even if the DOM nav is hidden.

Create a consistent lock-state protocol between the session/host and native dock. Hide/unmap the native dock before the lockscreen becomes visible. Start hidden on process launch until lock-state has been resolved. Fail closed if lock state is unknown during a transition. Restore only after successful unlock and Home surface readiness.

## 1.8 LPM/charger boot — exact root cause

The repository contains a detailed root-cause document at `docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md` and policy at:

- `configs/nuxel/power/power.json`
- `configs/nuxel/bootmode/bootmode-guard.json`
- `configs/nuxel/bootmode/README.md`
- `tools/s10plus/a33/nuxel-bootmode-guard.py`
- `tools/s10plus/a33/kernel-patches/sec_ts-lpm-initcall-deferred-bind.patch`
- `tools/s10plus/a33/tests/test-bootmode-guard.py`

The root cause documented and previously measured on the handset:

1. S-Boot cold starts in low-power charging mode when it is powered on from OFF with a charger attached.
2. S-Boot passes `androidboot.mode=charger` on the kernel command line.
3. Samsung `sec_bat_is_lpm_check()` in `drivers/samsung/misc/sec_batt.c` sets cached `lpcharge=1` in an `__setup` callback.
4. `sec_ts_init()` in `drivers/input/touchscreen/sec_ts/y771/sec_ts.c` returns `-ENODEV` before `i2c_add_driver()` when `lpcharge==1`.
5. There is no bound touchscreen client, no `sec_touchscreen` input device, no `/sys/class/sec/tsp`, and no touch IRQ line on that boot.
6. The same style of LPM gate is documented in fingerprint (`qbt2000`) and Wacom driver paths.
7. `sec_ts` is built-in (`CONFIG_TOUCHSCREEN_SEC_TS_Y771=y`) and `/lib/modules/4.14.253` is absent. `CONFIG_KEXEC` is unset. Userspace cannot reload the driver or re-enter the kernel with a new command line during that same boot.

The existing userspace guard classifies the boot via `/proc/cmdline`, kernel logs and device registration evidence. It publishes:

- `/run/nuxel-bootmode.state`
- `/run/nuxel-bootmode.json`

Its optional normal reboot is gated. `allow_reboot` is false by default; other gates include explicit CLI acknowledgement, capture/owner locks, minimum uptime, cooldown and charger-present-plus-charging. It issues `systemctl reboot`, not a bootloader command. Existing docs state that a Linux-initiated normal reboot does not re-enter charger mode even with the charging cable still connected.

The current permanent patch candidate is marked `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED`. Its context is reconstructed and must be compared with the exact checked-out Samsung kernel source. It proposes deferred `sec_ts` binding but is not sufficient evidence that the full system exits charger-only mode; it may not handle fingerprint/Wacom; it must not be applied blindly.

The required product behavior is **normal interactive Nuxel from a cold charger-attached power-on**. A warm OS reboot with the cable connected is not the acceptance test. Audit all `lpcharge` consumers, bootloader arguments, initramfs and userspace mode selection before deciding whether a board-specific boot override, kernel patch or a safe transition strategy is correct.

Do not clear `lpcharge` globally until all uses have been inspected. Preserve battery, charger, thermal and PMIC safety. Do not use userspace to pretend a built-in driver exists after its initcall declined to register it.

## 1.9 TWRP/BOOT-only kernel recovery agreement

If kernel/BOOT image changes are necessary, the previous Nuxel recovery agreement applies as a safety framework, but current device state must be re-confirmed at the time of flashing:

- Device must actually be in TWRP and visible over the agreed USB path.
- Verify exact device/model/codename and correct BOOT partition from live read-only partition evidence; never guess.
- Read back the current known-good BOOT image before modification, copy it off-device, verify SHA-256, size and image structure. A repository dummy `boot-original.img` is not a backup.
- Modify only the explicitly authorized BOOT partition. Do not touch EFS, modem, PIT, vendor, userdata or unrelated partitions.
- Build exact ARM64 candidate with pinned source/config/toolchain and preserve complete logs/config diff/hash.
- Flash one candidate at a time via validated TWRP method. No raw `dd` from a general shell, no Odin/Heimdall/fastboot, no partition guessing.
- If new kernel boot hangs, bootloops, returns to TWRP, loses display/touch or fails critical services, stop and restore the verified prior BOOT image immediately.
- If it boots successfully, verify all existing good state and continue.
- If TWRP/USB is not visible, do repository/source work only and ask owner to make the recovery target available; do not flash blind.

## 1.10 GPU metrics current implementation

The S10+ rootfs builder already builds/installs `nuxel-metricsd` and its systemd service/socket. Reuse it.

`services/nuxel-metrics/nuxel-metricsd.c` currently reads:

- GPU utilization: `/sys/devices/platform/18500000.mali/utilization`, fallback `/sys/kernel/gpu/gpu_busy`.
- GPU clock: `/sys/devices/platform/18500000.mali/clock`, code assumes kHz and converts to MHz.
- GPU memory allocations: `/sys/kernel/gpu/gpu_memory`, code parses `TGID PID bytes` rows and sums bytes.
- System RAM budget/usage: `/proc/meminfo` (`MemTotal`, `MemAvailable`).

The JSON contains utilization, frequency and allocation fields with availability status.

`pwa/nuxel-home/js/system-monitor.js` displays GPU utilization, GPU clock detail and a GPU-memory allocation percentage relative to total system RAM. Its comment correctly says the S10+ GPU uses shared system RAM, not dedicated VRAM. Current Home markup labels the memory meter `VRAM`, which is potentially misleading. Change to `GPU MEM (shared)` or `VRAM*` with a clear shared-RAM detail.

Audit actual live sysfs formats/units. Validate parsing and memory accounting. Do not blindly assume the vendor table's every row is uniquely allocated memory; check the ABI and whether summing duplicates shared pages. Zero GPU clock may mean idle, not unavailable. A missing file is unavailable, not zero.

## 1.11 Owner's latest GPU state

The owner reports from the PWNAGE-48000 follow-up:

- Phoc holds three `/dev/mali0` descriptors and one `/dev/udmabuf` descriptor plus a `dmabuf_udmabuf` anonymous inode.
- kbase debugfs lists a GPU context owned by Phoc.
- `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-web` are active.
- Bridge reports `FRAMES_OK`, `decon_pan_failed=0`.
- `/run/nuxel-gpu-fallback` is absent.
- `/dev/fb0` restored at 1440×3040 / virtual 1440×6080.

The owner also states WebKitGTK/GTK GL remains software because GTK GL initialization fails and the current Mesa kbase path is surfaceless-only; WebKit Wayland EGL expects a DRM render node. A Wayland-enabled Mesa test was reverted after the same failure. The final `screencopy → fbdev` copy/upscale is still CPU work.

Preserve the working kbase compositor. Do not label the whole GUI/WebKit path fully accelerated merely because Phoc owns a kbase context. Keep per-layer graphics status.

---

# 2. GLOBAL SAFETY AND DATA-PRESERVATION RULES

1. No fake status. `ON`, `OFF`, `UNKNOWN`, `UNSUPPORTED`, `BLOCKED` and `ERROR` are distinct.
2. No broad privilege expansion for quick toggles. PWA calls a typed Bridge provider, which calls one bounded privileged owner.
3. Do not directly manipulate kernel nodes from browser JavaScript.
4. Preserve Wi-Fi/SSH, USB CDC console, serial diagnostics and a known-good normal boot path.
5. Preserve user data, Notes, photos, downloads, app data, credentials, authenticator vault, settings and layouts.
6. Do not weaken battery/thermal charging safety to eliminate LPM.
7. Do not disable SELinux or app sandboxing to make GTK/Flatpak apps display.
8. Do not replace the working Mali kbase/Phoc setup with an unverified graphics stack.
9. Preserve the single `/dev/fb0` owner (`nuxel-wl-fb`); no second framebuffer process.
10. Kernel/BOOT writes require active TWRP confirmation, exact partition verification, an off-device hashed known-good backup and an explicit owner-authorized flash step.
11. Never touch modem, EFS, PIT, vendor, userdata or any non-approved partition.
12. Do not run expensive graphics tests, sensor loops or high-frequency polling while the relevant UI surface is hidden.
13. Every service/API call must be bounded; every UI spinner must have a timeout and a visible final state.

---

# 3. PHASE A — SETTINGS RESPONSIVE LAYOUT, NO SIDEWAYS PAGE SCROLL

## 3.1 Requirements

Make Settings comfortable at the real phone viewport. The whole Settings page/panel must not pan sideways. The tabs rail may scroll horizontally as an isolated tab selector because the full list may exceed the available width.

Use a layout contract:

- `html`, `body`, `main`, `.panel`, `.card`, headings, `.row`, labels and every flex/grid child respect `max-width:100%` and `min-width:0`.
- page containers use `overflow-x:clip` with a safe fallback; keep vertical scroll.
- `main` must not inherit a wider intrinsic size from nested controls.
- flex children that contain code/labels set `min-width:0`.
- grid uses `minmax(0, 1fr)` or a responsive column strategy, not fixed minimum tracks that force the viewport wide.
- use `overflow-wrap:anywhere` for device paths, MAC addresses, renderer strings, package IDs, URLs and diagnostics.
- state/pre elements scroll internally only when the user intentionally interacts with that log area; they must not resize the entire page.
- The ten-zone safe-zone editor is responsive; either compress/wrap its controls or give it its own deliberately bounded internal scroller with a clear affordance. It cannot expand the full Settings document.
- theme cards and selectable controls wrap into one/two columns based on available space.
- buttons and selects fit the width and maintain useful touch sizes.
- preserve normal vertical pan and form controls; don't set `touch-action:none` on the body.

## 3.2 Test plan

For every panel, at minimum:

- 320×640
- 360×760
- 384×832
- 393×852
- 430×932
- portrait and supported landscape

Automated test checks:

- `document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1`;
- body/main/panel width and scroll bounds;
- tabs rail can scroll independently;
- no important control has a right edge outside viewport;
- keyboard open does not create a horizontal page pan;
- long status and error strings wrap.

Also physically swipe vertically and horizontally in each Settings panel. Vertical content scroll must remain smooth, while horizontal swipes over content must not slide the whole page. A horizontal swipe on the tab bar may move only the tab selector.

---

# 4. PHASE B — EVERY INSTALLED APP RESPONSIVE ON S10+

## 4.1 Inventory

Build a live inventory from:

- canonical Nuxel app registry;
- installed PWA manifests/app JSON;
- rootfs app tree;
- native `.desktop` entries;
- RPM packages;
- Flatpak app inventory if Flatpak actually works on the current kernel.

Do not hardcode a partial list. Include Home, Recents, Search, Quick Settings, Home Settings, lockscreen, Settings and every installed app. Include Files, Gallery/Photos, Notes, NuXTore, SnekByte, Media Player, Downloader, Authenticator, Safe Cleanup, DevMgmt, PenguInterface and all others actually installed.

## 4.2 PWA requirements

For each app:

- inspect viewport meta and app root sizing;
- eliminate fixed 800/1024px desktop widths and wide minimums;
- use responsive grid/flex layouts;
- keep one-column layouts for narrow screens where appropriate;
- make forms/dialogs, menus and selection bars fit the viewport;
- make buttons touch-sized and spaced;
- keep keyboard above bottom dock and prevent inputs from being hidden;
- prevent whole-page horizontal scrolling;
- support rotation changes and dynamic viewport sizing;
- check `100vh` vs `100dvh`/WebKit behavior where keyboard and safe area matter;
- test app iframe/window constraints and scroll ownership;
- preserve accessibility labels and focus behavior;
- don't mask overflow by shrinking text to unreadable sizes.

## 4.3 Native GTK and Flatpak requirements

- Probe actual screen geometry and compositor scaling.
- Check every installed native app's minimum window size and adaptive behavior.
- Prefer GTK adaptive widgets/libadwaita breakpoints where available; ensure forms/sidebar become stack navigation on a phone.
- Correct oversized toolbars, action buttons and table views; use touch scrolling and readable controls.
- Flatpak apps inherit the portal/session/display constraints; only call a Flatpak app responsive if the real installed sandboxed app opens on the handset and is usable.
- Do not modify the package app's security policies as a shortcut.

## 4.4 Deliverable

Create `docs/beta-finalization/live/evidence/pwnage-52000/app-responsiveness-matrix.md` with app ID, type, installed state, portrait result, landscape result, keyboard result, horizontal overflow result, navigation result and unresolved issue. Fix each active installed app, not just one representative.

---

# 5. PHASE C — REMOVE CHARGER-ONLY/LPM BOOT FROM THE NORMAL PHONE EXPERIENCE

## 5.1 Product outcome

When the phone is fully powered off and the owner connects a charger then powers it on, Nuxel should reach a normal interactive phone environment with working display and touchscreen. The user should not be stuck in low-power charging-only mode with no touch. Battery charging and thermal safety behavior must remain correct.

The exact cold charger-attached power-on is the acceptance test. A warm reboot after Linux is already running does not prove this.

## 5.2 Confirmed root cause

The archive root-cause document records:

```text
/proc/cmdline: androidboot.mode=charger
sec_bat_is_lpm_check: Low power charging mode: 1
sec_ts_init: Do not load driver due to : lpm 1
```

`sec_ts_init()` returns `-ENODEV` before `i2c_add_driver()`. The touchscreen is not registered at all. It is not a userspace touchscreen daemon problem.

The same class of gate is documented for fingerprint (`qbt2000`) and Wacom. The kernel driver is built-in, so `modprobe` cannot recover it. `CONFIG_KEXEC` is off, so userspace cannot replace/re-enter the kernel during the same boot.

## 5.3 Audit all LPM-related kernel consumers

Before editing the candidate patch:

1. Pin the exact vendor kernel source commit/revision matching the installed 4.14.253 image.
2. Search all kernel source for `lpcharge`, `androidboot.mode`, `sec_bat_is_lpm_check`, low-power charging, touch LPM checks, fingerprint LPM checks, Wacom LPM checks, display/panel LPM checks and charger animation/init behavior.
3. Determine whether `lpcharge` affects charging current, thermal constraints, backlight, watchdog, suspend, battery UI, touch, fingerprint and other drivers.
4. Inspect bootloader cmdline and `boot/s10plus` packaging/bootargs to determine whether a board-specific Nuxel interactive boot flag can safely override only the reduced-OS behavior while preserving charger safety.
5. Inspect initramfs/systemd bootmode handling. Confirm whether Nuxel userspace itself is also selecting a reduced boot target when `androidboot.mode=charger` is present.
6. Distinguish the Samsung bootloader charging interface from Linux low-power charging mode; do not assume changing the UI removes the kernel state.

Do not globally zero `lpcharge` as a first reaction. Do not remove thermal/PMIC protections. Do not bypass input regulator/IRQ sequencing.

## 5.4 Kernel fix requirements

The checked-in candidate `tools/s10plus/a33/kernel-patches/sec_ts-lpm-initcall-deferred-bind.patch` is marked not deployed and contains reconstructed context. Validate it against the exact vendor source before modifying or applying it.

The final fix must:

- allow an interactive Nuxel boot with charger connected;
- ensure touch controller I2C client, regulators, reset and IRQ are initialized safely;
- avoid an initcall crash, delayed-work race, invalid driver pointer or sleeping-in-atomic-context error;
- handle the LPM-to-normal transition correctly if the boot still starts with an LPM flag;
- address fingerprint/Wacom only if their drivers are truly supported and safe; no false capability claim;
- preserve battery/charging/thermal protections;
- degrade gracefully if one input device fails rather than blocking all Nuxel startup;
- be built from pinned source/config/toolchain and included in a reproducible BOOT image.

The proposed patch currently focuses on registering `sec_ts` while postponing sensing, but that may not fully remove LPM or cover all gated devices. Review it as a proposal. If a dedicated boot override is used, document it precisely, test all consumers and ensure it is not a general bypass for safety-related LPM behavior.

## 5.5 Gated normal-reboot transition

The existing userspace guard in `tools/s10plus/a33/nuxel-bootmode-guard.py` publishes accurate mode and touch status. Config defaults `allow_reboot:false`. It requires explicit request and acknowledgement, owner locks clear, uptime floor, cooldown, and charger-present-plus-charging. Preserve these safeguards.

If no permanent full-boot fix can be deployed immediately, an opt-in single normal reboot from LPM may serve as a controlled transition. It must not loop, must visibly explain why, and must never auto-reboot on unknown charger state. Do not call this a permanent fix.

## 5.6 TWRP recovery process

Any kernel/BOOT change must use this strict process:

- Confirm the phone is currently in TWRP and visible over the agreed USB transport; do not assume a past ADB state.
- Read exact partition map/model/codename; confirm BOOT partition target by read-only evidence.
- Read back current live working BOOT image to on-device and off-device backup locations; verify SHA-256, size, structure and provenance. A dummy repository `boot-original.img` is not acceptable.
- Preserve a known-good restore image and have the restore method prepared before flashing.
- Build exactly one candidate and check kernel config, DTB, initramfs, image format, ARM64 architecture and `beyond2lte` device identity.
- Flash only the authorized BOOT target. No EFS/modem/PIT/vendor/userdata or other partition writes.
- First boot and verify normal/charger-attached behavior plus touch, display, battery, Wi-Fi/SSH, USB console, kbase, Phoc and `nuxel-wl-fb`.
- If it hangs, bootloops, returns to TWRP, loses input/display or fails core services, stop immediately and restore the verified prior BOOT image. Verify old system before continuing.
- Do not perform multiple speculative flashes. Do not flash if TWRP/USB is not present.

---

# 6. PHASE D — LOCKSCREEN PRIVACY: NEVER SHOW STATUS BAR OR NAV DOCK

## 6.1 Exact requirement

When locked, never display:

- Home top status bar/time/signal/Wi-Fi/Bluetooth/battery icon cluster;
- DOM Back/Home/Tabs navigation buttons;
- native Back/Home/Tabs layer-shell dock;
- app drawer, Home dock, Recents, search, Quick Settings or app content.

This must hold from first lockscreen paint through unlock. A single one-frame leak is a failure.

## 6.2 One lock-state authority

Inspect current lock state in `lockscreen.js`, the PWA host/session and `nuxel-navdock.c`. Define one authoritative lock-state transition that is consumed by DOM and native dock. The native host must not guess from a CSS class.

Sequence on lock:

1. Mark session lock state authoritative.
2. Prevent new application focus/launch.
3. Hide/inert top bar and DOM nav.
4. Send native dock hide/unmap command and confirm it is unmapped/inactive.
5. Show lockscreen surface.

Sequence on unlock:

1. Authenticate/unlock through existing policy.
2. Ensure Home content is ready.
3. Update session lock state.
4. Reveal top bar and dock.
5. Re-enable nav input only after visible state is correct.

On native dock process start, if lock state is unknown, start hidden until the host provides a definitive unlocked state. On lost IPC during lock, fail closed.

Do not rely on `z-index` alone. The existing lockscreen's z-index 500 vs status bar 100 hides some content visually, but native layer-shell is separate and transition flashes remain possible.

## 6.3 Tests

- lock from Home;
- lock while PWA is open;
- lock while native GTK app is foreground;
- cold boot to locked state;
- display-off/wake;
- Home/host/WebKit reload while locked;
- PWA host restart;
- native dock restart;
- lock/unlock racing with screen rotation;
- native app launch request while locked.

Assert hidden state at DOM and native host level, no clickable hidden controls, no QS gesture and no frame where nav/topbar appears.

---

# 7. PHASE E — TOP STATUS ICONS: PROVIDER-TRUTH AND USER VISIBILITY

## 7.1 Visibility formula

For each icon, keep distinct:

- user preference `show` or `hide`;
- hardware capability `supported` / `unsupported` / `unknown`;
- live state `on` / `off` / `unknown` / `transitioning`;
- relevance condition (e.g. USB link active, notification pending).

The visible rule should be equivalent to:

`visible = user_preference_show && supported && state_is_relevant && !lockscreen_active`

Do not conflate the preference with the underlying radio/service. Hiding the icon must not turn off Wi-Fi, Bluetooth, NFC or Location.

## 7.2 Fix Wi-Fi visibility

`status-bar.js:_renderWifi()` currently always draws the Wi-Fi glyph and dims it when not connected. Add a separate radio-powered state. Hide the icon for known OFF/unavailable/unmanaged states; if radio is ON but disconnected, show an appropriately neutral enabled-but-not-connected glyph if user preference allows it. Unknown must not render as a confident active connection.

## 7.3 Preserve Bluetooth correctness

Bluetooth already hides when powered state is not true. Ensure user preference can additionally hide it. If unknown/provider error, do not preserve a stale visible ON glyph.

## 7.4 All top-bar icons user-configurable

Add a Screen Settings card called `Status Bar Icons`. Build the settings list from actual rendered status-bar icon registry so new indicators cannot be omitted later. Include currently supported icons:

- Time (if product wants it configurable);
- mobile/cellular signal;
- Wi-Fi;
- Bluetooth;
- NFC;
- Location;
- USB/file-transfer/console;
- sound mode/vibrate/silent;
- battery;
- battery percentage;
- any additional real status icons discovered in current app.

Each item has a checkbox/switch. Provide live preview, Save (if not immediate), Restore Defaults and an explanation that hiding an icon never disables the service.

Persist through the validated Bridge config/settings store to a separate document such as `/etc/nuxel/display/statusbar-icons.json` with schema version/migration. Merge unknown keys and validate types; no direct filesystem access from PWA.

When a preference is hidden, remove layout width and exclude it from status-bar overlap calculations. Reapplying a show preference must hydrate from fresh provider state.

## 7.5 Tests

- Each icon preference hidden/shown;
- radio off hides regardless of preference (unless explicitly configured to show a disabled-state badge; default is hidden);
- user hide takes precedence over on-state;
- user show does not force a fake icon when provider unsupported;
- unknown provider never becomes ON;
- no stale icon after radio shutdown;
- settings survives Home/Settings restart;
- all icons fit safe zones and rotations.

---

# 8. PHASE F — EXPANDED QUICK SETTINGS PRIVACY CONTROLS

## 8.1 Layout

Keep existing two rows exactly in place. Add row 3 beneath them and show it only when the panel is fully expanded:

| Third-row tile | Meaning |
|---|---|
| NFC | Real NFC radio enable/disable |
| Fingerprint | Allow/disable biometric unlock (not direct sensor sysfs power) |
| Camera | System-wide camera privacy block/allow |
| Microphone | System-wide capture mute/unmute |

Use existing custom Nuxel Quick Settings icon pack assets when applicable. The `25-camera-disabled.png` and `24-microphone-muted.png` assets may be used as OFF/privacy art; make ON state visible through consistent active-state presentation or additional matching art. Do not make all tiles the same icon regardless of state.

## 8.2 NFC

Use one canonical Bridge NFC provider. Read real controller, driver, firmware and state. Toggle only through the provider owner. If unsupported, show a disabled tile and reason. Do not treat a config file or UI preference as an actual powered controller.

## 8.3 Fingerprint

Interpret as a switch controlling whether the existing security manager accepts fingerprint as an unlock factor. It does not power the sensor directly. Turning it off disables biometric unlock but preserves enrolled data and mandatory PIN fallback. Enable only when secure sensor/TEE provider and enrollment are truly ready. No raw fingerprint templates, sysfs register writes or fake success.

## 8.4 Camera privacy

Implement a true Nuxel-wide camera capture policy through one privileged owner/capability broker:

- OFF blocks new capture sessions across Nuxel applications;
- handle/revoke currently active camera streams, or report honestly if a current stream cannot be revoked;
- ensure PWA/Bridge camera APIs, native V4L2 applications and other sessions respect the policy;
- no blind `killall` or killing unrelated processes;
- no arbitrary `/dev/video*` chmod/chown from JS;
- report camera hardware present, active session count, policy state and exact failure;
- ON means camera use is permitted, not active.

If universal enforcement cannot be implemented on the current kernel/session, call the tile `Camera access` and scope it accurately rather than claiming a physical shutter.

## 8.5 Microphone privacy

Use the actual PipeWire/WirePlumber/ALSA capture control owner:

- mute all capture sources/system capture sessions when privacy mute is enabled;
- apply to new streams as well as existing streams;
- restore only when user turns mute off;
- survive PipeWire restart and device reconnect;
- do not mistake speaker volume mute for microphone capture mute;
- test with a temporary synthetic/near-silent sample and verify no meaningful capture is obtained while muted;
- do not store private recording data.

If a hardware capture device cannot be globally blocked, clearly report scope and limitation.

## 8.6 State synchronization and UI lifecycle

- One provider/manager per function, no competing UI polling.
- State reads on panel open and immediately after provider actions.
- UI changes only after backend acknowledgement.
- Unknown, unsupported, busy and error are visible distinct states.
- Long press/drag/scroll cannot accidentally toggle a tile.
- The row only exists in expanded layout; compact panel stays unchanged.
- Stop polling/cancel stale responses when panel closes.
- Add D-Bus/Bridge change event subscriptions where stable, otherwise bounded visible-only polling.

---

# 9. PHASE G — FIX GPU METRICS AND ACCELERATION CLAIMS

## 9.1 Preserve existing collector

The builder already compiles and installs `nuxel-metricsd` and its service/socket. Extend it; do not create an independent metrics daemon.

`nuxel-metricsd.c` currently has the following assumptions:

- `utilization` or `gpu_busy` parses as a percentage 0–100;
- vendor clock is kHz and converted to MHz;
- `/sys/kernel/gpu/gpu_memory` has `mem_used` header and lines `tgid pid bytes`;
- summing `bytes` yields used GPU memory;
- `MemTotal` is the GPU memory budget.

Validate all these on the active kbase kernel. The owner has reported a successful kbase GPU context from Phoc, but this does not automatically validate the metrics sysfs ABI. Do not report fabricated data if a node is missing.

## 9.2 Frequency and utilization

- Read active GPU frequency from the correct driver node and validate units by comparing against available frequencies/devfreq/current clock where exposed.
- Handle zero while idle as valid only if the live driver semantics confirm it.
- Verify utilization node is in percent. Some vendor drivers expose a value/string with a different meaning; normalize only after confirming source semantics.
- Validate 0–100 and reject malformed/out-of-range values.
- Expose sample timestamp and stale indicator.
- Keep GPU frequency and utilization separate: utilization is a load percent; frequency is current clock in MHz.
- Never put MHz in the percentage gauge or percent in the clock detail.

## 9.3 GPU memory accounting

- This SoC shares system DRAM; do not label the pool as dedicated VRAM.
- Inspect actual `gpu_memory` format and confirm whether each table row represents a process, a context, an allocation or an aggregate.
- Determine whether summing bytes double-counts shared allocations or multiple contexts.
- Handle PID exit/race and malformed records.
- If the source reports only tracked allocations, label the metric `Tracked GPU allocations (shared RAM)`.
- Use total system RAM as a documented *upper bound/budget reference*, not as physical VRAM capacity.
- If no reliable budget is available, display used allocation amount only and set percent unavailable.
- Present units (MiB/GiB) and update status truthfully.

## 9.4 Metrics JSON contract

Preserve existing fields used by `system-monitor.js`, while adding provenance/status fields. Recommended conceptual fields:

```json
{
  "gpu_percent": 23.4,
  "gpu_status": "ok",
  "gpu_util_source": "/sys/devices/platform/18500000.mali/utilization",
  "gpu_frequency_mhz": 468,
  "gpu_frequency_status": "ok",
  "gpu_frequency_source": "...",
  "gpu_memory_kib": 123456,
  "gpu_memory_total_kib": 8000000,
  "gpu_memory_status": "ok_shared_budget_reference",
  "gpu_memory_kind": "tracked_shared_allocations",
  "timestamp_ms": 0
}
```

Example only; use actual schema/units and no fake numeric placeholders. `null` means unavailable; zero means an observed value of zero.

## 9.5 GPU label suffix `(ACC)` / `(A)`

Add a canonical renderer status that distinguishes:

- Phoc compositor uses kbase GPU renderer;
- GTK GL initializes and renders with hardware GPU;
- WebKitGTK accelerated compositing is active in the Home/Settings WebKit process;
- final display bridge still does CPU copy/upscale into fbdev;
- fallback directory/state.

The Home system monitor's label represents the live interactive UI environment. Show `GPU (ACC)` only when the acceleration status provider proves the primary GUI path relevant to the meter is actually accelerated. If Phoc is accelerated but WebKitGTK is software, show `GPU (PARTIAL)` or keep `GPU` without `(ACC)`, with a clear tooltip explaining the partial state. Never mark everything accelerated just because `/dev/mali0` exists or Phoc has a context.

The label must update when renderer status changes and clear if the proof becomes stale/failed. The Graphics Settings card remains the authoritative detailed breakdown.

## 9.6 Home meter labels

- GPU meter main value: utilization percent.
- GPU detail: current MHz.
- GPU label: `GPU`, `GPU (ACC)`, or `GPU (PARTIAL)` as defined.
- Memory meter label: `GPU MEM` / `VRAM*` with explicit shared-memory explanation.
- Main memory meter remains separate from GPU allocation meter.
- Do not conflate process allocations with total GPU memory hardware capacity.

---

# 10. PHASE H — GRAPHICS ACCELERATION BLOCK BEFORE EXTERNAL CONNECTORS

## 10.1 Panel order

In `pwa/nuxel-apps/settings/index.html`, the `#tab-displays` panel should be ordered:

1. **Graphics Acceleration** block.
2. Existing **External display (USB-C / HDMI)** connector discovery block.

The Graphics block must be visible immediately when the panel opens and must not depend on external monitor scanning.

## 10.2 Fields

Render actual values for:

- GPU model/device (e.g. Mali-G76 MP12 if confirmed);
- kernel GPU driver and version (`mali_kbase`/vendor or Panfrost);
- `/dev/mali0` present/permission state;
- active GPU context proof where readable;
- EGL vendor/version/display platform and initialization status;
- GLES version/renderer string from a working test process;
- Phoc renderer backend and GPU/software status;
- GTK GL initialization/render status;
- WebKitGTK acceleration/compositing status and exact failure reason;
- DMA-BUF/udmabuf availability, import/export and modifier support only if actually tested;
- `nuxel-wl-fb` current state, FRAMES_OK, fps, blit averages and DECON pan failures;
- final display output path: framebuffer/DECON or DRM/KMS;
- global verdict: ACCELERATED / PARTIAL / SOFTWARE / UNKNOWN / ERROR.

Do not confuse external monitor DRM connectors with GPU render-node support. `/dev/dri` may be absent in the vendor kbase environment; the new provider must report the active backend without using connector presence as its GPU-acceleration verdict.

## 10.3 API design

Create a dedicated Bridge namespace such as `graphics.status` and `graphics.test` (or follow current Bridge naming standards). It must be read-only for status and bounded for test. It must not write GPU registers/sysfs/debugfs or change EGL libraries.

Status should be quick (2–3 second timeout) and gather cached/latest provider state where appropriate. Expensive active rendering test should require explicit button press and have a separate timeout.

Return structured error/status per subcomponent; one failed EGL probe must not suppress valid kbase, Phoc or framebuffer information.

## 10.4 Independent refresh and no infinite spinner

- Graphics block refresh is independent of external DisplayProvider.
- External connector refresh uses separate state and separate cancellation.
- Use per-request IDs/AbortController or Bridge cancellation to discard stale results.
- Every promise resolves to success/error/timeout; no forever spinner.
- Don't call a long GPU rendering test on every Settings refresh or a 4-second developer polling interval.
- If no response, show `Timed out — last successful sample at <time>` rather than blank “Checking…” forever.
- When navigating away, stop visible-panel polling and ignore stale results.

## 10.5 Fix duplicate IDs and developer refresh coupling

Rename all duplicate status IDs and update:

- `hardware-settings.js:renderDisplays()`;
- `refreshDisplays()`;
- `settings.js:refreshDev()`;
- any other `getElementById('display-state')` callers.

Developer refresh should update only the Developer panel's own elements. It must never overwrite the Graphics or External Displays section. Add unique-ID tests for all Settings pages.

## 10.6 Graphics test button

`Run Graphics Test` should create a tiny, known Wayland GLES rendering workload in the same Phoc user session, retrieve actual EGL/GLES vendor/renderer strings, render frames and verify completion. It must be isolated and must not restart Phoc or replace shared libraries. If the current kbase stack can render only surfaceless but cannot import into the compositor, report that clearly. Clean up surfaces, file descriptors, buffers and processes even on failure.

---

# 11. PHASE I — REGRESSION TESTS AND QUALITY GATES

## 11.1 Settings responsive tests

- no duplicate IDs;
- no horizontal overflow at five phone widths;
- only tab rail can scroll horizontally;
- safe-zone editor remains reachable;
- all controls accessible with keyboard open;
- portrait/landscape.

## 11.2 App responsive tests

- enumerate all installed apps;
- launch each active PWA and test content, scroll, forms, modal, keyboard and viewport;
- launch representative GTK and Flatpak apps, and inventory every installed package result;
- no accidental desktop min width;
- no clipping behind bottom dock or safe area.

## 11.3 Charger/LPM tests

- guard offline fixtures: normal boot, LPM boot, prose-only charger mention, unknown cmdline;
- reboot gate tests preserve explicit acknowledgement/owner locks/uptime/cooldown/charger check;
- kernel patch compiles against exact source and passes static review;
- driver probe failure does not block rest of system;
- cold boot from powered-off with charger attached must give normal Nuxel UI and physical touch;
- touch, fingerprint and Wacom status reported individually;
- charging and thermal protections remain correct;
- normal boot without charger still works;
- cable inserted after boot does not trigger LPM transition.

## 11.4 Lock screen tests

- no status bar visible on lock;
- no DOM navigation visible;
- native dock unmaps/hides;
- no flicker across boot, wake, host restart, app transition or rotation;
- hidden controls are inert;
- unlock restores topbar/dock only after authentication.

## 11.5 Status icon tests

- Wi-Fi off/disconnected/on states;
- Bluetooth off/on/unknown;
- NFC off/on/unsupported;
- location off/on/unknown;
- every individual icon preference;
- user hidden wins over on;
- provider off wins over preference show;
- no stale layout reservation/overlap.

## 11.6 Quick Settings privacy tile tests

- third row hidden when collapsed;
- row appears below first two only when expanded;
- NFC actual provider state;
- fingerprint policy toggle with PIN fallback;
- camera privacy enforced across supported app API paths;
- microphone capture mute enforced across existing/new streams;
- unsupported/unknown correctly rendered;
- no stale updates after close.

## 11.7 GPU metrics tests

- parser fixtures for live Mali utilization values, units, malformed values, missing files, zero idle, stale values;
- frequency parsing and conversion;
- GPU memory table format, duplicates/shared allocations, malformed/negative/overflow cases;
- RAM budget reference semantics;
- N/A vs zero;
- Home label suffix proof and stale clear;
- metrics endpoint remains socket-activated and does not poll when Home is hidden.

## 11.8 Graphics Settings tests

- Graphics block is first in Displays tab.
- External connector provider timeout does not block GPU status.
- GPU status timeout exits spinner and shows reason.
- Duplicate state IDs absent.
- refreshDev does not overwrite Screen/Graphics/External sections.
- Run Graphics Test reports actual renderer and cleans up even on failure.

---

# 12. PERFORMANCE AND VISUAL REQUIREMENTS

- Preserve the existing kbase-accelerated Phoc state and avoid unnecessary GPU stack reconfiguration.
- Home `system-monitor.js` should continue polling only while Home is visible; do not add another interval for the Graphics panel.
- Quick Settings polls only while visible.
- Graphics tests are user-initiated and bounded.
- Settings responsive layout should not force expensive layout thrashing on each scroll.
- Use `min-width:0`, stable container dimensions and lightweight transitions.
- Avoid full-screen blur/backdrop filters and large soft shadows on the software/partially accelerated path.
- No perpetual animation for status icons or privacy tiles.
- When hidden, topbar icons should not still create invisible layout cells.
- Keep the native dock lock protocol event-driven; do not poll lock state at high frequency.

Measure:

- Settings tab open to interactive;
- vertical scroll frame cadence and any horizontal drift;
- app cold/warm first paint and orientation resize;
- lock/unlock first frame;
- Quick Settings expand/collapse;
- Graphics status response time;
- GPU metrics age and read time;
- startup time from kernel/userspace milestones to interactive Home;
- charge-attached cold boot time until actual touchscreen is ready.

Don't claim performance improvements without before/after measurements.

---

# 13. LIVE DEVICE DEPLOYMENT AND RECOVERY

## 13.1 Staged software deployment

- Use the existing configured Wi-Fi SSH or USB console target; do not guess IP/credentials.
- Back up every replaced file/unit/config first.
- Stage a versioned deployment directory; verify SHA-256 and ARM64 binary architecture.
- Atomically replace assets/configs where possible.
- Restart only the affected service.
- Don't restart Phoc/`nuxel-wl-fb` merely to refresh a PWA stylesheet.
- Keep the only framebuffer owner alive.
- Preserve SSH and USB CDC console.

## 13.2 Kernel/BOOT deployment

Only if Phase C proves a kernel change is necessary and the TWRP gate is satisfied. One candidate, one controlled flash, immediate validation, immediate rollback on hang/failure. The agent must not silently continue with other changes after a failed kernel boot.

## 13.3 Rollback order

- UI/CSS/PWA cache changes: restore previous asset bundle/service-worker version.
- Statusbar config: restore previous JSON and rehydrate.
- Quick Settings: disable unsupported provider tile/restore prior script.
- Metrics: restore prior daemon binary and service.
- Graphics provider: remove new API/unit without touching GPU driver state.
- Kernel: restore exact verified prior BOOT image via TWRP; verify Nuxel normal boot and known-good display/touch/SSH before anything else.

---

# 14. REQUIRED DELIVERABLES

Create/update:

1. `docs/beta-finalization/live/PWNAGE-52000-TODO.md`.
2. `docs/beta-finalization/live/evidence/pwnage-52000/` containing:
   - baseline state;
   - Settings overflow measurements/screenshots;
   - installed app responsiveness matrix;
   - lockscreen hidden-state captures/logs for DOM and native dock;
   - status icon preferences/provider fixtures;
   - expanded Quick Settings screenshots and backend test evidence;
   - raw GPU metric samples/units and parser tests;
   - Graphics Settings status output and graphics smoke test logs;
   - charger/LPM cold boot logs, source patch review, kernel build hashes and physical touch proof;
   - TWRP backup hashes and flash/rollback record if a kernel change is performed.
3. Source changes to the active PWA/Settings/Bridge/providers/metrics/boot/kernel build path.
4. Regression tests and clean ARM64 rootfs/package checks.
5. PWA cache version updates for every changed asset/script.
6. Exact deployment/restart/rollback instructions.
7. Final report with confirmed root causes, files changed, test commands/counts, owner physical checks, remaining blockers and a truthful PASS/FAIL/UNSUPPORTED matrix.

No credentials, raw fingerprint templates, private keys, authenticator seeds, personal audio or unrelated Notes contents may enter the evidence bundle.

---

# 15. FINAL ACCEPTANCE MATRIX

| Feature | Pass condition |
|---|---|
| Settings horizontal scroll | Page content cannot pan sideways; all tabs remain reachable. |
| All apps responsive | Every installed PWA/native/Flatpak app is usable within S10+ viewport; no broad horizontal overflow or clipped essential controls. |
| Charger cold boot | Power on from OFF with charger attached reaches normal Nuxel session and touch works. |
| Lock screen | Status bar and DOM/native three-button dock are never visible while locked, including transitions. |
| Top-bar icons | Radios/features OFF/unsupported are hidden; user can individually hide every icon. |
| Quick Settings privacy row | NFC, Fingerprint-auth policy, Camera privacy and Microphone mute work below first two rows in expanded mode. |
| GPU speed | Actual current GPU clock and utilization are correct, units verified. |
| GPU memory | Tracked shared GPU allocations are correctly counted and not presented as dedicated VRAM. |
| GPU ACC suffix | Appears only when the current relevant GUI path is truly accelerated; partial state reported distinctly. |
| Graphics Settings | Graphics card appears before external connectors and renders independently without spinner lock. |
| Existing stack | kbase/Phoc/`nuxel-wl-fb`/DECON working path remains intact. |

A hardware-dependent feature may be `UNSUPPORTED` or `BLOCKED_KERNEL` only after evidence proves the limitation. A missing provider must not be marked PASS. The charger cold-boot requirement is not satisfied by the existing gated warm-reboot mitigation alone.

**PWNAGE-52000 is complete when the phone is responsive, privacy surfaces are correct, charger-connected cold boot is interactive, GPU status is honest and the actual UI/metrics state is proven on the S10+. No fake ON states, no duplicate DOM IDs, no silent kernel regressions and no permanent lockscreen UI leakage.**

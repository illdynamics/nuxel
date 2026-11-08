# Nuxel — All 31 repair prompts (reading/reference edition)

**Do not send this entire book to a coding agent at once. Use each individual file.**



---

# NUXEL REPAIR 01 — Bottom navigation dock artwork and layering

**Priority:** P0  
**Prerequisite repair IDs:** 04,31  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

The three-button Back/Home/Recents region has supplied custom artwork; the owner reports dock backgrounds absent on the live screen. Source image presence is not proof of visible rendering. Do not confuse navigation bar background with the separate four-app dock.

## Inspect these repository paths first

- `pwa/nuxel-home/css/launcher.css`
- `pwa/nuxel-home/index.html`
- `pwa/nuxel-home/assets/branding/button-left.png; button-middle.png; button-right.png`
- `pwa/nuxel-home/sw.js`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`

## Required engineering work — execute all items

1. Trace which DOM element encloses the *navigation* three-button bar, and its height, stacking contexts, z-index, clipping and transforms in WebKitGTK. Determine whether custom navigation artwork is separately supplied; do not accidentally paint BG1/BG2 behind system buttons.
2. Identify the actual active webroot and image URL; compare source/deployed SHA-256, HTTP status/MIME and computed CSS background-image. Audit parent backgrounds, safe-area inset and overscan with portrait/landscape.
3. Use a dedicated noninteractive pseudo-element behind the three button hitboxes, preserving SVG/PNG crisp edges and transparent space. Do not use an opaque blue rectangle as a default when custom artwork is configured.
4. Preserve pointer ownership for short Back, long Back, Home and Recents; test taps at boundaries. Ensure animations and page transitions do not send the bar behind another surface.
5. Add a DOM/CSS integration test and a diagnostic capture of computed style, element bounding boxes and visible framebuffer. Deploy only userspace web assets via the existing USB path with cache-version bump.

## Acceptance gates (all required for completion)

Artwork actually visible across full intended bottom width on S10+; Back/Home/Recents accept single touches and long-hold; no clipping, accidental scroll or overlapping panel in either desktop; survives launcher restart/reboot.

## Evidence to collect

Phone screenshot plus owner confirmation; asset SHA-256, resource HTTP 200, computed DOM stacking report, and recorded three-button event sequence.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 02 — Four-app dock BG1/BG2 invisible or unswitchable

**Priority:** P0  
**Prerequisite repair IDs:** 04,31  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Owner reports no bottom app-dock artwork, and dock setting cannot switch correctly; A39/A43 asset hash tests pass but do not establish WebKit presentation. `.dock::before` had stacking fixes but still lacks on-device proof.

## Inspect these repository paths first

- `assets/nuxel-bottom-bar.jpg`
- `assets/nuxel-bottom-bar2.png`
- `pwa/nuxel-home/assets/nuxel-bottom-bar.jpg`
- `pwa/nuxel-home/assets/nuxel-bottom-bar2.png`
- `pwa/nuxel-home/css/launcher.css`
- `pwa/nuxel-home/js/launcher.js`
- `pwa/nuxel-home/js/home-settings.js`
- `pwa/nuxel-home/js/settings-store.js`

## Required engineering work — execute all items

1. Trace Home Settings selected dock ID → persistent store → render state → `.dock` CSS class/style → before pseudo-element → live resource path → WebKit compositor. Capture computed `content`, `background-image`, opacity, z-index, width/height, and parent `overflow` on phone.
2. Confirm BG1 is `nuxel-bottom-bar.jpg`, BG2 is `nuxel-bottom-bar2.png`, and BG2 is default when no saved preference. Validate PNG alpha and avoid an opaque wrapper over its transparent corners.
3. Correct stylesheet specificity and actual app-dock layer, keeping background above wallpaper but behind four tappable app icons; never use negative z-index inside an opaque stacking context without proof.
4. Make switch immediate, preserve user layouts, prevent service-worker stale CSS, and deploy identical assets to the active webroot. If loaded image differs from screenshot, inspect WebKit repaint and compositing, not just source references.
5. Write tests for default/migration, toggling, persistence, URL/hash resolution, missing-asset fallback and no pointer interception.

## Acceptance gates (all required for completion)

Physical app dock displays BG2 after fresh preferences; BG1 immediately replaces it via Home Settings; both survive reload/reboot; four apps remain correctly positioned, responsive and stationary when pages slide.

## Evidence to collect

Two real phone screenshots BG1/BG2, actual computed styles and image HTTP fetches, source/deployed hashes, owner PASS/FAIL, preference value before/after reboot.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 03 — Quick Settings shade and notification panel graphics

**Priority:** P1  
**Prerequisite repair IDs:** 01,02,04,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Custom toggles and shade backgrounds are present in assets, but the physical WebKit rendering state is unverified. The full shade must remain scrollable and not obscure control hitboxes.

## Inspect these repository paths first

- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-home/css/style.css`
- `pwa/nuxel-home/index.html`
- `pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/`
- `pwa/nuxel-home/sw.js`

## Required engineering work — execute all items

1. Inventory which surfaces have actual supplied panel artwork; distinguish compact shade, fully expanded shade, per-toggle background and notification panel instead of applying one image everywhere.
2. Audit CSS computed layers after compact and expanded transitions; verify active source asset URLs, opacity, scaling, and noninteractive decorative layers.
3. Preserve 2-stage swipe down/up state transitions, rendering of toggles during screen rotation, and accessibility labels and touch hitboxes.
4. Use crisp scaling for pixel graphics when appropriate, keep transparent regions truly transparent, and measure the effect on repaint/animation cost.
5. Update build/deploy manifests and service-worker caches. Exercise visible panels over Home/Settings and log any missing assets or WebKit errors.

## Acceptance gates (all required for completion)

Compact and expanded Quick Settings art and custom toggles visibly correct, controls clickable, content scrolls, no boring blue fallback in areas designed for artwork, smooth reopen and persistence after reload.

## Evidence to collect

S10+ framebuffer captures for compact/expanded shades; network/HTTP asset receipts; computed CSS and gesture traces; owner confirmation.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 04 — Custom icon loading and WebKit asset/cache consistency

**Priority:** P0  
**Prerequisite repair IDs:** none  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Icon packs exist and some artwork has appeared on device before, but mismatched active webroots and stale WebKit service workers previously caused source-correct assets not to render.

## Inspect these repository paths first

- `pwa/nuxel-home/sw.js`
- `pwa/nuxel-home/js/apps.js`
- `pwa/nuxel-home/assets/branding/`
- `pwa/nuxel-apps/_shared/`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`
- `tools/s10plus/a39/tests/test_a39_assets.py`

## Required engineering work — execute all items

1. Enumerate active app, navigation and toggle icons from generated registries; assert every URL resolves on the actual phone web server, not just inside repository.
2. Verify filesystem staging, MIME, case sensitivity, transparent pixels and SHA-256 against source icon art. Fix missing registry entries, wrong absolute `/pwa` versus `/assets` URLs, and ignored assets when needed.
3. Trace service-worker fetch strategy and cache names; ensure build versions invalidate *code assets* without deleting layout/credential/user data. Avoid permanently caching broken 404s.
4. Check duplicate old icon renderers, CSS backgrounds and clipped controls after first boot, Home reload, Quick Settings reopen, and app-switching.
5. Add a manifest-based test that opens each registered image URL; instrument WebKit load errors and collect device screenshots for spot checking.

## Acceptance gates (all required for completion)

Every referenced custom icon returns a real image and is visibly correct in launcher, buttons, quick toggles and Browser/Settings without stale or duplicate rendering; no user data loss during cache refresh.

## Evidence to collect

Source + deployed hashes, URL status and MIME table, service-worker cache keys, real screen evidence for representative icons and owner sign-off.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 05 — Actual CPU utilization and frequency meter

**Priority:** P1  
**Prerequisite repair IDs:** 28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

A40 C telemetry collector exists but is omitted from fresh rootfs until image-parity repair; CPU percent must use `/proc/stat` deltas and MHz must be a *current* frequency, not a CPU marketing maximum.

## Inspect these repository paths first

- `services/nuxel-metrics/nuxel-metricsd.c`
- `services/nuxel-metrics/nuxel-metrics.service`
- `services/nuxel-metrics/nuxel-metrics.socket`
- `pwa/nuxel-home/js/system-monitor.js`
- `pwa/nuxel-home/js/home-settings.js`

## Required engineering work — execute all items

1. Audit daemon CPU sampling for first-read invalidity, jiffy wrap, idle/iowait/steal calculation and contention between multiple HTTP clients. Unit test known synthetic `/proc/stat` snapshots.
2. Read Exynos CPUFreq per-cluster sysfs with units and thermal scaling; choose/label a defensible representative displayed MHz, and handle offline cores.
3. Expose a stable read-only JSON schema through the existing local metrics socket, consume it without duplicate intervals and stop when Home hidden.
4. Provide ON/OFF, 1/2/3/5/10-second intervals (3-second default), and persistent settings; do not recreate the widget for each update.
5. Ensure systemd packaging in fresh image and live USB upgrade; compare daemon readings with a diagnostic independent of UI.

## Acceptance gates (all required for completion)

Under idle/load, CPU percent and current MHz change plausibly; unavailable values display N/A, not fabricated 100%; 3-second default; collector single instance and low overhead.

## Evidence to collect

Time-aligned source counters and UI screenshots on S10+; unit test fixture results; power/CPU overhead measurement; service status from fresh-built image.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 06 — Real RAM usage, percentage and quantities

**Priority:** P1  
**Prerequisite repair IDs:** 28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

RAM meter currently depends on metrics daemon; final.md requires MemTotal/MemAvailable-based used/total GiB and a truthful percentage on the Home widget.

## Inspect these repository paths first

- `services/nuxel-metrics/nuxel-metricsd.c`
- `pwa/nuxel-home/js/system-monitor.js`
- `pwa/nuxel-home/js/home-settings.js`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`

## Required engineering work — execute all items

1. Audit `/proc/meminfo` parser robustness for missing/reordered fields and kB units, use MemTotal−MemAvailable rather than naive MemFree, and bound 0–100%.
2. Ensure process/OS reservations are not accidentally presented as independent physical GPU VRAM. Mark unavailable when procfs cannot be read rather than guessing.
3. Update widget layout to show `RAM xx% · used/total GiB` without truncating on the S10+ resolution; review screen rotation.
4. Integrate with the shared 3-second metrics refresh and Home-hidden pause; validate no extra subprocesses/timers.
5. Run deterministic parser tests, live stress test and fresh-image systemd installation verification.

## Acceptance gates (all required for completion)

Reported utilization agrees within rounding with `/proc/meminfo`, updates under real workload, stays readable and persists preferences without growing CPU consumption.

## Evidence to collect

Meminfo snapshots, numerical calculations, device screenshots, service boot logs, and test outputs.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 07 — Mali GPU utilization and frequency

**Priority:** P1  
**Prerequisite repair IDs:** 28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

GPU metrics are conditional: driver instrumentation may not expose true utilization; the current UI may show N/A. Frequency is not utilization.

## Inspect these repository paths first

- `services/nuxel-metrics/nuxel-metricsd.c`
- `pwa/nuxel-home/js/system-monitor.js`
- `docs/s10plus-autonomous-boot-repair/`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`

## Required engineering work — execute all items

1. Inventory live Mali GPU driver implementation, `/sys/class/devfreq`, thermal/devfreq counters, busy/idle accounting, debugfs availability and permissions. Identify exact live interface and sampling units before writing a parser.
2. When driver exposes monotonic active/total time, compute percent from deltas with wrap/reset detection. Show per-GPU current frequency in MHz only if read from real clock interface.
3. Do not elevate daemon privileges or expose arbitrary debugfs unnecessarily. If no hardware busy counters exist, leave usage N/A and document precise kernel driver limitation without calculating an invented percentage.
4. Separate GPU utilization field from frequency status in collector schema/UI. Add fixtures for zero counters, missing nodes, wraparound and thermal scale changes.
5. Test while animating UI or a reproducible GPU load, comparing rate/trend with system instrumentation where available.

## Acceptance gates (all required for completion)

Actual utilization varies on load only if live driver provides trustworthy busy accounting; correct frequency displayed; honest N/A and specific blocker when instrumentation unavailable.

## Evidence to collect

Device sysfs/debugfs paths and contents, schema samples, bench trace, screenshots; no claim of driver support from file names alone.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 08 — Mali shared GPU allocation accounting

**Priority:** P2  
**Prerequisite repair IDs:** 28,07  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Current collector deliberately emits `gpu_memory_kib:null`; display says N/A because Mali uses shared system RAM. `final.md` asks for GPU-attributed allocation if genuinely exposed, not fictitious dedicated VRAM.

## Inspect these repository paths first

- `services/nuxel-metrics/nuxel-metricsd.c`
- `pwa/nuxel-home/js/system-monitor.js`
- `services/nuxel-metrics/README.md`

## Required engineering work — execute all items

1. Identify driver-specific allocation accounting (e.g. supported Mali memory data, dma-buf heap statistics, DRM GEM/cgroup mappings) and document whether it is attributable to the GPU rather than global shared memory.
2. Carefully distinguish reserved GPU heaps, dma-buf allocations used by several subsystems, total system RAM and genuinely GPU-attributable pages. Do not double-count.
3. If a defensible per-GPU measure exists, implement read-only sampling with supported units, provenance/source label and unavailable fallbacks. If not, preserve N/A and explain why a numeric meter is impossible without new instrumentation.
4. Implement counter and overflow tests and verify runtime permissions without privileged broad filesystem access.
5. Show `GPU MEM` as GiB/MiB only when metric is real; never imply the chip contains dedicated VRAM.

## Acceptance gates (all required for completion)

A numeric value is shown only with documented live allocation evidence and behaves under GPU memory pressure; otherwise honest N/A and explicit driver blocker are accepted as technically correct.

## Evidence to collect

Driver docs, runtime node/data samples, ownership accounting assumptions, baseline/load comparisons and owner-visible fallback.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 09 — S10+ Broadcom radio firmware and driver bring-up

**Priority:** P0  
**Prerequisite repair IDs:** 28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

NetworkManager software API is present, but no physical S10+ evidence proves WLAN enumerates, firmware loads, or scanning works. Chip/driver model must be confirmed by live PCI/SDIO/platform/device-tree evidence—not deduced from filename alone.

## Inspect these repository paths first

- `docs/wifi-bcm4390-status.md`
- `tools/s10plus/a33/nuxel-wifi-diag.sh`
- `configs/networkmanager/10-nuxel-s10plus-wifi.conf`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`
- `services/nuxel-bridge/src/bridge.py`

## Required engineering work — execute all items

1. Capture `uname -a`, relevant DT compatible nodes, `dmesg` firmware/PCIe/SDIO messages, `lsmod`, `modinfo`, `rfkill list`, `iw dev`, `nmcli -f GENERAL,IP4 dev show`, NetworkManager and wpa_supplicant logs.
2. Determine first break in power rails, bus enumeration, module bind, NVRAM/CLM and firmware, interface creation, rfkill, regulatory domain, scan. Inventory legal firmware assets already shipped, versions, board-specific NVRAM selection and chip ID.
3. Fix only verified device-specific files/service ordering/udev/systemd/NM conflicts; use the existing NetworkManager, never start a competing wpa_supplicant.
4. Validate state transitions after sleep/wake, radio off/on and one safe userspace reboot. Do not print SSID passwords or secrets in logs.
5. If required vendor firmware or kernel capability is missing, identify exact first failing node and prepare an offline patch plan; do not replace boot/kernel or claim success.

## Acceptance gates (all required for completion)

Real radio appears in `iw`, rfkill unblocked, scan returns nearby APs, can associate and remain stable across restart without disturbing USB console; no phantom Wi-Fi indicator.

## Evidence to collect

Anonymized hardware probe, kernel/firmware logs, first successful scan and NM status, driver and firmware hashes, owner-confirmed association.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 10 — Full NetworkManager-backed Wi-Fi Settings

**Priority:** P0  
**Prerequisite repair IDs:** 09,28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Existing `NetworkWifiScan/Connect/Disconnect/SetEnabled` D-Bus methods and a Wi-Fi tab cover only a subset of requested flows; saved networks, forget, hidden SSIDs and connection details are missing/incomplete.

## Inspect these repository paths first

- `pwa/nuxel-apps/settings/wifi-settings.js`
- `pwa/nuxel-apps/settings/settings.js`
- `pwa/nuxel-apps/settings/index.html`
- `services/nuxel-bridge/src/bridge.py`
- `services/nuxel-bridge/polkit/50-nuxel-bridge-network.rules`

## Required engineering work — execute all items

1. Extend existing `NetworkManagerConnector`, not a competing manager. Enumerate active + saved connections, AP BSSID/SSID/signal/security, grouped SSIDs, connection state/error, IPv4/IPv6/gateway/DNS and autoconnect flags.
2. Add per-app-scoped, validated D-Bus methods for forget/deactivate, connect existing profile, hidden SSID/profile creation, connection details; ensure access control via existing bridge permissions and polkit. Return structured errors rather than subprocess stderr.
3. Use NM secure settings agent/keyring mechanism; never log, echo, query-string, or store passphrases in localStorage. Treat WPA3 capability honestly and never silently downgrade authentication.
4. Finish Settings UI with scan/refresh, password prompt, connect/disconnect, saved/forget, hidden option, retry, progress and clear Wi-Fi-disabled/unavailable states. No credentials embedded in DOM logs.
5. Add fake D-Bus/NM integration tests for 401/access-denied, failed auth, wrong password, SSID collision, 2.4/5 GHz, hidden network, disconnect/reconnect, and redaction tests; live-test against an authorized AP.

## Acceptance gates (all required for completion)

Users can manage real network lifecycle in Settings, including saved/hidden entries and truthful IP/DNS details; no duplicate supplicant; password safe; reconnect survives reboot.

## Evidence to collect

NM connection metadata without secrets, UI screenshots, scan/connect/forget logs with redaction, saved profile lifecycle and live owner PASS/FAIL.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 11 — End-to-end IP, DNS, TLS, browser connectivity

**Priority:** P0  
**Prerequisite repair IDs:** 09,10,12  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Connected Wi-Fi does not prove internet. There is no S10+ receipt covering association, DHCP, route, DNS, HTTPS validation and actual browser rendering.

## Inspect these repository paths first

- `services/nuxel-bridge/src/bridge.py`
- `pwa/nuxel-apps/settings/wifi-settings.js`
- `pwa/nuxel-home/js/status-bar.js`
- `pwa/nuxel-apps/browser/`
- `tools/s10plus/a33/nuxel-wifi-diag.sh`

## Required engineering work — execute all items

1. Add an explicit bounded connectivity diagnostic with independent phases: carrier/association/auth, IPv4/IPv6, default routes, local gateway, DNS resolution, TCP/HTTPS TLS certificate verification, HTTP result and Browser navigation.
2. Use safe fixed known endpoints or user-configured probes with reasonable timeouts and no captive-portal credentials; avoid declaring success from a DNS cache or a 302 redirect without interpreting it.
3. Separate status enums radio unavailable / disconnected / authenticating / local only / captive portal / internet verified / certificate failure. Ensure UI refreshes on NM events rather than aggressive polling.
4. Distinguish Wi-Fi connection through NM from USB tether internet, to avoid false success when MacBook supplies network.
5. Write mocked failure-stage tests; capture real on-phone DNS and TLS output for one public HTTPS site and verify WebKit loads it normally.

## Acceptance gates (all required for completion)

After a real AP join, valid gateway/DNS/HTTPS and Browser page load succeed; breaking DNS/TLS produces accurate diagnostics; no false internet status from USB connectivity.

## Evidence to collect

Network device/routes (redacted), resolver result, TLS certificate chain verification, HTTP response and actual Browser screenshot.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 12 — Full native WebKit multi-tab Nuxel Browser

**Priority:** P0  
**Prerequisite repair IDs:** 10,11,28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Current Browser is an iframe using `view.src=target`, which fails framing-restricted sites and does not provide native top-level browser contexts, downloads or private sessions.

## Inspect these repository paths first

- `pwa/nuxel-apps/browser/index.html`
- `pwa/nuxel-apps/browser/js/browser.js`
- `pwa/nuxel-apps/browser/css/browser.css`
- `tools/s10plus/a33/nuxel-pwa-host.c`
- `pwa/nuxel-home/js/apps.js`
- `services/nuxel-portal/`

## Required engineering work — execute all items

1. First inspect actual GTK/WebKit host capabilities and existing app launch contracts. Design privileged native Browser UI/controller with real `WebKitWebView` (one per tab), proper signals (`load-changed`, title, progress, can-go-back/forward, download-started, TLS errors) and a narrow IPC surface—not general root/bridge access to sites.
2. Migrate Browser UI to address/search bar, tabs create/switch/close, history/bookmarks, find-in-page, refresh/stop, download status, user agent preference, mobile viewport and touch gestures.
3. For private mode create ephemeral WebKit data manager/context, no persistence of cookies/cache/history; ensure regular-profile state isolation and session clearing on close.
4. Implement download destination through a permission-scoped file portal, confirmation, filename validation and safe handling. Deny or request permissions for camera/location/mic; do not bypass TLS errors by default.
5. Test top-level sites with X-Frame-Options/CSP denial, TLS-valid/TLS-invalid pages, downloads, process crashes, back/forward, multi-tab, private cookies and OSK text entry.
6. Ensure fresh rootfs installs native host changes and browser exposes no privileged Nuxel JS APIs to arbitrary websites.

## Acceptance gates (all required for completion)

User opens a real HTTPS site that forbids framing, multiple tabs work and persist appropriately, private cookies vanish, downloads produce usable local files, TLS errors fail closed.

## Evidence to collect

Native window list/signal logs, real site screenshots, download SHA-256, browser privacy test and validated S10+ AArch64 binary.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 13 — Real filesystem File Explorer operations and security

**Priority:** P0  
**Prerequisite repair IDs:** 28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Current Files app caches `storage.list-dir` once, starts at `/`, navigates cached entries only, stores folder/create/delete changes in localStorage, has placeholder previews and unsafe `innerHTML` insertion of filesystem metadata.

## Inspect these repository paths first

- `pwa/nuxel-apps/files/js/files.js`
- `pwa/nuxel-apps/files/index.html`
- `pwa/nuxel-apps/files/css/files.css`
- `services/nuxel-portal/src/portal.py`
- `services/nuxel-bridge/src/bridge.py`

## Required engineering work — execute all items

1. Design and implement permission-scoped filesystem bridge/portal operations for list/stat/read/open/mkdir/rename/copy/move/delete-to-trash/restore; begin in the actual unprivileged user's home, not `/root`. Authenticate app identity at host boundary and do not trust JS-provided app IDs alone.
2. Implement server-side canonical path validation anchored to granted roots, symlink defense, ownership checks, race-safe operations where possible (`openat`/dirfds), bounded reads/uploads, and consistent errors. Never shell-interpolate names.
3. Replace cached path navigation with async per-directory reloads, breadcrumbs, back/forward, show hidden, storage roots, sorting/filtering and keyboard/touch selection. Render filenames using `textContent` or escaped nodes, not interpolated `innerHTML`.
4. Support multi-select mixed files/folders, clipboard copy/cut/paste, progress, conflict resolution, permissions details and basic real previews only for supported types; disable unsupported buttons rather than showing fake success.
5. Implement structured tests with temp dirs, symlinks, escaped names, quotes/HTML markup, non-ASCII filenames, permissions, conflicting writes, rollback of partial copy/move and user-home detection; add a live temp test under the actual user HOME.

## Acceptance gates (all required for completion)

Real files/folders change on disk, are visible after app restart, cannot escape allowed roots; operations have truthful errors, path navigation works, unsafe filename markup never executes.

## Evidence to collect

Filesystem-before/after `stat` and checksums, portal permission log, actual in-app screenshots and tests on disposable user home fixtures.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 14 — Secure ZIP create, inspect and extract in Files

**Priority:** P1  
**Prerequisite repair IDs:** 13  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Requested ZIP operations are not implemented end to end in File Explorer; creating a fake archive entry or only manipulating localStorage does not satisfy file management.

## Inspect these repository paths first

- `pwa/nuxel-apps/files/js/files.js`
- `services/nuxel-portal/src/portal.py`
- `pwa/nuxel-apps/downloader/`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`

## Required engineering work — execute all items

1. Implement archive operations in the Files privileged backend using a maintained library: create ZIP from selected files/folders, validate/open archive listing, Extract Here and Extract to new folder, progress/cancellation and conflict handling.
2. Defend against Zip Slip (`../`, absolute paths, drive prefixes), archive symlink escapes, hard-link tricks, duplicate entries, malformed compression, decompression bombs, sparse filesystem exhaustion and unauthorized destination paths.
3. Enforce per-operation limits for extracted bytes, entry count, path depth and runtime; use staging dirs and atomic rename or roll back incomplete output on failure. Do not overwrite without explicit confirmation.
4. Support UTF-8 names and document handling encrypted ZIP only if a suitable, auditable library actually supports it; otherwise show unsupported.
5. Run adversarial archive fixtures and golden round trips, then create/extract a real ZIP of sample files on the S10+ and verify checksums.

## Acceptance gates (all required for completion)

User can create ZIP and safely extract into intended location; malicious ZIPs cannot escape or exhaust storage unchecked; progress/errors honest and all files verified.

## Evidence to collect

Pre/post file tree and SHA-256, adversarial test logs, storage/cancel tests, live user test and rollback instructions.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 15 — S10+ Exynos/Madera physical speaker playback path

**Priority:** P0  
**Prerequisite repair IDs:** 28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

UCM verb/Speaker/Headphones/Headset EnableSequence and DisableSequence remain empty. MP3 decoder success is not physical sound; owner has heard no output. Actual route and CS35L40 use require live hardware evidence.

## Inspect these repository paths first

- `configs/alsa-ucm/beyond-madera/HiFi.conf`
- `configs/alsa-ucm/beyond-madera/`
- `tools/s10plus/a33/nuxel-audio-diag.sh`
- `configs/wireplumber/nuxel-s10plus-audio.conf.d/`
- `configs/pipewire/nuxel-s10plus-audio.conf.part`
- `docs/beta-finalization/manual-proof/06-audio.md`

## Required engineering work — execute all items

1. Run a read-only physical ALSA map first: `aplay -l -L`, `cat /proc/asound/cards`, `amixer -c … contents`, `alsaucm list`, `dmesg` firmware/ASoC, DT codec binding and regulators/clocks. Correlate codec IDs and amplifier capabilities with exact present board before naming controls.
2. Trace process → WirePlumber/PipeWire → ALSA PCM open → DAPM widget graph → codec output → amp power and protection → physical speaker, documenting the earliest failed transition.
3. Use known Samsung board/vendor device-tree and existing-driver controls as research references, but NEVER blindly replay proprietary register dumps, disable speaker protection, overdrive amp power, or invent mixer values. Stage reversible changes and keep hardware capped/low level.
4. Implement verified UCM control sequences only after capability and safe-limit documentation. Test tiny low-level audio on device with owner present; check silence/distortion/overheating and logs. Consider headphones/Bluetooth as diagnostics but not proof of built-in speaker.
5. If missing kernel support/firmware prevents routing, provide exact missing driver/module/firmware, evidence and separately reviewable offline patch; no kernel flashing.

## Acceptance gates (all required for completion)

Audible and owner-confirmed low-volume clean sound from built-in S10+ speaker plus consistent ALSA stream/route evidence; headphones and speaker routes do not conflict; otherwise precise BLOCKED report.

## Evidence to collect

ASoC topology dump, observed controls and transitions, UCM diff, PCM logs, amp thermal/protection status if available, owner audible PASS/FAIL.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 16 — Boot cue and rapid volume feedback through verified output

**Priority:** P0  
**Prerequisite repair IDs:** 15,25  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Boot and volume cues exist in source but remain inaudible. This prompt must not treat a clean decoder exit as pass; first ensure physical speaker path has a verified route (task 15).

## Inspect these repository paths first

- `assets/nuxel-boot-audio.mp3`
- `assets/nuxel-pow.mp3`
- `services/nuxel-session/systemd/nuxel-boot-sound.service`
- `services/nuxel-session/systemd/nuxel-button-manager.service`
- `tools/s10plus/a34/nuxel-button-manager.c`
- `configs/nuxel/audio/audio.json`

## Required engineering work — execute all items

1. Trace the true boot animation → Home-ready event → one-shot playback semantics, including service restarts and launcher page reload; prevent multiple/replayed cues. Verify 7.7-second source and 44% software PCM request through an audio gain control that respects the proven protective physical cap.
2. Separate volume input event processing from playback, using a bounded nonblocking cue queue or debounce so successive presses remain responsive; avoid hundreds of overlapping `mpg123` processes.
3. Ensure volume step reflects effective selected mixer output and per-mode sound policies, and cue starts only after successful volume change. Do not spam during long key hold.
4. Add mocked transition tests for boot twice/restart, no sound device, stalled decoder, rapid 50 events, and system mute state. Include device timing logs for keydown→mixer confirmation→sound onset.
5. Use only the verified ALSA playback device/routes from speaker mission; test after one safe normal reboot with owner listening.

## Acceptance gates (all required for completion)

One and only one startup cue after real handoff; audible low-volume `nuxel-pow.mp3` on each intentional volume step; immediate responsive buttons, no runaway processes or unsafe gain.

## Evidence to collect

Boot event timestamps, systemd journal and audio route receipt, input latency numbers, real owner audible confirmation.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 17 — System-wide Normal/Vibrate/Silent sound behavior

**Priority:** P1  
**Prerequisite repair IDs:** 15,16,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Existing sound-mode UI/settings presence has not been proven to enforce alerts and haptics end-to-end. Do not conflate an existing notification bell icon with sound mode, and do not imply telephony ringtone support works.

## Inspect these repository paths first

- `configs/nuxel/audio/audio.json`
- `pwa/nuxel-apps/settings/settings.js`
- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-home/js/status-bar.js`
- `services/nuxel-notifications/`
- `services/nuxel-haptics/`

## Required engineering work — execute all items

1. Trace notification event → category/policy → audio playback/haptic controller and audit current stored sound setting. Define Normal, Vibrate, Silent policies with separate media vs notifications; preserve exceptions only when explicitly allowed.
2. Use a single daemon/policy source for mode state, durable storage and D-Bus change notifications. Prevent duplicate vibrator controllers and never mute media implicitly without documented preference.
3. Integrate Settings, Quick Settings and status bar with real readback: one source of truth and a distinct sound-mode indicator when bell already signals notifications.
4. Handle mode changes while alerts are queued, app restarts, reboots and speaker-hardware unavailability. In unavailable hardware cases report mode policy applied but audio path blocked, not 'audible'.
5. Write test matrix across all 3 modes × alerts/media/haptics × restart; conduct owner haptic/audible validation once task 15 succeeds.

## Acceptance gates (all required for completion)

Mode selection survives restart, alert sound/haptic obey policy, media behavior documented, status icon correct, no contradictory UI states.

## Evidence to collect

Event policy traces, Settings/QS screenshots, notification + audio/haptic logs, owner mode-by-mode confirmation.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 18 — BlueZ HCI, pairing, profiles and connected devices

**Priority:** P1  
**Prerequisite repair IDs:** 28,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Bluetooth configs and portal groundwork exist, but no physical HCI initialization, pairing, A2DP or BLE evidence from the S10+.

## Inspect these repository paths first

- `configs/nuxel/bluetooth/bluetooth.json`
- `tools/s10plus/a33/nuxel-bluetooth-diag.sh`
- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-apps/settings/settings.js`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`

## Required engineering work — execute all items

1. Identify actual transport (USB/UART/SDIO), controller ID, chip-specific firmware, hciattach/serdev requirement, `rfkill`, `bluetoothctl list/show`, BlueZ logs and current adapter state. Fix firmware/service startup ordering with reversible changes only.
2. Implement one BlueZ D-Bus manager for power, discovery, secure pairing confirmation, trust, connect/disconnect, list of saved devices and event signals; avoid parallel Bluetooth daemons.
3. Add touch-friendly Settings devices screen and Quick Settings tile using real D-Bus readback; pair keyboards/mice and BLE where supported; handle PIN/passkeys securely.
4. For A2DP test, separately inspect WirePlumber/PipeWire Bluetooth profiles and codec availability; do not confuse Bluetooth speaker success with physical internal speaker completion.
5. Test real adapter off/on, scan, pair, reconnect after restart, unpair, link drop, erroneous passkey and a physically available device.

## Acceptance gates (all required for completion)

A real adapter enumerates and one physical test device pairs/reconnects; list reflects actual BlueZ state, sound profile only claimed if audible confirmed.

## Evidence to collect

`bluetoothctl` readbacks, firmware messages, HCI status, paired-device receipt with private IDs redacted, audio/owner proof.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 19 — Native S10+ NFC NCI and NDEF reader

**Priority:** P2  
**Prerequisite repair IDs:** 28,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

There is configuration/diagnostic groundwork, not proven NFC controller initialization or tag reads. Owner requests a truthful toggle and actual NDEF support, NFC default OFF.

## Inspect these repository paths first

- `configs/nuxel/nfc/nfc.json`
- `tools/s10plus/a33/nuxel-nfc-diag.sh`
- `pwa/nuxel-home/js/qs.js`
- `docs/beta-finalization/manual-proof/12-nfc.md`

## Required engineering work — execute all items

1. Inspect `dmesg`, device-tree/driver bindings, I2C/SPI nodes, firmware loading, NCI device nodes and Linux NFC userspace availability. Confirm controller revision from actual system, not another S10 model.
2. Determine reversible power/enable control with proper permissions and default-off service policy. Never implement UI-only toggles.
3. Where Linux NCI driver works, add service with explicit statuses unavailable/disabled/enabling/ready/tag-detected/error and minimal NDEF read-only parsing; require per-app permission before sharing tag content.
4. Handle malformed/hostile NDEF payloads, rapid tag removal and suspend/resume. Do not claim payments or secure-element emulation.
5. Test with user-supplied benign physical NDEF tag and collect controller state before/after OFF/ON; if driver absent, report exact device ID/missing kernel capability.

## Acceptance gates (all required for completion)

Physical NFC controller toggles and harmless tag is read as NDEF with owner confirmation; otherwise explicitly unavailable with blocker and no fake ON indicator.

## Evidence to collect

Kernel binding/firmware evidence, NCI state, safe test-tag read trace and permission audit.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 20 — Real GNSS, GeoClue, permissions and location lifecycle

**Priority:** P2  
**Prerequisite repair IDs:** 09,28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

`GeoClueConnector` exists but there is no proof of GNSS-capable device/firmware, fix, accuracy or per-app permission. A correct clock is not GNSS evidence.

## Inspect these repository paths first

- `services/nuxel-bridge/src/bridge.py`
- `pwa/nuxel-common/geolocation.js`
- `configs/nuxel/capabilities/connectivity-time-audio-buttons.json`
- `pwa/nuxel-apps/settings/settings.js`

## Required engineering work — execute all items

1. Inspect `timedatectl`/RTC/NTP first and explicitly separate time-source diagnosis from GNSS. Inventory modem/location interfaces, GNSS device nodes, GPSD/GeoClue providers, firmware logs and actual chip API.
2. Add location default OFF, per-app consent with clear duration/revoke, provider confidence/source, fix timestamp, horizontal accuracy and timeout behavior.
3. Ensure a request returns no coordinates unless authorized and a valid provider has produced them; do not label IP-derived position as GPS fix.
4. Subscribe to changes/suspend/resume with no background constant polling; location OFF must stop updates and revoke UI disclosure. Protect logs against unrequested persistent tracking.
5. Test negative cases missing modem, denied permission, stale fix, wrong timestamps and provider errors; physically verify a current GNSS fix if vendor stack supports it.

## Acceptance gates (all required for completion)

Location OFF at first boot; setting/on request controls real GeoClue provider; GPS fix only claimed with timestamp/accuracy/satellite or provider proof; permissions and revocation work.

## Evidence to collect

Source-labeled GeoClue/gpsd output, permission receipts, owner outside fix confirmation, power impact and refusal tests.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 21 — Nuxel Maps online tiles, OSM behavior and GNSS

**Priority:** P2  
**Prerequisite repair IDs:** 11,20,12  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Map has offline grid, IndexedDB tile cache and optional URL template; it does not have verified network tile provider, accurate live GPS or full route/search service behavior.

## Inspect these repository paths first

- `pwa/nuxel-apps/maps/js/maps.js`
- `pwa/nuxel-apps/maps/index.html`
- `pwa/nuxel-apps/maps/css/maps.css`
- `pwa/nuxel-common/geolocation.js`

## Required engineering work — execute all items

1. Inspect current canvas mapping math, tile addressing, caching and drawing; ensure antimeridian/wrap, polar limits, zoom clamping and proper pixel coordinates.
2. Configure a legitimate OpenStreetMap-compatible tile provider respecting its attribution, request rate, user agent and bulk-download rules. Do not assume public OSM tiles can be bulk cached offline.
3. Integrate permission-scoped location provider from task 20 and distinguish real GNSS fix from manual marker/approximate location. Show accuracy circle, last-fix time and unavailable state.
4. Implement touch panning, pinch zoom, markers, coordinate search and search/routing only when real provider configured; expose clear offline error and opt-in tile cache limits.
5. Test no-network maps, provider 429, corrupt tiles, wrong GPS permissions, dateline crossing and app memory under prolonged pan/zoom; test real download after Wi-Fi/HTTPS passes.

## Acceptance gates (all required for completion)

Real licensed/attributed map tiles load over HTTPS; pan/pinch works smoothly, cached tiles survive offline; current-location button uses a permitted, accurately labeled real fix or shows unavailable.

## Evidence to collect

Rendered tile screenshots, provider/attribution settings, permission logs, offline/online test, owner location comparison when available.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 22 — S10+ V4L2/ISP camera and real capture

**Priority:** P1  
**Prerequisite repair IDs:** 28,24  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Current Camera PWA uses `getUserMedia()` but source availability does not prove the Samsung ISP/sensors, proprietary firmware, V4L2 backend, portals or WebKit permissions expose physical video frames.

## Inspect these repository paths first

- `pwa/nuxel-apps/camera-gallery/js/camera.js`
- `pwa/nuxel-apps/camera-gallery/index.html`
- `docs/beta-finalization/manual-proof/15-camera.md`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`

## Required engineering work — execute all items

1. Probe /dev/video*, /dev/media*, media-controller graph, kernel dmesg, camera DT endpoints, sensor power/regulators and firmware. Distinguish capture devices from codec-only video nodes.
2. Determine if a supported V4L2/libcamera/PipeWire path can produce a frame from one sensor. Before changing UI, acquire and inspect a non-placeholder physical sample image through the actual camera graph.
3. Integrate front/rear selection only for enumerated working cameras; request permission through existing portal, preserve lock screen/user consent, and handle missing sensor cleanly.
4. Wire preview/capture/rotate/save to user Pictures/Photo Gallery with content URI and verified write receipts; use non-root user and prevent path escape.
5. Test failure states (permission denial, camera in use, suspended sensor, storage full), double-Power shortcut interaction and actual on-device frames. If hardware requires unavailable vendor driver/ISP firmware, document precise blocker without kernel flashing.

## Acceptance gates (all required for completion)

Camera preview shows physical scene, user saves a real JPEG/PNG under Pictures with correct resolution/orientation and repeatable capture; otherwise no fake preview and exact hardware blocker.

## Evidence to collect

Media topology and sensor IDs, captured image metadata, actual frame hash and owner photo confirmation; errors from kernel, portal, pipeline.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 23 — Real LED torch backend and fail-honest toggle

**Priority:** P1  
**Prerequisite repair IDs:** 25,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Button manager sends a flashlight request while actual LED is owned by another backend; Quick Settings flashlight action reports unavailable. There is no physically demonstrated torch.

## Inspect these repository paths first

- `tools/s10plus/a34/nuxel-button-manager.c`
- `pwa/nuxel-home/js/qs.js`
- `services/nuxel-bridge/src/bridge.py`
- `configs/nuxel/buttons.json`

## Required engineering work — execute all items

1. Identify rear flash/torch hardware and kernel exposure through LED class or V4L2 flash subdevice, not guessed GPIO/registers. Check camera flash resource ownership and vendor driver capability.
2. Implement a single broker service with on/off readback, permission checking, bounded torch duration, automatic OFF on crash/suspend/thermal alarms and safe brightness.
3. Wire both Quick Settings and double-Bixby request to that same backend; UI state must reflect actual LED power and error states, not optimistic CSS only.
4. Do not use photo flash/strobe commands as a continuous torch, disable thermal/current limits or write unknown sysfs nodes.
5. Test toggling while camera open, rapid presses, screen lock, power suspend, service crash and owner observation; report exact hardware limitation if torch API missing.

## Acceptance gates (all required for completion)

Physical rear LED visibly turns on/off on request and state syncs in QS/Bixby; auto-off and thermal safety work; otherwise unavailable with exact driver evidence.

## Evidence to collect

Kernel LED/V4L2 node dump, output state, structured logs and owner physical confirmation.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 24 — Power+VolumeDown authentic live-frame screenshots

**Priority:** P1  
**Prerequisite repair IDs:** 25,28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Wayland snapshot and button FSM code exists but there is no real screenshot from the current compositor proven to match the current display.

## Inspect these repository paths first

- `tools/s10plus/a34/nuxel-wl-snapshot.c`
- `tools/s10plus/a34/nuxel-wl-fb.c`
- `tools/s10plus/a34/nuxel-button-manager.c`
- `services/nuxel-session/systemd/`
- `pwa/nuxel-apps/files/`

## Required engineering work — execute all items

1. Map Power+VolumeDown chord priority over standalone buttons and verify its path into the current Phoc/Wayland capture utility; ensure supported screencopy is bound to *current* output rather than old framebuffer.
2. Implement secure screenshot request with explicit screenshot target under the actual current user's `~/Pictures/Screenshots/`, correct permissions, atomic file creation and timestamp collision handling.
3. Exclude secrets/protected lock-screen content according to existing OS policy and prevent arbitrary app process from screen-capturing without authorization.
4. Ensure capture output is decoded correctly, oriented/rotated correctly, not stale, and user gets bounded completion feedback. Handle missing wlroots protocol and damaged buffers honestly.
5. Run pixel/content comparisons against a screen with deliberate visible timestamp/text change, portrait and landscape, two captures in succession, storage full and input chord bounce.

## Acceptance gates (all required for completion)

One chord captures current visible screen to an actual PNG, differs when screen content changes, and no unintended sleep/volume event escapes; file visible in Files.

## Evidence to collect

Two timestamped actual PNG files and checksums, compositor protocol logs, process status and owner screenshot confirmation.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 25 — Deterministic Power/Bixby/volume input FSM

**Priority:** P1  
**Prerequisite repair IDs:** 22,23,24,16  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Hardware FSM source exists but the double Power camera, double Bixby torch, screenshot chord and volume responsiveness have not been verified as a coherent physical input pipeline.

## Inspect these repository paths first

- `tools/s10plus/a34/nuxel-button-manager.c`
- `tools/s10plus/a34/nuxel-button-fsm.h`
- `configs/nuxel/input/button-fsm.json`
- `services/nuxel-session/systemd/nuxel-button-manager.service`
- `tools/s10plus/a34/nuxel-button-trace.sh`

## Required engineering work — execute all items

1. Audit single owner of evdev devices and event emission; measure kernel event time vs debounce vs action; prevent double consumption from another UI daemon.
2. Write explicit FSM for single Power = sleep/wake, hold Power = power menu, double Power within calibrated 350–450 ms = camera, double Bixby = flashlight, Power+VolDown = screenshot, and volume auto-repeat; priority should prevent accidental sleep or volume changes when chord matched.
3. Guarantee short vs hold mutually exclusive, handle contact bounce, key rollover, delayed release, simultaneous keys, lost focus and service restart; never kill essential processes through long navigation Back.
4. Route actions to their real backend with readback and bounded retries, not shell strings or fake CSS state; ensure unsuccessful camera/flashlight actions report blocked.
5. Add table-driven input trace fixture suite plus real 90-second user hardware test, measure latency before/after and preserve navigation/haptics.

## Acceptance gates (all required for completion)

Each physical gesture invokes exactly one intended operation, never spurious actions, and works while applications focused; volume shows prompt consistent changes.

## Evidence to collect

Evdev trace anonymized, FSM transition log, timing histogram, app/window state, owner PASS/FAIL for each key combination.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 26 — Truthful single-instance status icons + battery/sound

**Priority:** P1  
**Prerequisite repair IDs:** 09,10,17,18,19,20,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Owner observed overlapping/double Wi-Fi icon and phantom SIM bars; source-only indicators cannot establish actual radio/battery/charging/sound status.

## Inspect these repository paths first

- `pwa/nuxel-home/js/status-bar.js`
- `pwa/nuxel-home/css/status-bar.css`
- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-apps/settings/settings.js`
- `pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/`

## Required engineering work — execute all items

1. Create one event-driven state model for Wi-Fi radio/association/internet, cellular modem present vs SIM absent vs registration, BT, GPS, NFC, sound mode, charging/battery and notifications. Ground each field in system service readback and expose unknown/unsupported distinctly.
2. Eliminate duplicate DOM insertion/listeners across reloads; use a responsive, single flex/grid row with safe-area insets instead of overlay hacks. Audit small S10+ status-bar width and rotation.
3. Preserve three battery display modes: percentage inside battery (readable), percentage-only text, proportional fill bar. Do not render a collapsed line in percent-only mode; test 0/50/100/unknown and charging.
4. Do not show cellular signal bars when no modem/SIM registration exists. Never present an icon animation as proof of connectivity.
5. Add DOM tests for repeated initialization, every indicator state and overlapping boxes; capture real top bar with different hardware states.

## Acceptance gates (all required for completion)

No overlapping indicators or duplicate Wi-Fi; battery modes readable and accurate; no-SIM accurate; unsupported features have truthful neutral states; tap opens matching functional setting.

## Evidence to collect

System-state JSON snapshots, bounding-box/DOM dumps, three battery screenshots and owner verification.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 27 — Actual Quick Settings toggles with synchronized backend

**Priority:** P0  
**Prerequisite repair IDs:** 09,10,17,18,19,20,23,26  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

`qs.js` `_toggle()` currently routes Wi-Fi to `_setWifiEnabled()` but other tile IDs emit an unavailable message, failing Phase 13. Functional logic must use existing backends or report unsupported—not fake tile state.

## Inspect these repository paths first

- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-home/js/bridge.js`
- `services/nuxel-bridge/src/bridge.py`
- `pwa/nuxel-apps/settings/settings.js`
- `pwa/nuxel-home/css/style.css`

## Required engineering work — execute all items

1. Inventory each tile and its actual privileged owner: Wi-Fi via NetworkManager, BT via BlueZ, location via GeoClue, NFC via NCI, torch via verified LED broker, sound mode via notifications policy, cellular via ModemManager and rotation/power via real compositor/power service.
2. Design a narrow typed RPC/status contract for state, supported capabilities, permitted actions, in-progress and errors. Check backend before enabling a tile; enforce permissions and prohibit the PWA calling arbitrary commands.
3. Implement read→request change→verify readback→update UI with explicit timeouts, rollback of optimistic visual state and error copy. Subscribe to D-Bus events instead of continual polling.
4. Integrate with Settings using the same state source and avoid conflicting toggles/parallel radio managers. Preserve compact/expanded shade gestures and original supplied icons.
5. Automate per-tile state transition tests including permission failure, absent driver, rfkill, subprocess crash, concurrent toggle and UI restart; physically validate independent supported toggles.

## Acceptance gates (all required for completion)

No tile claims ON unless real backend says ON; supported functions change physical device state and Settings mirror them; unavailable ones are clearly disabled with exact reason.

## Evidence to collect

Per-tile API and daemon receipts, live device state before/after, UI screenshots and owner confirmations.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 28 — Fresh Fedora S10+ rootfs parity with live userspace

**Priority:** P0  
**Prerequisite repair IDs:** none  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

A40 live installer deploys `nuxel-metricsd`/socket but image builder omits them. Fresh GitHub image therefore cannot be assumed to match live handset capabilities. Other live-only services need comparison too.

## Inspect these repository paths first

- `images/s10plus/build-phone-rootfs-inside-fedora.sh`
- `images/s10plus/build.sh`
- `services/nuxel-metrics/nuxel-metricsd.c`
- `services/nuxel-metrics/nuxel-metrics.socket`
- `services/nuxel-metrics/nuxel-metrics.service`
- `tools/s10plus/a40/package-live.sh`
- `tools/s10plus/a40/install-live.py`

## Required engineering work — execute all items

1. Inventory every live-install manifest (A34/A37/A39/A40/A43), compare against Fedora rootfs build payload and active systemd units. Document where binaries, assets, configs, unit files and package dependencies diverge.
2. Build metrics daemon for AArch64 reproducibly within container, install verified units, socket/listener permissions, enablement dependencies and local-only endpoint. Install any other truly required stable userspace services missing from builder without reviving deprecated boot modes.
3. Check identical library ABIs (`file`, `readelf`, `ldd` on ARM64 target), service paths, privilege restrictions, symlinks and full asset registry. Do not ship Mac binaries or developer's prebuilt local `build/out` results.
4. Add CI image mount/extraction assertions verifying daemon presence, systemd symlinks, app webroot and checksums; compare normalized manifest against intended userspace release payload.
5. Run real Fedora 43 ARM64 image build where runner/toolchain available; verify checksum and test boot on device *only with explicit separate authorization for flashing*; live USB updates can be tested safely otherwise.

## Acceptance gates (all required for completion)

Fresh image reproducibly includes metrics, working launcher, settings, browser host, audio/NetworkManager stack and all stable live-installed service components; no stale missing units or host architecture binaries.

## Evidence to collect

Artifact SBOM/hash manifest, chroot/runtime service checks, CI image verification, delta report between live and clean image, build logs and explicit unflashed status.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 29 — Main-merge CI, tag, prerelease and verified S10+ artifacts

**Priority:** P0  
**Prerequisite repair IDs:** 28  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Current workflow listens for `main` pushes, tags `v*`, and manual dispatch; publication skips a main push if canonical VERSION tag already exists. No remote successful release run or bootable image proof exists.

## Inspect these repository paths first

- `.github/workflows/release.yml`
- `images/s10plus/build.sh`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`
- `tools/verify-artifacts.sh`
- `tools/package-release.sh`
- `VERSION`

## Required engineering work — execute all items

1. Audit prepare/build/release job outputs and secrets/tokens permissions under GitHub branch protections. Define release behavior: each merged PR to main runs build/test; only a new valid `VERSION` creates a new tag/prerelease. Decide separately whether unchanged-version merges should publish nightly artifacts, but never replace an immutable tag.
2. Validate canonical tag `v0.6.3-beta` for VERSION match, checked-out SHA reachable from protected main, tag creation races, workflow_dispatch source SHA and tag-push duplicate triggers. Use concurrency, immutable artifacts, no force pushes or rewrite old published release.
3. Ensure S10+ image build includes verified Fedora rootfs from task 28, current launcher/service components, boot image checks, checksums, release notes and artifact download smoke test. Never claim release succeeded because YAML parsed.
4. Write local workflow-contract tests and actionlint; exercise GitHub Actions on an authorized test PR; capture logs, final check status, generated tag, published release URL and artifact SHA after PR merge.
5. If bot token cannot create tag under ruleset, return explicit permissions/required administrator setup; do not bypass protections or silently mutate main.

## Acceptance gates (all required for completion)

Every merge runs verified CI; a valid version-bumping merge publishes exactly one canonical tag and GitHub prerelease with downloadable S10+ artifacts; failures block publish and report precise cause.

## Evidence to collect

Actual GitHub run IDs/conclusions, tag→main SHA, release URL, downloadable archive hash and included image manifest; no fabricated remote success.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 30 — Evidence-based documentation, progress and feature claims

**Priority:** P1  
**Prerequisite repair IDs:** 01-29  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

README still has v0.6.1-beta heading, historical A39 material in changelog, and `final.md` is a list of acceptance requirements—not proof of completion. Audit report identifies unfinished features.

## Inspect these repository paths first

- `README.md`
- `CHANGELOG.md`
- `VERSION`
- `A43-VERIFICATION.md`
- `docs/beta-finalization/manual-proof/`
- `final.md`

## Required engineering work — execute all items

1. Create a single machine-readable acceptance status table for all 27 final.md rows, with distinct source/build/live-deployed/owner-confirmed statuses and links to evidence; never convert missing test to PASS.
2. Update README current release identity and real supported device matrix, known S10+ limitations, production vs beta claims, setup/install prerequisites and kernel restriction.
3. Normalize CHANGELOG chronological structure and version history while preserving past data; do not rewrite history or invent release dates.
4. Recalculate source-derived counts/percentages only with documented numerator, denominator and rationale; distinguish project milestones/57 prompt-only branches from implemented features and user-confirmed hardware.
5. Generate a self-audit script that fails on inconsistent VERSION/README/release notes, duplicate stats and missing verification receipts; report publication and hardware status honestly.

## Acceptance gates (all required for completion)

Docs correctly say what works, what is unverified, what is blocked, and where proof lives; all percentages reproducible; README/changelog/version consistent and no unsupported production claims.

## Evidence to collect

Document diff, acceptance-data snapshot, calculation script output and receipts to underlying source/build/owner proofs.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.


---

# NUXEL REPAIR 31 — Home gesture arbitration, app drawer, zoom and smoothness

**Priority:** P1  
**Prerequisite repair IDs:** 02,04,27  
**Target release baseline:** v0.6.3-beta  
**Mode:** Implement, test, safely deploy over live USB, physically verify where applicable.

## Grounded starting state

Previous user reports bottom-half swipe-up app drawer not reliably opening, unwanted Home zoom/pan, jittery scrolling and inconsistent app/window activation. A43 only passed static source checks; no frame measurements.

## Inspect these repository paths first

- `pwa/nuxel-home/js/gestures.js`
- `pwa/nuxel-home/js/launcher.js`
- `pwa/nuxel-home/js/navigation.js`
- `pwa/nuxel-home/js/recents.js`
- `pwa/nuxel-home/css/launcher.css`
- `pwa/nuxel-home/js/scroll-indicators.js`

## Required engineering work — execute all items

1. Map gesture recognizers, event capture/bubble and touch-action CSS; define per-screen ownership: upper Home half down Quick Settings, lower Home half up app drawer, second swipe up Settings, reverse swipe closes; horizontal Home pages must not conflict with dock drag/drop.
2. Disable pinch/double-tap page zoom only in launcher Home viewport while preserving deliberate map/browser zoom and accessibility-friendly user scale outside Home. Eliminate unintended panning when Home at natural scale.
3. Fix drawer open/render/close transitions using stable state and focus ownership, not timeout hacks; launching an app must wait for mapped visible window and close drawer without stealing keyboard focus.
4. Implement composited transform/opacity transitions with reduced-motion support and one requestAnimationFrame-driven update path; trim log console DOM refreshes and synchronous touch handlers. Avoid intercepting scrolling inside Settings/list views.
5. Capture S10+ frame times, touch-down→visible drawer latency and user test for long-press drag, screen rotation, Home navigation and app switching. Add test traces for swipe direction, repeated touch sequences, cancellation, two-finger pinch and gesture conflicts.

## Acceptance gates (all required for completion)

Bottom swipe opens drawer on first intentional gesture, desktop swipes animate smoothly, no unwanted Home zoom, independent scroll views work, Home/Back/Recents and drag are not regressed; measured improvement rather than anecdote.

## Evidence to collect

Device frame-time traces before/after, rendered screenshots, touch event logs, owner 90-second gesture PASS/FAIL matrix.

## Non-negotiable execution contract

- Work against the **current repository checkout** and the existing live USB-connected Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Fedora ARM64, legacy Samsung 4.14 kernel). Verify the installed revision and architecture first; archived source may differ from what is running. This is an **implementation mission**, not a request to generate another prompt or checklist.
- Read `final.md`, `NUXEL-v0.6.3-beta-INDEPENDENT-COMPLETENESS-AUDIT.md` if available, existing design and tests. Inspect before editing; cited paths are investigation starting points, not permission to assume symbols/API behavior have remained unchanged.
- Record baseline (`git status`, services, logs, affected file hashes), preserve home layouts/preferences and establish recovery/rollback. Work in a focused feature branch, commit cohesive changes with meaningful messages. Avoid rewriting unrelated modules or ignoring pre-existing failures.
- **No flashing, raw partition writes, kernel/bootloader/recovery replacement, unapproved reboot or loss of live USB console.** Hardware bring-up changes that require kernel/boot changes must stop at a separately reviewable proposal. Never make unverified amplifier/LED/power-register writes or weaken security to produce a green check.
- Prefer existing NetworkManager, BlueZ, GeoClue, PipeWire/ALSA, portal and local bridge ownership. New APIs must validate input, authenticate caller identity and expose only narrowly scoped privileges. Keep logs free of Wi-Fi secrets, precise locations, and other private content.
- Add focused automated tests plus at least one negative/failure-path test. Build native outputs as Linux AArch64 where relevant and check `file`/ELF architecture. Stage userspace deployment with backup and rollback, verify active files and service readback, and restart only the affected units.
- Where physical acceptance is required, announce a short owner test session and capture timestamped evidence; **a source check, mocked success, HTTP 200 or decoder exit is not a physical PASS**. If blocked by real hardware/firmware, preserve working phone, document exact first blocker and continue no further unsafe steps.

## Required final report

Return a concise table of source files changed, tests/exit codes, deployed paths/hashes, measured behavior, hardware/owner confirmations, open failures and rollback command(s). Label each milestone **SOURCE VERIFIED**, **DEPLOYMENT VERIFIED**, **HARDWARE VERIFIED**, **OWNER CONFIRMED**, **BLOCKED** or **NOT TESTED**, supported by receipts. Do not claim this issue complete until the specific acceptance gates below pass or its unsupported hardware dependency is explicitly classified and explained.

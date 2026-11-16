# PWNAGE-96000 — Kickstarter / Execution Prompt

You are starting **PWNAGE-96000** in the Nuxel repository. Execute the complete implementation specification in `full-pwnage-96000.md` from start to finish. This is an implementation and physical-verification mission, not a planning-only task.

## Mission

Fix the following on the current Nuxel S10+ build:

1. Ferdium, WhatsApp and Signal attachment buttons must open a working chooser with **Gallery** and **Files** sources, return selected images/files to the requesting app and cancel cleanly. Trace the true XDG Desktop Portal/GTK/Electron path. Remember: `org.nuxel.Portal` is Nuxel's hardware-permission broker and is not automatically `org.freedesktop.portal.FileChooser`.
2. Battery lightning is the charging indicator. Hide the separate USB icon for charger-only/external-power-only state. Show it only for a genuine PC USB data connection or active MTP/file-transfer/USB-console function. Fix the provider truth and UI renderer.
3. Add a top-right vertical three-dot menu to the actual launched Nuxel Browser. Add persistent Phone/Mobile-site and Desktop-site modes. Desktop mode must change the User-Agent/layout in the actual browser WebKit view, not just Nuxel CSS. Reconcile the PWA iframe viewer and native WebKitGTK browser so the user-facing launcher does not expose duplicate or inconsistent browsers. Preserve external-navigation opt-in, TLS checks and browser Back integration.
4. Make Firefox responsive and touch-usable on the S10+. Find whether sizing/scaling/Wayland issues are global to GTK/Flatpak/native windows; fix the shared root cause globally and keep only justified app-specific settings. Preserve the existing Firefox Flatpak-to-RPM sandbox-safe wrapper.
5. Fix fullscreen native GTK/Flatpak top-edge reveal so it shows the **one canonical Nuxel top bar** matching the default/Home design and truthful status. Trace the actual visible surface. Remove the obsolete/wrong competing implementation from the build/deploy path, but do not remove the only correct bar, Home DOM bar, lockscreen or nav dock. Enforce one owner and lockscreen precedence.
6. Make Quick Settings substantially more responsive. Profile gesture-to-first-paint, provider latency, tile interaction and close. Preserve its existing cache-first render, `_stateSyncPromise` single-flight guard, generation checks and visible-only timer. Coalesce real duplicate fetches and DOM writes; do not add another fast polling loop.
7. Make the app drawer and Home desktop smoother. Preserve the existing `_drawerSignature`, cached `drawerList`, stable icon DOM and 250 ms gesture settle guard. Profile and fix real JS/layout/decode/provider/compositor bottlenecks rather than rebuilding the drawer every open.
8. Set the active presenter target to 30 FPS only after measurement. Implement true VSync/vblank waiting only if the live S10+ driver exposes a proven API. A timer-based 30 FPS cap is not VSync. Preserve 8/3/1 FPS idle backoff, zero screen-off capture, the single `/dev/fb0` owner and required `FBIOPAN_DISPLAY` commit.

## Start by auditing the real checkout/device

Run git/status/version/build identity checks, inspect changed files, find current build and deploy scripts under `./scripts`, `./tools`, `./images` and device-specific paths, then reproduce each defect on the physical S10+. The supplied archive baseline is `v0.8.1-beta`; verify the real checkout. Read all of `full-pwnage-96000.md` before editing and use it as the detailed source of truth.

## Non-negotiable safeguards

- Never remove or overwrite the existing tested graphics/framebuffer fallback.
- Do not enable DRM/KMS, experimental NEO/DMA-BUF paths, replace the kernel or modify boot partitions in this mission.
- Do not remove `FBIOPAN_DISPLAY`; it is required by the known-good command-mode panel path.
- Do not bypass sandboxing with `--no-sandbox`, `--filesystem=host`, `--device=all` or broad permissions.
- Do not confuse the Nuxel hardware permission broker with XDG Desktop Portal FileChooser.
- Never show duplicate top bars; never let native chrome cover or bypass the lockscreen.
- Do not force a global User-Agent, GTK scale or renderer setting without measured proof.
- Do not add redundant polling loops or regress QS/drawer caching already present.
- Do not say VSync is fixed unless actual presentation/vblank synchronization is measured and supported.

## Execute in this order

1. Baseline/reproduction and evidence capture.
2. Portal/FileChooser request tracing and Gallery/Files attachment selection.
3. Battery/USB indicator truth matrix and tests.
4. Nuxel Browser canonical launch path, ⋮ menu, Phone/Desktop modes and real WebKit UA switching.
5. Firefox and system-wide GTK/Flatpak responsiveness.
6. Canonical single-owner native top bar, immersive reveal and obsolete-bar cleanup.
7. Quick Settings fetch/render/animation profiling and optimizations.
8. App drawer/Home responsiveness profiling and optimizations.
9. 30 FPS pacing/VSync capability check, reversible active target and sustained physical benchmark.
10. Targeted tests, full relevant project tests, deployment, reboot/recovery checks and report.

Implement each independent workstream fully. Do not stop after diagnosis. If a specific app is not installed or a kernel/app prerequisite is unavailable, provide exact evidence, test the common pathway with a real fixture/client, and finish the remaining work.

## Visual and display safety

Any experimental display/presentation policy or new shell-chrome activation that could leave the panel blank must be canaried with a visible Nuxel notification asking: **“Can you see the display working correctly?”** Provide explicit **YES** and **NO** actions and a 30-second deadline. Only an actual human YES received within 30 seconds counts as confirmation. NO, timeout, lost notification, service crash or ambiguous state means failure: automatically return to the known-good graphics/presentation configuration, capture diagnostics, fix and retry only after verifying the fallback is healthy. Never treat SSH reachability, process health or screenshot automation as the user's visual YES. Do not run endless retries: use bounded retries per candidate, preserve fallback and report a hard blocker after repeated identical failures. This does not authorize activating NEO/DMA-BUF/KMS.

## Required evidence and completion

Create `docs/pwnage-96000/evidence/<timestamp>/`, `REPORT-PWNAGE-96000.md` and performance results. Keep raw logs/screenshots, source and deployed hashes, exact test commands, before/after metrics and rollback instructions.

Report every objective honestly as `FIXED_AND_PHYSICALLY_VERIFIED`, `FIXED_HOST_TESTED_PHYSICAL_TEST_PENDING`, `PARTIALLY_FIXED`, `BLOCKED_WITH_EVIDENCE` or `NOT_REPRODUCED`. Provide exact test counts. No false “all passed” claims. Confirm after deployment that:

- a real image can be selected from Gallery and Files and returned to each supported messenger;
- charger-only state displays battery lightning without the separate USB data icon;
- browser Phone and Desktop modes truly change the rendered website and persist;
- Firefox and representative GTK/Flatpak apps fit and respond correctly;
- exactly one matching Nuxel status bar appears on fullscreen native app top-swipe;
- QS and drawer first-paint/interaction metrics improve or their bottleneck is precisely isolated;
- 30 FPS is sustained without tearing/input regressions/thermal failure, or the unsupported VSync path is truthfully documented and safe 20 FPS rollback remains available;
- the existing framebuffer graphics fallback remains intact and recoverable.

**Now execute `full-pwnage-96000.md`. Do not return only a plan.**

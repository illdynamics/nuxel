# PWNAGE-90000 — Kickstarter / Execution Prompt

You are now executing the full Nuxel shell reliability mission. Read **the entire `full-pwnage-90000.md`** in the repository/workspace first and treat it as the complete specification. This kickoff file does not replace or shorten any requirement in that megaprompt.

## Mission

Implement, integrate, test and verify all P90-01 through P90-13 in `full-pwnage-90000.md`:

- Stop the outgoing “Restart accepted” message/overlay from leaking into the next boot and over the laser penguin preload image.
- Fix the preload MP4 so it visibly plays its full ~6.016 seconds instead of moving for only one second and freezing.
- Make all visible desktop and dock icons paint on the first unlocked frame; fix repeated Flatpak redraw/reinitialization on lock/unlock.
- Measure and materially improve Flatpak time-to-first-frame without weakening Flatpak sandboxing.
- Remove the dark-blue rectangle after Reload launcher by fixing the actual stale layer/surface, not by hiding arbitrary UI.
- Fix the invisible touch/input interceptor after a single Back press so the app drawer works immediately.
- Coordinate fullscreen top and bottom gesture strips: first top pull reveals compact statusbar, second pull opens Quick Settings, swipe up closes compact/expanded shade, and bottom-up nav reveal works while the keyboard is open.
- Generate the actual systemd boot/shutdown analysis at `./SYSTEMD-GRAPH.md`, plus reusable collector and graph evidence.
- Make Back navigate inside PWA/native/Flatpak apps first, and only return to Home at a confirmed app root. Keep Penguin/Home immediate and long-Back as a distinct close/terminate gesture.

## Execution rules

1. Inspect the live checkout, Git status, branch, `VERSION`, target device and current toolchain before editing. Do not discard or overwrite existing user changes. The source archive used for preparation was `v0.7.7-beta`; verify the real checkout rather than assuming this version.
2. Reproduce and instrument each issue before fixing it. Record baseline values, especially preload clock/frame presentation, icon first paint, lock/unlock Flatpak PID/window state, Flatpak launch stages, and systemd boot timing.
3. Keep Nuxel's existing ownership architecture. In particular, do not create a second preload player, launcher, statusbar, navdock, Flatpak lifecycle owner or competing service.
4. Build a single consistent fix across the JS, native Wayland clients, bridge, Flatpak provider, packaging, tests and on-device services. Do not stop at TODOs, mock UIs or source-only changes.
5. Preserve secure lockscreen input isolation, Wayland rules, Flatpak sandbox, permissions and recovery paths. Never kill/relaunch apps as a lock/unlock optimization. Never claim an app is at its Back root merely because there is no adapter.
6. For the preload freeze, instrument mpv IPC/monotonic time, player ownership, EOF/pause state, decoded frames and actual Wayland/framebuffer presentation. The configured 12-second bound does not by itself explain a one-second freeze. Keep audio disabled and keep a bounded fail-open path.
7. For fast icons, distinguish immutable built-in icons from mutable artwork; cache/version immutable icons, eagerly prioritize only visible desktop/dock assets, retain stable image DOM nodes, decode asynchronously and show a correct placeholder immediately. Do not block unlock on network I/O.
8. For Flatpaks, trace tap → bridge → sandbox/runtime → process → Wayland map → first frame. Only change rendering environment variables after device-specific comparison; do not weaken bwrap/namespace/portal policies.
9. For fullscreen gestures, implement the single explicit state machine in the full prompt and coordinate PWA `immersive.js` / `status-bar.js` / `qs.js` with native `nuxel-statusbar.c` and `nuxel-navdock.c`. Test actual touchscreen routing with the OSK visible.
10. For Back, fix the current false `at_root:true` behavior for unhandled native apps. Add a truthful PWA Back protocol and verified per-app Flatpak/native adapters. Discover the exact installed app the user referred to as “GTP+” from the live registry; do not invent its ID.
11. Create `tools/diagnostics/nuxel-systemd-graph.py` (or an equivalent canonical collector), generate root `SYSTEMD-GRAPH.md`, and save the boot SVG/raw data under `diagnostics/systemd/`. Collect actual timings from the Nuxel phone, not the build laptop. Shutdown data must come from real previous-boot journal/manager data; mark it `NOT CAPTURED` if unavailable, never fabricate it.
12. Run existing tests before and after. Add regressions for the exact user-reported sequences, including app → one Back → immediately open drawer; fullscreen first pull/second pull/up-dismiss; OSK + bottom gesture; restart → next boot; ten lock/unlock cycles; and full MP4 playback.
13. Rebuild and stage native AArch64 clients and all packaged files using the repository's actual build/deploy scripts. Bump service-worker cache versions and related manifests when required. Validate systemd units. Keep rollback for new native binaries and service changes.
14. Do not flash boot/kernel/modem partitions. Do not push/merge/release unless the current operator explicitly requests those operations in the active task.
15. Do not stop after a plan. Execute the implementation and tests in this session, making a best-effort pass on all work. Clearly distinguish hardware-tested, host-tested, blocked and not-run checks.

## Required execution sequence

**A. Baseline** — read full prompt; inspect source/Git/target; run relevant pre-existing tests; reproduce and capture every reported bug; collect current systemd boot data before changing unit ordering.

**B. Fix session/surface cleanup** — restart state, boot surface ownership, Reload launcher rectangle, Back-to-Home transition, invisible overlays/input capture and Flatpak surface retention.

**C. Fix startup/first paint** — immutable icon cache and stable desktop DOM; instrument and optimize Flatpak startup under unchanged security policy.

**D. Back + gesture contract** — PWA app Back protocol, native/Flatpak adapters, confirmed-root behavior, topbar compact/expanded state machine, upward dismissal and OSK-safe bottom strip.

**E. Preload cinema** — prove where playback stalls, repair the decoder/presentation/overlay cause, and verify all 6.016 seconds on the phone.

**F. Systemd graph + full verification** — produce `SYSTEMD-GRAPH.md`, raw boot/shutdown evidence, run complete relevant tests and packaging checks, then prepare a final report.

## Final gate

Use `FULLY_DONE` only if every acceptance item in section 19 of `full-pwnage-90000.md` passes. Otherwise use `PARTIAL` or `BLOCKED` and state exactly what remains. Include root causes, changed files, exact test counts, on-device evidence, baseline/after timing, systemd report path, verified Back adapter coverage (including GTP+ discovery), and rollback steps.

**Start now: read `full-pwnage-90000.md` in full, inspect the real repository state, and execute the mission.**

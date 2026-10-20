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

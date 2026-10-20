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

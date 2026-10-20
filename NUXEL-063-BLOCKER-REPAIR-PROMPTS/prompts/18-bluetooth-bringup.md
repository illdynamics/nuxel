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

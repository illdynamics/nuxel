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

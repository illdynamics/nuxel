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

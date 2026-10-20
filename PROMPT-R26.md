# NUXEL R26 — SIM, microSD, modem and cellular
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r26-sim-microsd-modem-cellular`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make SIM/microSD/modem behavior truthful and safe. This branch must treat SIM, microSD, and the Samsung Shannon LTE modem as separate workstreams, report only real detector/ModemManager values, mount external media read-only by default, and refuse writes to internal storage or protected modem/EFS partitions.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/modem/modem.json`, `configs/nuxel/modem/microsd.json`, `configs/nuxel/modem/90-nuxel-microsd.rules`, `configs/nuxel/modem/nuxel-microsd-automount.service`, `tools/s10plus/a33/nuxel-modem-diag.sh`, `tools/s10plus/a33/nuxel-microsd-diag.sh`, their fixtures, and `configs/nuxel/capabilities/hardware-subsystems.json`. The manifest says there is no upstream ModemManager plugin for Shannon LTE and the default cellular verdict is NOT_SUPPORTED_ON_DEVICE.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns SIM presence redaction, modem interface discovery, microSD detection/mount policy, and per-subsystem status. Does not own modem firmware, EFS/calibration, or voice/SMS features that the stack cannot support. No protected-partition access, no format/partition of media, and no fabricated signal/operator/data.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Enumerate SIM, cp/wwan/rmnet interfaces, ModemManager plugins, and microSD host/block devices; record the real evidence per subsystem.
2. Keep IMSI/ICCID/IMEI/PIN/PUK redacted in every output and test the redactor.
3. Implement microSD mount as read-only by default with external-only device checks, boot-window refusal, unknown-filesystem refusal, and safe unmount.
4. Verify SIM detection and explicitly report when PIN/registration/data/SMS/voice are unsupported instead of exposing dead controls.
5. Verify modem interface presence and the first missing stack hop; do not open an AT channel without explicit owner approval.
6. Test card insert/remove/eject, internal-device refusal, busy unmount, and unknown filesystem fixtures.
7. Define owner tests for physical SIM and microSD insertion and record them separately.

## Failure modes and diagnostics
- Watch for the S10+ hybrid tray being SIM-only on some units, mmcblk0/microSD confusion, automount during boot enumeration, and ModemManager probing a character device with no supported plugin. Protected modem/EFS partitions are never read or written.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The report gives a per-subsystem capability table for SIM, microSD, modem, data, voice, and SMS.
2. No signal/operator/registration/data value is shown without a real API source.
3. IMSI/ICCID/IMEI/PIN/PUK are redacted in logs and UI.
4. microSD mounts read-only on insert, refuses `/dev/mmcblk0*`/internal targets, and never formats.
5. Unknown/busy/unsupported cards produce safe errors and no data loss.
6. Modem absence/firmware/plugin gaps are reported as precise BLOCKED states.
7. Physical SIM/microSD results are owner-labeled and remain NOT TESTED until observed.

## Hardware, privilege and rollback safety
No flashing, no modem firmware, no EFS/calibration writes, no mkfs/partitioning, and no read-write mount without explicit owner consent. Preserve data on any inserted card.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r26-sim-microsd-modem-cellular`, with tests and docs for this component only.
- `docs/component-reports/r26.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the only path to a feature requires protected partitions or unsupported radio firmware. Report NOT_SUPPORTED_ON_DEVICE/BLOCKED_FIRMWARE rather than faking cellular service.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.

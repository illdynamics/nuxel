# NUXEL R24 — NFC
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r24-nfc`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Bring up NFC only as far as the real S10+ hardware/stack supports. This branch must identify the sec-nfc/S3FWRN5-family controller, driver/module, firmware, NCI/userspace stack, polling, and tag-read capability, and must not invent card emulation, payments, or secure-element access.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/nfc/nfc.json`, `tools/s10plus/a33/nuxel-nfc-diag.sh`, `tools/s10plus/a33/tests/hw-subsystems/test-nfc-diag.py`, the `nfc-*` fixtures, `docs/hardware-ids.md`, and `configs/nuxel/capabilities/hardware-subsystems.json`. The device profile names a Samsung sec-nfc controller at I2C 0x27 with an embedded secure element; actual kernel binding/firmware is unproven.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns NFC controller/firmware/stack diagnostics, polling control, tag-read test, and capability reporting. Does not own payments, secure-element provisioning, or modem/ESE trust. No fabricated tag UID and no card-emulation claim.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Enumerate the I2C device at 0x27, driver modules, character devices, firmware candidates, and NCI/netlink interfaces; report the first missing stage.
2. Verify the real userspace stack (neard/nfc-list) and its ability to talk to the kernel interface.
3. Implement bounded polling with an always-available stop and no boot-time activation.
4. Test a physical tag read and compare the UID with the physical tag; test a second tag for non-fabrication.
5. Report unsupported secure-element/card-emulation features explicitly instead of exposing fake toggles.
6. Handle controller present but firmware missing, driver absent, and userspace absent as distinct states.
7. Keep NFC power/polling from draining battery or interfering with other radios.

## Failure modes and diagnostics
- Watch for a controller node that exists without a bound driver, a firmware filename that varies by vendor, neard running without a usable NCI transport, and an old tag UID cached from a previous session.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The report names the real controller/driver/firmware/stack path or the exact missing stage.
2. Polling starts and stops explicitly and never runs automatically at boot.
3. A physical tag read returns a UID that matches the tag and differs across two tags, or is reported BLOCKED.
4. No payments/card-emulation/secure-element capability is claimed without code and evidence.
5. Missing firmware and missing userspace stack produce different actionable verdicts.
6. The UI/status surface reflects the real poll/tag state.
7. The owner test remains NOT TESTED until a physical tag is used.

## Hardware, privilege and rollback safety
No secure-element writes, no payment provisioning, no radio firmware changes, no flash. Polling must be bounded and explicit.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r24-nfc`, with tests and docs for this component only.
- `docs/component-reports/r24.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the controller is not supported by the vendor kernel; report BLOCKED_KERNEL/NOT_SUPPORTED_ON_DEVICE. Do not emulate NFC in software and call it hardware.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.

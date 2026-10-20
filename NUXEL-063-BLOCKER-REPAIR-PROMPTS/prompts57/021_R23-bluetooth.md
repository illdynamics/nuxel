# NUXEL R23 — Bluetooth
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r23-bluetooth`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make Bluetooth work through the real BCM4375/BlueZ stack and report state truthfully. This branch owns adapter/firmware/rfkill discovery, BlueZ service/profile readiness, scan/pair/bond/connect state, input/audio profile behavior, airplane-mode transitions, and a bounded owner pairing test.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/bluetooth/bluetooth.json`, `configs/nuxel/bluetooth/main.conf.d/60-nuxel.conf`, `tools/s10plus/a33/nuxel-bluetooth-diag.sh`, `tools/s10plus/a33/tests/hw-subsystems/test-bluetooth-diag.py`, the `bluetooth-*` fixtures, `pwa/nuxel-home/js/status-bar.js`, and `configs/nuxel/capabilities/hardware-subsystems.json`. The expected HCD is `bcm4375B1_semco.hcd`; adapter/firmware pairing is not proven.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns Bluetooth adapter/firmware/rfkill/service diagnostics, BlueZ policy, pairing UX/state, and airplane-mode behavior. Does not own Wi-Fi or audio routing internals. No guessed firmware symlink, no automatic adapter power-on at boot, and no pairing without an owner-selected peer.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Enumerate adapter nodes, rfkill entries, loaded modules, and HCD firmware paths; identify the first missing stage.
2. Verify BlueZ/`bluetoothd` compatibility with the Nuxel config drop-in and ensure no competing Bluetooth daemon exists.
3. Implement bounded scan, pair, trust, connect, disconnect, and forget flows for an owner-selected peer, with MAC/name shown correctly.
4. Verify a data path (audio or file transfer) rather than treating a link as success.
5. Handle rfkill/airplane mode, adapter power cycling, service restart, and missing firmware distinctly.
6. Audit UI state so it follows BlueZ events and does not show enabled when the adapter is blocked.
7. Record redacted diagnostics and a repeatable owner test.

## Failure modes and diagnostics
- Watch for an HCD filename that differs by vendor suffix, BlueZ auto-enable, rfkill soft block after resume, duplicate `bluetoothd`, and a paired-but-not-connected device shown as connected. Do not reuse Pixel BCM4390 firmware instructions.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The report names the actual adapter, firmware path, module, and rfkill state.
2. The adapter can be powered on explicitly without auto-enabling at boot.
3. Scan finds the peer, and pair/bond/connect state matches `bluetoothctl`.
4. A real data path succeeds or the exact profile blocker is reported.
5. rfkill/airplane mode updates the UI and does not leave a false connected state.
6. Missing HCD firmware yields BLOCKED_FIRMWARE with the exact searched paths.
7. Owner-visible pairing/audio results are separate from offline fixtures.

## Hardware, privilege and rollback safety
Do not install a random firmware blob, change radio calibration, or flash. Pairing with an unknown device requires owner consent. Preserve USB console/network access.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r23-bluetooth`, with tests and docs for this component only.
- `docs/component-reports/r23.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the adapter is absent or firmware cannot be identified. Report BLOCKED_HARDWARE/BLOCKED_FIRMWARE rather than creating a guessed symlink.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.

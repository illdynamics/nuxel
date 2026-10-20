# NUXEL R18 — Power management and battery modes
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r18-power-battery-modes`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make battery, charging, profile, brightness, and suspend state truthful and usable. This branch must bind the UI to real power_supply/UPower data, fix the three battery display modes (number inside, percentage-only, proportional fill), apply only supported power profiles, and distinguish charger/LPM boot from normal operation.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/power/power.json`, `configs/nuxel/power/nuxel-power-mode.service`, `tools/s10plus/a33/nuxel-power-diag.sh`, `tools/s10plus/a33/tests/hw-subsystems/test-power-diag.py`, the power fixtures, `pwa/nuxel-home/js/status-bar.js`, `pwa/nuxel-home/js/settings-store.js`, and `pwa/nuxel-apps/settings/settings-model.js`. Power/charging values are explicitly owner-verified; the current capability state is OFFLINE_TESTED/NEEDS_OWNER_TEST.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns battery gauge discovery, charge-state reporting, profile selection/rollback, battery icon rendering, and boot-mode-aware power UI. Does not own the power menu or raw charger register writes. No invented capacity/health value and no write to charger current/voltage limits.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Enumerate `/sys/class/power_supply/*` and identify the real gauge/charger nodes, fields, units, and update cadence.
2. Map the three battery display modes to one data source and verify 0/50/100% rendering, including the reported percentage-as-line defect.
3. Implement stale-data and absent-gauge handling so the UI shows UNKNOWN/BLOCKED rather than a fabricated percentage.
4. Apply power profiles only through available governors/cgroup knobs and record the previous state for rollback.
5. Verify charger/LPM boot detection from `/proc/cmdline` and make the UI/service report the reduced-input mode.
6. Test charge/discharge transitions, thermal/health fields where present, and one reboot persistence check under policy.
7. Ensure the status bar and Settings show the same battery/profile state.

## Failure modes and diagnostics
- Watch for multiple power_supply entries, microvolt/millivolt and deci-Celsius unit confusion, a gauge that updates slowly, and the UI reading a cached value from a different service. Do not write charge-control nodes.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The report names the real battery device and every field/unit used.
2. The UI renders 0%, 50%, and 100% correctly in all three configured modes, including a half-filled battery at 50%.
3. An absent gauge produces BLOCKED_KERNEL/UNKNOWN, never a synthetic value.
4. The selected profile maps to an available governor/cgroup knob and persists or reports refusal clearly.
5. Charger/LPM boot is distinguished from a normal boot and does not claim touch readiness.
6. Profile apply has a recorded previous state and rollback.
7. Battery/charging observations are owner-labeled and not promoted from sysfs alone.

## Hardware, privilege and rollback safety
No charger-register or partition writes. A reboot for persistence follows the bounded reboot policy. Preserve the existing low-power safeguards.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r18-power-battery-modes`, with tests and docs for this component only.
- `docs/component-reports/r18.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if no trustworthy gauge exists or if a proposed profile write is not supported by the running kernel. Do not fake battery percentage to make the UI look complete.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.

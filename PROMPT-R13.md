# NUXEL R13 — Time, RTC and timesync
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r13-rtc-time-timesync`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make Nuxel's clock and time synchronization truthful across boot, offline operation, network acquisition, suspend/resume, and reboot. This branch must identify the real RTC, distinguish monotonic from wall time, configure systemd-timesyncd/chrony correctly, and show uncertainty instead of a false synchronized state.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/time/time.json`, `configs/nuxel/time/nuxel-rtc-check.service`, `configs/nuxel/time/nuxel-rtc-check.timer`, `configs/nuxel/time/nuxel-chrony.conf`, `configs/nuxel/time/60-nuxel-timesyncd.conf`, `tools/s10plus/a33/nuxel-time.sh`, and `tools/s10plus/a33/tests/test-time-rtc.py`. The capability slice marks RTC read/write and persistence as NEEDS_OWNER_TEST and timesync backend as only OFFLINE_TESTED.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns RTC discovery/read policy, wall-clock initialization, timezone handling, NTP client selection, last-known-time behavior, and the time status surface. Does not own network connectivity itself, but must report when sync is impossible because the network is down.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Enumerate RTC devices and determine which one persists across power loss; record the exact sysfs/dev path and supported read/write operations.
2. Implement a mark/compare procedure that survives reboot and records boot ID, RTC time, wall time, and delta.
3. Select exactly one timesync backend (systemd-timesyncd or chrony), document why, and remove/disable the competing service.
4. Define boot behavior when the RTC is absent or clearly wrong: use last-known-time only above a documented sanity floor and label it unsynchronized.
5. Test timezone/DST changes without altering the hardware clock unexpectedly.
6. Test offline boot, network acquisition, NTP failure, and suspend/resume timekeeping.
7. Expose a UI/status value that distinguishes SYNCHRONIZED, LAST_KNOWN, RTC_SUSPECT, and NO_TIME_SOURCE.

## Failure modes and diagnostics
- Watch for UTC/local-time confusion in the RTC, an RTC that reads 1970 or a future date, systemd-timesyncd and chrony fighting, and `timedatectl` reporting synchronized while no reachable server exists.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The report names the real RTC path and proves whether it persists across one normal reboot.
2. A mark/compare run records RTC and wall-clock deltas and returns PASS only when the delta is within the stated tolerance.
3. Exactly one timesync backend is enabled; the other is disabled or absent.
4. With networking unavailable, the UI shows unsynchronized/last-known rather than a false synced state.
5. Timezone/DST changes affect display time but do not silently rewrite the RTC incorrectly.
6. RTC-absent/implausible-clock fixtures produce RTC_SUSPECT or NO_TIME_SOURCE.
7. Owner-visible clock evidence is separated from offline fixture results.

## Hardware, privilege and rollback safety
Do not flash or write protected partitions. RTC writes are limited to the intended clock device and require a documented rollback. A reboot used for persistence testing must follow the bounded reboot policy.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r13-rtc-time-timesync`, with tests and docs for this component only.
- `docs/component-reports/r13.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if no trustworthy RTC/clock source can be identified. Do not set the clock to a guessed date and call it synchronization.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.

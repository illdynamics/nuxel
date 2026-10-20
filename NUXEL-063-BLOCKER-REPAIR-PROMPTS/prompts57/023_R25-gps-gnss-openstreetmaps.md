# NUXEL R25 — GPS/GNSS and OpenStreetMap
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r25-gps-gnss-openstreetmaps`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make location useful and honest: identify the real GNSS path, consume NMEA/fix data without fabricating coordinates, and integrate OpenStreetMap-compatible maps with offline tile caching and privacy-preserving permissions. A device node or a modem interface is not a fix.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/gnss/gnss.json`, `configs/nuxel/gnss/osm-tiles.json`, `tools/s10plus/a33/nuxel-gnss-diag.sh`, `tools/s10plus/a33/nuxel-osm-tiles.py`, `tools/s10plus/a33/tests/hw-subsystems/test-gnss-diag.py`, the `gnss-*` fixtures, `pwa/nuxel-apps/maps/`, and the location permission entries in `configs/nuxel/security/privacy-config.json`. The manifest marks a fix as NEEDS_OWNER_TEST and requires outdoor sky view.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns GNSS device/module/firmware/NMEA diagnostics, gpsd consumption, map tile policy, offline cache, and location state. Does not own cellular modem registration or map data fabrication. No guessed position, no silent online tile request, and no location permission bypass.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Enumerate GNSS nodes/modules/firmware and identify the first missing stage: node, driver, firmware, stream, fix.
2. Verify NMEA sentence parsing and gpsd/consumer integration with timestamps, fix quality, accuracy, and age.
3. Implement the no-fix/indoors state explicitly and never display a stale coordinate as live without an age warning.
4. Verify OSM tile layout, attribution, offline caching, network-optional behaviour, and zoom limits.
5. Wire location permission to the Maps app and ensure no background location use without consent.
6. Test bad checksums, truncated NMEA, leap/UTC handling, tile miss, and offline cache corruption.
7. Define an outdoors owner test for time-to-first-fix and coordinate/accuracy recording.

## Failure modes and diagnostics
- Watch for a GNSS node with no NMEA stream, gpsd using the wrong baud/protocol, UTC/leap-second mistakes, and an online-only map that silently leaks location. Cold start can take minutes; do not label a timeout as no hardware without evidence.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The report names the GNSS node/driver/firmware path and the first missing stage.
2. A physical fix has a real NMEA/position source, accuracy, age, and timestamp; no coordinate is invented.
3. Indoors/no-fix shows an explicit state and never reuses a stale coordinate as live.
4. Maps renders cached OSM tiles offline with required attribution.
5. Location permission controls access and can be revoked; no background fix runs silently.
6. Tile miss/corruption and malformed NMEA are handled without a crash or fake data.
7. The outdoors owner result is recorded separately from fixture tests.

## Hardware, privilege and rollback safety
Do not change modem firmware or radio partitions. Location tests require owner consent and outdoors access. Preserve privacy and avoid committing coordinates or personal tracks.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r25-gps-gnss-openstreetmaps`, with tests and docs for this component only.
- `docs/component-reports/r25.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if no GNSS transport is exposed by the kernel or if a fix cannot be tested safely. Report BLOCKED/NO_FIX rather than fabricating a position.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.

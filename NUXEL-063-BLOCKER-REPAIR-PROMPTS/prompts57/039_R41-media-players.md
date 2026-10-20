# NUXEL R41 — Media players
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r41-media-players`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Build a usable Nuxel media player on the actual GStreamer/FFmpeg/PipeWire/ALSA capabilities, with library scanning, playlists, media-session integration, seek/volume, background playback, and headset/BT route handoff. UI correctness must remain honest while built-in speaker audibility is unresolved.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `pwa/nuxel-apps/media/app.json`, `pwa/nuxel-apps/media/index.html`, `pwa/nuxel-apps/media/tests/test-media-library.js`, `pwa/nuxel-home/js/qs.js`, `configs/pipewire/nuxel-s10plus-audio.conf.part`, `configs/wireplumber/nuxel-s10plus-audio.conf.d/51-nuxel-s10plus-audio.conf`, `configs/nuxel/audio/audio.json`, and `configs/nuxel/audio/jack-routes.json`. The media app and tests exist; codec support, route changes, and audible output must be measured.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns media library/indexing, playback controls, playlist/queue state, media-session metadata, background/lifecycle behavior, and route-change handling. Does not own the ALSA speaker route or Bluetooth stack. No fake playback progress and no bundled codec with unclear licensing.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Inventory supported containers/codecs from installed GStreamer/FFmpeg plugins and report unsupported media clearly.
2. Implement library scan/index with safe filename handling, metadata extraction, and missing-file reconciliation.
3. Verify play/pause/seek/next/previous/volume, playlist persistence, and background playback through the real audio sink.
4. Handle headphone/USB-C/Bluetooth route changes without losing position or blasting unsafe volume.
5. Test corrupt file, unsupported codec, removed file, empty library, and storage/permission failure.
6. Add bounded memory/queue behaviour and a media-session/status surface.
7. Perform a real audible test through headphones or an available verified output, keeping speaker audibility separate.

## Failure modes and diagnostics
- Watch for a UI timer advancing while audio is stalled, codec plugin absence misreported as a file error, directory scans following symlinks into system paths, and route changes resetting track position.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The supported codec/container list is derived from installed plugins and matches observed playback.
2. Play/pause/seek/queue/playlist persistence work with real media fixtures.
3. A route change preserves position and reapplies the volume cap.
4. Unsupported/corrupt/missing files produce actionable errors without crashing.
5. Background playback and media-session state match the actual player.
6. Headphone/USB-C output is owner-verified where available; speaker remains separately labeled.
7. No fake progress or success is shown when decoding/output fails.

## Hardware, privilege and rollback safety
No DRM bypass, no unlicensed codec bundling, no full-volume test. Preserve user media and a rollback path.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r41-media-players`, with tests and docs for this component only.
- `docs/component-reports/r41.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the required codec pipeline is absent; report BLOCKED_EXTERNAL_RESOURCE/BLOCKED_KERNEL. Do not claim audible playback without owner confirmation.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.

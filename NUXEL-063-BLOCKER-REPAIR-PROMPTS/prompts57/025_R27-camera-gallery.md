# NUXEL R27 — Camera and gallery
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r27-camera-gallery`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Bring up the S10+ camera as far as the real V4L2/media/ISP stack allows, and make the gallery fully usable independently. This branch must enumerate sensors, nodes, firmware, media graph, format negotiation, PipeWire/portal chain, permissions, and capture evidence, and must never treat a USB webcam or synthetic test pattern as proof of the integrated Samsung cameras.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/camera/camera.json`, `tools/s10plus/a33/nuxel-camera-diag.sh`, `tools/s10plus/a33/tests/hw-subsystems/test-camera-diag.py`, the `camera-*` fixtures, `shell/nuxel-camera-portal/`, `pwa/nuxel-apps/camera-gallery/`, `pwa/nuxel-apps/photos/`, and `services/nuxel-bridge/src/api.py`. The manifest expects S5K2L4/S5K3M3/S5K3P9/front sensors but says frame capture is unproven; a synthetic PipeWire node is explicitly not hardware proof.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns camera node/sensor/firmware/media-graph diagnostics, format negotiation, portal/PipeWire chain, capture UX, gallery storage/metadata/thumbnails, and privacy indicators. Does not own kernel ISP drivers or Android camera HALs. No Android camera libraries and no fabricated capture.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Enumerate `/dev/video*`, subdev/media nodes, sensor names, firmware blobs, and media links; report the first missing stage.
2. Verify V4L2 format negotiation (resolution, pixel format, stride, colour space) on a real or explicitly synthetic source and label synthetic clearly.
3. Validate the V4L2 -> PipeWire -> xdg-desktop-portal Camera -> WebKit `getUserMedia` chain.
4. Implement explicit owner-initiated capture, EXIF orientation, file naming, non-overwrite, and gallery thumbnails/metadata.
5. Keep camera and torch resource ownership exclusive and show a recording indicator.
6. Test permission denial, no camera, missing firmware, media-graph failure, and portal backend absence.
7. Prove gallery browsing works with imported images even when no integrated camera is available.

## Failure modes and diagnostics
- Watch for a `/dev/videoN` that is an ISP output with no sensor bound, missing setfile/firmware, unsupported multiplanar formats, and a portal that publishes a synthetic node without labeling it. A USB camera test proves the userspace chain, not the S10+ hardware.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The report separates real sensor nodes from synthetic sources and never calls synthetic output hardware proof.
2. A real capture is claimed only after a frame is captured and viewable in the gallery; otherwise the exact ISP/driver/firmware blocker is reported.
3. Format/stride/colour-space values are recorded and produce a correct image without corruption.
4. The portal/PipeWire/WebKit chain is verified hop by hop.
5. Capture is owner-initiated, permission-gated, and shows an indicator.
6. Gallery storage, thumbnails, metadata, and browsing work independently with test images.
7. Camera/torch cannot own the flash concurrently.

## Hardware, privilege and rollback safety
No Android camera HAL install, no kernel/ISP register writes, no flash. Capture requires owner action and privacy consent. Preserve existing photos and never overwrite silently.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r27-camera-gallery`, with tests and docs for this component only.
- `docs/component-reports/r27.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if only synthetic capture is possible; report BLOCKED_FIRMWARE/BLOCKED_KERNEL precisely. Do not claim camera success from a test pattern.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.

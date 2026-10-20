# NUXEL R42 — Custom media downloader
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r42-custom-media-downloader`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Implement a lawful, user-consented media downloader with a durable queue, redirect/resume handling, hash verification, filename safety, quota/free-space checks, and clear progress. The branch must exclude DRM bypass, credential scraping, arbitrary code execution, and silent background downloads.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `pwa/nuxel-apps/downloader/app.json`, `pwa/nuxel-apps/downloader/index.html`, `pwa/nuxel-apps/downloader/tests/test-download-queue.js`, `docs/app-store.md`, `configs/nuxel/app-registry/app_registry.json`, `configs/nuxel/security/privacy-config.json`, and `images/s10plus/packages-manifest.json`. The app declares `download:queue`; persistence, resume, integrity, and network-failure behavior need proof.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns download queue state, URL policy, resume/retry, destination naming, integrity, quotas, and UI progress. Does not own DRM circumvention, media extraction from protected services, or a hidden background daemon. No arbitrary shell execution.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Define accepted URL schemes and explicitly reject file/local/SSRF/internal-network targets unless owner-authorized.
2. Implement a persistent queue with pause/resume/cancel, bounded retries, redirect limits, and resumable range requests.
3. Sanitize filenames and directories, prevent path traversal/overwrite, and choose a user-approved destination.
4. Verify checksums where provided and report mismatch without replacing an existing good file.
5. Enforce free-space/quota limits and stop safely on disk full or network loss.
6. Show real bytes/progress/status from the download engine, including stalled/failed states.
7. Test redirect loops, resumed partial files, corrupt payload, cancellation, and app restart.

## Failure modes and diagnostics
- Watch for trusting `Content-Disposition` filenames, following unlimited redirects, resuming a file whose ETag changed, and writing partial files into the final destination. Verify MIME/type and size limits.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The queue persists across app restart and resumes or restarts according to a documented rule.
2. Redirects/resume are bounded and the final URL is validated against URL policy.
3. Path traversal/overwrite attempts are refused.
4. Checksum mismatch is reported and the bad file is not silently installed/moved.
5. Disk-full/network-loss/cancel leave a recoverable state and no corrupt final file.
6. UI progress matches actual bytes/status.
7. No DRM bypass, credential scraping, or arbitrary command execution exists.

## Hardware, privilege and rollback safety
Respect copyright/terms and user consent. No DRM circumvention. Do not download to protected/system paths or run downloaded content. Preserve existing files.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r42-custom-media-downloader`, with tests and docs for this component only.
- `docs/component-reports/r42.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if a requested source requires DRM bypass or credential scraping; refuse it explicitly. Report the limitation rather than implementing a gray-area workaround.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.

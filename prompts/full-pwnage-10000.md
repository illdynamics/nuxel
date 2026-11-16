# FULL-PWNAGE-10000 — NEXUS + NEO Phase 0
## Baseline freeze, device capability truth, graphics ownership map and safe implementation preparation

**Mission class:** Phase 0 — reconnaissance and baseline; no NEO output activation  
**Target repository:** Nuxel `v0.8.1-beta` baseline, subject to live-worktree verification  
**Primary device:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte` / Exynos 9820 / Mali-G76 MP12  
**Architecture:** NEXUS (Nuxel EXtensible Unified Surface System) + NEO (Nuxel Engine for Overlays)  
**Required outcome:** a repeatable, evidence-backed baseline and an exact implementation map for Phases 1 and 2.

---

# 0. Mission command

Read this entire document before acting. Read the supplied NEXUS + NEO engineering specification and performance audit. Execute the Phase 0 work; do not return only a plan. Phase 0 is deliberately non-invasive: inspect, measure, document, build read-only probes and prepare test harnesses. Do not activate a new renderer, alter the active presenter, change frame rate, modify the live compositor, change kernel configuration or alter display ownership.

The objective is to make later NEO work evidence-driven and reversible. Establish exactly what is running on the phone now, which source/build produced it, who owns the panel, what can be measured, what is merely experimental, and how the known-good fallback will be preserved.

## Mandatory device and repository context

**Repository baseline supplied for this mission:** Nuxel `v0.8.1-beta`, archive commit `bd798f7f6c18e454921573251e02a7ac52e8da7c`, audit date 8 November 2026. The live worktree may have advanced; inspect it and never assume the archive is the current checkout.

**Primary target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820, Mali-G76 MP12, Nuxel/Fedora ARM64.

**Expected working checkout on the development Mac:** `~/x/nuxel`. Confirm with `git rev-parse --show-toplevel` and inspect `git status` before edits. Do not edit the uploaded ZIP in place or treat it as the deployed checkout.

**Known device connection supplied by the owner:**

```bash
ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167
```

Prefer the repository's authenticated helper when available, while retaining its strict host-key handling:

```bash
cd ~/x/nuxel
KEY="$HOME/.ssh/wicked_wqn_id_rsa"
test -r "$KEY"
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host 192.168.178.167 \
  --user root --key "$KEY" --status
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host 192.168.178.167 \
  --user root --key "$KEY" --shell
```

If the helper's actual CLI differs, inspect its `--help` and source and use the supported invocation. Direct SSH is an acceptable fallback. Never use `StrictHostKeyChecking=no`, never delete/replace a pinned host key merely to connect, never print private-key contents, and never put secrets into reports. If live SSH is unavailable, do all safe repository-side work and clearly mark physical validation as blocked; do not pretend it happened.

## Non-negotiable graphics safety agreement — applies to every phase

The owner explicitly requires this agreement. It is part of the implementation contract, not an optional test suggestion.

### A. The currently working graphics engine is a permanent fallback

1. The current production Phoc + Mali/GLES composition + `nuxel-wl-fb` + `/dev/fb0` presentation path is the known-good graphics engine. Keep it installed, bootable, selectable and recoverable for the entire NEXUS/NEO project. Do not delete it, overwrite its only binary, replace its service in place, remove its release assets, or remove its recovery scripts.
2. Preserve a verifiable copy of the exact current working presenter binary and its matching service/configuration, plus source/build provenance and SHA-256 hashes. Backups are additive and versioned. Do not assume a newly rebuilt copy is identical to the currently deployed binary; capture the actual deployed binary/hash where permissions permit.
3. The legacy backend remains an explicit `legacy`/fallback profile even after NEO eventually becomes preferred. Never make fallback conditional on NEO being healthy.
4. There must be exactly one panel writer at a time. Do not run two processes that both own `/dev/fb0`, send `FBIOPAN_DISPLAY`, or otherwise drive the panel. Keep the current ownership lock, boot-animation handoff/receipt protocol and service ordering intact.
5. A new candidate must be separately built and staged under a distinct path. Do not replace `/usr/lib/nuxel/nuxel-wl-fb` (or the path discovered on the device) during a canary. Use a controlled, atomic handoff and a tested rollback to the exact saved legacy backend.
6. The current `FBIOPAN_DISPLAY` operation is required by the documented Samsung command-mode panel behaviour. Do not remove or weaken it based on assumptions.

### B. Mandatory on-device visual confirmation for every NEO activation test

Whenever any new NEO runtime component or NEO presentation path is activated for a physical-device test, display an on-device confirmation prompt asking:

> **NEO graphics test: Can you see the Nuxel display working correctly?**
>
> **YES** / **NO**

Requirements:

1. The prompt must be visibly rendered on the phone display during the exact candidate run being tested. An SSH message, terminal output, log entry, notification-daemon acknowledgement, or automated test is not a substitute for the owner's physical confirmation.
2. The owner must physically press **YES within 30 seconds**. Only that explicit on-device YES, tied to the current unique test-run ID, is a pass.
3. **NO** immediately means the candidate failed. Absence of YES by the 30-second monotonic deadline also means failure. Do not interpret a timeout, lost notification, notification-action error, disconnect or missing callback as success.
4. On NO, timeout or inability to prove the prompt was presented, immediately stop the candidate and restore the exact known-good legacy backend. Capture logs and the failure reason after restoring visibility.
5. After rollback, diagnose and fix the root cause. Continue the fix/test/retry cycle whenever it is safe to do so; ask for confirmation again on every new candidate run. Do not merely relaunch the same failed binary/configuration unchanged. Each retry must contain a material code/configuration fix and pass preflight checks.
6. Do not set an arbitrary small retry count as a reason to abandon a safely fixable failure. Continue until the owner explicitly confirms YES or a genuine safety blocker makes another attempt unsafe (for example, legacy rollback cannot be proven, panel ownership is ambiguous, or notification/recovery infrastructure itself is broken). In that case leave the legacy backend active, stop activation attempts and document the blocker rather than risking a black screen.
7. The 30-second timer must use a monotonic clock and must be enforced by a supervisor independent of the candidate code path. Candidate crash, compositor crash, notification failure or loss of the display must still result in timeout and rollback.
8. Use a unique nonce/run ID for each attempt. YES/NO responses from an old notification must not approve a newer run. Ignore stale, duplicate, malformed or late responses.
9. The notification must expose real YES and NO actions. If the existing notification daemon cannot reliably show interactive actions over the full-screen Nuxel session, implement a small native Nuxel confirmation overlay/dialog using the existing trusted UI/session integration. Do not fake action buttons or rely on an unverified `notify-send` option. Audit the current notification stack and select the supported mechanism.
10. The confirmation overlay must be legible, high contrast, touch-friendly, not hidden behind the candidate content, and must not require keyboard input. It must not expose SSH, debugging or privileged controls to ordinary apps.
11. An automated/unit-test mock may test the timer and response state machine, but it must be impossible for a mock, environment variable or agent script to synthesize the live physical YES. Only the owner pressing the displayed YES action in the active run can satisfy the live acceptance condition.
12. Pressing YES confirms only that the display was visible and apparently working for that specific canary attempt. It does not waive automated checks, authorize kernel flashing, or automatically promote NEO to the production default.

The candidate may continue its bounded canary workload after a valid YES, but any later loss of display, service crash, watchdog failure, frame corruption or panel ownership conflict must still trigger automatic rollback. Every new candidate version/activation requires a new 30-second confirmation.

### C. General engineering rules

- Inspect actual source and device state before editing. The repository is evolving; verify every path and assumption.
- Do not flash a kernel, boot image, recovery image, bootloader, modem or partition in these phases. No repartitioning, bootloader unlock, firmware replacement or risky panel-driver activation.
- Do not enable `CONFIG_DRM_EXYNOS` blindly. The supplied S10+ configuration says the old Exynos7 DECON driver is not the Exynos 9820 DPU20 driver and may conflict with the working fbdev panel driver.
- Do not globally advertise `zwp_linux_dmabuf_v1`, force WebKit DMA-BUF mode, force Electron GPU, inject host Mali libraries into Flatpaks, swap Mesa/wlroots globally, or claim direct scanout. The live NEO/DMA-BUF experiment previously crashed Phoc during screencopy and was reverted.
- Do not remove the NEON scaler, cached SHM buffers, partial-row blits, idle pacing, screen-off capture stop, full repaint logic or any other existing optimization without a measured replacement and regression tests.
- Do not modify the active frame-rate cap during these phases unless that phase explicitly calls for a separately controlled experiment. Keep the current `NUXEL_TARGET_FPS=20` and 8/3/1 FPS idle policy as the default baseline.
- Do not claim a percentage gain without an actual controlled before/after measurement. Separate estimates from measured device results.
- Preserve touch, lockscreen, status bar, wake ordering, animation handoff, screen blanking, app rendering, orientation and service recovery.
- Use atomic file writes, backups, checksums, bounded systemd restart policies and explicit rollback commands.
- Do not run GUI applications as root. Root may manage system services; interactive confirmation UI must run in the active Nuxel graphical session as its normal session user or through the established trusted system/session bridge.
- Do not leak credentials, cookies, private keys, tokens or personal information into logs or artifacts.


# 1. Required reading and source-of-truth hierarchy

Read at minimum:

- `NEXUS-NEO-ENGINEERING-SPEC-2026-11-08.md` (the approved architecture specification in the provided artifacts; locate the current copy if it has been added to the repository).
- `Nuxel-Performance-Audit-2026-11-08.md` (the source audit; locate the current copy if checked in).
- `GPU-ACCEL-REPORT.md`.
- `ARCHITECTURE.md`, `SYSTEMD-GRAPH.md`, `PWNAGE-91000-REPORT.md`.
- `release/s10plus/gpu/graphics-profile.json` and `gpu-manifest.json`.
- `tools/s10plus/a67/nuxel-wl-fb.c` in full.
- `tools/s10plus/a29/wlr-screencopy-unstable-v1.xml` in full.
- `services/nuxel-session/systemd/nuxel-wl-fb.service`, `nuxel-wayland.service`, and `services/nuxel-s10/systemd/nuxel-wl-fb.service.d/15-idle-fps.conf`.
- `tools/s10plus/a67/sync-gpu-release-assets.sh`, its manifest generator, related GPU wrapper/profile tools, and `tests/pwnage60000/test_gpu_manifest.py`.
- `tools/s10plus/a67/mesa-kbase-wayland-wsi.patch` and `wlroots-kbase-linear-dmabuf.patch` including their reports/decision documents.
- Existing PWNAGE prompts/tests under `prompts/`, `nuxel-pwnage/`, and `tests/` that describe release gates and hardware validation.

Use this evidence hierarchy:

1. Fresh live-device runtime evidence from this exact boot.
2. Current checked-out source and deployed binary hashes.
3. Current build/configuration and release manifests.
4. Archived reports and the uploaded audit/spec.
5. Assumptions or generic upstream documentation.

If evidence conflicts, report the conflict and establish which artifact is current. Never silently copy a historical value into the live capability profile.

# 2. Phase 0 scope boundary

## Allowed

- Read-only inspection of source, kernel config, sysfs, devices, processes, services, Wayland globals, runtime JSON and logs.
- Read-only live probes and benchmark scripts that do not alter graphics state.
- Host-side unit tests, protocol XML validation, static analysis and source instrumentation plans.
- Create documentation, JSON schemas, baseline scripts and test fixture definitions under the Phase 0 evidence/docs area.
- Copy/hash the currently deployed legacy presenter and its service/config into a versioned backup location, provided this is a read-only copy and does not change active paths.
- Measure current performance using existing telemetry and safe workload scripts.

## Forbidden

- No NEO runtime activation on the physical phone in Phase 0.
- No new NEO process attached to the live frame path.
- No modified `nuxel-wl-fb` executable deployed to the device.
- No `copy_with_damage` activation, no FPS changes, no new service enablement, no systemd restart solely for a measurement, no global notification changes.
- No DMA-BUF/KMS/DRM activation, no experimental wlroots/Mesa patch activation, no kernel build/flash.
- No deletion, replacement, chmod change or in-place edit of the working legacy presenter, its service, its owner lock or recovery assets.

If a requested measurement would require restarting the compositor or display bridge, do not do it during Phase 0. Record the missing measurement and provide a safe test procedure for a later controlled phase.

# 3. Establish exact source/worktree identity

1. Verify the repository root and branch. Record `git rev-parse HEAD`, branch, `git status --short`, dirty/untracked files, submodule state, and the archive commit if available.
2. Record `VERSION` and compare it to the supplied v0.8.1-beta archive. Do not assume version alone identifies the deployed build.
3. Identify canonical source versus release copies for GPU wrapper, session script, graphics profile, presenter, service units, protocol XML and release manifests.
4. Hash source, release copies and build outputs. Record any stale copies, particularly the known candidate mismatch in `release/s10plus/gpu/nuxel-session.sh`; do not silently sync or mutate it in this phase. Log it as a release issue with exact hashes and the supported repair command.
5. Identify the actual build system and test commands from Makefiles/scripts/CI. Do not invent `make test` if no such target exists.
6. Create `docs/nexus-neo/phase-0/` with `BASELINE.md`, `SOURCE-MAP.md`, `DEVICE-CAPABILITIES.json`, `SERVICE-OWNERSHIP.md`, `PERFORMANCE-BASELINE.csv` (or equivalent raw format), `ISSUES.md`, and a `SHA256SUMS` manifest. Add raw captures under a timestamped evidence subdirectory.

# 4. Live S10+ reconnaissance

Connect over the known WLAN SSH route. Record the exact date/time, boot ID, kernel release, OS release, device model, board/DT identity, uptime, CPU topology, RAM, GPU identity, panel mode/geometry and thermal sensors. Use commands supported by the live device; capture stdout/stderr and exit codes.

At minimum inspect:

- `uname -a`, `/etc/os-release`, `/proc/cmdline`, boot ID, kernel config source (`/proc/config.gz` or `/boot/config-*` only if actually present).
- `/dev/mali0`, `/dev/udmabuf`, `/dev/fb0`, all `/dev/dri/*`, `/dev/dma_heap/*`, `/dev/video*`, `/dev/media*`; record major/minor, ownership, permissions and driver symlinks.
- `/sys/class/misc/mali0/device/gpuinfo`, framebuffer geometry/bitfields/stride/fixed info, panel and display-related sysfs nodes, relevant device-tree compatibles and bound drivers.
- `CONFIG_DRM`, `CONFIG_DRM_EXYNOS`, `CONFIG_DRM_VGEM`, `CONFIG_UDMABUF`, `CONFIG_DMA_SHARED_BUFFER`, `CONFIG_SYNC_FILE` from the actual active config. Mark unknown if config is unavailable; do not infer from a fragment.
- GPU renderer probe result, EGL vendor/config, GLES version, Phoc environment and open file descriptors. Confirm renderer name and device nodes, not only environment variables.
- `phoc`, `nuxel-wl-fb`, wrapper, fallback/painter processes; all command lines, owners, cgroups, open display FDs and restart counters.
- systemd unit state, drop-ins, dependencies/order, active and enabled status, restart policy, owner lock path and boot-animation handoff/receipt files.
- Wayland runtime socket, compositor globals and the bound screencopy manager version. Record if a safe read-only protocol probe exists; do not restart Phoc to add one.
- current graphics-profile and GPU-manifest content and their consistency with live devices.

Do not print sensitive environment variables wholesale. Redact tokens, cookies, Wi-Fi passwords, private paths containing secrets and unrelated personal data.

# 5. Map the working graphics chain and ownership

Produce an exact sequence diagram for the S10+ path as it is actually deployed:

`Application/Wayland surface → Phoc/wlroots GLES2 composition → screencopy manager → A67 SHM buffer → compare/damage logic → NEON row expansion/conversion → framebuffer mmap writes → FBIOPAN_DISPLAY → Exynos DPU20/fbdev panel`.

Verify every stage, and label it `VERIFIED`, `HOST_VERIFIED`, `EXPERIMENTAL`, `BLOCKED`, `UNAVAILABLE` or `UNKNOWN`.

Inspect the complete A67 presenter and document:

- Wayland global binding and screencopy protocol version.
- The existing damage callback and its current behaviour.
- All `capture_output`/`copy` request sites and their event-loop sequencing.
- SHM buffer creation, size/stride/format validation, reuse, resize and destruction.
- previous-frame cache and row comparison.
- dirty-row/run tracking and partial-row framebuffer blit path.
- NEON scaler/conversion routine and its input/output layout.
- framebuffer map, pitch, x/y offsets, color bitfields and pan ioctl.
- display-off handling, control FIFO/event, wake sequencing, forced full repaint and brightness/backlight sequencing.
- single panel owner lock, painter-stop mechanism, boot animation receipts and recovery behaviour.
- target FPS and 8/3/1 idle backoff logic.

Explicitly preserve the facts already found in the supplied source audit unless fresh source proves otherwise:

- NEON 2× row expansion exists and is already optimized; don't rewrite it.
- SHM buffers are reused; don't allocate/map a new one every frame.
- unchanged frames skip blit/pan; don't remove the hash/damage fast path.
- partial-row updates exist; do not make them less precise.
- `FBIOPAN_DISPLAY` remains required after changed frames.
- display-off stops capture; keep it that way.
- current service override sets `NUXEL_TARGET_FPS=20`; idle pacing falls to 8/3/1 FPS.

# 6. Baseline measurements

The supplied audit's Nov 6–7 samples report approximate averages of capture 5–7 ms, comparison 0–3 ms, blit 1–4 ms and panel pan 9–10 ms. Treat them as historical reference only. Gather a fresh baseline if safe without restarting services.

Use at least the following workload matrix. Each measurement must state whether it is a live-device result, historical log, host proxy or unavailable:

1. Static Home for 5 minutes.
2. Home icon/tap and one ordinary app launch.
3. App drawer open/close and scroll.
4. Desktop/workspace transition.
5. Continuous vertical and horizontal scrolling.
6. Quick Settings/notification surface open/close.
7. Lock/unlock and lockscreen indicator update.
8. Browser/PWA controlled animation and page scroll.
9. Full-screen video only if already supported; label decode separately from composition.
10. Display off, wait, wake and first lockscreen frame, using existing safe workflow only.

Capture when available:

- `FRAMES_OK` fields: total, fps_1s, failures, blits, present_skipped, capture_avg_ms, compare_avg_ms, blit_avg_ms, pan_avg_ms, damage ranges/runs, damage_blits, decon pan success/failure.
- Per-process CPU time/utilization and RSS for Phoc, bridge, WebKit and Home.
- System CPU/load/memory, GPU load/frequency if genuinely exposed, thermal zones, battery current/voltage/temperature and throttling counters.
- frame interval histogram/p50/p95/p99 if a safe existing capture source supports it. Do not invent p95 from averages.
- user-observed stutter only if actually observed; do not claim the agent can see the phone.

Do not install intrusive profilers or change CPU governor/brightness/thermal policy just to obtain a preferred result. Keep repeated runs at the same brightness/power state/starting thermal band where possible. If the owner must perform a UI workload, ask for one concise action only when no automation exists; do not claim it was performed.

# 7. Capability discovery model

Create a versioned, machine-readable capability report. It must report independent states rather than one `gpu=true` flag. Include at least:

- device/kernel/boot identity;
- GPU node, driver, renderer, EGL/GLES, successful probe evidence;
- SHM support and formats;
- udmabuf presence and proven use;
- DMA-BUF export/import evidence, formats/modifiers and exact producer/consumer pairs tested;
- GBM presence and working DRM render device, if any;
- DRM primary device, connectors, CRTCs, planes, atomic properties, and test-only commit evidence if safely queryable;
- `fbdev` path and actual panel commit mechanism;
- Wayland globals/protocol versions;
- explicit/implicit synchronization primitives and evidence;
- current backend profile and fallback profile;
- confidence/status and timestamp for each feature.

Use these status values consistently: `VERIFIED`, `HOST_VERIFIED`, `EXPERIMENTAL`, `BLOCKED`, `UNAVAILABLE`, `UNKNOWN`. Missing device nodes mean unavailable for this boot, not proof that all future kernels lack the feature.

The expected current S10+ baseline from the archive is Mali-G76 through Samsung kbase at `/dev/mali0`, Mesa/Panfrost EGL/GLES, Phoc `WLR_RENDERER=gles2`, SHM/fbdev final presentation, `/dev/fb0`, no proven `/dev/dri` KMS path, `CONFIG_DRM_EXYNOS=n`, and no production DMA-BUF scanout. Verify each item on device.

# 8. Fallback integrity audit

The legacy backend must be preserved, not merely described.

1. Determine the actual deployed executable path, hash, ELF architecture, package ownership, service unit and environment.
2. If safe, copy the installed executable and all required matching config/assets to a versioned immutable backup directory. Include metadata and SHA-256; do not replace the active executable.
3. Verify the source/release counterpart and note any mismatch. The checked-in `sync-gpu-release-assets.sh` synchronizes GPU policy/session assets and regenerates the manifest; inspect it but do not run it during this baseline-only phase unless the owner separately authorizes a release repair.
4. Document the exact rollback sequence from a candidate to legacy, including service stop/start order and proof of single ownership.
5. Verify that fallback can start with existing files and dependencies. Do not test by stopping the currently visible service in Phase 0.
6. Record a recovery path that can be executed over SSH even when the candidate display is blank. Test only harmless syntax/availability checks, not a live owner handoff.

# 9. Notification confirmation contract preparation

Phase 0 does not activate NEO and must not show a live canary confirmation. However, it must inspect the current Nuxel notification/session UI architecture and document how Phase 1 will implement the required confirmation mechanism.

Find the actual notification daemon, D-Bus implementation, action support, PWA/native notification mechanisms, layer-shell capabilities and the currently logged-in graphical user. Do not assume `notify-send` action flags are supported.

Deliver a design for a trusted `neo-confirm` facility with:

- a unique test-run nonce;
- a physical, touch-accessible YES/NO prompt;
- 30-second monotonic timeout;
- exact-run response validation;
- one-shot response semantics;
- supervisor-controlled timeout independent of the candidate;
- automatic rollback on NO, timeout, no visible notification or candidate death;
- audit event recording without accepting a synthetic live YES.

Record the chosen UI transport and fallback notification transport, including why they are reliable in fullscreen Nuxel.

# 10. Tests and commands

Inspect project conventions and run the relevant non-invasive tests:

- protocol XML validity / generated client bindings consistency;
- existing A67 presenter unit/source tests;
- GPU manifest consistency tests (record the known stale session-script copy if it still exists; do not silently repair it in Phase 0);
- static analysis and compile-only tests for read-only probe additions;
- all relevant tests whose execution cannot change device graphics state.

Never trigger the full OS build, kernel image, flash or deployment unless the existing workflow requires it and it is safe. Do not call a suite passed if it timed out or was not run. Record exact command, exit status, duration and summary.

# 11. Phase 0 deliverables

Create/complete:

```text
docs/nexus-neo/phase-0/
  BASELINE.md
  SOURCE-MAP.md
  DEVICE-CAPABILITIES.json
  SERVICE-OWNERSHIP.md
  PERFORMANCE-BASELINE.md
  PERFORMANCE-BASELINE.csv       # if metrics are available
  FALLBACK-INTEGRITY.md
  CONFIRMATION-DESIGN.md
  ISSUES.md
  evidence/<timestamp>/...
  SHA256SUMS
```

Optional read-only utilities may be added under `tools/nexus/` or the repository's established tools directory. Do not create a new build framework if existing scripts suffice.

`BASELINE.md` must contain the true current status and explicit blockers. `DEVICE-CAPABILITIES.json` must be valid JSON and distinguish missing/unknown from false. Evidence files must be sanitized. Include exact paths, commits, hashes and test commands.

# 12. Phase 0 acceptance gates

Phase 0 is done only when:

- current checkout and live phone identity are recorded;
- production renderer and display path are mapped end-to-end;
- active panel owner and all relevant systemd dependencies are identified;
- deployed fallback binary/config are hash-pinned and recoverability is documented;
- live GPU/DRM/DMA-BUF/SHM capability states are evidenced;
- current screencopy version and `copy_with_damage` support are verified from XML and runtime binding evidence;
- performance baseline is repeatable or missing measurements are explicitly blocked;
- existing NEON/SHM/damage/idle/wake optimizations are documented as preserve-only;
- confirmation UI design meets the exact 30-second physical YES requirement;
- no active graphics behaviour, FPS policy, kernel config or panel ownership has changed;
- relevant tests have honest results;
- the Phase 1/2 implementation plan is specific to this source tree.

# 13. Final engineering report

Finish with a concise but complete report:

1. repository commit/version/dirty state;
2. live phone boot/kernel/device identity;
3. actual active graphics pipeline and owner;
4. verified/blocked/unavailable capability matrix;
5. raw performance baseline and missing metrics;
6. exact legacy fallback binary/service hashes and recovery route;
7. notification confirmation implementation recommendation;
8. files/scripts/docs created;
9. tests run and outcomes;
10. risks/blockers and Phase 1 go/no-go.

**Do not activate NEO in Phase 0. Do not remove or change the current graphics engine.**

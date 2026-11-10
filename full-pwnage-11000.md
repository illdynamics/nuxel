# FULL-PWNAGE-11000 — NEXUS + NEO Phase 1
## NEO contracts, observe-only runtime integration, bounded telemetry and physical confirmation framework

**Mission class:** Phase 1 — create NEO's internal contracts and observability without changing presentation  
**Prerequisite:** Phase 0 baseline completed and reviewed  
**Target:** S10+ production session, with host tests and an explicitly opted-in observe-only device canary  
**Default:** legacy graphics remains active; NEO observe mode is opt-in and must not alter pixels, frame scheduling or panel ownership.

---

# 0. Mission command

Read this entire prompt and the approved NEXUS + NEO engineering spec. Inspect the completed `docs/nexus-neo/phase-0/` evidence and re-verify the live device. Implement Phase 1, not Phase 2. Build NEO's small internal data contracts, capability discovery, bounded telemetry, status tooling and the physical YES/NO confirmation mechanism required for all future NEO activation tests.

The result must be useful but deliberately passive: NEO can observe and describe the existing pipeline, assign IDs to measured frames/events and expose diagnostics, but it must not allocate replacement graphics buffers, import DMA-BUFs, change capture requests, change composition, alter frame pacing or take control of `/dev/fb0`.

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


# 1. Phase 1 entry gate

Before code changes:

1. Confirm the Phase 0 acceptance report exists and its status is `GO` or list every unresolved blocker.
2. Re-run minimal live checks for boot ID, kernel, current service state, current presenter binary hash, active Phoc, `/dev/fb0`, `/dev/mali0`, `/dev/dri` and owner lock.
3. Confirm the actual deployed legacy executable and its rollback artifact still match the recorded hashes. If they differ, stop and refresh the baseline; do not overwrite either version.
4. Check `git status`. Preserve user changes and unrelated work.
5. Read all Phase 0 evidence, source map, fallback instructions and confirmation design.

If the Phase 0 report is absent or the fallback is not proven, do not activate anything. You may complete safe host-side contracts/tests, but report the missing gate.

# 2. Phase 1 scope and strict non-goals

## In scope

- Versioned NEXUS capability schema and honest runtime probe.
- NEO internal types/contracts for surface IDs, buffer descriptors, damage regions, sync state, frame IDs, composition decision enums and presentation telemetry.
- A small bounded telemetry facility (ring buffer or equivalent) with no blocking I/O on the render path.
- Read-only instrumentation of existing A67 presenter stages and, where safe, Phoc surface/commit/frame events.
- Read-only `neo-probe`, `neo-status` and `neo-dump` tooling following repository conventions.
- Explicit `legacy` (default) and `observe` modes, with no display-path selection in Phase 1.
- The trusted `neo-confirm` physical YES/NO confirmation mechanism with a monotonic 30-second timeout and independent supervisor.
- Host/unit/integration tests, including simulated timeout/NO/YES cases and device tests in observe-only mode.

## Not in scope

- No `copy_with_damage` usage or changes to the current capture request.
- No new `wl_shm` or DMA-BUF allocations, imports, exports, GBM/udmabuf pools or GPU memory changes.
- No `linux-dmabuf` global advertisement changes.
- No KMS/DRM display backend, atomic commits, plane assignment or direct scanout.
- No retained LayerTree replacing wlroots' scene graph, no compositor replacement and no second compositor.
- No new GPU composition path, WebKit WSI changes, Electron policy changes or Flatpak host GL injection.
- No FPS/idle cadence changes.
- No replacement or removal of the current presenter, service, owner lock or fallback.

# 3. Architecture integration rules

NEO is a Nuxel engine integrated with the existing Phoc/wlroots compositor and its current bridge. Phoc/wlroots remains the only authoritative owner of Wayland surfaces, focus, stacking, input routing, layer-shell roles and surface lifecycle.

Do not build a parallel compositor or a duplicate authoritative scene tree. For Phase 1, an NEO surface reference is a read-only observation record containing a stable NEO-local ID and a reference/generation tied to an existing compositor object. Do not keep stale Wayland pointers after object destruction.

NEO contracts should be internal C APIs if the existing code is C and the current build system supports it. Inspect build conventions, compiler standard, warnings, memory allocator practices and test harness before choosing structure. Avoid a new framework or dependency. Use opaque handles where possible. Do not expose private Wayland pointers as persistent IDs.

Proposed directory (adapt if repo conventions are stronger):

```text
graphics/nexus/
  README.md
  schema/nexus-capabilities-v1.schema.json
  profiles/s10plus.json
graphics/neo/
  include/nuxel/neo/{types,capabilities,frame,damage,telemetry,confirm}.h
  src/{core,capabilities,telemetry,confirm}/...
  tools/{neo-probe,neo-status,neo-dump}/...
  tests/{unit,integration,fixtures}/...
docs/nexus-neo/phase-1/
  IMPLEMENTATION.md
  CAPABILITY-MATRIX.md
  TELEMETRY.md
  CONFIRMATION-UI.md
  TEST-RESULTS.md
  ROLLBACK.md
```

Do not mechanically create every proposed file if a smaller clean organization is better. Record any layout deviation.

# 4. Required NEO contracts

Create typed, versioned contracts for the following concepts. Names may adapt to local coding conventions, but semantics must remain clear.

## 4.1 Device and pipeline capabilities

Represent each capability independently with state, evidence source, timestamp, device/boot identity and optional reason:

- `VERIFIED`, `HOST_VERIFIED`, `EXPERIMENTAL`, `BLOCKED`, `UNAVAILABLE`, `UNKNOWN`.
- GPU node/driver/renderer/EGL/GLES.
- `wl_shm` support and formats.
- udmabuf presence and actual verified producer/consumer pair.
- DMA-BUF export/import pair, formats and modifiers, not generic `true`.
- GBM and DRM main/render device.
- KMS connector/CRTC/plane/atomic support only when actually enumerated.
- fbdev and actual pan/commit path.
- Wayland globals and protocol versions.
- synchronization support/evidence.
- current active profile, available fallback and candidate profile states.

Do not mark `direct_scanout`, `overlay_planes`, `dmabuf_presented` or `fully_accelerated` as verified on this S10+ unless the full physical producer→consumer→display path is demonstrated. Missing `/dev/dri` must be recorded as unavailable on this boot, not masked by a build config.

Schema requirements:
- include `schema` version string;
- include target and boot ID;
- use explicit `null` or a status object for unknown data;
- include probe method/source and timestamp;
- reject malformed profile JSON and unknown required schema version;
- maintain backward compatibility or update every consumer atomically.

## 4.2 Frame and event identity

- NEO-local monotonically increasing frame/event sequence number.
- Include boot ID and process/session generation to avoid cross-boot collision.
- Record timestamps with `CLOCK_MONOTONIC` or `CLOCK_MONOTONIC_RAW` consistently; document conversions.
- Do not use wall clock for timeout or latency math.
- Do not keep raw pointers in persistent telemetry.

## 4.3 Surface observation record

Minimum read-only fields:
- NEO-local surface ID and generation;
- role/class if safely available;
- current visible/hidden state;
- output ID/geometry and scale/transform;
- buffer type class (`SHM`, `DMABUF`, `UNKNOWN`) without exposing client memory;
- committed content generation;
- aggregate damage count/area where available;
- creation/destruction lifecycle.

The observer must safely detach when a surface is destroyed or client disconnects. Never dereference a destroyed wlroots object.

## 4.4 Buffer descriptor contract (metadata only in Phase 1)

Define the fields NEO will need later: stable ID/generation, dimensions, format, per-plane strides/offsets, modifiers, allocator/exporter, ownership/reference state, acquire/release sync status, import status and memory size. Phase 1 must not allocate/import/export these buffers. Ensure descriptor structs do not imply ownership of an FD unless an explicit ownership API is called.

## 4.5 Damage region contract (metadata only in Phase 1)

Define a bounded region collection with validated x/y/width/height, output generation, coordinate-space label and a `full_repaint` marker. Include overflow-safe bounds checks. No Phase 1 code may change the current damage/copy behaviour.

## 4.6 Composition/presentation enums (descriptive only)

Provide truthful decisions such as `LEGACY_SHM_FBDEV`, `GPU_COMPOSED`, `DMA_BUF_IMPORTED`, `KMS_PLANE`, `DIRECT_SCANOUT`, `SOFTWARE_FALLBACK`, `UNKNOWN`. A recorded mode means only what its name asserts; distinguish render source, transport, composition and physical display backend. In this S10+ run, expected output is GPU-composed / SHM-captured / CPU-fbdev-presented if live probes confirm it.

# 5. NEO telemetry implementation

Implement telemetry so the instrumentation is cheaper than the work being measured.

Requirements:

1. Fixed-size bounded ring or similarly bounded queue; fixed maximum number of events; defined overflow/drop counter.
2. No file writes, JSON formatting, D-Bus calls, blocking locks or dynamic allocation on the per-frame hot path.
3. Prefer a single-producer or low-contention design consistent with actual call contexts. Do not introduce a complicated lock-free algorithm without tests and justification.
4. Store compact binary records and export/format them from a non-render thread or diagnostic tool.
5. Sample high-frequency events if necessary, but never silently change counters or drop required error events.
6. Add telemetry enable/disable and sampling settings; disabled by default for release or at a low safe overhead measured in Phase 1.
7. Include a schema/version field and event type.
8. Ensure no raw client content, buffer pixels, FDs, credentials, tokens or user data enter telemetry.
9. Record ring overrun/drop count and expose it through `neo-status`.
10. Add duration metrics for existing steps only where accurate start/end points exist. Preserve stage semantics: capture-ready time is not necessarily GPU render time; fbdev pan duration is a panel commit proxy, not proven VSync/presentation timestamp.

At minimum observe:

- frame loop start/end;
- capture request/ready/failure;
- compare start/end;
- blit start/end;
- `FBIOPAN_DISPLAY` start/end and return code;
- skipped present;
- current display on/off and forced full repaint;
- screen wake request/first post-wake commit;
- NEO observer activation/disable;
- confirmation prompt start/YES/NO/timeout/failure;
- fallback begin/completed/error.

Add histograms or raw sample export so p50/p95/p99 can be computed offline. Do not compute percentiles from averages.

# 6. Read-only runtime integration

Add an explicit mode such as `legacy` and `observe`. `legacy` must remain the default and behave byte-for-byte/semantically as before. `observe` may add measurement hooks but must not alter capture requests, buffer allocation, frame pacing, frame contents, composition choices, display ownership or service ordering.

Implementation rules:

- Use a compile-time feature or explicit environment/config switch for instrumentation, default off unless repository policy dictates otherwise.
- If the NEO observer fails to initialize, silently fall back to legacy behaviour with a clear diagnostic; it must never stop the display path.
- Observer callback failure must not propagate into compositor render/present failure.
- Never block Wayland dispatch waiting for telemetry.
- Bound all telemetry memory and CPU.
- Keep `NUXEL_TARGET_FPS=20` and current 8/3/1 idle cadence untouched.
- Do not alter the A67 `frame_damage()` callback or the ordinary `copy()` request in Phase 1.
- Preserve all existing `FRAMES_OK` output fields to avoid breaking diagnostic parsers; new fields may be added compatibly or exported separately.

# 7. Implement `neo-probe`, `neo-status` and `neo-dump`

Use repository's existing shell/C/Python conventions. Tools must be read-only.

`neo-probe`:
- collect current boot/device identity and capability states;
- check actual nodes, sysfs binding, renderer probe artifacts, Wayland globals/version and profile JSON;
- never load a module, create a DRM master, change display mode, advertise a protocol or perform a panel commit;
- support human-readable and JSON output;
- exit nonzero only for malformed/inconsistent required state, not merely because an optional capability is unavailable.

`neo-status`:
- show active `legacy`/`observe` mode;
- show current backend/profile and fallback availability;
- show NEO observer health, ring occupancy/overflow, last event age and frame stage summaries;
- clearly say `GPU-rendered / SHM-presented / CPU-fbdev` when that is the actual path, rather than `fully accelerated`.

`neo-dump`:
- export a sanitized bounded telemetry snapshot to a specified evidence directory;
- include schema version, boot ID, timestamps and redaction status;
- never dump frame pixels, FDs or sensitive environment.

# 8. Implement trusted `neo-confirm` physical confirmation

This is a required Phase 1 deliverable because Phase 2 must not begin live canary activation without it.

## 8.1 UI behaviour

Create a small high-contrast on-device prompt integrated with the existing Nuxel notification/session UI. The prompt must be above fullscreen content and accept touch. It must display the exact message:

**NEO graphics test: Can you see the Nuxel display working correctly?**

Buttons: **YES — display is visible** and **NO — display is not working**. Show a visible countdown from 30 seconds.

The dialog/notification should not obscure the entire screen; it should make enough of the underlying UI visible for the owner to judge whether it is working. Do not use browser `alert()` or any dialog that blocks the Wayland/session event loop.

## 8.2 State machine

Per unique run ID:

```text
CREATED → DISPLAY_REQUESTED → DISPLAYED/ACKNOWLEDGED
  ├─ physical YES before deadline → CONFIRMED
  ├─ physical NO                 → REJECTED
  ├─ deadline expires            → TIMED_OUT
  ├─ notification/UI failure     → DISPLAY_FAILED
  └─ candidate dies              → CANDIDATE_FAILED

REJECTED/TIMED_OUT/DISPLAY_FAILED/CANDIDATE_FAILED → ROLLBACK_REQUIRED
```

- Use monotonic 30-second deadline.
- One response only; YES after deadline is rejected and logged as late.
- Run ID must be bound to the action callback; a stale action must not confirm the current run.
- The trusted supervisor, not the candidate, owns the timeout and failure decision.
- If display acknowledgement cannot prove the overlay was submitted to the active visible session, mark `DISPLAY_FAILED` and rollback.
- Only an actual on-device press can set live `CONFIRMED`.

## 8.3 Supervisor/recovery

A supervisor must be able to stop the candidate and restore legacy even if the candidate crashes or blocks. The supervisor and rollback commands must not depend on NEO library code. Use systemd, a small established root supervisor or the repository's current service watchdog design; avoid adding a new daemon if existing systemd units and a small one-shot helper suffice.

Do not start any candidate and legacy panel writers concurrently. Preserve a single owner lock and verify its PID/process identity. A stale lock must be handled safely, not deleted while a real writer is alive.

## 8.4 Testing the confirmation mechanism

- Unit tests for YES-before-deadline, NO, timeout, late YES, duplicate click, stale run ID, candidate death, notification render failure, supervisor restart and clock changes.
- Use a fake monotonic clock for tests.
- Test notification action support on the actual Nuxel session without activating a new display backend; the legacy graphics path remains active.
- On physical device test, activate only the observe-only NEO instrumentation, display the prompt, and require the owner's real YES within 30 seconds. If timeout/NO occurs, disable the observer and return to plain legacy mode, then fix/retry the confirmation UI. Do not fake the live YES.
- If the agent cannot obtain a physical YES in this execution, do not claim this acceptance gate passed.

# 9. Physical observe-only activation test

After host tests pass and the fallback hash is re-verified:

1. Prepare a candidate build separate from the current installed binary.
2. Confirm preflight: current Phoc/presenter healthy, legacy fallback available, owner lock correct, notification action path ready, run ID unique, rollback supervisor armed.
3. Activate only the NEO observer. It must not alter the display pipeline.
4. Show the 30-second question and wait for real physical YES.
5. If YES: run a short observe-only workload and collect telemetry, ensuring display content, frame rate and panel owner remain unchanged.
6. If NO/timeout/notification failure/candidate crash: turn off the observer, preserve legacy, collect logs, fix the root cause and retry a materially changed build when safe.
7. Never use an SSH command to simulate pressing YES.

This physical test does not authorize Phase 2. It only proves the observer and confirmation mechanism.

# 10. Tests and quality gates

Create unit tests for capability parsing, enum validity, event-ring wrap/overflow, timestamp math, surface lifecycle generation, damage bounds validation, buffer metadata size/overflow, telemetry sanitization and confirmation state machine.

Integration tests must:
- run NEO observer off and on and compare current frame output/behaviour;
- confirm legacy output fields remain parsable;
- ensure telemetry cannot block when ring is full;
- destroy surfaces/client objects and prove no stale pointer is used;
- malformed profile JSON fails closed;
- unavailable DRM/DMA-BUF remains reported honestly;
- run the existing GPU manifest tests and the repository's applicable graphics/PWNAGE gates.

Performance gate:
- Compare `legacy` versus `observe` under identical workload.
- Target negligible observer overhead; do not accept more than 1% extra active presenter CPU or a measurable p95 frame-latency regression without a documented reason and opt-in-only status.
- If measurement resolution is insufficient, say so; do not fabricate zero overhead.

# 11. Deployment, default and fallback

- `legacy` remains the installed/default profile.
- NEO observer remains opt-in and disabled by default until Phase 1 passes.
- Use a separate candidate artifact and manifest entry.
- Do not replace the legacy executable or edit the canonical active service `ExecStart`.
- Add a rollback helper only if needed; test its syntax and dry-run logic.
- Record candidate and fallback hashes on host and device.
- Ensure a candidate service failure cannot prevent legacy from starting at boot.
- Do not change panel owner count or boot animation/receipt sequencing.

# 12. Phase 1 deliverables

```text
graphics/nexus/...                         # schema, profile and docs

graphics/neo/...                           # contracts, telemetry, confirmation

docs/nexus-neo/phase-1/
  IMPLEMENTATION.md
  CAPABILITY-MATRIX.md
  TELEMETRY.md
  CONFIRMATION-UI.md
  PERFORMANCE-OVERHEAD.md
  TEST-RESULTS.md
  DEPLOYMENT-ROLLBACK.md
  evidence/<timestamp>/...
```

Include a manifest with hashes for all NEO binaries, scripts, schemas and profiles. Ensure release packaging does not accidentally promote NEO observer or confirmation UI into the default display route.

# 13. Phase 1 completion criteria

Phase 1 passes only when:

- NEXUS capability/profile schema is versioned and truthful;
- NEO types/contracts exist and are tested;
- telemetry is bounded and nonblocking;
- observer attaches safely without duplicating compositor authority;
- `legacy` remains the default and is unchanged;
- `neo-probe`, `neo-status`, `neo-dump` are read-only and functional;
- the physical YES/NO confirmation UI and independent 30-second supervisor work;
- live observe-only test gets the owner's physical YES, or is explicitly marked blocked and safely rolled back;
- no DMA-BUF/KMS/damage/fps/panel path changed;
- all tests, overhead measurements and rollback steps are recorded.

# 14. Final engineering report

Report changed files, new interfaces, schema version, how observer data is collected, exact notification mechanism, state-machine test results, host/device test outcomes, overhead measurements, legacy hashes, current active mode, any blocked gates and explicit Phase 2 readiness.

**Do not implement Phase 2 in this mission. Do not change the capture request or display presentation path.**

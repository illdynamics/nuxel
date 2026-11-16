# FULL-PWNAGE-12000 — NEXUS + NEO Phase 2
## Damage-driven screencopy, validated partial updates and reversible fbdev presenter canary

**Mission class:** Phase 2 — first controlled NEO change to the current presentation pipeline  
**Prerequisites:** Phase 0 accepted; Phase 1 contracts/telemetry/physical confirmation mechanism accepted  
**Target:** Galaxy S10+ A67 Wayland-to-fbdev presenter  
**Default after implementation:** existing legacy `copy()` presenter remains production default; damage path is opt-in canary until physical acceptance is complete.

---

# 0. Mission command

Read this complete prompt, the NEXUS + NEO specification, Phase 0 and Phase 1 reports and the full current A67 source. Execute Phase 2: implement a damage-aware capture/consumption path using the screencopy protocol's `copy_with_damage` and damage events, while preserving the current full-copy path as a runtime fallback and retaining the exact currently deployed presenter as a separate fallback binary/service.

This phase does **not** implement DMA-BUF, direct scanout, KMS, GPU plane composition, WebKit WSI, new GPU allocation, a new compositor, a new kernel or a frame-rate policy change. It optimizes the existing stable pipeline and introduces the first real NEO canary behind a strict physical confirmation gate.

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


# 1. Entry gate and exact source verification

Before editing:

1. Verify Phase 0 and Phase 1 reports exist and their gates passed. If confirmation UI/supervisor did not pass on the phone, do not activate damage mode; complete host code/tests only.
2. Verify the live device boot ID/kernel and current service state.
3. Hash the exact installed legacy presenter, matching service/config, and Phase 0 fallback archive. If any differ, refresh the backup without changing active files.
4. Confirm only one process owns `/dev/fb0`, confirm the expected owner lock and animation-handoff protocol, and check that rollback starts the exact fallback.
5. Inspect all current code before patching. In the supplied archive the canonical A67 file is `tools/s10plus/a67/nuxel-wl-fb.c`; verify the live branch still uses it.
6. Confirm the checked-in XML at `tools/s10plus/a29/wlr-screencopy-unstable-v1.xml` really declares `zwlr_screencopy_manager_v1` version 3, `copy_with_damage` since version 2 and the `damage` event since version 2.
7. Search all call sites and generated protocol bindings. Do not modify generated files manually if the project has a protocol generation step.

If Phase 1 is incomplete, do not bypass the confirmation agreement. Stop activation, complete the missing safe prerequisite or report the blocker.

# 2. Current implementation facts to preserve

The current A67 presenter already has:

- cached reusable `wl_shm` buffer(s);
- a retained previous source frame;
- full-row `memcmp`-based change detection in `frame_damage_rows()`;
- dirty vertical row/run tracking and partial-row blitting;
- AArch64 NEON 2× row expansion/conversion;
- correct framebuffer mapping and panel colour/pitch handling;
- required `FBIOPAN_DISPLAY` after each changed frame;
- one owner of `/dev/fb0`;
- display-off capture stop and control-channel wake;
- full-frame repaint on initialization and wake/forced repaint;
- adaptive active/idle pacing controlled by `NUXEL_TARGET_FPS`, with a service override of 20 FPS and idle 8/3/1 FPS steps.

Do not rewrite or remove these working elements. The latest Nov 6–7 audit samples showed capture about 5–7 ms, compare about 0–3 ms, blit about 1–4 ms and pan about 9–10 ms. These figures justify measuring whether avoiding comparison helps; they do not prove a guaranteed speedup.

The identified inefficiency is specific: the current `frame_damage()` callback discards its x/y/width/height arguments; the active loop calls `zwlr_screencopy_frame_v1_copy()`; the presenter then scans all source rows against `prev_src`. The protocol supports damage-triggered copy and damage events, but the current presenter does not consume them.

# 3. Exact Phase 2 behaviour

Implement two independent capture modes:

- `legacy-full-copy`: current `capture_output()` + ordinary `copy()` + full-row compare/dirty-run logic. This must remain available and be the default.
- `neo-copy-with-damage`: use `copy_with_damage()` after the required initial full baseline, collect the union of damage events until the corresponding ready event, validate rectangles and use them to drive damage/blit decisions.

Expose a clear explicit mode switch (for example `NUXEL_NEO_DAMAGE=1` or a config/profile option) only after checking repository conventions. Default must remain unset/off and select legacy mode. The selected mode and run ID must be visible in logs/status.

Do not claim the protocol makes the compositor copy fewer bytes. `copy_with_damage` is a damage-triggered request and supplies damage metadata; the underlying compositor may still populate a full SHM frame. Phase 2's first guaranteed potential saving is avoiding the presenter's redundant full-row comparison and limiting subsequent CPU framebuffer writes to changed regions. Measure compositor copy cost separately if it is observable.

# 4. Protocol implementation

## 4.1 Bind and capability validation

- Bind the screencopy manager at the highest safe version supported by the compositor and generated client binding, capped by the client interface version. Current source/audit indicates version 3; verify live.
- Use `copy_with_damage` only when the negotiated manager/frame interface version is at least 2 and generated bindings expose the method/event.
- If the runtime version is below 2, the event is missing, the compositor rejects the request, or the protocol is inconsistent, fall back to legacy full-copy immediately and record a precise reason.
- Do not change the compositor's advertised globals or protocol version as a shortcut.

## 4.2 Frame state and callback correctness

Build an explicit per-capture state object rather than loosely shared global flags where practical. It should include:

- frame object and generation;
- pending SHM buffer and generation;
- `buffer` event seen / `buffer_done` state if required by the protocol/client binding;
- requested mode (`copy` or `copy_with_damage`);
- ready/failed/cancelled state;
- validated damage rectangles and count;
- first-frame/full-repaint marker;
- screen/display generation at request time;
- capture start/ready timestamps;
- protocol version and fallback reason.

The callback for the protocol `damage` event must record each rectangle. It may be called multiple times before `ready`; the union of all reported regions is the damage for the corresponding copy request. Never assume one event per frame.

Validate each rectangle with overflow-safe arithmetic:
- width and height must be nonzero to contribute;
- x/y and right/bottom must be within the correct output/buffer coordinate space after applying the verified protocol semantics;
- guard `x + width`, `y + height`, scaling and stride multiplication against integer overflow;
- clip only when the protocol permits clipping and record the clip; otherwise mark the capture invalid and request a full repaint/fallback.

Do not assume damage coordinates are physical pixels or logical pixels. Inspect the protocol documentation and the pinned wlroots implementation used by this repository, verify the actual output transform/scale semantics, and add tests for the measured configuration. Record the coordinate-space contract in code comments and docs.

## 4.3 Initial frame and subsequent capture

The first frame after process start, manager recreation, output resize, pixel-format/stride change, rotation/transform change, screen wake, buffer reallocation, recovery, invalid damage history or any unknown state must use ordinary full `copy()` and full repaint. Only after a valid baseline frame is complete may the client issue `copy_with_damage()`.

For later frames:
- issue `capture_output()` and wait for the buffer metadata as current code does;
- attach the listener;
- request `copy_with_damage()` with the cached valid SHM buffer;
- collect zero or more `damage` events;
- process `ready` only after damage events for that frame have been delivered;
- on `failed`, destroy the frame and retry through legacy `copy()` after a safe reset;
- on screen-off/control cancellation, destroy/cancel pending frame safely and return to the screen-off wait without retaining an unresolved object.

The `copy_with_damage` request may wait until new damage occurs. Do not design the event loop as if it always returns quickly.

# 5. Event loop and screen-off/wake correctness

This is a critical part of the implementation. The existing code dispatches Wayland events in a loop and separately pumps the display control FIFO in other places. A damage-waiting capture must not make screen-off or wake commands unresponsive.

Implement a correct Wayland event-loop integration that watches both:
- the Wayland display FD;
- the existing control FIFO/socket FD used for display on/off and status requests.

Use the correct libwayland read protocol (`prepare_read`, flush, poll, `read_events` or `cancel_read`, then dispatch pending events) or a repository-supported event loop integration. Avoid calling `wl_display_dispatch` in a way that blocks forever while ignoring the control FD. Handle `EINTR`, `POLLHUP`, `POLLERR`, lost display socket and control-channel closure.

On display-off:
1. Mark display generation/off state.
2. Cancel/destroy pending screencopy frame and clear its pending callback/buffer references safely.
3. Do not issue another capture/copy or panel commit while off.
4. Keep the established panel owner and backlight/blanking protocol intact.
5. Wait on the control FD and Wayland FD as necessary without CPU polling.

On wake:
1. Recreate/reinitialize capture state if protocol lifecycle requires it.
2. Force a full-frame ordinary copy (not damage-only) to rebuild a trustworthy baseline.
3. Force full panel repaint; do not use partial rectangles for the first post-wake frame.
4. Keep the panel dark until the existing verified post-wake commit condition is met.
5. Preserve the current brightness/backlight ordering and two-phase wake logic.

Test control requests while a `copy_with_damage` request is pending and while the display is static. A pending damage request must never prevent the screen from turning off.

# 6. Damage storage and coalescing

Use a bounded rectangle/region representation. Do not allocate unbounded lists from an untrusted compositor event stream.

- Define a maximum number of raw rectangles per frame.
- When the limit is reached, merge into a bounding box or fall back to full-frame damage; correctness wins over micro-optimization.
- Union all damage events that arrive before ready.
- Clip to the verified source output bounds.
- Coalesce adjacent/overlapping rectangles only where it cannot omit pixels.
- Maintain an area/count threshold above which a full repaint is simpler and likely cheaper.
- Track both raw rectangle count and coalesced rectangle count, total damaged pixels/area, and whether the frame fell back to full.
- Keep full-frame damage as the universal recovery path.

Initially it is acceptable to translate damage rectangles into vertical row spans and retain the existing partial-row blitter. Do not attempt horizontal sub-rectangle framebuffer writes in the same first patch unless the current blit primitives and tests already support them safely. If horizontal writes are implemented, make them a separately switchable subfeature with stride/offset/2× scaling proof.

# 7. Integrate the damage path with existing source-frame state

The current `prev_src`, hash/damage baseline and `frame_damage_rows()` logic must not become stale or disagree with protocol damage.

Design a clear source-frame update contract:

- For the first/full frame, copy/update the entire `prev_src` baseline and set full dirty region.
- For a damage frame, trust protocol damage only after its history is valid. Update the regions of the baseline that correspond to the new capture and mark those regions dirty.
- If the SHM capture buffer contains a complete current frame, pixels outside protocol damage may still be read for shadow validation, but must not be unnecessarily blitted.
- If the captured buffer's unchanged regions are not guaranteed to contain valid prior pixels under the actual protocol implementation, do not read them as a full frame; instead maintain the correct prior source buffer and update only proven copied regions. Verify this against the pinned compositor source and frame hashes.
- Never use stale `prev_src` as proof that a new frame is unchanged after output resize, format change, wake, transform or dropped/failed capture.
- On any uncertainty, request ordinary full-copy and reset the baseline.

Do not use only a global bounding rectangle if it creates an unexpectedly huge copy for separated changes. Preserve row-run coalescing or add a bounded region-set implementation with a clear fallback threshold.

# 8. Full-frame shadow validator

Before using damage data to skip comparisons/writes, implement a debug/validation mode that checks it against a reference full-frame result.

The shadow validator should:
- compare the complete captured frame with the maintained baseline when the buffer semantics allow it;
- independently derive actual changed regions using a full-row compare or reference pixel diff;
- compare actual changed pixels/rows with the union of reported protocol damage;
- log missing-damage and over-reported-damage counts/areas;
- identify the frame ID, transform, dimensions, format, stride, protocol version and state transitions for every mismatch;
- force a full repaint and switch that run to legacy mode on a missing-damage mismatch.

A mismatch is a correctness failure, not a performance tradeoff. No stale pixels may remain on the AMOLED. If the protocol's damage definition is at a different coordinate granularity than raw pixel differences, document the correct conservative comparison rule.

Shadow mode may be CPU-expensive; run it during validation only. Record its overhead separately and disable it only after enough physical evidence. Do not claim a CPU gain from a benchmark where shadow comparison is still active.

# 9. Preserve the existing presenter fast paths

The following must remain functionally identical and covered by regression tests:

- cached SHM buffer and mapping reuse;
- existing NEON 2× row scaling/conversion;
- framebuffer geometry/pitch/format handling;
- dirty-row/run blitting;
- `FBIOPAN_DISPLAY` after each changed frame;
- no pan/CPU blit for a genuinely unchanged frame;
- active frame pacing and idle 8/3/1 FPS backoff;
- stop capture while display is off;
- wake-time full repaint and delayed backlight release;
- single `/dev/fb0` owner and animation/painter stop receipts;
- status/control FIFO requests;
- error counters and the existing `FRAMES_OK` log contract.

Do not change the service's default `NUXEL_TARGET_FPS=20` in Phase 2. Do not add DMA-BUF, DRM, overlay plane, renderer or kernel changes. Keep this patch narrow enough to isolate the damage protocol effect.

# 10. Canary packaging and permanent fallback

The known-good legacy backend must remain a separate, startable artifact and must not be overwritten.

1. Build the candidate presenter to a separate path/name and include a distinct build ID/hash. Keep the legacy executable, service config and release copy unchanged.
2. Use the existing systemd graph and owner protocol to design the activation transaction. Inspect all relevant units, drop-ins, dependencies, `Restart=`, `StartLimit*`, `Conflicts=`, painter handoff, owner locks and boot-animation receipts. Do not create competing owners.
3. Candidate service/mode must be opt-in. Legacy is the boot/default path.
4. Before candidate activation, arm the independent rollback supervisor and verify that legacy can be restarted. Candidate crash or confirmation timeout must stop candidate and restore legacy automatically.
5. Do not make the legacy service depend on the candidate or NEO libraries.
6. A failed candidate must not restart-loop against the owner lock or continuously interrupt the fallback. Use bounded candidate restart and a clear rollback state.
7. After rollback, verify the legacy service is active, owns `/dev/fb0`, commits a fresh full frame and the panel is visible. A systemd `active` status alone is insufficient.
8. Record host/device hashes and exact activation/rollback commands.

# 11. Required physical confirmation and retry loop

Every damage-mode physical activation requires the Phase 1 `neo-confirm` mechanism.

Before the candidate is activated:
- verify legacy fallback artifact/hash;
- verify only one current owner;
- arm rollback supervisor outside the candidate process;
- create a unique test-run ID;
- verify the YES/NO notification handler and 30-second timer are ready;
- verify candidate preflight tests and protocol version support.

After the candidate has produced a first successful output frame, display:

> **NEO graphics test: Can you see the Nuxel display working correctly?**
>
> **YES** / **NO**

The owner must physically press YES within 30 seconds. The prompt is valid only for that candidate run ID. An SSH response or log line is not accepted.

- YES within 30 seconds: mark the visual check passed and continue the canary test matrix.
- NO: immediately fail the attempt, rollback, diagnose, fix and repeat with a new run ID.
- No YES within 30 seconds: same failure/rollback/retry behaviour.
- Prompt not rendered, buttons not actionable, countdown not functioning, candidate crash or supervisor unavailable: failure/rollback.
- The agent must continue the fix/retry cycle after failures as long as a safe, materially changed candidate can be produced. Do not relaunch the same failing build unchanged. If fallback cannot be proven or another attempt risks the only working display, leave legacy active and stop for safety with an exact blocker report.

After YES, continue automatic tests. The owner should not have to press YES again for every frame; however, any new binary/config/run or any new activation after rollback needs a new question. A later display loss triggers rollback even after earlier YES.

# 12. Phase 2 test matrix

## 12.1 Host/unit tests

- protocol interface version gates (v1 fallback, v2/v3 damage path);
- multiple damage events before ready;
- zero damage/no immediate-ready semantics;
- malformed/overflow/out-of-bounds rectangles;
- overlapping/adjacent/separated rectangles;
- max-region overflow → safe full repaint;
- first frame and manager recreation;
- resolution/stride/format changes;
- output scale/transform/rotation coordinate conversion;
- cursor movement, status icon updates and small animated regions;
- frame failed event and lost Wayland connection;
- pending damage request interrupted by screen-off;
- wake causes full-copy/full-blit before backlight;
- control FIFO and Wayland FD simultaneous readiness;
- `EINTR`, HUP and poll errors;
- damage mismatch in shadow mode forces legacy fallback;
- buffer lifecycle/no stale references/double destruction;
- legacy mode remains identical.

Use a fake Wayland server or test harness if repository tooling supports it. Do not use a mocked server as proof of physical compositor correctness.

## 12.2 Physical smoke test

After the visual YES:

1. Static Home, clock/status changes.
2. Move cursor/pointer if applicable.
3. App drawer open/close.
4. Scroll long page vertically and horizontally.
5. Open/close Quick Settings and notification surface.
6. Launch/close several apps.
7. Browser/PWA animation and scroll.
8. Fullscreen video only if already stable.
9. Lock/unlock and lockscreen indicators.
10. Screen-off during a pending `copy_with_damage` request; wake and confirm fresh lockscreen with no stale desktop bands.
11. Rotate/resize if current phone workflow supports it.
12. Repeat wake/sleep 10 times.
13. Run a 10-minute interactive session; then 30-minute sustained test if all earlier gates pass.

For each case record panel appearance confirmation, frames/captures/failures, damage rectangle count/area, capture/compare/blit/pan timings, skipped presents, CPU/RSS, temperature/current and rollback events.

## 12.3 Correctness gates

- Zero missing pixels/stale regions in shadow validation.
- Zero `FBIOPAN_DISPLAY` failures attributable to candidate.
- Zero lost input/touch regression.
- Zero screen-off capture busy-loop.
- Wake full repaint and backlight order unchanged.
- No black screen, tearing, stale desktop band, incorrect orientation or colour changes.
- No double panel owner or fallback race.
- `copy_with_damage` unsupported/failed must switch to legacy full-copy without service restart where possible.

## 12.4 Performance gates

Keep FPS at 20 for this comparison to isolate damage protocol effect. Compare at least five runs per workload with similar temperature/brightness/start state.

Report:
- active capture, comparison, blit and pan p50/p95/p99 where samples permit;
- total presenter CPU and CPU time per presented frame;
- changed area and comparison bytes read;
- SHM capture bytes if known (do not assume `copy_with_damage` reduces it);
- bytes written to fb0;
- frame interval and input-to-visible latency proxies;
- energy/temperature trend;
- ring buffer and shadow validation overhead separately.

Do not claim a performance win if only the `compare_avg_ms` drops while total CPU/power or frame latency does not. Do not aggregate overlapping percentages. The intended win is less redundant comparison and smaller CPU framebuffer writes for small damage, without increased wake/interaction latency.

# 13. Rollback and recovery drills

Run controlled failure tests on a non-production test mode or during a canary where the supervisor can restore legacy:

- candidate exits before first frame;
- candidate produces no ready frame;
- notification cannot be shown;
- owner presses NO;
- 30-second timeout;
- simulated damage protocol failure;
- missing damage detected by shadow validator;
- candidate loses Wayland connection;
- supervisor restart during canary;
- fallback restart.

Never inject a failure that intentionally removes all panel control unless the remote recovery route and fallback are confirmed. For each drill verify the legacy binary hash, service state, owner lock and fresh panel frame.

# 14. Phase 2 deliverables

```text
graphics/neo/src/damage/...
graphics/neo/src/backends/fbdev/...
tools/s10plus/a67/                       # narrow patch or adapter; keep legacy source/history
services/nuxel-neo/                      # only if a separate canary unit is required
 tests/nexus-neo/phase-2/...
docs/nexus-neo/phase-2/
  DAMAGE-PROTOCOL.md
  IMPLEMENTATION.md
  COORDINATE-SPACE.md
  SHADOW-VALIDATION.md
  CANARY-DEPLOYMENT.md
  CONFIRMATION-LOG.md
  PERFORMANCE-COMPARISON.md
  ROLLBACK-DRILL.md
  TEST-RESULTS.md
  evidence/<timestamp>/...
```

Use actual repository conventions and avoid a parallel duplicate copy of source if the canary can be built from a separate target/feature without losing provenance. Include hashes for the unchanged legacy artifact and separate candidate.

# 15. Phase 2 completion criteria

Phase 2 passes only if:

- `legacy-full-copy` is unchanged, available and remains default;
- `neo-copy-with-damage` is separately selectable and off by default until accepted;
- protocol version/callback/state semantics are correct;
- damage rectangles are validated and transformed in a documented coordinate space;
- event loop remains responsive to screen-off/wake/control while waiting for damage;
- first/wake/recovery frames are full copies and full repaints;
- full-frame shadow validation detects no missing damage across the physical matrix;
- the on-device confirmation UI works with an explicit YES within 30 seconds for the canary;
- NO/timeout/crash/display failure automatically restores legacy;
- all retry attempts are materially changed and logged;
- one panel owner is guaranteed;
- the existing NEON, SHM reuse, partial-row blit, FBIOPAN, idle and wake behaviours remain correct;
- performance comparison is reproducible and honestly reports gains or no gain;
- no DMA-BUF, KMS, direct scanout, GPU renderer or kernel scope was added.

A Phase 2 candidate may remain experimental even when tests pass. Do not make it the default unless the owner has confirmed the canary visually, every automated/physical acceptance gate passes, rollback is proven and a separate explicit production-promotion decision is documented.

# 16. Final engineering report

Include:

1. root cause and design of the damage path;
2. exact source files, generated protocol bindings and tests changed;
3. protocol version observed on the phone;
4. full-copy vs damage mode behaviour and fallback reasons;
5. shadow validation results and mismatch evidence;
6. event-loop/screen-off/wake correctness;
7. confirmation run IDs, timestamps and outcomes (never fabricate YES);
8. candidate/legacy hashes and owner/service state;
9. physical workload results, p50/p95/p99 and thermal/power observations;
10. test counts and skipped/blocked tests;
11. exact rollback commands and result;
12. go/no-go recommendation for later NEO buffer/LayerTree phases.

**Do not implement DMA-BUF presentation, DRM/KMS, direct scanout, hardware planes, WebKit WSI or new kernel support in Phase 2. Keep the existing graphics engine as a permanent fallback.**

# IMPLEMENTATION PROMPT — Component R06: PRIORITY ZERO — Get the touchscreen fully working

> **This file is a prompt for a FUTURE implementation session.** It describes what to build, where it lives in this repository, how to test it locally, and how to verify it on hardware. Do **not** treat "must implement" as something you are doing right now if you are reading this during authoring — its only job is to be executed by a future agent working on the branch `nuxel/r06-touchscreen-fully-working`.
>
> Target platform: **Samsung Galaxy S10+ SM-G975F / Exynos 9820**, Nuxel Fedora ARM64 (Linux phone OS) with **no Android framework dependencies**. A MacBook host may build/test; the live phone may or may not be connected at execution time.

---

## 0. Mission statement

Implement **only** component R06: make the S10+ touchscreen *fully* working end to end — from the physical `sec_ts` digitizer all the way through to WebKitGTK DOM events that drive the Nuxel Home launcher — including correct pointer capture, long-press, drag, multitouch and coordinate alignment, correct behaviour after rotation and overlay transitions, plus on-device diagnostics and a safe fallback for unsupported hardware.

Constrain yourself to R06. Preserve everything already working (launcher navigation, haptics, custom icon assets, Home layouts, USB recovery). Do **not** implement other screenshot items in the same branch. If a change touches an unrelated subsystem, keep it minimal and clearly attributable to touch.

### Branch context (already landed; verify before editing)

The checked-out branch is `nuxel/r06-touchscreen-fully-working`. Touch support has already been *substantially* implemented across earlier commits on this line (e.g. the "Operation Touchable" work and the v0.6.0-beta merge that ships the S10+ image as-is). **Your job is to audit what exists, repair/gap-fill/verify the remainder, not to reinvent the pipeline from scratch.** Reuse actual Nuxel architecture; do not create parallel or fake substitutes.

**Verified facts about this repo (authoring-time snapshot — re-check with `git status` / `grep` before editing):**

- The touch event chain is: `sec_ts` i2c driver (`4-0048`) → IRQ → evdev node `/dev/input/event2` (`INPUT_PROP_DIRECT`, `ABS_MT_POSITION_X/Y`, contact-slot capacity) → **libinput path shim** (`LD_PRELOAD=/usr/lib/nuxel/libnuxel-libinput-path.so`, authoritative source `tools/s10plus/a33/nuxel-libinput-path.c`) → `phoc` headless compositor (`WLR_BACKENDS=headless,libinput`, `LIBSEAT_BACKEND=noop`, started by `services/nuxel-session/systemd/nuxel-wayland.service`, seat brokered by `seatd.service`) → `wl_touch` (wlroots 0.19) → WebKitGTK Nx session (`XDG_SESSION_TYPE=wayland`) → **Nuxel Home PWA** in `pwa/nuxel-home/`.
- The multitouch FSM lives in **`tools/s10plus/a33/nuxel-button-manager.c`**, which parses raw evdev `struct input_event` via the MT parser in **`tools/s10plus/a33/nuxel-mt.h`** (`NUXEL_MT_PHASE_DOWN/MOVE/UP/CANCEL`). The A34 tree has a separate copy (`tools/s10plus/a34/nuxel-button-manager.c`) that must stay consistent.
- Coordinate mapping (verified by `docs/s10plus-autonomous-boot-repair/TOUCHDOWN/TOUCH-COORDINATE-MAPPING.md`): raw `0..4095` → libinput normalises → phoc output **720×1520 phys** ÷ scale 2 → WebKit CSS viewport **360×760 CSS px, devicePixelRatio = 2**. So:
  ```
  logical_x = raw_x * 720 / 4095 / 2
  logical_y = raw_y * 1520 / 4095 / 2
  ```
  No rotation/offset at the input layer; safe-area padding is a launcher-layout concern (`pwa/nuxel-home/js/safe-zones.js`).
- The **launcher** (`pwa/nuxel-home/js/launcher.js`) already uses `PointerEvents` (pointerdown/move/up/cancel) plus `touchstart/touchend`, and implements tap-to-launch + drag-and-drop reorder with a long-press-to-start-drag. So much of "fully working" is about making that path robust, not writing a new one.

**Things the future agent MUST inspect before assuming (do not trust this list as current):**

- Which button-manager source tree the running image actually ships (`a31` vs `a33` vs `a34`) and which `.service`/`.sh` deploys it — check `services/nuxel-session/systemd/`, `build-a33-boot.sh`, `build-libinput-shim.sh`, and the deployed copy under `/usr/lib/nuxel/` / `/usr/sbin/phoc` env on-device.
- The exact udev rules that expose `/dev/input/eventN` to seatd, and whether the udev daemon is masked (the service comments indicate it is, on 4.14).
- Whether phoc/wlroots version matches the assumptions in `nuxel-libinput-path.c` (wlroots 0.19 interposition of `backend/libinput/backend.c`).

---

## 1. Trace physical touch events (component contract item 1)

Confirm, layer by layer, that a real finger contact at `sec_ts` reaches the Nuxel Home DOM with correct coordinates and phase. Use the **existing** diagnostic tooling before writing new code:

- **Tool:** `tools/s10plus/a33/nuxel-touch-trace.py` (7-layer pipeline trace) + harness `tools/s10plus/a33/nuxel-touch-capture.sh` + DOM probe `tools/s10plus/a33/touch-probe.html`.
- **What each layer must report** (`LAYER=<n> NAME=... STATE=ok|drop|blocked EVIDENCE=... DETAIL=`):
  1. `sec_ts` driver binding — kernel registered `sec_touchscreen`, i2c client `4-0048` bound (`dmesg`/ram-console, `/sys/bus/i2c/devices/4-0048`).
  2. IRQ delivery — the `sec_ts` line in `/proc/interrupts` increased across two snapshots ≥2 s apart while exercised.
  3. evdev node production — a **capability-selected** node (`INPUT_PROP_DIRECT` + `ABS_MT_POSITION_X/Y`, non-degenerate range, contact-slot capacity) that decodes to a point; identity from both sysfs and evdev ioctls (`EVIOCGID/EVIOCGNAME/EVIOCGPROP/EVIOCGBIT/EVIOCGABS`).
  4. libinput acceptance — shim handed the node to libinput and it returned a device; `/run/nuxel-libinput-path.state` lines with `PATH_ADD … accepted=1`.
  5. phoc input fds — compositor holds the node open (`/proc/<nuxel-wayland MainPID>/fd` under `/dev/input/`).
  6. Wayland seat / focus — `wl_touch` produced for the seat (bounded `WAYLAND_DEBUG`/journal or a launcher DOM line that could only come from a Wayland touch).
  7. WebKitGTK DOM — `touchstart/touchmove/touchend` reached the document **with coordinates** (`/run/nuxel-touch-dom.log` or `NUXEL_INPUT` lines in `/run/nuxel-home.state`).

**Deliverable:** a completed trace for at least one tap, drag and two-finger gesture showing `VERDICT=PIPELINE_DELIVERED`. If any layer is `drop`, that layer stops the pipeline — fix it; if `blocked`, record why (e.g. no phone) rather than reporting `ok`.

---

## 2. Repair pointer capture, long-press, drag, multitouch and coordinate alignment (item 2)

### 2a. Multitouch FSM correctness (`nuxel-button-manager.c` / `nuxel-mt.h`)
- Confirm the MT parser (`nuxel-mt.h`, `NUXEL_MT_PHASE_*`) correctly handles multi-contact slots, tracking IDs and cancels; confirm the daemon emits DOWN/MOVE/UP/CANCEL **only** on `SYN_REPORT` (not feed-on-TRACKING_ID — this was a real A34 defect fixed by latching pending down/up on `ABS_MT_TRACKING_ID`). Verify the A33 source is correct and that any shipped copy (`a31`/`a33`/`a34`) matches.
- **Long-press:** ensure a sustained contact is classified as long-press (used by e.g. back-gesture / context menus) and does not misfire on tap-vs-drag discrimination. The launcher's `longPressTimer` + drag threshold must agree with the FSM's classification window.
- **Drag & pointer capture:** verify drag-and-drop reorder in the launcher keeps a stable pointer/button id across `pointermove`, cancels correctly on `pointercancel`, and does not bleed into neighbouring tiles; ensure no stray double-activation from both `pointerup` and `click`.

### 2b. Coordinate alignment (item: "coordinate alignment")
- The mapper is `logical = raw * output / 4095 / scale`. Re-verify against the **current** phoc output geometry in `phoc-phone.ini` (`720×1520`, scale 2 → 360×760 CSS px, dpr=2). If the shipped ini or resolution changed, update the mapper and the trace's expected coordinate math together.
- Add a **corner test** (top-left / centre / bottom-right) to rule out nonlinear panel/controller calibration — this was explicitly still requested from owner hardware; do not claim it passes without live data.

### 2c. Rotation & overlay transitions (item 3)
- After screen rotation or an overlay change, `wl_touch` coordinates and the launcher's CSS viewport must stay consistent. Verify with `safe-zones.js` (rotation/safe-area handling) and re-run the trace at multiple orientations. Confirm no coordinate flip/inversion appears after rotation.

### 2d. Safe fallback for unsupported hardware (item 4 + acceptance gate)
- If the digitizer node is absent (charger-mode/LPM boot where `sec_ts` never binds, or a device without a direct multitouch panel), the pipeline must degrade **gracefully and visibly**, not crash or restart-loop. The `WLR_LIBINPUT_NO_DEVICES=1` guard already prevents phoc from restarting on zero devices — ensure touch diagnostics record "zero devices" state (via `/run/nuxel-libinput-path.state`) rather than silently passing.

---

## 3. On-device diagnostics and safe fallback (item 4)

- Keep/extend the existing `nuxel-touch-trace.py` / `nuxel-touch-capture.sh` as the primary on-device diagnostic (they already print machine-readable layer verdicts with bounded wall-clock, decoded-event and byte caps so the live console never hangs).
- The **synthetic** injector `tools/s10plus/a34/nuxel-uinput-touch-probe.py` (`--tap/--swipe`) proves the *software* path (libinput→phoc→wl_touch→WebKit→Home) when no finger is available. It prints `SYNTHETIC=1`; it **must never** be promoted to physical acceptance — treat it as evidence of the software stack, not proof of the panel.
- Provide a single `nuxel touch-diag` (or reuse an existing `nuxelctl` subcommand if one exists) that runs the trace and prints a compact PASS/FAIL/BLOCKED per layer plus the `VERDICT=` line, suitable for owner use.

---

## 4. Tests — real behaviour + failure paths, not static references (acceptance gate)

Use the **existing** offline test harnesses first; they run on a workstation with **no phone, no libinput, no /dev/input and no root**:

- `tools/s10plus/a33/tests/run-touch-tests.sh` (whole offline touch set; `--quick` skips the shim build) — this is the gate for the "Touchscreen & Reliable Interactive Input" build group.
- `tools/s10plus/a34/tests/test-touch-syn-translation.py` — pins the down/up-on-SYN_REPORT fix by structural inspection of `nuxel-button-manager.c`.
- `test-touch-mt.c` + MT-parser replay (builds with aarch64 Linux UAPI; macOS hosts may set `NUXEL_LINUX_UAPI_INCLUDE`, never hard-code a toolchain).
- `test-libinput-path-fixture.py`, `test-libinput-parity.py`, `test-libinput-shim-invocation.py`, `test-no-eventn-literal.py` — shim behaviour.
- `test-touch-keyboard.js`, `test-qs-gesture.js` (a34) — DOM/launcher touch + quick-settings gesture paths.

**Author new tests that exercise real behaviour and failure paths**, e.g.:
- MT parser fed a crafted multi-contact slot sequence (two simultaneous contacts, one cancel, resync) asserts correct phase sequence and tracking-id handling — not just "symbol present".
- Coordinate mapper unit test covering the full `raw→logical` transform at several orientations/scales, including an assertion that a corner tap maps near the expected corner within tolerance.
- Launcher pointer/drag test (headless JSDOM or a minimal EventTarget harness) asserting: single tap launches; long-press starts drag; `pointercancel` cancels without double-launch; two contacts do not both activate tiles. Keep it host-runnable and deterministic — no real hardware required.
- Failure-path trace case: simulate layer 4 (`libinput accepted=0`) and assert the tool reports `PIPELINE_STOPPED_AT_LAYER=4` with exit code `14`, not a false `PASS`.

Prefer extending these over new files; keep every test runnable offline. Never pass off mocks as physical checks.

---

## 5. Build & cross-compilation (AArch64 native code)

- The libinput path shim compiles to `/usr/lib/nuxel/libnuxel-libinput-path.so` via `build-libinput-shim.sh` (sources: `tools/s10plus/a3{1,3}/nuxel-libinput-path.c`). The button-manager is built into the boot image by `build-a33-boot.sh`.
- **AArch64 native code must be cross-built or documented with precise toolchain restrictions.** On a macOS host, build against an installed aarch64 Linux sysroot:
  ```
  aarch64-linux-gnu-gcc -std=gnu11 -O2 -Wall -Wextra \
      -isystem <aarch64-sysroot>/usr/include \
      -c tools/s10plus/a33/nuxel-libinput-path.c -o /tmp/shim.o
  ```
  Do **not** hard-code a Homebrew cellar revision. If no cross toolchain is present, document the exact command and mark the native build BLOCKED/NOT_TESTED rather than faking it. Host-side C tests that only need `linux/input.h` (MT parser) should be gated on header availability with a clear SKIP message.

---

## 6. Honest hardware verification (acceptance gate — do not fabricate)

- The live S10+ **may not be connected** during this task. If it is: capture real trace receipts (`nuxel-touch-capture.sh` output, `/proc/interrupts` deltas, `WAYLAND_DEBUG` windows, DOM logs), then mark each layer `ok` with the evidence path.
- If it is **not** connected (or a capability cannot be exercised without a finger/panel): write a **BLOCKED / NOT_TESTED** evidence report for that specific capability — state exactly what was required and why it could not be obtained — and commit the deliverable source/docs/tests **without claiming a physical pass**. Never claim a hardware test succeeded when it did not.
- Explicitly separate, in every report: (a) offline/host-verified facts (builds, unit tests, structural checks), and (b) live-hardware claims that require the phone.

---

## 7. Required workflow & deliverables

1. **Source audit** of the real files listed above; record existing behaviour and the smallest coherent repair/implementation plan.
2. Implement source / assets / service-config changes + tests needed for R06 only. Preserve working launcher navigation, haptics, custom icon assets, Home layouts and USB recovery.
3. Run the most relevant local tests/build/lint (see §4–5). Cross-build or document toolchain limits precisely; never pass off mocks as physical checks.
4. Write **`docs/component-reports/r06.md`** containing: code paths changed, commands/receipts, PASS/FAIL/BLOCKED/NOT_TESTED per item, actual device deployment status, unresolved issues and safe rollback instructions.
5. **Commit only this component's** code, tests, documentation and report on the checked-out branch. Do not merge into main, switch branches, add secrets, or generate unrelated features. Check `git status` and finish with a clean worktree. The queue runner will push the branch.

---

## 8. Acceptance gates (all must hold)

- Every R06 item in §1–§4 is implemented **or explicitly marked BLOCKED** with concrete evidence (not omitted).
- Tests exercise real behaviour and failure paths, not only static symbol references.
- Device-specific capabilities require live hardware verification; if unavailable, a BLOCKED/NOT_TESTED evidence report is written and deliverables are committed without claiming a physical pass.
- Any dangerous hardware operation (flashing, bootloader/partition write, kernel replacement, unsafe amplifier or LED setting) is **forbidden** during this task.
- If a critical external dependency blocks the feature, produce the smallest safe implementation, a precise blocker report, and stop — do not let manual hardware proof stall unrelated queue work.

---

## 9. Safe rollback (to include in `docs/component-reports/r06.md`)

- Revert to the pre-R06 baseline by restoring the shipped copies of any touched files (`tools/s10plus/a3{1,3}/nuxel-button-manager.c`, `nuxel-libinput-path.c`, the `.so`, `phoc-phone.ini`, launcher JS) from the last known-good commit on this branch.
- The libinput shim is an `LD_PRELOAD` at a fixed path; if it misbehaves, clear that environment entry in `services/nuxel-session/systemd/nuxel-wayland.service` (and its drop-ins) to fall back to stock udev/libinput discovery — the compositor already tolerates zero devices.
- Button-manager gestures are gated on opening a DIRECT+MT touch node; if gesture handling regresses, disabling touch in the FSM falls back cleanly to button-only operation (documented in `nuxel-button-manager.c`).

---

## 10. Scope guardrails

- Stay within component R06. Do not implement other screenshot items from the queue on this branch.
- Reuse existing architecture (`nuxel-touch-trace.py`, shim, MT parser, launcher Pointer Events); do not create parallel/fake substitutes.
- Keep changes minimal and clearly attributable to touch; preserve haptics, icon assets, Home layouts and USB recovery.

*End of prompt for R06.*

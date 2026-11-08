# PWNAGE-46000 — NUXEL ROTATION: MAKE ALL SEVEN MODES PHYSICALLY WORK

**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel, custom Fedora-based ARM64 Linux  
**Primary display path:** Phoc/Wayland headless output → `zwlr_screencopy` → `nuxel-wl-fb` → the single `/dev/fb0` owner  
**Input:** physical touchscreen through the existing seatd/libinput/Phoc path  
**Rotation service/API:** `services/nuxel-orientation/` and Bridge `orientation` RPC  
**Human verification channel:** the Nuxel Notes app, using its existing persistent `nuxel-notes` store  
**Mission:** source repair, real display + touch rotation, continuous auto-orientation, on-device user testing, repeated fix/deploy/test until every supported mode works.

## MISSION

Deeply inspect the current repository and the actual running S10+ before changing anything. Then make screen rotation genuinely work end-to-end. This is not a mode-selector/UI-only task: the screen pixels, logical output geometry, WebKit viewport, native Wayland surfaces, touchscreen coordinates, keyboard, status bar, Home dock, lockscreen and application layouts must all agree after every rotation.

The user will keep the Notes app open and provide physical test feedback by editing one dedicated rotation-test note:

- `yes` or `works` means the requested behavior worked correctly.
- `no` means it failed.
- deleting the waiting marker and leaving the response empty also means failure, once the note save has been observed.

Use that feedback to drive an iterative repair loop. Do not stop after three attempts or after offline tests pass. Apply one safe change, deploy it, ask the user to physically test the exact requested behavior, consume the Notes feedback, diagnose failures, make the next correction and repeat. Continue until all seven modes pass physically, or until a genuine external hardware/kernel/firmware blocker is proved and precisely documented. Never fake a pass.

## THE SEVEN EXACT MODES

Use these exact UI labels and meanings. Existing stable mode IDs should be retained unless a safe migration is required:

| User-facing label | Stable mode key | Allowed effective orientation | Required behavior |
|---|---|---:|---|
| **Auto** | `auto` | `0, 90, 180, 270` | Automatically follow all four natural device poses: portrait, landscape, reverse portrait and reverse landscape. |
| **Auto (PT)** | `auto-portrait` | `0, 180` | Automatically switch between normal portrait and reverse portrait; never enter landscape. |
| **Auto (LS)** | `auto-landscape` | `90, 270` | Automatically switch between normal landscape and reverse landscape; never enter portrait. |
| **Portrait** | `portrait` | `0` | Lock to normal/native portrait regardless of device movement. |
| **Landscape** | `landscape` | `90` | Lock to the selected normal landscape direction regardless of device movement. |
| **RPortrait** | `reverse-portrait` | `180` | Lock to upside-down/reverse portrait regardless of device movement. |
| **RLandscape** | `reverse-landscape` | `270` | Lock to the opposite/reverse landscape direction regardless of device movement. |

The existing policy document already defines these seven stable keys and allowed angle sets. Preserve its canonical hyphenated keys and legacy underscore aliases. The requested change is principally to make the modes truly apply, continuously respond to real sensor readings in auto modes, and use the user's exact visible labels.

## IMPORTANT FINDINGS FROM THE PROVIDED REPOSITORY ARCHIVE

The following were confirmed in the supplied `nuxel-main (10)(1).zip` snapshot. Recheck each against the live handset and current checkout before acting; the archive may not exactly equal the deployed phone.

1. `configs/nuxel/orientation/orientation.json` already defines all seven policies and uses the angle sets above. It also contains a sensor mount matrix and gravity reference marked `unverified`, plus a transform map `0→normal`, `90→270`, `180→180`, `270→90` that is explicitly unverified on hardware.
2. `services/nuxel-orientation/nuxel_orientation/policy.py` already implements the seven-mode policy, hyphenated keys and legacy underscore aliases. The labels currently say “Forced Portrait”, “Auto Portrait”, “Auto Landscape” and “Reverse …”; update labels to the exact user-facing names without breaking stable API keys or existing persisted state.
3. `pwa/nuxel-home/js/qs.js` already has a Rotate tile, a tap shortcut between `auto` and `portrait`, and a long-press menu listing all seven modes. Its labels currently differ from the requested exact labels.
4. `pwa/nuxel-apps/settings/settings.js` already has a seven-mode Settings panel calling the Bridge `orientation` namespace. It currently displays old “Forced …” / “advanced” labels. It displays compositor errors, but must not report a persisted selection as a physically applied rotation.
5. `services/nuxel-bridge/src/bridge.py` has an `OrientationConnector` whose default executable is `/usr/libexec/nuxel/nuxel-orientationd`. Its `set_mode()` currently invokes the daemon with `set <mode>` and does not pass `--apply`.
6. In `services/nuxel-orientation/nuxel-orientationd`, `do_set(..., apply_now=False)` persists the selected mode by default and only attempts a compositor transform when `apply_now=True`. Therefore the current Bridge/UI set path can report a successful mode selection while never asking the display stack to rotate. Repair this contract; do not confuse “saved” with “applied”.
7. `services/nuxel-orientation/nuxel_orientation/apply.py` currently only attempts `wlr-randr`. Its `wlr_randr_available()` uses `subprocess.run(["command", "-v", "wlr-randr"])`; `command` is a shell builtin, not a normal executable. Replace this with a correct non-shell executable lookup such as `shutil.which()`. Fixing that bug alone is not enough: the actual compositor/output must support the transform.
8. The orientation service unit in `services/nuxel-orientation/systemd/nuxel-orientationd.service` is currently `Type=oneshot`, runs only `nuxel-orientationd status`, and exits with `RemainAfterExit=yes`. That does not run a continuous sensor watcher. Auto modes require a real long-running owner/loop or an equivalent event-driven service.
9. **The current S10+ rootfs builder snapshot has no orientation references at all.** `images/s10plus/build-phone-rootfs-inside-fedora.sh` contains no `orientation` string, despite the Bridge expecting `/usr/libexec/nuxel/nuxel-orientationd` and the policy expecting `/etc/nuxel/orientation/orientation.json`. Verify whether a separate deployment path exists; if not, install the daemon/package, Python module, config/schema and systemd unit through the canonical image builder. Add a build test so the helper cannot silently be absent again.
10. The current image builder compiles `tools/s10plus/a34/nuxel-wl-fb.c` as the active `nuxel-wl-fb`, while newer A67 source exists separately in the repository. Do not patch a newer directory and assume it is deployed. Modify the source compiled by the active builder, or deliberately update the builder and all related tests/provenance as one coherent change.
11. The physical S10+ display path is not a normal DRM/KMS output. `nuxel-wl-fb` captures the Phoc/Wayland composite with `zwlr_screencopy_manager_v1` and is the single `/dev/fb0` writer. Its framebuffer/DECON path must remain the only owner. Never add a second framebuffer writer.
12. Earlier repository evidence (A53/A54/A69 docs) says the live compositor used a Phoc headless output (`HEADLESS-1`), while the orientation config and display helper refer to `DSI-1`. Prior evidence also says `wlr-randr`/output transform was unavailable. Resolve the current live output name and capabilities instead of trusting either stale name.
13. Earlier hardware diagnostics found the physical accelerometer (LSM6DSO behind the Samsung/Broadcom SSP sensor hub) enumerated, but the SSP sensor hub was down, `raw_data` was `0,0,0`, IIO had no usable `in_accel_x/y/z_raw` plus scale channels, no working `iio-sensor-proxy` accelerometer source was available, and the BCM4775x sensor-hub firmware/userspace bring-up was missing. This is a serious auto-mode blocker, but re-probe the current device before concluding it remains blocked.
14. `services/nuxel-orientation/nuxel_orientation/sensors.py` currently supports IIO raw accelerometer channels and `iio-sensor-proxy`; its manual source is diagnostic only and must never be treated as an auto-capable real sensor.
15. `configs/nuxel/orientation/orientation.json` has `revert_after_ms: 4000`, which is too short for a human to verify a rotated screen, open/continue Notes and type a response. Implement a deliberate user-confirmation trial window (e.g. 60–90 seconds) with automatic rollback unless the Notes feedback confirms success. Keep the watchdog independent of the UI.
16. Notes stores its list under Bridge storage key `nuxel-notes` with a localStorage fallback. The note objects include `id`, `title`, `body` and `updatedAt`; edits autosave after approximately one second. Use the Bridge-backed store as the agent feedback source. Do not overwrite or delete the user's existing notes.

## EXECUTION ORDER

1. Audit current source, current active build path and live device capabilities. Record the current selected mode and effective angle. Back up the current orientation config/state and display/input configuration.
2. Repair the orientation package/build integration and Bridge command semantics. Make status report requested mode, effective angle, sensor state, actual output backend, actual touch calibration and whether the physical transform is applied.
3. Make the four **fixed/manual** modes work first without requiring an accelerometer. Implement a real compositor/output transform or a coordinated presenter + logical-output + input transform. CSS-only rotation is forbidden.
4. Add a safe apply/confirm/rollback transaction. Keep Notes visible as the test surface. If the user does not confirm `yes`/`works`, or enters `no`, revert to the last-known-good orientation automatically.
5. Physically test Portrait, Landscape, RPortrait and RLandscape individually, including screen geometry, touch corners, keyboard, status bar, dock, app window and Notes editing.
6. Investigate the real sensor path. If a verified gravity source exists, calibrate its mount matrix and gravity reference on the phone. If the SSP firmware/userspace blocker remains, investigate legitimate available alternatives and report the exact missing component; never fabricate sensor values.
7. Implement the continuous auto-mode watcher. Validate Auto, Auto (PT) and Auto (LS), including allowed and forbidden poses, hysteresis, flat-phone behavior and mode switching.
8. Use the Notes-based owner feedback loop for every physical test. On failure collect current status/logs, diagnose, patch, run automated tests, deploy a minimal delta and repeat. Do not impose an arbitrary three-attempt limit.
9. Run regression tests and clean ARM64 image/package checks; deploy through the existing configured Wi-Fi SSH path when available; record a full evidence and rollback report.

## HUMAN TEST LOOP — REQUIRED

Create a dedicated Notes entry named **PWNAGE-46000 Rotation Test Feedback**. Preserve every existing note. Use a unique run ID and include one response line for the current challenge:

`ANSWER: WAITING`

Tell the user to leave the Notes app open on this note. For each test, clearly state the exact requested mode, physical handset movement, what should rotate, what must remain fixed and what needs to be tapped/typed. The user replaces `WAITING` with `yes` or `works` if everything passes; enters `no` if anything fails; or deletes the marker/leaves the answer empty if it fails. The Notes app autosaves; read the current note via Bridge storage key `nuxel-notes` and use its `updatedAt` to distinguish an intentional empty response from no response yet.

Never count a stale `yes` from the previous trial. Before each new challenge, re-arm the response line to `WAITING` and wait until the app has saved that baseline. If the active editor cannot safely accept a programmatic re-arm, ask the user to set the line to `WAITING` before starting the next challenge. Do not externally rewrite a note while the user has unsaved editor changes. Do not modify unrelated notes.

Each candidate transform must have a 60–90 second independent rollback watchdog. `yes`/`works` received during the current challenge commits the transform as last-good. `no`, an intentionally blank answer saved after the challenge starts, a display/input safety failure, or timeout causes rollback. The user must never be left with an unusable screen because an agent process or SSH session disappeared.

When a test fails, do not simply ask again. Record the exact mode/pose, current effective orientation, compositor transform, sensor reading/provenance, touch test result and error logs. Determine whether the failure is sensor classification, angle-to-transform mapping, output backend, framebuffer rotation, logical dimensions, touch calibration, WebKit viewport, layer-shell dock or UI state. Fix the responsible layer and re-run local automated tests before asking for another physical test.

## SAFETY

- Preserve the existing single `/dev/fb0` owner (`nuxel-wl-fb`). No second framebuffer writer, raw framebuffer helper or display daemon.
- Do not flash a kernel, enter bootloader/Recovery/Download Mode, write partitions, use `dd` to block devices or force reboot.
- Do not rotate pixels without matching logical dimensions and touch mapping. A rotated screenshot is not a working rotated phone.
- Do not use the `manual` test sensor as if it were a physical accelerometer.
- Never ship guessed mount matrices or transform mappings as verified. Calibrate by physical movement.
- If the display becomes blank, touch stops matching, or Notes cannot be edited, automatic rollback must restore the previous known-good orientation.
- Do not guess SSH addresses or credentials. Use the already configured target only; otherwise complete repository work and provide exact deployment commands.
- Preserve Notes data, app data, Wi-Fi and SSH access. Avoid rebooting unless necessary and explicitly safe.

## DEFINITION OF DONE

- All seven modes appear with exactly the requested labels and behave according to their allowed orientation sets.
- Fixed modes work without a sensor and stay fixed even when the handset is rotated.
- Auto modes follow real physical gravity readings, respect their allowed sets and never enter forbidden orientations.
- Display geometry, touch coordinates, Notes editor, keyboard, Home, lockscreen, status bar, native dock, dialogs and app content remain usable in all four effective orientations.
- Selecting a mode applies it in the actual active S10+ stack; the UI never confuses “saved” with “physically applied”.
- The orientation service/config/helper is included in a clean image and starts correctly at boot; auto monitoring is actually continuous.
- All owner tests receive `yes`/`works` confirmation through the dedicated Notes feedback note. A blank or `no` is a failure, not a silent pass.
- The 60–90 second rollback guard is tested and proven.
- Every local test passes; live device evidence, current blockers, deployment hashes and rollback steps are recorded.

**Do the real implementation and stay in the fix → deploy → ask → read Notes feedback → diagnose → fix loop until the physical result works. Do not stop at a menu, a persisted enum, a simulated test or a green offline suite.**

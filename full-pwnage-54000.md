# FULL PWNAGE-54000 — Nuxel Orientation: The Complete Rotation Fix
## Seven working modes, real touchscreen alignment, persistent orientation, VNC and XRDP synchronization

**Project:** Nuxel — Mobile Linux for Control Freaks  
**Device target:** Samsung Galaxy S10+ SM-G975F, `beyond2lte`, Exynos 9820  
**Primary architecture:** Fedora ARM64, Phoc/Wayland, Nuxel framebuffer presentation bridge  
**Priority:** High  
**Type:** Source audit, implementation repair, integration, device validation  
**Kernel changes:** Not authorized  
**Firmware changes:** Not authorized  
**Bootloader, recovery or partition changes:** Not authorized

---

# 0. Mission statement

Make orientation work properly throughout Nuxel.

This is not a request to create a new orientation subsystem. Nuxel already has an orientation configuration, policy implementation, sensor abstraction, display-application code, daemon, Bridge integration, Quick Settings controls and a Settings panel.

There have also already been successful rotations on the actual phone.

That last point is important: **do not discard the existing implementation and start experimenting with an unrelated rotation stack.** Find the exact code, backend, configuration, build or runtime state that produced those successful rotations. Recover it, reproduce it and make it the reliable foundation of the implementation.

The task is complete only when all seven requested modes work as expected, including touchscreen input, and remote desktop sessions follow the effective orientation.

The desired result is:

- The physical Nuxel display rotates correctly.
- The touchscreen continues to map to the correct visible coordinates.
- Phoc's logical output geometry changes correctly.
- The framebuffer bridge continues presenting the compositor's actual output.
- The dock, status bar, navigation, windows, keyboard and applications remain usable.
- Auto orientation uses actual sensor readings rather than simulated or manually supplied values.
- VNC follows the actual Nuxel desktop and handles updated geometry.
- XRDP sessions synchronize with Nuxel's current orientation without being logged out or restarted.
- A newly connected remote session starts with the current orientation.
- The selected mode survives reboot.
- Failures roll back locally without depending on SSH or remote desktop connectivity.

Do not mark a feature complete just because a setting can be selected or a status field says `success`.

---

# 1. Required orientation modes

Implement these exact labels throughout Quick Settings, Settings and any other user-facing orientation selector.

| # | User-facing label | Stable internal key | Allowed physical orientation |
|---:|---|---|---:|
| 1 | Auto (FULL) | `auto` | 0°, 90°, 180°, 270° |
| 2 | Auto (PT) | `auto-portrait` | 0°, 180° |
| 3 | Auto (LS) | `auto-landscape` | 90°, 270° |
| 4 | Locked (PT) | `portrait` | 0° |
| 5 | Locked (LS) | `landscape` | 90° |
| 6 | Locked (RPT) | `reverse-portrait` | 180° |
| 7 | Locked (RLS) | `reverse-landscape` | 270° |

Terminology:

- PT = portrait.
- LS = landscape.
- RPT = reverse portrait.
- RLS = reverse landscape.
- FULL = all four possible orientations.

The angle values above are the application's canonical orientation values. They are not permission to blindly assume that a particular compositor backend uses the same transform direction. Recover and verify the mapping that already worked on the physical device.

## 1.1 Preserve stable keys

The source already contains the following canonical keys:

- `auto`
- `auto-portrait`
- `auto-landscape`
- `portrait`
- `landscape`
- `reverse-portrait`
- `reverse-landscape`

Preserve them.

Existing underscore aliases such as `auto_portrait`, `auto_landscape`, `reverse_portrait` and `reverse_landscape` should continue to be accepted where existing configuration or persisted state may use them.

Do not make cosmetic UI labels the persisted configuration values.

The visible labels should map to the stable keys centrally. Avoid separate, hardcoded mode lists with subtly different names in Quick Settings, Settings, the daemon and Bridge.

## 1.2 Expected behavior

**Auto (FULL)**

The system may choose any of the four orientations based on the physical device's stable orientation.

**Auto (PT)**

The system may choose only between 0° and 180°. It must never switch into landscape.

**Auto (LS)**

The system may choose only between 90° and 270°. It must never switch into portrait.

**Locked (PT)**

The physical display must remain at 0°. Sensor readings must not change it.

**Locked (LS)**

The physical display must remain at 90°. Sensor readings must not change it.

**Locked (RPT)**

The physical display must remain at 180°. Sensor readings must not change it.

**Locked (RLS)**

The physical display must remain at 270°. Sensor readings must not change it.

Locked modes must work even when no orientation sensor is available.

Auto modes require a genuinely usable physical orientation source. Do not pretend an auto mode works merely because the user can select it or because a test utility can inject an angle.

---

# 2. Start with forensic recovery of the previously working rotation

This is the first implementation gate.

The owner has already observed several successful rotations. The objective is to recover why those rotations worked and preserve that behavior.

Do not begin by replacing `wlr-randr`, changing the angle mapping or rewriting the policy code.

## 2.1 Inspect the actual current repository

First establish the real repository state:

- Current branch and commit.
- Working tree changes.
- Untracked files.
- Existing local patches.
- Recent orientation-related commits.
- Existing build output.
- Installed orientation binaries.
- Current service state.
- Current compositor and output state.
- Current Nuxel image/package version.

Do not assume that the current checked-out source exactly matches the previously inspected archive.

The source locations below are known starting points, not permission to ignore newer implementations elsewhere.

## 2.2 Search all available history

Inspect:

- Git history involving orientation.
- Historical versions of `policy.py`.
- Historical versions of `apply.py`.
- Historical versions of `nuxel-orientationd`.
- Previous orientation configuration revisions.
- Previous working build scripts.
- Installer and root-filesystem integration changes.
- Previous deployment prompts and patches.
- Existing diagnostic bundles.
- Device logs.
- Any preserved successful transform configuration.

Search for:

- `wlr-randr`
- `--transform`
- `transform`
- `DSI-1`
- `HEADLESS-1`
- `orientation`
- `rotate`
- `reverse-portrait`
- `reverse-landscape`
- `apply_now`
- `apply_transform`
- `effective_degrees`
- `last_good`
- `nuxel-orientationd`
- `nuxel-wl-fb`

Also look for previous successful manual commands and scripts that are not currently part of the official service.

## 2.3 Reproduce the successful result

Before modifying the rotation backend, establish:

1. Which output was actually rotated.
2. Which display backend was used.
3. Which command or compositor operation performed the rotation.
4. Which transform value was used.
5. Whether output logical dimensions changed.
6. Whether the compositor remapped input coordinates automatically.
7. Whether touchscreen input was separately transformed.
8. Whether the framebuffer bridge continued receiving valid frames.
9. Whether the rotation survived application changes or compositor updates.
10. Whether the success was physical output rotation or merely a transformed application/window.

Record the exact successful command or API operation in the root-cause report.

If the old working path has disappeared, identify the commit or package transition that removed it.

**Do not replace an existing working transform mapping with a guessed mapping.**

## 2.4 Separate partial successes from complete successes

A rotation should be classified as one of these:

| Result | Meaning |
|---|---|
| Preference changed | The selected mode was saved |
| Compositor accepted transform | The output accepted a transform request |
| Display rotated | The actual visible panel content rotated |
| Geometry updated | Logical output dimensions match the orientation |
| Touch aligned | Physical touch corresponds to visible coordinates |
| Full local success | Display, geometry and touch work together |
| Remote success | Connected remote sessions followed the orientation |

A previous successful display rotation does not prove that auto sensors or touchscreen mapping were functional.

Record what actually succeeded, and build on it.

---

# 3. Audit the existing implementation before patching

Inspect the following known source paths and every related packaging or runtime integration path.

## 3.1 Configuration

- `configs/nuxel/orientation/orientation.json`
- `configs/nuxel/orientation/orientation.schema.json`

Check:

- Schema validity.
- Default policy.
- Supported modes.
- Stable mode ordering.
- Output identifier.
- Transform mapping.
- Sensor configuration.
- Stability/debounce configuration.
- Rollback configuration.
- Packaging destination.
- Runtime configuration destination.
- Permissions.
- Upgrade migration behavior.

The archived configuration used `DSI-1` and included a transform mapping whose verification status was not settled. Do not accept that as proof that the live system still uses the same output or mapping.

Discover the real active output at runtime.

## 3.2 Policy

Inspect:

`services/nuxel-orientation/nuxel_orientation/policy.py`

The existing policy already has the required conceptual orientation modes and allowed-angle sets.

Preserve that policy where it is correct.

Check:

- Canonical mode parsing.
- Alias support.
- Allowed-angle validation.
- Current orientation handling.
- Sensor transition behavior.
- Flat-device behavior.
- Invalid-sensor handling.
- Stability thresholds.
- Hysteresis.
- Last-good orientation behavior.

Do not duplicate policy decisions in Bridge, Quick Settings, Settings or remote-desktop services.

## 3.3 Display application

Inspect:

`services/nuxel-orientation/nuxel_orientation/apply.py`

The archived implementation uses `wlr-randr` as its display-application backend.

There is a known potential problem: checking whether an executable exists using a subprocess invocation of `command -v` is not a reliable implementation of executable discovery. `command` is normally a shell builtin.

Use a correct executable-discovery mechanism such as `shutil.which()` or a verified direct backend lookup.

However, do not blindly make `wlr-randr` the mandatory backend.

Determine what the installed Phoc/Wayland session actually supports and retain the backend that successfully rotated the physical display.

The implementation must be able to:

- Discover the real active output.
- Read its current transform.
- Read its current logical mode and dimensions.
- Apply an orientation transform.
- Verify the applied transform.
- Detect failed application.
- Detect a disconnected or unavailable output.
- Return an explicit result.
- Report the actual backend and output used.

If the chosen tool cannot reliably inspect an operation it applied, add an appropriate compositor/output-state verification step.

A zero exit status alone is not sufficient proof that the user-visible display is correct.

## 3.4 Daemon

Inspect:

`services/nuxel-orientation/nuxel-orientationd`

Pay particular attention to the difference between:

- Setting and persisting the policy.
- Applying an orientation immediately.
- Watching sensors continuously.
- Applying a newly accepted sensor orientation.
- Restoring the last-known-good orientation.
- Publishing a change for other services.

The archived implementation included a `do_set(..., apply_now=False)` pattern. The Bridge's `set_mode()` path invoked `set <mode>` without `--apply`.

This creates an important possible failure: the UI can save a selected mode while the actual display remains unchanged.

Verify whether this remains true in the current source. If it does, repair it.

A successful `set` operation must have an explicit and truthful contract. It must not claim a successful applied rotation when it only updated a JSON file.

The archived sensor-watch path also needs careful inspection: a detected new angle must lead to a real output application, not merely a new state value.

## 3.5 Systemd

Inspect:

`services/nuxel-orientation/systemd/nuxel-orientationd.service`

The previously inspected archive contained a `Type=oneshot` arrangement with a status invocation and `RemainAfterExit=yes`.

A one-shot status service is not a continuous orientation daemon.

The actual implementation must provide one persistent, reliable orientation authority that remains alive while Auto modes are active.

Use the appropriate systemd service type for the actual daemon implementation.

Ensure:

- Correct user and permissions.
- Correct Wayland runtime environment.
- Correct `WAYLAND_DISPLAY`.
- Correct runtime directory.
- Suitable startup ordering.
- Reliable restart behavior.
- Service readiness reporting.
- Useful logs.
- Clean shutdown.
- No duplicate orientation watchers.
- No unintended dependence on an SSH shell.

Do not make it start before there is an actual output to control.

If Phoc starts after the daemon, implement controlled output discovery and readiness rather than failing permanently at startup.

## 3.6 Bridge

Inspect:

`services/nuxel-bridge/src/bridge.py`

The archived code contains an `OrientationConnector` with helper calls for status, modes and setting a mode.

The Bridge must provide a proper application-facing contract.

Required operations:

- Retrieve supported orientation modes.
- Retrieve current selected policy.
- Retrieve current effective orientation.
- Retrieve actual output and backend status.
- Retrieve sensor state.
- Set the selected mode.
- Request a verified apply when appropriate.
- Receive orientation-change updates.
- Retrieve the last application error.
- Retrieve rollback state.

A mode-setting call must not silently bypass the actual display-application path.

The PWA should not have to know which executable, Wayland protocol or display backend performs rotation.

---

# 4. Define one authoritative orientation state

The system must distinguish between the user's chosen policy and the orientation currently applied to the display.

These are not interchangeable.

For example:

- Selected policy: `auto-landscape`
- Current applied orientation: `90°`
- Sensor: available
- Sensor reading: stable
- Display: applied and verified
- Touch: aligned and verified

Or:

- Selected policy: `auto`
- Current applied orientation: `0°`
- Sensor: unavailable
- Auto state: degraded
- Last good orientation: `0°`

The second example must not be reported as a fully functioning Auto mode.

## 4.1 State model

Use one authoritative state model. It should expose at least:

| Field | Purpose |
|---|---|
| `mode` | Selected stable policy key |
| `mode_label` | User-facing label |
| `effective_degrees` | Currently applied canonical orientation |
| `requested_degrees` | Target of any pending transition |
| `logical_width` | Verified logical output width |
| `logical_height` | Verified logical output height |
| `output_name` | Actual active output |
| `backend` | Actual display backend |
| `display_applied` | Whether display application succeeded |
| `display_verified` | Whether the resulting output was checked |
| `touch_owner` | Component responsible for input transformation |
| `touch_verified` | Whether input mapping was verified |
| `sensor_available` | Real sensor availability |
| `sensor_source` | Actual active sensor source |
| `sensor_last_update` | Timestamp of last valid sample |
| `sensor_degraded_reason` | Explanation when Auto cannot operate |
| `stable_candidate_degrees` | Current stabilized sensor candidate |
| `last_good_degrees` | Last verified local orientation |
| `transition_state` | Idle, applying, verified, rollback or failed |
| `transition_id` | Unique identifier for a rotation transaction |
| `sequence` | Monotonic change sequence |
| `last_error` | Last failure reason |
| `vnc_status` | VNC synchronization state |
| `xrdp_sessions` | Per-session XRDP synchronization state |

Use appropriate additional fields where necessary.

Do not expose only a single field called `orientation` if that makes it impossible to tell a selected policy from an applied result.

## 4.2 Persistence

Persist the selected policy separately from transient runtime sensor readings.

On reboot:

1. Load the last valid mode.
2. Discover the actual compositor output.
3. Discover the current display backend.
4. Restore a valid orientation.
5. Verify the output.
6. Establish the touch mapping.
7. Start sensor monitoring if the selected policy is Auto.
8. Publish the restored state.
9. Allow remote sessions to initialize from it.

Never restore an arbitrary angle simply because it appeared in an old state file.

Validate it against the selected mode's allowed set.

---

# 5. Implement real orientation transactions

A rotation is a transaction, not a preference write.

Use a consistent application sequence so that the display, geometry and touch state cannot silently drift apart.

## 5.1 Transaction sequence

For every requested orientation:

1. Validate the requested mode and angle.
2. Acquire the singleton orientation lock.
3. Confirm there is no conflicting transaction.
4. Read the currently verified output state.
5. Save the last-known-good orientation and geometry.
6. Create a local rollback guard.
7. Determine the transform required by the discovered backend.
8. Apply the output transform using the recovered working method.
9. Wait for the compositor to acknowledge the resulting output state.
10. Read the new logical dimensions.
11. Verify the expected portrait/landscape geometry.
12. Apply or verify the matching touch transformation through its single owner.
13. Wait for the framebuffer presentation bridge to reflect the new compositor geometry.
14. Verify that the physical display is still receiving valid frames.
15. Commit the effective angle and logical geometry.
16. Persist the appropriate policy/state.
17. Publish the orientation-change event.
18. Schedule VNC and XRDP synchronization asynchronously.
19. Complete the transaction and retain the rollback safety state until the configured confirmation period expires.

If any required local step fails, restore the previous verified orientation.

Remote desktop failures must not invalidate a locally successful rotation.

## 5.2 State commit must be honest

Do not update `effective_degrees` before the output transform is verified.

Do not update `touch_verified` merely because the compositor accepted a display transform.

Do not report `display_applied=true` when the implementation has only saved a configuration value.

The selected policy can be displayed immediately as a pending request, but actual application status must remain separate until verified.

## 5.3 Avoid concurrent rotations

Rapid mode selections and sensor changes must not start competing transforms.

Use:

- One orientation authority.
- A serialized transition queue or equivalent lock.
- A monotonic transition sequence.
- Stale-event rejection.
- Cancellation or replacement of obsolete candidates.
- Clear state reporting.

If an old sensor sample arrives after a newer one, it must not undo a more recent user-selected locked mode.

When the user selects any Locked mode, immediately stop Auto-driven changes.

---

# 6. Recover and verify the real display transform

The physical phone display must rotate through the active compositor/output path.

Do not fake rotation in individual PWA applications.

Do not rotate only the framebuffer image while leaving Phoc's logical output and touch coordinate system in portrait.

Do not let the framebuffer bridge and the compositor independently rotate the same content.

## 6.1 Discover the real output

Determine the actual active output name from the live Phoc session.

Possible historical identifiers include:

- `DSI-1`
- `HEADLESS-1`

These are not interchangeable, and neither should be hardcoded without proof.

Inspect the actual runtime output state and record:

- Output name.
- Physical resolution.
- Logical resolution.
- Scale.
- Current transform.
- Available modes.
- Whether the output is physical, headless or virtual.
- Whether the output is controlled by Phoc.
- Whether the chosen backend can apply transforms.

If multiple outputs exist, identify the intended phone display rather than applying a transform indiscriminately.

## 6.2 Reuse the successful backend

The old implementation used `wlr-randr` as one possible backend.

Check whether it is installed and whether the running compositor supports it.

If used, check the command's actual supported syntax and confirm that the operation changes the real output.

If another existing mechanism is responsible for the successful rotations, preserve and use that mechanism.

Do not assume that every output backend interprets a requested clockwise angle identically.

## 6.3 Canonical angle versus compositor transform

Nuxel's canonical angles are:

| Canonical angle | Meaning |
|---:|---|
| 0° | Normal portrait |
| 90° | Landscape |
| 180° | Reverse portrait |
| 270° | Reverse landscape |

A historical configuration contained a mapping resembling:

| Canonical angle | Historical transform |
|---:|---|
| 0° | `normal` |
| 90° | `270` |
| 180° | `180` |
| 270° | `90` |

The reverse 90° mapping may be deliberate because the panel mounting or compositor convention differs from the application's clockwise convention.

It is not proven to be correct for the current build.

Find the previous successful mapping and verify it physically.

Do not "simplify" it to a mathematically intuitive mapping unless the device test proves that this is correct.

Document both:

- Nuxel's canonical orientation.
- The actual backend transform used to achieve it.

## 6.4 Logical geometry

For a conventional portrait panel, landscape normally swaps the logical width and height.

For example, a nominal 1440 × 3040 physical panel may expose approximately 3040 × 1440 logical geometry in landscape.

This is only an expected relationship. Inspect the actual active output's mode, scale and geometry before asserting dimensions.

A correct rotation must update the compositor's real logical geometry.

Check:

- Output dimensions.
- Surface/window placement.
- Pointer coordinates.
- Status bar.
- Dock.
- Navigation area.
- Keyboard.
- Full-screen applications.
- PWA viewport dimensions.
- Screenshots.
- Remote desktop dimensions.

Do not solve this by applying CSS rotation to the entire launcher.

## 6.5 Framebuffer bridge integration

The established Nuxel presentation path is:

`Phoc/Wayland → zwlr_screencopy → nuxel-wl-fb → /dev/fb0 → Samsung display`

The framebuffer bridge is the presentation bridge, not a second orientation authority.

Maintain the invariant:

**`nuxel-wl-fb` is the sole `/dev/fb0` writer.**

After a compositor orientation change:

- Confirm the bridge observes the new logical output geometry.
- Confirm screenshot/capture buffers match the new dimensions.
- Confirm the physical framebuffer presentation remains valid.
- Confirm pan operations succeed.
- Confirm no stale portrait buffer is stretched into landscape.
- Confirm no second service starts writing to `/dev/fb0`.
- Confirm the bridge does not apply a second rotation.

Inspect the actual active C source and build path. Historically, the framebuffer builder has referenced `tools/s10plus/a34/nuxel-wl-fb.c`; verify whether that is still the source compiled into the current image.

If the bridge has assumptions about portrait dimensions, buffer stride, virtual height or fixed viewport geometry, fix them based on actual compositor output dimensions.

Do not hardcode a landscape resolution just to make one device test pass.

---

# 7. Touchscreen alignment is part of rotation, not an optional follow-up

The phone must remain usable after rotation.

A perfectly rotated picture with portrait-mapped touch is a failed implementation.

## 7.1 Find the single touch-transform owner

Inspect:

- Phoc input configuration.
- Libinput device configuration.
- Input device calibration.
- Device-tree mount matrix information already available to userspace.
- Any existing Nuxel touch transformation code.
- Any framebuffer/input bridge assumptions.
- Existing calibration and diagnostics.

Prefer compositor-owned input transformation whenever supported.

The display and touch coordinate transformations must be coordinated by one owner.

Do not let:

- Phoc rotate touch.
- A custom shim rotate touch again.
- An application rotate touch a third time.

Double transforms are a particularly likely cause of touches landing in the wrong area after a partial rotation fix.

## 7.2 Coordinate convention

For normalized screen coordinates `(x, y)` in the range 0–1, the conceptual clockwise mappings are:

| Orientation | Conceptual mapping |
|---:|---|
| 0° | `(x, y)` |
| 90° | `(1-y, x)` |
| 180° | `(1-x, 1-y)` |
| 270° | `(y, 1-x)` |

These formulas describe the intended geometric relationships, not a ready-to-paste hardware calibration matrix.

Actual physical panel mounting, raw touchscreen axes, swapped axes, inversions and compositor conventions must be measured.

Implement the mapping through the verified compositor/input mechanism.

## 7.3 Physical input test

For each of the four orientations:

1. Touch all four visible screen corners.
2. Touch the center.
3. Touch all four edges.
4. Test the top status bar.
5. Test the dock.
6. Test navigation controls.
7. Test the Quick Settings panel.
8. Open and use the on-screen keyboard.
9. Type into a text field.
10. Test a modal or dialog.
11. Test window/application controls.
12. Test scrolling.
13. Test any pointer movement generated through VNC/XRDP.

The visible target must receive the touch.

Pay particular attention to:

- Bottom navigation after rotation.
- Dock hit boxes.
- OSK key hit boxes.
- Status bar gestures.
- Application edges.
- Screen cutout and rounded-corner areas.

A screenshot that looks correct is not a successful touch test.

---

# 8. Make the Auto modes use real sensor data

Inspect:

`services/nuxel-orientation/nuxel_orientation/sensors.py`

The existing source contains abstractions for:

- IIO raw XYZ and scale.
- `iio-sensor-proxy`.
- Manual test input.

Determine which source actually exists and functions on the current phone.

## 8.1 Re-probe instead of trusting stale hardware notes

There is an older hardware-boundary report describing the LSM6DSO sensor path through a Samsung/Broadcom SSP sensor hub, with earlier diagnostics indicating unavailable hub access and missing usable raw IIO readings.

That information is important but may be stale.

The user has since observed successful manual rotations and the hardware/runtime state may have changed.

Probe the current device.

Check:

- IIO device enumeration.
- Available channels.
- Raw values.
- Scale values.
- Sampling frequency.
- Sensor availability.
- Sensor permissions.
- Sensor-proxy service availability.
- Sensor-proxy events.
- Actual readings while physically rotating the handset.
- Whether the sensor source remains available after login and screen locking.

Record the device and source actually used.

## 8.2 Do not treat manual input as a sensor

ManualSource is useful for development and deterministic policy tests.

It must not be marked as a production-capable Auto source.

If a manual diagnostic source is active:

- Report that it is manual.
- Disable any claim of genuine automatic orientation.
- Do not show a green Auto success state.
- Ensure production startup does not select it accidentally.

## 8.3 Sensor mapping

A sensor typically provides a gravity vector or an equivalent orientation signal.

Determine its physical axis mounting relative to the handset display.

Do not assume that increasing X means landscape-left or that increasing Y means portrait.

Calibrate using actual physical poses:

- Normal portrait.
- Landscape.
- Reverse portrait.
- Reverse landscape.
- Flat face-up.
- Flat face-down, where the sensor supports it.

The sensor's stable direction must map to the correct canonical orientation.

Document the measured mapping.

## 8.4 Stability and hysteresis

Auto rotation must not jitter.

Implement configurable:

- Sensor sampling interval.
- Minimum valid sample count.
- Candidate stability duration.
- Angular hysteresis.
- Flat-device threshold.
- Invalid-sample timeout.
- Minimum time between applied transitions.

Use a sensible initial stability window informed by the existing owner test, which previously used approximately 300–800 ms for settling.

Do not apply an angle based on one noisy sample.

A transition should occur only after the candidate is stable and permitted by the selected mode.

If the device is flat, hold the last good orientation.

If readings become invalid, hold the last good orientation.

If the sensor disappears, report an explicit degraded state.

## 8.5 Policy-specific sensor behavior

Implement the actual allowed-angle sets centrally:

```text
auto:
    0, 90, 180, 270

auto-portrait:
    0, 180

auto-landscape:
    90, 270

portrait:
    0

landscape:
    90

reverse-portrait:
    180

reverse-landscape:
    270
```

Auto PT must never apply 90° or 270°.

Auto LS must never apply 0° or 180°.

Locked modes must ignore sensor-driven changes.

## 8.6 Sensor loss and mode transitions

When changing from a Locked mode into an Auto mode:

1. Retain the current verified display orientation.
2. Start or resume sensor monitoring.
3. Wait for a valid stable candidate.
4. Verify that the candidate is permitted.
5. Apply it through the normal orientation transaction.

Do not rotate to a random default merely because Auto was selected.

When changing from Auto into a Locked mode:

1. Stop accepting Auto candidates.
2. Immediately request the exact locked orientation.
3. Apply and verify it.
4. Prevent queued old sensor events from undoing it.

---

# 9. Make the orientation daemon a real persistent service

There must be one long-running owner of orientation behavior.

It should:

- Load and validate configuration.
- Discover the actual active output.
- Initialize the last valid orientation.
- Monitor real sensor data when an Auto policy is selected.
- Apply locked orientations when selected.
- Serialize all transitions.
- Verify display geometry.
- Coordinate touch mapping.
- Maintain rollback state.
- Publish orientation events.
- Expose diagnostic status.
- Recover from transient output and sensor failures.

The daemon must not exit after reporting a one-time status if Auto orientation is expected to work.

Use an appropriate systemd service type and readiness contract.

The daemon must not require an SSH terminal to stay alive.

There must not be multiple independent services each applying transforms.

## 9.1 Startup ordering

Use a reliable startup strategy that handles:

- Phoc not yet running.
- Wayland socket not yet available.
- Output not yet advertised.
- Sensor service starting later.
- Framebuffer bridge starting later.
- Remote desktop services starting later.

A transient missing output should trigger a controlled retry, not an infinite busy loop.

When the output becomes available, initialize from the saved state and verify it.

## 9.2 Service restart

When the daemon restarts:

- Do not blindly rotate through all four orientations.
- Read the current compositor state.
- Read the last-good state.
- Validate the saved policy.
- Restore a permitted orientation.
- Re-establish subscriptions.
- Republish current state.
- Preserve valid remote sessions where possible.

A daemon restart must not create a screen rotation loop.

---

# 10. Rollback protection

Rotation can make the display difficult to use or leave the user unable to operate the interface.

Rollback must be local and independent of remote connectivity.

The archived configuration used a very short `revert_after_ms` value of approximately 4000 ms. That is too aggressive for a deliberate owner acceptance test and may trigger unexpected rollback while the user is still checking the display.

Replace this with an explicit, configurable transaction/confirmation design.

A reasonable initial owner-test window is approximately 60–90 seconds.

The exact timeout should be configurable and documented.

## 10.1 Required rollback behavior

Before applying a risky new orientation:

- Record the last verified orientation.
- Record the last verified logical dimensions.
- Record the previous transform and touch mapping.
- Start a local rollback guard.
- Apply the new orientation.
- Verify the display.
- Verify geometry.
- Verify touch mapping where possible.

If the transformation cannot be verified before the timeout:

- Restore the previous transform.
- Restore the previous touch mapping.
- Verify the previous output state.
- Mark the transaction rolled back.
- Record the failure reason.
- Publish the rollback event.

## 10.2 Independent watchdog

The rollback mechanism must not depend on:

- SSH staying connected.
- VNC staying connected.
- XRDP staying connected.
- The PWA remaining open.
- The initiating JavaScript process remaining alive.

If the orientation daemon crashes during an unconfirmed transaction, rollback must still occur.

Implement an appropriate local watchdog or equivalent transaction guard.

Avoid starting an unbounded collection of watchdog processes.

## 10.3 Remote failure is not local failure

If the phone has successfully rotated but the VNC client cannot resize, do not undo the phone rotation.

If XRDP cannot update one virtual session, do not undo the phone rotation.

Report the remote failure independently.

The local phone display and touchscreen are the primary transaction.

Remote synchronization is an asynchronous consumer of the verified local orientation event.

---

# 11. Quick Settings and Settings integration

The existing user-facing controls should be repaired, not replaced with a separate orientation interface.

Inspect:

- `pwa/nuxel-home/js/qs.js`
- `pwa/nuxel-apps/settings/settings.js`
- Any shared orientation UI or Bridge wrapper.

The archived Quick Settings implementation already had a Rotate tile with a short tap action and a long-press selection menu.

The archived Settings implementation already had an orientation settings panel.

Preserve useful existing UI behavior and improve it.

## 11.1 Exact labels

Use these exact labels:

```text
Auto (FULL)
Auto (PT)
Auto (LS)
Locked (PT)
Locked (LS)
Locked (RPT)
Locked (RLS)
```

Avoid alternate labels such as:

- Forced Portrait.
- Auto Portrait.
- Reverse Portrait.
- Landscape Locked.

Those may be understandable internally, but the seven requested labels should be the user-facing standard everywhere.

## 11.2 Selection behavior

The UI must clearly show:

- Currently selected policy.
- Currently applied angle.
- Whether a transition is in progress.
- Whether the sensor is available.
- Whether Auto is operational or degraded.
- Whether display geometry has been verified.
- Whether touch mapping has been verified.
- Whether remote sessions are synchronized.

Do not show the selected mode as the effective angle.

For example, Auto (FULL) is a policy, not an angle.

## 11.3 Quick Settings behavior

Tapping the Rotate tile must have a predictable effect.

Do not let the old simple Auto/Portrait toggle unexpectedly override a manually selected mode.

The long-press or expanded selection action should expose all seven modes.

After selecting a mode:

1. Send the stable key to Bridge.
2. Receive the transaction identifier/result.
3. Display a pending state.
4. Subscribe to the resulting orientation update.
5. Show the verified effective orientation.
6. Show any failure or rollback.

Do not optimistically display a successful rotation before the physical display has changed.

## 11.4 Settings behavior

The Settings page should provide:

- Seven selectable modes.
- Selected policy.
- Effective angle.
- Sensor source/status.
- Output/backend status.
- Touch mapping status.
- Last error.
- Last-good angle.
- VNC synchronization status.
- XRDP session status.

A diagnostic section should be available without making normal Settings cluttered.

If Auto has no real sensor source, state why.

---

# 12. One orientation event interface for remote services

VNC and XRDP must not each implement their own orientation policy.

They must consume the verified state from Nuxel's single orientation authority.

Implement a stable event/query interface through an appropriate existing mechanism.

Possible mechanisms include:

- D-Bus signals.
- A Unix-domain socket.
- An existing Bridge event stream.

Use the mechanism that fits the current architecture.

Do not introduce three competing interfaces when one existing interface can do the job.

## 12.1 Event contents

A useful orientation-change event should contain:

```json
{
  "sequence": 123,
  "transition_id": "example-transaction-id",
  "mode": "landscape",
  "mode_label": "Locked (LS)",
  "effective_degrees": 90,
  "logical_width": 3040,
  "logical_height": 1440,
  "output_name": "actual-discovered-output",
  "backend": "actual-active-backend",
  "display_verified": true,
  "touch_verified": true,
  "timestamp": "runtime-generated-timestamp"
}
```

This is a structural example, not a request to hardcode these example values.

The publisher must send the real current values.

Include an event version or equivalent compatibility mechanism if necessary.

## 12.2 Consumer behavior

VNC and XRDP should:

- Query the current state when they start.
- Subscribe to changes.
- Reject stale sequence numbers.
- Apply updates asynchronously.
- Report their own result.
- Avoid blocking the local orientation daemon.
- Reconnect to the event source when it restarts.
- Initialize new remote sessions from the latest state.

Do not create an independent high-frequency polling loop for each session.

---

# 13. VNC must mirror the rotated Nuxel desktop

The VNC user expects to see and control the actual Nuxel desktop.

It must not become an unrelated virtual desktop that happens to have a VNC connection.

Inspect the actual VNC implementation and confirm how it attaches to the running Phoc session.

The desired path is a mirror of the real compositor output.

If the implementation uses WayVNC, verify its actual capture and output behavior. If another existing VNC server is used, preserve the correct supported integration.

## 13.1 Physical rotation behavior

When Nuxel rotates:

- The Phoc output changes.
- The VNC capture sees the new orientation.
- The desktop image is correct.
- The desktop dimensions update.
- The remote pointer maps to the correct coordinates.
- The session remains connected where the client supports dynamic resizing.

Do not rotate the VNC image a second time if the captured Phoc output is already correctly oriented.

## 13.2 RFB desktop-size handling

Investigate the VNC server's support for the RFB DesktopSize pseudo-encoding or its equivalent dynamic desktop-size notification.

For a client that supports dynamic resizing:

- Advertise the new framebuffer dimensions.
- Update the captured output.
- Preserve the connection.
- Keep pointer coordinates correct.
- Verify that the client does not stretch stale portrait dimensions into landscape.

For a client that does not support dynamic resize:

- Use a supported scaling or letterboxing fallback.
- Preserve input coordinate mapping.
- Report the limitation.
- Do not pretend that the client received a native resolution change.

A fallback must not corrupt the actual physical display.

## 13.3 VNC pointer input

Test pointer positions at all screen corners and edges after each orientation.

The mapping must respect the current remote framebuffer dimensions and the active orientation.

If the remote desktop changes from portrait to landscape, a pointer click on the remote top-left corner must still land at the actual top-left corner of the presented desktop.

## 13.4 VNC connection lifecycle

Test:

1. Start VNC in portrait.
2. Connect.
3. Rotate the physical phone to landscape.
4. Keep the VNC session connected.
5. Verify the remote image and dimensions.
6. Rotate to reverse landscape.
7. Verify image and pointer mapping.
8. Rotate to reverse portrait.
9. Rotate to portrait.
10. Disconnect.
11. Change the phone orientation again.
12. Reconnect.
13. Verify the new client starts in the current orientation.

A reconnect must not restore stale portrait geometry.

## 13.5 Local isolation

VNC failure must never prevent local rotation.

If the server disconnects or rejects a resize, record the failure and keep the phone operating.

---

# 14. XRDP must follow orientation without destroying sessions

XRDP needs special treatment because its session architecture differs from VNC.

A VNC session can mirror the real Phoc desktop.

An XRDP session normally uses its own virtual Xorg/XRDP desktop rather than the physical Phoc surface.

Do not falsely describe XRDP as a mirror of the phone's physical compositor.

The requested behavior is that its desktop orientation and geometry follow Nuxel's effective orientation while the session remains usable.

## 14.1 Inspect the real XRDP architecture

Identify:

- Actual XRDP service.
- Actual xrdp-sesman service.
- Xorg backend.
- xorgxrdp version.
- Active session displays.
- Supported XRandR capabilities.
- Available display modes.
- RDP client display-control capability.
- Whether dynamic resizing is enabled.
- Existing user session persistence behavior.
- Existing launch environment.

Do not assume all XRDP sessions share one display or one geometry.

Track every active session separately.

## 14.2 Orientation mapping

When Nuxel's effective orientation changes, update the corresponding active XRDP sessions.

Expected behavior:

| Nuxel orientation | XRDP desktop behavior |
|---:|---|
| 0° | Portrait-oriented desktop |
| 90° | Landscape-oriented desktop |
| 180° | Reverse portrait-oriented desktop |
| 270° | Reverse landscape-oriented desktop |

The virtual desktop dimensions should follow the orientation.

The XRDP pointer must follow the same mapping as the visible desktop.

A reverse orientation must not silently be treated as ordinary portrait or landscape if the server can provide the correct transform.

## 14.3 Use native support where available

Probe whether the actual XRDP/Xorg stack supports:

- The required RandR output configuration.
- Runtime output resizing.
- Runtime rotation.
- The desired virtual output geometry.
- Relevant RDP display-control updates.

Do not assume that `xrandr --rotate` works in every xorgxrdp configuration.

If native support exists, use it and verify it.

If native rotation is not available, investigate a server-side virtual-desktop transformation layer or another supported approach that keeps the XRDP session alive.

Do not apply a CSS rotation to one application and claim the XRDP desktop follows the phone.

## 14.4 Dynamic resize and fallback

When a connected client supports dynamic desktop sizing:

- Request the appropriate desktop geometry.
- Apply the supported server-side update.
- Verify the active X display geometry.
- Verify the remote client receives the new dimensions.
- Preserve running applications.
- Preserve the existing XRDP session.

When a connected client cannot dynamically resize:

- Use a safe server-side scale/letterbox fallback if supported.
- Preserve correct pointer mapping.
- Report the limitation for that session.
- Avoid logout or session destruction.

Do not claim a full native rotation if the implementation only scales the image.

## 14.5 Keep sessions alive

The following are explicitly forbidden as normal rotation behavior:

- Logging out the XRDP user.
- Killing the user's desktop processes.
- Terminating the XRDP session.
- Restarting `xrdp-sesman`.
- Recreating the whole virtual desktop.
- Killing applications to force a new size.
- Disconnecting all sessions to make a rotation work.

A rotation event must update an active session through the supported live mechanism.

If a particular backend fundamentally cannot support the desired operation, report the limitation with evidence and implement the best non-destructive fallback.

## 14.6 New and reconnected XRDP sessions

When an XRDP session starts:

1. Query the current orientation authority.
2. Read the current effective orientation.
3. Create or configure the virtual desktop with matching geometry.
4. Apply the supported orientation transform.
5. Establish correct pointer mapping.
6. Report session synchronization state.

The new session must not default to portrait when the phone is already in landscape.

When an existing session reconnects, refresh its orientation and geometry from current state rather than restoring stale dimensions.

## 14.7 Per-session reporting

Track at least:

- Session identifier.
- User/session display.
- Current virtual width and height.
- Requested orientation.
- Applied orientation.
- Resize capability.
- Rotation capability.
- Last synchronized sequence.
- Last synchronization result.
- Current fallback, if any.
- Last error.

One unsupported session must not cause the other XRDP sessions to fail.

## 14.8 Jump Desktop on macOS

The owner uses Jump Desktop on macOS and expects the remote display to follow Nuxel's orientation.

Test the actual available Jump Desktop client against the running server.

Verify:

- Portrait.
- Landscape.
- Reverse portrait.
- Reverse landscape.
- Dynamic resize.
- Reconnect behavior.
- Pointer accuracy.
- Whether the client window resizes or letterboxes.
- Whether the server session stays alive.

Do not rotate the Mac's physical display.

Do not confuse resizing the Jump Desktop application window with changing the remote Nuxel desktop.

If Jump Desktop does not support a particular server-side dynamic update, document its actual behavior and test a second compatible client to distinguish server capability from client limitations.

Do not claim Jump Desktop has been tested if the agent did not have access to a real client session.

---

# 15. Keep the display, touch and remote paths consistent

The correct high-level relationship is:

```text
                   User / Sensor Policy
                           |
                           v
                  nuxel-orientationd
                           |
             Verified orientation transaction
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
         Phoc output   Touch mapping   State/event
             |             |             |
             v             v       +-----+------+
       Wayland output   Physical     |            |
             |          touchscreen |            |
             v                      v            v
       nuxel-wl-fb                VNC         XRDP
             |                 Phoc mirror  Virtual session
             v
         /dev/fb0
             |
             v
       Physical AMOLED
```

This is a conceptual responsibility diagram.

The precise implementation should reuse Nuxel's current components and existing interfaces rather than adding unnecessary services.

Important invariants:

1. One orientation policy owner.
2. One verified local display-transform owner.
3. One touch-transform owner.
4. One `/dev/fb0` writer.
5. VNC consumes the actual Phoc session.
6. XRDP updates its own virtual sessions.
7. Remote failures cannot undo successful local rotation.
8. New sessions query current effective orientation.
9. All consumers reject stale events.

---

# 16. Build, packaging and installation integration

A correct patch in the source tree is insufficient if the device image does not contain it or the running device continues using an older binary.

Inspect every relevant build and installation path.

At minimum, verify:

- Orientation Python package installation.
- `nuxel-orientationd` installation.
- Helper executable installation.
- Systemd unit installation and enablement.
- Configuration installation.
- Schema installation.
- Bridge integration.
- Quick Settings assets and scripts.
- Settings assets and scripts.
- Remote desktop event subscription integration.
- Framebuffer bridge compatibility.
- Root filesystem build.
- Update/deploy scripts.
- Release packaging.

The previously inspected archive's `images/s10plus/build-phone-rootfs-inside-fedora.sh` did not appear to include all orientation references expected from the service tree.

Re-inspect the current builder and confirm that the actual deployed root filesystem includes the current orientation implementation.

Do not rely on a developer machine's installed Python package or manually copied files.

## 16.1 Runtime verification

After deployment, prove that the phone is running the new implementation.

Collect:

- Installed file versions or hashes.
- Running daemon executable path.
- Running service definition.
- Current configuration.
- Bridge helper path.
- Active output state.
- Current orientation state.
- Framebuffer bridge status.
- VNC server status.
- XRDP service and session status.

A successful local unit test is not proof that the phone is running the patched code.

## 16.2 Avoid unnecessary restarts

Do not restart all of Nuxel just because an orientation UI file changed.

Restart only the components required for the actual patch.

Do not restart XRDP sessions just to update their geometry.

Do not restart Phoc unless a verified technical requirement makes it unavoidable.

If a compositor restart is unavoidable, explain why, make the recovery path explicit and preserve user data and session safety.

---

# 17. Configuration and migration

Keep configuration centralized and schema-validated.

The configuration should define:

- Available stable mode keys.
- User-facing labels or a shared label mapping.
- Default policy.
- Backend preference/fallback.
- Output discovery preferences.
- Sensor source preferences.
- Sensor stability parameters.
- Flat-device behavior.
- Rollback timeout.
- Event interface version.
- Diagnostic logging settings.

Do not duplicate transform mappings in three files.

## 17.1 Backward compatibility

For existing Nuxel installations:

- Preserve valid stable mode keys.
- Normalize supported aliases.
- Migrate old labels only where needed.
- Preserve a valid last-good orientation.
- Reject unknown modes safely.
- Do not corrupt an existing config on parse failure.
- Create a backup before migration.
- Preserve unrelated user settings.

If the output identifier changes, prefer live output discovery and a validated selection mechanism over a brittle hardcoded replacement.

## 17.2 Safe defaults

A reasonable default is the existing Auto policy if the implementation can establish a genuine supported sensor source.

If no usable sensor exists, do not pretend the phone is automatically rotating.

Preserve the existing policy preference while reporting the degraded state, or use the project's explicitly chosen safe default if the current installation has no valid preference.

Locked modes must remain available independently of sensor availability.

---

# 18. Testing strategy

Tests must cover policy, application, hardware, UI, remote sessions and failure recovery.

Do not stop at unit tests.

## 18.1 Automated policy tests

Test:

- All seven canonical keys.
- All supported aliases.
- Unknown mode rejection.
- Allowed-angle enforcement.
- Auto FULL acceptance of all four angles.
- Auto PT rejection of both landscape angles.
- Auto LS rejection of both portrait angles.
- All four Locked modes.
- Flat-device hold.
- Invalid reading handling.
- Stale sample rejection.
- Hysteresis.
- Stable candidate handling.
- Sensor source reporting.
- Manual-source non-production status.
- Mode persistence.
- Configuration migration.

## 18.2 Application tests

Use a fake or controlled display backend to test:

- Successful normal transform.
- Successful 90° transform.
- Successful 180° transform.
- Successful 270° transform.
- Unknown output.
- Missing backend.
- Backend command failure.
- Output disappearing.
- Output failing to change.
- Logical dimensions not updating.
- Touch application failure.
- State commit ordering.
- Rollback.
- Simultaneous requests.
- Old events arriving late.

Verify that failed transformations never update effective state to an unverified angle.

## 18.3 Bridge tests

Test:

- Mode listing.
- Mode labels and keys.
- Setting each mode.
- Result and error reporting.
- Current effective state.
- Event subscription.
- Event sequence ordering.
- Restart/reconnect.
- Old client compatibility where applicable.

A Bridge test must fail when a mode is persisted but the actual apply operation is never called.

## 18.4 UI tests

Test all seven labels in:

- Quick Settings.
- Quick Settings expanded/long-press selection.
- Settings orientation panel.

Verify:

- The same label and key mapping everywhere.
- No stale selection after a change.
- No false green status.
- Pending state.
- Verified state.
- Failure state.
- Rollback state.
- Sensor degraded state.
- Remote synchronization updates.

## 18.5 Physical display matrix

Run the following on the actual Galaxy S10+.

| Test | Expected result |
|---|---|
| Locked (PT) | Physical portrait, 0° |
| Locked (LS) | Physical landscape, 90° |
| Locked (RPT) | Reverse portrait, 180° |
| Locked (RLS) | Reverse landscape, 270° |
| Auto (FULL) | All four stable physical poses permitted |
| Auto (PT) | Only portrait and reverse portrait |
| Auto (LS) | Only landscape and reverse landscape |
| Flat while Auto | Last good orientation retained |
| Invalid sensor | No random rotation |
| Sensor unavailable | Auto reports degraded status |
| Reboot | Saved policy restored |

For each physical orientation, verify:

- Correct image.
- Correct logical dimensions.
- Correct panel content.
- No black screen.
- No stale framebuffer geometry.
- No doubled transform.
- No unexpected compositor crash.
- Correct status bar and dock.

## 18.6 Touchscreen matrix

For every physical orientation test:

- Four corners.
- Four edges.
- Center.
- Dock.
- Navigation.
- Quick Settings.
- Status bar gestures.
- Keyboard.
- Text input.
- Dialogs.
- App controls.
- Scrolling.

All hit targets must correspond to their visible positions.

Repeat after switching directly from every orientation to every other orientation where practical. Do not test only the sequence portrait → landscape → portrait.

## 18.7 VNC matrix

Keep a VNC client connected during orientation changes.

| Scenario | Expected result |
|---|---|
| Connect in portrait | Portrait image and geometry |
| Rotate phone to landscape | Same session follows landscape |
| Rotate to reverse landscape | Correct reverse orientation |
| Rotate to reverse portrait | Correct reverse orientation |
| Rotate back to portrait | Correct portrait |
| Pointer at corners | Correct target coordinates |
| Client supports resize | Updated framebuffer dimensions |
| Client lacks resize | Safe fallback and honest status |
| Disconnect/reconnect | Current orientation restored |
| VNC server restart | Local display remains unaffected |

## 18.8 XRDP matrix

Keep an XRDP session connected while changing phone orientation.

| Scenario | Expected result |
|---|---|
| New session in portrait | Portrait-oriented virtual desktop |
| Existing session to landscape | Live geometry/orientation update |
| Landscape to reverse landscape | Correct orientation |
| Reverse landscape to reverse portrait | Correct orientation |
| Reverse portrait to portrait | Correct orientation |
| Applications open during rotation | Applications remain running |
| Pointer at corners | Correct mapping |
| Dynamic resize supported | Session receives updated geometry |
| Dynamic resize unsupported | Safe fallback and clear status |
| Disconnect/reconnect | Current orientation restored |
| Multiple sessions | Each session reports its own state |

Explicitly verify that no normal orientation transition logs out users or terminates applications.

## 18.9 Combined stress test

Run a combined test with:

- Auto (FULL).
- Quick Settings open.
- An application in the foreground.
- Keyboard open and closed.
- VNC connected.
- XRDP connected.
- SSH connected.
- Framebuffer bridge running.

Perform multiple orientation transitions.

Observe whether:

- The screen remains usable.
- Touch stays aligned.
- The application remains open.
- The keyboard remains usable.
- VNC updates.
- XRDP updates.
- SSH stays connected.
- The framebuffer bridge stays healthy.
- No transform loops occur.
- No service repeatedly restarts.

Remote sessions must not destabilize the local display.

---

# 19. Operational diagnostics

Add or repair one clear diagnostic command.

The precise command name should follow existing Nuxel conventions, but a command such as:

```bash
nuxel-orientationd status
```

should return useful, machine-readable or clearly formatted diagnostic information.

It should report:

- Selected policy.
- User-facing label.
- Effective angle.
- Pending angle.
- Current transition state.
- Actual output name.
- Actual backend.
- Current transform.
- Current logical dimensions.
- Sensor source and availability.
- Last valid sensor sample.
- Stabilized candidate.
- Last-good orientation.
- Touch-transform owner.
- Touch verification state.
- Rollback guard state.
- Last error.
- Current event sequence.
- VNC synchronization.
- Each XRDP session and its synchronization state.

Add appropriate commands for:

- Listing supported modes.
- Setting a mode.
- Requesting a diagnostic.
- Reading current state.
- Testing sensor availability.

Do not add a production command that can silently set an unverified effective state.

## 19.1 Useful logs

Use structured, actionable logs.

Examples of useful messages:

```text
orientation: policy selected: auto-landscape
orientation: discovered output: <actual-output>
orientation: display backend: <actual-backend>
orientation: sensor source: <actual-source>
orientation: candidate stabilized: 90
orientation: applying canonical angle 90
orientation: compositor transform verified
orientation: logical geometry verified
orientation: touch mapping verified
orientation: local orientation committed
orientation: published sequence <n>
orientation: VNC synchronization: success
orientation: XRDP session <id> synchronization: success
```

Use actual discovered values.

Failure examples:

```text
orientation: no supported sensor source
orientation: auto mode degraded; retaining last good orientation

orientation: display application failed
orientation: restoring previous transform

orientation: touch mapping could not be verified
orientation: rollback triggered

orientation: XRDP session <id> does not support native resize
orientation: applying supported fallback
```

Do not log passwords, session secrets or private connection credentials.

---

# 20. Safety constraints

These constraints are mandatory.

## 20.1 No kernel flashing

Do not:

- Build a new kernel for this task.
- Flash a kernel.
- Change the boot image.
- Write partitions.
- Change the bootloader.
- Modify recovery.
- Flash device firmware.
- Modify the device tree on the phone.

If the current kernel does not expose the required sensor, report the precise limitation.

Fixed orientation modes must still be made to work without an accelerometer.

Any future kernel or firmware work must be a separate explicitly authorized task with its own device recovery plan.

## 20.2 Preserve existing access

Preserve:

- Existing SSH access.
- Existing Tri-Link application IDs.
- Existing VNC and XRDP connection configuration where valid.
- Existing user data.
- Existing Nuxel desktop state.
- Existing remote-access security policy.

Do not widen remote service bind addresses or firewall access as a shortcut.

Do not introduce experimental USB networking.

Do not assume a USB transport is safe merely because the current SSH-over-Wi-Fi path works.

## 20.3 No competing framebuffer writer

`nuxel-wl-fb` remains the sole `/dev/fb0` writer.

No orientation-specific helper may independently write to `/dev/fb0`.

## 20.4 No fake sensor success

An injected orientation or manual test reading is not proof of hardware Auto behavior.

Report unavailable sensors accurately.

## 20.5 No destructive remote-session behavior

Do not log out or kill XRDP sessions to force a resize.

Do not disconnect VNC clients as the default way to apply a rotation.

Use safe fallbacks and report capability limits.

---

# 21. Deployment over Wi-Fi SSH

Use the existing Nuxel deployment workflow.

Do not create a new deployment system if the repository already contains an appropriate safe deployment path.

Before deployment:

1. Confirm the target device is the expected S10+.
2. Confirm SSH connectivity.
3. Check available storage.
4. Capture the current orientation state and configuration.
5. Back up files that will be replaced.
6. Build the patched userspace components.
7. Run automated tests.
8. Verify packaging contents.
9. Prepare rollback commands.
10. Confirm that the deployment does not write kernel or firmware partitions.

Deploy only the required userspace files/packages.

After deployment:

1. Verify installed versions.
2. Start or restart only necessary services.
3. Check the orientation daemon.
4. Check Phoc output discovery.
5. Check framebuffer bridge health.
6. Test Locked (PT).
7. Test Locked (LS).
8. Test Locked (RPT).
9. Test Locked (RLS).
10. Test Auto sensor capability.
11. Test touch.
12. Test VNC.
13. Test XRDP.
14. Test reboot persistence.

If a rotation causes the display to become unusable, the local rollback mechanism must restore the previous known-good state without SSH.

Do not report deployment success merely because the files copied successfully.

---

# 22. Documentation to update

Update the existing orientation documentation instead of creating contradictory descriptions.

Inspect and update:

- `docs/A49/OWNER-TEST-ORIENTATION.md`
- `docs/a54-reliability/ORIENTATION-MATRIX.md`
- `docs/a69/ROTATION-HARDWARE-BOUNDARY.md`

Also update relevant service, build and remote-desktop documentation.

Document:

- The seven modes.
- Stable keys.
- Canonical angles.
- Actual physical transform mapping.
- Active display backend.
- Active output.
- Touch-transform owner.
- Actual sensor source.
- How to test sensors.
- How rollback works.
- VNC behavior and limitations.
- XRDP behavior and limitations.
- Jump Desktop results if physically tested.
- Known remaining hardware restrictions.

Do not simply change old hardware-boundary documentation to say that the sensor works unless it was verified on the current device.

Clearly distinguish:

- Verified working.
- Implemented but not hardware-tested.
- Degraded due to unavailable sensor.
- Client-dependent behavior.
- Unsupported behavior.

---

# 23. Required deliverables

The implementation agent must return all of the following.

## 23.1 Root-cause report

Explain:

- What made the previous rotations succeed.
- Which backend was actually responsible.
- Which transform mapping was correct.
- Why later behavior was unreliable.
- Whether mode changes were only being persisted.
- Whether the sensor-watch path applied transforms.
- Whether systemd was running a persistent daemon.
- Whether touch mapping was missing or duplicated.
- Whether build integration omitted required components.
- How VNC and XRDP previously handled geometry.

Back every conclusion with source, log or device evidence.

## 23.2 Source changes

Provide:

- Every modified file.
- Every new file.
- Reason for each change.
- Any removed or replaced code.
- Compatibility/migration notes.

Avoid unrelated refactoring.

## 23.3 Tests

Provide:

- Automated test results.
- Policy matrix results.
- Transform backend tests.
- Rollback tests.
- Bridge/UI tests.
- Sensor probe results.
- Physical display results.
- Touchscreen results.
- VNC results.
- XRDP results.

Clearly mark tests that could not be performed on actual hardware.

## 23.4 Deployment package

Provide:

- The complete patched source or drop-in replacement package.
- Correct device-image integration.
- Deployment instructions.
- Rollback instructions.
- Required service commands.
- Post-deployment verification commands.

The deliverable must not be a collection of isolated snippets that the owner has to guess how to integrate.

## 23.5 Evidence

Include useful logs or screenshots demonstrating:

- All four physical display orientations.
- Touch working in each orientation.
- Auto behavior with real sensor readings.
- Connected VNC synchronization.
- Connected XRDP synchronization.
- New remote sessions inheriting current orientation.
- Successful rollback behavior.

Do not fabricate screenshots, sensor readings or client test results.

---

# 24. Definition of done

The task is complete only when the following are true.

### Local orientation

- [ ] Auto (FULL) is present.
- [ ] Auto (PT) is present.
- [ ] Auto (LS) is present.
- [ ] Locked (PT) is present.
- [ ] Locked (LS) is present.
- [ ] Locked (RPT) is present.
- [ ] Locked (RLS) is present.
- [ ] All seven modes use the correct stable keys.
- [ ] All four fixed orientations physically work.
- [ ] The previous successful transform mapping has been recovered or conclusively replaced by a verified mapping.
- [ ] The display geometry matches the actual orientation.
- [ ] The framebuffer bridge continues working.
- [ ] Touch works in all four orientations.
- [ ] No second framebuffer writer exists.

### Automatic orientation

- [ ] Auto FULL uses real sensor readings.
- [ ] Auto PT cannot enter landscape.
- [ ] Auto LS cannot enter portrait.
- [ ] Sensor stability and hysteresis prevent jitter.
- [ ] Flat and invalid readings retain the last good orientation.
- [ ] Locked modes ignore sensor events.
- [ ] Missing sensor hardware is reported honestly.

### Reliability

- [ ] One persistent orientation authority exists.
- [ ] A selected mode actually triggers an apply transaction.
- [ ] State is updated only after verification.
- [ ] Failed transitions roll back locally.
- [ ] Rollback does not depend on SSH.
- [ ] Daemon restart is safe.
- [ ] Reboot restores the saved policy.

### VNC

- [ ] VNC mirrors the actual Phoc session.
- [ ] Connected clients receive updated geometry where supported.
- [ ] Remote pointer mapping follows the display.
- [ ] Unsupported client resizing uses a safe fallback.
- [ ] Reconnected clients inherit current orientation.
- [ ] VNC failure cannot break local rotation.

### XRDP

- [ ] Active sessions receive orientation updates.
- [ ] Virtual geometry follows orientation where supported.
- [ ] Reverse orientations are handled correctly or have a documented verified fallback.
- [ ] Pointer mapping remains correct.
- [ ] Applications remain open.
- [ ] Sessions are not logged out or restarted for rotation.
- [ ] Reconnected sessions inherit current orientation.
- [ ] Each session reports its actual synchronization capability and status.

### Integration

- [ ] Quick Settings shows all seven modes.
- [ ] Settings shows all seven modes.
- [ ] UI selected policy and applied orientation remain distinct.
- [ ] Build and image packaging include the correct code.
- [ ] The running phone is verified to use the patched implementation.
- [ ] Documentation reflects actual device results.
- [ ] Wi-Fi SSH deployment and rollback instructions are complete.

---

# 25. Final instruction to the implementation agent

Do not turn this into a broad Nuxel display rewrite.

Do not replace working pieces merely because a different approach looks cleaner.

**The first job is to find the rotations that already worked.**

Then repair the complete chain around that working mechanism:

`mode selection → policy → real output transform → logical geometry → touch mapping → framebuffer presentation → orientation event → VNC/XRDP update`

Keep all seven modes.

Keep one authority.

Keep the phone recoverable.

Make the remote sessions follow the phone.

Do not confuse a saved preference, a successful command exit code or a simulated sensor sample with an actually working rotation.

The final result must be demonstrated on the real S10+ wherever hardware testing is required. Where testing cannot be performed, state that limitation clearly rather than inventing a successful result.

**PWNAGE-54000 is finished only when Nuxel rotates correctly, remains touch-usable, and its connected remote desktop sessions follow the new orientation without losing their sessions.**

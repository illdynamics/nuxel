# full-pwnage-101000.md
# NUXEL — EXTERNAL HDMI COLOUR CORRECTION, AUTOMATIC ORIENTATION AND HOT-PLUG RECONNECTION RECOVERY

**Project:** Nuxel  
**Repository:** `~/x/nuxel`  
**Target device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**SoC:** Exynos 9820  
**External output:** USB-C DisplayPort Alt Mode → HDMI adapter → TV  
**Previous milestone:** PWNAGE-100000 — physical external display output achieved  
**Priority:** High  
**Execution:** Inspect → Capture → Diagnose → Implement → Test → Deploy → Physically Verify

---

# 0. Executive mission

The S10+ running Nuxel has successfully produced a real picture on an external display using USB-C-to-HDMI.

The user supplied a photograph showing the Nuxel desktop, application icons and a live terminal window on the external screen.

This is a major breakthrough. The physical output path has worked.

However, three defects must now be fixed:

1. The external image has an obvious red/orange colour cast.
2. Landscape mode and phone rotation are not being handled correctly.
3. After disconnecting and reconnecting the USB-C-to-HDMI adapter, the external display disappears and does not automatically return.

This prompt is specifically about completing and stabilising that existing implementation.

**Do not treat this as a new HDMI bring-up project. Do not destroy the working external display path to solve these defects.**

The intended final result is:

- Accurate external colours.
- Correct orientation-aware mirroring.
- Proper landscape handling.
- Automatic rotation updates.
- Reliable USB-C/HDMI hot-plug recovery.
- Automatic external output restoration after reconnection.
- No reboot or manual daemon restart required.

All three areas must be investigated, implemented and independently verified.

---

# 1. Existing implementation: preserve first, modify second

Read the prior PWNAGE reports and inspect the actual code before making changes.

At minimum inspect:

- `REPORT-PWNAGE-99000.md`
- `REPORT-PWNAGE-100000.md`, if available.
- `REPORT-PWNAGE-101000.md`, if an earlier version exists.
- All relevant `REPORT-*.md` files.
- Previous PWNAGE implementation prompts if present.
- Current display manager implementation.
- External framebuffer bridge.
- Notification hub integration.
- Rotation and sensor services.
- Compositor configuration.
- Current deployment scripts.

The previous work reportedly introduced:

- `nuxel-displayd`
- `nuxel-display-ctl`
- `nuxel-wl-fb-ext`
- Wayland screencopy to `/dev/fb1`.
- Aspect-preserving scaling and letterboxing.
- ABGR conversion.
- Rotation support.
- Frame pacing.
- `fb1` ownership locking.
- Mirror and Separate desktop settings.
- HDMI connection notifications.
- Reconnect generation tracking.
- External audio integration.

Verify what is actually present and running. Do not assume the previous report describes the current working tree or live device perfectly.

## 1.1 Initial live-state capture

Connect to the S10+ using the supplied SSH access, if still valid:

```bash
ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167
```

Preserve host-key verification. Never expose the private key.

Identify the actual device and running software:

```bash
uname -a
cat /proc/version
cat /etc/os-release
cat /proc/cmdline
```

Record:

- Current branch and commit.
- Working-tree changes.
- Current running kernel.
- External display state.
- USB-C partner state.
- DP Alt Mode state.
- Current EDID and display mode if available.
- Framebuffer dimensions and formats.
- Internal AMOLED state.
- Orientation state.
- Current sensor service.
- Display manager state.
- External bridge process and service state.
- Audio endpoint state.
- Current CPU and memory usage.

Save evidence under:

```text
evidence/pwnage-101000/initial/
```

Do not overwrite previous evidence.

## 1.2 Preserve the working output

The first visible HDMI result must be retained as a regression baseline.

Do not:

- Disable the current working DP Alt Mode implementation.
- Rework the entire CCIC/PD negotiation path without a concrete reason.
- Replace the compositor.
- Change internal AMOLED resolution or DPI.
- Stop the internal framebuffer bridge.
- Introduce a second `/dev/fb0` writer.
- Force software rendering.
- Reflash the kernel or DTB as an initial troubleshooting step.
- Add a dummy HDMI audio sink.
- Treat `fb1` writes as proof of physical output.

The normal approach for this task should be a focused userspace and bridge repair.

If a kernel or device-tree defect is actually proven, document it and follow the separate safety and recovery requirements before making any boot-chain changes.

---

# 2. Architecture and ownership audit

Before altering the colour, rotation or reconnect paths, understand the complete active architecture.

Trace:

```text
Phone display / compositor
        |
        v
Wayland output and screencopy
        |
        v
nuxel-wl-fb-ext
        |
        v
Scaling / rotation / colour conversion
        |
        v
External framebuffer or output target
        |
        v
Display controller / DP output
        |
        v
USB-C DisplayPort Alt Mode
        |
        v
HDMI adapter
        |
        v
TV
```

The diagram is a conceptual starting point. Replace it with the actual implementation and identify every interface and owner.

Also inspect the hardware event path:

```text
USB-C connector
        |
        v
CCIC / PDIC / Type-C controller
        |
        v
USB-PD / VDM / DP Alt Mode
        |
        v
Mux / lane assignment / PHY
        |
        v
HPD / AUX / EDID / link
        |
        v
External output availability
        |
        v
Display manager
        |
        v
External framebuffer bridge
```

Identify:

- Which service owns Type-C discovery.
- Which component receives USB-C events.
- Which component owns DP state.
- Which component owns the external framebuffer.
- Which component owns output rotation.
- Which component owns mirror mode.
- Which service owns sensor orientation.
- Which component controls HDMI audio routing.
- Which component emits connection notifications.

Do not create duplicate controllers for functionality already implemented elsewhere.

Each state and resource should have a clearly defined owner.

---

# PART A — COLOUR PIPELINE REPAIR

# 3. Colour problem and investigation hypotheses

The user-provided photograph shows the external output with a pronounced red/orange tint.

The image still contains recognisable cyan and green elements, suggesting that at least part of the image and colour information reaches the TV.

The exact root cause is unknown.

Investigate these possibilities without assuming any one of them:

- RGBA/BGRA/ARGB/ABGR channel mismatch.
- Incorrect byte order.
- Incorrect framebuffer bitfields.
- Incorrect bits per pixel.
- Incorrect bytes per pixel.
- Incorrect source or destination stride.
- Incorrect framebuffer offset.
- Alpha channel being interpreted incorrectly.
- Premultiplied versus straight-alpha mismatch.
- Incorrect RGB range.
- RGB versus YCbCr mismatch.
- Incorrect colour-space conversion.
- Display-controller pixel-format configuration.
- Gamma or colour transformation.
- A display-service colour adjustment.
- A source rendering problem.
- TV input picture processing.

The photograph is evidence of the visible problem, not proof of a particular channel-order fault.

Do not apply a broad colour correction to disguise the problem.

---

# 4. Determine precisely where colour becomes incorrect

Capture the same known frame at every observable stage of the pipeline.

At minimum compare:

1. Original internal desktop appearance.
2. Wayland screencopy buffer.
3. Bridge input buffer.
4. Bridge converted buffer.
5. Bytes submitted to the external framebuffer.
6. Physical TV output.

Identify the first stage where expected colour values become incorrect.

Save evidence under:

```text
evidence/pwnage-101000/source-format/
evidence/pwnage-101000/framebuffer-format/
evidence/pwnage-101000/raw-pixels/
```

## 4.1 Wayland source format

Inspect the real negotiated source format.

Determine:

- Wayland format identifier.
- SHM or DMA-BUF transport.
- Width.
- Height.
- Stride.
- Bytes per pixel.
- Channel order.
- Alpha presence.
- Alpha semantics.
- Endianness.
- Any compositor colour transformation already applied.

Do not infer the format from names in source code.

Use the actual format supplied by the protocol or buffer metadata.

## 4.2 Destination format

Inspect the actual external output framebuffer or hardware output format.

If `/dev/fb1` remains the real target, collect:

- `fb_var_screeninfo`
- `fb_fix_screeninfo`
- Resolution.
- Virtual resolution.
- Bits per pixel.
- Line length.
- Memory length.
- Red offset, length and `msb_right`.
- Green offset, length and `msb_right`.
- Blue offset, length and `msb_right`.
- Transparency offset, length and `msb_right`.
- Visual type.
- Acceleration information.

Inspect the current device through framebuffer ioctls, not just guessed sysfs attributes.

Useful commands:

```bash
cat /sys/class/graphics/fb1/name 2>/dev/null
cat /sys/class/graphics/fb1/bits_per_pixel 2>/dev/null
cat /sys/class/graphics/fb1/virtual_size 2>/dev/null
cat /sys/class/graphics/fb1/stride 2>/dev/null
```

If the output target is not `fb1` in the current implementation, identify the actual target and inspect its format instead.

## 4.3 Format matrix

Create an evidence-backed comparison:

| Property | Wayland input | External output | Required operation |
|---|---|---|---|
| Format identifier | | | |
| Bits per pixel | | | |
| Bytes per pixel | | | |
| Red offset/length | | | |
| Green offset/length | | | |
| Blue offset/length | | | |
| Alpha offset/length | | | |
| Stride | | | |
| Endianness | | | |
| Alpha model | | | |
| Colour range | | | |

Do not leave fields blank when the information can be obtained.

Explicitly mark unavailable data as unavailable.

---

# 5. Correct pixel conversion

Implement a single well-defined pixel conversion layer.

Do not accumulate ad hoc swaps throughout the bridge.

The conversion layer should use explicit metadata for:

- Source format.
- Source dimensions.
- Source stride.
- Destination bitfields.
- Destination dimensions.
- Destination stride.
- Destination bytes per pixel.
- Alpha semantics.
- Scaling.
- Rotation.

Support only formats that the implementation actually needs and tests.

Potential formats to investigate include:

- `WL_SHM_FORMAT_ARGB8888`
- `WL_SHM_FORMAT_XRGB8888`
- `WL_SHM_FORMAT_ABGR8888`
- `WL_SHM_FORMAT_XBGR8888`
- `WL_SHM_FORMAT_RGBA8888`
- `WL_SHM_FORMAT_BGRA8888`
- RGB565

Do not claim all are supported unless they are actually implemented.

## 5.1 Destination channel packing

Derive the output from the real framebuffer bitfields.

The conversion must:

1. Decode source logical colour channels.
2. Apply correct alpha handling.
3. Scale channel precision.
4. Pack into destination channel offsets.
5. Respect channel lengths.
6. Respect `msb_right` when applicable.
7. Respect endianness.
8. Respect destination bytes per pixel.
9. Respect both source and destination stride.
10. Stay within the allocated output memory.

No hardcoded assumption that all output is 32-bit ABGR.

## 5.2 Alpha correctness

Determine whether the source uses premultiplied or straight alpha.

If the destination has no alpha channel:

- Composite against the correct intended background.
- Do not accidentally treat alpha as a colour channel.
- Do not multiply RGB by alpha twice.
- Handle alpha zero safely.
- Avoid uninitialised transparency data.

## 5.3 Colour-space investigation

Only after raw pixel bytes and channel mapping are confirmed correct, investigate:

- RGB versus YCbCr.
- Full versus limited range.
- BT.601/BT.709 where applicable.
- HDMI AVI InfoFrame colour-format information.
- Gamma.
- LUTs.
- Display-controller colour processing.
- HDR/SDR state.
- HDMI output quantisation range.

Do not introduce an arbitrary red/blue filter, gamma compensation or colour overlay.

---

# PART B — PHONE ROTATION, LANDSCAPE MODE AND EXTERNAL ORIENTATION

# 6. Orientation is a full pipeline feature

The user wants the external display to respect the actual rotation of the phone.

The implementation must respond correctly when the phone changes between:

- Portrait.
- Landscape left.
- Landscape right.
- Returning to portrait.

This must work while HDMI is already connected and while the phone is being used normally.

It must also work when the adapter reconnects while the phone is already in landscape.

Do not treat rotation as a static setting or a one-time framebuffer transformation.

The bridge must receive current orientation and dimensions, handle transitions, and recover correctly if buffers are reallocated.

## 6.1 Investigate the existing orientation source

Find the authoritative source of orientation in Nuxel.

Inspect:

- Accelerometer service.
- Rotation-vector/orientation logic, if present.
- Sensor manager.
- Display orientation service.
- Compositor output transform.
- Internal output dimensions.
- Surface rotation.
- Window-system orientation.
- Current rotation settings.
- Manual rotation override.
- Automatic rotation enable/disable preference.

Do not create a second competing sensor-orientation system.

Determine which service actually decides that the phone is portrait or landscape.

Trace the state from sensor input to the compositor's visible output.

Capture the current state before changing anything.

## 6.2 Orientation state model

Implement a single authoritative orientation state with enough information to distinguish:

- `PORTRAIT`
- `LANDSCAPE_LEFT`
- `LANDSCAPE_RIGHT`
- `PORTRAIT_UPSIDE_DOWN`, if supported by the device and current policy
- `UNKNOWN`

Do not claim support for upside-down orientation unless the active hardware and compositor can reliably represent it.

Record:

- Current physical orientation.
- Current compositor orientation.
- Current logical UI dimensions.
- Current physical internal output dimensions.
- Current external output dimensions.
- Current external transform.
- Whether automatic rotation is enabled.
- Whether a manual override is active.

Avoid multiple services independently making rotation decisions.

## 6.3 Mirror-mode orientation policy

For Mirror mode, the external screen must faithfully present the current Nuxel UI orientation.

The desired behavior is:

- When the phone is portrait, the logical source content is portrait.
- When the phone rotates to landscape, the logical source content transitions to landscape.
- When the phone rotates back, the output transitions back correctly.
- The external image remains properly composed for the physical TV.
- The output is not stretched or squeezed.
- Text and icons are not sideways.
- The external image does not remain stuck in an old orientation.

**Important distinction:** The TV's physical output timing and mode are not the same thing as the phone's logical UI orientation.

A conventional TV normally remains physically landscape. The system should render a correctly oriented landscape composition onto that screen when the phone's UI enters landscape.

Do not blindly rotate the entire HDMI signal or TV mode by 90 degrees simply because the phone rotates.

Determine whether the compositor already performs the correct source layout transformation. The bridge must follow the compositor's actual output and not apply a second conflicting rotation.

If the source image is portrait and must be mapped onto a landscape external mode, use a deliberate, well-defined layout and scaling policy. Never distort aspect ratio to fill the TV.

Document the chosen behavior and make sure it corresponds to the actual Nuxel compositor and mirroring architecture.

## 6.4 Separate desktop orientation policy

Separate desktop mode is distinct from mirroring.

If the active compositor supports a genuine second desktop output:

- Use the external display's real preferred mode.
- Normally use the TV's natural landscape mode.
- Keep the desktop layout independently appropriate for that screen.
- Do not blindly inherit the phone's physical rotation for the external desktop.
- Keep internal orientation and external desktop layout independent where possible.

If Phoc or the active compositor cannot provide a genuine second output, retain the honest existing limitation.

Do not simulate a second display by claiming that a copied framebuffer is a separate compositor output.

## 6.5 Transform correctness

Inspect the actual transform pipeline:

```text
Sensor orientation
        |
        v
Nuxel orientation authority
        |
        v
Compositor output transform/layout
        |
        v
Wayland source buffer dimensions
        |
        v
External bridge transform
        |
        v
Scaling / cropping / letterboxing
        |
        v
Destination framebuffer
```

Identify which stage owns rotation.

Ensure rotation is applied exactly once.

Avoid:

- Double rotation.
- Rotation applied after using stale width/height.
- Landscape dimensions paired with portrait stride.
- Old framebuffer mappings used after a mode change.
- Scaling against pre-rotation dimensions.
- Incorrect letterboxing after rotation.
- Input or pointer transforms being changed unnecessarily.
- Applying manual rotation on top of automatic rotation without explicit semantics.

## 6.6 Dynamic buffer and output reconfiguration

On orientation change, the bridge must determine whether:

- The source dimensions changed.
- The source buffer was reallocated.
- The source stride changed.
- The output dimensions changed.
- The framebuffer was reconfigured.
- Rotation can be handled in the existing buffer.
- The compositor requires a fresh screencopy object or output configuration.

Handle all necessary reconfiguration safely.

Do not continue using stale buffer dimensions or mappings.

Perform atomic or carefully synchronised updates so an orientation transition cannot expose a half-updated frame.

## 6.7 Orientation transition behaviour

Test:

1. Start in portrait with HDMI connected.
2. Rotate to landscape left.
3. Verify the external desktop updates.
4. Rotate to landscape right.
5. Verify the external desktop updates correctly.
6. Return to portrait.
7. Verify restoration.
8. Repeat with applications open.
9. Repeat during scrolling and animation.
10. Repeat while moving windows.
11. Repeat while the display connection is being renegotiated.
12. Disconnect and reconnect while already in landscape.
13. Confirm the external output restores directly in landscape.

If a rotation lock is enabled, respect it. Do not override user settings.

If the accelerometer or orientation is unavailable, report the state as unknown and retain the last valid orientation or existing system policy. Do not invent orientation data.

---

# PART C — USB-C / HDMI HOT-PLUG AND RECONNECTION RECOVERY

# 7. The reconnect failure

The user reports:

> When we reconnect the USB-C-to-HDMI adapter, we have no display anymore.

This must be fixed.

The display must return automatically after reconnection, without rebooting the phone or manually restarting a service.

A reconnect must cause Nuxel to rebuild the external-output lifecycle from fresh hardware state.

Do not simply preserve a stale connected flag.

Do not assume that the original framebuffer mapping, EDID, output mode, DRM/FB device, HPD state or bridge file descriptor remains valid after a physical disconnect.

## 7.1 Reconstruct the current failure

Inspect the actual reconnect code and state transitions.

Determine:

- What detects initial Type-C attach?
- What detects Type-C detach?
- What detects partner replacement?
- What detects DP Alt Mode exit?
- What detects DP Alt Mode re-entry?
- What detects HPD low/high?
- What detects AUX failure?
- What detects the display link disappearing?
- What detects a new EDID?
- What tells the display manager to reinitialise?
- What tells the bridge that old resources are invalid?
- What reopens or reconfigures the framebuffer?
- What restores the selected output mode?
- What restarts the capture path?
- What restores rotation?
- What restores audio routing?

Inspect whether the existing reconnect generation counter is actually driving resource reinitialisation or merely changing notification identifiers.

A generation increment without a complete output recovery is insufficient.

## 7.2 Separate connection layers

Implement a truthful state machine that distinguishes the following layers:

### Layer 1: Type-C partner

- Partner absent.
- Partner attached.
- Partner removed.
- Partner identity changed.

### Layer 2: USB-PD and Alt Mode

- PD negotiation pending.
- PD communication available.
- DP SVID discovery pending.
- DP Alt Mode entered.
- DP mode exited.
- DP configuration failed.

### Layer 3: Physical DP link

- Mux configuration pending.
- PHY initialisation pending.
- HPD low.
- HPD high.
- AUX unavailable.
- EDID unavailable.
- Link training pending.
- Link established.
- Link lost.

### Layer 4: External display output

- Connector detected.
- Output device available.
- Mode discovered.
- Framebuffer/output target ready.
- Bridge attached.
- Frames flowing.
- Display active.

### Layer 5: Nuxel presentation

- Mirror requested.
- Mirror active.
- Separate desktop requested.
- Separate desktop active.
- Output suspended.
- Reconnecting.
- Recovered.

Use names appropriate to the existing architecture, but preserve the distinctions.

Do not report `DP_LINK_READY` or `DISPLAY_READY` until the necessary physical and software conditions are established.

## 7.3 Event-driven detection

Identify the most reliable available hardware event sources.

Investigate:

- Type-C class notifications.
- Kernel uevents.
- Netlink/udev events.
- extcon state changes.
- DRM hot-plug events, if available.
- Framebuffer events, if available.
- Samsung CCIC/PDIC event interfaces.
- DP Alt Mode state changes.
- HPD interrupts.
- EDID changes.
- PHY and mux state.
- Existing vendor notification mechanisms.

Use the correct source for each layer.

Do not make polling the primary detection method if reliable event delivery exists.

If event delivery is incomplete on this kernel, use a bounded reconciliation mechanism as a fallback.

The fallback must:

- Be low frequency.
- Use existing state interfaces.
- Avoid reading hardware registers directly.
- Avoid causing negotiation.
- Avoid CPU-intensive loops.
- Detect missed events.
- Reconcile actual hardware state with daemon state.

## 7.4 Debouncing and event coalescing

USB-C and DP transitions can involve multiple closely spaced events.

Implement controlled debouncing and event coalescing.

Requirements:

- Ignore duplicate events that do not represent a new state.
- Do not collapse meaningful detach/re-attach transitions.
- Do not report repeated notifications during negotiation.
- Do not treat transient intermediate states as stable.
- Do not wait so long that a real reconnect appears broken.
- Preserve the most recent genuine connection generation.

Avoid arbitrary fixed delays as a substitute for hardware readiness.

Use actual state transitions to decide when to advance.

## 7.5 Reconnection generation and stale-state invalidation

The existing implementation reportedly has connection generations.

Inspect how these are used.

Every genuine physical detach/reattach cycle must invalidate stale external-output resources.

Use a connection epoch or equivalent generation identity to prevent asynchronous operations from an older connection from corrupting the new one.

On detach:

- Invalidate the old connection generation.
- Mark the external output unavailable.
- Stop new frame submissions.
- Stop or quiesce the external bridge safely.
- Release stale capture buffers.
- Close obsolete file descriptors.
- Unmap obsolete framebuffer mappings.
- Invalidate old EDID and mode information.
- Remove or disable stale audio routing.
- Clear stale output readiness.
- Preserve the internal display.
- Archive or update the notification correctly.

On reattach:

- Create a new connection generation.
- Detect the current partner.
- Observe actual PD/DP negotiation.
- Wait for a real DP output.
- Re-read the actual display identity and EDID.
- Re-enumerate output modes.
- Reopen the actual output target.
- Query framebuffer format and dimensions again.
- Reallocate buffers where necessary.
- Reinitialise or restart the external bridge safely.
- Apply current orientation.
- Restore the selected display mode.
- Re-enable mirror mode if the user's preference permits.
- Recreate HDMI audio routing only if a real audio endpoint exists.
- Update connection notification state.

Never allow old-generation frame callbacks or asynchronous completion events to update a new connection.

## 7.6 External bridge lifecycle

Investigate `nuxel-wl-fb-ext` or its current equivalent.

Determine whether it holds any resources that become invalid during a disconnect:

- Framebuffer file descriptor.
- Memory mapping.
- Wayland display connection.
- Wayland screencopy object.
- Buffer pool.
- Frame callbacks.
- Output dimensions.
- Pixel format.
- Stride.
- Rotation state.
- Scaling state.
- Connection-specific service handles.
- DP output identity.

The bridge must recover from a connection reset.

Do not simply keep writing to an old file descriptor and hope the hardware returns.

Implement an explicit lifecycle such as:

```text
STOPPED
  |
  v
WAITING_FOR_OUTPUT
  |
  v
OPENING_OUTPUT
  |
  v
QUERYING_FORMAT
  |
  v
ALLOCATING_BUFFERS
  |
  v
ATTACHING_CAPTURE
  |
  v
STREAMING
  |
  +---- output lost ----> QUIESCING
                              |
                              v
                       RELEASING_RESOURCES
                              |
                              v
                       WAITING_FOR_OUTPUT
```

Adapt the exact state names to the actual service, but implement the lifecycle and ownership.

## 7.7 Recover without a full phone reboot

The normal reconnection path must not require:

- Rebooting Nuxel.
- Restarting the entire compositor.
- Restarting all display services.
- Killing the Wayland session.
- Recreating the internal display bridge.
- Manually restarting the external bridge from SSH.

A targeted reinitialisation of the relevant external-output components is acceptable when needed.

If a controller-level event requires kernel-side recovery, use the driver's supported path. Do not force undocumented register writes.

If a service restart is required, make it a controlled and automatic recovery action with clear ownership and bounded retry.

---

# 8. DP link recovery and display rediscovery

The reconnect lifecycle must account for the real USB-C-to-DP path.

Preserve the working PWNAGE-100000 negotiation implementation.

On a genuine detach:

- Observe the actual Type-C partner removal.
- Observe the DP state leaving its active mode.
- Observe HPD/link loss.
- Invalidate external output state.

On a genuine reattach:

- Observe CC attach and orientation.
- Follow real USB-PD/VDM negotiation.
- Detect DP Alt Mode entry.
- Confirm the correct pin assignment.
- Confirm the mux state.
- Confirm PHY activation.
- Confirm valid HPD.
- Confirm AUX communication.
- Re-read actual EDID.
- Confirm link training and output availability.

Do not fake any of these steps.

A forced HPD signal must not be used as a normal reconnect mechanism.

Do not force an Alt Mode transition by writing undocumented sysfs values.

The proper recovery path must use the existing Samsung controller and driver state machine.

If the hardware driver itself becomes stuck after detach, identify precisely where and repair the driver's legitimate recovery or reset sequence.

Do not change a working initial attach path unless the new fix requires it and the regression tests cover both initial attach and reconnection.

---

# 9. Reconnection and orientation integration

These features must work together.

A common failure scenario is:

1. Phone in portrait.
2. HDMI connected.
3. External output works.
4. Phone rotates to landscape.
5. User disconnects the adapter.
6. User reconnects the adapter.
7. External display returns in the wrong orientation or not at all.

The implementation must recover from this exact sequence.

The reconnect process must re-read the current phone orientation.

It must not restore stale orientation captured during the previous connection generation.

Similarly, if a disconnect happens while a rotation change is being processed, stale callbacks must not corrupt the new connection.

On each new connection generation:

- Query current phone orientation.
- Query current compositor source dimensions.
- Query actual external mode.
- Query current output transform.
- Recompute scaling and letterboxing.
- Rebuild buffers using current format and dimensions.
- Apply the current mirror/separate policy.
- Resume streaming only after valid resources are established.

---

# PART D — USER EXPERIENCE AND SETTINGS

# 10. Connection notification

Preserve the current canonical Nuxel notification flow.

On successful external display detection, offer:

- Mirror.
- Separate desktop, only if genuinely supported.

During reconnection:

- Avoid repeated notification spam.
- Show a reconnecting indication when appropriate.
- Do not say the display is ready before the external output exists.
- Update the notification as the connection progresses.
- Archive or update previous notifications according to the existing notification model.
- Do not show stale display identity after a new partner is detected.

On disconnect, update the display state and release the previous external-output resources.

## 10.1 Display settings

Inspect the existing display settings UI.

Provide accurate state for:

- Internal only.
- Mirror.
- Separate desktop, if supported.
- Connected external display identity.
- Current external mode.
- Phone orientation.
- Current external presentation orientation.
- Automatic orientation.
- Manual rotation override.
- HDMI audio availability.

Avoid adding duplicate rotation controls if a canonical Nuxel orientation setting already exists.

A manual rotation option may remain available for troubleshooting, but automatic orientation must be the normal functional path.

The UI must expose actual state, not an assumed or cached state.

---

# PART E — IMPLEMENTATION AND TESTING

# 11. Implementation requirements

Make focused changes.

Do not rewrite unrelated display infrastructure.

Every change must have:

- A demonstrated failure mode.
- A clear owning component.
- A source-level explanation.
- A test.
- A rollback path.

Prioritise:

1. Exact colour conversion.
2. Authoritative orientation integration.
3. External bridge dynamic reconfiguration.
4. Complete hot-plug detection.
5. Reconnection state recovery.
6. UI and notification correctness.
7. Audio endpoint lifecycle.
8. Performance and stability.

Do not leave placeholder TODOs for the central requirements.

Do not stop at a proposed architecture if the relevant code is accessible and can be implemented.

---

# 12. Colour test suite

Create deterministic conversion tests.

Test every supported source/destination format combination.

At minimum:

| Colour | Expected RGB |
|---|---|
| Black | 0, 0, 0 |
| White | 255, 255, 255 |
| Red | 255, 0, 0 |
| Green | 0, 255, 0 |
| Blue | 0, 0, 255 |
| Cyan | 0, 255, 255 |
| Magenta | 255, 0, 255 |
| Yellow | 255, 255, 0 |
| Mid-grey | 128, 128, 128 |

Also test:

- Dark and light grey.
- RGB gradients.
- Alpha values.
- Premultiplied alpha.
- Straight alpha.
- No-alpha destinations.
- Padded stride.
- Different bytes-per-pixel.
- RGB565 if used.
- Bitfield layouts.
- Endianness.
- `msb_right` where applicable.

For each test record:

- Input logical RGB.
- Input source bytes.
- Converted bytes.
- Expected packed destination value.
- Actual decoded destination colour.

Check buffer bounds.

No out-of-range memory writes.

---

# 13. Orientation test suite

Test the entire orientation pipeline.

## 13.1 Portrait baseline

With HDMI connected:

- Start Nuxel in portrait.
- Confirm internal display orientation.
- Confirm external output orientation.
- Confirm image proportions.
- Confirm no sideways UI.
- Confirm application layout is correct.

## 13.2 Landscape left

Rotate the actual phone to landscape left.

Verify:

- Sensor/orientation state changes.
- Nuxel orientation authority reports landscape left.
- Compositor layout updates.
- Source screencopy dimensions or transform are updated.
- External buffer dimensions are recalculated.
- Output remains correctly oriented on the TV.
- Application windows and desktop are correctly laid out.
- Aspect ratio is preserved.
- No previous portrait buffer is reused incorrectly.

## 13.3 Landscape right

Repeat for landscape right.

Confirm the correct directional transform.

## 13.4 Return to portrait

Rotate back.

Verify complete restoration.

## 13.5 Reconnect while landscape

This test is mandatory:

1. Start in portrait.
2. Connect HDMI.
3. Confirm picture.
4. Rotate to landscape.
5. Confirm picture.
6. Disconnect the adapter.
7. Keep the phone in landscape.
8. Reconnect the adapter.
9. Confirm the external output comes back.
10. Confirm it uses the current landscape orientation.
11. Rotate back to portrait.
12. Confirm the picture updates again.

## 13.6 Applications

Repeat orientation tests with:

- Nuxel desktop.
- Terminal.
- Browser or another graphical application.
- A fullscreen application.
- A scrolling view.
- A moving/resizing window.

Do not fix desktop orientation while leaving fullscreen applications broken.

---

# 14. Hot-plug test suite

Test the complete adapter lifecycle.

## 14.1 Initial attach

- Attach the adapter.
- Observe Type-C.
- Observe PD/DP negotiation.
- Confirm actual external output.
- Confirm EDID/mode.
- Confirm bridge streaming.
- Confirm TV picture.

## 14.2 First disconnect

- Disconnect the adapter.
- Confirm the external display is marked unavailable.
- Confirm the bridge stops writing to stale resources.
- Confirm resources are released.
- Confirm the internal AMOLED remains normal.
- Confirm audio routing is cleaned up.
- Confirm notifications are correct.

## 14.3 First reconnect

- Reconnect the same adapter.
- Observe a new connection generation.
- Confirm hardware negotiation restarts.
- Confirm output is rediscovered.
- Confirm the framebuffer/target is reopened.
- Confirm source capture restarts.
- Confirm orientation is reapplied.
- Confirm the TV picture returns.

## 14.4 Repeated cycles

Perform at least five complete disconnect/reconnect cycles, provided the physical setup remains stable.

For each cycle record:

- Attach detection.
- Negotiation.
- DP state.
- HPD.
- EDID.
- Output mode.
- Framebuffer state.
- Bridge state.
- Orientation.
- Physical picture restored.
- Recovery time measured from actual attach to first visible frame.

Do not invent recovery times. Measure them.

## 14.5 HDMI cable and TV input changes

Where practical, investigate and test separately:

- USB-C adapter unplugged from phone.
- HDMI cable unplugged from adapter.
- HDMI cable unplugged from TV.
- TV switched to another input and back.
- TV powered off and back on.

Distinguish these cases. Not every TV power/input event requires USB-C Alt Mode renegotiation.

Do not make the user perform unnecessary physical operations. The adapter disconnect/reconnect test is the required primary test.

---

# 15. Automated recovery and fault injection

Add tests for the state machine using simulated hardware events.

Test:

- Duplicate attach.
- Duplicate detach.
- Attach followed quickly by detach.
- Detach during mode discovery.
- Detach during EDID read.
- Detach during bridge initialisation.
- Detach during active streaming.
- Reattach before old teardown completes.
- Late old-generation callback.
- Missing event followed by state reconciliation.
- PHY readiness timeout.
- EDID failure.
- Bridge open failure.
- Framebuffer dimension change.
- Orientation change during reconnect.
- Service crash during reconnect.
- Service restart while output remains physically connected.

Verify that old-generation events cannot mark the new connection ready.

The system must have bounded retries and a clear recovery error state.

Do not let repeated failures produce an infinite restart loop or flood logs.

---

# 16. HDMI audio lifecycle

Preserve the existing real hardware audio path.

On disconnect:

- Remove or disable the actual external audio route.
- Release stale device references.
- Avoid leaving a disconnected HDMI sink selected.
- Restore the normal default audio route.

On reconnect:

- Re-detect the actual DP audio endpoint.
- Re-evaluate capability.
- Recreate the correct PipeWire/WirePlumber route.
- Restore output selection according to the user's policy.
- Avoid dummy devices.

Verify actual sound output through the TV when a real DP audio endpoint is available.

Do not confuse a PCM device listing with verified physical HDMI audio.

---

# 17. Performance and stability

All changes must remain suitable for the Exynos 9820.

Measure:

- CPU consumption.
- Memory usage.
- Frame rate.
- Frame latency.
- Frame drops.
- Conversion time.
- Reconnect processing.
- Retry behavior.
- Service restart counts.
- Log growth.

Avoid:

- Busy polling.
- Tight reconnect loops.
- Reopening file descriptors every frame.
- Reallocating the entire pipeline unnecessarily.
- Full-screen conversions that are not needed.
- Excessive format conversions.
- Duplicate orientation events.
- Unbounded buffer queues.
- Unbounded service retries.
- Large logging output on every frame.

Retain existing frame pacing and damage handling if implemented.

Do not trade accurate colours or reliable recovery for a superficial FPS improvement.

---

# 18. Preserve the internal AMOLED and Nuxel architecture

The internal screen must remain unchanged.

Do not:

- Add a second `/dev/fb0` writer.
- Stop the original internal framebuffer bridge.
- Change the internal display's DPI or resolution.
- Replace Phoc.
- Replace the compositor.
- Force software rendering.
- Introduce llvmpipe.
- Modify internal AMOLED gamma to compensate for external output.
- Alter system-wide theme colours to conceal an output conversion defect.
- Break input or pointer mapping.
- Create a second conflicting orientation manager.

Retain the external output's existing ownership model.

If `/dev/fb1` remains in use, verify its actual mapping and owner before writing.

---

# 19. Deployment procedure

Use the Nuxel deployment scripts in:

```text
./scripts
```

Inspect the relevant deployment script before running it.

Do not blindly execute a script whose behavior has not been understood.

Before deployment:

1. Record the current branch and commit.
2. Record all working-tree changes.
3. Preserve unrelated user modifications.
4. Run the relevant tests.
5. Save the current external bridge executable.
6. Save current service units and configuration.
7. Capture current orientation settings.
8. Create and validate a rollback backup.
9. Deploy only the required files.
10. Restart only the affected services.
11. Keep the internal display and SSH connectivity available.
12. Verify HDMI output immediately after deployment.

Normally this work should be userspace-only.

Do not flash the kernel, DTB, boot image, firmware, modem or bootloader unless a separate, proven kernel-level defect requires it and all recovery gates are satisfied.

If a required kernel change is identified, document it and prepare the reproducible build/recovery package. Do not treat a successful userspace build as proof that a kernel defect has been fixed.

---

# 20. Required evidence

Create:

```text
REPORT-PWNAGE-101000.md
```

Save supporting evidence under:

```text
evidence/pwnage-101000/
```

Use this layout:

```text
evidence/pwnage-101000/
├── initial/
├── architecture/
├── source-format/
├── framebuffer-format/
├── raw-pixels/
├── colour-tests/
├── orientation/
├── rotation-transitions/
├── hotplug/
├── reconnect-cycles/
├── bridge-lifecycle/
├── performance/
├── implementation/
├── deployment/
├── physical-tests/
└── rollback/
```

The report must contain:

## A. Executive summary

- Original symptoms.
- What is now working.
- What failed.
- Root causes.
- Implemented repairs.
- Physical verification result.

## B. Colour pipeline

- Exact Wayland input format.
- Exact destination format.
- Actual framebuffer bitfields.
- Source and destination stride.
- Alpha model.
- Endianness.
- Conversion mathematics.
- Root-cause evidence.
- Colour test results.

## C. Orientation

- Sensor source.
- Orientation authority.
- Compositor behavior.
- External display policy.
- Transform ownership.
- Buffer reconfiguration.
- Portrait and landscape test results.

## D. Hot-plug recovery

- Event sources.
- State-machine implementation.
- Connection generation.
- Old-resource invalidation.
- Bridge recovery.
- EDID and mode rediscovery.
- Retry and timeout policy.
- Reconnect cycle results.
- Measured recovery time.

## E. Integration

- Colour, orientation and reconnect interaction.
- Mirror mode behavior.
- Separate desktop status.
- Audio lifecycle.
- Notification behavior.

## F. Files and code changes

List every changed file, service, setting, test and deployment artifact.

Explain why each change was made.

## G. Verification

For each test, record:

- Test name.
- Method.
- Expected result.
- Actual result.
- Evidence location.
- Status.

Separate:

- Unit tests.
- Integration tests.
- Live software tests.
- Physical hardware tests.

## H. Deployment and rollback

Record:

- Branch.
- Commit.
- Deployment procedure.
- Backup path.
- Rollback command/procedure.
- Current live state.

## I. Remaining blockers

Identify exact remaining blockers, not vague general statements.

---

# 21. Mandatory final acceptance tests

The work is not complete until these combined scenarios have been tested.

### Scenario A — normal colour and portrait

1. Boot Nuxel.
2. Connect USB-C-to-HDMI.
3. Verify the TV displays Nuxel.
4. Show the RGB colour test.
5. Verify accurate red, green and blue.
6. Verify neutral white and greyscale.
7. Show the real Nuxel desktop.
8. Confirm the red/orange cast is gone.

### Scenario B — automatic landscape

1. Keep HDMI connected.
2. Start in portrait.
3. Rotate to landscape.
4. Confirm the external content updates correctly.
5. Rotate the other way.
6. Confirm correct orientation.
7. Return to portrait.
8. Confirm the original layout is restored.
9. Repeat with fullscreen and normal applications.

### Scenario C — disconnect and reconnect

1. Keep Nuxel running.
2. Keep the adapter connected and confirm picture.
3. Disconnect the adapter.
4. Confirm external resources are cleaned up.
5. Reconnect the adapter.
6. Confirm automatic rediscovery.
7. Confirm HDMI output returns.
8. Confirm accurate colours.
9. Confirm current phone orientation is applied.
10. Repeat at least five cycles.

### Scenario D — reconnect while landscape

1. Connect HDMI.
2. Rotate the phone to landscape.
3. Confirm landscape output.
4. Disconnect HDMI.
5. Keep the phone in landscape.
6. Reconnect HDMI.
7. Confirm that output returns automatically.
8. Confirm landscape content is correct.
9. Rotate the phone back to portrait.
10. Confirm the display updates.

This combined scenario is mandatory because it tests whether reconnect recovery uses current orientation rather than stale state.

### Scenario E — internal display regression

Throughout every test:

- Internal AMOLED remains functional.
- No competing `/dev/fb0` writer exists.
- No change to internal colour rendering occurs.
- Nuxel input, pointer and navigation remain functional.
- No compositor replacement occurs.
- No uncontrolled service restart happens.

---

# 22. Final status

Choose exactly one primary status:

- `FULLY_VERIFIED_COLOUR_ORIENTATION_RECONNECT`
- `PARTIALLY_VERIFIED`
- `FIX_IMPLEMENTED_AWAITING_PHYSICAL_TEST`
- `BLOCKED_BY_FRAMEBUFFER_FORMAT`
- `BLOCKED_BY_FRAMEBUFFER_ORIENTATION`
- `BLOCKED_BY_HOTPLUG_DRIVER`
- `BLOCKED_BY_DISPLAY_CONTROLLER`
- `INVESTIGATION_INCONCLUSIVE`

A fully successful result requires:

- Correct physical TV colours.
- Correct portrait/landscape behavior.
- Correct rotation transitions.
- Automatic external display restoration after physical disconnect/reconnect.
- Successful reconnect while already in landscape.
- No regression to the internal screen.

Do not mark success based solely on a unit test, service status, framebuffer write, EDID listing or a single successful initial connection.

---

# 23. Non-negotiable rules

1. Preserve the working HDMI connection.
2. Investigate the actual running implementation.
3. Fix the colour pipeline using real source and destination metadata.
4. Do not blindly swap channels.
5. Do not hide tint with a filter.
6. Integrate with Nuxel's existing orientation authority.
7. Respect phone rotation without blindly rotating the physical TV signal.
8. Correctly reconfigure output buffers and dimensions when orientation changes.
9. Detect physical disconnect and reconnect reliably.
10. Re-establish DP/output state through the actual driver path.
11. Invalidate stale connection resources.
12. Do not rely on manual service restarts or reboots.
13. Reapply the current orientation after reconnect.
14. Preserve internal AMOLED output.
15. Preserve single-writer ownership.
16. Do not fake EDID, HPD, audio or display readiness.
17. Do not introduce unbounded polling or retry loops.
18. Test multiple real reconnect cycles.
19. Physically test the TV output.
20. Document exactly what was verified.

**The milestone is no longer simply getting an HDMI picture. The milestone is making Nuxel's external display genuinely usable: correct colours, proper landscape/portrait behavior, and reliable automatic recovery every time the adapter is reconnected.**

Begin with a live snapshot of the currently working external display and execute the complete task.

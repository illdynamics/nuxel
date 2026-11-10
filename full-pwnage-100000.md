# full-pwnage-100000.md
# NUXEL — Samsung Galaxy S10+ USB-C → HDMI / DisplayPort Alt Mode Root-Cause Investigation and Repair

**Project:** Nuxel  
**Device:** Samsung Galaxy S10+ SM-G975F — `beyond2lte`  
**SoC:** Samsung Exynos 9820  
**Target:** Real USB-C DisplayPort Alt Mode output to an HDMI display  
**Reference:** Google Pixel 10 Pro XL  
**Priority:** Critical  
**Execution mode:** Investigate → Diagnose → Repair → Deploy → Verify  
**Kickstarter:** `pwnage-100000.md`

---

# 0. Executive mission

Fix USB-C-to-HDMI output on the Samsung Galaxy S10+ running Nuxel.

The user will reconnect the USB-C-to-HDMI adapter and leave it connected before executing this prompt. The same TV and HDMI cable have already been tested successfully with a Google Pixel 10 Pro XL.

This is important evidence.

The previous PWNAGE-99000 investigation identified a failure somewhere in the S10+ USB-C/DisplayPort path. It reported:

- `secdp=0`
- `extcon0=DP=0`
- `usbpd_ids=0000:0000`
- `usbpd_type=0`
- `supports_usb_power_delivery=no`
- CCIC state `3` (`PE_SRC_Send_Capabilities`)
- No observed DP Alt Mode activation.
- AUX/DPCD reads failed during a controlled HPD test.
- The combo PHY remained in USB mode (`dp use=0`).

However, the previous investigation's conclusion that the adapter never supplied the required VDM negotiation must now be treated as **unproven until corroborated by raw controller and kernel evidence**.

The user has now confirmed that the same TV and HDMI cable work with the Pixel 10 Pro XL.

This makes the S10+ implementation the primary investigation target.

Your task is to find and fix the actual defect. Do not merely create another display daemon, add more UI controls, simulate a connection, or report that hardware is blocked without exhaustively examining the Samsung-specific implementation.

## Definition of success

<badge>Required physical success</badge>

The S10+ must establish a real external DisplayPort link through its USB-C port and produce a visible picture on the connected TV.

The following are not sufficient:

- A detected Type-C partner.
- A connected HDMI notification.
- A running display manager.
- A framebuffer device.
- Successful writes to `/dev/fb1`.
- A synthetic EDID.
- A forced HPD event.
- A successful AUX test performed with the DP mux in the wrong state.
- A dummy HDMI audio device.
- A successful software-only test.
- A theoretical explanation of what should work.

A real picture must be observed and documented.

---

# 1. Important existing implementation and previous results

Read the previous PWNAGE-99000 implementation and report before making changes.

The previous work reportedly implemented and deployed:

## 1.1 Display manager

- `nuxel-displayd`
- `nuxel-display-ctl`
- Connection-state model:
  - `DISCONNECTED`
  - `PARTNER_NO_PD`
  - `PD_NO_DP`
  - `DP_NO_FB`
  - `DP_LINK_READY`
- Connection notification.
- Disconnect archive.
- Reconnect generation handling.
- Mirror / Separate desktop controls.
- Manual rotation.
- Single-writer external output management.

## 1.2 External framebuffer transport

- `nuxel-wl-fb-ext`
- Wayland screencopy to `/dev/fb1`.
- Aspect-preserving fit and letterboxing.
- ABGR conversion.
- Rotation.
- Frame pacing.
- `fb1` ownership lock.

The previous test reportedly captured and wrote 48 frames to `fb1`, with content in a centered 227×480 region.

That proves a userspace framebuffer transport test was possible. It does not prove the external connector established a real DP link.

## 1.3 Notification and settings integration

- Connection notification.
- Mirror / Separate desktop actions.
- Internal-only mode.
- Manual rotation.
- HDMI audio control.
- Notification archive and reconnect generation handling.

Preserve this work unless evidence demonstrates a specific defect.

## 1.4 Previous deployment

The previous report recorded:

- Branch: `feature/v0.8.2-beta-pwnage-97000`
- Commit: `b6154b67ec1e421729cea8053839ce9cfae9095d`
- Deployment via `scripts/nuxel-deploy-live.py --apply --no-restart`
- Rollback: `/var/lib/nuxel/live-deploy/rollback-20261109T155518Z/`
- Evidence: `evidence/pwnage-99000/`

Verify the actual current branch, commit, deployed state and rollback availability. Do not assume these historical details remain unchanged.

---

# 2. New reference-device evidence

The Pixel 10 Pro XL has successfully driven the same TV and HDMI cable.

The user has confirmed the same TV and cable. Record the exact adapter model and markings during this run and establish whether it is the same physical adapter used in the Pixel test.

The Pixel result establishes that the display and cable are capable of working with a USB-C video-output device.

It does **not** establish that:

- The S10+ supports the same adapter's exact DP mode.
- The adapter negotiates identically with both devices.
- The S10+ connector is electrically healthy.
- The S10+ CCIC controller is operating correctly.
- The S10+ kernel has the correct vendor drivers.
- The Nuxel kernel contains the necessary Samsung-specific configuration.
- The S10+ DP mux or PHY is being switched correctly.

Do not assume that the Pixel uses the same controller, VDM sequence, lane assignment, power role or vendor driver as the S10+.

Use the Pixel test to narrow the investigation, not to skip it.

---

# 3. Mandatory first actions: preserve the live connected state

The adapter is expected to be connected when the agent starts.

**Do not begin by asking the user to unplug it.**

First inspect the repository and the deployment scripts. Then connect to the S10+ using the supplied access details if still valid:

```bash
ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167
```

Do not disable host-key verification. Do not expose private key contents. If access fails, report the exact reason and continue with available local source inspection.

## 3.1 Verify device identity

Capture:

```bash
uname -a
cat /etc/os-release
cat /proc/cmdline
cat /proc/version
```

Where available, also capture:

```bash
cat /sys/firmware/devicetree/base/model
cat /sys/firmware/devicetree/base/compatible
```

Confirm:

- It is the intended S10+.
- It is `beyond2lte`.
- It uses the expected Exynos 9820 platform.
- The currently running kernel is the expected Nuxel kernel.
- The active kernel version and build identity.
- The current repository branch and commit.

Do not make any assumptions based only on a hostname.

## 3.2 Record adapter and display details

Record:

- Adapter manufacturer.
- Adapter model.
- Adapter hardware revision, if visible.
- Any printed DP/HDMI/USB-PD specifications.
- TV manufacturer and model.
- HDMI input number.
- Cable type and any intermediate couplers.
- Whether the adapter has a separate USB-C power input.
- Whether power is connected to the adapter.
- Whether the TV currently reports a signal.

Do not invent missing information. Mark it unknown.

## 3.3 Capture an initial hardware snapshot

Before modifying anything, collect:

- USB device enumeration.
- Type-C class devices.
- Type-C partner state.
- CCIC controller state.
- USB-PD state.
- USB-PD message/event logs.
- DP Alt Mode state.
- extcon state.
- HPD state.
- PHY state.
- Mux state.
- EDID and connector state.
- DRM state, if available.
- Framebuffer state.
- Audio device state.
- Relevant kernel logs.

Search all relevant sysfs locations rather than assuming one fixed path.

Useful discovery commands include:

```bash
find /sys/class/typec -maxdepth 5 -type f -print 2>/dev/null
find /sys/class/extcon -maxdepth 4 -type f -print 2>/dev/null
find /sys/class/graphics -maxdepth 3 -type f -print 2>/dev/null
find /sys/class/drm -maxdepth 4 -type f -print 2>/dev/null
find /sys/bus/platform/devices -maxdepth 2 -type l -print 2>/dev/null
find /sys/bus/platform/drivers -maxdepth 3 -type l -print 2>/dev/null
find /sys/kernel/debug -maxdepth 4 -type f -print 2>/dev/null
```

Only read debugfs locations if available and safe.

Capture:

```bash
dmesg -T
journalctl -b -k --no-pager
lsusb -t
lsusb
```

Also inspect all relevant Samsung-specific log buffers and vendor diagnostics that exist on this build.

Save raw output under:

```text
evidence/pwnage-100000/initial/
```

Do not overwrite the PWNAGE-99000 evidence.

---

# 4. Reconstruct the real Samsung USB-C / USB-PD / DP negotiation

This is the central task.

The previous report's interpretation must be independently verified.

## 4.1 Do not confuse USB-PD roles with DP Alt Mode

USB-C power roles, USB-PD negotiation, structured VDM discovery and DisplayPort Alt Mode are related but distinct states.

A sysfs field such as:

```text
supports_usb_power_delivery=no
```

does not by itself establish that no PD communication occurred.

Likewise:

```text
usbpd_ids=0000:0000
```

does not conclusively prove that the partner never supplied identity information until the exact driver semantics and source implementation are understood.

Investigate what each field actually represents in this Samsung kernel.

Do not treat a single sysfs value as a complete protocol trace.

## 4.2 Inspect the complete CCIC state machine

Locate the exact source for the active Samsung CCIC implementation.

Search the repository, kernel source tree, module source, device tree and vendor source for:

- CCIC.
- S2MU / Samsung Type-C controller.
- PDIC.
- USB-PD.
- PD message handling.
- Structured VDM.
- Discover Identity.
- Discover SVIDs.
- Discover Modes.
- Enter Mode.
- DisplayPort SVID.
- DP Status.
- DP Configure.
- Attention messages.
- Exit Mode.
- HPD.
- DP pin assignment.
- Cable orientation.
- USB role switching.
- Type-C mux control.

Names vary across Samsung kernel revisions. Follow actual source references and call chains rather than relying on filename guesses.

Determine:

1. Which driver owns the connector.
2. Which driver owns PD negotiation.
3. Which driver receives PD interrupts.
4. Which driver parses VDMs.
5. Which driver handles the DisplayPort SVID.
6. Which driver activates the DP mode.
7. Which driver controls the lane mux.
8. Which driver enables the Exynos combo PHY.
9. Which driver handles HPD.
10. Which driver initiates AUX/DPCD communication.

Draw the actual call path and state transitions.

## 4.3 Capture raw protocol evidence

Find the best available way to observe the actual PD and VDM events.

Prefer, in order:

1. Existing controller event logs.
2. Existing Samsung PDIC/CCIC debug interfaces.
3. Existing tracepoints.
4. Driver-supported diagnostic logging.
5. Carefully added temporary instrumentation, if needed.

Capture:

- CC attach and detach.
- CC pin/orientation.
- Power role.
- Data role.
- PD contract state.
- Source capabilities.
- Request / Accept / PS_RDY.
- Structured VDM headers.
- SVID and mode discovery.
- DP mode entry.
- DP status.
- DP configure.
- Pin assignment.
- Mux state.
- HPD IRQ / level.
- AUX transaction results.

If packet-level visibility is unavailable, explicitly state that limitation.

Do not invent a VDM sequence from inferred state.

## 4.4 Interpret the previous CCIC state correctly

The previous report recorded:

```text
PE_SRC_Send_Capabilities
```

Do not assume that this state alone proves the adapter never negotiated DP.

Trace the actual state machine implementation and determine:

- Whether the state was transient or persistent.
- Whether interrupts continued to arrive.
- Whether the controller was in source or sink role.
- Whether the state corresponds to the S10+ or the connected partner's side.
- Whether the PDIC driver was correctly bound.
- Whether a vendor userspace service was expected to participate.
- Whether the controller's interrupt path was functioning.
- Whether the state was stale or incorrectly exported.

A frozen or incorrectly initialized PD state machine is a possible defect.

---

# 5. Compare against original Samsung `beyond2lte` implementation

The S10+ is not a generic USB-C DP Alt Mode device.

Investigate the original Samsung Exynos 9820 implementation and the exact `beyond2lte` kernel/device-tree configuration.

Identify trustworthy source references. Prefer:

- Original Samsung open-source kernel releases for the exact model and SoC.
- The appropriate Samsung device tree.
- Matching vendor driver source.
- Matching firmware packages where legally and technically appropriate.
- Known-working community implementations for the exact hardware.
- Upstream Linux sources for relevant generic infrastructure.

Do not blindly copy configuration or blobs from a different Samsung model.

## 5.1 Establish the active kernel baseline

Collect:

```bash
uname -a
cat /proc/version
zcat /proc/config.gz 2>/dev/null
```

If `/proc/config.gz` is unavailable, locate the exact configuration used to build the running kernel.

Identify:

- Kernel source commit.
- Build configuration.
- Toolchain.
- Compiler version.
- Build artifacts.
- Device-tree source and active DTB.
- Built-in drivers.
- Loadable modules.
- Firmware files.
- Module dependencies.
- Boot image layout.

Do not claim to have inspected the active kernel configuration if it cannot be obtained.

## 5.2 Build a prerequisite matrix

Create a table containing:

| Component | Required function | Nuxel status | Samsung reference | Finding |
|---|---|---|---|---|
| Type-C controller | CC attach/orientation | | | |
| CCIC/PDIC | Controller events | | | |
| USB-PD | Contract and message handling | | | |
| Structured VDM | DP discovery | | | |
| DP Alt Mode | Enter/configure mode | | | |
| DP pin assignment | Lane mapping | | | |
| Type-C mux | Switch high-speed lanes | | | |
| Combo PHY | DP PHY activation | | | |
| HPD | Hot-plug signalling | | | |
| AUX | DPCD/EDID access | | | |
| Display controller | External display pipeline | | | |
| Audio | DP audio transport | | | |

Include exact configuration symbols, source files, functions, device-tree nodes, firmware names and module names wherever evidence supports them.

Mark each item:

- Present and verified.
- Present but malfunctioning.
- Missing.
- Disabled in configuration.
- Incorrectly configured.
- Not applicable.
- Unknown due unavailable evidence.

## 5.3 Search kernel configuration thoroughly

Investigate all relevant generic and Samsung-specific configuration symbols.

Do not limit the search to generic names such as:

```text
CONFIG_TYPEC
CONFIG_DRM
CONFIG_USB
```

The Samsung vendor implementation may use different names and built-in infrastructure.

Search the actual kernel source and active configuration for the exact symbols referenced by the drivers.

For every missing or disabled symbol:

- Identify the source file that depends on it.
- Identify its Kconfig dependency chain.
- Determine whether it must be built-in or modular.
- Check whether its device-tree node is enabled.
- Check whether the corresponding module exists on the device.
- Check whether the required firmware exists.
- Explain why enabling it is necessary.

Never add speculative kernel flags merely because their names look relevant.

---

# 6. Device tree, firmware and vendor dependencies

Inspect the exact `beyond2lte` device tree and compare it against the original Samsung implementation.

Investigate:

- USB-C controller node.
- CCIC/PDIC node.
- Interrupts and GPIOs.
- Regulator supplies.
- Clocks.
- Pin control.
- Type-C orientation handling.
- USB/DP mux.
- Combo PHY.
- DP controller.
- Display controller connections.
- HPD GPIO or interrupt.
- AUX channel.
- Power sequencing.
- Runtime PM dependencies.
- Firmware references.

Verify whether every required resource is actually available and correctly described.

## 6.1 Firmware

For every firmware dependency:

- Identify the exact filename.
- Identify the expected path.
- Find the driver request call.
- Verify whether the file exists.
- Verify ownership and permissions.
- Verify whether firmware loading succeeded.
- Verify that the firmware matches the correct hardware revision.

Do not substitute firmware from a different device without proving compatibility.

Do not invent missing firmware files.

## 6.2 Vendor components

Identify whether the original Samsung implementation requires proprietary vendor components.

For each component, determine:

- What it does.
- Whether Nuxel already has an equivalent.
- Whether it is kernel-side or userspace-side.
- Whether it is required for the DP negotiation path.
- Whether it is legally and technically available.
- Whether a clean-room replacement is feasible.

Do not install an Android framework merely to obtain a vendor service.

Do not copy arbitrary vendor binaries into Nuxel.

If a proprietary component is genuinely necessary, document the exact dependency and the safest supported integration path.

---

# 7. Investigate the USB-C lane mux and Exynos combo PHY

A correct PD negotiation is not enough. The DP lanes must physically switch from USB to DisplayPort.

Inspect the actual mux and PHY implementation.

Determine:

- Who owns mux selection.
- How connector orientation is propagated.
- How DP pin assignment maps to physical lanes.
- Whether USB 3.x is disabled or reduced when required.
- Whether the DP PHY is powered.
- Whether the DP PLL locks.
- Whether required regulators and clocks are enabled.
- Whether the PHY is switched back correctly after disconnect.
- Whether runtime PM is disabling the PHY prematurely.

The previous report recorded:

```text
exynos_usbdrd_inform_dp_use dp use=0
```

Trace the exact source and call path responsible for this value.

Determine why it remains zero.

Do not manually write arbitrary sysfs values or invoke undocumented register writes to force DP mode.

If a driver change is required, implement it through the correct controller and state-machine path.

## 7.1 Orientation and pin assignment

Investigate both connector orientations if possible.

Do not rotate or reverse the cable as a substitute for fixing orientation detection.

Record the actual CC pin, orientation, pin assignment and mux state.

If the adapter negotiates an unsupported pin assignment, report the exact reason.

---

# 8. HPD, AUX, DPCD and EDID — no synthetic success

The previous report observed AUX/DPCD failures during a controlled HPD test.

Interpret these results in the correct sequence.

AUX/DPCD access can fail when:

- The DP Alt Mode was never entered.
- The mux was not switched.
- The PHY was not enabled.
- The AUX channel was not powered.
- HPD was not valid.
- The controller was in the wrong state.
- The driver was not bound.
- The display was not actually connected.

Do not interpret AUX failure as proof that the TV or cable is faulty.

Do not interpret an EDID-like value as proof that a monitor was detected.

The previous report explicitly recorded:

```text
monitor_info=BNQ,0x7f54,0x5445
```

This was identified as built-in unit-test EDID, not the attached display.

Preserve this distinction.

## 8.1 Real EDID verification

Once DP Alt Mode and the PHY are correctly activated:

- Read the actual EDID from the physical sink.
- Validate its header and checksum.
- Decode manufacturer, product, serial and supported modes.
- Compare with the actual TV model.
- Verify that it is not a test fixture or cached EDID.

If no real EDID can be read, report the exact stage at which the chain fails.

## 8.2 HPD handling

Do not use forced HPD as proof of a physical connection.

Do not leave HPD forced after a diagnostic test.

Any controlled HPD test must:

1. Capture the original state.
2. Explain the driver-specific meaning of the control.
3. Ensure the correct mux/PHY state.
4. Run a bounded test.
5. Restore the original state.
6. Verify the restored state.

---

# 9. Investigate the adapter and compare the Pixel test

The user has confirmed that the same TV and HDMI cable work with the Pixel 10 Pro XL.

Record the adapter identity and establish whether the exact same physical adapter was used.

If the adapter has a USB-C PD power input, record whether it is powered in the S10+ test.

Do not disconnect the adapter merely to collect this information.

Investigate:

- Adapter model and chipset, if identifiable.
- Supported DP Alt Mode versions.
- Supported lane configurations.
- USB-PD power requirements.
- Whether the adapter requires external power.
- Whether the adapter behaves differently with Samsung's PD implementation.
- Whether its required DP pin assignment is supported by the S10+.
- Whether the adapter's HDMI conversion chipset has any relevant requirements.

Do not assume that successful operation on the Pixel proves every adapter negotiation path is universal.

## 9.1 If an adapter incompatibility is suspected

Provide evidence for the specific incompatibility.

Do not recommend purchasing another adapter until the S10+ controller and kernel have been properly examined.

If the adapter requires a mode the S10+ cannot support, explain the exact mismatch.

---

# 10. Implement the actual fix

After the evidence-based diagnosis, implement the smallest complete repair.

Potential repair categories include:

- Missing kernel configuration.
- Incorrect Kconfig dependency.
- Missing built-in driver.
- Missing kernel module.
- Incorrect module load order.
- Missing firmware.
- Incorrect device-tree node.
- Missing regulator or clock.
- Broken CCIC interrupt handling.
- Incorrect PD state-machine initialization.
- Broken VDM parsing.
- Missing DP SVID support.
- Missing DP Alt Mode state transitions.
- Incorrect pin assignment.
- Broken orientation handling.
- Missing or incorrect Type-C mux integration.
- Incorrect combo PHY activation.
- Incorrect HPD propagation.
- AUX controller initialization.
- EDID handling.
- Nuxel display manager integration.
- Audio routing integration.

Do not select a repair before establishing the root cause.

## 10.1 Fix requirements

Every change must:

- Have a traceable root cause.
- Be minimal and maintainable.
- Preserve the existing Nuxel display architecture.
- Include comments where vendor-specific behavior is non-obvious.
- Include tests where possible.
- Include a rollback.
- Be documented in the report.
- Avoid unrelated refactoring.

Do not disable working internal display components to make external output work.

Do not change the internal AMOLED resolution or DPI as a workaround.

Do not use software rendering to fake external output.

---

# 11. Kernel rebuild and reflash gate

A kernel or device-tree fix may be required. If so, do the complete engineering work to prepare it, but do not perform a risky kernel/DTB/firmware flash without passing this section.

## 11.1 Determine whether reflash is genuinely necessary

First establish whether the problem can be fixed through:

- Existing kernel configuration.
- Existing modules.
- Existing firmware.
- Userspace service configuration.
- Device-tree overlays supported by the current boot chain.

If the active kernel was built without a required built-in driver or configuration option, userspace changes cannot magically enable it.

Explain exactly why a kernel rebuild or reflash is required.

## 11.2 Prepare a reproducible build

If kernel changes are necessary:

- Identify the exact source revision.
- Preserve the existing working configuration.
- Make only justified configuration changes.
- Record all configuration differences.
- Build using the correct toolchain.
- Build all required modules.
- Build the appropriate device tree.
- Verify module ABI compatibility.
- Verify firmware dependencies.
- Verify image format and boot packaging.
- Verify image signatures or required boot metadata.
- Validate the resulting artifacts.
- Produce checksums.
- Preserve the current bootable image.

Do not mix source revisions or device trees from different S10+ variants.

## 11.3 Reflash safety

Before flashing anything, establish:

- Exact boot partition and image layout.
- Exact recovery method.
- Current boot image backup.
- Current DTB/DTBO backup where applicable.
- Current kernel backup.
- Verified recovery path through TWRP or another supported mechanism.
- Sufficient battery.
- Stable USB connection if needed.
- Correct target device identity.
- Validated artifact checksums.
- Clear rollback steps.

**Do not flash bootloader, modem, PIT, recovery, or unrelated firmware.**

**Do not flash a kernel or DTB if recovery is unverified.**

If flashing is not safe, leave the validated package ready and report the precise remaining prerequisite. Do not risk making the phone unbootable to claim completion.

The user has authorized the investigation and repair task, but that is not permission to bypass the safety gate for destructive boot-chain operations.

---

# 12. Preserve and complete the existing Nuxel display manager

The PWNAGE-99000 display manager work should be retained.

Inspect the actual implementation of:

- `nuxel-displayd`
- `nuxel-display-ctl`
- `nuxel-wl-fb-ext`
- Connection notifications.
- Display settings.
- Mirror / Separate desktop controls.
- Rotation.
- Audio routing.

Do not rebuild these components unnecessarily.

## 12.1 Truthful connection states

Preserve the distinction between:

```text
DISCONNECTED
PARTNER_NO_PD
PD_NO_DP
DP_NO_FB
DP_LINK_READY
```

Extend the model only if the actual investigation demonstrates that more precise states are necessary.

Consider separate states for:

- Type-C partner detected.
- PD communication active.
- DP SVID discovered.
- DP Alt Mode entered.
- Pin assignment configured.
- DP mux switched.
- PHY ready.
- HPD asserted.
- AUX operational.
- Valid EDID detected.
- Display link trained.
- Framebuffer/output available.
- Physical display active.

The UI must not report an HDMI display as ready merely because a USB-C partner is connected.

## 12.2 Notification behavior

When a real external display becomes available:

- Show a connection notification.
- Offer Mirror and Separate desktop actions.
- Show the actual detected display name when real EDID is available.
- Avoid fabricated manufacturer/model information.
- Avoid duplicate notifications during negotiation.
- Handle disconnect and reconnect generations correctly.
- Preserve the existing notification hub integration.

If the adapter is connected but DP negotiation fails, the notification must describe the actual failure state rather than claim a working external display.

## 12.3 Mirror mode

Once a physical output is available:

- Mirror the internal desktop.
- Preserve the internal AMOLED output.
- Maintain aspect ratio.
- Avoid stretching.
- Avoid unnecessary CPU copies.
- Maintain stable frame pacing.
- Handle portrait and landscape correctly.
- Keep input behavior predictable.

## 12.4 Separate desktop mode

The previous report stated that live Phoc exposed only:

```text
HEADLESS-1
```

and reported:

```text
DESKTOP_OUTPUT_UNAVAILABLE
```

Investigate the current compositor version and output architecture.

Do not claim that Separate desktop works until a genuine second output is available and verified.

If a second compositor output is unsupported, report the limitation accurately and keep Mirror mode working.

Do not replace Phoc or introduce a second compositor as a shortcut.

---

# 13. HDMI audio

Do not create a dummy HDMI audio sink.

Inspect the real DP audio path.

The previous report stated that a DP Audio PCM existed but was unavailable because:

```text
ch_hdmi_audio=0
```

and there was no DP link.

Determine whether the audio path is blocked by the same missing DP Alt Mode activation or by a separate audio configuration problem.

Verify:

- Real DP audio capability.
- Audio codec and controller.
- Kernel PCM device.
- ALSA card and device.
- PipeWire/WirePlumber discovery.
- Correct profile activation.
- Default sink routing.
- Disconnect and reconnect handling.

Once a real display link exists, play a known test sound through the TV and physically confirm that sound comes from the TV.

Do not mark HDMI audio as verified based on an ALSA device listing alone.

---

# 14. Orientation and display modes

After the real display link is operational:

- Read supported modes from real EDID.
- Select a supported mode.
- Verify portrait and landscape.
- Keep internal and external orientation independent where appropriate.
- Preserve the user's manual rotation control.
- Avoid unsupported mode requests.
- Avoid forcing global internal display resolution or DPI.
- Verify that rotation does not break input mapping.

If the TV does not support a requested orientation or mode, report that accurately.

---

# 15. Live verification and physical testing

The connected adapter is the central test fixture.

Do not ask the user to disconnect it before the initial diagnostic capture.

Once a likely fix has been implemented and deployed safely, perform the following tests.

## 15.1 Protocol and controller tests

Verify:

- CC attach.
- Correct orientation.
- PD communication.
- Partner identity, if available.
- DP SVID discovery.
- DP mode entry.
- DP status and configuration.
- Pin assignment.
- Mux switching.
- PHY activation.
- HPD.
- AUX communication.
- DPCD read.
- Real EDID.
- Link training.
- Display controller activation.

Record raw evidence.

## 15.2 Physical picture test

The decisive test:

1. Confirm that the TV is on the correct HDMI input.
2. Confirm that the adapter remains connected.
3. Confirm that the S10+ is running Nuxel.
4. Confirm that the display manager detects the actual external output.
5. Activate Mirror mode.
6. Observe the TV physically.
7. Confirm that the Nuxel desktop is visible.
8. Move or change something on the internal screen.
9. Verify that the external picture updates.
10. Confirm that the image is stable and correctly scaled.

Record the exact result.

If the TV remains blank, capture the state at the exact point of failure.

## 15.3 Separate desktop

If supported:

1. Activate Separate desktop.
2. Confirm that the compositor exposes a genuine second output.
3. Move a window to the external display.
4. Verify it appears on the TV.
5. Verify the internal AMOLED remains functional.
6. Test pointer movement and input.
7. Test orientation and mode changes.

If unsupported, report `NOT_SUPPORTED` or the precise blocker.

## 15.4 HDMI audio

If the link is active:

1. Select the real HDMI/DP audio output.
2. Play a known test sound.
3. Confirm the sound physically comes from the TV.
4. Confirm volume control.
5. Confirm disconnect handling.

## 15.5 Disconnect and reconnect

Only after initial connection and physical output verification, test:

- Disconnect.
- Notification archive.
- Reconnect.
- New connection generation.
- Mirror mode restoration or user-choice behavior.
- Audio sink removal and restoration.

Ask the user before any test that requires physically disconnecting the adapter if the user has not already authorized that action.

---

# 16. Performance and architecture constraints

Preserve the existing Nuxel architecture.

Do not:

- Introduce a second `/dev/fb0` writer.
- Stop or replace the internal framebuffer bridge.
- Replace the compositor.
- Force software rendering.
- Introduce llvmpipe as a workaround.
- Force HPD permanently.
- Fake EDID.
- Fake an HDMI audio sink.
- Claim that `fb1` writes mean a physical display works.
- Change global DPI or resolution to hide geometry problems.
- Disable unrelated working USB functionality.

External output must have clear ownership and cleanup.

If `/dev/fb1` remains part of the external bridge:

- Verify its actual kernel meaning.
- Verify its allocation and ownership.
- Verify that it maps to the correct physical output.
- Do not assume that a framebuffer device represents a working DP connector.
- Ensure that a failed link cannot cause an endless busy loop or high CPU usage.

Measure:

- CPU usage.
- Memory.
- Frame rate.
- Frame latency.
- Service restarts.
- Kernel warnings.
- Display stability.

---

# 17. Test suite

Add or update automated tests for:

## USB-C / PD state handling

- No partner.
- Partner without PD.
- PD active without DP.
- DP SVID discovered.
- DP mode entered.
- DP configuration failed.
- Mux failure.
- PHY failure.
- AUX failure.
- EDID failure.
- Link training failure.
- Fully ready display.

## Lifecycle

- Repeated connection events.
- Disconnect during negotiation.
- Disconnect during active output.
- Reconnect.
- Orientation change.
- Display mode change.
- Service restart.
- Compositor restart.
- Notification generation handling.

## Safety

- Internal display remains active.
- No competing fb0 writer.
- No dummy HDMI sink.
- No fabricated EDID.
- No stale ready state.
- No uncontrolled HPD state.
- No endless retry loop.
- No unbounded logs.

## UI

- Accurate connection state.
- Accurate display identity.
- Mirror action.
- Separate desktop action only when supported.
- Rotation controls.
- Audio controls only when a real output exists.
- Correct notification behavior.

Automated tests must not be presented as physical hardware tests.

---

# 18. Deployment procedure

Use the existing Nuxel deployment mechanisms.

Inspect all scripts in:

```text
./scripts
```

In particular, inspect the current deployment script and its supported flags before using it.

Do not blindly execute deployment scripts without reading them.

Before deployment:

1. Record current branch and commit.
2. Check the working tree.
3. Preserve unrelated user changes.
4. Run the relevant tests.
5. Create a rollback backup.
6. Verify the rollback backup.
7. Deploy only the required components.
8. Restart only the services required by the change.
9. Preserve the internal display and active SSH connectivity.
10. Confirm that the device remains reachable.

Do not flash boot-chain components through the userspace deployment path.

If kernel/DTB/firmware changes are needed, follow Section 11.

---

# 19. Required reports and evidence

Create:

```text
REPORT-PWNAGE-100000.md
```

Save supporting evidence under:

```text
evidence/pwnage-100000/
```

Organize it:

```text
evidence/pwnage-100000/
├── initial/
├── protocol/
├── kernel/
├── devicetree/
├── firmware/
├── comparison/
├── implementation/
├── deployment/
├── physical-tests/
└── rollback/
```

The report must include:

## A. Executive result

Choose exactly one primary status:

- `FULLY_VERIFIED_PHYSICAL_HDMI`
- `PARTIALLY_FIXED_PHYSICAL_HDMI`
- `FIX_IMPLEMENTED_AWAITING_REFLASH`
- `FIX_IMPLEMENTED_AWAITING_PHYSICAL_TEST`
- `BLOCKED_BY_CONFIRMED_HARDWARE`
- `BLOCKED_BY_KERNEL_OR_DRIVER`
- `BLOCKED_BY_MISSING_DEPENDENCY`
- `BLOCKED_BY_UNAVAILABLE_RECOVERY`
- `INVESTIGATION_INCONCLUSIVE`

Do not select a status merely because the code compiles.

## B. Root cause

Explain:

- What was broken.
- Why it was broken.
- Which component owned the failure.
- Why the previous implementation did not work.
- How the Pixel reference test narrowed the investigation.
- What evidence proves the diagnosis.

## C. Negotiation trace

Include the real observed sequence from attach through the last successful state.

Clearly distinguish observed events from inferred events.

## D. Kernel and vendor comparison

Include the prerequisite matrix from Section 5.

Include exact source files, configuration symbols, device-tree nodes and firmware dependencies.

## E. Changes

List every modified file, service, kernel configuration item, module, device-tree entry and firmware dependency.

Explain the reason for each change.

## F. Verification

For every test, report:

- Test name.
- Test method.
- Expected result.
- Actual result.
- Evidence path.
- Status.

Separate automated, live software and physical tests.

## G. Deployment and rollback

Record:

- Branch.
- Commit.
- Deployment method.
- Backup location.
- Rollback procedure.
- Current device state.

## H. Remaining work

State precisely what is still required.

If the device cannot physically display an image, explain the exact hardware or driver stage preventing it.

Do not hide behind generic statements such as “hardware limitation” when the investigation has not proven that conclusion.

---

# 20. Final execution rules

1. Start with the connected adapter.
2. Capture the live state before changes.
3. Read the previous PWNAGE-99000 report and implementation.
4. Investigate the Samsung-specific kernel and Type-C stack.
5. Treat the Pixel test as meaningful evidence.
6. Do not blame the TV or HDMI cable without new evidence.
7. Do not assume `supports_usb_power_delivery=no` proves no VDM negotiation.
8. Do not force HPD or write undocumented controller registers.
9. Do not fabricate EDID, display identity, audio devices or output readiness.
10. Do not destabilize the internal AMOLED display.
11. Implement justified fixes rather than stopping at analysis.
12. Prepare a kernel reflash package if genuinely required.
13. Do not perform a risky flash without verified recovery and the explicit safety gate.
14. Deploy safe userspace changes and verify them live.
15. Physically verify the TV picture.
16. Report honestly if physical verification remains impossible.
17. Never claim success based solely on a successful build or framebuffer write.

**The mission is not to make Nuxel believe an HDMI display is connected. The mission is to make the Samsung Galaxy S10+ actually drive the connected TV.**

Begin with the adapter connected and work through the entire chain.

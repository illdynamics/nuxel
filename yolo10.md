# NUXEL — S10+ ULTIMATE GUI & TOUCHSCREEN COMPLETION MISSION
## DeepSeek V4 Flash Thinking · CodeSeeQ · A26 → A27+
### ONE PLANNED TWRP BOOT UPDATE → LIVE FEDORA → VM-QUALITY GUI → REAL TOUCHSCREEN

# 1. THE MISSION

You are the autonomous lead engineer responsible for finishing Nuxel on the physical Samsung Galaxy S10+.

Nuxel is our Fedora-based ARM64 Linux PHONE operating system.

WE HAVE ALREADY ACHIEVED:

- Native ARM64 Linux kernel execution.
- Kernel-embedded initramfs startup.
- UFS partition discovery.
- Fedora 43 ext4 rootfs mounting.
- Fedora systemd PID 1.
- Successful Fedora service execution.
- A26 systemd boot-graph completion.
- Working Exynos AMOLED framebuffer output.
- Original Nuxel MP4-derived boot animation.
- Bidirectional USB live console.
- Working command execution and verified transfers.
- Automatic startup of the native Nuxel UI process.
- Successful framebuffer commits and animation handoff.

The user has physically photographed the Nuxel home screen running on the Samsung.

However, the GUI is visually broken, touchscreen interaction is not yet proven, and the obsolete early-boot splash still appears briefly before the correct Nuxel animation.

**YOUR FINAL OBJECTIVE: A seamless original Nuxel boot animation that transitions into a polished, functional, touchscreen-controlled Linux phone interface matching the Nuxel VM's visual design as closely as the available graphics hardware permits.**

You are running DeepSeek V4 Flash Thinking with CodeSeeQ.

You have permission to inspect the repository, run build tools, edit source code, perform authorized BOOT flashing through TWRP, reboot, reconnect to live Nuxel, deploy userspace fixes, and test them.

Execute the engineering work. Do not merely write recommendations.

---

# 2. VERY IMPORTANT — TWO-STAGE WORKFLOW

The user is manually putting the S10+ into TWRP ONE MORE TIME NOW.

This visit is intentional maintenance, not evidence of a new boot failure.

## Stage A — TWRP

Finish and flash the seamless original-animation first-light BOOT fix.

Then reboot normally into Nuxel.

## Stage B — Live Nuxel

As soon as the USB console becomes available:

1. Reconnect.
2. Verify Fedora.
3. Verify the GUI process.
4. Fix the visual corruption.
5. Deploy the improved GUI live.
6. Fix touchscreen detection.
7. Test actual touch interaction.
8. Finish Fedora userspace integration.
9. Continue improving the phone UI.

**DO NOT RETURN TO TWRP FOR ROUTINE GUI, TOUCH USERSpace, SERVICE OR CONFIGURATION CHANGES.**

Use the live console and verified deployment tools.

TWRP is retained as an emergency recovery and BOOT replacement mechanism.

The old automatic "TWRP return = failed boot" agreement is not part of this mission. A future return to recovery must be interpreted according to the actual operation and its recorded test state.

Do not promise that TWRP will never be needed again: future kernel/embedded-initramfs changes may still require it.

---

# 3. EXACT DEVICE

- Samsung Galaxy S10+
- SM-G975F
- Codename beyond2lte
- Exynos 9820
- ARM64 / aarch64
- EUR OPEN
- Board revision 26
- Bootloader G975FXXSEFUL1
- Samsung downstream Linux 4.14.253
- Fedora 43 ARM64
- systemd 258 with Nuxel compatibility repairs
- TWRP 3.7.0_9-2
- ADB serial R58M75KDB2X

Recovery partition mappings previously confirmed:

- BOOT: `/dev/block/by-name/boot`
- USERDATA: `/dev/block/by-name/userdata`
- RECOVERY: `/dev/block/by-name/recovery`

Reverify the actual paths before writing.

Do not assume historical measurements replace live checks.

---

# 4. PROJECT PATHS

Repository root:

`~/x/nuxel`

Critical files:

- `boot/initramfs/init.sh`
- `tools/s10plus/nuxel-fb-phone.c`
- `tools/s10plus/nuxel-anim-player.c`
- `tools/s10plus/nuxel-ui.c`
- `tools/s10plus/a26/build-a26-boot.sh`
- `tools/s10plus/a26/make-firstlight-asset.py`
- `tools/s10plus/a26/decode-touch.py`
- `tools/s10plus/a26/nuxel-rootfs-fixes.sh`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`
- `assets/nuxel-boot-animation.mp4`

Live development scripts:

- `scripts/s10plus-debug-pack/nuxel-live.sh`
- `scripts/s10plus-debug-pack/nuxel-live-deploy.sh`

Flashing pack:

`scripts/nuxel-adb-flash-pack/`

Engineering records:

`docs/s10plus-autonomous-boot-repair/`

Boot candidates:

`build/out/s10plus/debug-candidates/`

Current Fedora image:

`build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img`

A26 artifacts are supplied, but the uploaded A26 archive contains an initramfs cpio file, NOT a complete BOOT image.

Do not attempt to flash a standalone cpio archive.

Read the latest STATUS, NEXT-ACTION, A26-SEAMLESS-BOOT-ANIMATION, A26-PHONE-UI-ACCEPTANCE, A26-TOUCHSCREEN-ACCEPTANCE and A26-SYSTEMD-BOOT-GRAPH-FIX documents before editing.

---

# 5. FIRST: CAPTURE ANY OUTSTANDING EVIDENCE

The phone is expected to enter TWRP now.

Wait for verified root ADB.

Before the planned BOOT update:

- Capture any outstanding previous-boot logs.
- Preserve pstore and last_kmsg where available.
- Record installed BOOT identity.
- Record image hashes and current recovery information.
- Read the latest A26 build journal.
- Confirm a recovery backup exists on the MacBook.
- Preserve the last known working BOOT image.

Do not erase or alter USERDATA to perform the early-splash fix.

Keep Fedora's successful A26 changes intact.

---

# 6. STAGE A — COMPLETE THE SEAMLESS ORIGINAL BOOT ANIMATION

## 6.1 Root cause already identified

The old two-second splash comes from:

`boot/initramfs/init.sh`

The script invokes:

`nuxel_first_light`

which runs:

`/opt/nuxel/nuxel-fb-phone`

That binary paints the obsolete diagnostic Nuxel/penguin screen.

Later, after USERDATA mounts, the actual MP4-derived Nuxel animation starts.

This is why the user sees the old artwork briefly before the correct animation.

The appropriate solution is to show the REAL animation's opening image as the very first display frame.

**Do not remove early panel initialization. Replace its artwork while preserving the hardware-proven display initialization.**

## 6.2 Current A26 build state

A26 already has a generated `NUXSPL01` first-frame asset.

The prepared code and asset builder live under:

`tools/s10plus/a26/`

The first-frame data is generated from the actual original MP4-derived animation container.

However, the uploaded source still lacks the required first-frame rendering implementation in:

`tools/s10plus/nuxel-fb-phone.c`

The A26 builder currently checks for `--firstlight` in source text.

That is insufficient release verification.

Complete the missing implementation.

Do not merely insert `--firstlight` into a comment to satisfy the gate.

A missing implementation must make the builder fail with a nonzero exit code.

## 6.3 Implement the real NUXSPL01 renderer

Read the contract documented at the top of:

`tools/s10plus/a26/build-a26-boot.sh`

Implement it completely.

Requirements:

1. Load the actual first-frame asset.
2. Validate its NUXSPL01 magic and header.
3. Validate palette and pixel-plane sizes.
4. Reject malformed dimensions or unsupported flags.
5. Convert the RGB565 palette into the actual Samsung ABGR_8888 hardware layout.
6. Use the same pixel packing as the working animation player.
7. Scale using the same integer nearest-neighbor spans as the MP4-derived player.
8. Paint every framebuffer page the driver might initially display.
9. Respect the actual stride and mapped framebuffer size.
10. Preserve panel initialization and framebuffer diagnostics.
11. Preserve the known-working fallback renderer if the new asset is missing or invalid.
12. Avoid introducing another competing framebuffer writer.

The first frame should match the original animation's first visible frame, pixel-for-pixel wherever technically possible.

The first-light asset should be compact and deterministic.

## 6.4 Validate before building BOOT

Test the asset parser against:

- Valid original asset.
- Truncated header.
- Wrong magic.
- Invalid palette count.
- Truncated pixel plane.
- Invalid dimensions.
- Buffer-size overflow.
- Unsupported compression flags.
- Incorrect pixel order.

Compare the reconstructed early frame with the actual animation's first decoded frame.

Verify identical intended composition, colors and scaling.

The current source's `nuxel-fb-phone` binary must actually contain the new renderer.

Compile it for ARM64.

Verify the resulting ELF architecture.

Verify the new asset and binary are embedded in the initramfs.

## 6.5 Build a complete BOOT candidate

The uploaded A26 artifact is only an initramfs.

Build a complete Android BOOT image using the known-working Samsung kernel packaging.

Preserve:

- Working raw ARM64 kernel.
- Correct Android boot header.
- Correct S10+ board configuration.
- Hardware-proven embedded initramfs strategy.
- Working USERDATA discovery.
- Fedora handoff.
- USB console boot initialization.
- Existing original animation startup.
- Last known functional Nuxel UI configuration.

Important: the initramfs also carries UI components that can be copied into the Fedora rootfs during startup.

Audit those copies so the BOOT update does not replace newer, proven Fedora binaries with stale versions.

Create a uniquely versioned candidate.

Do not overwrite A25 or prior working images.

Verify:

- BOOT structure.
- Android header.
- ARM64 kernel.
- Embedded initramfs.
- New first-frame data.
- New first-light binary.
- Console binaries.
- Image size.
- Partition capacity.
- SHA-256.

Run available regression tests.

## 6.6 Perform the planned TWRP flash

Once the COMPLETE BOOT candidate passes verification:

1. Verify device identity.
2. Verify TWRP root ADB.
3. Verify BOOT partition mapping and capacity.
4. Confirm current BOOT backup.
5. Confirm the exact new image path.
6. Flash BOOT only through the existing ADB flash pack.
7. Require successful write and expected byte count.
8. Perform byte-for-byte SHA-256 readback.
9. Record the receipt.
10. Reboot normally into Nuxel.

Do not flash the 4 GiB Fedora rootfs unless a separately established issue genuinely requires it.

Do not flash RECOVERY, DTB, DTBO, EFS, modem, PIT or bootloader.

Do not reboot into an image with a mismatched readback.

If the full candidate cannot be built and validated, do not flash an incomplete artifact. Continue repairing the build until the gate passes.

## 6.7 Visual acceptance

On the real AMOLED:

- The old diagnostic penguin screen must not appear.
- The actual Nuxel opening image must appear first.
- The full boot animation must start normally.
- No black flash.
- No double penguin.
- No incorrect red/blue conversion.
- No abrupt geometry change.
- No stale framebuffer content.
- No panel power loss.

Only count the seamless animation as hardware-proven after actual visual observation.

---

# 7. STAGE B — RECONNECT TO LIVE NUXEL AUTOMATICALLY

After the planned reboot, monitor the USB CDC-ACM device.

Do not expect TWRP ADB after a successful Nuxel boot.

Discover the actual live console device rather than hard-coding its Mac path.

Previous endpoint:

`/dev/cu.usbmodem201`

Use the installed Nuxel live-console scripts.

Prove command execution with:

`uname -a`

`id`

`cat /etc/os-release`

`ps -p 1 -o pid,comm,args`

`systemctl is-system-running`

`systemctl --failed`

`systemctl is-active nuxel-ui.service`

`cat /var/lib/nuxel/animation`

Require real output, exit codes, and a valid response frame.

If live access works:

**SWITCH TO LIVE DEVELOPMENT IMMEDIATELY.**

From this point onward, ordinary UI, touchscreen-event handling, application and systemd repairs should be deployed live.

No more routine TWRP cycles.

If live access does not return, perform bounded recovery and consult persistent logs rather than claiming the new BOOT image succeeded.

---

# 8. HIGH-PRIORITY DISCOVERY — THE CURRENT GUI HAS REAL LAYOUT BUGS

The user has provided a photograph of the actual Nuxel phone UI.

Observed visual problems include:

- Extremely large clock digits colliding with other elements.
- Unreadable overlapped text in the middle of the screen.
- Status-bar text colliding near the top and camera cutout.
- Bottom navigation labels running into neighboring items.
- A crude diagnostic appearance compared with the Nuxel VM.
- Pixelated block-letter typography.
- Poor information hierarchy.
- Inconsistent spacing and scaling.

The source inspection identifies specific defects.

**Do not blame all of this on framebuffer corruption or color order. Much of the visible damage is explainable from incorrect layout geometry.**

## 8.1 Confirmed clock-width defect

In:

`tools/s10plus/nuxel-ui.c`

The home page currently uses:

`int cs = SC * 14;`

At the actual 1440-pixel panel width:

`SC = 4`

so:

`cs = 56`

The five-character clock is rendered using the 5×7 font with six-cell horizontal advance.

Its required width is:

`5 * 6 * 56 = 1680 pixels`

The panel is only 1440 pixels wide.

**THE CLOCK IS WIDER THAN THE PHYSICAL SCREEN.**

This must be fixed using a width-constrained layout.

Do not arbitrarily hard-code a smaller number without calculating actual text bounds.

## 8.2 Confirmed clock-height and overlap defect

The clock glyph height is:

`7 * 56 = 392 pixels`

But the subsequent layout advances vertically by only approximately 72 pixels before positioning other text.

Later content is placed inside the clock's actual rendered area.

This explains the photograph's overlapping text and large white blocks.

Fix the layout engine so each element's bounding box is respected.

Every element must occupy a non-overlapping rectangle except where deliberate overlay behavior is specified.

## 8.3 Confirmed bottom navigation defect

The current bottom navigation divides 1440 pixels into five slots:

`1440 / 5 = 288 pixels per slot`

But `SETTINGS`, at the current font scale, requires approximately 384 pixels.

Consequently, the labels run together.

The navigation must be redesigned with:

- Correct slot measurements.
- Dynamic font fitting.
- Center alignment.
- Icon-first presentation where appropriate.
- Clipped text within the allocated region.
- Touch-friendly hit targets.
- No overlap at any tested display width.

Use a compact, modern navigation design inspired by the VM UI.

## 8.4 Other likely layout defects

Audit the full renderer for similar errors.

Especially inspect:

- `page_home()`
- `draw_status_bar()`
- `draw_dock()`
- `kv_row()`
- `draw_toast()`
- `draw_error_banner()`
- Font scale calculations.
- Card geometry.
- Text-centering logic.
- Text truncation.
- Vertical row spacing.

In particular, `kv_row()` defines a row height of `SC * 11` while allowing value text to use `SC * 3` font scale.

At `SC=4`, that is a 44-pixel row containing 84-pixel-high text.

This can make Settings/System pages overlap as well.

Fix it systematically.

Do not patch only the photographed Home screen while leaving the other pages broken.

---

# 9. REPLACE THE FRAGILE UI LAYOUT WITH A PROPER PHONE LAYOUT SYSTEM

Implement predictable, reusable layout primitives.

Required capabilities:

- Measured text width and height.
- Bounded font scaling.
- Rectangular clipping.
- Minimum padding.
- Maximum content width.
- Row and column layout.
- Consistent spacing.
- Proper card grids.
- Scrollable content where needed.
- Bottom navigation safe area.
- Status-bar safe area.
- Camera-cutout avoidance.
- Touch-target size constraints.
- Correct alignment.
- Orientation-aware coordinates.

The panel is 1440 × 3040, but use actual measured framebuffer dimensions.

Use phone-scale design coordinates and transform them into pixels.

Do not multiply text size repeatedly by an already-scaled factor.

Use a consistent device-independent design space.

All visible elements should be positioned according to their measured dimensions.

Add automated overlap detection.

A UI test should fail if important text bounding boxes intersect unexpectedly or extend beyond their containers.

Test at least:

- 360 × 760 logical size.
- 720 × 1520.
- 1080 × 2280.
- 1440 × 3040.

Include tests for long strings, invalid battery readings, large uptime values, missing network information and different times of day.

---

# 10. THE USER WANTS THE ACTUAL NUXEL VM LOOK

**DO NOT REINVENT NUXEL'S VISUAL IDENTITY.**

The repository already contains the VM interface and its design assets.

Inspect:

`pwa/nuxel-home/`

`pwa/nuxel-home/css/`

`pwa/nuxel-home/js/`

`shell/nuxel-home-native/`

`shell/nuxel-home-native/nuxel_home/style.css`

`vm/`

`assets/nuxel-background.png`

Review the actual running VM's home screen if the VM is available.

Capture VM reference screenshots at a comparable portrait phone viewport.

If the VM is not running, render the existing PWA using a suitable local browser or review its implementation and assets directly.

Do not invent a visual design from memory.

## 10.1 Preserve VM design language

The VM Nuxel Home already uses:

- Deep navy backgrounds.
- Blue accents.
- Clean white typography.
- Nuxel branding.
- Mobile status bar.
- App grid.
- App icons.
- Bottom dock.
- Search interface.
- Quick settings.
- Phone-first proportions.

Reuse the existing design tokens and assets.

The existing PWA uses colors including:

- Background `#0a1628`.
- Secondary background `#0d1f3c`.
- Cards `#122952`.
- Accent blue `#3b82f6`.
- White foreground.
- Muted blue secondary text.

Use the repository CSS and assets as the authoritative reference.

Avoid the current oversized debug-clock appearance.

## 10.2 Typography upgrade

The current framebuffer UI uses a simple scaled 5×7 bitmap font.

This is adequate for early diagnostics, but not for a polished phone environment.

Improve typography using a technically suitable approach.

Options include:

- A small rasterized font atlas generated on the MacBook.
- A suitable permissively licensed bitmap/font-rendering library.
- Build-time prerendered glyphs.
- An embedded font renderer capable of antialiasing.

Choose an approach that works on the available Fedora/framebuffer environment.

Requirements:

- Clean readable type.
- Multiple font sizes.
- Proper ascent/descent and baseline handling.
- Text measurement.
- Truncation/ellipsis.
- UTF-8 support appropriate to the selected font.
- Consistent alignment.
- No text overflowing cards.
- Reasonable memory consumption.

Do not distribute proprietary system fonts without authorization.

## 10.3 Proper app launcher

The native interface should present real Nuxel phone functions rather than only diagnostic shortcuts.

Where already implemented in Nuxel:

- Home.
- Search.
- Settings.
- Files.
- System.
- Logs/diagnostics.
- Phone.
- Messages.
- Contacts.
- Camera.
- Power controls.

Only mark an application as available when its actual executable or backend works on the device.

Unavailable functions should have a clear disabled or development state rather than pretending to work.

Build the interface to match the VM's launcher structure as closely as possible.

Do not destroy the existing functional diagnostic pages. Integrate them into a developer/system section.

## 10.4 Graphics limitation

The current S10+ kernel has a functional Samsung framebuffer path.

It does not have a demonstrated working DRM/KMS backend for Phoc.

The VM's GTK4/libadwaita and PWA interfaces may rely on Wayland/Chromium capabilities not yet available on this phone.

Therefore:

**DO NOT CLAIM THAT COPYING GTK/CSS FILES MAKES THE SAME GUI EXECUTE ON THE S10+.**

Choose the best technically viable path.

If a matching high-quality framebuffer-native interface can be developed using the existing design assets, do that.

If a true compositor is necessary, keep the DRM/KMS kernel-porting effort as a separate engineering track.

The immediate target is VM-like visual design and genuine native interaction.

Document any functionality differences honestly.

---

# 11. CRITICAL TOUCHSCREEN BUG — INCORRECT EVDEV IOCTLS

The actual S10+ kernel has already enumerated:

`sec_touchscreen`

on:

`/dev/input/event2`

in a normal boot.

However, the UI did not discover it correctly.

Source inspection identified invalid ioctl construction in:

`tools/s10plus/nuxel-ui.c`

## 11.1 Fix EVIOCGBIT

Current implementation:

`0x80000000 | (len << 16) | (ev << 8) | 0x20`

This places the event type in the wrong field.

For:

`EVIOCGBIT(EV_ABS, 32)`

the correct request on the target Linux ABI is:

`0x80204523`

The current code produces:

`0x80200320`

Correct this using Linux's actual `_IOC` encoding.

Prefer using a verified Linux UAPI definition or an equivalent implementation tested against those definitions.

## 11.2 Fix EVIOCGABS

The source also constructs the absolute-axis ioctl incorrectly.

Correct requests for the target ABI include:

`EVIOCGABS(ABS_MT_POSITION_X) = 0x80184575`

`EVIOCGABS(ABS_MT_POSITION_Y) = 0x80184576`

The existing requests do not match those values.

The structure size and command number must be correct.

Verify all related ioctl definitions, not only those two.

Add compile-time or offline tests against Linux input UAPI headers.

## 11.3 Validate touchscreen detection live

After the fixes:

1. Enumerate actual `/dev/input/event*` devices.
2. Query their names and capabilities.
3. Identify the device using `EV_ABS` and `INPUT_PROP_DIRECT`, not only a hard-coded event number.
4. Read actual X/Y minimum and maximum.
5. Read slot and tracking-ID capabilities.
6. Confirm the expected device is the panel touchscreen.
7. Report ioctl failures and errno explicitly.
8. Handle devices appearing after UI startup.
9. Reconnect cleanly if the input node disappears and reappears.

Do not assume `/dev/input/event2` will always be the correct device after future kernel changes.

## 11.4 Correct multitouch Type B event handling

Inspect the existing input loop.

It currently relies heavily on `BTN_TOUCH` release and the last received X/Y values.

Implement proper handling of:

- `ABS_MT_SLOT`.
- `ABS_MT_TRACKING_ID`.
- `ABS_MT_POSITION_X`.
- `ABS_MT_POSITION_Y`.
- `SYN_REPORT`.
- BTN_TOUCH where provided.

Correctly associate coordinates with individual contacts.

Handle touch-down and release ordering.

Avoid using stale coordinates from a previous contact.

Prevent ghost taps and duplicate click events.

## 11.5 Coordinate mapping

Use the actual device's minimum and maximum ABS values.

Map coordinates to the measured screen dimensions.

Support rotation and inversion only where the device's actual event behavior requires it.

Test:

- Top-left tap.
- Top-right tap.
- Bottom-left tap.
- Bottom-right tap.
- Center tap.
- Vertical swipe.
- Horizontal swipe.
- Repeated rapid taps.
- Touch release.

Do not guess orientation.

Use physical evidence to validate it.

---

# 12. PHYSICAL TOUCH TEST AGREEMENT

CodeSeeQ can read touchscreen events, but it cannot physically touch the Samsung.

The user can provide the required input.

When the capture process is armed, request a short physical test: several taps across the screen and a drag/swipe.

Do not stop for routine software permissions, but do not claim touch works without this real test.

A previous A26 touch capture was reported as zero bytes.

Check whether that old capture window has expired.

Start a fresh bounded capture if necessary.

If events still do not arrive after the ioctl fix, investigate:

- Touch controller power state.
- Driver input-open behavior.
- Interrupt delivery.
- SEC touchscreen firmware state.
- Charger/normal boot mode.
- Samsung sensor and regulator dependencies.
- Event-device permissions.

Do not modify power regulators blindly.

Do not disable battery or thermal safeguards.

Once actual touch events are captured, map them into the existing UI hit-testing and gesture system.

**TOUCH SUCCESS REQUIRES THE USER TO PHYSICALLY NAVIGATE THE NUXEL INTERFACE.**

---

# 13. IMPORTANT FRAMEBUFFER SAFETY CORRECTION

The current native UI contains another problem.

The application opens:

`/dev/fb0`

before checking its own single-instance PID guard.

On this Samsung, previous experiments showed that closing a framebuffer descriptor can invoke the DECON release path and disable the panel.

Thus a second UI process that opens the framebuffer and then refuses to run may still cause damage to the active display state.

## Required correction

Move exclusive framebuffer ownership acquisition BEFORE opening `/dev/fb0`.

Use a reliable atomic lock or another verified single-owner mechanism.

Only after ownership has been acquired may the UI open and map the framebuffer.

Handle stale process identities safely.

Never use PID existence alone as proof that a particular process owns the display.

The lock must remain effective across:

- Service restarts.
- Failed starts.
- Console reconnects.
- Repeated deployment.
- Application crashes.
- Stale state files.

Do not run a second framebuffer client to test the locking behavior on the actual phone.

Test refused-second-client behavior using a fake framebuffer or offline harness.

Retain the working MP4-to-UI transition.

Do not let multiple renderers draw to the panel simultaneously.

---

# 14. FIX THE UI'S SCREENSHOT AND DIAGNOSTIC PATH

The current GUI supports screenshots through its own command FIFO:

`/run/nuxel-ui.cmd`

Preserve this interface.

A26 documentation identifies a screenshot argument parsing bug where:

`screenshot small`

can incorrectly treat `small` as a filename.

Fix the command parser.

Support unambiguous commands such as:

- `screenshot`
- `screenshot /path/to/file.ppm`
- `screenshot small`
- `screenshot /path/to/file.ppm small`

Verify the parser accepts and rejects each form correctly.

All screenshots must be captured through the already-running UI process.

Do not open `/dev/fb0` from a separate diagnostic application.

Improve the screenshot workflow so CodeSeeQ can:

1. Request a UI screenshot.
2. Receive a success/error response.
3. Pull it through the live console.
4. Verify SHA-256.
5. Render it on the MacBook.
6. Compare it against the VM reference.
7. Identify remaining layout defects.
8. Apply a live patch.
9. Repeat.

This should become the primary UI development loop.

---

# 15. LIVE GUI DEVELOPMENT — NO REFLASHING

Once Nuxel boots after the initial BOOT update, all ordinary UI improvements should happen through the live connection.

Workflow:

`SOURCE EDIT → COMPILE ARM64 → OFFLINE SCREENSHOT TEST → LIVE DEPLOY → VERIFY HASH → ACTIVATE → SCREENSHOT → REVIEW → REPEAT`

Do not reflash BOOT for font, layout, color, icon, app, touchscreen-event handler or systemd service changes that live entirely in Fedora userspace.

Do not reflash the 4 GiB rootfs for small file changes.

Use the verified Nuxel deployment script.

Before replacing an application:

1. Record the running executable version.
2. Record its SHA-256.
3. Copy the previous executable to a rollback location.
4. Transfer the new executable to a staging path.
5. Verify exact bytes and hash.
6. Atomically activate it where possible.
7. Restart only the affected component.
8. Verify the console is still accessible.
9. Verify the UI starts successfully.
10. Verify a frame is committed.
11. Roll back if the replacement fails.

Do not overwrite a running executable in place.

Do not destroy the live console while testing GUI code.

Preserve all changes in the source repository and reproducible rootfs builder.

A phone-only patch that disappears after the next full Fedora build is not acceptable.

---

# 16. HARDEN THE EXISTING LIVE DEPLOYMENT TOOL

The A26 live console has successfully demonstrated framed command output and hash-verified file pulls.

However, inspect:

`scripts/s10plus-debug-pack/nuxel-live-deploy.sh`

The supplied deploy script uses a separate raw serial transfer implementation.

It does not yet fully reuse the console's newer port locking and response-framing infrastructure.

Audit and repair:

- Concurrent port access.
- Host-side locking.
- Partial writes.
- Interrupted uploads.
- Backpressure.
- Transfer cancellation.
- Exact destination hash verification.
- Atomic installation.
- Failed service restart.
- Automatic rollback.
- Host disconnects.
- Device reconnects.
- Command exit-code handling.

The deploy tool must not report success merely because it printed an installation command.

Require an actual verified installed hash and a healthy service.

Fix the documented macOS USB `OSError: Device not configured` handling so the console reports a clean disconnection instead of a traceback.

Do not make unnecessary changes to the functioning USB gadget/kernel path.

---

# 17. FEDORA RUNTIME — PRESERVE A26 SUCCESS AND FIX REMAINING COMPATIBILITY

The A26 engineering journal reports:

`systemctl is-system-running = running`

`nuxel-ui.service = active`

`systemctl --failed = 0`

That is significant progress.

But the boot graph was repaired partly by compatibility workarounds:

- Masking systemd-userdbd.
- Switching from dbus-broker to dbus-daemon.
- Masking systemd-udevd after a worker-spawning storm.
- Adjusting NSS behavior.

These are legitimate interim bring-up measures, but not proof that every normal Fedora subsystem has full functionality.

## Required work

First preserve the working state.

Then investigate the remaining kernel/systemd 258 compatibility defects using real evidence.

In particular:

- pidfd-based child watching.
- systemd sd-event fallback behavior.
- User/group lookup services.
- Udev worker management.
- Cgroup v2 behavior.
- D-Bus.
- Logind.
- Input permissions.
- NetworkManager.
- Charging/battery reporting.
- Persistent journal storage.

A26 recorded an `asix`/wireless-related uevent storm and more than 17,000 worker attempts during one failure episode.

Do not unmask udevd blindly.

First identify and correct its worker compatibility issue and the event storm.

Test on a bounded sample before allowing unrestricted device-event processing.

Any deeper kernel repair must be separated from ordinary live UI work.

Do not sacrifice a working visible Nuxel GUI to pursue speculative systemd modernization.

Keep Fedora 43 as the rootfs.

Do not switch to Alpine or replace Nuxel with Android.

---

# 18. THE VM-QUALITY GUI ACCEPTANCE TEST

This is the central visual deliverable.

The user wants the phone interface to look substantially like the VM, not a debugging dashboard with enormous 5×7 lettering.

Use actual VM/PWA screenshots and repository design assets as references.

Prepare comparable screenshots at the same logical phone viewport.

Compare:

- Overall composition.
- Status bar.
- Logo placement.
- Typography.
- Background.
- App grid.
- Icon styling.
- Card geometry.
- Search/navigation.
- Dock.
- Padding.
- Touch target sizes.
- Visual balance.

Do not settle for a screen that merely contains the same words.

The new visual system should look deliberate, modern, polished, and recognizably Nuxel.

## Automated visual regression tests

Implement offline rendering tests for:

- Home.
- Settings.
- System.
- Logs.
- About.
- Power.
- Search/launcher if supported.
- Error/recovery states.

Verify:

- No text overlaps.
- No text extends outside its allocated container.
- No clipped clocks.
- No merged navigation labels.
- Correct color order.
- Correct physical resolution.
- Correct camera-cutout safe area.
- Consistent margins.
- Correct icons.
- Correct scrolling.
- No stale framebuffer blocks.
- No framebuffer bounds violations.

For hardware acceptance:

1. Deploy the fixed UI.
2. Render Home.
3. Capture a verified screenshot.
4. Compare it with the VM reference.
5. Have the user observe the AMOLED.
6. Test page navigation.
7. Test touchscreen.
8. Test return to Home.
9. Confirm no UI crash or display shutdown.

**THIS MILESTONE IS NOT COMPLETE UNTIL THE PHYSICAL PHONE SHOWS A CLEAN, LEGIBLE, VM-INSPIRED NUXEL HOME SCREEN.**

---

# 19. BOOT ANIMATION TO GUI HANDOFF

Preserve the now-working original Nuxel MP4-derived animation.

The successful boot sequence should be:

`SAMSUNG BOOTLOADER`

→ `NUXEL ORIGINAL FIRST FRAME`

→ `NUXEL FULL BOOT ANIMATION`

→ `FEDORA SYSTEMD READY`

→ `NUXEL HOME UI FRAME READY`

→ `ANIMATION STOPS`

→ `NUXEL INTERACTIVE HOME`

The screen must not flash back to the old diagnostic artwork.

The animation must not paint over the GUI.

The GUI must not acquire the framebuffer through a competing temporary process.

Do not stop the animation until the home UI is actually ready to display a valid frame.

If GUI startup fails, preserve a visible diagnostic fallback and the live USB console.

The user must be able to understand whether Nuxel is still booting or has encountered an error.

---

# 20. TOUCHSCREEN ACCEPTANCE TEST

After the corrected UI detects the real touchscreen:

Perform these real-hardware tests with user participation:

1. Tap Settings.
2. Return Home.
3. Tap System.
4. Return Home.
5. Tap Logs.
6. Scroll or swipe.
7. Open Power without accidentally triggering reboot.
8. Verify the power confirmation workflow.
9. Test repeated navigation.
10. Leave the interface running and verify continued responsiveness.

Use actual touch input events, not only console-injected synthetic taps.

Record coordinate mapping and physical result.

Keep the console-based `tap X Y` command as a debugging fallback.

Do not treat successful simulated tapping as proof of working touch hardware.

---

# 21. PHOSH AND COMPLETE GRAPHICAL STACK

The repository already contains:

`shell/nuxel-home-native/`

and the Fedora rootfs includes Phosh/Phoc packages.

However, the current Samsung 4.14 kernel does not have demonstrated working DRM/KMS support for Phoc.

Keep this distinction explicit.

Two separate outcomes must be tracked:

**Outcome A — VM-inspired framebuffer-native Nuxel interface**

A real working interactive Linux phone UI built on the existing display path.

**Outcome B — Full Phosh/Phoc Wayland graphical environment**

Requires a suitable DRM/KMS graphics stack or another proven supported compositor backend.

Do not claim Outcome B has been achieved merely because Outcome A works.

Investigate the future Exynos DRM/KMS port separately.

Do not undertake an unsafe kernel upgrade during the GUI-fixing phase unless it is necessary, justified, and independently validated.

Prioritize making the already working Fedora framebuffer interface usable first.

---

# 22. STRICT HARDWARE AND RECOVERY LIMITS

The user explicitly authorizes this planned TWRP BOOT update and subsequent autonomous software development on their expendable Samsung.

Routine authorized testing does not require repeated confirmation.

However:

- Never erase or overwrite RECOVERY.
- Never modify EFS or SEC_EFS.
- Never modify Samsung bootloader or PIT.
- Never repartition.
- Never alter radio calibration.
- Never flash modem firmware.
- Never change hardware fuses.
- Never disable critical battery or thermal protections.
- Never flash unrelated partitions.
- Never write raw BOOT/USERDATA partitions from the running Fedora system.
- Never execute a destructive flash without confirming the target device and image.

Retain a verified recovery route and last known working BOOT candidate.

Do not perform repeated automatic boot experiments without new evidence.

If the planned BOOT update fails and the live console does not return, report the recovery requirement and wait for the necessary manual intervention.

Do not claim software recovery is possible if the host no longer has an actual command channel.

---

# 23. PERSISTENT ENGINEERING RECORDS

Continue using:

`docs/s10plus-autonomous-boot-repair/`

Update:

- `STATUS.md`
- `NEXT-ACTION.md`
- `ROOT-CAUSE.md`
- `BOOT-STAGES.md`
- `TEST-RESULTS.md`
- `DEVICE-OBSERVATIONS.md`
- `DISPLAY-BRINGUP.md`
- `LIVE-DEBUG-CONNECTIVITY.md`
- `A26-SEAMLESS-BOOT-ANIMATION.md`
- `A26-PHONE-UI-ACCEPTANCE.md`
- `A26-TOUCHSCREEN-ACCEPTANCE.md`

Create:

- `A27-BOOT-FLASH-RECEIPT.md`
- `A27-LIVE-RUNTIME-BASELINE.md`
- `NUXEL-GUI-LAYOUT-ROOT-CAUSE.md`
- `NUXEL-VM-DESIGN-PARITY.md`
- `NUXEL-TOUCH-IOCTL-REPAIR.md`
- `NUXEL-INPUT-EVENT-ACCEPTANCE.md`
- `NUXEL-FRAMEBUFFER-OWNERSHIP-REVIEW.md`
- `NUXEL-GUI-VISUAL-ACCEPTANCE.md`
- `NUXEL-LIVE-DEPLOYMENT-QUALITY.md`

Every significant change must record:

- Source files.
- Justification.
- Actual defect.
- Tests.
- Exit codes.
- Built artifacts.
- SHA-256 hashes.
- Deployment result.
- Runtime result.
- Physical hardware observation.
- Rollback instructions.

Preserve all current images and logs.

---

# 24. EXACT EXECUTION ORDER

The user is placing the phone in TWRP now.

**PHASE A — ONE CONTROLLED BOOT UPDATE**

1. Verify TWRP and root ADB.
2. Capture previous-boot evidence.
3. Read the A26 seamless-animation notes.
4. Complete the missing NUXSPL01 renderer.
5. Validate the actual first-frame asset.
6. Compile the corrected ARM64 first-light binary.
7. Build a complete new BOOT image.
8. Preserve the existing Fedora rootfs and runtime fixes.
9. Pass all release checks.
10. Flash BOOT only.
11. Verify exact SHA-256 readback.
12. Reboot normally into Nuxel.

**PHASE B — AUTOMATIC LIVE RECONNECTION**

13. Discover the Nuxel USB console.
14. Establish verified command execution.
15. Verify Fedora is running.
16. Verify systemd and Nuxel services.
17. Verify original animation and UI handoff.
18. Record the new runtime baseline.

**PHASE C — FIX THE ACTUAL GUI**

19. Fix the clock layout overflow.
20. Fix vertical text overlap.
21. Fix dock labels.
22. Fix all settings/system row measurements.
23. Implement layout clipping and bounding boxes.
24. Improve typography.
25. Match the existing VM design.
26. Build offline screenshot regression tests.
27. Fix framebuffer ownership before opening the device.
28. Fix screenshot argument parsing.
29. Deploy the corrected UI live.
30. Verify actual AMOLED output.

**PHASE D — FIX PHYSICAL TOUCH**

31. Correct evdev ioctl encoding.
32. Verify touchscreen discovery.
33. Read actual ABS capabilities.
34. Capture physical touch events.
35. Correct Type B multitouch handling.
36. Fix coordinate transformation.
37. Connect touch events to real UI actions.
38. Verify actual finger-driven navigation.

**PHASE E — STABILIZE AND FINISH**

39. Harden the live deployment tool.
40. Verify Fedora service health.
41. Preserve A26 compatibility repairs.
42. Investigate remaining masked-service limitations.
43. Verify no renderer collisions.
44. Verify no spontaneous resets.
45. Verify boot animation remains seamless.
46. Verify live console reconnect and deployment.
47. Update the S10+ milestone and completion table.
48. Document remaining Phosh/DRM dependencies separately.

Do not stop after completing only the first planned flash.

Continue into live Nuxel development automatically.

---

# 25. FINAL ACCEPTANCE GATES

The mission is successful when the following have been demonstrated on the physical Samsung.

## GATE 1 — BOOT VISUALS

- Correct original Nuxel opening frame.
- No obsolete two-second splash.
- Smooth original boot animation.
- Clean handoff to the UI.
- No visual regressions.

## GATE 2 — LIVE CONTROL

- Functional USB command execution.
- Verified file transfer.
- Working service management.
- Reliable reconnect.
- No TWRP needed for ordinary userspace changes.

## GATE 3 — GUI QUALITY

- No overlapping text.
- Proper clock scaling.
- Clean bottom navigation.
- Modern Nuxel typography.
- VM-inspired styling.
- Usable Settings, System and Logs pages.
- Correct display output.
- No duplicate framebuffer processes.

## GATE 4 — TOUCHSCREEN

- Touchscreen ioctl requests succeed.
- Actual input device detected.
- Physical taps registered.
- Coordinates mapped correctly.
- Swipe/navigation works.
- UI responds to physical touch.

## GATE 5 — FEDORA STABILITY

- systemd operational.
- Nuxel UI service operational.
- Necessary services healthy.
- No uncontrolled process storms.
- Persistent logs accessible.
- No unexpected reboot during normal testing.

## GATE 6 — HONEST GRAPHICS STATUS

Clearly state whether the device is running the framebuffer-native interface or an actual Phosh/Wayland compositor.

Do not present the framebuffer UI as Phosh.

---

# 26. FINAL DIRECTIVE

**WE HAVE A REAL LINUX PHONE BOOTING FEDORA ON THE SAMSUNG S10+.**

The remaining problem is no longer getting basic Linux to start.

The immediate problems are the incomplete early-splash replacement, broken UI geometry, broken evdev ioctl requests, and unfinished visual polish and touch interaction.

Perform the one planned TWRP BOOT update.

Then keep the phone running Nuxel.

Use the live console to finish everything else.

Do not rebuild or reflash the whole operating system for ordinary application changes.

Do not redesign the Nuxel identity from scratch.

Use the actual VM design and assets.

Fix the current source instead of layering temporary visual workarounds onto it.

Preserve the Fedora, kernel, AMOLED, animation and console milestones we've already achieved.

## FINAL WoNQ MISSION

**SAMSUNG LOGO → ORIGINAL NUXEL BOOT ANIMATION → BEAUTIFUL NUXEL HOME SCREEN → WORKING TOUCHSCREEN → STABLE LINUX PHONE.**

NO MORE NUXDOWN 95 GLITCH EDITION.

NO MORE GIANT CLOCK OVERFLOW.

NO MORE FUSED NAVIGATION LABELS.

NO MORE TOUCHSCREEN DETECTION BUGS.

ONE PLANNED TWRP TRIP. THEN LIVE NUXEL DEVELOPMENT.

**FINISH THE INTERACTIVE NUXEL PHONE OS.**

🐧🔥 EXECUTE NOW.

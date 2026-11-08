# PWNAGE-38000 — NUXEL END-TO-END AUDIO RESTORATION

**Project:** Nuxel  
**Target device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**Mission priority:** Critical — audio functionality  
**Status:** Do not mark complete until the required hardware-supported outputs have been tested.

## 0. Executive mandate

Nuxel needs a complete, reliable audio system.

Bluetooth functionality has recently improved and appears to work. Preserve that progress while investigating and repairing the complete audio pipeline, from physical audio hardware and kernel interfaces through ALSA, audio services, routing, application playback, volume controls, and the user interface.

The target is straightforward:

**When the user selects a supported audio output and plays a sound, the sound must actually be audible through that output.**

The required outputs are:

- Built-in loudspeaker.
- Wired headphones.
- Bluetooth headphones and speakers.
- USB-C to HDMI/display audio.
- USB-C headphones.
- USB-C-to-3.5-mm headphone adapters.

Use the real capabilities of the S10+ and the connected accessories to determine the precise implementation needed for each route. Do not assume that all USB-C adapters use the same technology or that every USB-C display connection provides audio automatically.

In addition to restoring normal playback, implement audible feedback using `./assets/nuxel-pow.mp3`:

1. Play a brief confirmation sound after Nuxel's audio subsystem has initialized and an appropriate output route is ready.
2. Play the sound after a real volume change.
3. Add a working Test Audio button to Audio Settings.
4. Ensure the test button plays the same sound through the currently selected output.
5. Verify actual audible output rather than trusting software return codes.

This is a delivery mission, not a research-only task. Inspect the code, establish a baseline, fix the causes, build and deploy safely, test the physical outputs, and report the evidence.

---

# 1. Safety, compatibility, and non-negotiable requirements

- Preserve existing working Bluetooth functionality.
- Preserve the current bootable installation and recovery routes.
- Do not flash firmware, replace the kernel, modify partitions, or change the bootloader as part of an unapproved workaround.
- Do not blindly change device-tree configuration, codec registers, mixer values, or hardware-specific routing.
- Back up any configuration before changing it and document rollback.
- Do not disable audio security or permissions checks merely to make playback work.
- Do not create a fake audio device or report playback success when the hardware remains silent.
- Do not silently fall back to a different output while claiming that the selected output worked.
- Do not force maximum volume for test playback.
- Do not play overlapping sounds indefinitely when volume keys are held.
- Do not break microphone input, call audio, Bluetooth, USB networking, display functionality, or unrelated services while fixing playback.
- Do not introduce a second competing audio manager if Nuxel already has an authoritative audio framework.
- Do not assume that a modern PipeWire or PulseAudio configuration is present. Inspect the actual running environment and use its existing architecture where possible.
- Do not report physical-device testing unless it actually happened.

The desired end state is fully functional audio on the supported hardware paths. A software-only change cannot compensate for a genuinely missing driver, unsupported adapter, or absent hardware capability; such blockers must be demonstrated precisely and addressed through the appropriate safe engineering work rather than concealed.

---

# 2. Establish the actual system architecture

Before making changes, inspect the running phone and repository.

## 2.1 Identify the current platform

Verify:

- Device model and hardware revision where available.
- Running kernel version and configuration.
- Userspace distribution and release.
- Audio codec and amplifier hardware, where discoverable.
- Loaded audio-related kernel modules.
- Available sound devices and PCM interfaces.
- Available mixer controls.
- Running audio services and their versions.
- Current audio policy and routing configuration.
- Permissions and access to audio device nodes.
- Existing Nuxel Audio Settings implementation.
- Existing volume-key event handling.
- Existing sound-effect playback implementation, if any.
- The location, format, duration, and decoding compatibility of `./assets/nuxel-pow.mp3`.

Inspect actual system state. Do not assume the device has the same configuration as a desktop Fedora installation or a conventional Android installation.

## 2.2 Discover the active audio framework

Determine whether playback is routed through:

- Direct ALSA.
- A PulseAudio-compatible service.
- PipeWire and its relevant session/policy components.
- A custom Nuxel audio service.
- Another existing audio abstraction.

Identify which service or component owns routing and volume.

There must be one clear authoritative path for audio state and output selection. Avoid creating competing daemons or independently controlling the same hardware through multiple layers.

If the project currently has no appropriate audio abstraction, design a minimal one that fits the existing architecture.

## 2.3 Establish a baseline

For each currently available output, record:

- Whether the device is detected.
- Whether an output route is exposed.
- Whether the selected route is considered active.
- Whether playback starts.
- Whether the sound is physically audible.
- Whether volume changes affect the actual hardware.
- Whether errors appear in application logs, audio-service logs, kernel logs, or mixer state.

Record actual device identifiers, codec information, service names, and relevant log excerpts.

Do not publish secrets, saved wireless credentials, Bluetooth pairing secrets, or unrelated personal data in evidence files.

---

# 3. Diagnose the complete playback pipeline

Follow a test sound from the application to the physical output.

The expected chain is conceptually:

Application or sound-effect service → audio API → sound server or ALSA → routing/policy → mixer controls → codec/driver → amplifier or output device → audible sound.

Determine the actual chain used by Nuxel.

At every layer, establish:

- Whether the component exists.
- Whether it is running.
- Whether the next layer is available.
- Whether the stream is accepted.
- Whether the correct device is selected.
- Whether data reaches the physical output path.
- Whether errors are reported or silently ignored.

Inspect the appropriate logs and hardware state rather than guessing.

Distinguish at least these failure classes:

1. Application cannot open or decode the asset.
2. Audio service is unavailable.
3. No PCM or output device is exposed.
4. Device is exposed but no valid route is selected.
5. Mixer controls are muted or configured incorrectly.
6. Codec or amplifier initialization fails.
7. Audio reaches the wrong output.
8. Playback succeeds in software but no physical sound is produced.
9. The output is functional but volume controls do not affect it.
10. The device disconnects or fails when the route changes.

Fix the earliest real failure in the pipeline and then retest downstream behavior.

---

# 4. Built-in loudspeaker restoration

The built-in speaker is a primary acceptance target.

## 4.1 Investigate the hardware path

Identify the actual codec, amplifier, relevant device-tree configuration, loaded drivers, and audio-routing implementation for the installed S10+ system.

Check:

- Kernel logs during audio initialization.
- Missing or failed codec/amp probes.
- Required firmware, if applicable.
- Available ALSA cards, PCM devices, and mixer controls.
- Mute and gain settings.
- Amplifier enablement and power-management state.
- Correct routing from playback PCM to the speaker.
- Whether the expected sound device is exposed to the active audio framework.
- Whether Nuxel runs with the permissions required to access it.

Use read-only inspection first. Do not blindly write registers or change hardware-specific mixer controls.

## 4.2 Restore playback

Ensure a valid PCM or framework-level playback route reaches the physical loudspeaker.

The implementation must correctly handle:

- Audio initialization.
- Stream creation.
- Format negotiation.
- Sample rate and channel count.
- Buffering and underruns.
- Volume and mute.
- Stream closure.
- Error reporting.

Use the existing supported playback interface when possible.

## 4.3 Verify physically

Play `nuxel-pow.mp3` through the built-in speaker at a safe, moderate volume.

Confirm that the sound is physically audible.

A successful process exit or a nonzero PCM write count is not, by itself, proof that the amplifier and speaker produced sound.

---

# 5. Wired headphone routing

Investigate wired audio paths separately rather than treating every headphone connection as equivalent.

## 5.1 Supported physical paths

Determine which of the following are supported by the current device and accessories:

- A conventional analog headphone jack, if present on the actual device.
- USB-C audio accessories.
- USB-C-to-3.5-mm adapters with an active DAC.
- USB-C adapters using passive analog audio accessory mode, if the device and adapter support it.

Do not assume that a USB-C connector automatically exposes analog audio.

## 5.2 Insertion and route detection

When a supported headphone device is connected:

- Detect its actual presence.
- Identify the device type.
- Make the output available to the audio framework.
- Select the intended route according to Nuxel's audio policy.
- Avoid sending the sound to a disconnected or stale output.
- Update Audio Settings from actual device state.

When the device is removed, restore a valid available output according to the established policy.

Avoid abrupt or dangerously loud route changes.

## 5.3 Verification

Test each available wired accessory separately.

For each one:

1. Connect the accessory.
2. Verify device discovery.
3. Verify output-route selection.
4. Press Test Audio.
5. Confirm the sound is audible in the headphones.
6. Change volume.
7. Confirm the real output level changes.
8. Disconnect the accessory.
9. Confirm the route returns to an available output.

Record the adapter model and whether it is an active DAC or a passive adapter. Do not claim support for an adapter type that has not been demonstrated.

---

# 6. Bluetooth audio restoration and preservation

Bluetooth functionality appears to be working now. Preserve it and establish repeatable audio-output tests.

Inspect the existing Bluetooth stack, device discovery, pairing state, profile availability, audio-session creation, and routing.

Determine whether the connected device exposes an appropriate playback profile and whether Nuxel's audio framework can select it.

Requirements:

- Preserve successful Bluetooth discovery and pairing.
- Select an actual playback-capable profile.
- Route audio to the connected device.
- Update the UI when the device connects or disconnects.
- Keep volume controls synchronized with the selected route where supported.
- Recover from temporary disconnection.
- Avoid breaking other Bluetooth functions while repairing audio.

Do not assume that a successful Bluetooth connection means an audio profile is connected.

Test with a paired, available Bluetooth speaker or headphone device:

1. Connect it.
2. Confirm the playback profile is active.
3. Press Test Audio.
4. Confirm the sound is audible through Bluetooth.
5. Change volume and confirm the output responds.
6. Disconnect it and confirm that Nuxel recovers gracefully.

Do not claim Bluetooth audio is fixed solely because Bluetooth pairing works.

---

# 7. USB-C headphones and USB-C-to-3.5-mm adapters

USB-C audio must be treated as a distinct hardware path.

## 7.1 Identify the actual accessory

Determine whether the connected adapter is:

- A USB Audio Class device with an active DAC.
- A passive analog adapter that relies on USB-C analog audio accessory support.
- Another proprietary or unsupported accessory.

Inspect the actual USB descriptors, device events, kernel logs, and audio devices exposed after connection.

Do not infer the adapter type from the physical connector alone.

## 7.2 Active USB DAC support

For a USB Audio Class device:

- Verify USB enumeration.
- Check whether the existing kernel exposes the necessary USB audio support.
- Confirm that an ALSA card or appropriate audio endpoint appears.
- Confirm the audio framework discovers the device.
- Select the correct output route.
- Handle sample-rate, channel-count, and format negotiation.
- Ensure device removal and reconnection work.
- Avoid leaving stale device entries in Audio Settings.

If the active USB DAC is detected by the kernel but ignored by Nuxel, fix userspace discovery and routing.

If the kernel does not expose the required functionality, document the exact missing driver or configuration capability and the safe next step. Do not replace the kernel blindly.

## 7.3 Passive analog adapter support

A passive adapter cannot be made functional by software alone if the phone does not provide the required analog audio mode or hardware support.

Determine whether the specific S10+ hardware, firmware, and current system support that mode.

If it does, implement the required detection and routing. If it does not, document the exact hardware limitation and test a supported active USB DAC adapter instead.

Do not claim universal USB-C headphone compatibility without testing the relevant accessory types.

## 7.4 Verification

Run the same playback, volume-change, disconnection, and reconnection tests used for other outputs.

The device must be tested physically.

---

# 8. USB-C HDMI / DisplayPort Alt Mode audio

USB-C HDMI audio requires more than an audio-player change. It depends on the display transport and the audio path exposed by that transport.

## 8.1 Inspect display and audio capabilities

Determine how the current S10+ build handles:

- USB-C DisplayPort Alt Mode negotiation.
- Display connection and hotplug detection.
- The current display output stack.
- Any HDMI adapter or dock in use.
- Audio capability discovery and display-audio endpoints.
- The kernel and driver support required for audio over the display connection.
- The audio framework's ability to expose and select the display output.

Do not assume that a working USB-C connection or working video output proves that HDMI audio is supported.

## 8.2 Implement routing where supported

When the connected adapter/display exposes an actual audio output:

- Discover the output.
- Add it to the audio routing model.
- Make it selectable in Audio Settings.
- Route playback to the display endpoint.
- Keep volume and mute state coherent with the actual endpoint's capabilities.
- Handle display disconnects and reconnects.
- Recover to a valid output when the display audio endpoint disappears.

If the display path lacks a necessary driver or endpoint, identify the exact blocker. Do not create a fake HDMI output entry.

## 8.3 Verification

Connect the phone to an HDMI display or receiver with known-working speakers.

Confirm:

1. The display connection is active.
2. The audio endpoint is actually exposed.
3. Nuxel selects the intended endpoint.
4. Test Audio plays `nuxel-pow.mp3`.
5. The sound is physically audible through the display/receiver.
6. Disconnecting the display restores a valid audio route.

Video output alone is not sufficient evidence of HDMI audio functionality.

---

# 9. Create a single authoritative audio-routing model

Review the current Audio Settings implementation and audio-service integration.

Avoid having the UI maintain a separate, fabricated list of audio devices.

The authoritative audio model should report, where supported:

- Available output devices.
- Device type.
- Connection status.
- Current selected output.
- Actual mute state.
- Current volume.
- Whether playback is available.
- Playback errors.
- Relevant capabilities and limitations.

Use the project's existing data model if it is sound. Extend it only as necessary.

Audio Settings must distinguish:

- An output that is physically connected.
- An output that is detected by the OS.
- An output that is usable by the audio framework.
- An output that is currently selected.
- An output that has actually passed a physical playback test.

Do not represent these as interchangeable states.

If a route cannot be tested, show its actual status rather than claiming that it works.

---

# 10. Implement `nuxel-pow.mp3` playback

The required asset is:

`./assets/nuxel-pow.mp3`

Inspect its existence, file size, format, sample rate, channel count, duration, and decoding compatibility.

Ensure the asset is included in the deployed installation at a known, stable location. Do not depend on the current working directory being the repository root.

## 10.1 Reuse the proper playback path

Use the same authoritative audio playback and routing infrastructure as normal system audio.

Do not create a second playback system solely for this sound effect if a suitable shared service exists.

The sound-effect API should:

- Resolve the deployed asset path reliably.
- Verify that the asset is available.
- Decode it using an installed, supported decoder.
- Respect the currently selected output.
- Respect mute and volume policy.
- Avoid blocking the UI thread.
- Handle missing assets, decoder failures, and unavailable outputs.
- Release playback resources correctly.
- Report the actual result of the playback request.

If MP3 decoding is unavailable, identify the missing dependency or decoder support and add the smallest compatible solution that fits the existing environment. Do not silently replace the sound with a different file.

## 10.2 Playback behavior

Provide one reusable sound-effect operation, conceptually equivalent to:

`play_system_sound("nuxel-pow.mp3")`

Adapt this to the real codebase and naming conventions; do not add a redundant abstraction if one already exists.

Ensure the operation cannot spawn unbounded players or build a queue of old sound effects.

If a sound is already playing, apply a deliberate policy: avoid overlapping copies or coalesce repeated requests. Do not let repeated volume events cause an audio storm.

---

# 11. Play a confirmation sound after audio initialization

After the audio subsystem has initialized and a usable output route is available, play `nuxel-pow.mp3` once as an audible confirmation.

Important requirements:

- Do not play the sound before an output is ready.
- Do not delay startup waiting for the sound to finish.
- Do not make sound playback a prerequisite for opening the lockscreen.
- Do not replay it on every service restart or repeated initialization event.
- Do not report success if playback failed.
- Do not repeatedly retry in a tight loop.
- Handle a late-appearing output gracefully.

If audio initialization succeeds before a physical output is available, defer the confirmation until a usable route appears, subject to a bounded and clearly defined policy.

If the output remains unavailable, record the failure and allow the rest of Nuxel to operate normally.

If a normal reboot or service restart causes initialization to run again, ensure the sound is emitted only once for the relevant initialization lifecycle, not continuously.

Use a reasonable, safe volume. Never force maximum volume to make the confirmation audible.

The confirmation must be tested on the actual device.

---

# 12. Play `nuxel-pow.mp3` when volume changes

Implement audible volume-change feedback through the currently selected output.

## 12.1 Define the event semantics

Trigger the sound only after a genuine volume change has been accepted by the authoritative volume control.

Do not play it when:

- The requested volume was rejected.
- The volume was already at the same level.
- A UI redraw merely repeats the current value.
- An unrelated device status changes.
- The volume value is restored internally without a user-requested adjustment, unless the established product design explicitly treats that as a feedback event.

Avoid a feedback loop in which the sound-effect playback itself causes repeated volume-change events.

## 12.2 Rate-limit and coalesce rapid changes

When the user holds a volume key or drags a slider, many changes can arrive quickly.

Implement a small, bounded debounce/coalescing policy so the feedback remains responsive without generating a backlog of overlapping sounds.

Requirements:

- Do not spawn one independent audio player for every volume step.
- Do not queue dozens of delayed sounds.
- Do not block the volume control.
- Do not make the volume adjustment wait for the sound to finish.
- Do not replay the sound indefinitely while a control is held.
- Ensure the final volume value is accurate.
- Ensure mute behavior remains respected.

The feedback should confirm an actual change, not become an irritating stream of repeated sounds.

## 12.3 Respect output and mute state

Play the sound through the selected route, not an unrelated default device.

If the selected route is disconnected or unavailable, do not silently play through a different output and claim the selected output worked.

If the system is muted, respect the mute state rather than overriding it. If Nuxel's existing policy explicitly allows certain system sounds while muted, follow that policy consistently and document it.

Do not raise the volume temporarily to make the feedback audible.

## 12.4 Test

Test:

- A single volume increase.
- A single volume decrease.
- Multiple rapid keypresses.
- Holding a volume key.
- Slider changes.
- Muted state.
- Volume at minimum and maximum.
- Route changes during playback.
- A disconnected output.
- Audio-service failure.

Confirm that the volume changes and the sound effect both behave correctly.

---

# 13. Add a Test Audio button to Audio Settings

Add a clear, accessible **Test Audio** button to the existing Audio Settings screen.

Use the existing visual language and layout. Do not create an unrelated new settings application.

## 13.1 Button behavior

When the user presses Test Audio:

1. Read the current authoritative selected output.
2. Verify that the output is available for playback.
3. Play `nuxel-pow.mp3` through that output.
4. Keep the settings interface responsive.
5. Display an honest result.

The button must work with:

- Built-in speaker.
- Each supported wired output.
- Bluetooth audio.
- Supported USB-C audio devices.
- Supported USB-C HDMI audio.

If a route is unavailable, explain the reason rather than reporting a successful test.

## 13.2 UX requirements

- Keep the button visible and easy to press on the phone's screen.
- Provide immediate input feedback.
- Do not block the UI while the sound is playing.
- Avoid launching multiple overlapping test players if the user presses repeatedly.
- Allow a subsequent test after the previous one completes.
- Provide an actionable error message when playback fails.
- Do not confuse "playback request accepted" with "physical sound confirmed."

The UI may report that a playback request was sent or completed at the software level, but only a physical listening test can confirm that sound actually came out.

## 13.3 Test-button regression tests

Verify:

- The button is present in Audio Settings.
- It invokes the shared sound-effect playback path.
- It uses the currently selected output.
- It handles missing assets.
- It handles unavailable routes.
- It handles audio-service failures.
- Repeated taps do not create unbounded playback instances.
- The interface remains responsive during playback.
- The button does not unexpectedly change volume or output selection.

---

# 14. Volume controls and routing consistency

Inspect physical volume keys, software volume controls, Audio Settings sliders, and the audio service's mixer state.

All controls should operate on the same authoritative volume state for the selected output, subject to hardware and protocol limitations.

Requirements:

- Volume changes affect actual playback.
- UI values reflect the real current volume.
- Mute state is accurate.
- Route changes update the available controls appropriately.
- Unsupported hardware volume controls are not falsely presented as working.
- Changing the output does not leave the UI attached to stale mixer controls.
- Bluetooth volume synchronization works where supported.
- USB and HDMI endpoints expose only the controls they actually support.
- Sound-effect playback uses the current volume and route.

If different routes have different volume-control capabilities, model those differences explicitly.

Do not assume that every hardware endpoint uses the same mixer control or volume scale.

---

# 15. Audio initialization, errors, and recovery

The audio subsystem must initialize robustly and recover from common failures.

Inspect:

- Service startup ordering.
- Permissions.
- Device discovery.
- Route changes.
- Device disconnection.
- Service crashes.
- Decoder failures.
- Resource exhaustion.
- Device-busy conditions.
- Audio stream underruns.
- Stale PCM or route handles.

Requirements:

- Nuxel remains usable when no audio output is available.
- Audio failures are reported clearly.
- The system can recover when an output appears later.
- Reconnecting a device does not require rebooting the phone.
- Bluetooth reconnection does not break built-in speaker playback.
- USB DAC disconnection does not leave the UI stuck.
- Display disconnection does not leave a stale HDMI route selected.
- An audio-service restart does not produce an endless sound-effect loop.
- A missing sound asset does not prevent the lockscreen or desktop from starting.

Use bounded retries and event-driven recovery where possible. Do not introduce infinite retry loops or repeated service restarts.

---

# 16. Test matrix and acceptance criteria

Create a test matrix containing:

- Test ID.
- Output type.
- Physical device or adapter.
- Preconditions.
- Action.
- Expected result.
- Actual result.
- Pass/fail.
- Evidence reference.

## 16.1 Built-in speaker

- Discover the internal audio device.
- Confirm a usable playback route.
- Press Test Audio.
- Confirm `nuxel-pow.mp3` is physically audible.
- Change volume in both directions.
- Confirm actual loudness changes.
- Reboot and repeat.

## 16.2 Wired headphones

For every available supported wired path:

- Connect the device.
- Verify discovery.
- Verify route selection.
- Play Test Audio.
- Confirm physical output.
- Change volume.
- Disconnect and verify recovery.

## 16.3 Bluetooth

- Connect a paired playback device.
- Verify the active audio profile.
- Play Test Audio.
- Confirm physical output.
- Change volume.
- Disconnect and verify fallback/recovery.
- Repeat after reboot.

## 16.4 USB-C audio

For each available adapter type:

- Identify the actual adapter technology.
- Verify USB/device discovery.
- Verify the correct output route.
- Play Test Audio.
- Confirm physical output.
- Change volume.
- Test disconnect/reconnect.

Do not treat a USB-C adapter as supported until the actual adapter has been tested.

## 16.5 USB-C HDMI audio

- Connect a known-working display/receiver with audio.
- Verify display transport.
- Verify that an actual audio endpoint exists.
- Select the display output.
- Play Test Audio.
- Confirm physical audio through the receiver.
- Change volume where supported.
- Disconnect and verify recovery.

## 16.6 Sound feedback

- Confirmation sound plays after audio initialization when a usable route is ready.
- No repeated confirmation sound occurs during normal UI redraws.
- Volume feedback plays after real volume changes.
- Rapid volume changes do not generate a backlog.
- Test Audio plays the same asset.
- Mute and output selection are respected.
- Missing assets and failed playback are handled correctly.

## 16.7 Regression

Confirm that:

- Bluetooth remains functional.
- Wi-Fi is unaffected.
- USB networking and console recovery remain available.
- The display and lockscreen still work.
- Navigation remains responsive.
- Audio failures do not block startup.
- The device remains usable if all external audio devices are disconnected.

---

# 17. Required physical-device evidence

For each target output, record the exact device/adapter, connection state, route selected, relevant logs, test outcome, and how physical sound was verified.

Software diagnostics alone can establish that the operating system exposed a route and accepted playback. They cannot conclusively prove that a physical speaker or headphone produced audible sound.

Where physical listening tests cannot be automated, require a human to perform and record the test. Do not mark those tests as passed merely because the software stream completed.

If an output is blocked by a kernel, firmware, device-tree, codec, display transport, or hardware limitation, provide:

- Exact observed failure.
- Relevant logs and device information.
- The layer that lacks support.
- Whether a safe userspace fix exists.
- The precise additional driver/configuration/hardware work needed.
- Any prerequisite or risk associated with that work.

Do not hide an unresolved output behind an “audio works” summary.

---

# 18. Deployment and rollback

Inspect the current build and deployment workflow.

- Preserve uncommitted changes.
- Back up modified configuration.
- Build and test before deploying.
- Deploy using the existing safe procedure.
- Preserve USB, serial, and WLAN recovery access.
- Do not flash the kernel or firmware as a blind experiment.
- Verify the running version after deployment.
- Document how to restore the previous configuration and software state.

If the necessary fix is outside the safe scope, complete the safe userspace work first and document the remaining dependency.

---

# 19. Required report

Create or update:

`docs/pwnage-38000.md`

Use the existing evidence directory if available, preferably:

`docs/beta-finalization/live/evidence/pwnage-38000/`

Include:

1. Root-cause analysis.
2. Actual audio architecture and playback chain.
3. Hardware and codec identification.
4. Every modified file and its purpose.
5. The implementation of speaker, wired, Bluetooth, USB-C, and HDMI routing.
6. The sound-effect playback implementation.
7. Volume-change feedback behavior and rate limiting.
8. The Audio Settings Test Audio button.
9. Tests performed and exact outcomes.
10. Physical-device verification for every available output.
11. Before/after behavior.
12. Build and deployment status.
13. Remaining blockers, with evidence.
14. Safe rollback instructions.

Never fabricate logs, test results, hardware support, or physical listening confirmation.

---

# 20. Definition of done

PWNAGE-38000 is not complete until every applicable requirement below is satisfied:

- [ ] Built-in loudspeaker produces actual audible sound.
- [ ] Supported wired headphones produce actual audible sound.
- [ ] Bluetooth headphones/speakers produce actual audible sound, and existing Bluetooth functionality remains intact.
- [ ] Supported USB-C headphone and active USB DAC paths produce actual audible sound.
- [ ] USB-C HDMI/display audio works on the supported display/adapter path.
- [ ] `./assets/nuxel-pow.mp3` is deployed at a stable path and plays through the selected route.
- [ ] The audio-initialization confirmation sound plays once when a usable output is ready.
- [ ] Genuine volume changes produce the sound effect without creating a playback backlog.
- [ ] Audio Settings includes a functional Test Audio button.
- [ ] Test Audio uses the selected output and reports errors honestly.
- [ ] Volume and mute controls affect the actual output where supported.
- [ ] Disconnection and reconnection do not leave stale routes.
- [ ] The UI remains responsive during playback and audio errors.
- [ ] All available physical outputs have been tested and documented.
- [ ] Unsupported or blocked output paths have been identified precisely, with evidence and the remaining engineering requirements.
- [ ] Deployment and rollback are documented.
- [ ] No unsafe firmware, kernel, bootloader, or partition modifications were performed.

## FINAL DIRECTIVE

The target is functional audio, not a prettier settings screen.

Find the actual cause. Fix the actual audio path. Play `nuxel-pow.mp3`. Test the physical output. Add the Audio Settings button. Make volume feedback work. Preserve Bluetooth. Verify each supported wired and display-audio route.

Do not declare victory because a device appears in a list. Do not declare victory because an API returns success. Do not declare victory while the speaker is silent.

**NUXEL MUST MAKE SOUND. PERIOD. 🔊🐧**

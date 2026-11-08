# PWNAGE-38000 🔊 NUXEL AUDIO: MAKE SOUND HAPPEN. PERIOD.

Read ./full-pwnage-38000.md for the full prompt, use it.

Bluetooth is now working. The next mission is to make Nuxel audio work end-to-end on the Samsung Galaxy S10+ SM-G975F (`beyond2lte`).

**HARD, NON-NEGOTIABLE TARGET: FUNCTIONAL AUDIO OUTPUT.**

Investigate the complete audio stack, implement the fixes, deploy safely, and verify real audible output. Do not stop at UI changes, detected devices, successful API calls, or a plan.

## Required outputs

1. Built-in phone loudspeaker.
2. Wired headphones through every supported and available analog/digital audio path.
3. Bluetooth headphones and speakers, building on the currently working Bluetooth functionality.
4. USB-C to HDMI/display audio, including the required USB-C DisplayPort Alt Mode, display, and audio-routing dependencies.
5. USB-C headphones and USB-C-to-3.5-mm adapters, distinguishing active USB DAC adapters from passive analog adapters and testing each available type.

## Required sound feedback

Use the existing asset `./assets/nuxel-pow.mp3`.

- Play a short `nuxel-pow.mp3` confirmation sound after the audio subsystem has initialized and a real output route is ready.
- Play the same sound after a genuine volume change, through the currently selected output.
- Add a clearly visible **Test Audio** button to Audio Settings. Pressing it must play `nuxel-pow.mp3` through the selected output.
- Ensure volume-change sounds are rate-limited/debounced so holding a volume key does not produce a backlog of overlapping sounds.
- Respect mute, output selection, and reasonable volume limits. Do not unexpectedly blast audio at full volume.
- Report playback failures honestly; never display a successful test result just because playback was requested.

## Deep investigation

Trace ALSA, mixer controls, codec and amplifier initialization, audio routing, the active sound server or audio framework, permissions, device discovery, Bluetooth profiles, USB Audio Class devices, and HDMI/display-audio integration. Inspect kernel logs and the actual hardware capabilities.

Determine the real cause of silence or broken routing. Fix the appropriate layer instead of layering workarounds over it.

**Hard rule:** Do not mark the mission complete while a required, hardware-supported output remains broken. If a missing kernel capability, firmware component, or unsupported physical adapter blocks an output, identify it precisely, complete all safe work, and provide the exact remaining engineering requirement. Do not fake compatibility or claim success without audible verification.

Do not flash firmware, replace the kernel, alter partitions, or change the bootloader blindly. Preserve Bluetooth functionality and console recovery access.

Inspect the repository and `docs/pwnage-38000.md` if present. Implement, test, deploy safely, and document every result.

**Definition of done:** Real sound from every supported target output; working volume feedback; a functional Audio Settings Test Audio button; successful `nuxel-pow.mp3` playback; and recorded physical-device test evidence.

NO MORE SILENT PENGUIN. MAKE NUXEL SPEAK. 🔊🐧

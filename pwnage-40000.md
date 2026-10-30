# PWNAGE-40000 — FINAL SPEAKER AUDIO FIX
## Get the S10+ Loudspeaker to Actually POW — and Prove It

**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820
**OS:** Nuxel, Fedora-based ARM64
**Connection:** Existing Wi-Fi SSH
**SSH key:** Use the existing working identity recorded by the latest PWNAGE-40000 deployment. The latest evidence identifies `~/.ssh/wicked_wqn_id_rsa`.
**Audio asset:** `./assets/nuxel-pow.mp3`
**Objective:** Actual audible playback through the built-in phone loudspeaker.

## THE CURRENT STATE — WE ARE CLOSE

Previous work has already established:

- Calliope firmware reaches `MUB0`.
- Both CS35L41 amplifier DSP1s report booted and running.
- `ABOX RDMA1_EN=1`.
- The ABOX RDMA1 → SPUS → SIFS1 → UAIF1 route is configured.
- Left/Right AMP PCM Gain is persistently set to 12.
- PipeWire's default sink is `alsa_output.hw_0_1`.
- The sink and hardware stream use 48 kHz.
- The RDMA1 hardware pointer advances during playback.
- The startup cue has been attempted after the boot readiness gate.

However, **physical speaker audibility is still not confirmed**.

A successful `pw-play` exit code is not proof that the speaker made sound.

## THE MOST IMPORTANT NEW DISCOVERY

The live mixer namespace contains:

`ABOX Sound Type`

Its enumerated values are:

- `0 = VOICE`
- `1 = SPEAKER`
- `2 = HEADSET`
- `3 = BTVOICE`
- `4 = USB`
- `5 = CALLFWD`

The previous PWNAGE-38000 correction selected `0 = VOICE`, even though our current task is to play through the built-in loudspeaker.

The current persistent route script does not set or verify this control.

**FIRST TARGETED EXPERIMENT: Set `ABOX Sound Type` to `SPEAKER` (enum value 1), read it back, and perform an actual loudspeaker test.**

Do not assume this is the answer until the owner confirms hearing the sound. Preserve the original value and make the change reversible.

Other confirmed details:

- `Right AMP SPK` maps to the physical SPEAKER output.
- `Left AMP SPK` maps to the RECEIVER output.
- Both output DAPM paths have previously been observed ON.
- `Left/Right AMP PCM Gain=12` corresponds to the previously working `GAIN_CTRL=0x193`.
- Gain 19 corresponds to the silent cold-boot state `GAIN_CTRL=0x273`.

Preserve the verified amplifier gain of 12 unless live measurement establishes a different requirement.

## OUR HUMAN CONFIRMATION AGREEMENT

I will have the Nuxel Notes application open with the Title field focused.

For every test:

1. Announce the test number and what is being tested.
2. Play `./assets/nuxel-pow.mp3` exactly ONCE.
3. Give me 30 seconds to hear it and react.
4. Watch the active Notes Title field.

My responses:

- `yes` = I heard it.
- `works` = I heard it.
- `no` = I did not hear it.
- Empty Title for the full 30 seconds = I did not hear it.

After `yes` or `works`, record a positive human confirmation and stop the repair loop for the current route.

After `no` or an empty 30-second response, record a negative test and continue diagnosing and fixing.

**Do not play another sound during the 30-second response window.**

Every iteration is one playback, one 30-second response window, one recorded result, and then the next repair.

## IMPORTANT NOTES INPUT PREFLIGHT

Previous PWNAGE-40000 tests failed to observe any Notes keystrokes, even though AT-SPI reported that the Title field was focused, showing and editable.

Before the first audio test:

- Verify the screen is awake.
- Verify Notes is unlocked and open.
- Verify the Title field is actually focused.
- Verify the on-screen keyboard or intended typing device is working.
- Verify that a fresh title change reaches the live Notes model and storage.
- Perform a one-time `ready` input preflight and confirm that it is detected.
- Clear the test Title and establish a fresh empty baseline.

If this cannot be verified, fix the confirmation channel before treating a blank Title as evidence of no sound.

## FIRST FIX PRIORITIES

1. Verify current boot route and preserve the working configuration.
2. Investigate and test `ABOX Sound Type = SPEAKER (1)`.
3. Confirm Right AMP → physical SPEAKER routing and stereo channel delivery.
4. Verify AMP PCM Gain is 12/12, not 19/19.
5. Verify normal sound mode, unmuted amplifiers and a valid PipeWire sink.
6. Test `nuxel-pow.mp3` at the current output volume.
7. If necessary, progressively raise the normal PipeWire sink volume in controlled steps.
8. Continue one-play / 30-second confirmation iterations until I type `yes` or `works`.
9. Update the persistent route and readiness checks with the settings that actually produced audible sound.
10. Reboot only after a working configuration has been confirmed, then repeat the audible test after boot.

## NON-NEGOTIABLES

- Focus ONLY on the internal loudspeaker for this mission.
- Preserve the correct RDMA1 48 kHz playback path.
- Use `pw-play` through PipeWire; do not fight PipeWire by opening its occupied PCM directly through ALSA.
- Use `pw-play --volume 1.0` so there is no accidental second attenuation stage.
- Preserve CS35L41 DSP1 protection firmware and thermal protections.
- Do not blindly set amplifier gain to maximum.
- You are authorized to make the necessary normal userspace, ALSA, mixer, PipeWire, service and source-code changes.
- You may temporarily increase the normal PipeWire output volume in measured steps during owner-supervised tests.
- No TWRP reflash.
- No kernel, boot-image, bootloader or firmware-partition flashing.
- No destructive reset or repartitioning.
- Preserve Wi-Fi SSH and recovery access.
- Do not mark audibility verified until a fresh `yes` or `works` appears in Notes.

## DEFINITION OF DONE

The internal S10+ loudspeaker must actually produce the Nuxel POW sound.

I must hear it and type `yes` or `works` in the Notes Title field.

The configuration must then survive a fresh boot and another successful audible test.

**Do not stop at READY, RUNNING, DMA ADVANCING, or PLAYER_OK. Stop when the speaker makes sound and I confirm it.**

🐧 **MAKE THE PENGUIN POW.**

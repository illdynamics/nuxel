# Nuxel S10+ audio — current status (2026-10-30)

Device: Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820
Userspace: Fedora 43 aarch64, PipeWire + WirePlumber
Question this document answers: **does audio work?**

## Verdict

**Almost.** The complete software path is now verified on the handset:

- ABOX Calliope reaches `MUB0`.
- Both CS35L41 DSP1 protection images report `booted=Y running=Y`.
- `ABOX RDMA1_EN=1` and the full RDMA1 → SPUS → SIFS1 → UAIF1 crossbar is set.
- `Left/Right AMP PCM Gain` is forced to and read back as `12` after every boot.
- The static default sink is `alsa_output.hw_0_1` at 48 kHz.
- RDMA1 reports `state=RUNNING` with an advancing `hw_ptr`.
- `pw-play` completes with `rc=0`, the boot cue plays once per boot, the volume
  cap is 25 %, and Settings → Sound → **Test Audio** now refuses to play unless
  the live route passes the same readiness gate as the boot cue.

The one thing **not** claimed is human audibility. Repeated three-POW rounds
played successfully, but the owner-confirmation step (a fresh `works` entry in
the live Notes title) was never entered, so the physical speaker has not been
independently confirmed. Microphone capture, wired headset audio and USB-C audio
are also untested.

Status vocabulary: **VERIFIED** means the live handset proved it in this cycle.
**NOT CONFIRMED** means the software path is present and measured but the
physical/owner result is not available. A player exit code is never treated as
proof of sound.

## Verified live route

| Stage | Observed value |
|---|---|
| Calliope core firmware | `MUB0` after bounded PM reload attempts |
| CS35L41 DSP1 (bottom + receiver) | `booted=Y running=Y`; protection `wmfw` loaded |
| Amplifier digital trim | `Left/Right AMP PCM Gain = 12 / 12` (`GAIN_CTRL=0x193`) |
| ABOX playback gate | `ABOX RDMA1_EN = 1` |
| Crossbar | RDMA1 → SPUS IN1 → SPUS OUT1 → SIFS1 → UAIF1 SPK |
| SPKAMP mapping | `SPKAMP A/B = RDMA1` |
| PipeWire sink | `alsa_output.hw_0_1`, `s16le 2ch 48000Hz` |
| Default sink | `alsa_output.hw_0_1`, selected and read back by name |
| RDMA1 runtime | `rate=48000`, `state=RUNNING`, `hw_ptr` advancing |
| Volume ceiling | 25 %; bridge and hardware volume keys share the cap |
| Boot cue | `nuxel-boot-sound.service` runs once after route readiness |
| Settings Test Audio | route gate first, then `pw-play --volume 1.0 nuxel-pow.mp3` |
| Result honesty | API reports `audible: unverified` |

## Functions and controls that exist

- **Playback routing:** `nuxel-audio-route.service` applies the proven RDMA1
  route at boot and on a retry timer; `nuxel-audio-route.sh --check` is a
  read-only readiness probe.
- **Boot readiness:** the boot cue waits for UI ownership *and* the audio route;
  it does not play into a half-applied graph.
- **Volume keys:** the button manager drives the same PipeWire default sink as
  the UI in absolute 5 % steps and cannot exceed the 25 % safety cap.
- **Settings:** real ALSA inventory, PipeWire backend state, selected output,
  volume/mute capability reporting, and a Test Audio button.
- **Sound modes:** normal/vibrate/silent policy is shared with the button chord.
- **Persistence:** the route survives cold boot and a session restart; the
  installer refuses to overwrite a newer proven route script with an older
  staged copy.
- **Safety:** no max-volume or continuous-loop test is performed; no amplifier
  protection or thermal limit is disabled.

## What remains for “audio works”

1. **Owner audibility confirmation.** Unlock the phone, open Notes, focus the
   title, play the three-POW cue, type `works`. The detector requires a fresh,
   focused, editable title and store corroboration.
2. **Capture path.** Verify the microphone with a real recording and inspect the
   WAV, not merely a device node.
3. **Alternate outputs.** Test the earpiece, 3.5 mm headset and a USB-C DAC.
4. **Route transitions.** Exercise speaker → headset → USB-C and back while
   playback is active.

## Evidence

- `docs/beta-finalization/live/PWNAGE-40000-REPORT.md`
- `docs/beta-finalization/live/PWNAGE-40000-TODO.md`
- `docs/beta-finalization/live/evidence/pwnage-40000/`
- `docs/s10plus-live-fixes-20261028.md`
- `services/nuxel-s10/bin/nuxel-audio-route.sh`
- `services/nuxel-bridge/src/hw_providers.py`

## Explicitly not done

- No kernel rebuild, flashing, bootloader change or repartitioning.
- No invented UCM controls or fake speaker-success claim.
- No change to amplifier protection, thermal limits or the 25 % safety cap.

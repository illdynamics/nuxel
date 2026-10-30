# Nuxel S10+ audio — current status (2026-10-29 20:12Z)

## Owner answer

**No — not heard yet.** The owner's confirmation signals (3× Home penguin in
`/run/nuxel-navdock.state`, or typing `works` in the open note title) were
watched live for several 3-pow runs and stayed at 0. No audibility is claimed.

## What is fixed now

### The UI Test Audio path was genuinely broken

`Settings → Sound → Test Audio` sent `audio.test-audio {gain_percent:25}`.
The HTTP bridge ran `gst-launch-1.0 … ! pulsesink` and killed it after a 2.5 s
window. On this image `pulsesink` never posts EOS, `decodebin` had not linked
inside that window, and **no `abox_uaif_trigger` appeared in dmesg at all**
when the owner tapped Test Audio at 19:45:30. The effective level was also
`0.20 × 0.25 = 5%`.

Replaced with the player that already works on this unit:

```
pw-play --volume <gain> /usr/share/nuxel/assets/nuxel-pow.mp3
```

- `services/nuxel-bridge/src/hw_providers.py` `_pipewire_play()` → `pw-play`,
  timeout 8 s, honest `pw-play completed` detail.
- `AudioProvider._ensure_default_sink()` selects `alsa_output.hw_0_1` by
  stable name first. After a cold boot WirePlumber published the sink without
  a default node; `pw-play` then failed with
  `Translate ID error: '-1' is not a valid ID (returned by
  default-nodes-api)`.
- Settings `gain_percent` 25 → 100, so the PipeWire sink volume is the only
  attenuation.
- Deployed to `/usr/lib/nuxel/nuxel-bridge/hw_providers.py` and
  `/usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js`.

### Volume keys are now 5 % steps

The button manager had selected the first writable ALSA element it found:
`ABOX PCM ext Out Fade Start` (range 0..1), so every press jumped 0 %/100 %.
It now drives the same PipeWire default sink as every app:

```
wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+
wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-
```

Verified live: `20 → 25 → 30 → 35 → 30 → 25 → 20`. The volume preview cue is
throttled to one per 500 ms, which stops the autorepeat “pow nonstop”.

### Route / boot

`services/nuxel-s10/bin/nuxel-audio-route.sh` now also sets:

- `Left/Right PCM Source = ASP` (direct path; DSP1 stays booted/running)
- `ABOX Sound Type = 0` (VOICE, boot default)
- `Left/Right AMP PCM Gain = 12` (driver default 4 dB was inaudible at a
  20 % sink level)
- default sink by name, then sink volume `0.20`
- verification reads the real `: values=` line (the old parser printed the
  ENUMERATED type line, e.g. `1,items=11`)

Timer/retry: `45/90/150 s` after boot and every `300 s`; retry unit has
`TimeoutStopSec=5`, `SendSIGKILL=yes`.

### Live software state at 20:12:41Z

```
default_sink    alsa_output.hw_0_1
sink_volume     0.20
AMP PCM gain    12 / 12
PCM Source      ASP / ASP
ABOX Sound Type 0 (VOICE)
DSP1            cs35l40-bot… + cs35l40-rcv…, booted=Y running=Y
3× bridge test-audio at 20:12:41..45
  HTTP 200 {"success":true,"played":true,"detail":"pw-play completed"}
dmesg: GAIN_CTRL=0x193, abox_uaif_trigger[P](1),
       abox_rdma_trigger[1](1), then trigger(0)
```

Evidence: `docs/beta-finalization/live/evidence/pwnage-38000/audio-fix-20261029c.txt`.

## What still blocks owner confirmation

Software reaches the ABox and the CS35L41 DAPM path is `On` (Main AMP,
AMP SPK, CLASS H, AMP Enable, AMP Playback), but physical audibility is still
unconfirmed. The owner was last active at 19:45:30; after the display slept,
`wl-fb` could not wake it (`BL_POWER write=-1`). Direct sysfs wake works but
can wedge `hsi2c 10990000` (panel bus), so the panel was force-woken and the
screen timeout set to `never` for testing.

Next tests if the owner still hears nothing, in order:

1. Confirm the phone is in hand / speaker not covered, screen on, and tap
   **Settings → Sound → Test Audio** once (now 100 % into the 20 % sink).
2. Try the receiver/earpiece path explicitly (left CS35L41 = `RECEIVER`,
   right = `SPEAKER`; both are On).
3. Try `RDMA2` / `RDMA3` with `SPKAMP_A/B`/`SPUS IN1` remapped.
4. If the UI path is silent but a direct `pw-play` is audible at 100 % sink,
   the remaining issue is gain staging, not routing.

## 20:14Z — one clean 3× run (still no owner confirmation)

The owner tapped Settings → Test Audio at 20:12:09 and 20:12:22 after the
bridge/JS deploy; the taps are in `/run/nuxel-home.state`, but the owner did
not press Home three times or type `works`.

To remove stream-start/ramp doubt, a single 2.5 s file containing exactly
three pow bursts separated by 0.5 s was generated and installed:

```
/usr/share/nuxel/assets/nuxel-pow-3x.wav
(48 kHz stereo, 2.5 s, three × 0.366 s pow with 0.5 s silence between)
```

Played once at 20:14:47 with:

```
default sink   = alsa_output.hw_0_1
sink volume    = 0.20
AMP PCM gain   = 12 / 12
pw-play --volume 1.0 /usr/share/nuxel/assets/nuxel-pow-3x.wav -> rc=0
```

No `action=home` in `/run/nuxel-navdock.state` for the following 90 s.
Therefore, by the owner's criterion, **audio still does not work**.

Remaining likely causes (software path is now correct):

1. Physical speaker / connector / amp output on this unit.
2. Both CS35L41 DAPM output paths are `On` (Main AMP, CLASS H, AMP SPK,
   AMP Enable, AMP Playback), so this is not a simple mixer mute.
3. The only confirmed audible event this session was the loud 1 kHz reference
   at ~19:42; a busy 1 kHz tone may have come from the receiver/earpiece,
   while the quiet pow does not.

Do not mark speaker audio as working until the owner hears it and presses the
Home penguin three times.

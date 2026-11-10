# Nuxel audio output discovery and routing (PWNAGE-102000)

## Real S10+ path

```
USB-C DP Alt Mode
  -> exynos-displayport (EDID + DP audio info)
  -> Samsung DP DMA: /proc/asound/pcm "DP Audio" (hw:0,22 on the current boot)
  -> PipeWire sink created on demand by nuxel-soundd
  -> PulseAudio-compatible default sink / active streams
```

`hw:0,22` is resolved from `/proc/asound/pcm` at runtime. It is never
persisted. The stable identity is `alsa:beyond-madera:dp-audio`.

The vendor display driver publishes `edid_audio_informs()` through
`/sys/class/switch/ch_hdmi_audio/state`. It is a packed word, not a boolean:
the live Philips TV value is `0x043b0102` (two-channel LPCM, 48 kHz, DP).
A value of `-1`/`0xffffffff`, zero channels, or zero sample-rate flags means
no usable endpoint.

## One authoritative manager

`nuxel-soundd` owns output policy and the `nuxel_audio_outputs.py` module.
`nuxel-displayd` continues to own the separate display state machine and only
publishes audio capability; it never changes a PipeWire default sink.

The manager:

1. Reads the DP link/extcon, `DP Audio` PCM and EDID audio-info word.
2. Loads `module-alsa-sink` with `sink_name=alsa_output.nuxel_hdmi` only while
   a verified HDMI/DP audio endpoint exists.
3. Enumerates real `Audio/Sink` nodes from PipeWire, excluding monitors,
   null/dummy/auto sinks and virtual nodes.
4. Applies automatic/manual policy, moves active sink inputs, and verifies the
   default-sink readback.
5. Falls back to the last valid non-HDMI output (normally the phone speaker)
   before unloading the HDMI sink.
6. Persists only routing mode and stable identities in
   `/var/lib/nuxel/audio/output-policy.json`.

## Policy

* **Automatic**: verified HDMI first; otherwise the last valid non-HDMI output,
  then speaker, then the current/default physical output.
* **Manual**: an explicit stable output identity wins. HDMI hotplug does not
  change it. If the selected device disappears, the manager selects a safe
  fallback and retains the preference. If that stable device returns, the
  preference is restored.
* Bluetooth and USB are manual-selectable like any other real output. In
  Automatic mode HDMI has priority over them, matching the required
  display-audio policy; manual intent always wins.

## Commands

```sh
nuxel-audio-ctl outputs --json
nuxel-audio-ctl diagnostics --json
nuxel-audio-ctl automatic
nuxel-audio-ctl select alsa:beyond-madera:dp-audio
nuxel-audio-ctl select alsa:beyond-madera:rdma1
nuxel-audio-ctl volume 50
nuxel-audio-ctl mute on
nuxel-audio-ctl test
```

The public machine-readable state is `/run/nuxel/audio-outputs.json`.
The Settings → Sound page uses the same socket commands through the local
bridge and refreshes every two seconds while visible.

## Honest verification

A PipeWire sink appearing, `pactl` returning success, `pw-play` exiting zero or
the Settings UI showing HDMI is **not** proof that a TV emitted audio. Physical
audibility is recorded only from human confirmation or a separate physical
capture test.

# PWNAGE-40000 — report (final continuation, 2026-10-30T13:0xZ)

## Verdict

The **persistence and boot-readiness repair is complete and verified on the
handset after a fresh cold boot**. The internal speaker's *physical* audibility
is **NOT CONFIRMED**: every three-POW batch completed with `pw-play` rc=0 and a
live focused/editable Notes Title, but no fresh `works` entry appeared and no
key/input event reached the Notes WebView. No audibility claim is made.

## Root-cause item fixed in this continuation

The live amplifier digital trim `Left/Right AMP PCM Gain` was **19** after cold
boot. On this unit 19 logs `GAIN_CTRL = 0x273` and is the silent boot default;
the proven 2026-10-29 value **12** logs `GAIN_CTRL = 0x193`. The route script
never set this control, so every boot silently reverted to 19. This is now a
mandatory, read-back route step:

- `services/nuxel-s10/bin/nuxel-audio-route.sh` sets `Left/Right AMP PCM Gain = 12`,
  verifies both by name in `route_controls_ready()`, and its `--check` gate
  refuses readiness unless both are 12.
- Deployed to `/usr/lib/nuxel/nuxel-audio-route.sh`; source and live sha256 match
  (`0e7e9e8156dfef344a3e2c47b770cc6f42fac01a50899e03d26c8bbf13fabe09`).

## What was verified after the cold reboot (new boot id `c78289f2…`)

| Evidence | Value |
|---|---|
| ABOX Calliope cold boot | `MUB0` (reached on its own; route deferred briefly until DSP1 download completed) |
| CS35L41 DSP1 ×2 | `booted=Y running=Y`, bot+rcv protection wmfw |
| `Left/Right AMP PCM Gain` | 12 / 12 (read back in `--check`) |
| `ABOX RDMA1_EN` | 1 |
| PipeWire sink | `alsa_output.hw_0_1 s16le 2ch 48000Hz` |
| Default sink | `alsa_output.hw_0_1` |
| RDMA1 runtime | `rate: 48000`, `state=RUNNING`, `hw_ptr` 0→7182→13362→16388 |
| Startup POW | `nuxel-boot-sound` ran once at 13:59:33 after the readiness gate, `player_ok`, marker written |
| Screen timeout | restored to 300 s (`never: false`) |

## Three-POW confirmation rounds (this continuation)

Rounds at ~25 % and one at 0.90 (temporary, restored to 0.25) all produced
`pw-play` rc=0 and `detector_rc=1` (TIMEOUT). The Notes Title was live, focused,
showing and editable, and the bridge store remained `missing` (no note saved),
so the fresh `works` value was never entered.

The remaining blocker is the human confirmation itself, not the audio route.

## Explicitly not done / unchanged

- No kernel rebuild, flashing, bootloader change or repartitioning.
- `systemd-udevd` not re-enabled.
- Stub UCM not filled with invented controls.
- No amplifier gain copied from an old capture beyond the measured 12 (0x193).

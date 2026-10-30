# PWNAGE-40000 — updated speaker-output root-cause assessment

**Evidence cut-off:** repository archive received 2026-10-30, including the
PWNAGE-43000 speaker-path experiments.

## Verdict

The digital playback path is substantially verified, but the physical built-in
speaker has **not** been audibly confirmed. This is not merely a missing Notes
response: the later owner-supervised PWNAGE-43000 experiments passed the Notes
input preflight and captured explicit `no` responses.

The next investigation must focus on the final CS35L40-compatible amplifier
output/boost stage and the physical speaker endpoint. Do not repeat the earlier
Sound Type, PCM Source or 55% volume experiments as the first step.

## Proven negative experiments

`docs/beta-finalization/live/evidence/pwnage-43000/05-speaker-path-audibility-experiments.md`
records valid owner-supervised results:

- `ABOX Sound Type=1` (SPEAKER) at 25% PipeWire sink volume: no audible sound.
- The same SPEAKER mode at 55%: owner explicitly typed `no`.
- CS35L41 PCM Source changed ASP -> DSP, with DSP1/PCM Source DAPM widgets ON
  and PWR_CTRL2 moving from `0x21` to `0x3721`: owner explicitly typed `no`.
- Baseline was restored to Sound Type VOICE (0), PCM Source ASP (0), sink
  volume 0.25, then route `--check` passed.

These are useful negative experiments. The new agent should not repeat them
unless new evidence changes the hypothesis.

## What is already working in the digital path

The latest evidence records:

- ABOX Calliope firmware `MUB0`.
- Both CS35L41 DSP1 protection processors `booted=Y running=Y`.
- `ABOX RDMA1_EN=1` and the RDMA1/SPUS/SIFS1/UAIF1 crossbar set.
- Both amplifier enable and unmute controls on.
- `PWR_CTRL1=0x1` during playback.
- `DIG_VOL_CTRL=0x8000` during playback.
- `GAIN_CTRL=0x193` when the tested AMP PCM Gain controls are 12.
- PipeWire default sink `alsa_output.hw_0_1`, S16LE, stereo, 48 kHz.
- RDMA1 enters RUNNING and its hardware pointer advances during the test.
- No reported CS35L41 mailbox/CSPL errors during the controlled tests.

None of these observations alone proves the physical speaker is emitting
sound. They do narrow the failure toward the final amplifier power/boost,
output-enable, routing-to-transducer or physical-output stage.

## Specific code-path lead in the pinned 4.14.253 kernel

The build wrapper pins:

`Linux4/android_kernel_samsung_exynos9820`

commit:

`f7194c1d15eded1c2a1a4dc63825b26103435cc0`

In that exact source's `sound/soc/codecs/cs35l41.c`,
`cs35l41_main_amp_event()` on `SND_SOC_DAPM_POST_PMU`:

1. applies `cs35l41_pup_patch`;
2. sets `CS35L41_PWR_CTRL1.GLOBAL_EN`;
3. sends DSP PAUSE/RESUME depending on the path;
4. calls `cirrus_pwr_start()`;
5. returns without the later upstream external-boost `SPK_OUT_ENABLE` handling.

The companion `drivers/mfd/cirrus-pwr.c` shows `cirrus_pwr_start()` marking an
amp active and queueing the Passport thermal/power-monitor state machine. It
is not the missing external speaker-output enable command. Do not mistake a
successful `cirrus_pwr_start()` or Passport work item for speaker-output
activation.

An upstream 2023 CS35L41 change introduces mailbox command
`CSPL_MBOX_CMD_SPK_OUT_ENABLE` (value 7) for **external boost** because the two
speaker-output register writes need tight sequencing to avoid a pop/click.
It retains a legacy sequence when compatible firmware is absent. A later
compatibility correction states that firmware v0.28.0 and older do not support
that mailbox command; the actual DSP firmware version must therefore be read
from the correct `fw_id_version` metadata, not inferred from `fw_id` alone.

**This is a conditional lead, not a proven fix.** The external-boost sequence
must only be ported if the actual S10+ board/DT/OTP/boost hardware is positively
identified as external boost. The command is not a generic speaker-on switch.

## Captured DTB clue — not sufficient to classify live boost topology

The ZIP includes a historical captured DTB:

`scripts/s10plus-debug-pack/captures/20261015T065746Z-boot-image-10304/boot-image/fdt-00-at-22056960.dtb`

A read-only FDT parse found two nodes:

- `hsi2c@109A0000/cs35l40@40`, `compatible="cirrus,cs35l40"`,
  `reg=0x40`, `cirrus,dsp-part-name="cs35l40-bot"` and
  `cirrus,boost-peak-milliamp=0x1004` (4100 mA).
- `hsi2c@109A0000/cs35l40@41`, `compatible="cirrus,cs35l40"`,
  `reg=0x41`, `cirrus,dsp-part-name="cs35l40-rcv"` and
  `cirrus,boost-peak-milliamp=0x1004` (4100 mA).

That historical capture did **not** contain a `cirrus,boost-type` property or
`cirrus,gpio1-output-enable` / `cirrus,gpio1-src-select` properties on those
nodes. It did contain `cirrus,gpio-config2` entries (GPIO2 configuration).

The modern binding describes boost type as internal (0), external (1), or
shared boost variants, and specifies a GPIO1 output configuration for external
boost. The old captured DTB does not prove that external boost is in use; it
also does not prove the active live DTB is identical. The agent must inspect
the live handset DT, actual OTP/driver interpretation, GPIO1 state and board
power topology before selecting any boost-specific sequence.

## Additional high-value leads to capture during a real playback

### 1. CS35L41 output-power telemetry

The archived mixer snapshot had read-only DSP protection controls:

- `Left DSP1 Protection cd PL_SPK_OUTPUT_POWER`
- `Right DSP1 Protection cd L_SPK_OUTPUT_POWER`

They were zero in an idle snapshot. That is not diagnostic by itself.
Read their live values immediately before, during and after one playback,
without writing to those controls. Also inspect the `cirrus_pwr` class's
left/right output power telemetry if exposed. The `cirrus-pwr` implementation
reads `CIRRUS_PWR_CSPL_OUTPUT_POWER_SQ` while an amp is active.

A persistent zero while PCM/DAPM are active would be useful evidence that the
signal is not reaching the amplifier DSP/output stage, but interpret it against
the telemetry format and its update lifecycle rather than asserting it proves
hardware failure.

### 2. ABOX SoundBoost controls

The archived mixer inventory captured:

- `ABOX SOUNDBOOST_A=0` (None)
- `ABOX SOUNDBOOST_B=0` (None)
- `ABOX SOUNDBOOST_EN=0` (Off)

These are distinct ABOX controls. Their necessity for the current RDMA1 to
CS35L40 route has not been established. Identify their driver semantics and
DAPM/route relationship before changing them. Do not turn them on blindly.

### 3. Physical speaker versus receiver mapping

`tools/s10plus/a33/nuxel-button-manager.c` explicitly notes that the DAPM
`SPEAKER` widget is fed by `Right AMP SPK`; `Left AMP SPK` maps to the receiver.
It also prefers `Right AMP PCM Gain` for the volume keys because Left AMP PCM
Gain does not drive the external SPEAKER. Confirm the actual live DAPM and
physical mapping. Do not accept receiver-only output as speaker success.

### 4. Correct the stale gain claim

The route script previously described gain 12 as the only value that had
produced confirmed sound. The later owner-supervised tests at 12/12 produced
no audible sound. The comment has been corrected: gain 12 is a measured
configuration, not an acoustically confirmed value.

## New read-only diagnostic

`tools/s10plus/a33/nuxel-cs35l41-speaker-diag.sh`

This script captures:

- actual live I2C/OF node properties;
- available `cirrus,boost-*` and GPIO1 properties;
- amplifier DSP debugfs state;
- read-only register snapshots where debugfs is already mounted;
- targeted ALSA control readbacks including SoundBoost and speaker-power
  telemetry;
- DAPM widgets;
- PipeWire sink/default/volume;
- PCM status/hw_params;
- filtered kernel audio messages.

Its optional watcher samples RDMA1 `status` and `hw_params` during a separately
started test and periodically captures read-only ALSA speaker-output power /
SoundBoost telemetry plus exposed Cirrus power-class values. It never plays
audio and never writes to hardware, ALSA controls, sysfs, GPIO, regmap or
service state. It does not mount debugfs.

## Kernel build wrapper defect fixed in this source package

The original `kernel/s10plus/build-kernel.sh` did not contain any `git apply`
step, despite the README claiming that `kernel/s10plus/patches/*.patch` were
applied. The wrapper now has an idempotent, logged patch application phase:

- skips the 0001 documentation stub;
- detects already-applied patches;
- checks and applies valid patches in sorted order;
- verifies applied patches with a reverse check;
- warns for optional patch conflicts;
- supports a `.required` sidecar for future mandatory patches.

This does not itself add a speculative CS35L41 driver patch. It ensures that a
future correctly ported and validated patch will actually be applied to the
pinned kernel checkout, rather than silently ignored.

## Conclusion / next action

The exact remaining hardware root cause is **not yet proven**. The next live
session should start with the read-only speaker diagnostic, including live
boost topology and output-power telemetry. The agent should then choose the
correct fix based on that evidence. If the true cause is an external-boost
speaker-enable omission, port the complete upstream-safe sequencing to the
4.14 driver. If not, continue with internal-boost setup, SoundBoost routing,
DSP input/output telemetry, channel/physical transducer mapping and board
power rails.

No kernel or boot image was built or flashed during this repository patch.
No physical speaker audibility was claimed.

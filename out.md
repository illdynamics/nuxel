## Result (2026-10-30, owner-supervised)

- **Root cause found:** DT programs `ampclk = 6,144,000 Hz`, but ABOX UAIF1 actually clocks the CS35L41s at **1,536,000 Hz** (16-bit stereo 48 kHz). The amp PLL was therefore locked to the wrong reference, so the protection DSP never drove the physical speaker.
- **Fix (owner-confirmed audible):** write both CS35L41s:
  - `SP_RATE_CTRL (0x4804) = 0x1b`  (1.536 MHz refclk entry)
  - `PLL_CLK_CTRL (0x2c04) = 0x370` (refclk 1.536 MHz + PLL enabled)
  - `AMP_DIG_VOL_CTRL (0x6000) = 0x8000` (0 dB, unmuted)
  - `AMP_OUT_MUTE (0x2024) = 0x0` (output/boost stage enabled)
- **Playback:** `pw-play --volume 1.0 /tmp/nuxel-confirm-440.wav` → rc=0.
- **Your confirmation:** Notes Title went `"" → "w" → "wo" → "wor" → "work" → "works"` during the 90 s window. **PASS — you heard it.**
- **Persistence:** the above four writes are now applied by `/usr/lib/nuxel/nuxel-audio-route.sh` (and mirrored in `services/nuxel-s10/bin/nuxel-audio-route.sh`). The route service and retry timer are enabled, so the fix re-applies after boot.
- **Backups:** `/usr/lib/nuxel/nuxel-audio-route.sh.bak-1793390000` on the phone.

## Next

Reboot + post-boot one-play confirmation remains. Reopen the Notes app after boot so the Title-field detector can see your reply.

## 2026-10-30 late — why the first "persistent" fix regressed, and the real fix

The earlier four raw I2C writes were necessary but **not sufficient**. The pinned
CS35L41 driver calls `cs35l41_pcm_mute(dai, mute=1)` on every stream stop
(`hw_free`). That path writes:

- `AMP_DIG_VOL_CTRL (0x6000) = mute value (0xa678)`
- `AMP_OUT_MUTE (0x2024) = 0x10`

So a boot-time or pre-play raw write was wiped by the **next** playback's own
power cycle. Measured live after boot: `0x4804=0x1b`, `0x2c04=0x370` survived,
but `0x6000=0xa678` and `0x2024=0x10` had been rewritten.

The durable path is the driver's own cache, not raw I2C:

- `Digital PCM Volume` = **817** → the driver maps this to `0x6000 = 0x8000` (0 dB)
- `AMP Mute` = **Unmuted (1)**
- `AMP Enable` = on, `PCM Source` = ASP, `PCM Gain` = 12

On every playback start `cs35l41_pcm_mute(..., 0)` clears `0x2024` and restores
the cached `0x8000` value. The PLL patch (`0x4804=0x1b`, `0x2c04=0x370`) is
applied on boot by `nuxel-audio-route.sh` and survives playback.

### Owner-confirmed results

| Test | When | Playback | State during play | Result |
|---|---|---|---|---|
| 1 | 2026-10-30 21:35Z | `nuxel-pow.mp3`, 50% | correct regs, but detector store bug | no reply (FAIL) |
| 2 | 2026-10-30 21:37Z | `nuxel-pow.mp3`, 50% | `2014=1 2018=21 6000=8000 2024=0 4804=1b 2c04=370` | **`works` — PASS** |
| 3 | 2026-10-30 21:44Z **after reboot** | `nuxel-pow.mp3`, 50% | identical to test 2 | **`works` — PASS** |

`nuxel-notes-works-detector` also had a real bug fixed here: with an empty Notes
store (`data:null`) it treated the store as available-but-unmatched and could
never PASS. It now treats a missing store key as unavailable corroboration.

### Volume policy change

The 25% low-volume bring-up cap is **retired**:

- policy ceiling: **100%**
- first-boot default: **50%**
- live sink level: **50%** (`wpctl get-volume` → `Volume: 0.50`)
- bridge API: `volume_cap_percent=100`, `volume_percent=50`
- `/etc/asound.conf` softvol `max_dB = 0.0`

### Frozen state

`/root/pwnage-40000/frozen-state/` on the phone contains `state.txt`,
`confirmed-midplay.txt`, `README.txt`, copies of the scripts/configs and
`sha256.txt`. The route service and retry timer are enabled, and a normal reboot
was already used for test 3.

## FINAL 2026-10-30 22:06Z — actual root cause of the regression

The four CS35L41 register writes were correct but **not sufficient**. During a
failing play both amps reached the exact "working" snapshot
(`0x2014=1 0x2018=0x21 0x6000=0x8000 0x2024=0`) and still produced no sound.
The kernel trace showed the difference: working runs logged
`beyond_speaker ev: 2`; failing runs did not. The physical `SPEAKER` /
`Right AMP SPK` DAPM path was never powered.

`nuxel-pow.mp3` is only ~0.366 s. On a cold path the speaker DAPM widget powers
up in the same instant the clip ends, so the cue is swallowed. Yesterday's
successful tests were longer streams; today's short cue was not.

### Fix (owner-confirmed, persistent)

New `/usr/lib/nuxel/nuxel-audio-warmup`:
- starts an inaudible 8 s 48 kHz stereo WAV at volume 0.0,
- waits until `/sys/kernel/debug/asoc/beyond-madera/dapm/SPEAKER` is `On`,
- re-asserts the PLL/0 dB/unmute registers,
- then the caller plays the real POW once.

The old `nuxel-cs35l41-apply.sh` was also broken: it word-split control names
with spaces, so every `amixer cset` failed. It now delegates to the corrected
helper.

Wired into:
- `/usr/libexec/nuxel/nuxel-sound-cue` (volume keys + boot cue),
- `hw_providers.AudioProvider.test_audio` (Settings → Test Audio),
- boot service drop-in `20-warmup-keepalive.conf` (`KillMode=process`).

Volume: ceiling 100%, default/live 50%, unmuted.

Owner confirmations:
- 21:56:25Z manual warm-up + POW — `works`
- 21:58:09Z production volume cue — `works`
- 22:00:39Z Settings Test Audio provider — `works`
- 22:05:33Z after full reboot, volume cue — `works`
- 22:06:41Z exact frozen helper build, volume cue — `works`

Frozen state: `/root/pwnage-40000/frozen-state/` (state, hashes, scripts,
silence asset, boot drop-in).

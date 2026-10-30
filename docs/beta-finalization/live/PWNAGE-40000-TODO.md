# PWNAGE-40000 TODO — audio persistence and boot readiness

Device: Samsung Galaxy S10+ SM-G975F / beyond2lte
Live host: `root@192.168.178.167` over Wi-Fi SSH (`~/.ssh/wicked_wqn_id_rsa`)
Continuation run: 2026-10-30T10:36+01:00
Evidence: `docs/beta-finalization/live/evidence/pwnage-40000/continuation-20261030T1036Z/`

Status vocabulary: **VERIFIED** = the live device proved it in this run.
**NOT CONFIRMED** = software path proven, but the owner's fresh `works` entry
has not been observed. A player exit code is never used as proof of audibility.

| # | Item | Result | Status |
|---|------|--------|--------|
| 1 | Preserve live config | Backed up `/usr/lib/nuxel/*`, units, cue, graph conf, notes state to `/var/backups/nuxel/pwnage-40000-20261030T094225Z/` before every write; all deploys staged + sha256-verified | VERIFIED |
| 2 | ABOX RDMA1 gate | Live `ABOX RDMA1_EN=1` before and after my changes; repo script matches the proven live route | VERIFIED |
| 3 | Full ABOX crossbar | RDMA1 → SPUS IN1 → SPUS OUT1 → SIFS1 → UAIF1 SPK; SPKAMP A/B=RDMA1; read back by name | VERIFIED |
| 4 | CS35L41 DSP1 protection firmware | Both amps: `cs35l40-bot-dsp1-spk-prot` + `cs35l40-rcv-dsp1-spk-prot`, `booted=Y running=Y` | VERIFIED |
| 5 | ABOX Calliope core | Cold boot reached `MUB0` after 2 bounded PM reload attempts | VERIFIED |
| 6 | Honest readiness gate | `--check` verifies MUB0, both DSPs, all mixers, 48 kHz sink, default sink, native PipeWire core, volume cap | VERIFIED |
| 7 | Boot cue readiness + asset | **Fixed**: `ExecStartPre` was a one-shot `--check` that failed 0.1 s after the ABOX reload. Now `--wait 200`, bounded and read-only; cue plays `nuxel-pow.mp3` once per boot | VERIFIED |
| 8 | PipeWire default sink | `_ensure_default_sink()` now rejects a non-48 kHz sink and a literal `null` read-back; result is checked at every call site | VERIFIED |
| 9 | 48 kHz + hw_ptr | Sink and graph clock 48000; `/proc/asound/card0/pcm1p/sub0` shows `rate 48000` and `hw_ptr` 20486→72720 across samples | VERIFIED |
| 10 | 25 % ceiling | Settings API `set-volume 90` → readback 25 %; retry route no longer lowers a user setting already below the cap | VERIFIED |
| 11 | Settings Test Audio | Now runs the same `nuxel-audio-route.sh --wait` gate first, then `pw-play` on the verified sink; still reports `audible: unverified` | VERIFIED |
| 12 | Volume feedback | One attenuation stage (sink), non-blocking flock suppresses overlap | VERIFIED |
| 13 | Notes `works` detection | Detector discovers the session AT-SPI bus (`/run/nuxel-wayland/at-spi/bus`) before libatspi loads; requires live FOCUSED+SHOWING+EDITABLE Title, whole-word `works`, freshness vs baseline, and store corroboration. It captured the live Title as focused/editable and correctly refused PASS on an empty Title. **Six play rounds produced no `works` and no keystroke ever reached the WebView** | NOT CONFIRMED |
| 14 | Three sequential POWs | Rounds 1–2 pre-reboot, round 4 after reboot (launch blocked by lock), rounds 5–6 after unlock with Notes Title focused; `pw-play` rc=0 sequentially each round | VERIFIED (playback) / NOT CONFIRMED (audible) |
| 15 | Startup POW once | After reboot: `ExecStartPre` and `ExecStart` both `status=0/SUCCESS`; exactly one boot cue entry; per-boot marker written | VERIFIED |
| 16 | Other output routes | Receiver (`Left AMP SPK`→RECEIVER) and speaker (`Right AMP SPK`→SPEAKER) are both live in DAPM; no 3.5 mm plug or USB-C audio accessory was attached, so those routes are **not tested**, and no controls were invented. UCM stub untouched | DOCUMENTED (not tested) |
| 17 | Reboot persistence | Cold reboot: new boot id, Wi-Fi SSH returned, MUB0, route auto-applied, DSPs up, 48 kHz, boot POW once | VERIFIED |
| 18 | Session restart persistence | `systemctl restart nuxel-wayland` → route still applied; first `pw-play` right after restart failed with `Host is down`, gate now detects this via native PipeWire probe | VERIFIED (with fix) |

## Defects found and fixed in this run

1. **Boot cue never played after boot.** `ExecStartPre=… --check` was a single
   non-waiting sample. Added `--wait N` (read-only polling) and used it.
2. **ABOX wrapper raced PipeWire.** It started the route before the session
   socket existed and returned before the route applied. It now starts the
   session, waits for `pipewire-0`, then applies the route synchronously.
3. **Retry timer rewrote DSP firmware every 5 minutes** and slammed the sink
   volume to 25 %. `set_ctl` now reads first; volume is only lowered if above
   the cap.
4. **44100 Hz graph clock restored at boot** from the staged pwnage36000
   bundle. Fixed in the repo, the live file, and the staged bundle.
5. **Readiness was optimistic during a session restart** (`pactl` answered
   before the native socket accepted `pw-play`). `--check` now probes
   `pw-core` over `pipewire-0`.
6. **Detector could not connect to AT-SPI** (missing bus address). Fixed.
7. Screen timeout left at `never` by the previous run → restored to 300 s.

## Explicitly not done

- No kernel rebuild, flashing, bootloader change or repartitioning.
- `systemd-udevd` not re-enabled.
- Stub UCM not filled with invented controls.
- Amplifier gain was not changed from the live values (19/19); no gains copied.
- Physical audibility is **not** claimed.

## Open blocker for the human confirmation

Two independent device-side conditions prevented a confirmation:

1. **Locked at boot.** `NUXEL_INPUT LOCKS … reason=boot locked=1`; the launcher
   refuses launches (`EVT launch:blocked-locked app=org.nuxel.Notes`).
2. **The panel blanked itself mid-test.** `nuxel-button-manager` fired
   `IDLE_SCREEN_OFF timeout_ms=300000 idle_ms=300138` and set
   `/sys/class/backlight/panel/bl_power=4` (`display=off`), so the owner could
   not see or touch the Notes UI. The display was brought back with
   `screen-on` + brightness and the timeout temporarily disabled for the last
   rounds.

Even with the display on, the Notes Title focused and `nuxel-pow.mp3` played
three times, **zero keystrokes arrived** (no `key`/`input` events, no text in
the Title). The detector therefore timed out honestly. To finish:

1. unlock the phone (drag the penguin up),
2. open **Notes** and tap the empty **Title**,
3. type `works` after the three POWs.

The detector records PASS only from a fresh focused Title containing the whole
word `works`, corroborated by the app's saved store.

## Final continuation 2026-10-30T13:0xZ

- **Found and fixed**: `Left/Right AMP PCM Gain` was 19 after every cold boot
  (`GAIN_CTRL=0x273`, silent). The route script now sets and read-backs 12
  (`GAIN_CTRL=0x193`, the proven 2026-10-29 value). Source and live sha256 match.
- **Post-reboot verified**: MUB0, both CS35L41 DSP1 `booted=Y running=Y`,
  gain 12/12, `ABOX RDMA1_EN=1`, `alsa_output.hw_0_1` 48 kHz default sink,
  RDMA1 `state=RUNNING` with advancing `hw_ptr`, and a single gated startup POW.
- **Still NOT CONFIRMED**: fresh `works` in the live Notes Title. Six+ three-POW
  rounds completed with rc=0 and a focused/editable Title; no `works` appeared
  and no input event reached the Notes WebView. Physical audibility remains
  unclaimed, exactly as required.

## Superseding speaker-path continuation — 2026-10-30

The later owner-supervised evidence in
`docs/beta-finalization/live/evidence/pwnage-43000/05-speaker-path-audibility-experiments.md`
supersedes the older Notes-input blocker above. In that later session the
Notes Title preflight passed and the owner explicitly typed `no` for the
speaker tests. Therefore these are valid negative acoustic tests, not merely
missing Notes input.

| # | New item | Result | Status |
|---|---|---|---|
| 19 | ABOX Sound Type SPEAKER (1), sink 25% | Owner did not hear output | VERIFIED NEGATIVE |
| 20 | ABOX Sound Type SPEAKER (1), sink 55% | Owner typed `no` | VERIFIED NEGATIVE |
| 21 | PCM Source ASP → DSP, SPEAKER mode | Owner typed `no`; DSP1/PCM Source DAPM widgets changed On | VERIFIED NEGATIVE |
| 22 | Restore baseline | Sound Type VOICE (0), PCM Source ASP (0), sink 0.25; route check passes | VERIFIED |
| 23 | Final amplifier/boost output path | Exact topology-specific cause not yet established | OPEN |
| 24 | Read-only amplifier diagnostic | Added `tools/s10plus/a33/nuxel-cs35l41-speaker-diag.sh`; captures live DT/boost properties, controls, DAPM, DSP, PipeWire, PCM and concurrent output-power/SoundBoost telemetry | IMPLEMENTED; LIVE RUN PENDING |
| 25 | Kernel build patch application | Wrapper now applies sorted patches idempotently and logs outcomes; no audio driver patch added yet | IMPLEMENTED; BUILD NOT RUN |

Important correction: the older report's statements about 19/19 cold-boot gain
and 12/12 being the current deployed setting refer to earlier, different runs.
The latest 05 experiment records 12/12 during the supervised tests and its
restored baseline. Always read the handset before assuming either value.

## Current next action

Deploy the patched read-only diagnostic over Wi-Fi SSH. Identify live boost
topology for both CS35L40-compatible amplifiers, inspect ABOX SoundBoost
semantics, and sample CS35L41 speaker output-power telemetry during one POW.
Do not port an external-boost-only driver sequence until the live hardware is
positively identified as external boost. Continue with one POW and a 30-second
Notes response window per test.

# PWNAGE-40000 — final report (2026-10-30 continuation)

## Verdict

The audio **persistence and boot-readiness repair is implemented, deployed and
verified on the handset**. The internal speaker's *physical* audibility after
the three POWs is **NOT CONFIRMED**: in three separate three-POW rounds no
fresh `works` entry appeared, and — critically — no pointer or text input
reached the Notes WebView at all in any of those rounds.

This report makes no audibility claim. `pw-play` exited 0 every time; that is
recorded as playback, not as sound.

## What was broken (measured, not assumed)

1. **Startup POW could never play.** `nuxel-boot-sound.service` ran
   `ExecStartPre=… --check` once. On the 09:35:45Z boot that check failed with
   "both CS35L41 DSP1 protection DSPs are not booted+running" 0.1 s after the
   ABOX reload; the route only completed 27 s later.
2. **The ABOX wrapper raced the session.** It issued
   `systemctl --no-block start nuxel-audio-route.service` *before* starting
   wayland/PipeWire, so the route deferred with "static PipeWire sink absent",
   and the unit returned before anything had applied.
3. **The 5-minute retry timer re-wrote DSP1 firmware/preload** and forced the
   sink to 25 %, overriding a quieter user setting.
4. **A staged bundle restored 44.1 kHz at boot.**
   `/usr/lib/nuxel/stage36000/nuxel-s10/pipewire/99-nuxel-s10.conf` was
   installed over `/etc/pipewire/pipewire.conf.d/99-nuxel-s10.conf` on the
   cold boot, so the graph clock came back as 44100 Hz even though the RDMA1
   sink was 48000 Hz.
5. **Readiness was optimistic during a UI restart.** `pactl` answered over
   `pulse/native` while the native `pipewire-0` socket was still being
   replaced; `pw-play` then failed with `Host is down`.
6. **The Notes detector could not attach to AT-SPI.** It never set
   `AT_SPI_BUS_ADDRESS`, so it died with "Couldn't connect to accessibility
   bus" although the live Notes Title entry was visible.

## What is now true (live evidence)

| Evidence | Value |
|---|---|
| `calliope_version` after cold boot | `MUB0` (2 bounded PM reload attempts) |
| CS35L41 DSP1 ×2 | `booted=Y running=Y`, `fw_id=0x000400a4`, bot+rcv protection bins |
| `ABOX RDMA1_EN` | 1 (plus SPKAMP_EN=1, SPKAMP_A/B=RDMA1, SPUS/SIFS1/UAIF1 mapped) |
| PipeWire sink | `alsa_output.hw_0_1  s16le 2ch 48000Hz` |
| Graph clock | `default.clock.rate = 48000`, `pactl info` → `float32le 2ch 48000Hz` |
| RDMA1 runtime | `rate: 48000`, `hw_ptr` 20486 → 72720 across samples |
| Default sink | `alsa_output.hw_0_1`, read back after `set-default-sink` |
| Volume | 0.20–0.25; API request of 90 % clamps to 25 % |
| DAPM during playback | Main AMP / AMP SPK / CLASS H **On** on both amps |
| Startup cue after reboot | `ExecStartPre` and `ExecStart` `status=0/SUCCESS`, once |
| Session restart | route still `state=applied`, gate READY |
| Reboot (1st) | new boot id, Wi-Fi SSH returned, all of the above re-verified |
| Reboot (2nd, final) | boot id `542fd9b1…`; Wi-Fi SSH returned; MUB0; route `state=applied`; both DSP1s Y/Y; RDMA1_EN=1; graph + sink 48000 Hz; boot cue `Result=success`, exactly **1** boot entry after readiness |

## Three-POW confirmation rounds

| Round | Playback | Detection |
|---|---|---|
| 1 (before reboot) | 3× `pw-play`, rc=0 each | TIMEOUT, baseline Title `""` |
| 2 (before reboot) | 3× `pw-play`, rc=0 each | TIMEOUT, baseline Title `""` |
| 4 (after cold reboot) | 3× `pw-play`, rc=0 each | `NO_TITLE_ENTRY`: the phone booted locked, launch refused |
| 5 (after unlock, display forced on) | 3× `pw-play`, rc=0 each | TIMEOUT, Title focused and empty |
| 6 (after Notes relaunch) | 3× `pw-play`, rc=0 each | TIMEOUT, Title focused and empty; **zero keystrokes arrived** |

Round 5 exposed a second, independent blocker: `nuxel-button-manager` fired
`IDLE_SCREEN_OFF timeout_ms=300000 idle_ms=300138` and left
`bl_power=4` (`display=off`), so the panel was dark while the owner was being
asked to type. The display was restored (`screen-on`, brightness) and the
timeout temporarily set to `never` for round 6; the default 300 s policy was
restored afterwards.

In rounds 1–2 the Notes Title was live, focused, showing and editable the whole
time (`notes-works-baseline.json`), yet **no pointer or text input events were
recorded** (`/run/nuxel-home.state` had zero `EVT key`/`pointerdown`/`focusin`
after launch). There was therefore nothing to detect — this is not a detector
failure.

## Blocking condition for the human confirmation

After a reboot the phone is **locked by design**
(`NUXEL_INPUT LOCKS[a45.1] … reason=boot locked=1`), and the launcher rejects
app launches while locked (`EVT launch:blocked-locked app=org.nuxel.Notes`).
The owner must:

1. unlock the phone (drag the penguin upward),
2. open **Notes**, tap the empty **Title** field,
3. type `works` after the three POWs are heard.

The detector then records PASS only from a fresh, focused Title containing the
whole word `works` that is also corroborated by the app's own saved store.

## Final reboot (second cold boot, after the 48 kHz fix)

`40-final-reboot-verify.txt` records: graph clock `48000`, effective
`float32le 2ch 48000Hz`, sink `alsa_output.hw_0_1 s16le 2ch 48000Hz`,
Calliope `MUB0`, bot+rcv DSP1 `booted=Y running=Y`, `ABOX RDMA1_EN=1`,
default sink correct, `nuxel-audio-route.sh --check` READY, screen timeout back
at 300 s, Wi-Fi active. The startup cue ran once
(`ExecStartPre` + `ExecStart` = 0/SUCCESS, one `event=boot` entry).

## Other outputs

- Speaker (`Right AMP SPK` → SPEAKER) and receiver (`Left AMP SPK` →
  RECEIVER) are both live in DAPM.
- No 3.5 mm plug and no USB-C audio accessory was attached, so headphone and
  UAC routes are **not tested**; no mixer names were invented for them.
- The Type-C port exists (`/sys/class/typec/port0`); no USB audio card was
  enumerated.

## Safety / non-negotiables observed

- No kernel, bootloader, firmware or partition changes.
- `systemd-udevd` not re-enabled; stub UCM untouched; no invented controls.
- Amplifier gain left at the live 19/19.
- 25 % ceiling enforced at the sink and re-checked before every play.
- Wi-Fi SSH and the serial recovery path were left intact.
- Offline regressions: 87 tests pass, including 14 new PWNAGE-40000 tests.

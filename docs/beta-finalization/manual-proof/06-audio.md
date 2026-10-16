# Area 6 — Speaker audio path (beyond-madera / CS47L93 / CS35L40 / ABox, low volume only)

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED).
Owner action required? **Yes** — whether sound is *audible* is an observation only
a human ear can make. The repository finishes and offline-tests the codec path,
the UCM generation, the low-volume safety cap and the pipeline walker; the
listening result is deferred to the owner.

**Device truth used by this document.** The S10+ (SM-G975F) presents its audio as
the ALSA card **`beyond-madera`**: a **Cirrus Logic CS47L93 (MADERA)** ASoC codec
plus **2× CS35L40** smart speaker amplifiers inside the **Exynos 9820 ABox**.
The card *name* is the anchor — a config that names any other card is wrong for
this device. Pixel BCM4390 / Pixel 10 Pro XL documentation in this repository
does not describe this codec and was not applied.

**Hard rule for this area:** a *writable mixer control is NOT an acceptance criterion* for the beta.
Writability is a property of a register; audibility is a property of a speaker and an ear. The repository never promotes audio to
`VERIFIED_ON_S10PLUS` on the strength of a mixer write.

---

## 1. Feature

The real speaker playback path and its bring-up tooling:

* UCM2 master profile for `beyond-madera`
  (`configs/alsa-ucm/beyond-madera/HiFi.conf`, `beyond-madera.conf`,
  `VoiceCall.conf`);
* PipeWire + WirePlumber device policy
  (`configs/pipewire/nuxel-s10plus-audio.conf.part`,
  `configs/wireplumber/nuxel-s10plus-audio.conf.d/51-nuxel-s10plus-audio.conf`);
* the ALSA-layer low-volume safety cap
  (`configs/pipewire/asound-nuxel-safe.conf`, softvol `max_dB = -6.0`);
* the pipeline walker / capture / tone tool
  `tools/s10plus/a33/nuxel-audio-diag.sh` (also `nuxelctl audio …`) with
  `status`, `pipeline`, `controls`, `capture`, `ucm-install`, `tone`,
  `safe-volume` and `selftest`.

The walker goes in the order sound actually has to travel —
**card → PCM → mixer controls → DAPM widgets → route → “is the DAC/ABox actually
running?”** — and names the **first** stage that is missing, silent or broken.

## 2. Why this matters

The amplifier path on this device is large and device-specific, and a first
bring-up of an unknown path at full scale is a real hazard (to the speaker and to
the wearer's ear). So the default is **low-volume-only**, enforced at the ALSA
layer where a session-manager restore cannot defeat it, and the first tone is a
small fraction of range. The tooling must also be honest: it reports `OK` only
for stages it actually observed, and it never converts "the control accepted a
value" into "the phone makes sound".

## 3. Preparation

1. Handset booted into Nuxel, screen unlocked, console/SSH access.
2. Quiet room, phone at arm's length, volume low. Nothing here should ever be
   driven loud; if it is, stop and treat that as a safety finding.
3. Zero-cost snapshot first — it decides whether there is anything to listen to:

   ```sh
   nuxelctl audio status
   nuxelctl audio status --json
   nuxelctl audio cards
   ```

   If the verdict is `NO_CARD`, `BLOCKED_FIRMWARE` or `NO_PCM`, **stop**: the
   path cannot pass, and the correct next action is the offline bring-up work
   (firmware/DTB/UCM), never a louder retry. `NO_CONTROLS` means no mixer reader
   is installed on the image; `DAC_NOT_RUNNING` means a stream never left
   `SETUP`.

## 4. Exact action

a. Walk the pipeline and record the first broken stage:

   ```sh
   nuxelctl audio pipeline        # card -> PCM -> controls -> DAPM -> route -> DAC
   nuxelctl audio controls        # candidate playback controls (evidence only)
   ```

b. Generate the concrete UCM route from what the card **actually** exposes, then
   install it with a backup and a hash check (nothing is hand-written, no control
   name is invented):

   ```sh
   nuxelctl audio capture         # -> /var/lib/nuxel/audio/controls.{json,raw}
                                  #    /var/lib/nuxel/audio/HiFi.conf.generated
   nuxelctl audio ucm-install --yes
   nuxelctl audio pipeline        # re-walk; the route stage must now be OK
   ```

c. Render the bounded **low-volume** test tone and let the tool decide whether the
   DAC/ABox actually ran:

   ```sh
   nuxelctl audio tone 800 --yes  # 8 % of range, bounded to 800 ms, cap 25 %
   ```

   Then **listen**: do you hear a steady tone from the speaker? Note the verdict
   line the tool prints (`DECISION: ...`) next to what you heard.

d. Re-run `nuxelctl audio tone 800 --yes` while watching the pipeline in another
   shell (`nuxelctl audio pipeline`) and confirm the PCM is in `state=RUNNING`
   **while** the tone plays.

e. Check the cap is real, not a promise:

   ```sh
   nuxelctl audio safe-volume            # prints the ceiling (= the policy cap)
   nuxelctl audio safe-volume 90         # must be REFUSED (> cap)
   ```

f. Save the evidence:

   ```sh
   nuxelctl audio pipeline --json > /tmp/audio-after.json
   journalctl -b --no-pager | grep -i -E 'asoc|madera|cs35l40|cs47l93|abox|dapm' | tail -80
   ```

## 5. Expected result

* `nuxelctl audio pipeline` walks all six stages and ends with verdict
  `OK_DAC_RUNNING`, with `first_broken_stage=none`.
* `nuxelctl audio tone 800 --yes` renders a tone that is **quiet** (≈8 % of
  range, never full scale) and reports `PCM state after the render: RUNNING`,
  i.e. `DECISION: the DAC/ABox ran`.
* `nuxelctl audio safe-volume 90` is refused with a message naming the cap.
* **The owner hears the tone from the speaker.** This is the only line that
  proves audibility; the tool cannot and does not claim it.
* After the bring-up, ordinary playback (a notification, a ringtone) is audible
  at a normal volume without a clipped or missing first moment.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning / next action |
|---|---|
| `NO_CARD` — `beyond-madera` absent from `/proc/asound/cards` | The codec/ABox driver did not bind. Offline kernel/DTB work; not a user error. |
| `BLOCKED_FIRMWARE` — card or DSP firmware absent | Codec DSP firmware (`cs47l93-dsp*.wmfw`, `cs35l40-dsp*.wmfw`) missing from `/lib/firmware`; the DSP will not enumerate. Repository-side deploy only. |
| `NO_PCM` | No playback PCM node under `/proc/asound/cardN/pcm*p`; the DAI link is not up. |
| `NO_CONTROLS` | No `amixer`/`tinymix` on the image, or the card exposes no controls; a package/pipeline problem. |
| `DAC_NOT_RUNNING`, pipeline otherwise `OK` | A stream opened but never left `SETUP`: the amplifier/ABox path is not actually running. This is the "silent phone" case. |
| Pipeline `OK` but you hear nothing | The DAC ran and the register path is fine, yet no sound reaches the ear — a **routing/gain/amp** finding. Report it as unproven audibility, never as a PASS. |
| Tone is very loud | Safety violation: the softvol cap is not installed (`/etc/asound.conf`) or was bypassed. Stop and fix the cap first. |
| Crackles / clipped first word | Amplifier re-enable or clocking; capture the PipeWire/WirePlumber journal excerpt before changing anything. |
| `BLOCKED_EXTERNAL_RESOURCE` on `tone` | No `aplay` on the image; nothing can render the tone. |

## 7. Diagnostic command / log path

* `nuxelctl audio status|pipeline|controls|capture|ucm-install|tone|safe-volume` —
  `tools/s10plus/a33/nuxel-audio-diag.sh`
* Policy: `configs/nuxel/audio/audio.json` → `/etc/nuxel/audio/audio.json`
  (low-volume cap 25 %, first tone 8 %, softvol `max_dB = -6.0`)
* UCM: `configs/alsa-ucm/beyond-madera/HiFi.conf` →
  `/usr/share/alsa/ucm2/beyond-madera/HiFi.conf`
* Generators and evidence: `/var/lib/nuxel/audio/controls.json`,
  `/var/lib/nuxel/audio/controls.raw`,
  `/var/lib/nuxel/audio/HiFi.conf.generated`
* Evidence log: `/var/log/nuxel/audio-diag.log`
* Kernel/session: `dmesg | grep -i -E 'asoc|madera|cs35l|abox|dapm'`,
  `journalctl -b -u pipewire -u wireplumber --no-pager`
* Offline regression: `python3 tools/s10plus/a33/tests/test-audio-diag.py` and
  `nuxel-audio-diag.sh selftest` (eight pipeline fixtures)

## 8. PASS / FAIL

* **PASS** — the pipeline ends `OK_DAC_RUNNING` with `first_broken_stage=none`,
  the low-volume tone renders with `state=RUNNING`, the owner **hears** it from
  the speaker, `safe-volume 90` is refused, and the status JSON plus the kernel /
  session journal excerpts are attached to the report.
* **FAIL** — any of: a `NO_*` / `BLOCKED_*` / `DAC_NOT_RUNNING` verdict, no
  audible tone despite an `OK` pipeline (recorded as unproven audibility), a tone
  that is uncomfortably loud, or a cap that can be exceeded. Quote the exact
  `nuxelctl audio pipeline --json` line — `first_broken_stage` names the layer.

## Current automatic evidence (repository, this build group)

* `tools/s10plus/a33/nuxel-audio-diag.sh selftest` → 8/8 pipeline fixtures PASS
  (`tools/s10plus/a33/tests/fixtures-p3/audio-*`): `NO_CARD`, `BLOCKED_FIRMWARE`,
  `NO_PCM`, `NO_CONTROLS`, `DAC_NOT_RUNNING`, `OK_DAC_RUNNING` (DAPM view
  unavailable), fully `OK`, and route-present-but-empty.
* `python3 tools/s10plus/a33/tests/test-audio-diag.py` → all checks PASS,
  including: the first-broken-stage naming, the "writable controls but silent
  PCM → `DAC_NOT_RUNNING`" case, tone refusal without `--yes`, refusal of a level
  above the cap, the installed softvol ceiling, the generated UCM containing only
  observed controls clamped to the cap, the empty shipped UCM sequences, and no
  flashing surface.
* Audibility is **not** claimed: it stays `NEEDS_OWNER_TEST` in
  `configs/nuxel/capabilities/connectivity-time-audio-buttons.json` until the
  owner records a listening result.
* Owner test registered as `NEEDS_OWNER_TEST` in area 6 of
  `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md` (report group).

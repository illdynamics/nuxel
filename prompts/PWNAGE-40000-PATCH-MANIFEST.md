# PWNAGE-40000 patched source-package manifest

**Package state:** patched source + read-only final-stage diagnostics; physical speaker fix is not yet proven or included.

## Latest owner evidence used

`docs/beta-finalization/live/evidence/pwnage-43000/05-speaker-path-audibility-experiments.md`

No literal `out.md` exists in this archive. The owner's approval to continue is recorded in the experiment file above. It confirms the Notes input preflight passed and records explicit negative `no` responses for the three final speaker experiments.

## Strongest current engineering lead

The digital ABOX/RDMA1/PipeWire/CS35L41 DSP path is active during playback, but the built-in speaker is not audible. The pinned downstream CS35L41 driver lacks the later external-boost `SPK_OUT_ENABLE` handling. That code is hardware-topology-specific. The live S10+ boost mode must be identified before deciding whether that sequence applies. No speculative amplifier register writes or external-boost patch are included.

## Files added or updated in this package

- `tools/s10plus/a33/nuxel-cs35l41-speaker-diag.sh` — new read-only live diagnostic and concurrent PCM/output-power/SoundBoost telemetry watcher.
- `tests/pwnage40000/test_cs35l41_speaker_diag.py` — tests read-only behavior, telemetry capture hooks and kernel patch-wrapper behavior.
- `kernel/s10plus/build-kernel.sh` — idempotent, logged patch application for the patch directory that the documentation already claimed was applied.
- `kernel/s10plus/README-toolchain.md` — corrected toolchain/build-source documentation.
- `kernel/s10plus/patches/README.md` — patch application contract and warning about topology-specific CS35L41 output enable.
- `services/nuxel-s10/bin/nuxel-audio-route.sh` — corrected misleading comment: gain 12 is not an acoustically confirmed value.
- `audio.md` — updated current status and next diagnostic.
- `docs/beta-finalization/live/PWNAGE-40000-AUDIO-ROOT-CAUSE.md` — evidence-led final-stage root-cause analysis.
- `docs/beta-finalization/live/PWNAGE-40000-TODO.md` — superseding owner-supervised test results and new work items.
- `docs/beta-finalization/live/PWNAGE-40000-REPORT.md` and `docs/beta-finalization/live/evidence/pwnage-40000/FINAL-REPORT.md` — explicitly supersede older Notes-input status with later valid `no` responses.
- `pwnage-40000.md` — updated Kickstarter.
- `full-pwnage-40000.md` — updated final physical speaker repair prompt.
- `PWNAGE-40000-DEPLOY-WIFI-SSH.md` — detailed Wi-Fi SSH deployment and live-fix prompt.

## Local validation performed

- Bash syntax check: diagnostic and kernel build wrapper passed.
- Embedded Python watcher syntax: passed.
- Python compile: diagnostic test and Notes detector passed.
- Focused PWNAGE-40000 + audio-rate/firstlight + related Bluetooth regression suite: 42 passed.
- Existing offline `tools/s10plus/a33/tests/test-audio-diag.py`: 0 failing checks.
- Existing kernel patch files 0003 and 0004 parse with `git apply --stat`.

## Not performed / not claimed

- No access to the physical S10+ speaker from this packaging environment.
- No owner acoustic confirmation was fabricated.
- No kernel source clone/build was performed.
- No new CS35L41 driver patch was added.
- No TWRP, kernel, boot image, bootloader, firmware partition or storage flashing was performed.
- Existing diagnostic still needs to be run over Wi-Fi SSH on the live phone.

## Next live action

Deploy the read-only diagnostic over Wi-Fi SSH, capture actual live boost topology and output-power telemetry during one owner-supervised POW test, then implement only the topology-correct amplifier output-enable fix. Require a fresh Notes `yes`/`works` and post-reboot confirmation.

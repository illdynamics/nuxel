# PWNAGE-40000 — WIFI SSH DEPLOYMENT & LIVE SPEAKER-OUTPUT FIX PROMPT

## MANDATORY MODEL

Use `deepseek-v4-pro-thinking` for all repository analysis, diagnosis, source changes, test design, kernel-driver review and live iteration. Do not silently switch to a smaller model. If unavailable, report the limitation.

## TARGET AND ACCESS

- Target: Samsung Galaxy S10+ SM-G975F / beyond2lte.
- Last recorded target: `root@192.168.178.167`.
- Last recorded SSH key: `~/.ssh/wicked_wqn_id_rsa`.
- Transport: the currently working WLAN SSH route.
- Do not assume the address or key still match: verify before connecting.
- Never print, copy off-host, upload or disclose the private key.

## MISSION

Deploy the patched Nuxel source changes over Wi-Fi SSH, run the new read-only speaker diagnostics on the actual phone, identify the final physical speaker-output failure, and continue the PWNAGE-40000 repair loop until the owner confirms audible output through Notes.

The supplied archive contains no literal `out.md`. The owner's affirmative decision is recorded in `docs/beta-finalization/live/evidence/pwnage-43000/05-speaker-path-audibility-experiments.md`.

The latest physical test results are NEGATIVE and valid: the Notes input preflight passed; the owner typed `no` after the SPEAKER mode, 55% volume and DSP-source tests. Respect these results. Do not repeat the same failed variants unchanged.

---

# PHASE 1 — VERIFY LOCAL SOURCE AND REMOTE TARGET

1. Identify the exact local Nuxel repository root containing this prompt.
2. Confirm the expected files exist:
   - `tools/s10plus/a33/nuxel-cs35l41-speaker-diag.sh`
   - `tools/s10plus/a33/notes-works-detector.py`
   - `services/nuxel-s10/bin/nuxel-audio-route.sh`
   - `kernel/s10plus/build-kernel.sh`
   - `docs/beta-finalization/live/PWNAGE-40000-AUDIO-ROOT-CAUSE.md`
3. Capture local `git status` if the checkout is a Git worktree. Do not overwrite uncommitted work.
4. Verify the private key exists without displaying its content.
5. Verify host-key identity using the existing known_hosts entry. Do not use `StrictHostKeyChecking=no` as a shortcut.
6. Connect to the last recorded phone address only after confirming it is the handset.
7. Confirm the session's source and reply route are WLAN. Capture `SSH_CONNECTION`, `ip route get <client-ip>`, interface type and current Wi-Fi device state.
8. Preserve the active Wi-Fi SSH session. Do not turn Wi-Fi off, restart NetworkManager, bring down the interface or alter its profile.

If the remembered target IP is no longer reachable, inspect the project's existing known host/tri-link configuration. Do not scan unrelated networks or guess another address.

# PHASE 2 — BACKUP AND DEPLOY THE PATCHED DIAGNOSTICS

Create a timestamped remote evidence/backup directory, for example:

`/root/pwnage-40000/final-speaker-deploy-<UTC timestamp>/`

Before replacing any existing remote file, copy it to that directory and record its SHA-256.

Deploy the new read-only diagnostic to:

`/usr/local/sbin/nuxel-cs35l41-speaker-diag.sh`

Install it with mode `0755` and verify its remote hash against the local source.

The diagnostic is read-only: it must not start playback, modify ALSA controls, write sysfs, write GPIO, write regmap, change firmware, restart services or mount debugfs. Confirm the deployed `--help` explicitly says READ-ONLY.

Compare the Notes detector source and known deployed path:

- Source: `tools/s10plus/a33/notes-works-detector.py`
- Deployed executable: `/usr/local/bin/nuxel-notes-works-detector`

One earlier log used `/usr/libexec/nuxel/notes-works-detector.py`, which did not exist. Do not repeat that stale path. If source and deployed hashes differ, back up the old detector, deploy the current source to the correct path and verify executable permissions/imports. Do not break the currently working Notes application or storage model.

Do not overwrite the live route script, PipeWire config or kernel without a specific diagnosis. The current baseline has valuable working settings. Preserve them first.

# PHASE 3 — CAPTURE LIVE BASELINE (NO WRITES)

Run the deployed diagnostic as root:

```bash
sudo /usr/local/sbin/nuxel-cs35l41-speaker-diag.sh \
  --out /root/pwnage-40000/final-speaker-deploy-<UTC timestamp>/baseline
```

Inspect and summarize:

- Calliope version and runtime PM state.
- Both CS35L41 I2C devices and live OF/DT properties.
- Each amplifier's boost type / boost-related GPIO properties if exposed.
- Each DSP1's `booted`, `running`, `fw_id`, `fw_id_version`, firmware names and state.
- ALSA card identity and RDMA1 PCM.
- All relevant mixer controls, including `ABOX Sound Type`, both AMP gain/mute/enable, PCM Source, boost controls and `ABOX SOUNDBOOST_A/B/EN`.
- `PL_SPK_OUTPUT_POWER` and `L_SPK_OUTPUT_POWER` idle values.
- DAPM widgets.
- Read-only regmap snapshot if debugfs is already mounted.
- PipeWire process/session/socket, sink, default sink and actual volume.
- Kernel audio/CS35L41/CSPL/mailbox/boost/rail messages.

Confirm current live settings; do not assume archived values. The latest recorded state after experiments was Sound Type VOICE (0), PCM Source ASP (0), PipeWire volume 0.25, AMP PCM Gain 12/12, and route applied, but re-read everything on the live handset.

## IMPORTANT: FIRST FIND THE FINAL AMP/BOOST STAGE

The latest experiments already tested:

- ABOX Sound Type SPEAKER (1) at 25% and 55%: no sound.
- CS35L41 PCM Source DSP with SPEAKER mode: no sound.

Do not repeat these exact experiments first.

The pinned 4.14.253 driver calls `cirrus_pwr_start()` from its main amp DAPM event after setting `PWR_CTRL1.GLOBAL_EN`. That is Passport power/thermal monitoring, not the newer external-boost `CSPL_MBOX_CMD_SPK_OUT_ENABLE` speaker-output sequence.

The latter is specific to external-boost hardware. The historical captured DTB does not prove the current handset uses external boost. Positively identify live topology from live DT, OTP/driver data and both amplifier configurations before porting anything.

Investigate:

1. Does either CS35L40-compatible amplifier actually use external, internal or shared boost?
2. Are the boost rails and enable GPIOs correctly configured?
3. Are the DSP output-power controls changing during playback?
4. Are ABOX SoundBoost controls required by this topology?
5. Is the Right AMP physical SPEAKER output enabled and receiving nonzero samples?
6. Does the pinned driver miss a required output-enable sequence for this exact topology?

Do not apply a speculative register write.

# PHASE 4 — NOTES INPUT PREFLIGHT

The owner will have Nuxel Notes open with the Title field focused.

Before any sound test:

1. Verify the currently active `#note-title` element via AT-SPI.
2. Verify focused, showing and editable state.
3. Verify the screen is awake.
4. Ask the owner to type `ready` physically.
5. Run `/usr/local/bin/nuxel-notes-works-detector --timeout 30 --out <run-dir>` or its appropriate preflight mode if the source supports it; verify the live model/store reflects the new input.
6. Clear the field and establish a fresh baseline before each test.

The latest experiment says preflight passed and the owner typed `no`, but revalidate for this deployment session and after reboot.

Do not programmatically inject `ready`, `yes`, `works` or `no`. The owner must type the response.

If Notes input fails, repair the observation path first. A blank field cannot be treated as silence when the input channel is broken.

# PHASE 5 — ONE POW, FULL 30-SECOND OWNER RESPONSE

For every controlled iteration:

1. Announce test ID, what changed, current speaker route and volume.
2. Start a fresh 4-second diagnostic watcher BEFORE playback:

```bash
sudo /usr/local/sbin/nuxel-cs35l41-speaker-diag.sh \
  --out <run-dir>/test-XX --watch-seconds 4 --interval-ms 25
```

Keep that capture process alive while the playback begins. If the tool exits after 4 seconds, collect its JSONL afterward.

3. Identify the actual Nuxel PipeWire user and runtime socket from the live process/service environment. Do not guess a user, UID, runtime directory or socket.
4. Play the exact deployed asset exactly ONCE through PipeWire's verified default sink:

```bash
pw-play --volume 1.0 /usr/share/nuxel/assets/nuxel-pow.mp3
```

Run it as the account owning the working PipeWire session, with the verified `XDG_RUNTIME_DIR`, `PIPEWIRE_RUNTIME_DIR` and socket environment. Do not run direct ALSA playback against a PCM already owned by PipeWire.

5. Immediately after the playback finishes, start the Notes detector with `--timeout 30`, using the fresh Title baseline. The owner receives a full 30-second response window.
6. Do not play any other sound during those 30 seconds.
7. Classify:
   - exit 0 / fresh `yes` or `works`: audible PASS;
   - exit 3 / fresh `no`: audible FAIL;
   - exit 1 / empty after 30s: no audible response, if preflight passed;
   - exit 2: Notes/AT-SPI channel failure; not an audio verdict.
8. Save detector JSON, diagnostic JSONL, player exit status, exact command, settings and timestamp.
9. Reset Title to empty and verify fresh baseline before another test.
10. Continue the same SSH/agent session; do not make the owner restart the whole mission.

Do not repeat playback within a test. No 3-play batches. No diagnostic tones. No volume chimes. One asset invocation only.

# PHASE 6 — EVIDENCE-LED FIX

Preserve verified baseline:

- Calliope `MUB0`.
- Both DSP1 protection engines booted/running.
- RDMA1 enabled and routed.
- PipeWire static sink `alsa_output.hw_0_1`.
- 48 kHz hardware clock.
- Current known-good amp gains and protection.

Use telemetry during playback:

- PCM status/hw_params and hardware pointer.
- PipeWire stream node and link.
- Right AMP DAPM/output path.
- `PL_SPK_OUTPUT_POWER` and `L_SPK_OUTPUT_POWER` values during the actual sound.
- Cirrus power class values if exposed.
- ABOX SoundBoost controls.
- Relevant driver/CSPL mailbox logs.

A player `rc=0`, active DMA, DAPM ON or DSP READY is not proof of speaker audibility.

## If external boost is positively established

Inspect the upstream CS35L41 external-boost driver change and backport its complete safe sequence to the exact pinned 4.14.253 source. The mailbox `CSPL_MBOX_CMD_SPK_OUT_ENABLE` is firmware-version dependent; firmware v0.28.0 and older do not support it, so verify `fw_id_version` and provide the proper supported legacy sequence. Port the complete power-up/power-down sequencing, test-key lock/unlock, PUP/PDN wait, timeout and error paths. Preserve thermal/protection firmware. Apply the correct sequence to the correct amplifier(s) only.

## If internal/shared boost is established

Do not use external-boost-specific commands. Identify the correct topology-specific rail/GPIO/driver/DAPM/ABOX boost enable path and port only the matching proven sequence.

## If output power is zero during active PCM

Investigate signal arrival at DSP, SoundBoost and final amp enable in this order. Determine whether the DSP is receiving samples, generating output, and delivering power. Do not assume zero idle telemetry is a fault; compare active samples.

## If output power is nonzero but no sound

Investigate the right physical speaker route, output mute/connector/supply and speaker transducer. Do not make repeated PipeWire changes if the signal already reaches the amplifier's output stage.

Only one logical group of changes per iteration. Back up control values and source files. Every experiment must have explicit rollback.

# PHASE 7 — KERNEL PATCHING AND SAFETY

The patched repository now fixes a real tooling defect: `kernel/s10plus/build-kernel.sh` previously did not actually apply `kernel/s10plus/patches/*.patch`, despite claiming to do so. It now applies in lexical order, skips stubs, detects already-applied patches, logs outcomes and supports a `.required` sidecar.

If a kernel patch is needed:

1. Build/test against the exact pinned commit.
2. Inspect patch application log.
3. Verify the patch applies and reverse-checks.
4. Review the complete source diff.
5. Run compile/static checks where toolchain allows.
6. Confirm no unrelated driver or platform changes.
7. Keep the built artifact and hash.
8. Do not flash it automatically.

The owner has explicitly said a TWRP reflash is not needed and has not authorized destructive reflash operations. Do NOT TWRP reflash, flash boot.img/kernel, alter bootloader, write modem/EFS/firmware partitions, repartition or format. A local kernel build is allowed only if the diagnosis requires it; deployment/flashing of that kernel requires separate explicit approval.

Never bypass CS35L41 DSP protection, thermal controls or limiter. No arbitrary userspace protected-register writes. No direct I2C/SPI pokes. No unverified firmware blobs.

# PHASE 8 — PERSIST THE FIRST CONFIRMED FIX

When the owner first confirms `yes` or `works`:

1. Immediately stop changing the working route.
2. Capture all mixer settings and readbacks.
3. Capture boost mode, GPIO/regulator state and driver logs.
4. Save output-power telemetry and PipeWire route.
5. Save the fresh Notes confirmation JSON without unrelated note content.
6. Identify the exact code/config source required to restore this setting every boot.
7. Update source and staged/deployed versions consistently.
8. Update route readiness so it verifies the actual final output enable, not just RDMA1/DSP state.
9. Add regression tests for the new route/driver behavior.
10. Preserve one-time startup audio semantics and the boot readiness gate.
11. Do not make the diagnostic/test runner a production dependency.
12. Prepare backup/rollback before any reboot.

# PHASE 9 — REBOOT AND POST-BOOT AUDIBLE ACCEPTANCE

Only reboot after the actual speaker has been heard and the working route is persistent and backed up.

Before reboot:

- Save evidence and state.
- Verify WLAN SSH recovery path.
- Verify boot service dependencies.
- Verify route and driver source/stage parity.
- Ensure no temporary test process is required for normal audio.

Reboot normally, reconnect by WLAN SSH using the specified key, verify the new boot ID and all ABOX/CS35L41/boost/route/PipeWire state. Ask owner to reopen Notes and rerun the input preflight. Perform one POW and wait the full 30 seconds. Require fresh `yes` or `works` after this reboot.

If a post-boot confirmation fails, revert to the captured known-good software baseline and continue diagnosing. Do not pretend the manual test is proof of persistence.

# PHASE 10 — REQUIRED DELIVERABLES

Create/update:

- `docs/beta-finalization/live/PWNAGE-40000-TODO.md`
- `docs/beta-finalization/live/PWNAGE-40000-REPORT.md`
- `docs/beta-finalization/live/PWNAGE-40000-AUDIO-ROOT-CAUSE.md`

Store each run under:

`docs/beta-finalization/live/evidence/pwnage-40000/final-speaker-<UTC>/`

Report source and deployed hashes, boost topology, driver sequence, output telemetry, every test and owner response, persistent changes, post-boot confirmation, blockers and rollback.

# FINAL ACCEPTANCE

PASS requires all of the following:

- Correct live boost topology established.
- Correct final speaker-output enable/power sequence implemented.
- Right AMP physical speaker route verified.
- Existing ABOX/Calliope/CS35L41 protection path preserved.
- PipeWire/RDMA1 48 kHz path preserved.
- Owner hears the real `nuxel-pow.mp3` and types fresh `yes` or `works` in the Notes Title field.
- Exact successful settings/driver path made persistent.
- Fresh reboot completed.
- Fresh post-boot one-play/30-second confirmation succeeds.
- No TWRP/boot/kernel flashing without separate explicit approval.

If any physical component or proprietary input remains unavailable, report the exact missing evidence and dependency. Do not fake a PASS.

**Do not stop at a successful player process. Fix the final output stage and obtain the owner's audible confirmation.**

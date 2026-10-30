# PWNAGE-40000 — FINISH NUXEL AUDIO PROPERLY
## The Penguin Must POW on Demand and After Every Boot

**Device:** Samsung Galaxy S10+ SM-G975F / beyond2lte
**OS:** Nuxel, Fedora-based ARM64
**Connection:** Wi-Fi SSH
**SSH key:** `~wicked/.ssh/wicked_wqn_id_rsa`
**Test asset:** `./assets/nuxel-pow.mp3`

## THE IMPORTANT DISCOVERY

We already heard audio during yesterday's experiments: a 440 Hz tone, another diagnostic tone, and multiple POWs. This proves that at least one actual hardware output path has worked. The archive's earlier statement that physical audio was unconfirmed predates that newer human confirmation.

The repository contains several concrete clues explaining why audio is not reliably persistent:

### 1. A missing critical mixer control in the checked-in route script

`services/nuxel-s10/bin/nuxel-audio-route.sh` explicitly says that `ABOX RDMA1_EN` does not exist.

However, the later live evidence `live-audio-evidence-20261029b.txt` records that control as present and OFF. Setting it ON was part of the live routing correction.

**The checked-in boot script must be reconciled with the proven live route. Do not deploy the stale script over the working live configuration.**

### 2. A cold-boot ABOX firmware problem

The ABOX is probed before the root filesystem is mounted. Its Calliope core firmware is therefore unavailable during the initial kernel probe.

The userspace suspend/resume workaround sometimes reloads it, but audio must not be considered ready until:

`/sys/devices/platform/18c50000.abox/calliope_version` reports `MUB0`.

### 3. An unreliable audio-ready test

The boot cue currently relies partly on the existence of `/run/nuxel-audio-route.state`, which does not necessarily prove that the route is applied. Its asset existence condition also checks `nuxel-boot-audio.mp3`, while the sound-cue program actually plays `nuxel-pow.mp3`.

Fix the real readiness conditions.

### 4. A highly device-specific playback path

The known working hardware PCM is RDMA1 (`hw:0,1`) at 48 kHz. RDMA0 does not advance its hardware pointer, and the tested RDMA1 44.1 kHz path returns EIO.

Preserve the static PipeWire RDMA1 sink and verify the actual runtime sample rate.

## THE HUMAN CONFIRMATION AGREEMENT

I will unlock the phone, open Notes, and leave an empty Title field focused.

You will:

1. Fix and deploy the next audio improvement.
2. Play `./assets/nuxel-pow.mp3` exactly THREE times, sequentially.
3. Wait for me to hear it.
4. Detect the literal word `works` appearing in the currently focused Notes Title field.
5. Record PASS only when that fresh entry is detected.
6. If it is not detected, continue diagnosing and fixing without restarting the entire mission.

The Notes implementation already exposes useful interfaces: `#note-title`, the `nuxel-notes` store, and `window.nuxelNotes.app()`. Inspect and use the actual live application model/storage where possible. Do not rely on stale saved text.

**A successful playback command is not confirmation that I heard the sound.**

## REQUIRED ORDER

1. Connect over Wi-Fi SSH using the specified key.
2. Create the TODO and evidence directories.
3. Compare the running phone's audio configuration with the checked-in repository. Protect any working live configuration.
4. Establish the Notes `works` detection mechanism.
5. Repair the actual ABOX/CS35L41 routing, starting with the missing `ABOX RDMA1_EN` configuration.
6. Fix persistent Calliope firmware readiness and verify `MUB0`.
7. Verify RDMA1 at 48 kHz, actual PipeWire default-sink selection, and real hardware-pointer progress.
8. Run the three-POW confirmation loop until the internal speaker is audibly confirmed.
9. Make all working mixer settings, services, routing and playback persistent.
10. Make the startup POW run once, only after genuine audio readiness.
11. Repair Audio Settings → Test Audio and volume feedback to use the same working PipeWire playback path.
12. Test other physically available output routes.
13. Reboot, reconnect over Wi-Fi SSH, and repeat the three-POW confirmation after boot.

## TECHNICAL NON-NEGOTIABLES

- Distinguish Samsung ABOX Calliope firmware from the separate CS35L41 amplifier DSP1 protection firmware.
- Verify both amplifier DSPs are actually booted and running.
- Do not assume DAPM widgets being ON means the speaker is audible.
- Do not accept `pw-play` exit code zero as proof of audibility.
- Check the return value of PipeWire default-sink selection; the current bridge calls `_ensure_default_sink()` but ignores its result.
- Use `pw-play` through PipeWire when PipeWire owns RDMA1. Do not use a direct ALSA player against a PCM already held by PipeWire.
- Keep the hardware clock and RDMA1 stream at 48 kHz.
- Keep a safe output-volume ceiling of 25%. Do not blindly copy amplifier gain values from old captures.
- Do not fill the S10+ stub UCM profile with invented mixer controls.
- Do not re-enable `systemd-udevd` blindly.
- Do not flash firmware, rebuild/replace/flash the kernel, alter the bootloader, or repartition storage without separate explicit authorization.
- Preserve Wi-Fi SSH and recovery access.

## DEFINITION OF DONE

- The proven live audio route is present in source and deployed configuration.
- `ABOX RDMA1_EN` and the other required routing controls have correct verified values.
- The ABOX Calliope core reports `MUB0` on cold boot.
- CS35L41 DSP1 protection firmware is loaded and running for both amplifiers.
- RDMA1 operates at 48 kHz, with actual hardware pointer advancement.
- The internal speaker produces audible POWs confirmed using Notes.
- Audio survives ending the test process, restarting Nuxel, and rebooting.
- A single startup POW plays after audio is genuinely ready.
- Settings Test Audio uses the working playback backend.
- Volume feedback works without overlapping playback or draining the battery.
- Other supported outputs are tested honestly; unavailable routes are documented.
- Final reboot and post-boot audible confirmation pass.

**This is a persistence and boot-readiness repair, not another temporary audio experiment. Make the working path permanent.** 🐧

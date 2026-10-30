# PWNAGE-43000 — Pre-wayland ABOX reload experiment

**Date:** 2026-10-30
**Target:** root@192.168.178.167 (S10+ beyond2lte) over Wi-Fi SSH
**Key:** ~/.ssh/wicked_wqn_id_rsa

## Hypothesis
Run the ABOX Calliope firmware reload before `nuxel-wayland.service`, when no
PipeWire exists to hold the uninterruptible ABOX runtime-PM reference, so the
display bridge is never torn down.

## Deployed change (device, then reverted)
- `nuxel-abox-firmware-reload.service`: pre-wayland one-shot
  (`After=local-fs.target sound.target systemd-udev-trigger.service`,
  `Before=nuxel-wayland.service`, `WantedBy=multi-user.target`).
- `nuxel-abox-firmware-reload-boot.sh`: removed Wayland stop/start; bounded PM
  cycles only.

## Cold-boot result
- ABOX reached `MUB0` after 2 PM attempts (~40 s).
- `nuxel-wayland` started only after ABOX reload; `nuxel-wl-fb` started once and
  stayed up (no Wayland restart storm).
- **Regression:** both CS35L41 amp DSP1s stayed `booted=Y running=N`,
  `wmfw_file_name=` empty, `fw_id=0`. Playback logged the known
  `Timout waiting for DSP to set mbox cmd` mailbox failure.

## Variants tried (all with pre-wayland ABOX ordering)
1. `nuxel-audio-route.service` ordered after `nuxel-abox-firmware-reload`
   and before `nuxel-wayland` — amp DSP1 still did not load.
2. `nuxel-audio-route.service` ordered after `nuxel-wayland` — amp DSP1 still
   did not load.
3. Active `pw-play` stream + toggle `Left/Right DSP1 Preload Switch` off/on —
   amp DSP1 still did not load.

## Rollback
Restored known-good unit/wrapper and `nuxel-audio-route.service` ordering,
rebooted. After rollback:
- `codec:cs35l41-codec.0.auto booted=Y running=Y fw=cs35l40-bot-dsp1-spk-prot.bin`
- `codec:cs35l41-codec.4.auto booted=Y running=Y fw=cs35l40-rcv-dsp1-spk-prot.bin`
- `nuxel-audio-route --check` => READY (calliope=MUB0, dsp1=2/2, route verified).

## Audio confirmation test (known-good after rollback)
- Notes Title focused/editable, single `pw-play /usr/share/nuxel/assets/nuxel-pow.mp3`.
- `pw-play rc=0`.
- Owner response in Notes Title: `no` => **no audible sound**.

## Conclusion
Pre-wayland ABOX reload fixes the Wayland teardown storm but uncovers/creates a
separate blocker: the CS35L41 protection DSP firmware does not load under this
ordering. Until the amp DSP boot sequence is fixed independently, the pre-wayland
reload is not shippable. Device left on known-good configuration.

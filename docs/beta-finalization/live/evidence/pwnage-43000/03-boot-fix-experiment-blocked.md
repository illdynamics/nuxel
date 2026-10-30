# PWNAGE-43000 — Audio decoupling experiment (BLOCKED by kernel, rolled back)

**Date:** 2026-10-30
**Status:** Experiment rolled back to known-good. Device healthy over Wi-Fi SSH.

## Hypothesis
Move PipeWire/WirePlumber out of the phoc session into a standalone
`nuxel-audio-session.service` so the ABOX Calliope firmware reload can stop only
the audio stack and leave the AMOLED display bridge + launcher running.

## What was deployed (then reverted)
- New `nuxel-audio-session.service` + `nuxel-audio-session.sh`.
- `nuxel-session.sh`: audio startup removed (env exports kept).
- `nuxel-abox-firmware-reload-boot.sh`: stop/start audio-session instead of wayland.
- `nuxel-abox-firmware-reload.service`: ordered after audio-session.

## Result (cold boot)
- `nuxel-wayland` and `nuxel-wl-fb` stayed `active` across an audio-session
  restart in a live pre-reboot test (good).
- On the real cold boot, the ABOX reload entered a stop/start storm:
  - PipeWire/PipeWire-Pulse could not rebind `/run/nuxel-wayland/pipewire-0*`
    and `/run/nuxel-wayland/pulse/native` because the previous instance was
    stuck in an uninterruptible ABOX runtime-PM state (`D` state) and survived
    SIGTERM/SIGKILL (`Processes still around after final SIGKILL`).
  - The ABOX wrapper's bounded waits timed out, `nuxel-audio-session.service`
    kept failing/restarting, the launcher display bridge restarted 7 times, and
    the boot did not reach `finish` in the observation window.

## Root-cause note (why the current design couples audio to the UI)
The current `nuxel-abox-firmware-reload-boot.sh` stops the **entire**
`nuxel-wayland.service` (phoc cgroup) precisely because a standalone PipeWire
cannot be reliably reaped while it holds the ABOX runtime-PM reference on this
4.14 vendor kernel. Decoupling audio from the compositor therefore does not work
without first solving the unreapable D-state PipeWire problem.

## Corrected next step (to try)
Reorder the ABOX firmware reload to run **before** `nuxel-wayland.service`
(after `/dev/snd/controlC0` appears), when no PipeWire process exists to hold
the PM reference. This would avoid stopping the UI entirely. Requires a new,
pre-wayland one-shot reload (no session stop/start) and a reboot to verify.

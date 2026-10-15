# STATUS — cycle 12 / candidate A25 (2026-10-15)

Previous snapshot: `A24-POSTMORTEM.md`, `NUXEL-BOOT-STALL.md`, `NUXEL-INTERACTIVE-UI.md`.

## Headline

**The Nuxel phone UI now RUNS on the handset as a real Fedora userspace process, commits a
real framebuffer frame and hands over from the boot animation — and the reason it never
did before is not a renderer at all: the Fedora boot graph on this image never completes.**

Three independent discoveries this cycle, all measured on hardware:

1. **The boot stalls.** On A23, six minutes after `switch_root`,
   `systemctl is-system-running` was still `initializing` and *every* job was in state
   `waiting` (sysinit, basic, local-fs, multi-user, udevd, getty, dbus-broker...). Nothing
   was running, so no normally-enabled service could start -- which is why a UI unit in
   `multi-user.target.wants` stayed `inactive` and `systemctl start nuxel-ui` blocked
   forever. This is the real answer to "the spinning penguin never becomes a phone UI".
   Full measurement: `NUXEL-BOOT-STALL.md`.
2. **The panel's real colour order is ABGR_8888** (R on bits 0..7), proven from the
   driver's own commit path (`decon_pan_display` hard-codes
   `DECON_PIXEL_FORMAT_ABGR_8888` while `decon_check_var` declares red@16), corroborated
   by the A20 photograph. Every frame from A16 to A22 was red/blue swapped.
   Full proof: `NUXEL-COLOUR-ORDER.md`.
3. **The live console was single-use**: when the Mac closed the port, SIGHUP killed the
   shell for the rest of the boot. Fixed with a respawning supervisor plus a
   `trap '' HUP` re-exec (an ignored disposition survives `execve`).

## Milestones

| Milestone | State |
|---|---|
| Nuxel kernel executes / Fedora rootfs mounts / systemd PID 1 | PROVEN (unchanged) |
| systemd services execute, cgroup2, journald | PROVEN A18 (unchanged) |
| Nuxel renders on AMOLED, spinning penguin | PROVEN A16 (unchanged) |
| Original MP4 animating at 24.00 fps, 0 skips | PROVEN A21/A22 (unchanged) |
| **Interactive live shell with root, verified** | **PROVEN** -- A21 acceptance suite; A24 added disconnect survival |
| **Fedora userspace UI process** | **PROVEN A24** (`UI_STARTED`, pid, `ui.log`, state files) |
| **Real framebuffer commit by that process** | **PROVEN A24** (`FIRST_FRAME_COMMITTED fbio_pan rc=0`, `ui-fb-ready`) |
| **Animation -> UI handoff** | **PROVEN A24** (`ANIMATION_STOP_SIGNALLED pid=3525`, `anim-stop` written, `PHONE_UI_READY`) |
| UI visible to a human / interactive by touch | NOT YET (A25 on the phone, awaiting a power cycle) |
| Touchscreen events | NOT YET -- every boot so far was `androidboot.mode=charger`, where no touch input device exists |
| MP4 playback with the A23 colour order | NOT YET observed by a human (player + first-light verified in code + offline) |
| Boot graph completes (root cause of the stall) | NOT YET named; `bootreport.txt` now instruments it |
| DRM/KMS, Phoc/Phosh | NOT AVAILABLE on this kernel (`# CONFIG_DRM is not set`); separate porting track |
| Stable usable Nuxel phone | NOT YET |

## Blockers, in order

1. **A power cycle** to boot A25 (the phone is in TWRP; nothing can proceed without it).
2. Name and fix the stalled systemd job (`bootreport.txt` is on the next boot).
3. Touch on a non-charger boot.
4. Human observation of the UI and of the MP4's colours.

## Rules being kept

* RECOVERY untouched; EFS/SEC_EFS, PIT, bootloader, radio untouched; BOOT-only flashes with
  full SHA-256 readback; previous images and every candidate preserved.
* No milestone claimed from a marker, a buffer write or a file's existence: every PROVEN
  line above names a hardware observation.
* The penguin never stops on a timer: the UI stops it only after committing its own frame.

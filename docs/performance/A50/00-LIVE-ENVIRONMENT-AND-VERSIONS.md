# A50 — 00: Live environment and versions

Captured read-only over the Nuxel S10+ Live Console (`/dev/cu.usbmodem201`,
VID 0x18d1 / PID 0x4ee7 / serial `NUXEL-S10PLUS-0001`, 115200 8N1) on
2026-10-22 (CEST). Every remote command ran through the capability-based,
framed, SHA-256-verified `tools/beta/live/nuxel_live.py` path. No flashing, no
partition writes, no kernel/bootloader changes, no reboot.

## Device identity (live)
| Field | Value |
|---|---|
| Model | Samsung Galaxy S10+ SM-G975F (`androidboot.em.model=SM-G975F`) |
| Codename | beyond2lte |
| Board | `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820` |
| Bootloader | `G975FXXSEFUL1` (revision 26, warranty_bit=1, verifiedbootstate=orange) |
| Kernel | `Linux fedora 4.14.253 #15 SMP PREEMPT … aarch64` (vendor kernel, CONFIG_DRM unset) |
| OS | Fedora Linux 43 (Forty Three) |
| Boot mode | normal (no `androidboot.mode=charger` in `/proc/cmdline`) |
| Console | root shell (`uid=0`); `/opt/nuxel/nuxel-console /newroot` |

## Repository
- Branch: `nuxel/A50-operation-smooth-penguin` (created for this mission from `nuxel/bootscreens-orientation-big-screen`)
- HEAD: `5aa29fbbdbe997ca31465e237346d6ecf2a9db4d`, describe `v0.6.0-beta-26-g5aa29fb`
- `git status` before work: ahead 7 commits, untracked `NUXEL-A50-…md`, `smooth.md` only.

## Running services (systemd, live)
| Unit | state | enabled |
|---|---|---|
| nuxel-wayland | active | enabled |
| nuxel-wl-fb | active | enabled |
| nuxel-button-manager | active | enabled |
| nuxel-touch-arm | active | enabled |
| seatd | active | disabled (Wants dependency) |
| nuxel-pwa | inactive | not-found (not used; static web server runs inside session) |
| nuxel-console | inactive | disabled (started pre-systemd by initramfs) |
| nuxel-metricsd | inactive | (available but not running) |

Main PIDs: phoc **5352**, nuxel-wl-fb **5399**, nuxel-button-manager **5400**,
nuxel-pwa-host **5389** (child of phoc), WebKitWebProcess **5450**,
nuxel-navdock **5409**, phosh-osk-stevia **5413**.

## Deployed binaries vs repository
| Binary | Live path | sha256 (live) | repo source |
|---|---|---|---|
| nuxel-wl-fb | `/usr/lib/nuxel/nuxel-wl-fb` | `bc38e12d…` (78600 B, Oct 21 08:43) | **NOT in repo** — live is newer than `tools/s10plus/a34/nuxel-wl-fb.c` |
| nuxel-wl-fb.prev | same dir | 78304 B, Oct 19 02:26 | a34-era |
| nuxel-wl-fb.prev-a32 | same dir | 76160 B, Sep 15 | a32 |
| nuxel-pwa-host | `/usr/lib/nuxel/nuxel-pwa-host` | 78512 B, Oct 21 08:37 | `tools/s10plus/a45/nuxel-pwa-host.c` |
| nuxel-button-manager | `/usr/lib/nuxel/nuxel-button-manager` | 77360 B, Oct 21 08:38 | `tools/s10plus/a45/nuxel-button-manager.c` |

**Critical finding:** the deployed `nuxel-wl-fb` binary is an **uncommitted build
newer than any `nuxel-wl-fb.c` in the repository.** Its state protocol includes
`DISPLAY_SLEEP … capture=stopped`, `FRAMES_OK … blits=… present_skipped=…
idle_ms=…`, and the wlr-screencopy v3 requests `copy_with_damage` /
`capture_output_region` — none of which exist in a34 (the newest committed
source). The on-device staged source is only `src/a33/nuxel-wl-fb.c`. Therefore
**no a34-derived rebuild may be deployed over this binary** (it would regress the
already-working damage-skip and screen-off capture-stop behavior).

## Known-good recovery path
The USB live console (pre-systemd) plus the `.prev`/`.prev-a32` rollback
binaries plus the standard service units constitute the recovery surface. See
`08-ROLLBACK.md`. No persistent change was made during A50 inventory/baseline.

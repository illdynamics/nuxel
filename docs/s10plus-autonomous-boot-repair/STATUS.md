# STATUS — cycle 7 / candidate A17 (2026-10-15)

**Mission:** boot Nuxel (Fedora 43 aarch64) on Samsung Galaxy S10+ SM-G975F
(`beyond2lte`), Exynos 9820 rev 26, bootloader G975FXXSEFUL1, TWRP 3.7.0_9-2,
ADB serial R58M75KDB2X.
Previous snapshots: `STATUS.md.cycle3`, `.cycle4-pre-A13`, `.cycle4-final`,
`.cycle5-pre-A16`, `.cycle6-pre-A17`.

## Headline

**The penguin is real, and the reason nothing else worked is now a two-line bug
in a library — not a mystery.**

A16 was physically observed rendering the Nuxel first-light screen and the
animated penguin on the AMOLED panel. Forensics on the A16 ram console
(`captures/20261015T143625Z-A16-postfail/`, full write-up in `A16-POSTMORTEM.md`)
then established, with evidence:

1. **A16 never rebooted itself.** It booted once, ran 168 s, and was ended by the
   operator's Samsung hard-reset hook. `RESET_CAUSE=SEC_HARD_RESET_HOOK(operator)`.
   The animation *is* an intentional infinite loop; the mission's warning about
   mislabelling it a bootloop was correct.
2. **systemd 258 really runs** (PID 1, unit graph built, `basic.target` reached).
3. **Every service was marked failed while its process was already running.** The
   A13 `posix_spawn` fallback works; the very next statement,
   `pidref_set_pid()`, calls `pidfd_open()` (Linux **5.3**+), gets `ENOSYS` on this
   4.14 kernel, and returns `-ENOSYS` for a process it just started successfully.
   `udevd` then ran for 161 s while `systemd-udevd.service` was "failed".
4. **A second, independent blocker:** the cgroup2 mount was hidden by a later
   `mount -t sysfs sysfs /sys`, so in the final namespace `/sys/fs/cgroup` was an
   empty sysfs directory and no unit cgroup could be created.

Both are now fixed and **verified offline** (`SYSTEMD-COMPATIBILITY.md` §4):
against a stub that emulates a pidfd-less 4.14 kernel, the A17 library makes
`posix_spawn_wrapper()` return `rc=0` where the A13/A16 shim returns
`rc=-38 ENOSYS`. A17 also adds a live USB CDC-ACM diagnostic console
(`LIVE-DEBUG-CONNECTIVITY.md`) delivered by the BOOT partition alone.

## A17 — current state

```
CANDIDATE=A17
boot.img        51,193,856 B  sha256 911a72e9fbe7f8b591e36fc72bac2d296f7a53b4ff2f9992eedea98e9c6582c2
Image-A17       48,453,640 B  sha256 f9529cd739c6deb97025429a6f7dc79c21010fc79298ba708c011506ca37a745
initramfs.cpio   8,011,812 B  sha256 3e0ca12e8dccd134215a0964cf153054d7a6935ba54084bbdad00c780c5f0ea5
FLASHED to BOOT (/dev/block/sda14) with full SHA-256 readback VERIFIED
REBOOT_AT=2026-10-15T15:07:35Z
STATE=AWAITING_BOOT_RESULT
USERDATA / RECOVERY / DTBO: not written
```

A16 is preserved untouched at `debug-candidates/A16/` and two full BOOT backups
were taken from the device before writing (`backups/s10plus/20261015T145711Z-…`,
`scripts/nuxel-adb-flash-pack/backups/nuxel-adb/20261015T145717Z-…`).

## Milestones (evidence-backed; "hardware" = measured on the handset)

| Milestone | State |
|---|---|
| S-Boot executes Nuxel kernel | PROVEN |
| ARM64 kernel runs | PROVEN |
| Built-in initramfs executes | PROVEN |
| USERDATA discovered / Fedora ext4 mounts rw | PROVEN |
| Fedora systemd PID 1 executes | PROVEN |
| Nuxel renders on AMOLED | **PROVEN A16** |
| Animated penguin visible | **PROVEN A16 — USER OBSERVED** |
| A16 runtime stability | **PROVEN for the 168 s window** (no self-reboot; operator reset only) |
| Fedora service execution | **FIXED in A17, awaiting hardware confirmation** |
| cgroup v2 usable in the final namespace | **FIXED in A17, awaiting hardware confirmation** |
| Live USB diagnostics in Nuxel | **IMPLEMENTED in A17, awaiting hardware confirmation** |
| Animation hold supervision / handoff primitive | IMPLEMENTED (PID published, stage files) |
| DRM/KMS compositor backend | NOT AVAILABLE (`# CONFIG_DRM is not set`) |
| Phoc / Phosh / touchscreen / interactive UI | NOT PROVEN |

## Blockers, in order

1. **Confirm the A17 service fix on hardware** — does `systemd-udevd.service`,
   `systemd-journald.service`, `dbus-broker.service` reach `active`?
2. **Get the live console or the ram console out of the A17 boot.** No USB device
   enumerated on the MacBook after the A17 reboot, so either the gadget bind
   failed, the boot stalled before it, or the panel is showing something and the
   operator has not recovered yet.
3. **Then** the graphical backend decision (`PHONE-UI-HANDOFF.md`): fbdev-native
   transitional UI now, DRM/KMS porting in parallel. Phoc cannot start on this
   kernel as it stands.
4. Touchscreen/input enumeration, seat and permission model for phone services.

## Rules being kept

* RECOVERY is never written. EFS/SEC_EFS, PIT, bootloader, radio, Knox: untouched.
* USERDATA is only written with a stated reason (not in A17).
* A16 is never overwritten; every candidate is separately versioned.
* No milestone is claimed from file presence or from a userspace buffer write.
* Marker files are no longer accepted as proof of deployment (`A17-INIT-2`).

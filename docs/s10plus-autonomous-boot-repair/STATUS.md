# STATUS — cycle 13 / A26 (2026-10-15)

Previous snapshot: `STATUS.md` cycle 12 (A25), `NUXEL-BOOT-STALL.md`,
`A24-POSTMORTEM.md`. This cycle was executed entirely on the **running** phone.

## Headline

**The Fedora systemd boot graph is repaired, and it was repaired while the phone
was running. `systemctl is-system-running` is `running` for the first time —
previously `initializing`, forever.**

Three measured root causes, all `ENOSYS` on Samsung Linux 4.14.253:

1. **`systemd-userdbd` cannot start** (`Failed to watch child: Function not
   implemented` — systemd 258 dropped the `waitid()` child watcher and needs
   `pidfd_open`, Linux 5.3). Its varlink socket still exists, so **every**
   user/group lookup that reaches userdb **blocks forever**.
   `systemd-tmpfiles-setup-dev-early.service` (oneshot, `TimeoutStartUSec=infinity`,
   `Before=sysinit.target`) hung on the `audio` group lookup and pinned all 45
   other jobs in `waiting`. `/etc/nsswitch.conf`'s
   `group: files [SUCCESS=merge] systemd` made it worse: `getent group audio`
   took **forever** (rc=124) instead of 0.003 s.
2. **`dbus-broker-launch` dies in `launcher_fork`** (same ENOSYS), so `polkitd`
   (`Type=dbus`) could never acquire its name and `multi-user.target` never
   activated. Switched the system bus to Fedora's other implementation,
   `dbus-daemon` → `busctl --system list` returns real names.
3. **`systemd-udevd` cannot create worker objects** (same ENOSYS). With an event
   storm on the device tree it forked **17,723 processes in 50 s** and the board
   watchdog-reset once. Contained by masking udevd; devtmpfs supplies every node
   Nuxel needs (`/dev/fb0`, `/dev/input/event*`, `/dev/ttyGS0`).

All four changes are persisted in `tools/s10plus/a26/nuxel-rootfs-fixes.sh`, which
`images/s10plus/build-phone-rootfs-inside-fedora.sh` now runs against the rootfs
staging tree — no phone-only hotfix.

## Milestones

| Milestone | State |
|---|---|
| Nuxel kernel / Fedora rootfs / systemd PID 1 | PROVEN (unchanged) |
| systemd services execute, cgroup2, journald | PROVEN A18 (unchanged) |
| **Fedora boot graph completes (`is-system-running` = `running`)** | **PROVEN A26** |
| **Essential Fedora services: udevd(contained), journald, dbus, logind, user-sessions, sockets, all targets** | **PROVEN A26** |
| Original MP4 animation, ABGR_8888, 0 skips | PROVEN A21/A22/A23 |
| **Nuxel UI starts automatically as a normal unit; animation stops; panel owned** | **PROVEN A26** |
| **UI navigation via its own FIFO (home/settings/system/logs), `PAN_RC=0`** | **PROVEN A26** |
| **UI screenshot obtained and pulled with SHA-256 verification** | **PROVEN A26** |
| **Live console hardened (framing, IDs, timeout, Ctrl-C, hash-verified pull)** | **PROVEN A26** |
| **USB loss + re-enumeration survived, console returned** | **PROVEN A26** (accidental) |
| Touchscreen device present in a NORMAL boot, multitouch caps read | **PROVEN A26** |
| Physical touch events recorded / touch navigation | **NOT YET** (capture armed; needs a finger) |
| Seamless first light: MP4 frame 0 asset built + verified offline | **A26, asset only** — blit + BOOT candidate pending |
| Old two-second splash actually gone from a boot | NOT YET (needs the BOOT update) |
| DRM/KMS, Phoc/Phosh | NOT AVAILABLE (no DRM in-tree); path assessed in `PHOSH-ASSESSMENT.md` |

## Blockers, in order

1. **A finger on the glass** to close P4 (capture armed on `/dev/input/event2`).
2. **`nuxel-fb-phone.c` blit** for `NUXSPL01` (contract in
   `tools/s10plus/a26/build-a26-boot.sh`), then a controlled BOOT-only update.
3. The durable systemd fix: teach `sd-event`'s child watcher to fall back to
   `waitid()` — then `userdbd`, `dbus-broker` and `udevd` can all be un-masked.
4. The `asix`/`wl_cfg80211` uevent storm (now unconsumed, should still be stopped).

## Rules being kept

* RECOVERY untouched; EFS/SEC_EFS, PIT, bootloader, radio, DTBO untouched. No
  partition was written this cycle at all — every change was filesystem-level on
  the running system.
* No milestone claimed from a marker or a file's existence: every PROVEN line
  names a hardware observation.
* `/dev/fb0` is never opened by a diagnostic; the UI is driven only through
  `/run/nuxel-ui.cmd`.
* A screenshot alone is not proof of what the glass shows — said so explicitly.

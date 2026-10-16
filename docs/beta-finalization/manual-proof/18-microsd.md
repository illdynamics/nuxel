# Manual area 18 — microSD (S10+ / beyond2lte)

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED for detection,
mount and eject logic). Owner action required? **Yes** — a card must be inserted
and removed by hand, and the *tray* configuration of the actual unit must be
checked.

**Device truth used by this document.** Samsung Galaxy S10+ (SM-G975F). The
hybrid tray holds a nano-SIM and (on the trays that support it) a microSD card.
**Internal storage is UFS 2.1 and appears as `/dev/mmcblk0*`; the microSD is the
external card (`/dev/mmcblk1*`).** No Nuxel path treats `mmcblk0` as a card:
`nuxel-microsd-diag.sh` refuses any `/dev/mmcblk0*` and any `/dev/block/*`
target outright. **Media is never formatted and existing data is never
modified**; the default mount is **read-only**.

---

## 1. Feature

`configs/nuxel/modem/microsd.json` + `tools/s10plus/a33/nuxel-microsd-diag.sh`:

* **insertion/removal detection** from the mmc host + the removable flag +
  an external block device, with the *external* device identified (never the
  internal one);
* **filesystem metadata** read (unknown stays unknown — the tool refuses to
  guess);
* **safe mounting** — read-only by default, `nodev,nosuid,noexec,noatime`, and
  `uid=1000,gid=1000,umask=0022` for vfat/exfat; read-write only with an
  explicit `--rw --yes` and only for filesystems the policy marks `rw_allowed`;
* **auto-mount on INSERT** — `configs/nuxel/modem/90-nuxel-microsd.rules` +
  `configs/nuxel/modem/nuxel-microsd-automount.service` +
  `nuxel-microsd-diag.sh automount`. It is read-only, external-card-only,
  idempotent, refuses an unknown filesystem, and **deliberately skips the boot
  window** (uptime < `automount.boot_grace_s`, 120 s), because the kernel replays
  the same "add" uevent for a card that was already seated — so a card present at
  boot is never auto-mounted (`diagnostics.auto_mount_on_boot` is false). The
  owner can switch it off entirely with `automount-off`;
* **eject / unmount** with `sync`, a busy check and a refusal to force;
* hard invariants: `never_format`, `never_partition`,
  `never_write_to_internal`, unknown filesystems `REFUSE`, and no
  `mkfs`/`fdisk`/`parted`/`wipefs`/`dd` invocation anywhere.

## 2. Why this matters

The single most destructive thing a phone OS can do to a user is format or wipe
their card. On this device there is an extra trap: the internal UFS storage is
also an mmc device (`mmcblk0`), so a careless "mount the first mmcblk device"
tool would target internal storage. The policy and the tool make both mistakes
impossible — the internal device is refused by name and the card is mounted
read-only unless the owner explicitly asks otherwise — and the mission's "never
automatically format media / preserve existing data" rule is enforced in code,
not in a comment.

## 3. Preparation

1. Handset booted into Nuxel, screen on, **not** in charger-mode
   (`nuxel-power-diag.sh status`).
2. Console/SSH or the on-device terminal.
3. A microSD card with data you can afford to *read* (never a card you cannot
   risk — the tool is read-only, but a healthy backup is still good practice),
   and a way to verify the card's contents from another machine.
4. Check what the device exposes before touching the tray:

   ```sh
   nuxel-microsd-diag.sh status          # controller, internal, external, verdict
   nuxel-microsd-diag.sh status --json   # machine-readable
   nuxel-microsd-diag.sh cards           # hosts + internal/external + supported fs
   ```

   `INTERNAL_ONLY` is a real verdict: it means the controller exists and only
   internal storage is present — **insert a card**, do not retry the command.
   `NO_CARD_CONTROLLER` means the kernel exposes no mmc host at all
   (`BLOCKED_KERNEL`): record it, it does not gate other areas.

## 4. Exact action

1. **Verify the tray:** power off, use the SIM tool to pull the hybrid tray, and
   confirm whether your unit's tray has a microSD position at all. If it does
   not, record `NOT_SUPPORTED_ON_DEVICE` for this unit and stop.
2. **Insert:** put the microSD into the tray (correct orientation) and seat the
   tray. Power on.
3. **Detect:** `nuxel-microsd-diag.sh status` — the verdict should move from
   `NO_CARD`/`INTERNAL_ONLY` to `CARD_PRESENT_UNMOUNTED`, and the **external**
   device (`/dev/mmcblk1…`) must be the one listed under `external devices`,
   while `internal (mmcblk0)` must stay untouched.
4. **Mount read-only:** with the auto-mount switch on
   (`nuxel-microsd-diag.sh automount-status`), a card inserted *after* the boot
   window is mounted read-only automatically by the udev rule + service; the
   verdict must become `MOUNTED_RO` with no command from you. Confirm the
   service ran: `journalctl -u nuxel-microsd-automount -n 20` and
   `grep -i 'automount' /var/log/nuxel/microsd-diag.log`.
   To mount by hand instead: `nuxel-microsd-diag.sh mount /dev/mmcblk1`
   (add `--fstype <type>` if `status` reports `filesystem: unknown`). Confirm
   the mount point under `/run/media/nuxel/` and check the verdict becomes
   `MOUNTED_RO`.
   * **Boot-window check (important):** re-seat the card *during* the first
     120 s after boot; `nuxel-microsd-diag.sh automount` must print
     `SKIPPED - this is the boot window` and mount nothing. This is the
     documented behaviour, not a fault.
   * **Switch-off check:** `nuxel-microsd-diag.sh automount-off`, re-insert the
     card, and confirm nothing mounts; `automount-on` restores it.
5. **Preserve the data:** `ls -la /run/media/nuxel/<name>` and compare the file
   listing (and a checksum of one file) with the other machine that wrote the
   card. **Nothing may change.**
6. **Write check (optional, explicit):** only if you intend to use the card for
   storage, mount read-write with `--rw --yes`, copy one small test file, and
   confirm it appears. Then unmount.
7. **Eject:** `nuxel-microsd-diag.sh eject /dev/mmcblk1` — it must unmount,
   `sync`, and print "safe to remove". Then pull the card.
8. **Removal detection:** with the card removed, `status` must report `NO_CARD`
   (or `INTERNAL_ONLY`), and no dangling mount point may remain.
9. **Format-safety check:** confirm the tool contains no format path:
   `grep -nE 'mkfs|fdisk|parted|wipefs|dd if=' tools/s10plus/a33/nuxel-microsd-diag.sh`
   must find nothing.
10. **Internal-storage safety check:**
    `nuxel-microsd-diag.sh mount /dev/mmcblk0p1` must refuse with
    "INTERNAL UFS storage".

## 5. Expected result

* `status` reports the controller, the internal device (marked never-a-target),
  the external device, the removable flag, the filesystem (or `unknown`), and a
  verdict from `NO_CARD_CONTROLLER` / `NO_CARD` / `INTERNAL_ONLY` /
  `CARD_PRESENT_UNMOUNTED` / `MOUNTED_RO` / `MOUNTED_RW`.
* The card mounts read-only by default with the hardening options.
* Every file that was on the card is still there, byte-identical.
* `eject` leaves no mount and prints "safe to remove"; removal is detected.
* `mount /dev/mmcblk0p1` and any `/dev/block/*` target are refused.
* A card inserted after boot is auto-mounted **read-only** by the udev rule +
  `nuxel-microsd-automount.service`; a card seated during the boot window is
  **not** (the service reports the skip), and `automount-off` disables the whole
  path.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning |
|---|---|
| `NO_CARD_CONTROLLER` | No mmc host at all → `BLOCKED_KERNEL`; offline driver/DT work, not a retry loop. |
| `INTERNAL_ONLY` after inserting a card | The card is not detected: check the tray seating and whether your unit's tray has a microSD position. Capture `ls -l /dev/mmcblk*`, `ls /sys/class/mmc_host/` and `dmesg \| grep -i mmc`. |
| `filesystem: unknown` and mount refuses | Expected: the tool never guesses. Re-run with an explicit `--fstype` (and `--yes`) only if you know the type. |
| Mount fails with an error about the filesystem | The card may need an fsck. **Do not format.** Report the exact error; a read-only check can be arranged separately. |
| Files differ after the read-only mount | Defect: report immediately, the card must not be written by a read-only mount. |
| `unmount`/`eject` says busy | A process still uses the mount. Close it and retry; the tool never forces an unmount. |
| Mount point still present with the card removed | Defect: report it, removal detection must clear the state. |
| The internal device is ever mounted or written | Critical defect: report it; `mmcblk0` must be refused by name. |
| Card appears reformatted or empty | Critical defect: report it with the tool's output; nothing in this subsystem may format or wipe media. |
| Card inserted after boot is not auto-mounted | Check `nuxel-microsd-diag.sh automount-status` (owner switch, boot window) and `journalctl -u nuxel-microsd-automount -n 40`. The most common benign cause is a card seated during the boot window (by design) or a switch turned off by the owner. |
| Card mounts READ-WRITE by itself | Critical defect: auto-mount is read-only-only. Capture `cat /proc/mounts` and the service journal; do not "just remount". |

## 7. Diagnostic command / log path

* `nuxel-microsd-diag.sh status [--json] | cards | mount <dev> [--rw --yes] [--fstype T] | unmount <dev>|--all | eject <dev> | automount | automount-on|off|status | report`
  (`tools/s10plus/a33/nuxel-microsd-diag.sh`)
* Auto-mount: `journalctl -u nuxel-microsd-automount -n 40`;
  owner switch `/var/lib/nuxel/microsd/automount`;
  udev rule `/etc/udev/rules.d/90-nuxel-microsd.rules`.
* Evidence log: `/var/log/nuxel/microsd-diag.log`
* Kernel side: `ls -l /dev/mmcblk*`, `ls /sys/class/mmc_host/`,
  `cat /sys/block/mmcblk1/removable`, `cat /proc/mounts`, `dmesg | grep -i mmc`
* Offline suite: `python3 tools/s10plus/a33/tests/hw-subsystems/test-microsd-diag.py`
  and `nuxel-microsd-diag.sh selftest` (6 fixtures: no controller / internal-only
  / card present-unmounted / mounted read-only / past the boot window / inside
  the boot window).

## 8. PASS / FAIL

* **PASS** — the card is detected as the *external* device, mounts read-only,
  every pre-existing file is still present and unchanged, `eject` leaves no
  mount and reports safe-to-remove, removal is detected, both safety refusals
  (internal device, unknown filesystem) work, and the auto-mount behaves exactly
  as the contract says (read-only, insert-only, skipped in the boot window,
  silenced by the owner switch). Record the device path, the
  filesystem type, the mount point and the file/checksum comparison.
* **FAIL** — any of: a card that is not detected, a mount that refuses for an
  unexplained reason, a difference in the card's contents, a busy unmount that
  was forced, a dangling mount, or any path that formats, partitions or writes
  internal storage. Record the verdict, the device paths, the mount options and
  the exact output — that is what a repair cycle needs.

## Current automatic evidence (repository, this build group)

* `bash tools/s10plus/a33/nuxel-microsd-diag.sh selftest` → 6/6 fixtures PASS
  (`fixtures/microsd-absent`, `microsd-internal-only`, `microsd-present`,
  `microsd-mounted`, `microsd-ready`, `microsd-boot-window`).
* `python3 tools/s10plus/a33/tests/hw-subsystems/test-microsd-diag.py` → all
  checks PASS (state chain, internal-storage refusal, `/dev/block` refusal,
  unknown-filesystem refusal, rw-needs-`--yes`, policy read-only for ntfs3,
  auto-mount boot-window skip / idempotency / switch-off / read-only plan,
  udev+service invariants,
  no format/partition tooling, fragment completeness).
* A physically inserted card: **not claimed** — every `status --json` emits
  `"card_data_written": false` and `"auto_format": false`, and the capability
  keeps this at `NEEDS_OWNER_TEST`.

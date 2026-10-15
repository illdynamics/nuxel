# NEXT-ACTION — cycle 7, candidate A17 (2026-10-15)

## State

`STATE=AWAITING_BOOT_RESULT`
`FLASHED=2026-10-15T15:07:35Z` (BOOT only, readback-verified sha256 `911a72e9…`)
`PERMANENT AGREEMENT: if the operator has returned the phone to TWRP, this attempt
FAILED — capture the new evidence and continue. No further confirmation is
needed.`

## 1. Read the A17 result

**Preferred (new):** if the Mac shows `/dev/cu.usbmodem*`, the live console is up:

```sh
ls /dev/cu.usbmodem*
screen /dev/cu.usbmodemXXXX 115200
```
Then, on the phone: `systemctl is-system-running`, `systemctl --failed`,
`journalctl -b -p err | tail -50`, `cat /var/lib/nuxel/boot-stage`.

A monitor is already running and logging to
`scripts/s10plus-debug-pack/captures/20261015T150726Z-A17-live-run/`
(`usb-console.log`, `usb-watch.log`).

**Fallback (TWRP):** read `/proc/last_kmsg` and `<rootfs>/nuxel-boot-diag.log`,
and look for, in order:

1. `SYSTEMD_LIB_VERIFIED_PRESENT` or `SYSTEMD_LIB_INSTALLED_VERIFIED` (+ the
   `NUXEL-VERIFY sha256 … machine=183` lines that prove it).
2. `CGROUP2_MOUNT_OK` then `CGROUP2_VERIFIED controllers='…'` with a non-empty
   list, and `CGROUP2_PROC_MOUNTS '… cgroup2 …'`.
3. `LIVE_CONSOLE_STARTED` and the `nuxel-console: …` lines (UDC name, bind result,
   `ttyGS0 ready`, shell pid).
4. `BOOT_STAGE_SYSTEM_STARTING`, `ANIMATION_HOLD_PID=<pid>`.
5. **count of `Failed to spawn executor`** — must be 0.
6. `Started systemd-udevd.service`, `Started dbus-broker.service`,
   `Started systemd-journald.service`, `Started systemd-logind.service`.
7. any `kernel BUG` / `sec_reboot` / `hard_reset_hook` (operator reset only).

## 2. Decision table

| Observation | Conclusion | Next step (A18) |
|---|---|---|
| Penguins + 0 spawn failures + udevd/dbus/journald active + USB console alive | **Fedora service execution PROVEN** | move to the phone-UI phase: fbdev-native UI (Path B) + input enumeration |
| 0 spawn failures but services still fail at CGROUP | cgroup fix incomplete | inspect `/proc/self/cgroup`, `cgroup.subtree_control`, `cgroup.kill` live from the console; check `cgroup_no_v1` need on 4.14 |
| `Failed to spawn executor` still present | third spawn-path incompatibility | from the live shell, run `strace -f` on a `systemctl start` of a trivial unit and/or `sd-executor --deserialize` by hand |
| No USB device, `LIVE_CONSOLE_STARTED` present, `BIND FAILED` logged | UDC not in device mode | A18: bind the gadget immediately after the devtmpfs mount; try `CONFIG_USB_CONFIGFS_RNDIS` (kernel has it) or nudge the role switch |
| No `LIVE_CONSOLE_STARTED`, boot ends before it | boot regressed earlier | compare against A16 milestone list; the last `nuxel-init:` line names the stage |
| Penguins, no reset, services work, but no UI | expected intermediate state | implement the fbdev-native Nuxel phone UI (Path B, PHONE-UI-HANDOFF.md §3) |

## 3. Standing constraints

* Never overwrite RECOVERY. Never touch EFS/SEC_EFS, PIT, bootloader, radio, Knox.
* A16 stays at `debug-candidates/A16/`, untouched, as the display regression test.
* Prefer BOOT-only updates; a USERDATA write needs a stated reason and a
  versioned image + ext4 integrity check.
* No milestone from file presence and none from a userspace buffer write.

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

## 2b. MANDATORY procedure change for the next hardware test

`sec_bat_is_lpm_check: Low power charging mode: 1` was present in the A16 Nuxel
boot (its own log line at t = 0), and `lpcharge == 1` makes `sec_ts_init()`
return `-ENODEV` — no touchscreen, no fingerprint, no wacom. Reboots issued from
TWRP **while the USB cable is attached** appear to be what produced it.

For A18 and any input-sensitive candidate:

1. from TWRP, `adb reboot` **with the USB cable detached** (or power on by keys
   with no cable),
2. confirm `Low power charging mode: 0` and the **absence** of
   `sec_ts_init: Do not load driver due to : lpm 1`,
3. attach USB **after** the boot to give the dwc3 role switch a chance to bring
   up device mode, so the A17 `nuxel-console` channel can bind.

Never record `TOUCHSCREEN=FAILED` from an LPM boot.

## 3. Standing constraints

* Never overwrite RECOVERY. Never touch EFS/SEC_EFS, PIT, bootloader, radio, Knox.
* A16 stays at `debug-candidates/A16/`, untouched, as the display regression test.
* Prefer BOOT-only updates; a USERDATA write needs a stated reason and a
  versioned image + ext4 integrity check.
* No milestone from file presence and none from a userspace buffer write.

## 4. A18 is one build away (prepared, not built)

Ready and unrun, awaiting a focused hypothesis from the A17 result:

* `tools/s10plus/a17/build-a18-initramfs.sh` — parameterised initramfs builder
  (default base = the A17 archive that is on the BOOT partition now) that also
  inserts the new probe.
* `build/out/s10plus/debug-candidates/A18/nuxel-hwprobe`
  (625,496 B, sha256 `bff976529790f4bb3207a6ecc53ca5384df6129eb6ac5f78ca355773571dbbff`)
  — one command that dumps identity + boot mode, `/dev/fb*` geometry, DRM
  presence/absence, the **full input inventory with capability bitmaps** (is
  there a `sec_touchscreen` with multitouch ABS?), cgroup v2 state, PID 1/systemd
  state and the power supplies. It prints absence as loudly as presence, and it
  is safe to run from the live console or from `init.sh`.
  Source: `tools/s10plus/nuxel-hwprobe.c`.

Candidate change sets to choose between, once A17's evidence is in:

| If A17 shows | A18 = |
|---|---|
| services active, console up | A17 + `nuxel-hwprobe` run from init + begin the fbdev-native UI (Path B) |
| services fixed, console not bound | A17 + bind the gadget immediately after the devtmpfs mount + `nuxel-hwprobe` |
| `Failed to spawn executor` still present | A17 + a strace of one `systemctl start` captured over the console; do not guess |
| `CGROUP2_VERIFY_FAILED` | A17 + live inspection of `/proc/self/cgroup`, `cgroup.subtree_control` and the `cgroup_no_v1` question for 4.14 |

---

# CYCLE 7b — NEXT-ACTION for A18 (2026-10-15)

`STATE=AWAITING_BOOT_RESULT` for A18 (`REBOOT_AT=2026-10-15T15:33:59Z`).
**The Nuxel USB gadget enumerated on the MacBook** (`Nuxel S10+ Live Console`,
0x18d1/0x4ee7, `/dev/cu.usbmodem201`) — but carried 0 bytes. So the live channel is
half-proven and the decisive evidence still needs one TWRP round trip.

## Read, in this order, as soon as TWRP is back

1. `adb shell cat /proc/last_kmsg` → the A18 Nuxel session. Look for:
   * `CMDLINE_PARTS n bytes=… samsung=yes` (the full cmdline is now recoverable);
   * `dispatch: DEVICE='s10plus'` followed by **`s10plus: waiting for /dev/sda31`**
     and `s10plus: USERDATA via documented /dev/sda31 … after Ns`;
   * `ROOTFS_HANDOFF_STARTED`, `switching root`;
   * `systemd[1]: systemd 258.11-1.fc43 running in system mode`;
   * **count of `Failed to spawn executor`** — the whole point of A17/A18;
   * `Started systemd-udevd.service` / `Started systemd-journald.service` /
     `Started dbus-broker.service`;
   * `CGROUP2_MOUNT_OK` + `CGROUP2_VERIFIED controllers='…'`;
   * `nuxel-console: …` — `ttyGS0 ready` vs `waiting for /dev/ttyGS0 (N s …)` vs
     `NEVER APPEARED after 60 s`, and `shell tty fd=…`;
   * `SYSTEMD_LIB_INSTALLED_VERIFIED` or `SYSTEMD_LIB_VERIFIED_PRESENT`.
   Use `scripts/s10plus-debug-pack/scripts/20-triage-nuxel-boot.py`.
2. Mount USERDATA read-only and read, in the rootfs:
   * `/var/log/nuxel-bootreport.txt` — the **persistent report** (systemd verdict,
     failed units, running services, `journalctl -b -p warning`, spawn-failure
     count, cgroup state, boot-stage files). This is the answer even if the console
     never works.
   * `/var/lib/nuxel/{boot-stage,animation,fb-hold.pid}`.
   * `usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so` hash — must be
     `848149cf…` (A17 library) if the verified deployment ran.
3. Record `BOOT_RESULT`, `RECOVERY_ACCESS=RESTORED`, and update
   `FLASH-ATTEMPTS.md` / `TEST-RESULTS.md` / `STATUS.md`.

## Decision table

| Observation | Conclusion | Next (A19) |
|---|---|---|
| `Failed to spawn executor` = 0 and udevd/journald/dbus `active` | **the Linux 4.14 service blocker is SOLVED** | move to the phone-UI phase; keep the console work as a side task |
| services still fail, ram console names the reason | new, specific blocker | fix that one thing; do not guess |
| `ttyGS0 NEVER APPEARED` / `waiting for /dev/ttyGS0` | console device-side attach failed | A19's console build (already prepared) waits 60 s with per-second logging, opens without `O_CLOEXEC`, has the shell open its own handle, and emits a 10 s heartbeat so a silent link is self-evident |
| `ttyGS0 ready` + `shell tty fd=…` yet 0 bytes on the host | gadget→host data path issue | investigate `f_acm` line-state/notify behaviour; try the `RNDIS`/`NCM` function (kernel has both) as an alternative channel |
| root resolution failed again | the fix is incomplete | the chunked `CMDLINE_PART` lines give the exact cmdline for the first time |

## Prepared and unrun

* `tools/s10plus/a19/nuxel-console.c` + `build/out/s10plus/debug-candidates/A19/nuxel-console`
  — A19 console build (60 s tty wait with per-second klog, no `O_CLOEXEC`, own
  handle in the shell, 10 s heartbeat).
* `tools/s10plus/a17/build-a18-initramfs.sh` — parameterised initramfs builder.

---

# CYCLE 7c — NEXT-ACTION for A19 (2026-10-15)

`STATE=AWAITING_BOOT_RESULT` · `REBOOT_AT=2026-10-15T15:50:39Z` ·
boot.img `7a24c04a101b93dd7b3df45472f395f85b10d236a2e6a4212b05c2cbee3c1f1b`
The gadget enumerated (`/dev/cu.usbmodem201`, `Nuxel S10+ Live Console`) but the
console carried 0 bytes, so the A19 mknod path is unconfirmed.

## The single question to answer from the ram console

`nuxel-console:` lines decide between exactly three states:

| Ram-console line | Meaning | A20 action |
|---|---|---|
| `created /dev/ttyGS0 from /sys/class/tty/ttyGS0/dev (M:N)` | the node fix worked | then the shell/keeper did not attach or the link is one-way → test `RNDIS`/`NCM` (`CONFIG_USB_CONFIGFS_RNDIS=y`, `_NCM=y`) as an alternative channel |
| `waiting for /dev/ttyGS0 / /sys/class/tty/ttyGS0/dev (N s)` | the sysfs tty entry never appeared | the ACM function instance was not created → log/verify the `mkdir functions/acm.usb0` + symlink result (currently unchecked) |
| `/dev/ttyGS0 never became available` | same as above, after 30 s | as above |

Everything else about A19 is a re-run of A18's proven behaviour, so also confirm:

* `Failed to spawn executor` = 0, `Failed at step CGROUP` = 0, no `Failed with result`;
* `is-system-running` and `systemctl --failed` from
  `<userdata>/var/log/nuxel-bootreport.txt` — **A18 left the boot with journald
  active; the natural A19 goal is `systemctl --failed` empty with more services up**;
* `ANIMATION_HOLD_PID=<pid>` (A19 resolves it via `/proc` because toybox leaves
  `$!` empty) and `/var/lib/nuxel/fb-hold.pid` non-empty.

## Standing priorities after that

1. **Keep the service milestone.** A18 proved service execution; do not regress it.
2. **Give the operator a reason to wait.** The A18 boot was force-reset ~14 s after
   `switch_root`, before the unit graph completed. The penguin is still the only
   visible feedback; the next visible step is a progress indicator driven by
   `/var/lib/nuxel/boot-stage` (PHONE-UI-HANDOFF.md).
3. **Phase 6 input**: `sec_ts` loads on a non-LPM boot but
   `sec_ts_input_open: Failed to start device` repeats (`already power on`,
   SSP `ssp_down == true`) — the TSP opens but will not start. Investigate
   `/sys/class/sec/tsp/*` and the SSP state before promising touch.
4. **Display backend**: no DRM on this kernel, so the fbdev-native UI (Path B) is
   the only short-term route to an interactive Nuxel screen.

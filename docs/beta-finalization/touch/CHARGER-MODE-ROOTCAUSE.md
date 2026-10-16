# Charger-mode / lpcharge boot: root cause, mitigation and the not-deployed kernel fix

**Area 1 (touch), sub-item: "the charger-mode/lpcharge boot-mode finding".**

| Item | Verdict |
|---|---|
| Root cause identified (source-level) | **YES** — `sec_bat_is_lpm_check()` → `lpcharge=1` → `sec_ts_init()` returns `-ENODEV` |
| Root cause **re-measured live on the phone this cycle** | **YES** — see §1a: the handset is in charger/LPM mode right now and no touch device exists on this boot |
| Userspace mitigation (state + gated normal reboot) | **OFFLINE_TESTED**; live effect requires a normal reboot (**DEPLOYED_UNVERIFIED** until then) |
| Permanent fix (kernel/early-boot) | **BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED** |
| Finger test after the normal reboot | **NEEDS_OWNER_TEST** |

Tooling: `tools/s10plus/a33/nuxel-bootmode-guard.py`,
`configs/nuxel/bootmode/` (the guard's **own configuration subpath**; the legacy
`configs/nuxel/touch/` copy is retained for the already-generated deploy plan, and the
test asserts the two agree on every gate field),
tests `tools/s10plus/a33/tests/test-bootmode-guard.py`,
offline patch `tools/s10plus/a33/kernel-patches/sec_ts-lpm-initcall-deferred-bind.patch`.

---

## 1. The finding, with its evidence

Measured on the handset in the A16/A29b/A32 cycles and re-quoted here unchanged
(originals: `docs/s10plus-autonomous-boot-repair/DEVICE-OBSERVATIONS.md`,
`…/BETA-HARDWARE-FINALIZER/00-BASELINE.md` and `01-TOUCHSCREEN-ROOT-CAUSE.md`):

```
/proc/cmdline        androidboot.mode=charger   charging_mode=0x3030
dmesg  t=0.000       sec_bat_is_lpm_check: Low power charging mode: 1
dmesg  t=1.674       [sec_input] sec_ts_init: Do not load driver due to : lpm 1
dmesg  t=2.257       tsp_io: disabling        /  tsp_avdd: disabling
/proc/bus/input/devices   no sec_touchscreen at all
/sys/class/sec/tsp/       absent
/proc/interrupts          no sec_ts line
```

The condition is not a partial failure: **there is no touch device on that boot**.
Everything the touch pipeline above layer 1 reports is therefore empty by
construction — which is why cycles that measured "no touch" from a charger-mode
boot were measuring the bootloader's power state, not the driver.

## 1a. The condition re-measured live, this cycle (read-only console probe)

A bounded, **read-only** probe was run against the running phone over the USB CDC-ACM
live console (`scripts/s10plus-debug-pack/nuxel-live.sh`: exclusive flock, per-command
request ids, target-side SHA-256 of the payload verified after decoding, `--timeout 60`
per command). Nothing was written on the device: no partition, no bootloader, no DTB, no
modem, no EFS; no reboot; no arming of any input node; no `/dev/fb0` open. Raw transcript
and its grading:

`docs/beta-finalization/live/evidence/touch-20261016T193756+0200-cycl001-p0probe-live-run/`

| Probe (as run on the device) | Result |
|---|---|
| `tr ' ' '\n' < /proc/cmdline \| grep -E 'androidboot.mode\|lpcharge\|charging_mode'` | `charging_mode=0x3030`, `androidboot.mode=charger` |
| `dmesg \| grep -i -E 'sec_ts_init\|Low power charging'` | `[    1.638064] [sec_input] sec_ts_init: Do not load driver due to : lpm 1` |
| `grep -c sec_touchscreen /proc/bus/input/devices` | `0` (rc=1) |
| `ls -d /sys/class/sec/tsp` | `No such file or directory` |
| `grep -i -E 'sec_ts\|4-0048' /proc/interrupts` | no match |
| `ls /sys/class/input` | seven `event<N>` entries and seven `input<N>` entries, none of them the panel |
| `systemctl is-active nuxel-wayland nuxel-touch-arm seatd` | `active` / **`failed`** / `active` |
| `pgrep -af phoc` | `/usr/sbin/phoc --no-xwayland -C /etc/nuxel/phoc-phone.ini …` (running) |
| `tail -4 /run/nuxel-libinput-path.state` | `PATH_ASSIGN_SEAT seat='seat0' direct_devices_seen=0 added=0 db_seeded=0` |
| `cat /sys/class/graphics/fb0/modes` (+ `virtual_size`, `bits_per_pixel`) | `U:1440x3040p-0` / `1440,6080` / `32` |

That is the root cause measured end to end on the actual unit. It also establishes two
things that are easy to assume and hard to prove:

* **the compositor survives the missing device** — the shim logged
  `direct_devices_seen=0 added=0` and `phoc` stayed up, so a charger-mode boot does not
  turn into a display failure;
* **`nuxel-touch-arm.service` is `failed`** on this boot, exactly as an absent driver
  predicts — which is why cycles that read "no touch" from a charger-mode boot were
  measuring the bootloader's power state, not the driver.

Graded with the same rules as any capture:

```
FIRST_FAIL_LAYER=1 NAME=driver STATE=blocked
VERDICT=PIPELINE_STOPPED_AT_LAYER=1
GATE=fail   (layers 2..7: blocked, never ok)
```

**Action required on the device: unplug the charger and reboot normally** before any
touch measurement is attempted. Until that happens no touch claim of any kind is
possible on this unit.

## 2. Why the boot is in that mode

S-Boot chooses low-power charging (LPM) when the board powers up **from off with a
charger present**. It passes the mode on the kernel command line, and the vendor
kernel caches it once, in an `__setup` hook:

```c
/* drivers/samsung/misc/sec_batt.c */
static int sec_bat_is_lpm_check(char *str) {
        if (strncmp(str, "charger", 7) == 0) lpcharge = 1;
        pr_info("%s: Low power charging mode: %d\n", __func__, lpcharge);
        return lpcharge;
}
__setup("androidboot.mode=", sec_bat_is_lpm_check);
```

```c
/* drivers/input/touchscreen/sec_ts/y771/sec_ts.c — initcall */
if (lpcharge == 1) {
        pr_err("%s %s: Do not load driver due to : lpm %d\n", SECLOG, __func__, lpcharge);
        return -ENODEV;                 /* before i2c_add_driver() */
}
```

The same gate exists in the fingerprint (`qbt2000`) and the Wacom digitizer
drivers. In LPM the display is not being driven either, so there is no interactive
session for a working touchscreen to serve — the correct thing for the device to
do is to come up in **normal mode**.

## 3. Why userspace cannot repair the driver on that boot

* `CONFIG_TOUCHSCREEN_SEC_TS_Y771=y` — the driver is built in, and
  `/lib/modules/4.14.253` does not exist, so it cannot be re-loaded.
* `CONFIG_KEXEC is not set` — the kernel cannot be re-entered with a new command
  line.
* `sec_ts_init()`'s decision is taken **before** `i2c_add_driver()`. The
  `sec_ts_start_device()` "already POWER_ON" short-circuit that the A29 helper works
  around is never even reached, because the driver owns no device and no IRQ.
* `/sys/class/sec/tsp/**` (what `nuxel-touch-arm` drives) does not exist in this
  state, which is why that unit exited 2 and the failure was misread as a driver
  problem.

Poking regulators, blanking the panel, retrying the helper or re-running any
userspace step cannot create the device. Any claim to the contrary would be
fabricated.

## 4. The mitigation that works without flashing: one normal reboot

A Linux-initiated **normal** reboot does not re-enter charger mode, even with the
cable attached (measured A29b):

```
before:  androidboot.mode=charger          no sec_touchscreen
after `systemctl reboot`:
         androidboot.mode is ABSENT        input: sec_touchscreen as /devices/platform/104b0000.hsi2c/i2c-4/4-0048/input/input2
         /proc/interrupts: 431: … sec_ts   /sys/class/sec/tsp/ present
```

`nuxel-bootmode-guard.py` implements this **as a gated action, never a blind one**:

**(a) It publishes the state** (so nothing downstream has to guess):

| File | Contents |
|---|---|
| `/run/nuxel-bootmode.state` | `BOOTMODE=CHARGER_LPM|NORMAL|UNKNOWN`, `TOUCH_DRIVER_EXPECTED`, `SEC_TOUCHSCREEN_REGISTERED`, `LPCHARGE`, `PERMANENT_FIX=BLOCKED_KERNEL BOOT_UPDATE_REQUIRED NOT_DEPLOYED`, one `EVIDENCE_n=<why> [<file>]: <line>` per marker |
| `/run/nuxel-bootmode.json` | launcher-facing: `headline`, owner-readable `message` ("charging-mode boot: touch is disabled on this boot. Unplug the charger and reboot normally …"), `action: unplug-and-normal-reboot`, `permanent_fix`, `graded` |

`mode == "unknown"` (no readable evidence) is **never** presented as a pass: it is
`graded: false`, and the tool exits 2.

The status output also names the configuration file that won (`CONFIG=…`), the
launcher/Settings state file (`SETTINGS_STATE=/run/nuxel-bootmode.json`) and one
machine-readable line for the live console:

```
NX_STATUS bootmode=charger-lpm touch_available=false permanent_fix="BLOCKED_KERNEL BOOT_UPDATE_REQUIRED NOT_DEPLOYED"
```

`TOUCH_AVAILABLE` is tri-state (`true` / `false` / `unknown`): an unclassifiable boot is
reported `unknown`, never as available — matching the launcher JSON, where
`touch_available` is true only for a normal boot.

The guard cannot be the reason a boot fails: the unit accepts exit codes 0/2/10–13.

**(b) It can request one normal reboot, behind five independent gates.** The
reboot decision is a pure function, so every branch is unit-tested:

| Gate | Refusal |
|---|---|
| explicit request | nothing happens without `--reboot` |
| acknowledgement | `--reboot` does nothing without `--i-understand-this-reboots-the-phone` |
| config | `"allow_reboot": false` by default (`configs/nuxel/touch/bootmode-guard.json`) |
| owner-test locks | any of `/run/nuxel-touch-capture.lock`, `/run/nuxel-owner-test.lock`, `/run/nuxel-manual-proof.lock`, `/var/lib/nuxel/owner-test.lock` suppresses it |
| cooldown + uptime | a 900 s cooldown and a 120 s uptime floor, so a boot cannot become a reboot loop |
| power safety | refused unless a charger is connected **and** the battery reports charging; an unreadable power supply counts as *unknown* (refuse, not permit) |

The command is always `systemctl reboot` (userspace, systemd PID 1). There is no
path in this tool that writes a partition, a bootloader, a DTB, a modem, an EFS or
a partition table, and `--print-only` (plus fixture mode, which refuses to execute)
exercises the whole decision without rebooting anything.

The optional unit `configs/nuxel/touch/nuxel-bootmode-reboot.service` ships
**disabled**: enabling the automatic path takes both a config edit **and** an
explicit unit enable — deliberately two independent decisions.

## 5. The permanent fix is a kernel change, and it is NOT deployed

`tools/s10plus/a33/kernel-patches/sec_ts-lpm-initcall-deferred-bind.patch` is an
offline proposal: bind the device but keep sensing off while `lpcharge` is set, then
poll for LPM to clear and run the existing start path. That would make an LPM
power-up interactive without a reboot (useful for an always-on kiosk), but it is a
kernel/DTB change and therefore:

* **not compiled, not flashed, not loaded, not applied** to the phone;
* marked `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED` in the state file, the launcher
  JSON, the test expectations and this document;
* accompanied by a documented **future** procedure that is explicitly
  **not executed** in this beta:

  1. apply the patch to the vendor 4.14.253 tree in a clean branch, keeping the
     original `__setup` result reachable;
  2. build the arm64 `Image` (with the embedded Nuxel initramfs) and the merged DTB
     with the A25/A26 toolchain; SHA-256 every artifact;
  3. pass the offline gates (valid arm64 Image, DTB merges with `fdtoverlay`,
     initramfs contains the nuxel init) — all verifiable without the phone;
  4. only under explicit owner authorisation, a **BOOT-partition-only** write with a
     full-partition readback, recorded as `DEPLOYED_UNVERIFIED` until a normal boot
     proves the driver binds;
  5. rollback = restore the previously verified BOOT image from its retained
     SHA-256. No other partition is touched.

This repository has not performed steps 2–5 and must not claim it has.

## 6. What the owner sees, and what to do

```
$ nuxel-bootmode-guard.py --status
BOOTMODE=CHARGER_LPM
  hit: cmdline androidboot.mode=charger [/proc/cmdline]
  hit: dmesg sec_bat_is_lpm_check: Low power charging mode: 1 [dmesg]
  hit: dmesg sec_ts_init: Do not load driver due to : lpm 1 [dmesg]
TOUCH_AVAILABLE=false
PERMANENT_FIX=BLOCKED_KERNEL BOOT_UPDATE_REQUIRED NOT_DEPLOYED
VERDICT=CHARGER_MODE_TOUCH_DISABLED no action taken: unplug and reboot normally
```

The one-line check anyone can run:

```sh
tr ' ' '\n' < /proc/cmdline | grep androidboot.mode     # prints nothing on a normal boot
```

**Action:** unplug the charger and reboot the phone normally (or let the guarded
automatic path do it once it is enabled). Then re-run the touch capture. Never
report touch results from a charger-mode boot.

## 7. Honest limitations

* The mitigation's *effect* (touch exists after the reboot) has not been observed by
  this group: this group is repository-only and does not reboot the live phone. The
  reboot itself is proven (A29b), but the post-reboot touch state on the current
  beta image is `DEPLOYED_UNVERIFIED` until the live group performs a normal reboot.
* The guard's launcher message is **published**, not rendered: the status-bar /
  notification surface is owned by the launcher work. `configs/nuxel/bootmode/README.md`
  (canonical subpath) and `configs/nuxel/touch/README.md` (legacy path, kept for the
  generated deploy plan) fix the JSON contract (`mode`, `touch_available`, `message`,
  `action`, `graded`, `evidence`).
* An `androidboot.mode=charger` boot is not a testable state for *anything* in the
  touch pipeline. If the boot-mode check says LPM, every other touch measurement on
  that boot is meaningless, and this document is the reason why.

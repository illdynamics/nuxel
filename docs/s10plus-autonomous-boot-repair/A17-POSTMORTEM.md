# A17 POSTMORTEM — the toybox `case` defect that killed the boot (2026-10-15)

**Candidate:** A17 (`A17/boot.img` sha256 `911a72e9fbe7f8b591e36fc72bac2d296f7a53b4ff2f9992eedea98e9c6582c2`)
**Evidence:** `captures/20261015T152348Z-A17-postfail/` (`/proc/last_kmsg`, 20,780 lines,
2 S-Boot segments; Nuxel session = lines 8862–20048)

```
BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP
RECOVERY_ACCESS=RESTORED
NEXT_ACTION=CAPTURE_NEW_BOOT_EVIDENCE
RESET_CAUSE=SEC_HARD_RESET_HOOK(operator) after a software reboot request that did not take effect
```

## 1. What A17 achieved (real progress, all measured)

| Item | Result |
|---|---|
| A17 kernel + A17 initramfs executed | YES — kernel banner `#3 SMP PREEMPT Thu Oct 15 14:55:16 UTC 2026`, and the new A17-only marker `ANIMATION_HOLD_PID=` is in the record |
| Framebuffer | `/dev/fb0` 32 bpp `stride=5760` `virtual_size=1440,6080` `modes=U:1440x3040p-0`, t = 2.23 s |
| First light + penguin | `FIRSTLIGHT exit=0`, `FIRSTLIGHT_FRAME_WRITTEN`, then the resident animator (`nuxel-fb-phone:3368`) |
| **Touchscreen** | **PRESENT for the first time**: `input: sec_touchscreen as /devices/platform/104b0000.hsi2c/i2c-4/4-0048/input/input2`, plus `sec_touchpad`, `sec_touchproximity`, `hrm_sensor`. `sec_ts_init` ran normally — **no** `lpm 1` message |
| systemd | **never started** — the boot died at t = 7.27 s, before `switch_root` |

The touchscreen result also **confirms the LPM analysis** in `DEVICE-OBSERVATIONS.md`:
A17 booted in normal mode (not `androidboot.mode=charger`), so `lpcharge = 0` and
`sec_ts_init()` reached `i2c_add_driver()`. A16 booted in charger mode and the
touchscreen was gated off. Same kernel, same driver — the difference is the boot mode.

## 2. Where A17 died

```
t = 2.233078  identity pin: S-Boot cmdline reports exynos9820 -> DEVICE=s10plus
t = 7.273340  dispatch: DEVICE='s10plus' ROOT_SPEC='PARTUUID=52444E41-…' ROOT_FSTYPE=''
t = 7.274204  generic probe selected '/dev/sda2'                       <-- WRONG BRANCH
t = 7.274319  refusing the generic probe on an exynos9820 board
t = 7.274585  [FATAL] no root block device found (slot=a)
t = 7.275992  [ERROR] emergency shell: /proc/cmdline:
t = 7.280427  === NUXXEL PANIC: no root device ===
t = 22.281523  debug-snapshot: normal reboot starting                  <-- the emergency path's reboot -f
t = 47.594435  hard_reset_hook : hrtimer_start                         <-- operator forces the reset
t = 53.594728  kernel BUG at drivers/samsung/sec_hard_reset_hook.c:157!
t = 53.747428  Kernel panic - not syncing: Fatal exception in interrupt
```

Two separate defects, both new information:

### Defect 1 (fatal): the DEVICE dispatch never worked — toybox `case` bug

`boot/initramfs/init.sh` dispatch:

```sh
case "${DEVICE}" in
    mustang|vm|"")   ...generic probe...
    s10plus)         ...S10+ USERDATA resolution...
    g7power)         ...
```

**toybox 0.8.14 treats an EMPTY pattern alternative as a WILDCARD.** Reproduced in
podman using the initramfs's own `/bin/toybox`:

```
$ toybox sh -c 'D=s10plus; case "$D" in mustang|vm|"") echo G ;; s10plus) echo S ;; *) echo X ;; esac'
G
$ toybox sh -c 'D=s10plus; case "$D" in mustang|vm)   echo G ;; s10plus) echo S ;; *) echo X ;; esac'
S
```

So `DEVICE=s10plus` matched `mustang|vm|"")`. **The `s10plus` and `g7power` branches
were unreachable dead code on every boot**, and this board's root always came from
the generic probe followed by the separate `force_s10plus_root()` rescue.

### Defect 2 (fatal in combination): the rescue silently bailed

`force_s10plus_root()` began with `case " ${CMDLINE} " in *…exynos9820*|*…G97*) : ;; *) return 0 ;; esac`.
In A16 that gate passed and the rescue found `/dev/sda31` after one second. In A17
it returned immediately: the log jumps from the generic-branch refusal straight to
the FATAL, with **no** `root override: forcing …` line at all. Its only other
cmdline-gated behaviour is a `case` pattern test, i.e. the same fragile primitive.
(The A17 record's `Kernel command line:` printk is truncated by the ram console at
~1 KiB — another thing A18 fixes — so the exact cmdline of that boot is not
recoverable from it.)

Net effect: a boot whose kernel, initramfs, first-light renderer and touchscreen
stack were all **correct** stopped at 7.27 s because of shell pattern matching.

### Defect 3: the emergency `reboot -f` does not reset this SoC

The failure path requests a reboot so the operator can read the evidence:

```
t = 22.281523  debug-snapshot: normal reboot starting     (comm: init)
```

…and the machine **kept running for another 31 s** with monotonic timestamps until
the operator forced the reset by hand at t = 47.59 s. So on this kernel
`reboot -f` from the initramfs logs a reboot and does not perform one. Do not
design a recovery path that depends on it; A18 keeps the attempt but logs it.

## 3. The fix (A18)

| id | change |
|---|---|
| A18-inline-1 | `cmdline_matches_samsung()` — `grep -q` instead of `case` patterns, defined before its first caller |
| A18-inline-2 | the kernel cmdline is emitted to `/dev/kmsg` in **200-byte `CMDLINE_PART n:` chunks** so the ram console's ~1 KiB truncation can never hide `root=` or the board tokens again |
| A18-core-1 | `force_s10plus_root()` rewritten: no `case` patterns anywhere, unconditional evidence-driven gate (`cmdline_matches_samsung \|\| -b /dev/sda31`), 20 s heartbeat wait for the node |
| A18-core-2 | the `DEVICE` dispatch is now `if/elif` with explicit `[ "$DEVICE" = … ]` tests — the branch structure cannot be fooled by pattern semantics |
| A18-core-3 | the `s10plus` branch waits up to 20 s for `/dev/sda31` with a per-second heartbeat, instead of one single `[ -b ]` test that gave up before the UFS node existed |

`boot/initramfs/init.sh` A18: 60,889 B, sha256
`3ea2546cf197b0fbd4a290026b7fd3a089585f69e95f110287ab30a40822ee90`.

## 4. Offline validation of the fix (before flashing)

The root-resolution code was extracted from the A18 `init.sh` verbatim and run
under **the initramfs's own toybox** in podman, with the Samsung cmdline and a
simulated late `USERDATA` node:

```
SAY: CMDLINE_PARTS 1 bytes=131 samsung=yes
SAY: dispatch: DEVICE='s10plus' ROOT_SPEC='PARTUUID=52444E41-…' ROOT_FSTYPE=''
SAY: s10plus: waiting for /dev/sda31 t=1s blockdevs=''
SAY: s10plus: waiting for /dev/sda31 t=2s blockdevs=''
SAY: s10plus: USERDATA via documented /dev/sda31 (by-name userdata) after 2s; rootfs verified below
SAY: s10plus: root -> /dev/sda31 (fstype: ext4)
SAY: root override: enter ROOT_DEV='/dev/sda31' samsung=yes
SAY: root override: leaving ROOT_DEV='/dev/sda31' (not a bootloader/Android partition)
RESULT ROOT_DEV='/dev/sda31' DEVICE='s10plus'
```

Before the fix the same harness printed the generic-probe refusal and the FATAL.
That is the causal proof that A18 addresses the A17 failure.

## 5. What remains unproven (important)

**The A17 service-execution fix has still never run.** A17 died before
`switch_root`, so `pidref.c`'s degradation and the cgroup2 ordering change have
had **zero** hardware exposure. A18 is the first candidate that can test them —
A16's systemd stage (`systemd 258.11-1.fc43 running in system mode`, 29× `Failed
to spawn executor`) is still the baseline. Do not claim the service fix until
A18's log shows services reaching `active`.

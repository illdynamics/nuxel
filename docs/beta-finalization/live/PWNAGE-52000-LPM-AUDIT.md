# PWNAGE-52000 — exact LPM/charger-boot audit (S10+ / beyond2lte)

## Verdict

| Item | Verdict |
|---|---|
| Exact vendor source identified | `Linux4/android_kernel_samsung_exynos9820@f7194c1d15eded1c2a1a4dc63825b26103435cc0` (4.14.253) |
| All `lpcharge` consumers audited | **YES** (see table) |
| Root cause revalidated in exact source | `sec_ts_init()` returned `-ENODEV` before `i2c_add_driver()` when `lpcharge==1` |
| Exact-source patch prepared | `kernel/s10plus/patches/0006-sec-ts-lpm-bind.patch` |
| Patch applied to a live BOOT image | **NO — TWRP was not visible over adb on 2026-11-01; no partition write attempted** |
| Physical cold-boot proof | **BLOCKED_OWNER/TWRP** — power OFF + charger + power ON still uses the old kernel until a BOOT-only flash is authorised |

## Every `lpcharge` consumer in the pinned tree

| File | Use | Safety impact of binding touch |
|---|---|---|
| `drivers/samsung/misc/sec_batt.c` | `__setup("androidboot.mode=")` sets cached `lpcharge` | Unchanged; flag remains set on LPM boots |
| `drivers/input/touchscreen/sec_ts/y771/sec_ts.c` | initcall `-ENODEV`; dump-time log skip | **Patched**: bind driver; log-dump skip stays |
| `drivers/input/touchscreen/sec_ts/y771_d/sec_ts.c` | same pattern | Not built (`CONFIG_TOUCHSCREEN_SEC_TS_Y771_D` is not set) |
| `drivers/samsung/misc/sec_nad.c` | factory NAD init skip | Unchanged |
| `drivers/samsung/sec_reboot.c` | poweroff/reboot charger loop | Unchanged |
| `drivers/samsung/debug/sec_debug_platform_watchdog.c` | skip platform-watchdog check in LPM | Unchanged |

No fingerprint (`qbt2000`) or Wacom `lpcharge` gate exists in this exact source
tree. The prompt's claim about those gates is not present at this commit; they are
therefore **UNSUPPORTED/ABSENT**, not silently patched.

## Why the patch is minimal

The only thing an LPM power-up removes from userspace is the touch I2C client.
The Nuxel initramfs/userspace already starts Phoc and `nuxel-wl-fb` in that boot;
the framebuffer was live at 1440×3040 in the earlier measurement. `sec_ts_probe()`
has no LPM gate: rails, reset, I2C and IRQ are the ordinary probe path. The patch
therefore removes only the initcall `-ENODEV` and keeps the cached `lpcharge` for
`sec_reboot` and the platform-watchdog safety path.

It does **not** clear `lpcharge`, change charger current, thermal limits, PMIC
registers or the bootloader. The dump-time LPM check remains (only skips a
diagnostic dump).

## Deployment gate (not performed)

A BOOT-only flash requires, at the time of writing:

1. Phone actually in TWRP and visible over the agreed USB/adb transport.
2. Exact model/partition evidence (`SM-G975F`, `beyond2lte`, BOOT target).
3. Off-device SHA-256 readback of the current known-good BOOT.
4. One ARM64 candidate built from this exact patch/config, verified DTB and
   initramfs.
5. Flash only BOOT; on any hang/bootloop/TWRP return, restore the verified
   previous BOOT immediately.

On 2026-11-01 `adb devices -l` returned no device, so this was not attempted.

## Userspace fallback

`services/nuxel-s10/bin/nuxel-charger-mode-recovery.sh` remains a one-shot
fallback only. It now requires the authoritative `BOOTMODE=CHARGER_LPM` state,
absent touch, no owner/capture locks, ≥120 s uptime, charger online **and**
battery status `Charging`, and a 900 s cooldown. It is not presented as the
permanent fix.

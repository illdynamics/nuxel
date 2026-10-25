# NUXEL A74 / 23000 — FINAL STATUS

**Date:** 2026-10-25 (CEST)
**Branch:** `nuxel/a74-23000-usb-unplug-pwnage` — commit `909a9db`
**Boot ID (continuity marker):** `c630c24d-5261-486c-8217-82dd8765f4ad`

## Outcome

**Root cause:** kernel hard lockup → hardware watchdog reset, caused by the A73
physical detach veto reading the Samsung DWC3 debugfs `link_state` register node
after detach (FSYS0 power domain off → bus SLVERR → `Watchdog detected hard
LOCKUP on cpu 0` → s3c2410-wdt reset). See ROOT-CAUSE-AND-FIX.md and
CRASH-CLASSIFICATION.md for the full evidence chain.

**Fix:** removed that debugfs read from both indicator producers. The Type-C
class `data_role` is now the sole physical detach veto (safe PMIC sysfs
attribute, and already proven to extinguish the icons on detach). Deployed and
hash-verified; automated regression suites ALL PASS.

## What is done
- [x] Failure class proven (panic record + pstore + previous-boot journal).
- [x] Minimal fix implemented, tests extended, deployed, hashes repo==deployed.
- [x] Alternate recovery path: SSH over Wi-Fi (`root@192.168.178.167`) works.
- [x] Durable on-device detach logger (A74, no debugfs read) running and
      recording `boot_id` + `uptime` every state change.
- [x] Rollback script + backups on-device (`/var/lib/nuxel/a74-backup/`).

## NOT done — requires owner
- [ ] **Physical unplug/replug acceptance (P1–P11).** The agent cannot pull the
      USB cable. `PASS_PHYSICAL` is **not claimed**; the automated tests are
      `PASS_OFFLINE_ONLY`.

## Owner's physical test (safe now; alternate path is SSH over Wi-Fi)
1. On the phone, note the three penguins are correct while attached.
2. **Unplug** the USB cable from the computer (or phone).
3. Wait ~3 s: charging/PC/Live-Console penguins OFF; phone stays responsive;
   **no hang, no reboot**.
4. **Replug**: PC ON, Live Console ON once the session re-establishes.
5. Repeat unplug/replug at least **5** cycles.
6. (Optional) wall charger only → charging ON, PC OFF; healthy battery removal
   must not reboot.

The phone records every cycle to `/var/lib/nuxel/a74-usb-unplug.log` (with boot
ID + uptime per sample). After the cycles, run:
```sh
ssh root@192.168.178.167 'cat /proc/sys/kernel/random/boot_id; cat /proc/uptime;
tail -20 /var/lib/nuxel/a74-usb-unplug.log'
```
The boot ID must still be `c630c24d-5261-486c-8217-82dd8765f4ad` and uptime
must have continued across every cycle. Report the output back; the agent will
record `PASS_PHYSICAL`/`FAILED` per cycle in TEST-MATRIX.md.

## Regressions
None observed. Charging/PC/Live-Console artwork, sizes, positions and animations
were not modified; Wi-Fi/HTTPS (verified `200` to https://www.google.com),
Bluetooth/Location tiles, lockscreen/navigation and apps were not touched.

# FULL-PWNAGE-104300 — System time, RTC and clock sync on Nuxel

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte`
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Report to produce:** `REPORT-PWNAGE-104300.md`
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

The phone's clock is wrong and non-monotonic. It must:

1. Start from the hardware RTC (or, if the RTC cannot hold time, a correctly
   provisioned fallback) so the clock is right **before** networking and services.
2. Sync automatically over NTP once on Wi-Fi, and stay synced across suspend.
3. Report the correct timezone (`Europe/Amsterdam`, CET/CEST) with correct DST.
4. Keep logs, TLS certificate validity, `flock`-based auth and scheduled jobs sane.

---

## 1. Current observed state (2026-11-14 15:40–16:00 CET)

```
hostname: 2001-1c00-4d09-8a00-162b-e49d-dc7c-4128   (bogus / not a valid name)
kernel:   4.14.253-gf7194c1d15ed-dirty #3 SMP PREEMPT Sat Nov 14 09:51:04 CET 2026
journal boot entries alternate between "WIN-CLIENT" and the 2001-... hostname,
and some entries are stamped 2026-11-14 while the system clock reports 1970.
```

Symptoms to reproduce and confirm:

```sh
date; timedatectl 2>/dev/null || true
hwclock -r 2>&1 || true
ls -l /dev/rtc* /sys/class/rtc/rtc0/ 2>&1
cat /sys/class/rtc/rtc0/{date,time,since_epoch} 2>&1
systemctl status systemd-timesyncd chronyd ntp 2>&1 | head -40
journalctl --list-boots | head
```

Note which of these is true:

- RTC node missing / returns 1970 → no battery-backed time (S10+ uses the PMIC RTC;
  check `rtc-sec`, `max77865-rtc`, `s3c-rtc`, or similar).
- RTC readable but the kernel/init never sets the system clock from it.
- System clock set from RTC but immediately overwritten by a bad source.
- NTP service missing/blocked (no DNS, firewall, no network yet).
- Hostname derived from a serial/MAC and truncated into an invalid string.

---

## 2. Non-negotiable rules

1. Do not "fix" time by hardcoding `date` in a service that runs at boot only.
   That is a hack, not a fix; it also breaks after suspend.
2. Do not weaken TLS by disabling certificate checks to compensate for a wrong clock.
3. Keep the phone bootable; no flashing without approval.
4. Every change must be persistent (unit/config in the repo + deployed to the phone).
5. Bounded network operations (NTP queries) with timeouts.

---

## 3. Work order

### Step 1 — Establish the time source chain

Map exactly how time arrives:

- kernel → `systemd` → `systemd-timesyncd` (or `chronyd`/`ntpd`)
- RTC device driver and which `/dev/rtcN` is the PMIC RTC
- whether `CONFIG_RTC_HCTOSYS` is set and whether `hctosys` ran
- whether the vendor bootloader passes time to the kernel (`androidboot` args)

Document each link and where it breaks.

### Step 2 — Fix the RTC path

- Make the system clock initialize from the RTC at boot
  (`systemd` normally does this via `systemd-timesyncd`/`systemd-hwclock`; on this
  image check whether the units are present and enabled).
- Ensure the RTC is written back on shutdown/suspend.
- If the PMIC RTC is not supported by this kernel, state that precisely and propose
  the smallest kernel/DT change (requires approval) — do not fake it in userspace.

### Step 3 — NTP

- Enable `systemd-timesyncd` (preferred; already in Fedora) or `chronyd`.
- Make it wait for the network (`After=network-online.target`) but not block boot.
- Verify with `timedatectl timesync-status` / `chronyc tracking`.
- Confirm the clock is already sane **before** TLS services start where practical.

### Step 4 — Timezone and hostname

- Set the timezone to `Europe/Amsterdam` persistently.
- Replace the invalid hostname with a stable, valid one (e.g. `nuxel`), persistently
  (`/etc/hostname`, `hostnamectl`, `/etc/hosts`).
- Fix journal identity so logs are attributable.

### Step 5 — Verify

1. Reboot. Clock must be correct within ~60 s of network.
2. `timedatectl` shows `System clock synchronized: yes`, correct TZ, correct DST.
3. Simulate NTP loss (e.g. block UDP 123) → clock must not jump backwards; it may
   drift only.
4. Suspend/resume → clock continues correctly.
5. TLS endpoints (xrdp cert, wayvnc TLS, HTTPS to OSM tiles) validate without
   `--insecure`.
6. Logs use the correct hostname and monotonic 2026 timestamps.

---

## 4. Report contract (`REPORT-PWNAGE-104300.md`)

Include the source-chain map, before/after `date`/`timedatectl`/`hwclock` output,
units and config files changed, reboot evidence, NTP-loss test, DST test, hostname
fix, and rollback. End with `FULLY_DONE` / `PARTIAL` / `BLOCKED`.

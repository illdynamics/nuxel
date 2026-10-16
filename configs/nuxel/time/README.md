# `configs/nuxel/time/` — timekeeping, RTC and timesync (area 5)

Everything in this directory is S10+ (beyond2lte) timekeeping policy. Install
locations, read by the tool at the time it runs:

| File | Install to | Purpose |
|---|---|---|
| `time.json` | `/etc/nuxel/time/time.json` | Single policy source read by `nuxelctl time` (thresholds, backend preference, bridge/journal tolerances, RTC candidates) |
| `60-nuxel-timesyncd.conf` | `/etc/systemd/timesyncd.conf.d/60-nuxel-timesyncd.conf` | Preferred timesync backend (systemd, no extra package) |
| `nuxel-chrony.conf` | `/etc/chrony.d/60-nuxel.conf` | Documented fallback backend (chrony), enabled only if it is really available |
| `nuxel-rtc-check.service` | `/etc/systemd/system/nuxel-rtc-check.service` | Periodic evidence-only verifier (`nuxelctl time verify --log`) |
| `nuxel-rtc-check.timer` | `/etc/systemd/system/nuxel-rtc-check.timer` | Runs the verifier every 30 min, persistent across missed runs |

## What is deliberately NOT here

* No kernel cmdline edit, no partition write, no `rtc` register poking. Setting
  the clock and syncing the RTC (`hwclock --systohc`) happens through
  `nuxelctl time` on the running system only.
* No hard-coded RTC device name: `rtc.device = auto` and the tool enumerates
  `/sys/class/rtc/*` and reports the real name.
* No claim that a timesync daemon is running: the tool reports the backend that
  is actually installed and active, and says `NO_TIMESYNC_BACKEND` otherwise.

## Commands (on the device)

```sh
nuxelctl time status          # clock, RTC, backend, journald and launcher agreement
nuxelctl time verify          # PASS/FAIL per check, with the reason
nuxelctl time rtc             # RTC inventory (name, date, since_epoch)
nuxelctl time mark            # record the RTC before an ordinary reboot
nuxelctl time compare         # after the reboot: the recorded RTC delta
nuxelctl time sync            # request an NTP sync through the real backend
nuxelctl time set 2026-10-16T12:00:00Z   # manual set, then systohc
```

Full design, evidence rules and the owner procedure:
`docs/beta-finalization/system/TIME-RTC.md` and
`docs/beta-finalization/manual-proof/05-timekeeping.md`.

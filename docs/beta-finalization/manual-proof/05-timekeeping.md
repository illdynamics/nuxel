# Area 5 — Time, RTC and timesync

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED).
Owner action required? **Yes** — the mark/compare procedure needs one ordinary
reboot performed by the owner, with the phone in hand.

---

## 1. Feature

Timekeeping on the S10+ (beyond2lte): the PMIC RTC read/write path, the
timesync backend (systemd-timesyncd preferred, chrony fallback), the periodic
evidence-only verifier (`nuxel-rtc-check.timer`), and the console tooling
`nuxelctl time status | verify | rtc | mark | compare | sync | set`.

## 2. Why this matters

An unset clock breaks TLS, breaks NTP, makes every log line useless and turns
the launcher's status-bar clock into decoration. RTC persistence is also the only
thing that keeps the phone's clock sane on a network-less boot.

## 3. Preparation

1. Handset booted into Nuxel, screen unlocked, console/SSH access available.
2. Note the current time from a second device (a watch or another phone) — this
   is the independent reference for step 4d.
3. Run the read-only snapshot first:
   ```sh
   nuxelctl time status
   ```
   Record the verdict line. If it is `RTC_ABSENT`, stop: the RTC driver is not
   bound and persistence cannot pass; that is a kernel-side finding, not a retry.

## 4. Exact action

a. Backend sanity (no reboot needed):
   ```sh
   nuxelctl time verify
   ```
   Every line must be PASS except `NEEDS_OWNER_TEST RTC persistence` — that one
   is what part (c) below turns into a real verdict.

b. Clock correctness:
   ```sh
   nuxelctl time sync            # ask the active backend for a sync
   nuxelctl time rtc             # RTC name/date/since_epoch + kernel config symbols
   ```
   Then confirm the launcher's status-bar clock matches the system time
   (`nuxelctl time status` → `launcher_agrees=yes`).

c. Persistence across an ordinary reboot — the actual test:
   ```sh
   nuxelctl time mark            # BEFORE the reboot
   # perform exactly ONE ordinary reboot, which returns to Nuxel
   nuxelctl time compare         # AFTER the reboot
   ```
   Do **not** repeat the reboot a second time if the compare fails: one
   measurement is enough, and the honest next action is to read the numbers and
   the journal.

d. Independent cross-check (human, therefore needed):
   * compare the launcher clock with the reference clock from preparation step 2
     — the difference must be under a minute;
   * `journalctl -b -n 5 --no-pager` — the timestamps must be closer to "now"
     than to the last boot;
   * `nuxelctl time verify` again after 30 minutes of idle: the timer should have
     appended a fresh block to `/var/log/nuxel/time.log`.

## 5. Expected result

* `nuxelctl time verify` → `summary: pass=6 fail=0` (the persistence line reads
  `NEEDS_OWNER_TEST` until part (c) has been recorded).
* `nuxelctl time compare` → `PASS rtc_epoch advanced by Xs, wall clock by Ys`.
* The launcher clock, the system clock and the independent reference agree
  within one minute.
* `/var/log/nuxel/time.log` gains a new block every ~30 minutes.

## 6. Failure symptoms

| Symptom | Meaning / next action |
|---|---|
| Verdict `RTC_ABSENT` (no `/sys/class/rtc/*`) | No RTC driver bound — kernel-side work, offline only. Do not retry the reboot. |
| Verdict `NO_TIMESYNC_BACKEND` (verify FAILs) | No timesync daemon active: `systemctl status systemd-timesyncd`; the clock will keep drifting. |
| `CLOCK_NOT_SET` — epoch is 1970 | The RTC is unreadable at boot or `CONFIG_RTC_HCTOSYS` is off; both are findings, and the timestamps of everything logged before you fixed it are invalid. |
| `compare` FAILs with a positive RTC error | The RTC lost time while the phone was off (dying cell) or was not written back (`hwclock --systohc`). |
| `compare` reports `same boot_id` | No reboot happened between the mark and the compare — the pair proves nothing; redo it. |
| `journald_agrees=NO` | journald froze or is reading a stale clock: restart `systemd-journald` and re-run `verify`. |
| `launcher_agrees=UNKNOWN` | The bridge is unreachable, so the launcher clock is unverified — state that, never assume it is fine. |
| Clock jumps only after the network comes up | Normal before a sync; record the initial offset so the RTC's own error is visible. |

## 7. Diagnostic command / log path

* `nuxelctl time status|verify|rtc|mark|compare` —
  `tools/s10plus/a33/nuxel-time.sh`
* Evidence log: `/var/log/nuxel/time.log`
* Mark/compare state: `/var/lib/nuxel/time/rtc-before.json`,
  `/var/lib/nuxel/time/rtc-after.json`
* Kernel symbols: `nuxelctl time rtc` (reads `/boot/config-$(uname -r)`)
* Offline regression: `python3 tools/s10plus/a33/tests/test-time-rtc.py`
* Design: `docs/beta-finalization/system/TIME-RTC.md`

## 8. PASS / FAIL

* **PASS** — parts (a)–(d) hold: verify shows `fail=0`, `compare` returns PASS
  with the numbers quoted in the report, the independent reference agrees within
  a minute, and the timer keeps appending evidence.
* **FAIL** — any of: a FAIL line from `verify`, a FAIL/UNKNOWN verdict from
  `compare`, a launcher clock off by more than the tolerance, or a missing timer
  entry. Quote the exact `compare` line — it names the layer and the magnitude.

## Current automatic evidence (repository, this build group)

* `tools/s10plus/a33/nuxel-time.sh selftest` → 5/5 fixtures PASS
  (`RTC_ABSENT`, `NO_TIMESYNC_BACKEND`, `CLOCK_NOT_SET`, `PARTIAL_EVIDENCE`,
  `CLOCK_OK_UNVERIFIED_PERSISTENCE`).
* `python3 tools/s10plus/a33/tests/test-time-rtc.py` → all checks PASS, including
  the deterministic mark/compare PASS case, the FAIL case with numbers, and the
  same-boot-id refusal.
* `nuxelctl time verify` on the "everything agrees" fixture: `pass=6 fail=0`,
  persistence `NEEDS_OWNER_TEST`.
* On-device RTC persistence is **not** claimed: it stays `NEEDS_OWNER_TEST` in
  `configs/nuxel/capabilities/connectivity-time-audio-buttons.json` until the
  owner records the mark/compare pair.

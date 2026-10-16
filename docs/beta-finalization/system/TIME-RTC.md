# Time, RTC persistence and timesync on the S10+ (area 5)

Scope: the Samsung Galaxy S10+ **SM-G975F / beyond2lte / Exynos 9820**, Fedora 43
ARM64 userspace, Linux 4.14.253. Everything below is either verified from real
repository files or explicitly marked as not yet observed on hardware.

**Terminal states for this area**

| Item | State |
|---|---|
| Policy + drop-ins + verifier tooling | `OFFLINE_TESTED` |
| Fixture/verdict logic and mark/compare arithmetic | `OFFLINE_TESTED` |
| Which timesync package exists on this image | `OFFLINE_TESTED` (probe is part of the tool; package claim verified against repo metadata in the dependency report) |
| RTC set/read on the handset | `NEEDS_OWNER_TEST` |
| RTC persistence across an ordinary reboot | `NEEDS_OWNER_TEST` |
| Settings surface, clock permissions, last-known record, suspend honesty (contract + code) | `OFFLINE_TESTED` |
| Suspend/resume timekeeping on the handset | `NEEDS_OWNER_TEST` (a resume needs a finger; the kernel's own state list is reported, never assumed) |

No claim in this document is `VERIFIED_ON_S10PLUS`.

---

## 1. Why this exists

A phone that boots with an unset clock produces logs with meaningless
timestamps, breaks TLS certificate validation, makes NTP itself fail, and makes
the launcher's status-bar clock wrong. Two independent things have to be true:

1. the kernel must read the **RTC** at boot and hand a plausible time to
   userspace (`CONFIG_RTC_HCTOSYS`), and something must write the system clock
   back to the RTC afterwards (`hwclock --systohc`, or chrony's `rtcsync`);
2. userspace must actually run a **timesync** backend, otherwise the clock is
   only as good as the RTC's battery-backed drift.

The A32 baseline never made a claim about either. This area makes both
observable, and refuses to claim them when they are not.

## 2. Hardware / kernel facts and what is NOT assumed

| Fact | Status on this device |
|---|---|
| The RTC is inside the Samsung **PMIC** on the AP | Stated by the mission; the **driver/binding is not assumed** |
| `/sys/class/rtc/rtc0` with a `name` file | Observable; `nuxelctl time rtc` prints the real name |
| Kernel config `CONFIG_RTC_CLASS`, `CONFIG_RTC_DRV_S5M` (PMIC RTC family) | Read from `/boot/config-$(uname -r)` when present; reported `unknown` when it cannot be read — never assumed |
| `CONFIG_RTC_HCTOSYS=y` (RTC → system clock at boot) | Required for persistence; the tool reports the real value |
| RTC date/time registers | Read via sysfs `date`/`time`/`since_epoch`; `hwclock --show --utc` is the fallback |

The candidate driver name (`s5m-rtc` family) is recorded in the policy as a
*config symbol to check*, not as an assertion that it is what this handset
binds.

## 3. Policy: `configs/nuxel/time/`

| File | Installs to | Role |
|---|---|---|
| `time.json` | `/etc/nuxel/time/time.json` | Single source of policy: thresholds (`max_drift_s_warn` 60 s, `max_drift_s_fail` 300 s), backend preference, RTC candidates, bridge/journal tolerances, mark/compare paths |
| `60-nuxel-timesyncd.conf` | `/etc/systemd/timesyncd.conf.d/` | Preferred backend (see §4) |
| `nuxel-chrony.conf` | `/etc/chrony.d/60-nuxel.conf` | Documented fallback backend |
| `nuxel-rtc-check.service` | `/etc/systemd/system/` | Evidence-only verifier: `nuxelctl time verify --log` |
| `nuxel-rtc-check.timer` | `/etc/systemd/system/` | Every 30 min (`OnUnitActiveSec=30min`, matching `rtc.save_interval_min`), `Persistent=true` |

The verifier holds `SuccessExitStatus=0 1`: a recorded finding (e.g. a missing
RTC) does not fail a boot, while a genuinely wrong clock relationship still
surfaces as a non-zero exit and a journal entry.

## 4. Timesync backend choice (no assumptions from newer kernels)

* **Preferred: `systemd-timesyncd`** — ships with systemd on Fedora 43 ARM64,
  needs no extra package, and its SNTP client needs no kernel feature newer than
  4.14.
* **Fallback: `chrony`** — only if timesyncd is absent/disabled, and only after
  the package is verified to exist in the real ARM64 repository metadata
  (`dnf repoquery --arch aarch64 chrony`, recorded in the dependency report).
  `hwtimestamp` is deliberately **not** enabled: hardware timestamping depends on
  a NIC/RTC capability that is unverified on this handset.
* Anything else (`ntpsec`, `openntpd`, `ntpd`) is *detected* but never silently
  preferred; if none is active the tool reports **`NO_TIMESYNC_BACKEND`** and
  `nuxelctl time verify` fails the "timesync backend active" check.

Fedora 43 bootstrapping note: only one backend is enabled at a time. Enabling
`chronyd` while `systemd-timesyncd` is active would produce two clients fighting
over the clock, which is worse than either alone.

## 5. Commands

```sh
nuxelctl time status [--json]   # clock, RTC, backend, journald and launcher agreement + verdict
nuxelctl time verify [--json]   # PASS/FAIL per check; exit 1 if any check is wrong
nuxelctl time rtc               # RTC inventory + kernel config symbols
nuxelctl time mark              # record system+RTC+boot_id BEFORE an ordinary reboot
nuxelctl time compare           # AFTER the reboot: RTC delta with a PASS/FAIL verdict
nuxelctl time sync              # ask the active backend for a sync
nuxelctl time set <ISO8601>     # set the clock, then write it back to the RTC (systohc)
nuxelctl time selftest          # 5 offline fixtures
```

`nuxelctl` dispatches `time` to `tools/s10plus/a33/nuxel-time.sh`; `nuxelctl`
itself keeps the A32 commands byte-compatible by delegating everything it does
not own (see `tools/s10plus/a33/nuxelctl`).

## 6. The three agreements that make "the clock is right" observable

1. **RTC delta** — `system_epoch - rtc_epoch`, measured, with warn/fail
   thresholds from the policy. A large positive delta means the RTC is behind
   (its battery is dying or `systohc` never ran).
2. **journald agreement** — the newest journal entry's timestamp compared with
   the current clock. This catches the classic failure where journald froze (or
   is reading a stale kernel clock) while `date` looks fine.
3. **Launcher agreement** — the status bar renders the bridge's
   `phone/status.time` (`services/nuxel-bridge/src/api.py`,
   `_get_system_phone_status`), so the tool reads that *same* value over
   `http://127.0.0.1:8080/api/v1/phone/status` and compares it with the local
   clock. Reading the same source the user sees is what stops "the launcher clock
   is fine" from being an eyeball claim. When the bridge is unreachable the check
   reports **UNKNOWN** — never PASS.

## 7. Persistence across an ordinary reboot (owner procedure, evidence-based)

```sh
nuxelctl time mark       # before: writes /var/lib/nuxel/time/rtc-before.json
#  one ordinary reboot, which must return to Nuxel
nuxelctl time compare    # after: writes rtc-after.json and computes the verdict
```

The verdict is arithmetic, not optimism:

* it **refuses** the pair when `boot_id` did not change (no reboot happened —
  a same-boot comparison would be evidence of nothing);
* it reports **UNKNOWN** when the pre-reboot RTC was unreadable;
* it **PASSES** only when the RTC advanced by the same amount as the wall clock
  within `reboot_persistence.max_delta_s` (10 s default);
* it **FAILS** with the exact numbers otherwise (`rtc advanced by Xs, wall clock
  by Ys, error Zs`).

No flashing, no kernel cmdline edit, no RTC register poking is involved:
`nuxelctl time set` writes the clock and then `hwclock --systohc --utc`, nothing
else. If `hwclock` fails, the tool says the RTC was **not** updated.

## 8. Tests and evidence

| Test | What it proves |
|---|---|
| `tools/s10plus/a33/nuxel-time.sh selftest` | 5 fixtures: `RTC_ABSENT`, `NO_TIMESYNC_BACKEND`, `CLOCK_NOT_SET`, `PARTIAL_EVIDENCE`, `CLOCK_OK_UNVERIFIED_PERSISTENCE` |
| `python3 tools/s10plus/a33/tests/test-time-rtc.py` | verdict logic, `verify` exit codes, mark/compare PASS + FAIL + same-boot refusal, policy/unit self-consistency (timer cadence == policy), no-flashing invariant |
| `nuxelctl time verify --log` | appends the full report to `/var/log/nuxel/time.log` (the on-device evidence trail) |

The fixtures pass on a laptop with no RTC and no radio by construction: the tool
reads `/sys`, `/proc`, `/lib/firmware` and the tools under `NUXEL_DIAG_ROOT`,
and refuses to fall back to host state when the fixture isolation flag is set.

## 9. Rollback

* Revert `configs/nuxel/time/*` from git and re-install the previous files
  (the previous `/etc/systemd/system/nuxel-rtc-check.*` were never present before
  this change, so removal is `systemctl disable --now nuxel-rtc-check.timer` and
  delete the two units).
* No clock or RTC state is modified by installing this area; the only writes are
  the owner-driven `mark`/`compare` JSON files under `/var/lib/nuxel/time/` and
  the evidence log under `/var/log/nuxel/`.
* `nuxelctl time set` is the only command that changes the clock, and running it
  twice with the correct timestamp restores the intended state.

## 10. Who may set the clock (permissions)

`configs/nuxel/time/time.json → clock_permissions` records the rule the Settings
page must not break:

* `timedatectl set-time` / `set-timezone` require **root or `CAP_SYS_TIME`** and go
  through polkit, which will prompt an unprivileged caller.
* The **launcher / status bar only reads** the clock (the bridge's phone-status
  `time` field is local `HH:MM`); an app or PWA has no write path at all.
* After boot, **systemd-timesyncd (or chrony)** own step/slew; the page shows their
  state instead of pretending to be the authority.
* `CLOCK_MONOTONIC` is unaffected by clock steps, which is why the button FSM and
  every timeout use it rather than the wall clock.

## 11. Last-known time (a floor, never a fabricated instant)

A dead or reset RTC can make the phone boot in 1970: logs then get meaningless
timestamps, TLS validation fails and NTP itself cannot bootstrap. The policy
(→ `last_known_time`) keeps a **last-known lower bound** at
`/var/lib/nuxel/time/last-known.json`:

```sh
nuxelctl time last-known --record   # while the clock is plausible: write the floor
nuxelctl time last-known            # after a suspicious boot: compare against the floor
```

* A record is **refused** when the system clock is below
  `plausible_after` (2024-01-01T00:00:00Z): writing an implausible instant as
  "last-known" would fabricate a time.
* When the clock reads **earlier** than the record, the tool prints
  `RTC_SUSPECT` and says to re-sync before trusting any timestamp.
* The file itself states that it is a **floor**, not a measurement of "now".

## 12. Timezone data, automatic timezone and the display format

* **tzdata is probed, never assumed**: the picker is populated from
  `timedatectl list-timezones`, whose entries come only from the installed
  `/usr/share/zoneinfo`. With no tzdata the page reports `TZDATA_MISSING` and
  offers **UTC only**, saying so. The package claim is checked against the Fedora
  43 ARM64 manifest in `docs/beta-finalization/system/DEPENDENCY-REPORT.md`.
* **Automatic timezone is gated on the location service**: with location disabled
  the row is off and says why. A timezone is never inferred from an IP address or
  from a guess.
* **12/24-hour format is a display preference** (`time_format`): it changes the
  launcher's rendering and no kernel, RTC or timesync state.

## 13. Suspend / resume timekeeping (reported, not assumed)

`configs/nuxel/time/time.json → suspend_resume` and `nuxelctl time settings`
report the state list the **kernel** advertises:

```sh
nuxelctl time settings      # prints /sys/power/state and what it means
```

* If `/sys/power/state` contains `mem`, suspend-to-RAM is advertised by this
  kernel — that is a statement about the kernel, **not** proof that this handset
  suspends. Triggering a resume needs the owner, so the verdict stays
  `NEEDS_OWNER_TEST`.
* If it lists only `freeze`, the tool says so explicitly and suspend-to-RAM is
  **not claimed** for this kernel.
* `CLOCK_MONOTONIC` pauses across a suspend while the **wall clock** must be
  re-corrected by the RTC or the timesync backend after resume; that correction is
  observable in the journal, which is what makes it checkable rather than assumed.

## 14. Settings surface (renderer: briq-06d)

`nuxelctl time settings` prints the Date & time surface: auto time (NTP state),
automatic timezone (with its location dependency), the timezone, RTC-in-local-TZ,
the 12/24-hour preference, the configured NTP servers and the **last sync** state
(`UNKNOWN` when no backend answers — never replaced by the boot time). bg-03 owns
the contract in `configs/nuxel/time/time.json → settings_surface`; briq-06d
renders the page and must not display a value that no listed `read_api` produced.
## 15. Known limitations (stated, not hidden)

* RTC **persistence across power-off** (battery removal / deep discharge) is a
  different test from reboot persistence and is not covered here.
* NTP requires network reachability; on a phone without a working radio (area 4)
  the clock is corrected only by the RTC - and by `last-known` when the RTC is
  itself suspect.
* Whether the RTC is **battery-backed** is not assumed: it is inferred only from
  the observed behaviour across a real power loss plus the RTC's own delta, and is
  reported as uncertainty rather than as a datasheet fact.
* The S10+ vendor kernel's RTC driver behaviour after a Samsung-firmware
  "Download/Recovery" boot is out of scope: those modes must never be triggered
  (mission invariant).

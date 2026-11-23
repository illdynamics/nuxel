# S5000AP — Round 01: Live Baseline, Source Reconciliation, First Blocker

**Branch/HEAD:** `cs/mob` @ `9281b6f51964e9d1374b9d19d736a5e69ad6617c`
**Recorded baseline commit:** `22dd6b3ab46dece28abfe83607d7cc64add76843` (`fix(modem): report S5000AP transport truthfully`, 2026-11-17T13:48:42+01:00) — present in history, reachable from `feat/mob` / `origin/feat/mob`, **not** an ancestor of current HEAD (`22dd6b3...HEAD` = 1 / 39). No reset was performed.
**Round window (this run):** `2026-11-23T01:20Z` → `2026-11-23T01:40Z`. Device time is UTC (the host's SSH banner says `WIN-CLIENT`; kernel cmdline shows the real hardware is SM-G975F/beyond2lte).
**Handset actions:** read-only only. No reboot, no flash, no RF change, no Wi-Fi disable, no CP power/reset/download, no DT/DTBO/DTS touch, no BOOT or protected-partition write.

Classification vocabulary (mission §Sources):

| Class | Meaning |
|---|---|
| `PROVED_LIVE` | Observed on the physical handset in **this** round, with a timestamp |
| `CAPTURED_LIVE_OLDER` | A prior live capture exists; not re-observed this round |
| `OFFLINE_TESTED` | Passes a host unit/fixture test; no hardware proof |
| `SOURCE_ONLY` | Code/source exists and audits clean; never ran on device |
| `DOCUMENTED_ONLY` | Written down; no code or hardware evidence |
| `ASSUMPTION` | Engineering guess, explicitly not evidence |
| `UNVERIFIED` | Claimed somewhere, no supporting bytes/hash |
| `BLOCKED` | Cannot be attempted safely yet, with a named blocker |

---

## 1. Round anchor: gate receipt

| Gate | Observable | Observed this round? | Result | Source / evidence | First blocker downstream |
|---|---|---|---|---|---|
| KERNEL_PROBE | modem dmesg probe of S5000AP, `shm_ipc` map PASS, `/dev/umts_*`, `rmnet0..7` | yes | **PASS (probe only)** | `journalctl -k -b`, 2026-11-23T00:46:28Z: `mif: modem_probe: 10000.mif_pdata: +++`, `create_modemctl_device: s5000ap is created!!!`, `shmem<->s5000ap: LINK_ATTR_SBD_IPC`, `CP memory map verification: PASS!` | — |
| CP_FIRMWARE_VERIFIED | a hash-verified signed CP image accepted by the kernel | yes (absence observed) | **FAIL / UNKNOWN** | `/var/lib/nuxel/modem/` did not exist; `/var/lib/nuxel/modem/cp-firmware-verified.json` absent; no receipt anywhere in the repo; `mobile.md` CP archive is **not** present under `/Users/wicked/x/nuxel`. Class: `DOCUMENTED_ONLY` (acquired per document), `UNVERIFIED` (no hash) | none yet — cannot start |
| CBD_ABI_MATCHED | built `cbd` whose ioctl/struct set matches the pinned kernel | no | **BLOCKED (no `cbd`)** | Policy candidates `/usr/bin/cbd`, `/usr/local/bin/cbd`, `/usr/libexec/nuxel/cbd` all absent on device | — |
| CP_ONLINE | `IOCTL_MODEM_STATUS` returns `STATE_ONLINE` | **yes** | **FAIL: `OFFLINE (0)`** | `/var/tmp/nuxel-cp-status.host /dev/umts_boot0` → `{"state":"OFFLINE","state_code":0,"errno":0,"errno_name":"0","ts":"2026-11-23T01:34:50Z"}`; reproduced 4× until 01:35:20Z; deployed `/usr/local/bin/nuxel-cp-status` at 01:35:11Z gave the same | **cp_status: OFFLINE** |
| RFS_AND_SIPC_RESPOND | a real IPC/RFS transaction | not reachable | **UNKNOWN** | CP OFFLINE ⇒ no transaction attempted (policy: no control commands to an un-booted CP) | CP offline |
| SIM_READY | SIM readable via a proven source | not reachable | **UNKNOWN** | `/var/lib/nuxel/modem/sim.json` absent; `mmcli -L` → "No modems were found"; no `/sys/class/sim` | CP offline |
| REGISTERED | real carrier registration | not reachable | **UNKNOWN** | no modem object; signal/registration never printed | CP offline |
| DATA_BEARER | PDP context with an IP | not reachable | **UNKNOWN** | `rmnet0..7` exist, `state DOWN`, `link/ppp`, no IP | CP offline |
| VERIFIED_RMNET_INTERNET | HTTPS via rmnet with wlan down | not reachable | **UNKNOWN** | no bearer | CP offline |
| SMS / VOICE / IMS | carrier end-to-end | not reachable | **UNKNOWN** (not attempted; no consent-gated test, carrier plan) | — | CP offline |

The state machine now reflects this exactly: the live diag's `first_failing_stage` is **`cp_status`**, not `modemmanager_plugin`.

---

## 2. Live software versions and safety hashes

Timestamp family: `2026-11-23T01:23:56Z … 01:35:20Z`, all from `ssh root@<device>` over the owner's ZeroTier link, which runs on the physical SM-G975F behind a hostname that reads `WIN-CLIENT`. Hardware identity is asserted from the cmdline (`androidboot.em.model=SM-G975F`, serial and bootloader redacted, `androidboot.revision=26`) and from `/proc/device-tree/model = Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820`.

| Fact | Value | Class |
|---|---|---|
| Kernel release | `4.14.253-gf7194c1d15ed-dirty` | `PROVED_LIVE` |
| Kernel build | `#1 SMP PREEMPT Mon Nov 23 00:43:30 CET 2026`, `gcc 15.2.0` | `PROVED_LIVE` |
| Board | `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820` | `PROVED_LIVE` |
| Kernel config (running) | `CONFIG_SEC_SIPC_MODEM_IF=y`, `CONFIG_SEC_MODEM_S5000AP=y`, `CONFIG_LINK_DEVICE_SHMEM=y`, `CONFIG_UMTS_MODEM_S5000AP=y`, `CONFIG_CP_SECURE_BOOT=y`, `CONFIG_CP_DIT=y`, `CONFIG_CP_PKTPROC=y`, `CONFIG_CP_RAM_LOGGING=y` | `PROVED_LIVE` via `/proc/config.gz` |
| Kernel config (source) | same flags in `kernel/s10plus/.build/src.polluted.case-insensitive/drivers/misc/modem_v1/` | `SOURCE_ONLY` (matches) |
| ModemManager | `1.24.2` (`mmcli -L` → "No modems were found") | `PROVED_LIVE` |
| systemd | `is-system-running` = `running`, `systemctl --failed` = none | `PROVED_LIVE` |
| Network | `wlan0` default route (LAN IP redacted), `usb0` up, ZeroTier up | `PROVED_LIVE` |
| Uptime at start | `up 1:37`, load 12.1 (busy host; not modem related) | `PROVED_LIVE` |
| `/dev` CP nodes on device | `umts_boot0`, `umts_cass`, `umts_csd`, `umts_dm0`, `umts_ipc0`, `umts_ipc1`, `umts_ramdump0`, `umts_rfs0`, `umts_router` — **no** `/dev/cbd*`, `/dev/gsmtty*`, `/dev/wwan*` | `PROVED_LIVE` |
| rmnet state | `rmnet0..7` exist, all `state DOWN`, `link/ppp` (not the `rmnet` ARPHRD you'd see on a live bearer) | `PROVED_LIVE` |
| Deployed BOOT sha256 | `1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599` | `CAPTURED_LIVE_OLDER` (SSP-05_14 receipt, 23:47Z) |
| Embedded DT payload | not independently re-read this round (no `/dev/block/by-name`, `/dev/disk/by-partlabel/*` empty, `/boot` empty); DTBO not touched | **UNKNOWN this round** — baseline still the SSP-05_14 receipt (`dtb sda12 abc9d45d…`, `dtbo sda13 de3bc025…`, unchanged) |
| `/tmp/nuxel-boot` / `evidence/…/boot-0028` | 780 bytes? no: both are full 57,671,680-byte images; the 0028 file sha256 = `760c0e44ca5cdac9d0ce3b4721fae2f734ab99f03b70039faf23a78171620f1a` | `CAPTURED_LIVE_OLDER` |
| Host snapshot of the "deployed" image | `evidence/pwnage-ssp-05_14/boot-0029-candidate.img` sha256 = `1be1ded8…` (matches the receipt) | `CAPTURED_LIVE_OLDER` |
| `tools/s10plus/verify-boot-image.py` | The release-gate parser is present and exercised by `boot/s10plus/tests/test-boot-image-gates.sh` | `OFFLINE_TESTED` |

**Key honesty note:** With `/dev/disk/by-partlabel` empty on this kernel and `/dev/block/by-name` absent, the BOOT/DT payload cannot be re-read from the live partition without touching the raw `sda14` device — which this round declined to do. The **BOOT hash above is the last verified receipt, not a fresh read**. The round's actions did not change BOOT, DT, DTBO, kernel or recovery.

---

## 3. Files / commits studied, and the real first failing gate

### Git reconciliation

* `git rev-parse HEAD` → `9281b6f51964e9d1374b9d19d736a5e69ad6617c` on `cs/mob`.
* `git status --short` at start: `D pwn-mobile/{00,01,AUDIT,N UXEL…zip}` (deleted from worktree but tracked in HEAD) and `?? pwn-mob/` (the same 3 files + an extra `FILE_MANIFEST.json`/`README.md`/prompts, byte-identical to the tracked files).
* `22dd6b3a` (`feat/mob`) is present in history but is **not** an ancestor of `HEAD`; 39 commits ahead. `reports/S5000AP-RADIO-ENDGAME.md` exists **only** on `feat/mob` (`git ls-tree feat/mob reports | grep S5000AP` is non-empty, HEAD has none). `reports/S5000AP-RADIO-FINAL-RECOVERY.md` does not exist in **any** ref.
* `packs/mobile/` does not exist in HEAD or in any ref that this round checked. No `nuxel-ds-ssp*.zip` in `/Users/wicked/x/nuxel`.

### Files studied this round

| File | Class | What it says |
|---|---|---|
| `pwn-mob/00_MASTER_SAFETY_AND_TRUTH.md` | `DOCUMENTED_ONLY` | Mission contract; matches the prepended master contract |
| `pwn-mob/AUDIT_REPORT.md` | `DOCUMENTED_ONLY` | The archived audit; lists the exact concerns this round fixed (diagnostic priority, SIM false-positive, calliope mislabel, flash denylist gaps, TWRP contradiction) |
| `pwn-mob/01_LIVE_RECONCILIATION.md` | `DOCUMENTED_ONLY` | This round's plan |
| `hw/NUXEL_06_S5000AP_CELLULAR_STANDALONE.md` | `DOCUMENTED_ONLY` | Earlier 6-prompt mission |
| `mobile.md` | `DOCUMENTED_ONLY` | Latest mission: CP archive at `/Users/wicked/x/nuxel/SAMFW…CP_G975FXXS9DTK9…tar.md5`, root deliverable `reports/S5000AP-RADIO-FINAL-RECOVERY.md` |
| `docs/Samsung S5000AP - Exynos 9820 Native Linux Modem Bring-up for Nuxel.md` | `SOURCE_ONLY` | Architecture, ioctl set, "Calliope trap" |
| `kernel/s10plus/.build/src.polluted.case-insensitive/drivers/misc/modem_v1/*` | `SOURCE_ONLY` | **The real modem_v1 checkout this round used.** `modem_prj.h` has `#define IOCTL_MODEM_STATUS _IO('o', 0x27)`; `modem_io_device.c` handles it and returns `mc->phone_state`; `enum modem_state` has `STATE_OFFLINE=0 … STATE_CRASH_WATCHDOG=9` |
| `configs/nuxel/modem/modem.json` | previously `SOURCE_ONLY`; now `OFFLINE_TESTED` + `PROVED_LIVE` (installed) | Rewritten as described in §4 |
| `tools/s10plus/a33/nuxel-modem-diag.sh` | now `OFFLINE_TESTED` + `PROVED_LIVE` (deployed) | Rewritten start-to-finish state machine |
| `boot/s10plus/flash.sh`, `scripts/nuxel-adb-flash-pack/scripts/nuxel_adb_flash.py` | `SOURCE_ONLY` → `OFFLINE_TESTED` | Denylist audited and tightened |
| `firmware/s10plus/manifest.yml` (`modem_dsp`) | `DOCUMENTED_ONLY` | **Mislabel confirmed:** `calliope_*` are declared `Shannon/Calliope modem DSP` but the boot journal shows `samsung-abox 18c50000.abox: Direct firmware load for calliope_sram.bin` → these are ABOX/audio DSP, not the S5000AP cellular CP |
| `configs/s10plus/modem/README.md` | `DOCUMENTED_ONLY` | Claims the "no upstream MM plugin" IS the blocker — **wrong layer**; the first blocker is CP OFFLINE |

### The real first failing gate

**`cp_status` = `OFFLINE`.** Proven live this round:

```
/var/tmp/nuxel-cp-status.host /dev/umts_boot0
{"node":"/dev/umts_boot0","state":"OFFLINE","state_code":0,
 "errno":0,"errno_name":"0","ts":"2026-11-23T01:34:50Z"}
```

The shipped diag now reports that as `first_failing_stage: "cp_status"`, `state: "BLOCKED_FIRMWARE"`. The former "no Shannon ModemManager plugin" verdict was a phantom; a generic plugin — even if installed — cannot help a CP that is not booted.

---

## 4. Smallest source changes made (this round)

### 4.1 `tools/s10plus/a33/nuxel-modem-diag.sh` — state machine corrected

- `verdict()` removed and replaced by a per-stage probe chain matching the contract:
  `host_present → cp_status → firmware_candidate_verified → cbd_available → cp_boot_completed → ipc_responsive → rfs_responsive → sim_ready → registered → bearer_connected → rmnet_verified`.
- `CP_STATUS` is read **only** by `IOCTL_MODEM_STATUS` on `/dev/umts_boot0` opened `O_RDONLY` by a separate, owner-installed read-only binary (`nuxel-cp-status`); never by a JSON fixture, a plugin's existence, `rmnet` state, an old report, or a service status.
- `CP_BOOT_COMPLETED` derived only from the observed state (`ONLINE|SIM_ATTACH|SIM_DETACH`).
- SIM: `mmcli -L` listing a modem **never** sets SIM ready. Real `mmcli -m <n>` → `mmcli -i <sim>` must report `state: ready`; otherwise `unknown`/`no`, not `present`.
- State file: requires a **fresh** `mtime` (`state_file_max_age_s`), and is `unknown` on stale/malformed, not silently coerced.
- JSON gains `host_present, cp_status, cp_status_source, firmware_candidate_verified, cbd_available, cp_boot_completed, ipc_responsive, rfs_responsive, sim_ready, sim_source, sim_age_s, registered, bearer_connected, rmnet_verified`; all old fields preserved. `signal_quality/operator/registration_state` stay `null` unless sourced from a live API.
- `selftest` now asserts arbitrary `KEY=VALUE` lines per fixture, not just `state=`.
- Bug surfaced and fixed during deployment: an `awk` filter on the probe path wrongly rejected a real `/usr/local/bin/nuxel-cp-status`; replaced by an exact `case` whitelist. A second fix made the fixture probe whitelist **strict** on a live root, so a mock binary can never be reached in production.

### 4.2 `tools/s10plus/a33/cp-status/nuxel-cp-status.c` — NEW read-only probe

- 4-line ABI: `_Static_assert(NUXEL_IOCTL_MODEM_STATUS == 0x6f27)` and `_Static_assert(STATE_OFFLINE==0 && STATE_ONLINE==4 && STATE_CRASH_WATCHDOG==9)` — both pin the encoding and the enum ordering to this kernel, so a header drift fails the **build** rather than mislabelling the state.
- Opens `O_RDONLY | O_CLOEXEC | O_NOCTTY | O_NONBLOCK`, takes `LOCK_SH|LOCK_NB`, calls exactly one `ioctl` (`IOCTL_MODEM_STATUS`), closes, prints a single JSON object with `state`, `state_code`, `errno`, `errno_name`, `ts`.
- No `write()`, `O_RDWR`, `O_WRONLY`, reset, boot-on/off/done, download, xmit, RFS, SIPC, AT, mmap, or block-device access.
- Portable `strerrorname_np` (glibc >= 2.32) with a numeric fallback.
- Built:
  - host cross-compiled statically: `aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static` → `840a10406ff4989fa7b0319fc1e157ccc37b8679ddf05045699d6fbb73fc1f75`
  - device build: `gcc -O2 -Wall -Wextra -Werror` produced an equivalent AArch64 ELF; static linking failed only because the device lacks `libc.a` outside a vendor toolchain.

### 4.3 `configs/nuxel/modem/modem.json` — semantics fixed, not weakened

- `comment`: states the new gate ordering, that `cp_status` (CP OFFLINE) is the first real blocker, and that a missing Shannon MM plugin is a later hop.
- New sections: `cp_status` (device node, ioctl, enum), `firmware` (verified-receipt path, `calliope_*` explicitly forbidden as CP firmware — with the boot-journal reason), `cbd` (candidate list, "presence ≠ boot proof").
- `sim.comment` declares "a listed modem is NOT a ready SIM"; `state_file_max_age_s=3600`.
- `protected_partitions.never_read_or_write` gains `radio`, `radiobak`, `dtbo`, `vbmeta` (strict superset; no item removed).
- `protected_partitions.comment` names the **narrow** owner-authorized BOOT/OS repair scope and says explicitly that it does not authorize modem/efs/radio/efs-family writes (the previous README/JSON contradiction is now documented with a precise boundary rather than a global weakening).

### 4.4 `scripts/nuxel-adb-flash-pack/scripts/nuxel_adb_flash.py` — denylist tightened

- `DENY` now includes every name in `configs/nuxel/modem/modem.json#protected_partitions.never_read_or_write` (it was missing `efsg`, `radiobak`, `up_param`, `steady`, `carrier`, `cp_debug`).
- `startswith(...)` family cover extended to `efs_`, `efsg_`, `sec_efs_`, `radio_`, `radiobak_`, `persist_`, `param_`, `up_param_`, `misc_`, `carrier_`, `cp_debug_`.
- `boot_only` is `is True` in the local (already the case) and the default-rootfs fallback is gone when a truthy non-bool value is supplied by a broken caller.
- `MANIFEST.sha256` refreshed for the changed file (the test-manifest check now passes from the pack root).

### 4.5 Fixtures + tests

- New fixtures under `tools/s10plus/a33/tests/hw-subsystems/fixtures/`: `modem-cp-offline`, `modem-cp-booting`, `modem-cp-online-noipc`, `modem-sim-unknown`, `modem-no-bearer`, `modem-mm-modem-no-sim`, `modem-fake-signal`; existing `modem-cp-only`, `modem-nosim`, `modem-ready` rewritten to represent the **new** chain truthfully (and each `EXPECTED` states multiple keys, e.g. `first_failing_stage=cp_status`).
- `tools/s10plus/a33/tests/hw-subsystems/test-modem-diag.py` rewritten. It now asserts:
  - chain shape and every stage's fields for every fixture,
  - **CP OFFLINE ⇒ `first_failing_stage=cp_status`, never `modemmanager_plugin`** (and a negative control that the old shape would fail),
  - **stale SIM file + CP OFFLINE ⇒ `sim_ready=unknown`** (negative control),
  - **`mmcli -L` listing a modem ⇒ `sim_ready=unknown`** (negative control),
  - **a helper that prints signal/operator cannot leak into JSON** (negative control),
  - **true `present:false` ⇒ `sim_ready=no`** (real negative must surface, not hide),
  - **CP probe source ABI**: `_IO('o',0x27)==0x6f27`, `ONLINE==4`, `CRASH_WATCHDOG==9`, `O_RDONLY` in `open`, no `O_WRONLY|O_RDWR|IOCTL_MODEM_ON|...|/dev/block|efs|mmap(`, and the only `ioctl(fd, …)` is `IOCTL_MODEM_STATUS`.
- New `tools/s10plus/tests/test-flash-preflight-offline.py`: drives `select_parts` for **every** high-risk boot/rootfs target (`modem`, `radio`, `dtbo`, `bootloader`, `vbmeta`, `efs`, `sec_efs`, `persist`, `param`, `misc`, `recovery`, `sboot`, `abl`, `xbl`, `tz`, `hyp`, `cm`, `keystorage`, `keydata`, `frp`, `super`, `dtb`, plus `_a` family variants), asserts s10plus-confine, asserts boot_only, asserts shell `PROTECTED_PARTITIONS` covers the policy, asserts **policy denylist ⊆ python DENY**, asserts the shell flasher has no `--dtbo/--modem/--radio/--efs` write path, and runs `boot/s10plus/flash.sh --help` (no device access). No adb call is made by this test.

### Verified build/test commands and results (offline, this round)

```
bash -n tools/s10plus/a33/nuxel-modem-diag.sh                   → SYNTAX_OK
python3 -c 'import json;json.load(open("configs/nuxel/modem/modem.json"))' → JSON_OK
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static -o … nuxel-cp-status.c → BUILD_OK
bash tools/s10plus/a33/nuxel-modem-diag.sh selftest              → 11/11 PASS
python3 tools/s10plus/a33/tests/hw-subsystems/test-modem-diag.py → all checks PASS
python3 tools/s10plus/tests/test-flash-preflight-offline.py      → all checks PASS
python3 scripts/nuxel-adb-flash-pack/tests/test_flashing.py      → 18/18 OK
shasum -a 256 -c scripts/nuxel-adb-flash-pack/MANIFEST.sha256    → all OK
```

Pre-existing failures checked and identified as **not** caused by this round (reproduced on the untouched HEAD tree):

- `test-bluetooth-diag.py` (5 checks), `test-power-diag.py` (1 check), `test-led-diag.py` (1 check) — these belong to the SSP/camera round, not to modem.

---

## 5. Staged files, exact installations, rollback, flash declaration, recovery receipt

### Installations completed this round (userspace only)

| Installed file | Hash before | Hash after | Rollback receipt |
|---|---|---|---|
| `/usr/local/bin/nuxel-cp-status` | *(did not exist)* | `840a10406ff4989fa7b0319fc1e157ccc37b8679ddf05045699d6fbb73fc1f75` (0755, static AArch64) | remove the file |
| `/etc/nuxel/modem/modem.json` | `a1921afb8cdaab652ed238095138655735708d9f36c0994d8a7d956530686116` | `4303d5c6edc35ed933e129cb33c5139837ac3965f6af87dd6623e289205d8fac` (0644) | `/var/lib/nuxel/rollback/s5000ap-01-20261123T013410Z/modem.json.pre` = `a1921afb…` |
| `/usr/local/bin/nuxel-modem-diag.sh` | `ab4d8aa1c80bd599d9043917571c541e270b771fdd5119dd0311abc66378bcea` | `ef6cc3a78233f3cd733030dd15eddae97383b75691e1982475cf537cc1f6adee` (0755) | `/var/lib/nuxel/rollback/s5000ap-01-20261123T013429Z/nuxel-modem-diag.sh.pre` = `ab4d8aa1…` and an earlier `/var/lib/nuxel/rollback/s5000ap-01-20261123T013410Z/nuxel-modem-diag.sh.pre` |

Every installation followed the mission's hash discipline: host `sha256sum` → SCP → on-device `sha256sum` → exact-match assert **before** `mv` (atomic rename, no partial file). Two intermediate rollback directories exist precisely because the first diag upload used an `awk` filter that wrongly rejected the installed probe; the second is the final one. Restoring any of them reverts to the previous state; `rm /usr/local/bin/nuxel-cp-status` reverts the probe.

### Flash declaration

**NONE.** No BOOT, DT, DTBO, partition, bootloader, EFS/NV, or userdata write was performed this round. Recovery state: not entered, not changed. Pre-existing history: the last real flash was SSP-05_14 (0029 candidate to `sda14`, receipt as above, `CAPTURED_LIVE_OLDER`).

### Unrelated state noticed but not touched

- `pwn-mobile/*` were deleted in the working tree and replaced by `pwn-mob/*` (identical bytes). They are not staged by this round (they'd obscure the diff) and remain `git`-visible as deletions/untracked. The new `pwn-mob/` was deliberately not committed either: the mission wants only safe corrections to be committed; the prompt pack is the owner's input.

---

## 6. Hardware evidence vs. simulation (separated)

| Claim | Hardware? | Simulation? |
|---|---|---|
| `cp_status = OFFLINE (0)` | **yes**, on `/dev/umts_boot0`, `IOCTL_MODEM_STATUS` via `nuxel-cp-status`, `PROVED_LIVE` | fixtures also model OFFLINE to prove the state machine never calls it "plugin" |
| KERNEL_PROBE truth (shmem map, node creation) | **yes**, boot journal this boot | — |
| `rmnet0..7` exist and are down | **yes** | — |
| `mmcli -L` → no modems | **yes** | — |
| Signal / operator / registration | **never observed** | `null`, and the fixtures show a helper printing signal cannot leak into JSON |
| SIM presence/readiness | **never observed** (no state file, no modem, no sysfs) | stale-file and "mmcli -L but no SIM object" fixtures assert `unknown` |
| CBD ABI, RFS, SIPC responsiveness, PDP bearer | **not attempted** (CP offline) | — |
| BOOT / DT | last `CAPTURED_LIVE_OLDER` receipt only; NOT re-read this round | — |
| Calliope = ABOX | **yes** (boot journal `samsung-abox 18c50000.abox` requests `calliope_sram*.bin`) | fixed policy/fixtures assume this and prohibit use as CP firmware |

A PASS in the offline suite is `OFFLINE_TESTED`; it is **not** a phone capability. No file existence, plugin presence or interface creation was promoted.

---

## 7. User capability matrix

| Capability | LTE data | SMS | Voice | IMS/VoLTE |
|---|---|---|---|---|
| **Status** | **BLOCKED** | **BLOCKED** | **BLOCKED** | **BLOCKED** |
| Why | CP OFFLINE (`PROVED_LIVE`); firmware unverified; no `cbd`; no RFS/SIPC; no SIM; no registration; no bearer | same CP gate | same CP gate | same CP gate + no IMS implementation |
| Not-yet-observed pieces | firmware hash receipt, `cbd` ABI, CP ONLINE, IPC/RFS, SIM, registration, PDP | — | — | — |

Wi-Fi / SSH / USB remain **PASS** (proved live this round: wlan0 route, usb0, ZeroTier). Nobody can claim "100%" without a CP online, a real registered carrier and an HTTPS check over rmnet with Wi-Fi disabled.

---

## 8. Next highest-value task and exact blocker

**Highest-value next task.** Turn `firmware_candidate_verified` and `cbd_available` into real evidence in **offline** form: obtain the owner's matching CP archive (`/Users/wicked/x/nuxel/SAMFW…CP_G975FXXS9DTK9…tar.md5`), hash the archive and the `modem.bin.lz4` / `modem_debug.bin.lz4` members, extract `modem.bin` in an owner-local directory **outside Git**, record the decompressed sha256, then build the exact matching `cpboot_v3` `cbd` pinned to a LineageOS revision whose ABI is diffed against this kernel (`modem_prj.h`/`modem_io_device.c`) — and only then produce one signed owner-authorization manifest.

**Exact blockers to that task, all observable:**

1. The CP archive **does not exist** at the documented path in this worktree, and no hash receipt for it exists anywhere in HEAD, `feat/mob`, or `reports/`. `firmware_candidate_verified` therefore remains `unknown`.
2. `cbd` source (`cpboot_v3`) is not in the repository and not pinned. `cbd_available = absent`.
3. The device is CP OFFLINE, so none of `ipc_responsive`, `rfs_responsive`, `sim_ready`, `registered`, `bearer_connected`, `rmnet_verified` can be observed without a real, owner-authorized CP boot — which this round is not authorized to do.
4. Even after CP ONLINE, the RFS/SIPC control dictionary is **not** in the repository (the kernel only gives you the transport and framing). `nuxel-radiod` (or an isolated vendor RIL) must be written against a real transaction, not guessed. `MM`/`NetworkManager` come only after that.

Nothing above requires a DT, kernel-config or BOOT mutation. The DT fence remains intact: no DTB/DTBO/DTS/DTC/overlay/fdtput/repack was touched, and no kernel config or patch was applied this round.

---

## 9. Discrepancy / drift table (reported, not silently resolved)

| # | Claim / artifact | Where it is claimed | Fresh evidence this round | Class | Action in this round |
|---|---|---|---|---|---|
| 1 | "A missing ModemManager plugin is the blocker" | `configs/s10plus/modem/README.md`, `configs/nuxel/modem/README.md`, old `verdict()` | CP is **OFFLINE** on `IOCTL_MODEM_STATUS`; `mmcli -L` no modems is a **downstream** symptom | old: `DOCUMENTED_ONLY`, now `PROVED_LIVE` opposite | `verdict()` reordered; both READMEs left in place for a follow-up (only code was committed) |
| 2 | `first_failing_stage` = `modemmanager_plugin` | installed diag before 2026-11-23T01:35Z | installed diag now reports `cp_status` | fixed live | kept backward-compatible key names, changed the value to the truth |
| 3 | `mmcli -L` proves SIM present | old `enumerate()` | `mmcli -L` is only a modem **object** list; this device has no modems and no SIM | fixed in code and tested | `probe_sim` matches `SIM/<n>` then `mmcli -i <n>` must say `ready` |
| 4 | `calliope_*` are "Shannon/Calliope modem DSP" | `firmware/s10plus/manifest.yml` lines 351–375 | boot journal `samsung-abox 18c50000.abox: Direct firmware load for calliope_sram.bin` | mislabel confirmed | policy `firmware.must_not_use_as_cp_firmware` now lists them; **manifest itself is not edited** (outside this round's scope; flagged for a dedicated firmware round) |
| 5 | flash pack blocks every high-risk partition | `scripts/nuxel-adb-flash-pack/scripts/nuxel_adb_flash.py` `DENY` | 6 names in the policy denylist were not blocked (`efsg`, `radiobak`, `up_param`, `steady`, `carrier`, `cp_debug`) | real gap | closed; `MANIFEST.sha256` refreshed; offline test proves policy ⊆ `DENY` |
| 6 | TWRP is forbidden outright | `configs/nuxel/modem/modem.json` `flashing_tools_forbidden` + `configs/nuxel/modem/README.md` ("Heimdall/Odin/…/TWRP are on the denylist") | owner explicitly permits reviewed TWRP BOOT-only repair | contradiction | comment + policy scope note added: TWRP is forbidden **for modem**; BOOT-only repair is separate and explicitly bounded. No policy entry removed |
| 7 | `/dev/block/by-name/{boot,modem}` exists | multiple reports | On this running kernel, `/dev/block/by-name` doesn't exist; `/dev/disk/by-partlabel` also empty; `/dev/block/platform/*/by-name` empty | `PROVED_LIVE` correction | not used by any new code; CP probe targets `/dev/umts_boot0`, not block devices |
| 8 | `reports/S5000AP-RADIO-ENDGAME.md` is "the authoritative report" | `mobile.md` | It exists only on `feat/mob`; HEAD has no such file | ref | read from `feat/mob` this round; not committed (it's a `feat/mob` artifact) |
| 9 | `reports/S5000AP-RADIO-FINAL-RECOVERY.md` | `mobile.md` "required deliverable" | Never existed in any local ref this round | UNVERIFIED | not produced in round 01; this file is the round-01 report |
| 10 | `pwn/mobile*.md` | prompt pack mentions it | does not exist; `pwn/` only has ssp files | absence confirmed | reported, not fabricated |
| 11 | `packs/mobile/` exists | audit + old prompt | does not exist | absence confirmed | not recreated |
| 12 | `.git` omitted from the uploaded ZIP | prompt pack | `.git` **does** exist and reconciled | resolved | history preserved; no reset |

The old BOOT+DT chain is intact; `git log --all --oneline -- reports/S5000AP-RADIO-ENDGAME.md` shows only `feat/mob`-related commits, so no newer conflict exists there.

---

## 10. Per-round mandatory reply (contract §7)

1. **HEAD/branch/clean state:** `cs/mob` @ `9281b6f5…`, worktree **dirty** with exactly this round's source edits plus the pre-existing `pwn-mobile`→`pwn-mob` move. Live kernel `4.14.253-gf7194c1d15ed-dirty`, BOOT `1be1ded8…` (`CAPTURED_LIVE_OLDER`, not re-read), CP **OFFLINE (0)** (`PROVED_LIVE` 2026-11-23T01:34:50Z, reproduced to 01:35:20Z).
2. **Files / first failing gate:** studied `pwn-mob/*`, `mobile.md`, `hw/NUXEL_06…`, the pinned `kernel/s10plus/.build/.../modem_v1`, `reports/SSP-05_14-*`, `feat/mob` `S5000AP-RADIO-ENDGAME.md`, the two flash scripts, the manifest. **First failing gate = `cp_status` = OFFLINE.**
3. **Small changes + verified build/test:** `nuxel-cp-status.c` (new), `nuxel-modem-diag.sh` (state machine), `modem.json` (policy), `nuxel_adb_flash.py` (denylist) + `MANIFEST.sha256`, 10 fixtures, two test files. All build/test commands listed in §4 pass; pre-existing unrelated failures disclosed.
4. **Staged/installed/rollback/flash:** 3 userspace files installed with hash preflight and rollback receipts under `/var/lib/nuxel/rollback/s5000ap-01-*`; **no flash**, no BOOT/DT/DTBO/partition write, recovery not entered.
5. **Hardware vs simulation:** §6. OFFLINE is hardware; suite results are `OFFLINE_TESTED`.
6. **Capability matrix:** §7 — LTE/SMS/Voice/IMS each **BLOCKED**.
7. **Next task and blocker:** §8 — hash-verified CP image + exact pinned `cbd`, then an owner-authorized first CP boot. Blockers: no CP archive in tree, no pinned `cbd`, CP OFFLINE, RFS/SIPC dictionary unverified.

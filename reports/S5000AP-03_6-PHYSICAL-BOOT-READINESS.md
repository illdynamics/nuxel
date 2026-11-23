# S5000AP — Prompt 03.6: Physical Boot Readiness (Gate E)

**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4` (unchanged)
**Round window:** `2026-11-23T04:05Z` → `04:30Z` (host CET)
**Actions:** READ-ONLY ONLY (SSH probes, `IOCTL_MODEM_STATUS` read, `blkid`/`lsblk`,
bounded read-only partition hashes of `sda12/13/14/15` and RADIO metadata). No flash,
no reboot, no CP action, no DT change.

---

## 1. Fresh recovery baseline (PROVED_LIVE this round)

| Fact | Value | Status |
|---|---|---|
| Physical model | `SM-G975F` / `beyond2lte` / Exynos9820, `revision=26` (`WIN-CLIENT`) | PROVED_LIVE |
| Kernel | `4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT` | PROVED_LIVE |
| systemd | `running`; `--failed` = none | PROVED_LIVE |
| CP status | `OFFLINE (0)` via read-only `IOCTL_MODEM_STATUS` | PROVED_LIVE (03:11:35Z, 03:12:40Z) |
| `/dev/umts_*` | `boot0 cass csd dm0 ipc0 ipc1 ramdump0 rfs0 router` all `crw------- root root` | PROVED_LIVE |
| Competing cbd/rild | none | PROVED_LIVE |
| Modem kernel faults | only benign `mif: misc_open/release` probe lines + unrelated watchdog keepalive | PROVED_LIVE |

## 2. Device-tree immutability fence — VERIFIED live (fresh)

| Partition | PARTLABEL | Fresh SHA-256 (read-only) | Baseline | Verdict |
|---|---|---|---|---|
| `sda12` | dtb | `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780` | same | unchanged |
| `sda13` | dtbo | `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23` | same | unchanged |
| `sda14` | boot | `1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599` | 0029 known-good | match |
| `sda15` | recovery | `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87` | same | unchanged |

No DTS/DTB/DTBO/DTC/overlay/fdtput/repack performed. DT fence intact.

## 3. Network / recovery route

`wlan0` default route 10.20.30.16, ZeroTier `ztly5zthnf` (10.11.12.99), `usb0`
(10.100.10.1, linkdown), `sdb/sdc/sdd/sde` additional storage present. Wi-Fi was NOT
disabled (sole management route preserved). USB/TWRP recovery partition `sda15`
hash-matches baseline.

## 4. Known-good BOOT rollback (host, re-confirmed present)

`boot-0029-candidate.img` = `1be1ded8…` (== live sda14), plus `boot-0028` `760c0e44…`
and `boot-0020…` `9805d519…`. All valid `ANDROID!`-magic 57,671,680 B images.

## 5. Installed RADIO identity (NEW — resolves a prior gate-A4 blocker)

`blkid` → `sda16` = `radio` (52,428,800 B), contents `G975FXXSEFUJ2_CL2054966_Q
B20745891` / `SM-G975F_EUR_XX_EUR0` (valid ITOC). **The installed RADIO is EFUJ2, a
different build than the DTK9 candidate.** See INSTALLED-RADIO-IDENTITY report.

## 6. Preflight verdict

**Gate E (recovery readiness) = PASS** — freshest possible before a trial, all four
BOOT/DTB/DTBO/recovery hashes match baseline, DT-immutability live-verified, CP
OFFLINE, no competing owner, network/USB/TWRP intact, known-good rollback present.

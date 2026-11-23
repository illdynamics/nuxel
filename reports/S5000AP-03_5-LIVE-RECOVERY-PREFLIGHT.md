# S5000AP — Prompt 03.5: Live Recovery Preflight (Blocker E)

**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4`
**Round window:** `2026-11-23T03:41Z` (live probes) vs device journal timestamps ~1 h
earlier (device clock is UTC−0 heuristics; host is CET — noted, not assumed).

**Actions:** READ-ONLY. SSH `root@10.11.12.99` via owner key `~/.ssh/wicked_wqn_id_rsa`,
`IOCTL_MODEM_STATUS` read, and bounded SHA-256 of partitions already authorized in
prior BOOT-only receipts (`sda12/13/14/15` = dtb/dtbo/boot/recovery). No reboot, no
flash, no CP state change, no RADIO/EFS read/write.

---

## 1. Fresh hardware evidence (PROVED_LIVE this round)

| Fact | Value | Class |
|---|---|---|
| Physical model | `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820` | PROVED_LIVE |
| cmdline model | `androidboot.em.model=SM-G975F`, `androidboot.revision=26` | PROVED_LIVE |
| Kernel | `4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT Mon Nov 23 00:43:30 CET 2026` | PROVED_LIVE |
| systemd | `is-system-running` = `running`; `--failed` = none | PROVED_LIVE |
| CP status | `OFFLINE (0)` via `nuxel-cp-status /dev/umts_boot0` (read-only ioctl) | PROVED_LIVE |
| Kernel modem flags | `SEC_SIPC_MODEM_IF=y`, `SEC_MODEM_S5000AP=y`, `UMTS_MODEM_S5000AP=y`, `LINK_DEVICE_SHMEM=y`, `CP_SECURE_BOOT=y`, `LINK_DEVICE_PCIE` **not set** | PROVED_LIVE |
| `/dev/umts_*` | `boot0 cass csd dm0 ipc0 ipc1 ramdump0 rfs0 router` all `crw------- root root` (no group/other) | PROVED_LIVE |
| rmnet | `rmnet0..7` present, `state DOWN`, `link/ppp`, no IP | PROVED_LIVE |
| ModemManager | `mmcli -L` → "No modems were found" | PROVED_LIVE |

## 2. Immutable device-tree fence — VERIFIED live

| Partition | by-name | Fresh SHA-256 (read-only) | Baseline | Verdict |
|---|---|---|---|---|
| `sda12` | dtb | `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780` | same | **unchanged** |
| `sda13` | dtbo | `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23` | same | **unchanged** |
| `sda14` | boot | `1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599` | 0029 known-good | **match** |
| `sda15` | recovery | `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87` | same | **unchanged** |

No DTS/DTB/DTBO/DTC/overlay/fdtput/repack was performed. The DT fence is intact and
now independently re-verified on the live device.

## 3. Known-good BOOT backups (host, verified)

| Host path | Size | SHA-256 | Note |
|---|---|---|---|
| `evidence/pwnage-ssp-05_14/boot-0029-candidate.img` | 57,671,680 | `1be1ded8…` | == live `sda14` (deployed 0029) |
| `evidence/pwnage-ssp-05_12/boot-0028-candidate.img` | 57,671,680 | `760c0e44…` | prior known-good (0028) |
| `evidence/pwnage-ssp-05_9/candidate-boot-0020-0023-0025.img` | 57,671,680 | `9805d519…` | rollback (0020/23/25) |

All three `.img` files are valid `ANDROID!`-magic boot images and equal the exact
`sda14` partition size (56,320 × 1024 = 57,671,680). At least two independent
known-good copies exist on host (0029 live-matching + 0028 + 0020 alternatives).

## 4. Recovery route

- SSH over ZeroTier (owner key) functional. USB (usb0) noted as up in prior rounds.
- TWRP A-only recovery partition `sda15` hash matches baseline (bootable recovery).
- Rollback images present on host (§3). No protected-partition write performed or
  proposed by this round.

## 5. Network preservation plan (read-only confirmed)

wlan0 (default route), ZeroTier, and SSH were all observed functional; no RF/network
change was made. Wi-Fi was **not** disabled (sole management route preserved).

## 6. Preflight verdict

`**PASS**` for recovery/DT-immutability readiness against the actual device. The only
elements NOT verifiable this round are the installed RADIO identity (no partition
map on this boot) and firmware provenance (host-side, owner input) — both already
scoped to gates A/C, not E.

# S5000AP — Prompt 03.7: Live Safety Preflight (Gate E)

**Branch/HEAD:** `cs/mob` @ `ae26b271c144780abb748ce2fb172919abb1131d`
**Handset actions this round:** NONE. This is the offline reconciliation of the
frESHest available live evidence (round 03.6) plus the preflight *requirements*
for the Stage-04 trial. Fresh read-only re-measurement must be performed
immediately before Stage-04 (this document does NOT claim fresh measurements).

## 0. Fresh vs historical evidence

| Evidence | Class |
|---|---|
| Device model/rev, CP OFFLINE, `/dev/umts_*` perms, GPT labels, BOOT/DTB/DTBO/recovery hashes | **HISTORICAL live (round 03.6)** — baseline, not fresh truth this round |
| Wi-Fi/SSH reachable, USB/TWRP fallback | **HISTORICAL live (round 03.6)** |
| Kernel source @ `f7194c1d…`, cpboot_v3 @ `234b1387…` | **SOURCE (verified present this round)** |

## 1. Recorded baseline (from round 03.6; re-verify before trial)

- Model `SM-G975F` / beyond2lte / Exynos9820, `revision=26`.
- Kernel `4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT`.
- CP status `OFFLINE (0)` via read-only `IOCTL_MODEM_STATUS`.
- `/dev/umts_*` nodes `crw------- root root`. No competing cbd/rild. No modem crash.
- BOOT `1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599`
- DTB `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780`
- DTBO `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23`
- RECOVERY `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87`
- Host known-good: `boot-0029-candidate.img` == live BOOT (verified), plus `boot-0028`/`boot-0020`.
- RADIO `/dev/sda16` = EFUJ2 (identity in EFUJ2-SOURCE-AND-PROVENANCE report).

## 2. Stage-04 preflight requirements (to be executed then, read-only)

1. Fresh `IOCTL_MODEM_STATUS` == OFFLINE.
2. Re-hash BOOT/DTB/DTBO/recovery from the device; confirm == baseline.
3. Confirm Wi-Fi (management) + SSH + USB/TWRP route; preserve Wi-Fi through the trial.
4. Confirm no competing cbd/rild; verify `/dev/umts_boot0` ownership/rdev.
5. Stream/hash the EFUJ2 RADIO partition fresh; confirm GPT PARTLABEL `radio` == `/dev/sda16`.
6. Confirm no kernel modem fault/pstore warning before boot.
7. Confirm DT/DTBO unchanged (NO DTB/DTBO/DTS/overlay change is ever authorized).

## 3. Recovery status

Fresh re-verification is required, but the historical baseline shows a known-good,
independently-recoverable BOOT (`1be1ded8…` == host `boot-0029-candidate.img`) and
matching DTB/DTBO/recovery. No protected-partition write is part of the trial.
Recovery is via existing TWRP/ADB BOOT-only path (see `09_TWRP_A_ONLY_RECOVERY_AGREEMENT`).

## 4. Verdict

**Gate E = PASS (baseline verified historically; fresh re-measurement REQUIRED
immediately before Stage-04).** No physical CP action is authorized by this
document; the Stage-04 physical execution manifest remains in
`S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md` for owner review.

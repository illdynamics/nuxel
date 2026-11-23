# S5000AP — Physical CP Boot Proposal (Stage 04, immutable, EFUJ2)

**Status:** PROPOSAL ONLY — **NOT authorization**. Owner approval REQUIRED for this
exact manifest, in a separate interaction. Do NOT execute.
**TRIAL_ID:** `S5000AP-04-EFUJ2-<owner-approval-timestamp>`
**Branch/HEAD:** `cs/mob` @ `ae26b271c144780abb748ce2fb172919abb1131d`
**Prepared:** `2026-11-23` (Prompt 03.7 output)

> This is a **completely fresh** proposal selecting the **installed EFUJ2 RADIO**
> as the read-only source. It supersedes (not patches) the round-03.5 proposal that
> cited DTK9 section sizes and DTK9 provenance demands, and the round-03.6 header
> revision that still carried stale DTK9 body text.

## 1. Exact commit / build revisions

- Git HEAD: `ae26b271c144780abb748ce2fb172919abb1131d` (`cs/mob`).
- Kernel ABI pin: `f7194c1d15eded1c2a1a4dc63825b26103435cc0`.
- cbd source pin: `234b138716426c36ed801a71052bc144f7d8d806` (cpboot_v3, lineage-22.1).
- Loader source: `tools/s10plus/s5000ap-uapi/nuxel-cpbootd.c` (rewritten 03.7).

## 2. Physical device / recovery identity

- Model `SM-G975F` / beyond2lte / Exynos9820, `revision=26` (A-only, no slot).
- BOOT `1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599`
- DTB `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780`
- DTBO `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23`
- RECOVERY `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87`
- Host known-good: `boot-0029-candidate.img` (== live BOOT), plus `boot-0028`/`boot-0020`.
- **(Re-hash all four partitions fresh immediately before the trial; these are baseline.)**

## 3. Firmware source (EFUJ2) — identity + provenance + section table

- Source: `/dev/sda16`, GPT PARTLABEL `radio`, 52,428,800 B.
- Model `SM-G975F_EUR_XX_EUR0`, build `G975FXXSEFUJ2_CL2054966_QB20745891`.
- Full SHA256 (baseline) `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`.
- Provenance: physical + structural identity PASS; OEM archive/chain-of-custody UNKNOWN;
  secure-boot/TEE acceptance **`DEVICE_ACCEPTANCE_PENDING_04`** (only the trial can prove it).
- Section table (from EFUJ2 ITOC, parsed at runtime by `nuxel-cpbootd`): BOOT / MAIN /
  VSS / NV / OFFSET, with per-part `b_offset`, `m_offset`, `size`, `crc` read from the
  on-partition `TOC\0` container. **No DTK9 constants are used.**

## 4. Native executable (hardware-disabled default)

- Binary: `nuxel-cpbootd.aarch64.hw` (SHA-256 `2b630d4a8c7219c468a4aff94881029b23547d867f4f5a30898f080f2cb4fae7`).
- glibc AArch64 (interpreter `/lib/ld-linux-aarch64.so.1`, NEEDED `libc.so.6`).
- Compile-time gate `NUXEL_CPBOOTD_ENABLE_HW=1` (value-aware); runtime `--really-boot`
  + `--manifest-sha256 <immutable manifest>` + exact `/dev/umts_boot0`.

## 5. Canonical stage order (source-faithful, LEGACY_SIPC_IOCTL)

| # | Operation | ioctl / transport | Verified section | Expected | Deadline | Abort |
|---|---|---|---|---|---|---|
| 0 | STATUS probe | 0x6F27 | — | OFFLINE | — | rc<0 |
| 1 | SECURITY_REQ non-secure | 0x6F53 (RE_INIT=2,0,0) | — | SMC ok | 30 s | TEE error |
| 2 | XMIT_BOOT (BOOT/MAIN/VSS/NV) | 0x6F40 | EFUJ2 TOC parts | shmem copied | 30 s | bounds/rc<0 |
| 3 | SECURITY_REQ TOC | 0x6F53 (MANUAL=7) | TOC | SMC ok | 30 s | TEE error |
| 4 | SECURITY_REQ VSS (if present) | 0x6F53 (MANUAL=7) | VSS | SMC ok | 30 s | TEE error |
| 5 | SECURITY_REQ BOOT/MAIN | 0x6F53 (NORMAL=0) | BOOT/MAIN | SMC ok | 30 s | TEE error |
| 6 | POWER ON | 0x6F19 | — | AP2CP_CFG ok | 30 s | rc<0 |
| 7 | BOOT ON | 0x6F22 | — | cp_status polled | ~2 s | -EACCES |
| 8 | DL START | 0x6F28 | — | boot magic | 30 s | rc<0 |
| 9 | Handshake | SIPC UDL (0x9000/0xA000) | — | BOOT_DONE+FIN acks | 30 s | bad resp |
| 10 | BOOT OFF (COMPLETE_NORMAL_BOOTUP) | 0x6F23 | — | init_cmpl | 15 s | -EAGAIN |
| 11 | ONLINE verify | 0x6F27 | — | STATE_ONLINE(4) | — | not ONLINE |

## 6. End-to-end mock transcript

`nuxel-cpbootd --really-boot --mock --firmware <efuj2.itoc>` reaches
`{"verdict":"online","backend":"mock"}` passing every stage in the above order
(29 UAPI + 22 firmware tests green). No unimplemented or silently-skipped stage.

## 7. Operational constraints

- One-shot service, `Restart=no`, no timer/autostart, `TimeoutStartSec` hard cap.
- Exclusive owner via `flock(LOCK_EX|LOCK_NB)` + process/node ownership preflight.
- Wi-Fi (management) + USB preserved; no SIM required for first CP ONLINE proof;
  RF/network activity not assumed or claimed.

## 8. PASS criterion (verifiable)

**Real** `IOCTL_MODEM_STATUS` transitions to stable `ONLINE(4)` with kernel boot
confirm, repeated ≥2×. Standalone daemon activity / `rmnet` existence does NOT count.

## 9. Abort

On TEE refusal/error/unexpected state: process disabled, evidence preserved,
zero automatic retry/power-cycle. No protected-partition write. No DTB/DTBO change.

## 10. Recovery + boundary

Existing TWRP/ADB BOOT-only rollback; no DTB/DTBO modification. Clear boundary:
CP boot ends here; later SIPC/RFS/LTE work is Stage-05 and NOT authorization now.

## 11. Owner approval clause

Owner approval is requested for **this manifest only** — the exact EFUJ2 read-only
source, exact binary hash, exact stage list, exact abort/recovery plan. It is NOT an
open-ended hardware permission, and does NOT authorize any subsequent Stage-05
RFS/SIPC/RF/network activity.

## 12. Gate matrix

| Gate | Criterion | Result |
|---|---|---|
| A | EFUJ2 source identity + structural validation + defensible provenance/risk | PASS (TEE acceptance = `DEVICE_ACCEPTANCE_PENDING_04`) |
| B | Kernel ABI + controller match pinned source/live kernel | PASS |
| C | Complete, source-faithful, tested native bootstrap; no stub/no-op | PASS |
| D | End-to-end offline simulator + negative/safety + target build + deps | PASS |
| E | Fresh device recovery + connectivity preflight | BASELINE VERIFIED (fresh re-measure required before trial) |
| F | Exact manifest issued; physical authorization separate owner decision | PENDING |

**WARNING:** gates A–E are PASS **only with** the explicit caveat that E requires a
fresh read-only re-measurement before execution, and TEE acceptance (part of A) is
fundamentally hardware-only and can only close during the trial itself.

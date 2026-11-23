# S5000AP — Prompt 03.7: EFUJ2 Source and Provenance (Gate A)

**Branch/HEAD:** `cs/mob` @ `ae26b271c144780abb748ce2fb172919abb1131d` (live HEAD; round-03 commit `45b9097f3c989347ebc8572d733ca4e3a72f63e4` precedes it)
**Round window:** `2026-11-23` (offline source + provenance reconciliation)
**Handset actions:** NONE this round. This document consolidates the read-only
EFUJ2 identity established in round 03.6 and characterizes provenance honestly.
**No CP power/boot/load/reset/RF action of any kind.**

## 0. Headline

The selected read-only firmware source is the **installed EFUJ2 RADIO partition**
(`/dev/sda16`, GPT PARTLABEL `radio`), not the older DTK9 candidate. Its physical
identity is established; its **cryptographic/OEM provenance is NOT** — only TEE
acceptance (secure boot via kernel `exynos_smc`) can close that, and that is a
**DEVICE_ACCEPTANCE_PENDING_04** fact, not a claim of Samsung origin.

## 1. Source identity (read-only, round 03.6)

| Property | Value |
|---|---|
| Device | SM-G975F / beyond2lte / Exynos9820, revision 26 |
| Partition | `/dev/sda16`, GPT PARTLABEL `radio` (via read-only `blkid`) |
| Size | 52,428,800 B (102,400 × 512 B sectors) |
| Container magic | `TOC\0` (S5000AP ITOC) |
| Model | `SM-G975F_EUR_XX_EUR0` |
| Build | `G975FXXSEFUJ2_CL2054966_QB20745891` |
| Build date | 2021-10-20 |
| Full-partition SHA256 (reported) | `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7` |
| First-46,062,992 B SHA256 (reported) | `d2edc55cce48fe18cd87c6f377683dc75c07f88bc2fb602a2172aaf33b99a681` |

These hashes are **reported historical live reads** (round 03.6), not fresh
measurements this round; they remain baseline, not new truth, and must be
re-verified by a fresh read-only stream immediately before Stage-04.

## 2. Why EFUJ2, not DTK9

The derived candidate `modem.bin` (sha256 `1e4280d26de704281c01ddf59407fbfdfb714d3f87a55b780f6f74d1ab0e7881`)
is a **DTK9-family** image (`G975FXXS9DTK9`, 2020-11-13), a *different build* from
the installed EFUJ2. The stock `cpboot_v3` contract reads the installed RADIO
partition read-only (`-P .../by-name/radio` → `/dev/sda16`), so the least-invasive
correct source is the installed EFUJ2 image. The DTK9 archive
`CP_G975FXXS9DTK9_CP17435927_CL20034833_QB35905779_REV01_user_low_ship.tar.md5`
was **not found** in subsequent host searches and is NOT needed for the EFUJ2 path.

## 3. Provenance classification (honest, layered)

| Dimension | Result |
|---|---|
| Physical source identity | PASS — GPT PARTLABEL + size + ITOC magic + build tag (round 03.6) |
| Container structural integrity | PASS (partial) — `TOC\0` magic + bounds; per-part CRC32 must be re-computed from EFUJ2 (analyzer supports this) |
| Trusted OEM distribution provenance | **UNKNOWN** — no EFUJ2 `.tar.md5` archive; no chain-of-custody |
| Secure-boot signature verification | **UNKNOWN / device-side only** — kernel `shmem_security_request` → `exynos_smc` performs TEE acceptance at boot; userspace cannot pre-authenticate |
| Device/TEE acceptance | **DEVICE_ACCEPTANCE_PENDING_04** — only provable by the bounded authorized trial |

A SHA256/CRC32 hash proves *self-consistency*, NOT Samsung origin or secure-boot
acceptance. No `PASS` for authenticity is fabricated here.

## 4. Source input contract (`-P` equivalent) in `nuxel-cpbootd`

The native `nuxel-cpbootd` takes `--firmware <read-only RADIO/ITOC path>`:
- opened **O_RDONLY** (never O_RDWR/O_WRONLY);
- ITOC parsed under strict bounds (`b_offset + size <= firmware_size`);
- BOOT/MAIN/VSS/NV parts streamed to the kernel via `IOCTL_MODEM_XMIT_BOOT`
  (`struct modem_firmware`) — the kernel does `copy_from_user`, never a writable
  partition open by the daemon;
- **absolutely no RADIO/MODEM/CP/EFS write in any path.**

Source-open flags reflect the stock cbd contract (`std_boot_parse_toc_img` opens
`O_RDONLY`). The full partition is NOT assumed identical to a standalone `.bin`;
the parser reads the on-partition ITOC at runtime.

## 5. Verdict

**Gate A (source identity + structural validation + defensible provenance/risk
characterization) = PASS**, with the explicit residual uncertainty that secure-boot
acceptance is `DEVICE_ACCEPTANCE_PENDING_04`. No wrong-family firmware is selected
(EFUJ2 is `SM-G975F_EUR_XX_EUR0`, matching the device).

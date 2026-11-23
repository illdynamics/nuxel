# S5000AP — Prompt 03.6: Firmware Provenance Resolution (Gate A1/A3)

**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4` (unchanged)
**Round window:** `2026-11-23T04:05Z` → `04:30Z` (host CET)
**Handset actions:** READ-ONLY ONLY. SSH identity probes, one `IOCTL_MODEM_STATUS`
read, `blkid`/`lsblk` reads, and bounded read-only `head`/`dd` of the RADIO
partition header/metadata region (`sda16`). **No CP boot/reset/power, no RADIO/MODEM/
EFS write, no flash, no reboot, no DT change.**

---

## 0. Objective

Establish (to the maximum provable extent) whether the derived candidate
`modem.bin` can be tied to an authentic, model-compatible Samsung release, and
whether it matches the installed RADIO image.

## 1. Artifact inventory (re-verified this round)

| Artifact | Size | SHA-256 | Status |
|---|---|---|---|
| `modem.bin` | 46,062,992 | `1e4280d26de704281c01ddf59407fbfdfb714d3f87a55b780f6f74d1ab0e7881` | re-verified |
| `modem.bin.lz4` | 24,414,752 | `05371984d45f0bc33ebd06e189eaf6f298a468fc7525a479fd60ed320b5eacde` | re-verified |
| `modem_debug.bin` | 5,242,880 | `8d1c4e10e57d5b668d08de4aa284a44a145da3c4928a9d60b0206e1acd7d67d2` | re-verified |
| `modem_debug.bin.lz4` | 3,535,942 | `816c31160da7790548d64aa5c54d6b31950b4988f59944c72bc0639a1b62b971` | re-verified |
| `stock-cbd/cbd` | 494,000 | `c3e869fa2f78b1e8141cac58602c2a6fb852e31d5c08349ba969c75ef78f7b83` | re-verified |

All byte-identical to round-02/03.5 receipts.

## 2. Original archive chain of custody — STILL ABSENT

The documented archive
`CP_G975FXXS9DTK9_CP17435927_CL20034833_QB35905779_REV01_user_low_ship.tar.md5`
remains **absent** on this host (re-confirmed `find / -xdev -iname 'CP_G975F*'` →
empty; analyzer `ARCHIVE_MISSING`).

The derived workspace `/Users/wicked/.local/share/nuxel-s5000ap/
G975FXXS9DTK9-CP-20261117/` (owner uid 501, created 2026-11-17) contains members
`modem.bin.lz4`/`modem_debug.bin.lz4` whose LZ4-decompressed bytes (`modem.bin`,
`modem_debug.bin`) are internally consistent (content-checksum + ITOC CRC32 pass).
**This proves the `.bin` came from these `.lz4`, NOT that the pair came from Samsung's
original archive.**

## 3. Derived image identity (measured)

- Container: S5000AP ITOC (`TOC\0`), parts BOOT/MAIN/VSS (CRC32 match), NV/OFFSET.
- Appended MBN metadata: `SignerVer02`, `QBR`, build tag
  `G975FXXS9DTK9_CL1535157_QB17435920201113015242`, model `SM-G975F_EUR_XX_EUR0`,
  marker `NONEmrk`, signature region 784 B (NOT decoded).
- Build date: **2020-11-13**.

This is a **DTK9-family, SM-G975F/EUR-model-matched, structurally-valid** candidate.
It is **NOT** proven Samsung-signed or TEE-acceptable (signature offline-unverifiable;
`NONEmrk` is metadata, not authenticity).

## 4. Installed RADIO — NEW evidence this round (see companion report)

`blkid` (read-only) now yields the full GPT partition label map, which resolves the
prior "no partition map" blocker:

- **`/dev/sda16` = PARTLABEL `radio`**, size 52,428,800 B (102,400 × 512).
- Its first 16 bytes are `TOC\0` (valid ITOC container).
- Its embedded public build metadata: **`G975FXXSEFUJ2_CL2054966_QB20745891`**
  (`SM-G975F_EUR_XX_EUR0`), build date **2021-10-20**.

**Consequence:** the installed RADIO is **`G975FXXSEFUJ2`**, a **newer** Samsung
release than the DTK9 candidate. The derived `modem.bin` (DTK9) is a **different CP
build** from what is currently installed, not a byte-identical match.

## 5. Provenance verdict

| Dimension | Result |
|---|---|
| Structural integrity | PASS (offline) — ITOC CRC32 |
| Model/SoC compatibility | PASS — `SM-G975F_EUR_XX_EUR0`, beyond2lte/Exynos9820 |
| Firmware family | DTK9 (candidate) vs EFUJ2 (installed) — **differ** |
| Filename identity (documented archive) | UNKNOWN — absent |
| Package identity (CL/QB) | see CL-QB companion report |
| Internal modem build identity | candidate `CL1535157/QB17435920`; installed `CL2054966/QB20745891` |
| Cryptographic integrity | only CRC32/LZ4 (self-consistency), NOT signature |
| Source authenticity | UNKNOWN — original `.tar.md5` absent |
| Device compatibility | model-matched, but **candidate ≠ installed build** |
| Secure-boot acceptance | UNKNOWN — only provable by future authorized trial |

**Final: `STRUCTURALLY_VALID_PROVENANCE_UNKNOWN`** for the candidate (unchanged), now
with the additional, correctly-established fact that the **installed RADIO is a
different build (EFUJ2) than the DTK9 candidate.**

## 6. What this changes for the mission

1. The candidate `modem.bin` is a **legitimate DTK9 CP image** structurally, but it is
   **not the image currently installed** on the device (EFUJ2 is).
2. Whether the DTK9 image is even the right one for this handset's secure-boot chain
   depends on whether the SBoot/BL expects a matching CP, and on whether the owner
   intends to (a) boot the installed EFUJ2 image read-only (which is what stock `cbd`
   does via `-P .../by-name/radio`), or (b) replace with DTK9. **Replacing the RADIO
   partition is forbidden without separate explicit owner authorization** and is NOT
   part of any proposal here.
3. The **least-invasive correct path** is to boot the **installed EFUJ2 image read-only
   from `/dev/sda16`** (the stock cbd contract), NOT the DTK9-derived file. This is now
   fully supported by evidence (§4): the installed RADIO is a valid ITOC container.

## 7. Owner input still required (minimal)

Provide the original `CP_G975FXXS9DTK9_..._tar.md5`, **or** confirm the derived
`.lz4` pair is authoritative. Because the installed RADIO is proven to be **EFUJ2**
(not DTK9), the owner must also decide the intended source. **The agent does not
manufacture either the provenance or the decision.**

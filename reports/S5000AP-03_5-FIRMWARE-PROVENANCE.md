# S5000AP — Prompt 03.5: Firmware Provenance (Blocker A evidence)

**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4`
**No handset-changing action. No RADIO/MODEM/CP/EFS read or write.**

This report re-verifies and completes the round-02 provenance work, adds the
cpboot_v3 type-string evidence, and records the live read-only findings that could
this round be refreshed.

---

## 1. Artifact inventory (hashes re-verified this round)

| Artifact | Size | SHA-256 | Status |
|---|---|---|---|
| `modem.bin` | 46,062,992 | `1e4280d26de704281c01ddf59407fbfdfb714d3f87a55b780f6f74d1ab0e7881` | re-verified |
| `modem.bin.lz4` | 24,414,752 | `05371984d45f0bc33ebd06e189eaf6f298a468fc7525a479fd60ed320b5eacde` | re-verified |
| `modem_debug.bin` | 5,242,880 | `8d1c4e10e57d5b668d08de4aa284a44a145da3c4928a9d60b0206e1acd7d67d2` | re-verified |
| `modem_debug.bin.lz4` | 3,535,942 | `816c31160da7790548d64aa5c54d6b31950b4988f59944c72bc0639a1b62b971` | re-verified |
| `stock-cbd/cbd` | 494,000 | `c3e869fa2f78b1e8141cac58602c2a6fb852e31d5c08349ba969c75ef78f7b83` | re-verified |

All hashes match round-02 receipts byte-for-byte. The workspace is unchanged since
round 02 (`S5000AP-02-private/receipts/existing-cp-workspace.sha256` still valid).

## 2. Original archive discrepancy (still unresolved)

- `find / -xdev -iname 'CP_G975F*'` → empty (except browser cache, not firmware).
- Analyzer `ARCHIVE_MISSING` for the exact `mobile.md` path (re-confirmed).
- The `CL`/`QB` stamp mismatch persists and **matters**:

| Source | CL | QB |
|---|---|---|
| Image MBN metadata | `CL1535157` | `QB17435920` |
| `mobile.md` target filename | `CL20034833` | `QB35905779` |

Model (`SM-G975F_EUR_XX_EUR0`) and base build (`G975FXXS9DTK9`) match; the CP
component stamp does not. Per Samsung practice AP↔CP component stamps differ, but
**absent the original archive this cannot be proven**; the gap remains `UNVERIFIED`.

## 3. Signing / compatibility (structural vs provenance vs acceptance)

| Dimension | Result | Evidence |
|---|---|---|
| Structural integrity | ✅ PASS (offline) | ITOC BOOT/MAIN/VSS CRC32 all match |
| Model compatibility | ✅ model/SoC match | `SM-G975F_EUR_XX_EUR0`, beyond2lte/Exynos9820 (live cmdline + DT) |
| Firmware family | ✅ DTK9 base | `G975FXXS9DTK9_...` build tag |
| Provenance (origin) | ❌ UNKNOWN | original `.tar.md5` absent; derived workspace unauthenticated |
| Signing authenticity | ❌ UNKNOWN | `SignerVer02`/`NONEmrk` present; RSA/ECDSA chain not verifiable offline |
| Device-side TEE acceptance | ❌ UNKNOWN | only verifiable by the future authorized physical `SECURITY_REQ` trial |

**Verdict: `STRUCTURALLY_VALID_PROVENANCE_UNKNOWN`.** The image is a structurally
sound, model-matched DTK9-family candidate; it is NOT a proven Samsung-signed,
TEE-acceptable image, and the package stamp does not match the documented archive.

## 4. Installed RADIO image (live, this round)

- `IOCTL_MODEM_STATUS` → `OFFLINE (0)` (`PROVED_LIVE`, `nuxel-cp-status`, kernel log
  shows only `misc_open/misc_release`, no mutation).
- RADIO partition mapping: **NOT addressable** on this boot. `/dev/block` absent,
  `/dev/disk/by-partlabel` empty, no PIT/by-name map. `/proc/partitions` shows
  `sda` (UFS) with `sda1..sda31`; `/dev/sda*` nodes exist but there is **no name
  table** to identify which `sdaN` is `radio`/`modem`/`cpefs`.
- Candidate radio/modem sizes (`sda25`≈5.97 GB, `sda26`≈1.15 GB, `sda27`≈650 MB,
  `sda28`≈629 MB) — but **guessing is forbidden**; no read performed.
- Consequence: the installed RADIO image **cannot be correlated with the derived
  `modem.bin`** on this boot. `MATCHED_INSTALLED_IMAGE` is therefore `UNKNOWN`.

## 5. cbd `-t` type-string proof (new this round)

`cpboot_v3` @ `234b138716426c36ed801a71052bc144f7d8d806` (lineage-22.1):

```
Container.cpp:100-125:
  case 't':
    cmd = optarg;
    #ifdef CONFIG_TYPE_MODAP
    if (!strncmp(cmd, "modap_sit", 9) || !strncmp(cmd, "ss310", 5))
        bootdump = new BootDumpModap();      // ss310 == Shannon 310 == ModAP (SIT)
    #endif
    #ifdef CONFIG_TYPE_EXT
    if (!strncmp(cmd, "s5100sit", 8) || !strncmp(cmd, "s5100", 5))
        bootdump = new BootDumpExt();        // s5100 == EXT
    #endif
    if (!bootdump) { cbd_info("Unknown modem"); return ERROR; }
```

`BootDumpModap.cpp:413` hardcodes `name = "ss310"`. Kernel `modem_variation.h/c`
declares three distinct modem types `SS310AP`, `S5000AP`, `S5100`, each with its own
controller file. **`ss310` ≠ `s5000ap`.** The DTK9 `init.baseband.rc` line
`-d -tss310 ...` therefore names the **wrong modem generation** for the S5000AP.

Implication: the owner-private stock cbd, even if it could run (it cannot, see CBD
decision report), would instantiate the ModAP/SIT path rather than the S5000AP/SIPC
path. The correct S5000AP `-t` value is **not present in any recovered source** and
requires the owner's real DTK9 vendor runtime or a bounded live trace to establish.

## 6. Decision

`STRUCTURALLY_VALID_PROVENANCE_UNKNOWN`. Structural integrity and model/family
compatibility are proven; provenance, signing, and the type-string question remain
open and require owner input + (for the installed-image equivalence) physical
device access. Acceptance itself is only provable by the future authorized trial.

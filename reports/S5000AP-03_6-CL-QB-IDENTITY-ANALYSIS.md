# S5000AP — Prompt 03.6: CL/QB Identity Analysis (Gate A2)

**Branch/HEAD:** `cs/mob` @ `45b9097f3c989347ebc8572d733ca4e3a72f63e4` (unchanged)
**No handset-changing action.**

---

## 0. The three distinct identities

| Label | Where found | CL | QB | Full build tag |
|---|---|---|---|---|
| Documented archive filename | `mobile.md` (absent file) | `CL20034833` | `QB35905779` | `CP_G975FXXS9DTK9_CP17435927_CL20034833_QB35905779_REV01_user_low_ship` |
| Derived candidate `modem.bin` | MBN metadata | `CL1535157` | `QB17435920` | `G975FXXS9DTK9_CL1535157_QB17435920201113015242` |
| **Installed RADIO (`sda16`)** | MBN metadata (live read) | `CL2054966` | `QB20745891` | `G975FXXSEFUJ2_CL2054966_QB20745820211020041207` |

## 1. What CL/QB mean

`CL` (ChangeList) and `QB` (Quality Build) are Samsung **per-component build
identifiers** that differ across the AP (PDA), CP (modem), BL, and CSC components of a
single firmware release. They are **not** expected to be equal between the AP and the
CP. This is why the documented archive carries a CP/`CP17435927` component stamp
distinct from the MBN's internal `CL1535157`.

## 2. Resolution of the prior "mismatch"

The prior rounds treated the `CL1535157/QB17435920` (candidate MBN) vs
`CL20034833/QB35905779` (archive filename) as an "unresolved mismatch." This round
adds the decisive third data point:

- **Installed RADIO build = `G975FXXSEFUJ2`** (2021-10-20), entirely distinct from the
  DTK9 family (2020-11-13).

So the three CL/QB values belong to **three different firmware generations/builds**,
not a single equivalent set:

1. Documented archive: a **DTK9 CP archive** whose filename CP stamp is
   `CP17435927/CL20034833/QB35905779` (a specific DTK9 CP drop).
2. Derived `modem.bin`: a **DTK9 CP image** whose *internal* MBN stamp is
   `CL1535157/QB17435920` (a different DTK9 CP drop than the archive filename implies —
   i.e. the derived `.bin` is NOT the member one would expect inside the named archive).
3. Installed RADIO: **EFUJ2** CP image, `CL2054966/QB20745891` (a newer release).

## 3. Verdict

**`MISMATCH_EXPLAINED_AND_COMPATIBLE`** — in the narrow sense that:
- CL/QB differing between AP and CP is **expected Samsung behavior** (different
  namespaces per component), so no literal equality is ever required.
- The candidate's model (`SM-G975F_EUR_XX_EUR0`) and SoC (Exynos9820/S5000AP) **match**
  both the device and the installed image.

**BUT** the practical consequence is more important than the verdict label:

- The **installed RADIO is EFUJ2**, not DTK9. The DTK9 candidate is therefore a
  **different CP build than what is installed**, and the honest compatibility claim is
  limited to *"model/SoC-compatible DTK9 CP image,"* NOT *"the image the device
  currently runs."*

## 4. Which fields must match vs may differ

| Identity field | Must match for compatibility? | Evidence |
|---|---|---|
| Model (`SM-G975F[_EUR_XX_EUR0]`) | **YES** | candidate + installed + archive all `SM-G975F` / `..._EUR0` |
| SoC/board (beyond2lte/Exynos9820) | **YES** | live cmdline + partition map |
| Base family (`G975FXXS9…`) | NO (S = security patch series) | DTK9 (S) vs EFUJ2 (S) differ but same model |
| CL (ChangeList) | NO literal equality (component namespace) | AP≠CP≠BL≠CSC |
| QB (Quality Build) | NO literal equality | per-component |
| Internal MBN build tag | MUST be self-consistent | candidate `..._QB17435920...`; installed `..._QB20745891...` |

## 5. Remaining uncertainty

- Whether the **DTK9 CP** is acceptable to the **EFUJ2**-era secure-boot chain
  (SBoot/BL) is **unknown** and only provable by a bounded authorized trial, OR by
  obtaining the matching EFUJ2 CP archive (which would eliminate the provenance gap for
  the *installed* build entirely).
- The original `CP_G975FXXS9DTK9_..._CL20034833_QB35905779` archive is still absent, so
  we still cannot prove the derived `.bin` was ever that exact named archive's member.

## 6. Bottom line

The CL/QB "mismatch" is **explained** (component-namespace + three genuinely different
builds). The **material** fact upgraded this round is that the **installed RADIO is
EFUJ2, not DTK9** — so the least-invasive compatible source is the **installed EFUJ2
image read from `/dev/sda16`**, while the DTK9-derived file is a model-compatible but
**different-build** candidate whose provenance remains unproven.

# SSP-0025 — Kernel Reconciliation (Prompt 05_8)

**Agent:** DeepSeek-V4-Pro-Thinking
**Date:** 2026-11-22 (Europe/Amsterdam)
**Target:** SM-G975F (beyond2lte), Nuxel Linux
**Scope:** Offline source reconciliation + read-only live verification. **No flash, no rail transition performed.**

---

## 0. Verdict

Patch **0025 (`0025-nuxel-ssp-rail-force-coldcycle.patch`, SHA-256 `ab293ae6…`)** is
**source-correct, correctly scoped, and compiles cleanly**. It is the minimal
(one-line) correction to the MCU cold-cycle defect and is NOT a blanket
`regulator_disable` replacement.

However, a **full repoducible kernel BOOT candidate cannot be built on this host**,
for two independent, precisely-characterized reasons (see §5). This does not
invalidate 0025 — it gates the FLASH behind preflight, which is the correct
fail-closed outcome.

---

## 1. Exact correction (0025, verified in pinned source)

File: `drivers/sensorhub/brcm/ssp_sysfs.c`, `set_mcu_power()`, `case 0`:

```c
/* BEFORE (defective): */
if (regulator_is_enabled(data->regulator_vdd_mcu_1p8))
    ret = regulator_disable(data->regulator_vdd_mcu_1p8);

/* AFTER (0025, correct): */
if (regulator_is_enabled(data->regulator_vdd_mcu_1p8))
    ret = regulator_force_disable(data->regulator_vdd_mcu_1p8);
```

`case 1` (from patch 0023) already does an **unconditional** `regulator_enable()`
to re-acquire the reference after the cold-cycle:

```c
case 1:
    ret = regulator_enable(data->regulator_vdd_mcu_1p8);
```

### Why plain `regulator_disable` is a no-op here

Live-verified on the running device (read-only): `vdd_mcu_1p8` is `state=enabled`
with `num_users=0`. A `regulator_disable()` against a `num_users==0` regulator
returns `-EINVAL` ("unbalanced disable") from the Linux 4.14 regulator core and
**does not drop the rail**. The bootloader left the rail up with zero kernel
references. Only `regulator_force_disable()` detaches every reference and lets the
rail physically fall, re-opening the BCM47752 boot-ROM autobaud window.

### Scoping audit (no blanket replacement)

`regulator_force_disable` now appears in exactly **two** MCU power-management
call sites and **nowhere** it should not:

| Call site | Patch | Path | Correct? |
|---|---|---|---|
| `ssp_sysfs.c:584` `set_mcu_power` case 0 | 0025 | operator-initiated `echo 0 > mcu_power` | YES (the scoped fix) |
| `ssp_bbd.c:932` `nuxel_ssp_bringup_hw` recovery | 0027 | bring-up recovery + downloader | separate, see §5 |

No `regulator_disable()` remains in `drivers/sensorhub/` (verified via `grep`),
only in comments describing the old behavior. The correction is **not** a blind
global replacement.

---

## 2. Regulator dependency graph (source-backed + live-verified)

```
vdd_mcu_1p8 (1.8 V fixed, s2mps19 regulator.62)
  state=enabled, num_users=0          [LIVE-MEASURED, read-only]
  owner: ssp_dev.c (regulator_get + enable at probe)
  userspace: mcu_power sysfs (case 0 = force-disable, case 1 = enable)
  upstream: s2mps19 PMIC LDO
  declared consumers (source): ssp_dev.c only
  observed consumers (live): NONE (num_users=0)
  bootloader state: ENABLED (left up)
  shared with GNSS? UNRESOLVED (0025 AUDIT note; software controls distinct,
      physical rail sharing cannot be excluded from source alone)

GPS_PWR_EN (gpio-145 / gpg0-2)     [LIVE: out low]
  GNSS stand-by GPIO, NOT the MCU rail
  owner: bcm_gps_spi.c (export + direction output-low)
  NEVER touched by this mission

SPI spi17 / 10970000.spi            [LIVE: tx advances, rx=0]
  SSI transport, half-duplex; 0020 re-inits after runtime suspend

IRQ 441 "ttyBCM" (host_req)        [LIVE: count=0]
  armed on /dev/ttyBCM open; never fired (ROM silent)
```

### Disable semantics (source-verified against Linux 4.14 regulator core)

- `regulator_disable()` at `num_users==0` → `-EINVAL`, no-op (unbalanced).
- `regulator_force_disable()` → detaches all references, drops the rail regardless
  of `num_users`, and asserts the driver owns the regulator (WARN if not).
- `regulator_enable()` after force-disable → re-acquires a reference, restores rail.

---

## 3. Patch series application (reproducible, verified)

Pinned source: `android_kernel_samsung_exynos9820` @ `f7194c1d15eded1c2a1a4dc63825b26103435cc0`.

Clean checkout on a **case-sensitive** APFS volume (`/Volumes/kernelbuild`) — required
because the workspace `/Users/wicked/x/nuxel` is case-**insensitive** and corrupts
28–29 `netfilter/xt_*.c|h` files at checkout (verified: 29 `git status` entries
immediately after checkout on the case-insensitive clone).

Forward apply (order): 0020 → 0023 → 0025 → all apply cleanly (`git apply` no conflict).
0027 also applies cleanly but has a **separate link-time defect** (§5).

Reverse (full unwind 0027→0020) returns the tree to **exactly** pinned HEAD
(`git status --short` = 0). Series is idempotent/reproducible.

Source audit (`tools/s10plus/ssp-stage04/audit_kernel_source.py`, `--allow-patch-touched`):

```
status: PASS
actual_head: f7194c1d15eded1c2a1a4dc63825b26103435cc0
unexpected_modified_files: []
untracked_files: []   (after git-add of the 0023-created header, see §4 finding)
```

---

## 4. Reconciliation findings (surface truthfully)

### F1 — 0027 has a dangling extern symbol (`nuxel_bbd_patch_bytes`) — LINK FAILURE

Patch 0027 (`0027-nuxel-ssp-kernel-firmware-download.patch`) declares and calls,
but **never defines**, `nuxel_bbd_patch_bytes()`:

- `bbd.h:154` → `extern const unsigned char *nuxel_bbd_patch_bytes(int, int, size_t*);`
- `ssp_bbd.c:744` (`nuxel_ssp_dl_download`) → `cont = nuxel_bbd_patch_bytes(...);`
- **No definition anywhere** (0027, 0023, vendor tree all grep'd).

Result at link: `undefined reference to nuxel_bbd_patch_bytes`. The prior
reconciliation report's "compiles with no errors" was an **object-only** check
(`ssp_bbd.o`), which does NOT catch a missing external symbol — only the full
`vmlinux` link does. This prompt's §2 "check ... error paths" surfaces it.

**Impact on THIS candidate:** NONE. 0025 (the cold-cycle sysfs path) is independent
of 0027 (the in-kernel downloader). The 0025 candidate uses `mcu_power` + userspace
`--rom-probe`, not the 0027 downloader (consistent with prior deferrals). 0027 must
be repaired (implement the firmware byte supplier) before it can be part of any
future downloader build — it is currently un-linkable.

### F2 — audit tool flags the 0023-created header as "untracked"

`drivers/sensorhub/brcm/bbdpl/nuxel_ssp_variant_ctl.h` is legitimately created by 0023
(`git apply` leaves new files untracked). The strict audit correctly FAILs on this
until the file is `git add`-ed. For a reproducible build tree, new files introduced
by patches must be committed/staged. Documented; not a patch defect.

### F3 — macOS host toolchain cannot complete the full vendor-tree link (unrelated to SSP)

The SASamsung 4.14.253 tree carries a global `-Werror` (Makefile:428) plus vendor
`-Wformat`/`-Wunused-variable` defects across many SoC/display drivers
(`exynos-ppmpu.c`, DPU20 panel code, etc.) that GCC 15.2 promotes to hard errors.
The host also lacks `<elf.h>`/`<endian.h>` (shimmed by `kernel/host-tools/include`).
The SSP sensorhub objects (`ssp_bbd.o`, `ssp_sysfs.o`, `ssp_dev.o`) **compile
cleanly**, but the overall `Image.gz` link does not complete on this macOS/GCC-15
host. This is a toolchain-environment blocker, not an SSP-patch defect.

---

## 5. Build preflight result

| Gate | Result |
|---|---|
| Exact pinned commit `f7194c1d15ed…` | PASS (HEAD verified) |
| Clean case-sensitive source tree | PASS (0-diff at pinned HEAD) |
| Reproducible patch apply (0020→0023→0025) | PASS (forward + full reverse) |
| Patch 0025 scoping (no blanket replace) | PASS (2 sites only, correct) |
| SSP object compile (`ssp_bbd/ssp_sysfs/ssp_dev.o`) | PASS |
| Full `Image.gz` / `vmlinux` link | **FAIL** (0027 dangling symbol + GCC-15 `-Werror`) |
| BOOT candidate packaging | NOT REACHED (no Image.gz) |

**Any mandatory FAIL → NO FLASH.** The full-build failure is a `BLOCKED_PREFLIGHT`
condition regardless of 0025's correctness.

---

## 6. Next step to unblock preflight (for a future, separately-approved build)

1. Repair 0027 (implement `nuxel_bbd_patch_bytes` supplying the firmware patch blob,
   or fold the byte supplier into the downloader) — OR explicitly build the
   0025-only candidate with 0027 excluded and document the exclusion in the build receipt.
2. Use a GCC 4.9/8-era `aarch64-linux-android-` toolchain (the tree's intended toolchain),
   or neutralize the vendor `-Werror` globally for the unrelated SoC/display drivers.
3. Re-run `build-kernel.sh` (which manages `asm-generic archprepare` + host-tools shim)
   to produce `Image.gz`, then `pack-ssp-boot.py` for the BOOT candidate.

**None of the above was performed against the device. No BOOT partition was written.
No regulator force-disable was issued.**

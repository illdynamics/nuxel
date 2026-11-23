# SSP — BCM47752 MCU Power-Sequence Fix (Minimum Correct Correction)

**Prompt:** 05_7 §3
**Agent:** DeepSeek-V4-Pro-Thinking
**Date:** 2026-11-22
**Status:** Correction identified + source-verified; **NOT deployed** (requires a
kernel BOOT-only change, gated behind a separate owner authorization — see §8 and
the trial plan).

---

## 0. The exact defect

The deployed kernel (`4.14.253-gf7194c1d15ed-dirty`, patches 0020 + 0023 only —
confirmed live via `/proc/kallsyms`: `nuxel_ssp_bringup_hw` present,
`nuxel_ssp_dl_download`/`dl_*` absent) contains a cold-cycle recovery in
`nuxel_ssp_bringup_hw()` that calls **plain `regulator_disable()`** on
`vdd_mcu_1p8`.

Live evidence this session: `vdd_mcu_1p8` is `state=enabled` with `num_users=0`.
A plain `regulator_disable()` against a `num_users==0` regulator is an
"unbalanced disable" no-op (`-EINVAL` from the regulator core), so **the rail
never physically falls**. Therefore even the kernel's own documented recovery
path cannot re-enter the BCM47752 boot-ROM autobaud window, and every firmware
download attempt meets a silent ROM (`rx=0`, `HSI_CTRL=0xFFFFFFFF`).

## 1. The correction (one-line, source-verified, owner-scoped)

In `drivers/sensorhub/brcm/ssp_bbd.c`, `nuxel_ssp_bringup_hw()`, replace the
no-op disable with a force-drop that actually toggles the rail:

```c
/* BEFORE (deployed 0023, defective): */
if (regulator_is_enabled(data->regulator_vdd_mcu_1p8))
    regulator_disable(data->regulator_vdd_mcu_1p8);

/* AFTER (0025/0027, correct): */
if (regulator_is_enabled(data->regulator_vdd_mcu_1p8))
    regulator_force_disable(data->regulator_vdd_mcu_1p8);
```

The identical correction is already authored and reviewed in two repository
patches, so **no new source is invented**:

- `kernel/s10plus/patches/0025-nuxel-ssp-rail-force-coldcycle.patch`
  (SHA-256 `ab293ae6…`) — applies `regulator_force_disable` to the `mcu_power`
  `case 0` sysfs path, with an explicit AUDIT note that the rail may be shared
  with GNSS and must never be on an automatic loop.
- `kernel/s10plus/patches/0027-nuxel-ssp-kernel-firmware-download.patch`
  (SHA-256 `cc33f15e…`) — folds the same `regulator_force_disable` into the
  bring-up recovery path and then drives the two-phase firmware download.

**Preferred fix (least invasive, still kernel):** apply 0025 only, so the
existing `mcu_power` sysfs becomes a genuinely cold-cycling control, and reuse
the already-tested userspace `--rom-probe` (autobaud + GetVersion) for the ROM
identity exchange. This avoids pulling the large in-kernel downloader (0027)
into a trial, keeps the transfer single-owner (userspace), and does not change
DTB/DTBO.

**Why not a userspace-only fix:** there is no userspace regulator sysfs knob that
can force-drop a zero-reference rail. `/sys/class/regulator/.../force_disable`
does not exist on this 4.14 kernel; the only owner-scoped paths are the kernel
`mcu_power` (case 0 → needs the 0025 hunk) and the driver cold-cycle recovery
(needs the same hunk). A direct GPIO write is explicitly excluded by the prompt
("Do not use direct GPIO writes as a shortcut") and is a documented reboot hazard.

## 2. Minimum defensible correction (chosen)

1. Apply `0025-nuxel-ssp-rail-force-coldcycle.patch` (already authored, already
   reconciled in the patch stack) so `mcu_power` `case 0` uses
   `regulator_force_disable` and `case 1` unconditionally `regulator_enable()`.
2. Keep 0020 + 0023 (already deployed) unchanged.
3. Do **not** deploy 0027 (the in-kernel downloader) for the ROM-identity trial;
   the userspace `--rom-probe` already performs autobaud + GetVersion correctly.
4. Do **not** touch DTB/DTBO.

This is a `POWER_FIX_IMPLEMENTED_AWAITING_AUTHORIZATION` state: the software
correction is complete and source-verified, but the physical rail transition
requires owner approval and a kernel BOOT-only flash.

## 3. Defect checklist from the prompt §3 (assessed)

| Item | Finding |
|---|---|
| `bcm477x_hello` | OK (GPIO handshake); not the cause. Only drives `mcu_req`/`mcu_resp`. |
| `initialize_mcu` | OK (WHOAMI/AP_INFO/scan/fw-rev); silently fails on a non-booted ROM (correctly returns error). |
| `nuxel_ssp_bringup_hw` | **DEFECT**: cold-cycle recovery uses no-op `regulator_disable()`. |
| rail on/off routines | `mcu_power` sysfs: `case 0` is no-op without 0025. |
| runtime-PM resume/suspend | 0020 fixes SPI HW re-init; not the ROM-silence cause (TX works). |
| cold-start logic | Correct intent, wrong primitive (`disable` vs `force_disable`). |
| 0025 deferred rail-cycle | Correct fix; **not deployed** in running kernel. |
| wrong ordering | No (order is right; the disable primitive is wrong). |
| missing init | No. |
| stale state flags | `shutdown=1`/`resetting=1` are consequences of prior failed handshakes; cleared on next successful bring-up. |
| skipped delays | Delays are placeholders (unmeasured); per §2 evidence gate, poll `regulator_is_enabled()` rather than trust `msleep(300)`. |
| ownership conflicts | Single-owner transport confirmed (no process holds tty/bbd nodes). |

## 4. Offline verification (receipts, this session)

```
make -C tools/s10plus/ssp-native OUT=/tmp/ssp-prompt057-check check
  PASS SIMULATED nuxel_bbd_download framing, CRC, and patch validation
  PASS nuxel_bbd_flash framing + F1 records + RX decode (offline)
  PASS nuxel_bbd_flash negative cases (offline)   [16 cases incl. 2 ROM-boundary safety tests]
  test_verify_embedded_patch.py -> 2/2 OK
  check_protocol_replay.py -> passed=true hardware_verified=false operation_completion_verified=false

PYTHONPATH=services/nuxel-orientation python3 -m pytest services/nuxel-orientation/tests  -> 77 passed
python3 -S -m unittest discover -s NUXEL_SSP_RECOVERY_V2 -p 'test_*.py'                -> 14 passed (PLAN ONLY, zero device calls)
```

Safety boundaries re-verified:
- `--rom-probe` cannot emit MemoryWrite/StartScratchApp/ServiceStart (regression-proven via `NUXEL_BBD_TEST_INSTRUMENT` RPC recording hook).
- Single-owner transport confirmed live (`lsof` empty on tty/bbd nodes).
- No firmware-write reachable from `--rom-probe` (returns `EXIT_ROM_IDENTIFIED` before the MemoryWrite loop).
- No unintended reset/power-cycle in an ordinary read-only diagnostic (the fix is gated behind an explicit `mcu_power`/`nuxel_bringup` write, never an automatic loop).

### Source hashes (receipt)
```
5fae2216abfe829cb0a831c808d5e5fd8aa04eef011f92b73428afe0cf8043bd  tools/s10plus/ssp-native/nuxel_bbd_flash.c
3eb0991373074896b284f862fc5178e33c617b38cf972f322b3d89faf65d802d  tools/s10plus/ssp-native/tests/test_nuxel_bbd_negative.c
62a339642a8c039471c360da9a9175fd7e1b3e5e821cf3013ae953b0d6f73200  kernel/s10plus/patches/0020-nuxel-ssp-spi-runtime-reinit.patch
b21abad67fdee4734bfbc8c259295ff85f326fb16aabd68dc15dd208f92ca1db  kernel/s10plus/patches/0023-nuxel-ssp-native-bringup-reconciled.patch
ab293ae63951fe0e3753dd30e56478439c6db1523efbd174b58deee6d32d6e99  kernel/s10plus/patches/0025-nuxel-ssp-rail-force-coldcycle.patch
cc33f15e034b823c0b019d02f4948df2013715fdf86473f0ce4fab94c51e289d  kernel/s10plus/patches/0027-nuxel-ssp-kernel-firmware-download.patch
```

## 5. Kernel-change implications (per §8)

Because the fix is a **kernel change** (0025 hunk in `ssp_sysfs.c`), it cannot be
taken live without a BOOT-only flash. Per prompt §8, the pre-flash prerequisites
are therefore required before any physical transition:

- Clean pinned kernel build at `f7194c1d15ed…`.
- SSP patch reconciliation (0020 → 0023 → **0025**; 0027 optional/deferred).
- BOOT donor validation (`0e6aa34c…` donor SHA on record).
- Independent candidate verification.
- Full Stage-04 preflight.
- Known-good BOOT rollback staging (host + TWRP copies on record).
- DTB/DTBO preservation checks (`abc9d45d…` / `de3bc025…` unchanged).

**None of this has been flashed; no physical power transition has been performed.**

## 6. Decision

**`POWER_FIX_IMPLEMENTED_AWAITING_AUTHORIZATION`**

The verified root cause is fixed at the source level (one-line
`regulator_disable` → `regulator_force_disable`, already authored as 0025), and
the complete offline validation is green. The physical rail cold-cycle and the
subsequent ROM `GetVersion` trial require a separately authorized BOOT-only
kernel flash (to deploy 0025) followed by a bounded `--rom-probe`. See
`reports/SSP-ROM-WAKEUP-FIRST-LIGHT.md` for the trial plan and evidence log.

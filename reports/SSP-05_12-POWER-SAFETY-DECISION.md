# SSP-05_12 — MCU Power Safety Decision (corrected)

**Date:** 2026-11-22/23
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** SM-G975F (beyond2lte)

---

## Decision: `MCU_POWER_SAFETY_BLOCKED`

The previously declared `MCU_POWER_SAFETY_PASS` is **revoked**.  The deployed
0025 cold-cycle was proven ONE-WAY on hardware, and the real chip power gate is
`GPS_PWR_EN` (gpio-145), which is a documented reboot hazard and is explicitly
restricted by the mission safety invariants from unilateral manipulation.

## 1. Proof the 0025 mechanism was unsafe (one-way)

Live sequence on the deployed 0020+0023+0025 kernel:

```
echo 0 > mcu_power   -> vdd_mcu_1p8 state = disabled   (force_disable works)
echo 1 > mcu_power   -> vdd_mcu_1p8 state = disabled   (enable is a NO-OP)
echo 1 (again)       -> vdd_mcu_1p8 state = disabled
>>> required a FULL DEVICE REBOOT to restore the rail <<<
```

Root cause (regulator core, `drivers/regulator/core.c`):
```c
/* regulator_get() time, when CHANGE_STATUS not advertised: */
if (!regulator_ops_is_valid(rdev, REGULATOR_CHANGE_STATUS) &&
    _regulator_is_enabled(rdev))
    regulator->always_on = true;

int regulator_enable(struct regulator *r) { if (r->always_on) return 0; ... } /* no-op */
int regulator_is_enabled(struct regulator *r) { if (r->always_on) return 1; ... } /* always 1 */
```
`regulator_force_disable()` drops the rail; there was **no** matching force-
enable, so the rail could never be re-raised in-process.

## 2. Fix (deployed and verified): patch 0028

- Added symmetric `regulator_force_enable()` (calls `_regulator_do_enable()`
  directly, bypassing the `always_on` mask).
- `set_mcu_power` case 1 → `regulator_force_enable()`.
- `nuxel_ssp_bringup_hw()` fallback → `regulator_force_disable()` +
  `regulator_force_enable()`.

Verification on hardware (new kernel `4.14.253-g73727632c863-dirty`):
```
echo 0 > mcu_power  -> disabled
echo 1 > mcu_power  -> enabled      (NO reboot required)
```
`regulator_force_enable` symbol confirmed in `/proc/kallsyms`.

## 3. Remaining blocker: GPS_PWR_EN is the chip power gate

After the corrected cold-cycle, the ROM probe still returned `rx=0`.  SPI
diagnostics show the chip is not powered (`MISO 0xFF`, `HSI_CTRL=FFFFFFFF`,
`Nread 65535`).  The BCM47752 is gated by `GPS_PWR_EN` (gpio-145) = LOW, which
`bcm_spi_probe` drives to `0` and never asserts.  This is the actual power-on
dependency, and it is outside the safe scope of this mission (documented reboot
hazard; safety invariants forbid substituting GPS_PWR_EN for MCU power without
a verified vendor power-on sequence).

## 4. Minimum evidence needed to clear the blocker

1. The vendor/stock Samsung BCM47752 power-on sequence (order + timing of
   `vdd_mcu_1p8` vs `GPS_PWR_EN` vs `MCU_REQ`/`MCU_RESP` vs SSI autobaud).
2. Source-level confirmation that asserting `GPS_PWR_EN` HIGH is safe in the
   Nuxel context (no GNSS RF damage/reboot), or an explicit owner grant for a
   bounded, supervised GPS_PWR_EN assertion trial.

## Final

```
MCU_POWER_SAFETY_BLOCKED
```

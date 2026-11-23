# SSP-0025 — Power Safety Assessment (Prompt 05_8 §1/§4/§6)

**Agent:** DeepSeek-V4-Pro-Thinking
**Date:** 2026-11-22
**Scope:** Source-backed shared-rail risk assessment. **No power transition performed.**

---

## 0. Conclusion

The shared-consumer safety of `vdd_mcu_1p8` **cannot be established from source alone**.
A `regulator_force_disable()` on this rail will drop **every** consumer's reference
count. If the GNSS RF block is electrically on the same physical rail, GNSS will
cycle as well. This must be an explicit, separately-authorized, bounded trial — and it
MUST NOT be triggered by any automatic/service path.

This is a **BLOCKED_POWER_SAFETY** condition for *automatic* rail cycling, but a
*bounded, operator-supervised* cold-cycle remains permissible **only under separate
owner authorization** (which has NOT been granted).

---

## 1. The two distinct controls (do not conflate)

| Control | Physical meaning | Software owner | Mission status |
|---|---|---|---|
| `vdd_mcu_1p8` regulator | BCM47752 **MCU** 1.8 V rail | `ssp_dev.c` → `mcu_power` sysfs | the candidate's force-disable target |
| `GPS_PWR_EN` (gpio-145) | BCM47752 **GNSS stand-by** | `bcm_gps_spi.c` | **NEVER TOUCH** (documented reboot hazard) |

`GPS_PWR_EN` is a GNSS standby GPIO, NOT the MCU regulator control. Driving it high
twice rebooted the phone (documented in `hw/NUXEL_03_BCM47752_SENSORS_STANDALONE.md`).
This mission does not and will not manipulate `GPS_PWR_EN`.

## 2. Shared-rail risk (unresolved, must gate)

- Live state (read-only): `vdd_mcu_1p8 state=enabled, num_users=0`; `GPS_PWR_EN out lo`.
- The two *software* controls are distinct, but a **shared physical rail** between
  MCU and GNSS RF cannot be excluded from source alone (0025's own AUDIT note).
- A `regulator_force_disable` drops every reference; if GNSS shares the rail, GNSS
  briefly powers off and re-on within the same bounded operation.

### Decision rule (honoring §1 "If shared-consumer safety cannot be established, do not perform a forced power transition")

- **Automatic / periodic / service-retry cold-cycle:** FORBIDDEN (BLOCKED_POWER_SAFETY).
- **Bounded operator-supervised cold-cycle:** only under separate owner authorization,
  with `echo 0 > mcu_power` followed by `echo 1` in the same closely-bounded operation,
  and with pre/post evidence of independent regulatory state + GNSS health.

No such authorization has been granted in this prompt.

## 3. The 0025 sysfs path is safe from uncontrolled retries

The 0025 correction changes only `set_mcu_power()` `case 0`, which is reachable
**exclusively** via an explicit `echo 0 > /sys/.../mcu_power` sysfs write. There is
no automatic loop, no periodic worker, and no service-retry path that reaches it.
`case 1` (unconditional `regulator_enable`) restores the reference in the same
operator sequence. This satisfies §2.6 "verify the proposed cold-cycle cannot be
triggered by uncontrolled service retries" — it cannot.

## 4. What a bounded, authorized trial would require (not executed)

1. Confirm no competing transport owner (verified read-only: no process holds tty/bbd).
2. Capture pretrial `vdd_mcu_1p8 state/num_users`, `GPS_PWR_EN`, IRQ 441/443 counts, SIP state.
3. `echo 0 > mcu_power` → poll `regulator_is_enabled()==0` (evidence gate, not the API return).
4. `echo 1 > mcu_power` → poll `regulator_is_enabled()==1`.
5. Immediately run `--rom-probe` (autobaud + GetVersion).
6. Restore rail on any failure; verify GNSS/sensorhub health.
7. Max one cold-cycle per session; abort on reboot/hang/GPIO change.

## 5. Verdict

**BLOCKED_POWER_SAFETY** for any *automatic* rail transition.
A *bounded operator-supervised* cold-cycle is **AWAITING_POWER_TRIAL_AUTHORIZATION** and
separate from any BOOT-flash authorization. Neither has been granted.

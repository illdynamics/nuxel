# SSP-05_13 — Vendor Power Sequence (recovered from stock source)

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 1. Objective

Recover the exact Samsung/Broadcom BCM47752 power-on and ROM-communication
sequence from trustworthy source, and determine which event is missing in the
Nuxel native-Linux bring-up.

## 2. Recovered call graph

```
bcm_spi_probe()                                  bcm_gps_spi.c:1153
 ├─ of_get_named_gpio("ssp-gps-pwr-en")  → gpg0-2  (GPS_PWR_EN)
 ├─ of_get_named_gpio("ssp-mcu-req")     → gpg4-1  (MCU_REQ)
 ├─ of_get_named_gpio("ssp-mcu-resp")    → gpg4-2  (MCU_RESP)
 ├─ gpio_direction_output(mcu_req, 0)
 ├─ gpio_direction_output(gps_pwr_en, 0)   <-- GPS_PWR_EN set LOW (never reasserted)
 ├─ gpio_export_link(sec/gps, "GPS_PWR_EN", gps_pwr_en)  <-- userspace gpsd owns it
 ├─ request_irq(host_req → ttyBCM)
 ├─ misc_register("ttyBCM")
 └─ bbd_init(&spi->dev)

bbd_init() → registers LHD (gpsd) transport, /dev/bbd_patch, /dev/bbd_control
```

The **stock power-on ordering is performed by userspace `gpsd`**, not the
kernel.  The kernel only *prepares* the GPIOs (LOW = power-down) and exports
`GPS_PWR_EN` so `gpsd` can sequence it.

## 3. The missing step (root cause)

| # | Event | Owner | Nuxel state |
|---|---|---|---|
| 1 | `vdd_mcu_1p8` rail ON (LDO21M) | regulator core / SSP driver | ON (num_users=0, always-on) |
| 2 | **`GPS_PWR_EN` = HIGH (gpg0-2)** | **userspace gpsd** | **LOW — NEVER ASSERTED** |
| 3 | GNSS boot-ROM starts, waits for autobaud | chip (after power) | not reached |
| 4 | MCU_REQ/RESP hello handshake | `bcm477x_hello()` | code present, but chip powered down |
| 5 | Autobaud 32 × 0x80 | `bcm477x_rpc_get_version()` | sent, no reply |
| 6 | GetVersion RPC + response | ROM | rx=0 (chip dead) |

**Conclusion:** the GNSS boot-ROM never runs because `GPS_PWR_EN` (the GNSS
domain enable) is held LOW.  The kernel-side ROM protocol
(`bcm477x_rpc_get_version()`) is correct; it simply cannot reach live silicon
because the domain is power-gated.

## 4. Evidence for the sequence

- `bcm_gps_spi.c:1204-1225` — GPS_PWR_EN requested, set output LOW, exported.
  The immediately-preceding commented block is labeled "GPS_PWR_ON", proving
  the original Samsung source *had* a power-on request that is now commented
  out in favour of gpsd-owned control.
- `bcm_gps_spi.c:496-538` — `bcm477x_hello()` toggles `mcu_req`/polls
  `mcu_resp`; this is the transport-level wake, not the domain power.
- `bcm_gps_regs.c:46-158` — `bcm477x_rpc_get_version()` autobaud + GetVersion
  RPC, with no GPS_PWR_EN manipulation.
- `bcm_gps_mem.c:235` and `bcm_gps_mem.c` dump — the `gpio_set_value
  (priv->mcu_req, 1); mdelay(15)` "hello" is commented out, consistent with
  MCU_REQ being the wake line, not GPS_PWR_EN.

## 5. Exact sequencing/timing (trustworthy values only)

The only **vendor-authored** timing values present in source:

- `MAX_RESP_CHECK_COUNT 100` → MCU_RESP poll budget ≈ 100 ms
  (`bcm_gps_spi.c:498`).
- MCU_REQ re-toggled every 20 iterations with 1 ms deassert/reassert
  (`bcm_gps_spi.c:520-526`).
- ROM GetVersion poll: 20 ms granularity, `delta > 1000` loop bound
  (`bcm_gps_regs.c:118-145`).
- No vendor value for a GPS_PWR_EN rise→ROM-ready delay exists in this tree.
  Any such value must come from Broadcom datasheet or gpsd disassembly, which
  are not present.  **This is a documented uncertainty, not an invented value.**

## 6. Reconciliation of the apparent contradiction

The two conclusions ("GPS_PWR_EN is a GNSS standby signal, not an MCU power
substitute" and "GPS_PWR_EN gates the BCM47752 logic/SPI") are **both true**
because the die has multiple power domains:

- As an **MCU/sensor-hub power substitute** the signal is wrong — that domain
  is `vdd_mcu_1p8` (regulator) with no GPIO gate on this board.
- As the **GNSS domain enable**, `GPS_PWR_EN` does gate BCM47752 GNSS logic and
  therefore the SPI **slave for the GNSS boot-ROM**.  So "gate the logic/SPI
  interface" is correct **for the GNSS core**, not for the sensor-hub MCU.

The earlier interpretation was not wrong, just over-scoped: `GPS_PWR_EN` is not
a *substitute* for MCU power, but it *is* a *separate required enable* for the
GNSS ROM path that is currently unasserted.

## 7. Missing evidence (cannot be sourced locally)

1. Broadcom BCM47752 datasheet sequence (GPS_PWR_EN rise → ROM Ready timing,
   any required delay after power).
2. Samsung `gpsd`/`lhd` disassembly for the exact GPS_PWR_EN assertion order
   and post-power delay (the `05_12` report referenced an lhd VA 0xdfe4 for
   autobaud length only).
3. Confirmation that asserting GPS_PWR_EN HIGH in Nuxel does not energise GNSS
   RF in a way that is unsafe/unauthorized (RF domain alongside logic).

These are the minimum additional evidence for a safe physical trial (see
PHYSICAL-TRIAL-DECISION.md).

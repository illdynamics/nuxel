# SSP — BCM47752 MCU Power Root Cause (Live-Verified)

**Prompt:** 05_7 (POWER-STATE RECOVERY & ROM FIRST LIGHT)
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X, SSH 10.11.12.99
**Date:** 2026-11-22 (Europe/Amsterdam)
**Scope:** Read-only live baseline + source-verified root-cause analysis. **No rail/reset/GPIO/standby state change performed.**

---

## 0. Verdict up front

The MCU is **powered (rail ON) but the kernel holds ZERO regulator references**,
so no deployed code path can perform a genuine cold power-cycle to re-enter the
BCM47752 boot-ROM autobaud window. Every firmware-download attempt therefore
meets a silent ROM (SPI MISO idle `0xFF`, `HSI_CTRL=0xFFFFFFFF`, `rx=0`).

This is **not** an SPI electrical fault, **not** a userspace routing defect (that
was already fixed and proven correct in PROMPT 05_6), and **not** a protocol
framing error (untestable until the ROM answers). It is a **power-sequencing
defect**: the deployed kernel's cold-cycle recovery uses a plain
`regulator_disable()` that is a documented no-op when `num_users==0`, so the rail
never physically falls and the ROM never re-enters its download state.

**Classification (per §2 of the prompt):** MCU is **powered but running outside the
boot-ROM communication window** (the ROM autobaud window from the last physical
power-on has long since closed; a warm boot cannot re-open it without a genuine
rail drop).

---

## 1. What `GPS_PWR_EN`, `reset_info`, `shutdown`, `resetting`, `host_req`, and the regulator APIs actually mean

This is the core of the prompt's "do not assume a GPIO label proves physical
ownership of a rail" instruction. The labels were historically conflated; they
are **three distinct controls**.

### 1.1 `vdd_mcu_1p8` regulator — the SENSOR-HUB MCU rail (the real power)

- Regulator node: `/sys/devices/platform/15970000.speedy/i2c-16/16-0000/s2mps19-regulator/regulator/regulator.62`
- `name` = `vdd_mcu_1p8`, `microvolts` = 1800000, fixed 1.8 V.
- **Live read (this session): `state=enabled`, `num_users=0`.**
- Kernel owner: `ssp_dev.c` acquires it (`regulator_get(NULL, "vdd_mcu_1p8")`) and
  0023 adds `regulator_enable()` at probe. The vendor `lhd` daemon was the
  original runtime owner of this rail.
- Vendor `lhd.conf` maps this to `GpioNPowerPath=/sys/class/sec/sensorhub/mcu_power`
  — i.e. the **sysfs `mcu_power`** node, whose `case 0/1` bodies call
  `regulator_disable`/`regulator_enable` (0025/0027 make the disable a
  `regulator_force_disable`).

**Decisive finding:** `num_users=0` while `state=enabled` proves the rail is
physically ON but held by **zero** kernel references (the bootloader/PMIC left it
up, and no `regulator_enable()` reference survived to userspace). Under
`regulator_disable()`, a regulator whose `use_count` is already 0 returns
`-EINVAL` ("unbalanced disable") as a **no-op**: the rail never falls.

### 1.2 `GPS_PWR_EN` (gpio-145 / gpg0-2) — the GNSS power, NOT the MCU rail

- Live read: `/sys/devices/virtual/sec/gps/GPS_PWR_EN` → value `0`, direction `out`
  (output-low). Symlink target `gpiochip50/gpio/gpio145`.
- Kernel owner: exported by `bcm_gps_spi.c` probe via `sec_device_create("gps")` +
  `gpio_export_link`; probe sets `gpio_direction_output(gps_pwr_en, 0)`.
- Vendor `lhd.conf` maps this to `GpioNStdbyPath=/sys/class/sec/gps/GPS_PWR_EN/value`
  — the **GNSS stand-by** path, a *separate* control from `mcu_power`.
- **Documented hazard:** `hw/NUXEL_03_BCM47752_SENSORS_STANDALONE.md` §Baseline
  records that driving gpio-145 high **rebooted the phone twice**. It is a known
  danger, not a debugging shortcut.

### 1.3 `reset_info` = `"GPS OFF"`

`reset_info_show` (ssp_sysfs.c, `DEVICE_ATTR(reset_info, 0440, ...)`) is a
**read-only status string**. `"GPS OFF"` reflects the internal GNSS/SSP power
state bit (`data->…` GPS tracking off), i.e. the GNSS domain is reported off.
It is a **cached software state**, not a measured rail voltage. Live value this
session: `GPS OFF`.

### 1.4 `shutdown` / `resetting` (hub diag)

`nuxel_hub_diag` (0023, `show_nuxel_hub_diag`) prints:
`mcu_probe=1 shutdown=1 resetting=1 sensor_state=0x3feff enable=0x0 shub_irq=443`.
- `shutdown=1` → `data->bSspShutdown == true`. Upstream leaves this true until
  `lhd` sends `ESW:READY`; 0023 flips the probe default to `false`, but a prior
  failed handshake (`clean_msg` → dead hook) can re-raise it. The live reading
  means the hub is held in the "shutdown" software state.
- `resetting=1` → `data->resetting == true`, set by `bbd_mcu_reset(true)` on a
  failed `hello`. It means "a reset was requested / hub reported no-resp", NOT a
  measured pin state.

### 1.5 `host_req` (the MCU → AP data-ready line)

`nuxel diag` prints `host_req=0 mcu_req=0 mcu_resp=1 irq_en=0 irq_cnt=0 tx=80 rx=0`.
- `host_req=0` → the MCU is **not** asserting its data-ready line. Combined with
  `irq_cnt=0` (the `ttyBCM` IRQ 441 never fired), this is the transport-level
  proof that the ROM is silent — the MCU is not driving MISO nor the request line.
- `mcu_resp=1` is a **GPIO pull-up handshake line**, not a protocol reply; its
  high state does not prove the hub is answering (documented in §2.4 of the
  cold-start timeline and vendor-parity §7.5).

---

## 2. Source-backed dependency graph

```
                          ┌─────────────────────────────────────────────┐
                          │  BCM47752 boot-ROM download (RPC 0 GetVersion) │
                          └─────────────────────────────────────────────┘
                                          ▲  requires ROM in autobaud window
                                          │
   [vdd_mcu_1p8]  ──(real MCU rail)──►  MCU cold power-on
      1.8V fixed        state=enabled
      num_users=0       (no kernel ref)  ──► ROM window ALREADY CLOSED (warm boot)
      owner: ssp_dev.c                   ──► plain regulator_disable() = NO-OP
      sysfs: mcu_power                   ──► need regulator_force_disable() + enable()
                                          │
   [GPS_PWR_EN gpio145] ──(GNSS stand-by, SEPARATE)──► GNSS RF domain
      out lo (0)          NOT the MCU rail                    │
      hazard: driving high rebooted phone twice              (do NOT touch)
                                          │
   [SPI spi17 / 10970000.spi]  ──► SSI transport (half-duplex)
      0020: re-init after runtime suspend; tx=80 rx=0
                                          │
   [IRQ 441 "ttyBCM"]  = gpio_to_irq(host_req); held disabled at probe
                                         depth-1; armed on /dev/ttyBCM open
                                          │
   [clock] SPI 25 MHz (controller), gated by runtime PM; 0020 restores hwinit
```

### Ownership map (kernel vs userspace)

| Control | Kernel owner | Userspace trigger | Proven? |
|---|---|---|---|
| `vdd_mcu_1p8` regulator | ssp_dev.c (`regulator_get` + enable) | `mcu_power` sysfs (case 0/1) | S (patch) + M (`num_users=0`) |
| `GPS_PWR_EN` gpio145 | bcm_gps_spi.c (export + direction) | GNSS userspace (`GPS_PWR_EN/value`) | S + M (value=0) |
| host_req IRQ 441 | bcm_gps_spi.c (request + disable@probe) | /dev/ttyBCM open arms | S + M (`irq_cnt=0`) |
| SPI controller | spi-s3c64xx.c | tty write → bcm_spi_sync | S + M (`tx=80`) |
| `reset_info` | ssp_sysfs.c (read-only) | — | S + M (`GPS OFF`) |
| `shutdown`/`resetting` | ssp_bbd.c/ssp_dev.c flags | bring-up / failed hello | S + M |

### Proven electrical vs naming-convention

- **PROVEN (measured this session):** `vdd_mcu_1p8` `state=enabled` + `num_users=0`;
  `GPS_PWR_EN` out-low; `host_req=0`, `irq_cnt=0`, `tx=80 rx=0`.
- **PROVEN (source):** `regulator_disable()` is a no-op at `num_users==0`
  (Linux regulator core returns `-EINVAL` "unbalanced" for a get/put pair with
  no enable reference); `regulator_force_disable()` drops the rail regardless.
- **HYPOTHESIS→CONFIRMED (0025):** the bootloader leaves `vdd_mcu_1p8` enabled
  with `num_users==0` — now measured true (`num_users=0`).
- **CLASSIFIED UNRESOLVED (per §2):** whether `vdd_mcu_1p8` is *electrically
  shared* with GNSS. The two *software* controls (`mcu_power` vs `GPS_PWR_EN`)
  are distinct, but a shared physical rail between the sensor-hub MCU and the
  GNSS RF block cannot be excluded from source alone. A `regulator_force_disable`
  on `vdd_mcu_1p8` will drop **every** consumer's reference; if GNSS shares that
  rail, GNSS will also cycle. This must be in the authorization gate.

---

## 3. Required boot-ROM entry sequence (source-verified)

1. Genuine cold rail: `regulator_force_disable(vdd_mcu_1p8)` → rail falls →
   `regulator_enable(vdd_mcu_1p8)` → MCU re-enters ROM.
2. `msleep` ~300 ms after rail settle (ROM boot; the vendor parity doc flags all
   delays as placeholders — poll `regulator_is_enabled()` as the evidence gate).
3. Raw SSI autobaud: 32 × `0x80` (vendor `bcm477x_rpc_get_version`) — reconcile
   with the 36-byte lhd form (VA 0xdfe4) as a bounded secondary (already in
   `--rom-probe`).
4. `GetVersion` (RPC 0) reliable — the *only* ROM identity exchange the trial
   requires.
5. (Only after ROM identity, separately authorized) 479 × MemoryWrite (RPC 5) →
   StartScratchApp (RPC 46) → ServiceStart (RPC 55) → confirm GetVersion.

---

## 4. Why `--rom-probe` returns `rx=0` (the exact defect chain)

1. `--rom-probe` opens `/dev/ttyBCM`, sends autobaud + GetVersion → **TX reaches
   SPI** (`tx` went 32 → 80 in the prior trial). RX path is correct (fixed in
   05_6): raw SSI bytes surface on `/dev/ttyBCM`.
2. But the MCU never drives MISO or `host_req` because the ROM is **not** in its
   autobaud/window state — it is in post-boot idle (HSI uninitialized:
   `HSI_CTRL=0xFFFFFFFF`, `rx stat 0xff(PE)`, `rx_strm_fifo_ovfl`).
3. The ROM window only opens on a **genuine cold power-on**. The deployed kernel
   (0020+0023 only; confirmed via kallsyms: `nuxel_ssp_bringup_hw` present but
   `nuxel_ssp_dl_download`/`dl_*` absent) has **no** path that produces a genuine
   cold cycle:
   - its `nuxel_ssp_bringup_hw()` recovery uses plain `regulator_disable()`
     (= no-op at `num_users==0`),
   - 0025 (`regulator_force_disable` in `mcu_power` case 0) and 0027 (kernel
     downloader) are **not deployed**.

Therefore rx=0 is a **power-sequencing root cause**, and the correction is to
deploy a path that (a) force-disables then re-enables `vdd_mcu_1p8` (a real
cold cycle) and (b) drives the ROM sync at that exact moment. This is the
`POWER_FIX_IMPLEMENTED` scope of the companion report.

---

## 5. Smallest distinguishing observations (already gathered)

| Case (MCU state) | Distinguishing observation | Live value | Verdict |
|---|---|---|---|
| Fully unpowered | `vdd_mcu_1p8` state=disabled | `enabled` | NOT this |
| Powered, held reset | `resetting=1` + rail on | `resetting=1`, rail on | partially |
| Powered, shutdown/standby | `shutdown=1` | `shutdown=1` | partially |
| Powered, no clock | SPI reads stable 0xFF, HSI=FFFFFFFF | matches | contributing |
| Running, outside ROM window | tx ok, rx=0, host_req=0, irq_cnt=0 | **matches exactly** | **PRIMARY** |
| Running, wrong SPI RX | (eliminated: RX path proven correct in 05_6) | — | ruled out |

**Conclusion:** powered but **outside the boot-ROM communication window**, with a
deployed kernel that cannot re-open that window (no genuine cold-cycle path).

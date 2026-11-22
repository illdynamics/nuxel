# SSP — Cold-Start Timeline: Measured Evidence vs Hypotheses

**Stage:** 03. **Date:** 2026-11-22. **Hardware:** none touched.
**Purpose:** separate every claim into (M) measured-on-device, (S) source-derived
static fact, and (H) hypothesis/placeholder, then choose the least invasive
viable firmware-load architecture and the moment when the MCU is *actually*
ready.

---

## 1. The reported blocker, restated precisely

`ssp.md` and `report-ssp-prompt-00.md` record, from a live read-only baseline:

- `mcu_name=BCM47752KUB1G`, `mcu_rev=BR0121080900,BR010`, `mcu_reset=OK`
- `nuxel_hub_diag = mcu_probe=1 shutdown=1 resetting=1 sensor_state=0x3feff enable=0x0 shub_irq=443`
- **`tx=184 rx=0`** — 184 bytes transmitted on the SPI transport, **zero** RX.

The boot ROM never returns `GetVersion`. Root cause is **not proven**; the
three candidate causes from Stage 01 remain:

1. (rail/timing) warm reset never re-enters the ROM autobaud window,
2. (electrical) SPI clock/mode/IRQ fault (e.g. `0xFF` idle, runtime-suspend HW
   re-init loss),
3. (protocol) framing/autobaud-length mismatch.

---

## 2. Timeline — measured vs hypothesis

### 2.1 MCU rail `vdd_mcu_1p8` on/off
- **(H)** The bootloader leaves `vdd_mcu_1p8` **enabled with `num_users == 0`**,
  so a plain `regulator_disable()` is an "unbalanced disable" no-op and the
  rail never physically falls; a warm reboot therefore never re-enters ROM.
  **Source:** the comment embedded in patch `0025-nuxel-ssp-rail-force-coldcycle.patch`
  and the `nuxel_ssp_bringup_hw()` comment in `ssp_bbd.c`. **Not measured:** no
  live `regulator_is_enabled()` readback or `regulator_get_voltage`/consumer
  refcount capture was taken as evidence.
- **(S)** `regulator_vdd_mcu_1p8` is acquired at `ssp_dev.c` probe and enabled
  there; `set_mcu_power` and the bring-up recovery path are the only two places
  that can change it. `regulator_force_disable` (the 0025 change) detaches
  **every** consumer reference; the rail may be shared with GNSS — a
  force-disable drops GNSS too. **Must never be on an automatic/service loop.**

### 2.2 SPI clocks and IRQ availability
- **(S)** `spi->irq = gpio_to_irq(host_req)` is derived at
  `bcm_gps_spi.c` probe because the DT `interrupts` cell is 0. The IRQ is
  `request_irq(… IRQF_TRIGGER_HIGH …)` then **`disable_irq()`** (held at depth 1)
  until `bcm_ssi_enable_irq`.
- **(H→S)** After runtime suspend the SPI controller loses its FIFO/mode config
  and reads `0xFF` until `s3c64xx_spi_hwinit()` is re-run. This is the *rationale*
  of patch `0020-nuxel-ssp-spi-runtime-reinit.patch` (`need_hw_init=1` on
  `DOMAIN_TOP` suspend). **Source-verified** against `spi-s3c64xx.c`
  `s3c64xx_spi_runtime_suspend()`, but the live "0xFF after idle" reading was
  reported, not re-measured in Stage 03.

### 2.3 Warm reset → ROM re-entry
- **(H)** Whether a warm reset re-enters the boot ROM autobaud window is the
  *consequence* of the rail hypothesis: if the rail never physically falls, the
  ROM is never re-entered. **Not measured.** The intended cold-cycle evidence
  (rail actually reaching 0 V, then boot ROM returning `GetVersion`) does not
  exist yet.

### 2.4 `mcu_resp=1` meaning
- **(S, DEFINITIVE)** `mcu_resp` is a **GPIO handshake line**, not a protocol
  reply. `bcm477x_hello()` (bcm_gps_spi.c) sets `mcu_req=1` and polls
  `gpio_get_value(mcu_resp)` with a 100-ms budget; `mcu_resp=1` means "the chip
  asserted its awake/handshake line", **not** that any SSI/RPC byte arrived.
  The live `rx=0` is fully consistent with `mcu_resp=1` while the boot ROM is
  silent.

### 2.5 SPI `0xFF` reading
- **(S, DEFINITIVE)** `0xFF` on MISO is **electrical idle** (the line held high
  when the slave drives nothing), **not** a protocol reply. It is meaningless
  as a version/ACK. The decoder treats `0xFF` as garbage bytes (it never forms
  a valid ESC/SOP sequence).

---

## 3. Boot-chain / power design options (offline comparison)

| option | where firmware loads | power/rail implications | invasiveness |
|---|---|---|---|
| **kernel-coordinated** (chosen) | in `nuxel_ssp_bringup_hw()` / downloader in kernel | kernel already owns the regulator reference and GPIOs; single owner; cold-cycle is a bounded explicit op | **lowest** (kernel is the single owner; no new boot stage) |
| early-userspace | initramfs script before fs mount | would need to reach deferred probe + regulator + GPIO from userspace; splits MCU ownership across boot stages | higher (new coordination surface) |
| initramfs | very early (before `/dev` populated) | cannot rely on SPI/regulator/GPIO being probed yet; would fight the kernel probe | highest (ordering hazards) |

**Chosen: kernel-coordinated, single owner.** Rationale:
- The kernel already probes the SSP SPI node, acquires the regulator, requests
  the IRQ (held disabled), and sets up GPIO directions — it is the natural
  single owner of MCU power and BBD transport.
- The downloader already exists in the kernel (`nuxel_ssp_dl_download`), invoked
  **only** from the `nuxel_ssp_bringup_hw` recovery path after a genuine power
  cycle — i.e. at the only moment the MCU is *actually* cold-booted and able to
  enter ROM.
- Early-userspace/initramfs would *add* a second owner and a new boot-stage
  dependency for no measured benefit.

### Least-invasive viable design
1. Bounded, operator-initiated cold-cycle (`echo 0 > mcu_power` → wait for rail
   to fall → `echo 1`) — **not** an automatic loop.
2. Kernel bring-up triggers the two-phase download only after the rail is
   provably re-enabled (measure `regulator_is_enabled`, not a sleep).
3. Every delay (`150/120/300 ms`) replaced by an *evidence gate*: poll for the
   actual condition (IRQ armed, `host_req` state, first valid `GetVersion` byte)
   with a bounded timeout, not an arbitrary `sleep`.
4. No speculative GPIO/reset steps: the only GPIO writes are the already
   audited `mcu_req` (hello handshake) and `gps_pwr_en` (export-only at probe);
   `mcu_power` sysfs is the single rail control point.

---

## 4. Preflight acceptance criteria (each firmware stage)

| stage | conclusive preflight (no live HW yet) | live-conclusive (requires session) |
|---|---|---|
| identity | deterministic recompute of §1 identity | container matches `0x00800161` + records |
| ROM sync | corpus replay shows autobaud+GetVersion frame decodes; **autobaud 32-vs-36 reconciled** | a real `GetVersion` reply with correct CRC |
| transfer | 479 `F1` → 479 `MemoryWrite` encoded; parser exact EOF; non-F1 refused | each write transport-ACKed, no stale ACK |
| app start | `StartScratchApp`/`ServiceStart` bytes encoded | post-download `GetVersion` version matches |
| READY | `ESW:READY` code path gated behind all of above | `ESW:READY` emitted only on verified success |

**PASS** for Stage 03 (offline) is: identity recomputed, framing/CRC/RPC
source-verified, replay corpus reproducible, cold-start claims separated into
M/S/H, and a single-owner architecture chosen with no new sleep/GPIO spec. The
**hardware** PASS remains: real `GetVersion` reply, all 479 writes ACKed,
post-download version confirmed, WHOAMI `0x55`, `sensor_state` non-zero, and
real accel/gyro streaming — none of which is claimed here.

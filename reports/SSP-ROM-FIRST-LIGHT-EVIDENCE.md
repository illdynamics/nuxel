# SSP — ROM First-Light Physical Trial Evidence (Honest)

**Date:** 2026-11-22 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking (PROMPT 05_6)
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X, SSH 10.11.12.99
**Trial mode:** `--rom-probe` (ROM-identity-only; NO MemoryWrite, NO app-start, NO rail/reset/GPIO).

---

## 0. Result

| Gate | Required result | Actual |
|---|---|---|
| Nuxel boot | PASS | PASS (`4.14.253-gf7194c1d15ed-dirty`, systemd running, 0 failed units) |
| BOOT unchanged | PASS | PASS (`0e6aa34c…`) |
| DTB unchanged | PASS | PASS (`abc9d45d…`) |
| DTBO unchanged | PASS | PASS (`de3bc025…`) |
| Correct raw RX endpoint | PASS | PASS (reads `/dev/ttyBCM`) |
| Single transport owner | PASS | PASS (no process holds bbd/tty nodes) |
| ROM-only safety boundary | PASS | PASS (regression-proven, only RPC 0 emitted) |
| Offline regression tests | PASS | PASS (16 negative cases + 77 + 14) |
| Physical SPI transfer | Evidence required | PASS (tx 32 → 80; SPI TX occurred) |
| Genuine ROM response | Evidence required | **FAIL** (rx=0, no reply) |
| GetVersion validation | Evidence required | **FAIL** (no reply to validate) |
| Firmware transfer | NOT ATTEMPTED | NOT ATTEMPTED |
| SSP WHOAMI | NOT CLAIMED | NOT CLAIMED |
| Accelerometer | NOT CLAIMED | NOT CLAIMED |
| Gyroscope | NOT CLAIMED | NOT CLAIMED |

**ROM first light did NOT pass.** The boot-ROM did not answer GetVersion. The result is honest; no success is manufactured.

---

## 1. Pre-trial verification (all prerequisites met)

| Check | Value | Verdict |
|---|---|---|
| Kernel | `4.14.253-gf7194c1d15ed-dirty` | PASS (matches baseline) |
| systemd | running, 0 failed units | PASS |
| BBD nodes | `/dev/ttyBCM`(10,91) `/dev/bbd_sensor`(236,1) `/dev/bbd_control`(236,2) `/dev/bbd_patch`(236,3) | PASS (present) |
| SPI device | `spi17.0` `DRIVER=brcm gps spi` `OF_NAME=BCM4773` | PASS |
| Transport owner | 0 processes holding bbd/tty FDs | PASS (single-owner) |
| Deployed binary hash | `1900234a…` (host) / `5f05dba1…` (native) | PASS (tested build; source hash identical) |
| BOOT hash | `0e6aa34cdc550fd975129d9fc0f9dc785733e0483e3b8c119eb4592b5463621c` | PASS (unchanged) |
| DTB hash | `abc9d45d3745866346fd94c7c04028cc2c62ade4dd274b400dbbfec0c2ef4780` | PASS (unchanged) |
| DTBO hash | `de3bc02526c66647992a744608fdf61548823866e822a7400619d74126095c23` | PASS (unchanged) |
| Recovery hash | `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87` | PASS (unchanged) |

Safety boundary verified: the `--rom-probe` build **cannot** emit MemoryWrite/StartScratchApp/ServiceStart (regression-proven) and performs no rail/reset/GPIO/write-operations.

---

## 2. Trial execution (exact, timestamped)

```
2026-11-22T17:27:05Z  ROM-IDENTITY TRIAL START
bbd-flash: container 897113 B asic=0x004775b0 blobLen=438895 entry=0x00800161 crc_hdr=0x000000c1 decoded=438895
bbd-flash: patch verified: 479 records (BCM47752, entry=0x00800161)
bbd-flash: first memory-write dest=0x00800000 (entry=0x00800161)
bbd-flash: control: SSI:PassThru=1
bbd-flash: autobaud sent (32 x 0x80)
bbd-flash: reliable_rpc id=0: no reliable ACK for seq 2 within 2500 ms (retries=0)
bbd-flash: autobaud=32: no valid GetVersion reply (packets=0 crc_err=0 malformed=0 rpc=0)
bbd-flash: autobaud sent (36 x 0x80)
bbd-flash: reliable_rpc id=0: no reliable ACK for seq 3 within 2500 ms (retries=0)
bbd-flash: autobaud=36: no valid GetVersion reply (packets=0 crc_err=0 malformed=0 rpc=0)
bbd-flash: boot ROM handshake: no valid GetVersion reply (packets=0 crc_err=0 malformed=0 rpc=0)
bbd-flash: control: BBD:PassThru=0
bbd-flash: exit 3 (ROM_HANDSHAKE_TIMEOUT)
2026-11-22T17:27:10Z  ROM-IDENTITY TRIAL END (rc=3)
```

- Patch identity: VALID (479 records, matches embedded blob identity).
- Autobaud 32 and 36 both sent; GetVersion submitted; **zero reply** on both.
- Exit 3 = `ROM_HANDSHAKE_TIMEOUT` (honest).
- `ESW:READY` NOT emitted; `BBD:PassThru=0` restored.

---

## 3. Controller / transport diagnostics (where RX fails)

Pre-trial diag:
```
[SSPBBD] nuxel diag: host_req=0 mcu_req=0 mcu_resp=1 irq_en=0 irq_cnt=0 tx=32 rx=0
GPS_PWR_EN (gpio-145) = out lo
MCU REQ   (gpio-167) = out lo
MCU RESP  (gpio-168) = in  hi
```

Post-trial diag (TX counter advanced 32 → 80, confirming the tool's SPI writes DID reach the controller):
```
[SSPBBD] nuxel diag: host_req=0 mcu_req=0 mcu_resp=1 irq_en=0 irq_cnt=0 tx=80 rx=0
```

SPI controller errors during the trial (the decisive evidence):
```
s3c64xx-spi 10970000.spi: Set SPI clock rate: 25000000(100000000)
[SSPBBD]: REG HSI_CTRL @ : [FFFFFFFF] ...          (HSI uninitialized / idle)
[SSPBBD]: bcm_ssi_tx @ FD Nread 65535 is h/w overflowed of frame 8187...Fail
[SSPBBD]: bcm_ssi_tx @ FC Bwritten 65535 of 11...Fail retries 2/3/4
[SSPBBD]: REG(R) HSI_ERROR_STATUS(R) @ [2C]: 000000FF
[SSPBBD]: DBG SPI @ PZC: rx stat 0xff(PE) avail 114688, (rx_strm_fifo_ovfl)
```

Sensor-hub state:
```
nuxel_hub_diag: mcu_probe=1 shutdown=1 resetting=1 sensor_state=0x3feff enable=0x0 shub_irq=443
mcu_test       = NG,NG,NG
reset_info     = "GPS OFF"
mcu_reset      = "OK" (status string, not a live power state)
enable         = 0
```

Interrupt counters (unchanged — no host-req fire):
```
441: ttyBCM      count=0   (host-req data-ready line: NEVER fired)
443: ssp-shub-int count=1  (shub-int: one historical edge)
209: 10870000.hsi2c (irq 443) count=0
```

---

## 4. Root cause — narrowed, evidence-backed

The receive-path fix is **correct and not the cause of rx=0**. The evidence localizes the failure:

1. **Userspace routing is FIXED and PROVEN correct**: the tool reads `/dev/ttyBCM`, no peer is held, so raw SSI bytes would be delivered to the tool's `read()`. There is no routing defect remaining.
2. **Kernel delivery path is intact**: SPI TX reaches the controller (`tx` advanced), the tty read path exists, the IRQ is armed on open.
3. **The MCU never responds because it is not powered/awake for the boot-ROM autobaud window.**
   - `reset_info = "GPS OFF"` and `GPS_PWR_EN (gpio-145) = out lo` → the BCM47752 power is gated OFF.
   - `HSI_CTRL = FFFFFFFF`, `rx stat 0xff(PE)`, `rx_strm_fifo_ovfl`, `Nread 65535` → the host reads all-ones MISO (idle/floating) and the half-duplex handshake times out.
   - `host_req=0`, `irq_cnt=0` → the MCU never asserts its data-ready line.
   - `shutdown=1 resetting=1` → the kernel's view is "halted/reset".

**Conclusion:** rx=0 is a **cold-power/handshake defect** (the boot-ROM autobaud window never opens because the MCU power is OFF), NOT an SPI electrical bus fault and NOT a userspace receive-node defect. This is consistent with the deferred 0025 (`nuxel-ssp-rail-force-coldcycle`) hypothesis and the documented `bcm477x_hello` power sequencing, but that fix is **NOT within this prompt's authorization** (rail/reset/GPIO manipulation is explicitly excluded).

---

## 5. Failure classification (per §5 failure criteria)

| Failure mode observed | Yes/No |
|---|---|
| RX remains zero | YES |
| Reply all-0xFF | YES (MISO idle `0xff`) |
| Transfer times out | YES |
| Response fails validation | N/A (no response) |

Per the criteria, the trial was **stopped**, the exact evidence preserved, and the failing receive-chain layer identified: **controller operation / MCU power-sequencing (boot-ROM never awake)**, NOT userspace routing, NOT kernel delivery, NOT protocol framing (untestable until the ROM answers).

---

## 6. What was NOT done (authorization boundary respected)

- No MemoryWrite (RPC 5) records.
- No StartScratchApp (RPC 46) / ServiceStart (RPC 55).
- No `nuxel_bringup`, `mcu_power`, `GPS_PWR_EN` write, or `nuxel_stream` trigger.
- No regulator rail cycling, reset, or standby GPIO manipulation.
- No kernel/BOOT/TWRP/DTB/DTBO writes.
- No repeated hardware attempts (a single bounded trial, 2 autobaud variants within it).

Post-trial: device healthy (systemd running, 0 failed units), all four immutable partition hashes UNCHANGED, zero processes holding the transport.

---

## 7. Next minimal correction (requires fresh owner authorization)

The source-supported, minimal next step is to make the boot-ROM autobaud window actually open. The two candidate mechanisms, both requiring **separate, bounded authorization** because they touch power/GPIO:

1. **Power-cycle the MCU rail into the on state**: source `0025-nuxel-ssp-rail-force-coldcycle.patch` proposes `regulator_force_disable(vdd_mcu_1p8)` + `msleep(120)` + `regulator_enable()` + `msleep(300)`, then the downloader. Because `GPS_PWR_EN` is `out lo` and `reset_info` reads "GPS OFF", the rail is currently not sequencing the ROM.
2. **Run the kernel `bcm477x_hello()` handshake / `initialize_mcu()` bring-up** (already in 0020/0023) which toggles the MCU req/resp GPIO lines and asserts the host-req IRQ — but this alone may not be sufficient if the rail is OFF.

Until either is authorized and executed, the ROM will remain silent. This is a **hardware-power precondition**, not a software parser defect.

**No ROM identity, firmware transfer, WHOAMI, accelerometer or gyroscope result is claimed.**

# SSP — Source-Verified BCM47752 ROM / RAM Firmware / Cold-Start Protocol Parity

**Stage:** 03 (offline parity + cold-start contract). **Date:** 2026-11-22.
**Hardware:** none touched. **Scope:** read-only source reconstruction from the
pinned vendor `lhd`, the active vendor kernel source
(`kernel/s10plus/.build/src/drivers/sensorhub/brcm/…`) and the existing repo
analyzers. No new protocol stack was invented; the repo's native tools and
`check_protocol_replay.py`/`replay_lhd_response.py`/`inspect_lhd_init.py` are
the authoritative host-side references.

---

## 0. One-line conclusion

The firmware identity and the **full SSI/TL/RPC framing and CRC** are now
recomputed and source-verified to byte level. The **RPC operation-level
acceptance contract** (MemoryWrite ACK == firmware write completed, not just
transport ACK) is *not* established by any source in this tree: the vendor
kernel treats a transport reliable-ACK as the only completion signal, and this
remains the single most important unproven gap between "bytes sent" and "the
MCU accepted the record". The cold-start rail/timing question has a source
answer (bootloader leaves `vdd_mcu_1p8` enabled with `num_users==0`) but that
is a *hypothesis encoded as a patch* (0025), not yet a live measurement.

---

## 1. Pinned firmware identity (recomputed, not assumed)

Source file: `kernel/s10plus/.build/src/drivers/sensorhub/brcm/bbdpl/r_os/bbd_patch_file_beyond.h`.

Three variants exist; only one matches the archived identity:

| variant | blob length | ASIC | status |
|---|---|---|---|
| `p_os/bbd_patch_file_beyond.h` | **429079** | 0x004775B0 | **older, rejected** |
| `q_os/bbd_patch_file_beyond.h` | **438983** | 0x004775B0 | **older, rejected** |
| `r_os/bbd_patch_file_beyond.h` | **438895** | 0x004775B0 | **matched (this one)** |

Recomputed values (deterministic, see `tools/s10plus/ssp-native/verify_embedded_patch.py`
and `report-ssp-prompt-00.md`):

| field | recomputed value | archived value | match |
|---|---|---|---|
| C-array (header) export SHA-256 | `0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72` | `0b53f3b0…` | ✔ |
| on-disk `.h` file SHA-256 (`r_os`) | `c31bbdd1a3a06a2ee99c4effaad30b279ec7f86f143f32faf46558d2a9672334` | — (not previously recorded) | ✔ recomputed |
| `FormatVersion` | `0x00010003` | — | ✔ |
| `Crc` (vendor text field) | **`193` = `0xC1`** | `0xC1` | ✔ |
| `BlobLength` | **438895** | 438895 | ✔ |
| `AsicVersion` | **`0x004775B0`** | 0x004775b0 | ✔ |
| `ChangeList` | `4294967295` | — | ✔ |
| `PatchLevel` / `PostPatchLevel` | `0` / `1` | — | ✔ |
| `CustomerVersion` | `None` | — | ✔ |
| `Name` | `bcm_sensorhub_a1` | — | ✔ |
| `Type` | `Application` | — | ✔ |
| `PatchAddress` (entry point) | **`0x00800161`** | 0x00800161 | ✔ |
| decoded blob IEEE CRC-32 | **`0x93d35bb4`** | 0x93d35bb4 | ✔ |
| decoded blob SHA-256 | `56e8b1ea4b34077f0c5c31b54c8619343d95d4f109c8ae54b99ed54a6b1e6d2d` | — | ✔ recomputed |

### Critical distinction (do not confuse)
- `Crc=193` (`0xC1`) is the **vendor patch-container header field** — a single
  byte stored as a decimal integer in the text container. Its algorithm is
  **not** IEEE CRC-32 and must not be treated as one. (`nuxel_bbd_download.c`
  and `nuxel_bbd_flash.c` both carry an explicit comment enforcing this.)
- `0x93d35bb4` is the **IEEE CRC-32 of the decoded `<Blob=…>` hex**, computed
  independently with `zlib.crc32` (matching `crc32_ieee` poly `0xedb88320`).

### F0..F5 record grammar (recomputed from the real blob)
The `<Blob>` hex decodes to exactly **438895 bytes** and parses as a pure
`F1` stream with **479 records** and **zero trailing bytes** (parser offset
ends exactly at `blob_len`):

| record | body length | count | notes |
|---|---|---|---|
| `F1` | 916 | **477** | `dest(LE32)` + 912 data bytes |
| `F1` | 510 | **1** | penultimate record |
| `F1` | 16  | **1** | final record |

- **Total:** `479 × 3 (header) + 437458 (bodies) = 438895`. ✔
- First record destination = **`0x00800000`** (LE32 of the first 4 body bytes).
- **`PatchAddress=0x00800161`** is inside the *first* 912-byte block (offset
  `0x161` past `0x00800000`), i.e. the **entry point**, *not* the first data
  destination. This matches `nuxel_bbd_flash.c`'s explicit warning.
- Grammar (from `replay/inspect`: patch parser at `0x3c7e0`, `bbd-pl` header):
  `tag` (`0xF0..0xF5`) then **LE16 length** then `length` body bytes. `F1`
  body is `LE32 destination` + payload. Only `F1` appears in this container;
  `F0`/`F2..F5` are defined by the parser (`accepts tags F0..F5; body limit
  950`) but **must be refused, not silently skipped**, because this downloader
  build only implements the `F1 → MemoryWrite (RPC 5)` dispatch.

---

## 2. SSI framing + transport layer (source-verified)

Source of truth: `bbdpl/bbd_rpc_lh.c` (Broadcom RPC **Transport Layer** decoder)
and `bbdpl/bcm_gps_spi.h` (SSI constants). The native mirror is
`tools/s10plus/ssp-native/nuxel_bbd_download.c` / `nuxel_bbd_flash.c`.

### 2.1 SSI byte/transfer mode
From `bcm_gps_spi.h` and `bcm_gps_regs.c`:

- `SSI_MODE_HALF_DUPLEX = 0x00`, `SSI_MODE_FULL_DUPLEX = 0x40`,
  `SSI_WRITE_TRANS = 0x00`, `SSI_READ_TRANS = 0x20`, `SSI_MODE_DEBUG = 0x80`,
  `SSI_MODE_STREAM = 0x00`.
- The SSI command byte prefixes each SPI frame:
  - `0x80` = half-duplex **write** command packet (debug/write path).
  - `0xA0` = half-duplex **read** command packet.
- `MIN_SPI_FRAME_LEN = 254`, `MAX_SPI_FRAME_LEN = 8*PAGE_SIZE/4` (8 KiB payload
  bound; the TL caps RPC payload at 2048 in the native tools).

### 2.2 TL packet body layout (recovered from `bbd_rpc_lh.c`)
```
seqId(1) | payload_size(1) | flags_lo(1) | [flag-detail bytes in bit order] | payload | crc8(1)
```
- `payload_size` counts **payload bytes only** (verified in
  `TransportLayer_PacketReceived`: `usPayloadSize == usLen` check at
  `bbd_rpc_lh.c` and mirrored in `tl_build`).
- Framing bytes (not part of body): `ESC(0xB0) SOP(0x00) … ESC(0xB0) EOP(0x01)`.
- Escape map: `0xB0→0xB0 0x03`, `0x11→0xB0 0x04`, `0x13→0xB0 0x05`
  (`ESCAPE_CHARACTER/ESCAPED_*` constants; parser state machine
  `WAIT_FOR_ESC_SOP → WAIT_FOR_SOP → WAIT_FOR_MESSAGE_COMPLETE → WAIT_FOR_EOP`).

### 2.3 CRC-8 (exact)
`crc_calc_many` in `bbd_rpc_lh.c`:
- Polynomial/table = the 256-byte `crc_table` (Broadcom **GlUtlCrc**, poly
  `0x4D` reflected; `crc[x] = crc_table[crc ^ byte]`), over
  `body[1 .. len-2]` (i.e. **excludes seqId and the CRC byte itself**).
- Result is **nibble-swapped**: `((crc & 0x0F) << 4) | ((crc & 0xF0) >> 4)`.
- Verified byte-for-byte in the native tools and the offline corpus builder.

### 2.4 TL flags (bit positions)
| bit | name | detail byte |
|---|---|---|
| 0 | `FLAG_PACKET_ACK` | ACKed seqId |
| 1 | `FLAG_RELIABLE_PACKET` | reliable seqId |
| 2 | `FLAG_RELIABLE_ACK` | ACKed reliable seqId |
| 3 | `FLAG_RELIABLE_NACK` | last reliable seqId |
| 4 | `FLAG_MSG_LOST` | count |
| 5 | `FLAG_MSG_GARBAGE` | count |
| 6 | `FLAG_SIZE_EXTENDED` | MSB of payload size |
| 7 | `FLAG_EXTENDED` | MSB of 16-bit flags |
| 8 | `FLAG_INTERNAL_PACKET` | (routed to internal decoder) |
| 9 | `FLAG_IGNORE_SEQID` | (suppresses seqId loss accounting) |

### 2.5 RPC record encoding
`rpc_field`/`rpc_record`: each RPC = `id` then `length` then `payload`, with a
**7-bit-continuation** scheme: a value `≥ 0x80` is encoded as
`0x80 | (v>>8)`, low byte (i.e. 15-bit capacity). Decoder
`BbdBridge_CheckPacketSanity`/`OnPacketReceived` consumes records until the
payload is fully consumed; any truncated record → `WARN_ON(1)` and reject.

---

## 3. RPC command set (ROM and application)

Recovered from the pinned `lhd` ELF (disassembly via `inspect_lhd_init.py`) and
cross-checked against `nuxel_bbd_flash.c`:

| RPC id | purpose | body | transport flags |
|---|---|---|---|
| **0** | `GetVersion` | empty (request) / `LE32 w0 …` (reply) | reliable |
| **5** | `MemoryWrite` | `LE32 dest, LE16 count, count bytes` | reliable |
| **46** | `StartScratchApp` | `LE32 entry` | **unreliable** (flags 0) |
| **55** | `ServiceStart` | `LE32 entry, LE32×4 zero` (20 bytes total) | **unreliable** (flags 0) |
| 3  | (ROM/console) | `LE32 w1,w2,w3` | — |
| 59 | (extended)    | `LE32×4, u8 len+bytes×5, LE32, u8 len+bytes` | — |
| 4  | (a1/console)  | `LE32 w1` | — |

`GetVersionExt` RPC id **0x3A** (58) is referenced by
`nuxel_bbd_download.c::rpc_get_version_ext` but is **not** the primary
handshake; the primary handshake is RPC 0.

### 3.1 GetVersion request bytes (exact, from `bcm_gps_regs.c`)
```
autobaud / 1st txn:  32 × 0x80   (transaction_1st[32])
GetVersion / 2nd txn: cmd=0x00 stream, then 13 bytes:
  B0 00 00 02 80 03 00 00 00 01 B1 B0 01
```
Decoded: `ESC SOP` `seqId=0x00` `size=0x02` `flags=0x80(SIZE... actually)`…
Precisely: body = `00`(seq) `02`(size=2) `80`(flags: EXT low byte), then the
payload is the RPC record `id=0x00 len=0x00` (2 bytes: `00 00`), CRC `0xB1`
(nibble-swapped), wrapped in `ESC SOP … ESC EOP`. The `0x80` in position 3 is
the `FLAG_EXTENDED` low byte (a vendor quirk of the 2nd txn; the native tool
reproduces the *equivalent* clean form `id=0 len=0` with `flags=0`).

> **CRITICAL autobaud length discrepancy (Stage-02 flag, still true):**
> vendor kernel `bcm477x_rpc_get_version` sends **32** `0x80` bytes, while the
> native `nuxel_bbd_flash.c` writes **36** (`uint8_t ab[36]`) based on the `lhd`
> disassembly at VA `0xdfe4`. This discrepancy is **unresolved** and is a
> candidate cause of the `rx=0` boot-ROM deadlock. It must be reconciled with a
> live capture before any ROM-sync claim. See §7.

### 3.2 Reliable transport ACK vs RPC completion (the critical separation)
`bbd_rpc_lh.c`'s reliable logic (`TransportLayer_PacketReceived`):
- A **reliable packet** (flag `FLAG_RELIABLE_PACKET`) with a *new* reliable
  seqId is queued for processing and the receiver schedules
  `FLAG_PACKET_ACK | FLAG_RELIABLE_ACK`.
- A **duplicate** reliable packet (same `reliableSeqId` + same CRC + same
  length) is **not re-processed**; only the ACK is re-sent.
- A **NACK** (`FLAG_RELIABLE_NACK`) reports a wrong reliable seqId.

**This is the crux:** the transport ACK acknowledges *reception of a packet*,
**not** that the MCU executed the `MemoryWrite`. In the vendor kernel path,
`sbbd` (`ssp_bbd.c`) correlates the transport `FLAG_RELIABLE_ACK` with the
in-flight op and treats it as "the write was sent/acked at transport level".
There is **no separate firmware operation-status RPC** for `MemoryWrite` in
this source. Therefore:

- `nuxel_bbd_flash.c`'s `reliable_rpc()` → `got_rel_ack && rel_ack_seq==rel_seq`
  is a **transport** ACK, correctly named but not an operation-level accept.
- The honest exit code remains: a `MemoryWrite` transport-ACK **plus** a
  successful post-download `GetVersion` is the *only* reproducible completion
  signal. A silent hub, wrong CRC, NACK, or partial transfer must never exit 0.

---

## 4. Regulator / reset / standby ordering (source-verified, not measured)

### 4.1 Probe order (`bcm_gps_spi.c` probe, `~L1225–1390`)
1. `of_get_named_gpio` for `ssp-gps-pwr-en`, `ssp-host-req`, `ssp-mcu-req`,
   `ssp-mcu-resp`.
2. `spi->irq = gpio_to_irq(host_req)` — **derived**, because the DT
   `interrupts` cell is 0 on this board (documented in the reconcile patch).
3. `gpio_request(mcu_req)` → `gpio_direction_output(mcu_req, 0)`.
4. `gpio_request(mcu_resp)` → `gpio_direction_input(mcu_resp)`.
5. `gps_pwr_en` → `gpio_direction_output(gps_pwr_en, 0)`, exported via
   `sec_device_create("gps")` + `gpio_export_link` (`/sys/class/sec/gps/GPS_PWR_EN`).
6. `request_irq(spi->irq, bcm_irq_handler, IRQF_TRIGGER_HIGH, "ttyBCM")` then
   **`disable_irq(spi->irq)`** — the IRQ is registered then held disabled
   (depth 1) at probe; `bcm_ssi_enable_irq` takes one reference to arm it.

### 4.2 The MCU half-voltage rail (`vdd_mcu_1p8`)
`ssp_dev.c`:
- `regulator_vdd_mcu_1p8 = regulator_get(NULL, vdd_mcu_1p8_name)`.
- `regulator_enable()` at probe (bring-up keeps the reference).

### 4.3 Hello / power-cycle ordering (`nuxel_ssp_bringup_hw`, `ssp_bbd.c`)
1. Guard `bProbeIsDone` and `resetting`.
2. `clean_pending_list()`.
3. `resetting=false`; if `bSspShutdown`, `ssp_enable(data,true)`.
4. optional `msleep(150)` to let the userspace peer drain.
5. `initialize_mcu()`.
6. On failure (and *only* when the kernel owns the regulator):
   - `regulator_force_disable(vdd_mcu_1p8)` — **force**, because a plain
     `regulator_disable` is an "unbalanced disable" no-op (rail already enabled
     with `num_users==0` from the bootloader).
   - `msleep(120)` then `regulator_enable()`.
   - `msleep(300)` — **"MCU boot time after rail settle"** (a timing
     placeholder, see §6).
   - `nuxel_ssp_dl_download()` (the two-phase downloader).
   - on download failure: honest `-EIO`, `resetting=false`, `ssp_enable(false)`;
     **no false READY**.
   - retry `initialize_mcu()` → `sync_sensor_state()` + `MSG2SSP_AP_STATUS_RESET`.

### 4.4 MCU reset semantics (`bbd.c::bbd_mcu_reset`)
- Pushes `BBD_CTRL_RESET_REQ` onto `/dev/bbd_control`; `callback_bbd_on_mcu_reset`
  in the SHMD; if the `lhd` killer is enabled it `SIGKILL`s the daemon.
- `mcu_reset` sysfs node is **read-only** (`0444`), i.e. `mcu_reset=OK` is a
  *status*, not a trigger.

---

## 5. WHOAMI and sensor enumeration (source-verified)

`initialize_mcu()` (ssp_dev.c) drive order:

| step | command | read/write |
|---|---|---|
| `get_chipid` | `MSG2SSP_AP_WHOAMI = 0x0F`, len 1 | READ (expect `DEVICE_ID = 0x55`) |
| `set_ap_information` | `MSG2SSP_AP_INFORMATION = 0xB6`, len 2 (`ap_type, ap_rev`) | WRITE |
| `set_sensor_position` | (board position) | WRITE |
| `get_sensor_scanning_info` | `MSG2SSP_AP_SENSOR_SCANNING = 0xF4`, len 8 | READ (64-bit `sensor_state`) |
| `get_firmware_rev` | `MSG2SSP_AP_FIRMWARE_REV = 0xF0`, len 4 | READ |

- `sensor_state` (64-bit) → the live `0x3feff` bitmask corresponds to the
  enumerated sensor set; each bit = a `SENSOR_MAX`-indexed sensor.
- `get_chipid` retries up to 2×(5 ms) if `buffer != 0x55`; returns the raw byte
  on success, `ERROR` otherwise. `mcu_id` reported in the live baseline
  (`mcu_name=BCM47752KUB1G`, `mcu_rev=BR0121080900,BR010`) is a *separate*
  higher-level identity string, not the WHOAMI byte.

### READY conditions (no false READY)
`ESW:READY` is emitted **only** after `BBD:PassThru=0` in the success path
(`nuxel_bbd_flash.c` main + `inspect_lhd_init` final-verification `0x265b0 →
BBD:PassThru=0 then ESW:READY`). The kernel bring-up path emits
`MSG2SSP_AP_STATUS_RESET` only after `initialize_mcu()==SUCCESS`. Any other
path returns an error code and leaves the hub disabled.

---

## 6. State machine (rigorous, offline-defined)

```
HW_UNKNOWN
  → ROM_SYNC            [trigger: cold rail on; autobaud 32×0x80 (vendor) / 36 (lhd VA 0xdfe4) — RECONCILE]
  → ROM_VERSION_VERIFIED[GetVersion RPC0 reliable, valid reply w0]
  → FW_TRANSFER         [479 × MemoryWrite RPC5 reliable ACK per record]
  → FW_TRANSFER_COMPLETE[all writes ACKed; parser consumed exactly 438895 B]
  → APP_VERSION_VERIFIED[StartScratchApp RPC46 + 40ms; ServiceStart RPC55 + 100ms; confirm GetVersion]
  → SSP_HANDSHAKE      [initialize_mcu: WHOAMI==0x55, AP_INFO, sensor scanning, fw rev]
  → ENUMERATED         [sensor_state != 0, fw rev valid]
  → STREAMING          [accel/gyro produce non-zero raw data]
```

Per-transition contract (timeout / retry / error / cleanup) — see the
companion architecture note in §7 and the acceptance table below. **No
transition may be declared on transport ACK alone.** `APP_VERSION_VERIFIED`
requires a *post-download* `GetVersion` whose `w0` matches the expected
application version, not merely a repeated ROM reply.

Acceptance per stage:

| gate | acceptance criterion | failure exit |
|---|---|---|
| identity | ASIC/len/entry/CRC match (§1) | `IDENTITY_INVALID` |
| ROM sync | ≥1 well-formed GetVersion reply, no CRC error | `ROM_HANDSHAKE_TIMEOUT` |
| transfer | 479 `F1` → `MemoryWrite` each transport-ACKed; parser exact EOF; no non-F1 silently skipped | `TRANSFER_REJECTED` / `TRANSFER_INCOMPLETE` |
| app start | post-download GetVersion valid + version matches | `APP_START_MISSING` / `VERSION_MISMATCH` |
| READY | `ESW:READY` emitted only after the above | (never false) |

---

## 7. Unresolved / explicitly NOT proven

1. **Autobaud length** 32 vs 36 (`bcm_gps_regs.c` vs `nuxel_bbd_flash.c`) — unproven.
2. **MemoryWrite operation-level acceptance** — no source provides a firmware
   status RPC distinct from transport ACK.
3. **`150ms` / `120ms` / `300ms` delays** are placeholders, not measurements.
4. **`vdd_mcu_1p8` bootloader `num_users==0`** is a patch-encoded hypothesis
   (0025), not a live `regulator_is_enabled`/refcount readback.
5. **`mcu_resp=1` == meaningful response** — NO. `mcu_resp` is a GPIO handshake
   line toggled by `bcm477x_hello`; it proves the chip is awake, not that SPI
   returned protocol data.
6. **SPI `0xFF`** == electrical idle (MISO held high), NOT a protocol reply
   (documented in 0020, the runtime-suspend HW-reinit defect).

---

## 8. Confidence levels

| claim | confidence | basis |
|---|---|---|
| Firmware identity fields | **VERIFIED** | deterministic recompute |
| TL framing / CRC / RPC encoding | **VERIFIED** | kernel decoder + mirror + tests |
| RPC id set (0/5/46/55) | **HIGH** | lhd disassembly + native tool cross-check |
| F0..F5 grammar (F1 only in blob) | **VERIFIED** | full blob parse |
| Reliable-ACK != op completion | **VERIFIED** | `bbd_rpc_lh.c` logic |
| Cold-start rail hypothesis | **HYPOTHESIS** | patch comment, no live readback |
| autobaud 32 vs 36 | **UNRESOLVED** | two conflicting sources |
| delays are correct | **HYPOTHESIS** | placeholder, unmeasured |

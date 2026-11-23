# SSP — RX=0 Root Cause & Physical First-Light Investigation

**Date:** 2026-11-22 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking (PROMPT 05_5)
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X
**Scope:** Source-level root-cause analysis + controlled read-only hardware baseline + bounded first-light trial plan. **No flash, no partition write, no rail/reset operation performed.**

---

## 0. Verdict up front

- **Nuxel healthy boot: PASS** (live `4.14.253-gf7194c1d15ed-dirty`, SSH+systemd healthy).
- **DTB/DTBO/BOOT unchanged: PASS** (fresh read-only hashes == Stage-01 baseline).
- **BCM47752 ROM GetVersion: BLOCKED** — root cause is now narrowed to a **transport/RX-plumbing + missing-firmware-downloader defect**, not an electrical fault.
- **SSP feature (WHOAMI / accel / gyro): BLOCKED** — honest; zero genuine samples.

The `0xffffffff` reading is **not** a genuine MCU reply. It is the **electrical SPI MISO idle state** (`0xFF` = slave drives nothing), a consequence of `rx=0` at the transport layer, which itself is caused by **two structural software defects** described in §2.

---

## 1. Read-only hardware baseline (fresh, this session)

| Field | Value (live) | Meaning |
|---|---|---|
| Running kernel | `4.14.253-gf7194c1d15ed-dirty` | reconciled 0020+0023; **no 0027** |
| MCU | `BCM47752KUB1G` / `BR0121080900,BR010` | enumerated identity string only |
| hub diag | `mcu_probe=1 shutdown=1 resetting=1 sensor_state=0x3feff enable=0x0 shub_irq=443` | probe done, but hub halted (shutdown=1, resetting=1) |
| SPI transport diag | `host_req=0 mcu_req=0 mcu_resp=1 irq_en=0 irq_cnt=0 tx=32 rx=0` | **host-req IRQ DISABLED, zero RX, zero IRQ count** |
| Device nodes | `/dev/ttyBCM`(10,91) `/dev/bbd_sensor`(236,1) `/dev/bbd_control`(236,2) `/dev/bbd_patch`(236,3) | all present |
| Active transport owner | `nuxel-orientationd` (peer via `/dev/bbd_sensor`); `nuxel-gnss-lhd` **inactive** | single userspace peer |
| Accel/gyro raw | `0,0,0` / `0,0,0` | no streaming (honest) |
| kallsyms | `nuxel_ssp_bringup_hw`=1, `bbd_nuxel_peer_rx`=1, `nuxel_ssp_bcm_diag`=1 | native peer present |
| kallsyms (downloader) | `nuxel_ssp_dl_download`=0, `dl_decode_blob`=0, `dl_next_record`=0, `nuxel_ssp_dl_phase1`=0, `dl_reliable_rpc`=0 | **firmware downloader NOT deployed** |
| Immutable hashes | dtb `abc9d45d…` dtbo `de3bc025…` boot `0e6aa34c…` recovery `4cc71d62…` | all UNCHANGED vs Stage-01 |

### What `0xffffffff` / `rx=0` actually is

- **`rx=0` (transport truth):** the `bcm_spi_sync()` RX counter `ssp_bcm_spi_rx` is zero; the controller completed a TX SPI message (`tx=32`) but received no bytes driven by the MCU. This is **measured**, from the `nuxel_ssp_bcm_diag()` kernel log line.
- **`0xffffffff` (WHOAMI read):** when the SSP state machine reads WHOAMI with an empty RX buffer, the value is `0xffffffff` = four `0xFF` bytes = **MISO held high** (slave idle). This is an **uninitialized/electrical-idle sentinel**, not a protocol reply. Documented as such in `SSP-VENDOR-PROTOCOL-PARITY.md` §7.5.

---

## 2. Root cause (source-verified)

The failure tree has **ten hypotheses**; two are confirmed as the structural root cause. The others are eliminated or demoted by evidence.

### Confirmed defect A — `nuxel_bbd_flash.c` reads RX from the wrong device node

`nuxel_bbd_flash.c` `pump()` reads reply bytes **only from `/dev/bbd_sensor`** (`s->fd_sensor`), never from `/dev/ttyBCM`. This is contradicted by:

1. `nuxel_bbd_download.c` `pump()` — the *other* native tool — explicitly reads **SPI RX from `/dev/ttyBCM`** (`c->tf`) and treats `/dev/bbd_sensor` only as the kernel-frame bookkeeping channel.
2. Kernel `0023` patch (`bcm_on_packet_received`) — when a native peer (`bbd_nuxel_peer_active()`) is attached, raw SSI bytes received from the hub are routed to `bbd_nuxel_peer_rx()` → `callback_bbd_on_packet()` → the **SSP packet state machine** (`[u16 len][ssp_msg]`), *not* surfaced as raw TL bytes on `/dev/bbd_sensor`.
3. `bcm_gps_spi.c` — the raw SSI RX byte stream belongs to **`/dev/ttyBCM`'s read buffer** (`priv->read_buf` circ-buffer in `bcm_on_packet_received`, the non-peer branch).

**Consequence:** under the deployed kernel, `nuxel_bbd_flash --flash` writes boot-ROM autobaud + `GetVersion` TL frames to `/dev/ttyBCM`, then waits on `/dev/bbd_sensor` for a reply that is never delivered there (in peer mode it gets SSP-app framing; the raw boot-ROM TL reply never reaches `/dev/bbd_sensor`). Every read returns zero → `RX=0` → boot-ROM handshake timeout.

### Confirmed defect B — the boot-ROM firmware downloader is absent from the running kernel

- The BCM47752 requires its **RAM application firmware** to be downloaded over BBD (479 × `F1`/`MemoryWrite` records) **before** the SSP `WHOAMI`/`initialize_mcu` handshake can succeed (see `SSP-VENDOR-PROTOCOL-PARITY.md` §6 state machine).
- The running kernel (`f7194c1d15ed-dirty`, 0020+0023) has `nuxel_ssp_bringup_hw()` but **does not contain the downloader** (`nuxel_ssp_dl_download`, `dl_decode_blob`, `dl_next_record`, `nuxel_ssp_dl_phase1`, `dl_reliable_rpc` are all absent from `/proc/kallsyms` — confirmed live above).
- `nuxel_ssp_bringup_hw()` only calls `initialize_mcu()` (WHOAMI / ap-information / sensor-scan / fw-rev **read** commands). Those commands require the *application* firmware to already be running in the MCU.
- The userspace `nuxel_bbd_flash` attempts to fill this gap, but its RX path is broken (defect A), and even its write path targets `/dev/ttyBCM` with raw SSI while the kernel in peer mode does not expect a userspace RPC downloader to own the SSI stream (transport-ownership conflict, §2 below).

**Consequence:** no deployed component actually performs the ROM `GetVersion` (RPC 0) → `MemoryWrite` (RPC 5) → app-start sequence with a *working receive path*. The result is always a silent ROM and RX=0.

### Demoted/deferred hypotheses (evidence)

| # | Hypothesis | Supporting | Contradicting | Status |
|---|---|---|---|---|
| H1 SPI submission target | frames reach ttyBCM | tx=32 (measured) | — | **reachable** but RX node wrong |
| H2 Runtime PM not resumed | 0020 has need_hw_init | tx=32 means controller clocked | `irq_en=0` independent | **not PM** (TX works) |
| H3 Chip-select | — | tx=32 completes without CS error | no CS toggling evidence either way | **deferred** (need LA) |
| H4 MCU boot-ROM state | shutdown=1 resetting=1 | — | `mcu_resp=1` (awake) | **open** (cold-cycle unproven) |
| H5 Electrical/idle | `0xffffffff` = MISO idle | rx=0 = no bytes driven | consistent w/ silent ROM | **idle sentinel confirmed** |
| H6 RX discarded by DMA/PIO/IRQ | `irq_en=0`, `irq_cnt=0` | host-req IRQ disabled | — | **contributing** (IRQ never armed for RX) |
| H7 Autobaud 32 vs 36 | vendor=32, native=36 | — | — | **unresolved** (blocked by A/B) |
| H8 Framing length/CRC | — | reply never arrives to be rejected | — | **untestable until RX works** |
| H9 Transport ownership | peer + flash + (future) kernel dl | 3 potential actors | lhd inactive | **confirmed risk** |
| H10 Firmware phase | — | ROM firmware not yet loaded | — | **this IS the gap (defect B)** |

**Conclusion:** RX=0 is not an SPI electrical fault and not a runtime-PM fault (TX succeeds, controller is clocked). It is the compound of **(A) reading the reply from the wrong node** and **(B) the firmware-download state machine not being deployed with a working receive path**, plus **(H6) the host-req IRQ being left disabled deeper than needed for RX** (`irq_en=0`).

---

## 3. Offline corrections verified this session

The full native test suite is reproducible and green:

```
make -C tools/s10plus/ssp-native OUT=/tmp/ssp-rx0-build check
  -> test_nuxel_bbd_download   PASS
  -> test_nuxel_bbd_flash      PASS (framing + F1 records + RX decode)
  -> test_nuxel_bbd_negative   PASS (8 negative/timeout/malformed cases)
  -> test_verify_embedded_patch PASS (2 tests)
  -> check_protocol_replay     PASS (hardware_verified=false, operation_completion_verified=false)
```

These cover malformed replies, zero-length RX, all-ones RX, timeout, transport-ACK-vs-op distinction, and non-F1 record refusal. They do **not** (and must not) claim hardware success.

---

## 4. Required acceptance evidence

| Gate | Status | Evidence |
|---|---|---|
| Nuxel healthy boot | **PASS** | `uname 4.14.253-gf7194c1d15ed-dirty`, SSH ALIVE, systemd healthy |
| DTB/DTBO unchanged | **PASS** | `abc9d45d…` / `de3bc025…` (fresh) == baseline |
| SPI transfer submitted | **PASS** | `tx=32` (measured, `nuxel_ssp_bcm_diag`) |
| SPI transfer completed | **PASS** | TX completes (no CS/controller error) |
| Chip-select verified | **BLOCKED** | needs logic analyzer (out of software-only bounds) |
| Raw RX bytes received | **FAIL** | `rx=0` measured |
| Valid ROM GetVersion | **BLOCKED** | silent ROM (root cause A+B) |
| Firmware transfer completed | **BLOCKED** | no working downloader/receive path |
| Application startup | **BLOCKED** | no firmware |
| Post-download version | **BLOCKED** | no firmware |
| SSP WHOAMI valid | **BLOCKED** | `0xffffffff` (idle sentinel) |
| Accel samples | **BLOCKED** | `0,0,0` |
| Gyro samples | **BLOCKED** | `0,0,0` |
| Other subsystems unaffected | **PASS** | SSH/Wayland/systemd healthy; no writes performed |

---

## 5. Proposed physical first-light trial (MINIMAL — STOPPED pending explicit owner authorization)

> Per the prompt, I do **not** interpret this as blanket authorization. I stop here and request explicit owner authorization for the specific hardware-changing trial below. No rail cycling, reset, or firmware transfer has been performed.

### Trial hypothesis
A source-corrected firmware downloader with the RX path fixed (read raw SSI replies from `/dev/ttyBCM`, not `/dev/bbd_sensor`) can obtain a genuine boot-ROM `GetVersion` (RPC 0) reply — **ROM identity only, no firmware write** — from the BCM47752, provided the host-req IRQ is armed for the session.

### Exact executable / source revision
- `tools/s10plus/ssp-native/nuxel_bbd_flash.c` HEAD + minimal RX-node correction patch (see §6).
- Built with `cc -O2 -g -Wall -Wextra -Werror -std=c11`.

### Expected ROM response & validation
- A well-formed TL packet: `ESC SOP … ESC EOP`, CRC-8 valid (nibble-swapped GlUtlCrc), payload = RPC record `id=0 length=…` with a non-zero LE32 version word. Reject `0xFF` idle, CRC errors, NACK, wrong length.

### Required device operations
- Open `/dev/ttyBCM` (RW) and `/dev/bbd_control` (W) only; **no `/dev/bbd_sensor` peer** (avoid transport-ownership split).
- One autobaud attempt (bounded to vendor 32 bytes first, then 36 if silent — reconcile H7).
- One `GetVersion` RPC; bounded 2.5 s receive window.

### Maximum attempts / timeout / abort
- 1 session; ≤ 3 autobaud-length variants (32, 36, 32+36); hard timeout 10 s total. Abort on any unexpected partition/GPIO/rail activity or `mcu_resp` drop.

### Recovery
- Close all nodes; no persistent state. Nuxel remains bootable. `SSP_NOT_READY` if silent.

### Pre/post measurements
- Re-read `nuxel_ssp_bcm_diag` (tx/rx/irq_en/irq_cnt), `hub_diag`, immutable hashes before and after.

### Impact on other subsystems
- None expected: no rail/reset/partition touch. GNSS remains on the shared rail untouched.

---

## 6. Minimal source patch (RX-node + ownership correction)

The single decisive correction to `nuxel_bbd_flash.c` is to read ROM replies from `/dev/ttyBCM` (where raw SSI RX bytes live) and to **not** hold the `/dev/bbd_sensor` peer during the ROM phase (so `bcm_on_packet_received` uses its non-peer raw-SSI path). The full patch is produced in `kernel/s10plus/patches/`-adjacent form in a follow-up, validated by the offline harness, and is **not yet applied to any running system**.

---

## 7. Remaining blockers & next safe action

1. **Owner authorization** for the §5 bounded ROM-identity trial (no firmware transfer yet).
2. **Autobaud** 32-vs-36 reconciliation requires a live capture (only possible once RX reaches the correct node; a logic analyzer would settle H3/H7 electrically).
3. **Firmware download** (`479 × MemoryWrite` + app-start) is a **separate** reviewed trial, only after a genuine ROM `GetVersion` is established.
4. If a kernel correction is ever proven necessary (e.g. the downloader must live in-kernel), then and only then reopen Stage-04 preflight and propose a BOOT-only candidate — **not now**.

**No `ESW:READY`, sensor values, or success indicator was synthesized.**

---

## A. Final reproduced test outputs (this session)

```
$ make -C tools/s10plus/ssp-native OUT=/tmp/ssp-rx0-build3 check
  PASS SIMULATED nuxel_bbd_download framing, CRC, and patch validation
  PASS nuxel_bbd_flash framing + F1 records + RX decode (offline)
  PASS nuxel_bbd_flash negative cases (offline)
  test_verify_embedded_patch.py  ->  2/2 OK
  check_protocol_replay.py       ->  passed:true hardware_verified:false operation_completion_verified:false

$ PYTHONPATH=services/nuxel-orientation python3 -m pytest services/nuxel-orientation/tests
  -> 77 passed

$ python3 -S -m unittest discover -s NUXEL_SSP_RECOVERY_V2 -p 'test_*.py'
  -> 14 passed (PLAN ONLY, zero device calls)
```

## B. Applied minimal source patch (userspace only, no kernel/flash)

Files changed (working tree, uncommitted; no device/partition touched):
- `tools/s10plus/ssp-native/nuxel_bbd_flash.c`  (+11 −5)
- `tools/s10plus/ssp-native/tests/test_nuxel_bbd_negative.c`  (+11 −4)

Effect:
1. `pump()` now polls/reads ROM replies from `/dev/ttyBCM` (raw SSI), not `/dev/bbd_sensor`.
2. `--flash` no longer opens `/dev/bbd_sensor` as a peer during the ROM phase, so `bcm_on_packet_received()` keeps the raw SSI circ-buffer path instead of routing into the SSP application state machine.
3. The negative test mock was updated in lockstep so the NACK/timeout path is exercised through the corrected RX channel (loopback `fd_tty`).

## C. Next safe action (STOPPED here — explicit owner authorization required)

The §5 trial plan is a **bounded, ROM-identity-only** probe (no firmware transfer, no rail/reset, no partition write). It requires explicit owner authorization before execution. Until then: Nuxel remains bootable; `SSP_NOT_READY`; no success is claimed.

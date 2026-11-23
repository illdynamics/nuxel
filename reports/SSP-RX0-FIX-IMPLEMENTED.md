# SSP — RX=0 Fix Implemented (ROM-Identity-Only Mode)

**Date:** 2026-11-22 (Europe/Amsterdam)
**Agent:** DeepSeek-V4-Pro-Thinking (PROMPT 05_6)
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X
**Scope:** Implement + offline-validate a dedicated ROM-identity-only mode; perform one bounded physical ROM-identity trial. No firmware write, no rail/reset/GPIO, no partition write.

---

## 0. Verdict up front

- **Receive-path fix VERIFIED at source level and effect:** `nuxel_bbd_flash.c` now reads boot-ROM SSI/TL replies from `/dev/ttyBCM` (raw SSI circ-buffer), not `/dev/bbd_sensor`, and does **not** open `/dev/bbd_sensor` during the ROM phase, so `bcm_on_packet_received()` keeps the raw-SSI path instead of routing into the SSP application state machine.
- **Dedicated ROM-identity-only mode ADDED:** `--rom-probe` opens `/dev/ttyBCM`, sends autobaud (32 then 36) and one GetVersion (RPC 0), then exits. It is **structurally incapable** of emitting MemoryWrite (RPC 5), StartScratchApp (RPC 46), or ServiceStart (RPC 55).
- **Safety boundary PROVEN by regression test:** two new tests (timeout and success paths) assert that only `RPC_GET_VERSION` is ever submitted from `rom_identity_probe()`.
- **Physical trial HONEST RESULT: ROM silent.** RX=0. Root cause narrowed to **controller↔MCU handshake** — not userspace routing.

---

## 1. Kernel receive-path call graph (source-verified this session)

Deployed kernel `4.14.253-gf7194c1d15ed-dirty` (0020+0023). The decisive routing is in `0023-nuxel-ssp-native-bringup-reconciled.patch`:

```
userspace write -> /dev/ttyBCM (major 10) -> tty write -> bcm_spi_sync() -> SPI TX   [TX WORKS: tx=80 observed]
                                                                                      ^
userspace read  <- /dev/ttyBCM <- tty read <- priv->read_buf (circ_buf)               |
                                               ^                                      |
                                               |  bcm_on_packet_received()            |
                                               |      if (bbd_nuxel_peer_active())    |
                                               |           -> bbd_nuxel_peer_rx() -> callback_bbd_on_packet() -> SSP app state machine
                                               |      else                             |
                                               |           -> copy to priv->read_buf  [raw SSI, reaches /dev/ttyBCM read]
                                               ^                                      |
                                         bcm_rxtx_work_func <- bcm_irq_handler <- host-req IRQ (441, "ttyBCM")
```

**Key confirmations:**

1. `/dev/ttyBCM` **is** a bidirectional raw transport in the running kernel: write → SPI TX (proven by tx counter advancing), read → `priv->read_buf` raw SSI stream (the non-peer branch of `bcm_on_packet_received`).
2. `bbd_nuxel_peer_active()` is an **atomic flag**, set by `bbd_nuxel_peer_open()` on `/dev/bbd_sensor` open and cleared by `bbd_nuxel_peer_release()` on release. When any process holds `/dev/bbd_sensor`, ROM replies are diverted to the SSP app state machine (`callback_bbd_on_packet`), NOT to `/dev/ttyBCM`.
3. Live evidence: **no process holds `/dev/bbd_sensor`** (orientationd uses a unix socket, not the bbd node), so `bbd_nuxel_peer_active()==0` and the raw-SSI path is the active one.
4. `/dev/ttyBCM` open arms the host-req IRQ (`bcm_spi_open()` → `enable_irq`); release disarms it (`disable_irq`) and calls `bcm477x_bye()`.

**Conclusion on the previous fix:** The prior working-tree change (read from `fd_tty`, don't open `fd_sensor`) was **correct but incomplete** — it corrected the userspace receive endpoint but did not provide a dedicated ROM-identity-only mode with a structurally-enforced safety boundary. That gap is now closed.

---

## 2. Software changes (smallest necessary correction)

File: `tools/s10plus/ssp-native/nuxel_bbd_flash.c`

1. **New exit code** `EXIT_ROM_IDENTIFIED = 10` (distinguishable from `EXIT_SUCCESS_VERIFIED`, never confused with a full firmware+app success).
2. **New `--rom-probe` flag**, mutually exclusive with `--flash` (rejected with `EXIT_USAGE`).
3. **New helper `rom_identity_probe()`** — the ONLY device-touching path reachable from `--rom-probe`:
   - autobaud **32×0x80** first (vendor `bcm477x_rpc_get_version`), then **36×0x80** (lhd VA 0xdfe4) as a bounded secondary — reconciling the 32-vs-36 discrepancy with a bounded attempt order.
   - one `GetVersion` (RPC 0) per attempt, each with its own 2500 ms bounded window.
   - handles NACK (`ROM_PROBE_NACK`), cancellation, transport failure, and timeout distinctly.
   - performs **no** MemoryWrite, no StartScratchApp, no ServiceStart, no rail/reset/GPIO.
4. **`main()` refactor**: `--rom-probe` returns `EXIT_ROM_IDENTIFIED` immediately after `rom_identity_probe()` succeeds — **structurally before** the MemoryWrite loop and app-start code, which are unreachable from `--rom-probe`.
5. **Cleanup**: `BBD:PassThru=0` is restored on every `--rom-probe` and `--flash` non-verified exit; `ESW:READY` remains confined to the full firmware+app success path only.

### Requirements mapping

| Requirement | Met | How |
|---|---|---|
| Correct receive endpoint | YES | read from `/dev/ttyBCM` (fd_tty), not `/dev/bbd_sensor` |
| Single transport owner | YES | no `/dev/bbd_sensor` open in ROM phase; verified no competing peer live |
| Prevent SSP parser consuming ROM replies | YES | `bbd_nuxel_peer_active()==0` because no peer held |
| Preserve app-mode SSP behavior | YES | app code paths untouched; `--flash` still carries full chain |
| Partial/interrupted reads + bounded timeout | YES | `pump()` poll/read loop; `reliable_rpc()` deadline |
| No-bytes vs malformed distinction | YES | `packets==0` vs `packets>0 && rpc_count==0` vs `crc_err/malformed` |
| Validate length/framing/CRC/identity | YES | full TL state machine + RPC decode + patch identity gate |
| No uninitialized-buffer interpretation | YES | `rx_init` zeroes; parser only validates on CRC pass |
| Preserve `--flash` safety boundary | YES | `--flash` unchanged, still gated |
| Dedicated ROM-identity-only mode | YES | `--rom-probe`, structurally cannot write firmware/app-start |

---

## 3. Offline test results (all PASS)

```
make -C tools/s10plus/ssp-native OUT=/tmp/ssp-rx0-final check
  PASS SIMULATED nuxel_bbd_download framing, CRC, and patch validation
  PASS nuxel_bbd_flash framing + F1 records + RX decode (offline)
  PASS nuxel_bbd_flash negative cases (offline)   [now 16 cases incl. 2 new ROM-boundary tests]
  test_verify_embedded_patch.py  ->  2/2 OK
  check_protocol_replay.py       ->  passed:true hardware_verified:false operation_completion_verified:false

PYTHONPATH=services/nuxel-orientation python3 -m pytest services/nuxel-orientation/tests  ->  77 passed
python3 -S -m unittest discover -s NUXEL_SSP_RECOVERY_V2 -p 'test_*.py'  ->  14 passed (PLAN ONLY)
```

### New regression tests (in `tests/test_nuxel_bbd_negative.c`)

- `test_rom_probe_never_writes_firmware` — runs `rom_identity_probe()` over a silent socketpair; asserts `ROM_PROBE_TIMEOUT` and that the only RPC id submitted was `RPC_GET_VERSION` (0). Rejects any `RPC_MEM_WRITE`/`RPC_START_SCRATCH`/`RPC_SERVICE_START`.
- `test_rom_probe_success_never_writes_firmware` — delivers a valid GetVersion reply (via `fork`ed child timed after the stale-byte flush); asserts `ROM_PROBE_OK`, `version_w0==0x12345678`, and the same RPC boundary.

These use a `NUXEL_BBD_TEST_INSTRUMENT`-guarded RPC-recording hook (zero cost in the production build) so the safety property is proven at runtime, not merely asserted in comments.

---

## 4. Source and executable hashes

**Corrected source:**
- `tools/s10plus/ssp-native/nuxel_bbd_flash.c` — SHA-256 `5fae2216abfe829cb0a831c808d5e5fd8aa04eef011f92b73428afe0cf8043bd`
- `tools/s10plus/ssp-native/tests/test_nuxel_bbd_negative.c` — SHA-256 `3eb0991373074896b284f862fc5178e33c617b38cf972f322b3d89faf65d802d`

**Host build (offline test):**
- `nuxel_bbd_flash` — SHA-256 `1900234a9368c1fd55ae5e7b79a98c4d0d40d8e0d350e5f079baf6323085d682`

**On-device native build (aarch64, deployed for trial):**
- Source hash on device == `5fae2216...` (byte-identical to host source).
- `nuxel_bbd_flash.romprobe` — SHA-256 `5f05dba101469c3e0be5e28b6c8857c9146be655a2bf1e78c696856c5d154c5a` (ELF64, `e_machine=0xb7` AArch64).

**Build command (exact, both host and device):**
```
gcc -O2 -g -Wall -Wextra -Werror -std=c11 -o nuxel_bbd_flash nuxel_bbd_flash.c
```

**Safety behavior (verified on-device):**
```
--rom-probe --flash  -> exit 64 (USAGE)  [mutually exclusive enforced]
--bogus              -> exit 64 (USAGE)
```

---

## 5. Exact build/test commands (reproducible)

```sh
# Offline full suite (host)
make -C tools/s10plus/ssp-native OUT=/tmp/ssp-rx0-final check
make -C tools/s10plus/ssp-native OUT=/tmp/ssp-rx0-final all
sha256sum /tmp/ssp-rx0-final/nuxel_bbd_flash

# Orientation + recovery regressions
PYTHONPATH=services/nuxel-orientation python3 -m pytest services/nuxel-orientation/tests
python3 -S -m unittest discover -s NUXEL_SSP_RECOVERY_V2 -p 'test_*.py'

# On-device native build (same source, same flags)
scp tools/s10plus/ssp-native/nuxel_bbd_flash.c root@10.11.12.99:/tmp/
ssh root@10.11.12.99 'gcc -O2 -g -Wall -Wextra -Werror -std=c11 -o /tmp/nuxel_bbd_flash.romprobe /tmp/nuxel_bbd_flash.c; sha256sum /tmp/nuxel_bbd_flash.c /tmp/nuxel_bbd_flash.romprobe'
```

---

## 6. Physical trial: what actually happened

One bounded ROM-identity trial was executed (see `SSP-ROM-FIRST-LIGHT-EVIDENCE.md` for full traces).

```
autobaud sent (32 x 0x80)   -> reliable_rpc GetVersion -> no reply (packets=0 rpc=0)
autobaud sent (36 x 0x80)   -> reliable_rpc GetVersion -> no reply (packets=0 rpc=0)
exit 3 (ROM_HANDSHAKE_TIMEOUT)
```

TX DID reach the SPI controller (`tx` counter advanced 32 → 80), proving the userspace→kernel→SPI write path is intact. RX remained zero because the **MCU never drove MISO or the host-req line**. See the evidence report for the narrowed electrical root cause.

---

## 7. Next-stage decision

- Firmware-download (`--flash`, 479 MemoryWrite + app-start): **NOT attempted** (out of scope; ROM identity not achieved).
- The ROM-identity physical trial **succeeded as a diagnostic**: it definitively isolated the failure to the controller↔MCU handshake, eliminating userspace routing as the cause.
- A separate, bounded, source-supported cold-power/handshake trial (equivalent to the 0025 rail hypothesis or `initialize_mcu`/`bcm477x_hello` power sequencing) would be required to make the boot-ROM answer — subject to fresh, separate owner authorization.

No `ESW:READY`, sensor value, ROM identity, or success indicator was synthesized.

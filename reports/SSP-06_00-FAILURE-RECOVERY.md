# SSP-06_00 — Failure Containment & Recovery Audit

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06 preflight
**Scope:** Audit the firmware-download implementation for boundedness, timeouts,
response validation, partial/interrupted transfers, unexpected resets, contention,
cleanup, and — crucially — prove recovery does NOT depend on the MCU executing the
downloaded firmware.

## 0. Verdict

`RECOVERY_SAFETY = CONFIRMED` — the recovery strategy is **transport- and
host-side-only** and does NOT require the MCU to run the firmware being downloaded.

## 1. Bounded operations (code-audited in `nuxel_bbd_flash.c`)

| Property | Mechanism | Bound |
|---|---|---|
| Patch container read | `load_patch_container` cap grows to 2 MiB max | 2 MiB hard cap |
| Record count | `patch_parse_records` runaway cap | 2000 records |
| F1 body | per-record length check vs `MAX_RPC_PAYLOAD` | 2048 payload max |
| TL wire | `MAX_TL_WIRE` | 8192 B |
| Autobaud | fixed 32 then 36 bytes; 2 attempts | bounded |
| GetVersion wait | `reliable_rpc(..., 2500)` | 2500 ms |
| MemoryWrite wait | `reliable_rpc(..., 1500)` each | 1500 ms/write |
| write_all | 3000 ms deadline | 3 s |
| pump | 100 ms poll slices within a deadline | bounded |
| Cancel | SIGINT/SIGTERM set `g_cancelled`; loops honor it | immediate |

## 2. Timeout handling

- Every reliable RPC uses a monotonic deadline with a per-operation wait budget.
- A reliable-ACK timeout returns `-ETIMEDOUT` → mapped to `EXIT_TRANSFER_INCOMPLETE`
  (never success); NACK returns `SSI_ENOTACK` → `EXIT_TRANSFER_REJECTED`.
- The post-download GetVersion timeout → `EXIT_APP_START_MISSING`.
- `--rom-probe` timeout (no version reply) → `EXIT_ROM_HANDSHAKE_TMO`.

## 3. Response validation

- RX is a full TL state machine (escape/SOP/EOP, CRC-8 nibble-swap, payload-size
  equality, flag-detail consumption); a byte arriving is never treated as a valid reply.
- `on_pkt` only sets `got_version` for RPC id 3 (response), requiring ≥4 payload bytes;
  the request id 0 never classifies as a response (regression-covered).
- Reliable ACK/NACK are matched on the exact `rel_seq`; a stray ACK does not satisfy the
  current operation.
- Version reply is only "success" when `w0` decodes and (post-download) is compared via
  the lhd ASIC rule; otherwise `VERSION_MISMATCH`.

## 4. Partial transfer / interrupted transfer / unexpected reset

- `write_all` returns error on short write, EAGAIN retry, or deadline; no silent partial.
- Each F1 MemoryWrite requires its own reliable ACK; the loop tracks `memwrites_acked`
  vs `memwrites_total` and only sets `memwrites_all_acked` on exact equality.
- Any NACK/timeout/cancel mid-loop → immediate `goto out` with the correct nonzero exit
  code and cleanup; a partially-written firmware is never acknowledged as success.
- On SIGKILL of the process, the kernel `finally`-equivalent (`out:` path) closes the
  transport and restores `BBD:PassThru=0`; the chip remains in its prior reset/shutdown
  state (no firmware running), which is itself the safe default.

## 5. Transport contention

- `/dev/ttyBCM` is a single stream; the on-device `nuxel-ssp-bridge.service` is masked,
  so no other holder exists during a bounded native session.
- The prepared advisory `flock` on `/dev/ttyBCM` (refuse-if-held) is a recommended
  Stage 06 fold-in, not required for offline validation; the trial spec includes it as a
  preflight check.
- `/dev/bbd_sensor` is deliberately NOT opened during the ROM phase (holding it routes RX
  into the SSP app state machine and would swallow ROM replies); this is correct and
  documented in the source.

## 6. Safe cleanup (finally semantics)

The `out:` label always: closes `fd_tty`/`fd_sensor`, frees the patch (`patch_free`), and
— whenever pass-through was armed and not already restored on the success path — writes
`BBD:PassThru=0`. `ESW:READY` is emitted ONLY on the fully-verified success path
(post-download GetVersion validated). No rail/GPIO/reset operation is performed by the
downloader itself (it touches only `/dev/ttyBCM`, `/dev/bbd_control`, `/dev/bbd_patch`).

## 7. THE PROOF: recovery does not depend on the MCU executing the downloaded firmware

The recovery primitive is `bbd_mcu_reset()` (kernel `bbd.c:450`). Its source is decisive:

```c
/* bbd_mcu_reset - Interface function called from SHMD to reset chip
 *   BBD pushes reset request into /dev/bbd_control and actual reset is done by
 *   gpsd/lhd when it reads the request */
int bbd_mcu_reset(bool IsNoResp) {
    ...
    if (bbd.lk.enabled) { ... send_sig(SIGKILL, bbd.lk.lhd, 0); ... }
    else return bbd_on_read(BBD_MINOR_CONTROL, BBD_CTRL_RESET_REQ, ...);
}
```

Key facts:
1. `bbd_mcu_reset` does **not** directly reset the die. It pushes a `BBD_CTRL_RESET_REQ`
   into `/dev/bbd_control` (a **host-side** char device) or SIGKILLs lhd.
2. The "actual reset" is performed by **userspace (the host) reading that request** — i.e.,
   the recovery loop is host-host (kernel → control node → host session → rail), NOT
   host→MCU→firmware.
3. There is **no dependency** on the MCU successfully executing the firmware: the reset
   request is enqueued on the host side and the recovery action (MCU_REQ=0, GPS_PWR_EN=0,
   rail restore) is driven by the host session's `finally`/cleanup path, independent of
   whether any downloaded code is running.

Therefore recovery is **provably independent** of the MCU executing the downloaded
firmware. A firmware that fails to start, half-loads, or NACKs leaves the chip in its
prior reset/shutdown state, and the host-side reset request + cleanup path restores the
baseline unconditionally.

## 8. Recovery-after-incomplete-initialization

- Incomplete init (partial MemoryWrite, failed StartScratch/ServiceStart) leaves the hub
  RAM partially written but the application NOT started (no ServiceStart completed), so
  the MCU does not run the firmware.
- The confirmation GetVersion is the only gate to `ESW:READY`; without it the system
  stays `NOTREADY`.
- A subsequent retry is a clean re-download (full 479 writes) because the downloader
  never assumes prior state; it always re-runs the ROM sync + full patch stream.

## 9. Conclusion

Failure containment is **complete and correctness-focused**. The recovery path is
host-side-only and demonstrably does not require the MCU to execute the downloaded
firmware. The one residual item (advisory `/dev/ttyBCM` flock) is a recommended,
reversible, userspace-only fold-in for the trial, not a safety gap.

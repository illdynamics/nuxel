### The actual blocker (unchanged, now precisely characterized)
MCU halts: `resetting=1 shutdown=1 enable=0x0`, and `tx=184 rx=0` — **zero RX despite 184B TX over the SPI transport**. The boot ROM never returns GetVersion. This is the "no bidirectional ROM traffic" blocker; root cause (cold-start rail/timing vs SPI electrical vs protocol framing) is **not yet proven**.

### 0027 defects confirmed (must fix before any build/flash)
1. **Self-deadlock**: `bbd_do_transfer()` re-locks `pending_mutex` on its failure path while already held.
2. **Premature parser success**: truncated/invalid records cause a `break` + `nwrites>0` "success".
3. **Contiguous `kmalloc(~439 KB)`** fragmentation risk in `dl_decode_blob`.
4. **Stale ACK correlation** across writes.
5. Duplicate 0023 content + optional-patch silent-skip risk.

### Deliverables written
- `reports/SSP-20261122-LIVE-BASELINE.md`
- `reports/SSP-BOOT-DT-IMMUTABILITY-MANIFEST.json`
- `reports/SSP-ROLLBACK-READINESS.md`
- `report-ssp-prompt-00.md` (this checkpoint)
- `/tmp/nuxel-ssp-baseline/boot-sda14.img` (verified host rollback seed)

### Gate status
`ROLLBACK_READY = PENDING` — only one host copy exists; a second TWRP-accessible copy plus dual-endpoint byte-verify is deferred to Stage 04/05 (no recovery boot triggered in read-only Stage 01).

**No writes, no flash, no firmware, no rail/GPIO/reset.** Next stage is **02** (offline patch surgery on 0025/0026/0027). I will not build or flash until gates 01–04 pass.

I'll pause here and await your go-ahead to proceed into Stage 02 (offline kernel patch surgery), since that's a substantial source-level effort with a clear decision point before any hardware involvement.
tokens used


# SSP-05_16 — Physical First-Light Decision

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 0. Verdict

`PHYSICAL_TRIAL_SAFE = FALSE` — for the specific reason that the proposed operation has
no demonstrated *reachable* ROM-only GetVersion path, independent of any remaining RF
authorization.

This is a stronger, more precise conclusion than 05_15. Prior missions framed the blocker
as "missing vendor timing + RF authorization + proprietary RPC id." This mission
resolved the RPC id (id 0 request / id 3 response) and recovered the firmware identity
and vendor sequence, but uncovered a **deeper, source-proven ordering fact** that changes
the minimal safe trial:

## 1. The decisive finding

`kernel .../bcm_gps_spi.c bcm_rxtx_work_func()`:

```
if (!bcm477x_hello(priv)) {           // MCU_REQ=1, wait MCU_RESP <= 100 ms
    ... bbd_mcu_reset(true); return;  // <-- aborts BEFORE any SSI I/O
}
```

And `bcm477x_rpc_get_version()` (the only ROM GetVersion in the kernel) has **zero
callers** (dead/debug code). Therefore:

- There is **no live route** to a boot-ROM GetVersion through `/dev/ttyBCM` without first
  succeeding the MCU_REQ→MCU_RESP handshake.
- Live `nuxel_hub_diag = mcu_probe=1 shutdown=1 resetting=1` — the hub is in a
  shutdown/reset loop because no firmware has been downloaded/re-started.
- So a "minimal ROM GetVersion" (autobaud + RPC 0) cannot be answered until the MCU is
  out of reset — which is exactly the firmware-download operation that Stage 06 owns.

**Consequence:** the correct minimal physical trial is not "assert GPS_PWR_EN + probe
ROM"; it is "bring the MCU out of reset via the firmware download + app start, then
confirm identity." That is Stage 06, not Stage 05.

## 2. Safety checklist (item by item)

| Requirement | Status | Evidence |
|---|---|---|
| Source-backed signal identity | MET | gpio145/167/168/15 confirmed live (journal) |
| Verified polarity | MET | active-high; kernel drives raw 1/0 |
| Verified init ordering | MET (corrected) | MCU handshake must precede SSI (source-proven) |
| Known driver ownership | MET | kernel bcm_gps_spi.c; userspace-delegated, unowned |
| Resolved reboot hazard | MET (re-confirmed) | prior hazard was regulator cold-cycle (fixed 0025/28/29); GPIO transition caused no reboot this boot |
| Understood affected consumers | MET | no holder of GPS_PWR_EN; hub MCU separate rail |
| Defined abort & recovery | MET | `finally` deassert + `bbd_mcu_reset` |
| No unresolved electrical safety concern | **NOT MET** | GPS_PWR_EN energises GNSS RF; owner RF policy confirmation required |
| Reachable ROM-only GetVersion target | **NOT MET** | dead kernel helper + `hello` gate ⇒ ROM-only probe not physically reachable |

## 3. What changed vs 05_15

| 05_15 blocker | 05_16 status |
|---|---|
| RPC_GET_VERSION=0 "unsourced" | RESOLVED: id 0 = request, id 3 = response (lhd disasm + tests) |
| Missing vendor timing | Partially: ordering recovered; only the datasheet settle-delay still external |
| Proprietary RPC id unknown | RESOLVED (request/response + memwrite/scratch/service) |
| RF authorization | STILL REQUIRED (policy) |
| (new) unreachable ROM-only GetVersion | NEW DECISIVE FINDING: Stage 06 prerequisite |

## 4. Minimum owner action to proceed to Stage 06

The physical trial is now correctly framed as the **Stage 06 firmware-download trial**,
which requires:

1. **RF authorization** (GNSS RF energisation acceptable for a bounded, supervised trial).
2. **One timing artifact** (Broadcom BCM47752 power/ROM-ready datasheet value, OR explicit
   bounded settle-delay instruction, OR the owner's live stock lhd binary for the delay).
3. **Explicit bounded-trial grant** for: MCU wake + patch MemoryWrite(×479) +
   StartScratch + ServiceStart + post-download GetVersion, with recovery bound
   (MCU_REQ=0 / GPS_PWR_EN=0 / `bbd_mcu_reset`).

Until these are provided, no GPS_PWR_EN assertion, no MemoryWrite, no MCU app-start is
performed.

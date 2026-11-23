# SSP-05_15 — Physical First-Light Decision

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## PHASE 1 RESULT (this mission): `PHYSICAL_TRIAL_SAFE = FALSE`

The remaining unsatisfied requirement is **not** a GPIO-ownership or wiring
question; it is a **missing vendor-timing + RF-safety evidence** item plus a
**proprietary-protocol dependency** that cannot be resolved from GPL source.

## 1. The checklist (Section 6), item by item

| Requirement | Status | Evidence |
|---|---|---|
| Source-backed signal identity | MET | gpg0-2 = gpio145, `bcm_gps_spi.c` probe + live sysfs |
| Verified polarity | MET | active-HIGH (DT flag 0x0), kernel drives raw 1/0 |
| Verified init order | MET (for power) | probe sets LOW; userspace gpsd asserts HIGH; source-verified |
| Known driver ownership | MET | kernel `bcm_gps_spi.c`, userspace-delegated, currently unowned |
| Resolved reboot hazard | PARTIAL | GPIO write is not a reboot trigger; prior hazard was the *regulator* cold-cycle (0025/0028/0029), now fixed. GPS_PWR_EN transition has no documented reboot path, but **no live assertion has been independently performed under this mission's supervision.** |
| Understood affected consumers | MET | no process holds GPS_PWR_EN; sensor-hub MCU is on a separate rail; asserting energises GNSS logic+RF only |
| Defined abort & recovery | MET | `nuxel_lhd.py` already restores rail in `finally`; abort = write 0 to `GPS_PWR_EN` value |
| No unresolved electrical safety concern | **NOT MET** | `GPS_PWR_EN` energises GNSS **RF** (radio emission) alongside logic; the RF-safety policy (is energising GNSS RF acceptable) requires owner confirmation. Also the exact GPS_PWR_EN-rise→ROM-ready delay exists only in Broadcom datasheet / lhd disassembly, neither available. |

## 2. Why FALSE (the specific missing evidence)

Two non-bypassable items remain before a supervised assert-then-probe trial can
be declared safe:

1. **RF-safety owner confirmation.** `GPS_PWR_EN` gates GNSS logic *and* RF.
   The owner must confirm energising the GNSS RF domain (even briefly, bounded)
   is acceptable. This is a policy decision, not an engineering fact derivable
   from source.

2. **Post-power timing / ROM-ready delay.** The Broadcom BCM47752 datasheet (or
   Samsung `lhd` disassembly) defines the GPS_PWR_EN-rise → ROM autobaud-ready
   delay. It is not in the GPL tree. Without it, a bounded trial would be
   guessing at the settle time, and the prompt correctly prohibits speculative
   transitions.

In addition, even a successful power transition will not produce a ROM
GetVersion reply unless the **proprietary lhd RPC id/frame** for GetVersion is
correctly reproduced. The current `RPC_GET_VERSION=0` attribution is unverified
(SHA-referenced lhd absent from repo). See SSP-05_15-ROM-ENDPOINT.md §8–9.

## 3. What IS safe to proceed with now (and was done)

- Full read-only live precheck (done, healthy).
- ROM endpoint + power-sequence source audit (done, reports written).
- Offline regression suite (passed: framing, CRC, RX decode, negative cases, patch validation).
- The **software** trial harness is ready: `nuxel_lhd.py` (power+transport) and
  `nuxel_bbd_flash --rom-probe` (autobaud+GetVersion) exist and are separately
  validated. Neither asserts GPS_PWR_EN and probes in the *same* bounded session
  with verified vendor timing, which is the gap to close.

## 4. Minimum owner action required to reach `PHYSICAL_TRIAL_SAFE = TRUE`

Exactly one owner decision plus one artifact:

- **Decision:** authorize energising the GNSS domain (`GPS_PWR_EN=HIGH`), i.e.
  confirm GNSS RF energisation for a bounded, supervised ROM-identity trial is
  acceptable.
- **Artifact (one of):** (a) Broadcom BCM47752 datasheet power-on/ROM-ready
  timing, or (b) the owner's own stock `vendor/bin/hw/lhd` (binary — for bounds
  and RPC-map reference), or (c) explicit owner instruction with a specific
  safe post-power delay and recovery bound.

Until both are provided, the correct record is `PHYSICAL_TRIAL_SAFE = FALSE`,
and no GPS_PWR_EN assertion is performed.

## 5. Trial scope (prepared, to be approved before execution)

If/when approved, the bounded trial is:

1. Assert `GPS_PWR_EN = 1` (single write, readback-verified).
2. Wait the (approved) settle delay.
3. Run the ROM GetVersion probe (autobaud 32 + GetVersion) with the corrected
   vendor framing, bounded 2.5 s RX window.
4. Capture raw RX; validate framing/CRC; record identity.
5. Assert `GPS_PWR_EN = 0` (restore), confirm device healthy (systemd, 0 failed).
6. Single attempt; on no-response, preserve evidence and return to diagnosis.

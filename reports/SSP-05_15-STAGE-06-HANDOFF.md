# SSP-05_15 — Final Stage 06 Handoff

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X
**Kernel:** 4.14.253-gf7194c1d15ed-dirty
**BOOT sha256:** 1be1ded89f9e04a6a2ca0d32d9273bd363c2e200f478ab10213ea3927674a599

## FINAL RESULT

```
READY_FOR_06 = FALSE
```

`POWER_TRANSITION_SAFETY = NOT_RUN`
`ROM_GETVERSION = NOT_RUN`

The ten previously-accepted gates remain valid (re-verified live, no writes).

## Why not ready (honest, precise, non-bypassable)

The Stage 06 readiness depends on two gates that require a **physical GPS_PWR_EN
assertion** to the GNSS domain. This mission established:

1. `PHYSICAL_TRIAL_SAFE = FALSE`. Two items are missing and are **not derivable
   from any source in this repository**:
   - **RF-safety owner confirmation** — GPS_PWR_EN gates GNSS *radio* emission
     as well as logic; energising it requires the owner's explicit policy grant.
   - **Post-power timing / ROM-ready delay** — present only in the Broadcom
     BCM47752 datasheet or Samsung `lhd` disassembly (both proprietary/absent).

2. A **protocol dependency** with the same root: the live ROM GetVersion is
   performed by the proprietary `lhd` over BBD RPC; the `RPC_GET_VERSION=0` id
   used by the native probe is attributed to a `lhd` SHA that is not in this
   repo. The GPL `bbd_rpc_lh.c` enum has id 0 = `IRpcA.A` with no "GetVersion".
   So the exact GetVersion frame cannot be source-verified locally.

## What this mission DID complete (authorized, non-destructive)

1. **Live read-only precheck** — device healthy, all ten baseline gates intact,
   plus new live evidence (gpio145 = GPS_PWR_EN LOW; BBD char-devices; gnss-lhd
   service already asserts power at boot but handshake gps=False).
2. **ROM endpoint analysis** (Section 4) — definitive: correct transport
   (`/dev/ttyBCM`), but the GetVersion RPC id/frame is unverifiable without the
   proprietary lhd; `bcm477x_rpc_get_version()` is orphaned dead code.
3. **Power-sequence reconciliation** (Section 3) — every Section-3 item now
   source-verified (pin gpg0-2/gpio145, active-HIGH, kernel-owned+exported,
   currently unowned, GNSS logic+RF domain, safe sysfs transition mechanism).
4. **Software-blocker elimination** (Section 5) — offline regression suite
   re-run and PASS (TL framing, CRC, RX decode, negative cases, patch
   validation). No software defect in the TL/RPC/CRC code remains; the only
   "software" gap is the proprietary RPC map, which is not a code bug.
5. **Physical-trial decision** (Section 6) — `FALSE`, with exact missing
   evidence and the precise minimum owner action.
6. All seven required reports produced.

## No hardware state was modified

No GPS_PWR_EN assertion, no regulator transition, no reboot, no partition/GPO
write was performed. The device remains in the healthy 05_14 state.

## The single minimum owner action to unblock Stage 06

Provide **both**:

1. **Authorization** to energise the GNSS domain (logic + RF) for a bounded,
   supervised ROM-identity trial (confirming GNSS RF energisation is acceptable).
2. **One of:**
   - the Broadcom BCM47752 datasheet power-on / ROM-ready timing, **or**
   - the owner's own stock `vendor/bin/hw/lhd` binary (for RPC-map + timing), **or**
   - an explicit trial grant specifying a safe post-power settle delay and recovery bound.

With those, the agent can close the harness gap (assert GPS_PWR_EN → verified
settle → corrected GetVersion frame → raw RX capture → restore), run the bounded
trial, and either establish `ROM_GETVERSION = PASS` or preserve evidence and
return to diagnosis.

## Report manifest

- `reports/SSP-05_15-LIVE-BASELINE.md`
- `reports/SSP-05_15-ROM-ENDPOINT.md`
- `reports/SSP-05_15-POWER-SEQUENCE.md`
- `reports/SSP-05_15-PHYSICAL-TRIAL-DECISION.md`
- `reports/SSP-05_15-ROM-FIRST-LIGHT.md`
- `reports/SSP-05_15-ACCEPTANCE.json`
- `reports/SSP-05_15-STAGE-06-HANDOFF.md`

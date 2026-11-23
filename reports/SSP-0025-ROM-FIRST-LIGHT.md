# SSP-0025 — ROM First-Light Status (Prompt 05_8 §7/§8)

**Agent:** DeepSeek-V4-Pro-Thinking
**Date:** 2026-11-22
**Status:** **NOT ATTEMPTED** — no physical power transition, no BOOT flash, no ROM probe this prompt.

---

## 0. Why no ROM trial this prompt

A genuine ROM `GetVersion` requires the MCU boot-ROM autobaud window to be open, which
requires a genuine cold power-cycle (the 0025 `regulator_force_disable` fix), which
requires a deployed kernel change (BOOT-only flash), which requires a **successful
kernel build + preflight**.

This prompt's preflight did **not** pass (full `Image.gz` link blocked — see the
kernel-reconciliation and preflight deliverables). Therefore, by the prompt's own
gates, no ROM trial is permitted, and none was run.

## 1. ROM first-light status (truthful)

| Gate | Status |
|---|---|
| Genuine ROM GetVersion (framed/CRC'd/non-zero LE32 RPC0) | **BLOCKED** (not attempted) |
| Autobaud sequence emitted | NOT ATTEMPTED this prompt |
| SPI TX/RX counters | NOT ATTEMPTED this prompt |
| IRQ 441/443 / controller status | NOT ATTEMPTED this prompt |
| Raw received bytes | NOT ATTEMPTED this prompt |
| ROM framing / CRC validation | NOT ATTEMPTED this prompt |
| ASIC / version identity | NOT OBTAINED |

No `ESW:READY`, WHOAMI, accelerometer, or gyroscope value is synthesized or claimed.

## 2. Live baseline (read-only, this prompt)

```
kernel          4.14.253-gf7194c1d15ed-dirty
vdd_mcu_1p8     state=enabled  num_users=0        (root cause: no kernel ref)
nuxel_ssp_bringup_hw  symbol PRESENT              (0023 deployed)
nuxel_ssp_dl_download symbol ABSENT               (0027 NOT deployed)
mode            normal Nuxel (not recovery)
```

## 3. What the ROM first light REQUIRES (recorded for the future)

1. A successful, source-verified 0025 kernel BLOD build (Image.gz + BOOT candidate) —
   **currently BLOCKED_PREFLIGHT**.
2. Owner authorization for a BOOT-only flash (separate from the power trial).
3. Owner authorization for one bounded `mcu_power` cold-cycle (separate).
4. Then one `--rom-probe` (autobaud + GetVersion), acceptance = valid framed/CRC'd
   non-zero LE32 RPC 0 reply.

## 4. Verdict

**ROM first light: BLOCKED**, upstream of both open authorizations and the preflight
build gate. This is honest; no physical trial was authorized or attempted.

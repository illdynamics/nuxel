# Stage 06 — Round 19 results: exhaustive PDP/attach/auth matrix; bearer still not connected

**Branch:** cs/mob
**Commits:** e7dc9b87 (protocol + attach-flag config), ea6dd38a (auth config)
**Date:** 2026-11-23 CET

## Verdict

STAGE_06_NOT_YET_PASS. Every software-configurable data-session variable was
made runtime-tunable and live-tested against the physical S5000AP. No variant
establishes the default EPS bearer. The Nuxel AP->CP command serialization is
now byte-exact verified for every frame in the default-bearer path; the blocker
is upstream of Nuxel (modem NV / carrier data-service).

## Live matrix (SM-G975F, working SIM seated, PS REGISTERED_HOME 20416)

| Variable | Value | Result |
|---|---|---|
| PDP protocol | IPv4 (wire 0x05) | GPRS_CALL_STATUS state=3 (no bearer) |
| PDP protocol | IPv4v6 (wire 0x04, default) | state=3 |
| LTE attach flag | 3 (apply) | accepted, state=3 |
| LTE attach flag | 1 (define) | GEN result 4 (CP rejects) |
| PDP auth | NONE (1) | state=3 |
| PDP auth | PAP (2) | state=3 |

In every case the full sequence ACKs (GEN 0x8003 / result 0) but the CP
replies `GPRS_CALL_STATUS payload 010300000000000000` = cid 1, state 3
(NOT connected per IpcRxGprsCallStatus @0x321ab0), no ESM cause, and never
emits GPRS_IP_CONFIGURATION. rmnet0..7 stay DOWN.

## Re-verified vendor disassembly (independent, this round)

- `IpcTxSetPdpContext @0x31f6e0`: payload[0]=pdp_type, payload[1]=cid,
  payload[6..37]=APN, payload[38..69]=password (2nd char*), payload[102]=auth,
  payload[104]=protocol. ACTIVATE bit (0x10) OR'd onto flags when the 5th int
  arg is nonzero. Current frame is byte-exact for no-auth internet APN.
- `IpcTxPsAttach @0x31fa98`: attach payload = [1,0,0] (1=attach, 0=suspend,
  0=detach_reason). Current frame is byte-exact.
- `IpcRxGprsCallStatus @0x321ab0`: state 1/10/11 -> connected; anything else
  (incl. live-observed 3) -> NOT connected. Decode is correct (no misread).
- `SetLteAttachProfile @0x22b518` / `IpcTxSetLteAttachProfile @0x320238`:
  payload[0] = 3 when trailing bool set else 1. flag=3 (apply) is correct;
  flag=1 (define) is live-rejected with GEN result 4.

## Conclusion

No missing wire command exists (`SetAttachApn` userspace-only; `SetLteAttachPdnList`
/ `SetLteAttachtype` stubs — round-18). PS registration is genuinely
REGISTERED_HOME. All commands byte-exact and ACKed. The CP nevertheless reports
the default EPS bearer NOT connected with no cause. The remaining root cause is
carrier-side data-service provisioning or the modem's initial-attach APN in NV
(outside reachable userspace; writing NV/EFS remains forbidden absent separate
authorization).

## Safety

RADIO /dev/sda16, BOOT /dev/sda8 unchanged (no protected-partition write).
Wi-Fi (wlan0 10.20.30.16), ZeroTier (ztly5zthnf 10.11.12.99), USB preserved
throughout. Rollback binaries retained:
`nuxel-radiod.bak-stage06-ipv4-20261123T221457`,
`nuxel-radiod.bak-ipv4only-flag3`. Deployed binary
`a9506c24ee2eb8063028a6047b9684c787bde26ccba9d4ff58328b792668bc43`
(defaults unchanged: IPv4v6 / flag 3 / none).

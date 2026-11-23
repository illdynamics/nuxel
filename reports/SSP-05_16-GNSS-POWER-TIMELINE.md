# SSP-05_16 — GNSS Power Event Timeline

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking

## 0. The historical event (reconstructed from this boot's journal)

SSP-05_15 reported `nuxel-gnss-lhd.service` asserted `GPS_PWR_EN=1` at boot, with
`power={'success': True, 'enabled': True}` but handshake `gps: False`, and the GPIO
later read 0. This mission reproduces and fully explains the event.

## 1. Answers to the ten questions

1. **Did the GPIO assertion occur?** YES, for a bounded ~23.7 s window during the
   service run (00:46:30 → 00:46:54, process 5412).
2. **Which process performed it?** `/usr/bin/python3 /usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py --session`
   (the DEPLOYED older copy of nuxel_lhd.py; repo HEAD has since gained a hard refusal,
   see §3).
3. **Exact timestamp:** started 00:46:30, power asserted + readback-verified within the
   `set_power(True)` call; service deactivated 00:46:54 (Status=2, timeout).
4. **Was it subsequently deasserted?** YES, by the service `finally`/cleanup path; live
   gpio145 = 0 now.
5. **Which component deasserted it?** `nuxel_lhd.py cleanup()` → `GpsPowerControl.release()`
   → `set_power(False)`.
6. **Did it trigger a reboot/warning/error?** NO reboot. Repeated kernel lines
   `[SSPBBD] bcm4773_debug_info pin_MCU_REQ:0 pin_MCU_RESP:1` indicate `bcm477x_hello()`
   timeout calls (up to ~7, one per ~1 s) while the transport was open — the *handshake*
   failed, not a crash.
7. **Any hardware-ready condition observed?** NO. `handshake={'ok': False, 'gps': False}`.
8. **Any SPI traffic?** NO *successful* traffic: MCU handshake gated SSI off. No RX
   bytes were exchanged that decoded to a valid response.
9. **Any BBD RPC transmitted?** The deployed service observes/polls; it does NOT emit a
   ROM GetVersion frame in this (older) run. No RPC was sent.
10. **Why GNSS init failed?** (a) The MCU handshake `bcm477x_hello` cannot succeed
    because the hub is `shutdown=1 resetting=1` (no firmware), so all SSI I/O is gated;
    (b) even the deployed daemon only polls SSP state, it does not reproduce the lhd
    patch-download/GetVersion sequence; (c) GNSS position decode is additionally
    proprietary, out of Stage 06 scope.

## 2. Safety determination

The `GPS_PWR_EN` assertion was a **bounded, reversible userspace-only** transition
(gpio145 GPIO output write, not a regulator cold-cycle). It did **not** reboot the
device and did **not** disturb the sensor-hub MCU rail (`vdd_mcu_1p8` stayed enabled,
`num_users=0`). The prior "reboot hazard" was the *regulator* cold-cycle, fixed by
patches 0025/0028/0029. No evidence links the GPIO transition to any reboot or
cross-subsystem harm.

The remaining concern is **RF emission**: `GPS_PWR_EN` energises GNSS logic *and* RF.
Energising GNSS RF is a policy decision requiring owner confirmation (unchanged).

## 3. Deployed-vs-repo discrepancy (documented)

- Deployed `/usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py` (md5 `4e562874ab80f9c0088f12df813662aa`):
  an earlier revision whose `run_session()` asserts power, opens transport, polls.
- Repo `services/nuxel-gnss/src/nuxel_lhd.py` (HEAD): `run_session()` now **refuses**
  (`INITIALIZATION_PROTOCOL_UNVERIFIED`) before power/device access.

The repo has since been hardened to not assert power until a verified protocol+timing
contract exists. This is the correct state and should be the version deployed in any
approved Stage 06 trial.

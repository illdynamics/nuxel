# SSP-06_01 — Recovery Validation (three-level classification)

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06_01

## 0. Verdict

Recovery is classified at three distinct levels (per the mandate) and NOT
collapsed into a single "proven" claim.

- `RECOVERY_DESIGNED` — **CONFIRMED** (source-audited).
- `RECOVERY_OFFLINE_VALIDATED` — **CONFIRMED** (offline tests + code audit).
- `RECOVERY_PHYSICALLY_VERIFIED` — **NOT VERIFIED** (no physical trial has run).

## 1. `bbd_mcu_reset` — what it actually does (re-read this mission)

`kernel/.../bbdpl/bbd.c:444-472`:

```c
int bbd_mcu_reset(bool IsNoResp)
{
    pr_info("reset request from sensor hub\n");
    if (bbd.ssp_cb && bbd.ssp_cb->on_mcu_reset)
        bbd.ssp_cb->on_mcu_reset(bbd.ssp_priv, IsNoResp);

    if (bbd.lk.enabled) {
        /* to fix lhd hang issue, we don't use lhd's control interface to reset mcu */
        ...
        ret = send_sig(SIGKILL, bbd.lk.lhd, 0);
        ...
    } else
        return bbd_on_read(BBD_MINOR_CONTROL, BBD_CTRL_RESET_REQ, ...);
}
```

**Decisive:** `bbd_mcu_reset` does NOT directly reset the die. It (a) notifies the
SSP callback, and (b) either SIGKILLs the lhd userspace or pushes a
`BBD_CTRL_RESET_REQ` into the host-side `/dev/bbd_control` char device. The
"actual reset" is performed by **host userspace** reading that request. This is a
host→host loop, independent of whether the MCU is executing the downloaded
firmware.

## 2. Host-side state actually reset

| State | Mechanism | Independent of firmware execution? |
|---|---|---|
| lhd userspace | SIGKILL (kill victim) or control-request to host | ✅ yes |
| SSP callback (`on_mcu_reset`) | sets hub reset flags on host | ✅ yes |
| Transport restore | `BBD:PassThru=0` via cleanup `out:` path in downloader | ✅ yes |
| `GPS_PWR_EN` / `MCU_REQ` | restored by host session finally-path (`GPS_PWR_EN=0`, `MCU_REQ=0`) | ⚠️ only if the host finally-path runs |

The last item is the one caveat: `GPS_PWR_EN=0`/`MCU_REQ=0` restoration is driven
by the *host* session's cleanup path (the downloader's `out:` label or the service
`finally:`). If the host process is SIGKILLed mid-flight, the *kernel* default for
`GPS_PWR_EN` is its probe state (LOW), and `mcu_req` is deasserted by
`bcm477x_hello` timeout. These defaults are safe (both LOW = unpowered), so even a
host crash leaves the domain power-gated.

## 3. Remaining unverified recovery actions (honest list)

| Action | Status |
|---|---|
| GPIO return-to-inactive (`GPS_PWR_EN=0`, `MCU_REQ=0`) on host finally-path | OFFLINE_VALIDATED (code audit); NOT physically verified |
| Power-domain state independent observation (`vdd_mcu_1p8` vs `GPS_PWR_EN`) | LIVE-OBSERVED read-only (both currently safe); transition NOT physically exercised this mission |
| Transport close after timeout | OFFLINE_VALIDATED (downloader `out:` closes fds) |
| Host remains operational after MCU nonresponse | LIVE-OBSERVED (device healthy with MCU `shutdown=1`); NOT stress-tested during a download attempt |
| Failed startup → GNSS/other service impact | NOT demonstrated (no trial run) |
| Regulator cold-cycle (in `nuxel_ssp_bringup_hw`) | **FORBIDDEN for trial** — see root-cause report; excluded explicitly |

## 4. Conclusion

Recovery is **designed** and **offline-validated**, but **not physically verified**
because no physical trial has run. Per the mandate, physical recovery cannot be
claimed proven; the trial's authorisation document carries this as a residual
risk and imposes an unconditional, host-driven finally-path restore bound.

For the physical trial to be safe, the following must hold (all currently
satisfied as code + live read-only baseline, pending the trial):

1. The downloader restores `BBD:PassThru=0`, `GPS_PWR_EN=0`, `MCU_REQ=0` in its
   `out:`/finally path unconditionally.
2. `bbd_mcu_reset` remains reachable via `/dev/bbd_control` (host-side).
3. The trial does NOT invoke `nuxel_ssp_bringup_hw` (which auto-cold-cycles the regulator).

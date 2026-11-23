# SSP-06_01 — Recovery Validation, Independently Re-checked (Task C)

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06_01 (final unblock)
**Supersedes** the prior `SSP-06_01-RECOVERY-VALIDATION.md`, which compressed
“host-side cleanup works” into “recovery is complete”. It is not complete.

## 0. Verdict

```
RECOVERY = DESIGNED + OFFLINE_VALIDATED, NOT PHYSICALLY VERIFIED
           and NOT a "return to a known hardware state"
```

Two claims in the previous plan are **withdrawn**:

- **Withdrawn:** “`bbd_mcu_reset` resets the MCU.” It does not. It is a host-side
  notification / SIGKILL of the *host* lhd process. It never touches the die.
- **Withdrawn:** “recovery returns the hardware to a known state.” The host can
  restore *its own* GPIO outputs and file descriptors. It **cannot** observe or
  restore the MCU's internal state (RAM contents, PC, boot-ROM state machine,
  learned autobaud divisor). After a partial download the MCU is in a state we can
  describe only as “not known, not observable” — not “known good”.

What *is* defensible: the **hazard surface is bounded** to the GNSS domain
(`GPS_PWR_EN` gpio145, MCU_REQ gpio167, the SSI stream), the host can force all
relevant outputs to their inactive values, and a full die reset requires the
`vdd_mcu_1p8` rail ��� which this trial is **forbidden** to cycle.

## 1. `bbd_mcu_reset` — what it really is (re-read)

`bbdpl/bbd.c:449-473`:

```c
int bbd_mcu_reset(bool IsNoResp)
{
    if (bbd.ssp_cb && bbd.ssp_cb->on_mcu_reset)
        bbd.ssp_cb->on_mcu_reset(bbd.ssp_priv, IsNoResp);   /* host bookkeeping */

    if (bbd.lk.enabled) {
        /* to fix lhd hang issue, we don't use lhd's control interface to reset mcu. */
        ... ret = send_sig(SIGKILL, bbd.lk.lhd, 0);          /* kill HOST lhd  */
        ...
    } else
        return bbd_on_read(BBD_MINOR_CONTROL, BBD_CTRL_RESET_REQ, ...); /* host node */
}
```

- With `CONFIG_LHD_KILLER` (`bbd.lk.enabled = true` at `bbd_init_lk()`, `:327-333`),
  the only action is `send_sig(SIGKILL, bbd.lk.lhd, 0)` — and `bbd.lk.lhd` is set
  in `bbd_common_open()` (`:605`, minor == BBD_MINOR_SENSOR branch) to the task that opened `/dev/bbd_sensor`.
  The downloader deliberately does **not** open `/dev/bbd_sensor`
  (`nuxel_bbd_flash.c:923-933`), so `bbd.lk.lhd` is `NULL` → it returns `-1` and
  does nothing at all. **The reset is a no-op during the planned trial.**
- `BBD_CTRL_RESET_REQ` is read back by *userspace* from `/dev/bbd_control`; there
  is no kernel GPIO action and no MCU command in this path.
- `callback_bbd_on_mcu_reset()` in `ssp_dev.c` only adjusts host flags/counters.

**Therefore:** a “reset” in this plan is a *host software* action. It is useful
for clearing host-side lock/state, and it is **independent of whether the MCU is
executing firmware** — but it is **not** a physical MCU reset, and it must not be
presented as one. The only physical MCU reset available to software is dropping
`vdd_mcu_1p8`, which the trial forbids.

## 2. Intended inactive states (each with its mechanism and limit)

| Signal | Inactive value | Who can force it | Verified how (offline) |
|---|---|---|---|
| `GPS_PWR_EN` gpio145 | `0` (out lo) | root write to `/sys/devices/virtual/sec/gps/GPS_PWR_EN/value`; kernel probe default is `0` (`bcm_gps_spi.c:1218`) | live readback currently `0`; export path exists |
| `MCU_REQ` gpio167 | `0` (out lo) | kernel via `bcm477x_hello` timeout / `bcm477x_bye()` | live debug GPIO shows `out lo`; do **not** rely on userspace sysfs write (the export is owned by the driver and re-export refused — see §5) |
| `BBD:PassThru` / `SSI:PassThru` | pass-through off | `write_control("BBD:PassThru=0")` in downloader `out:` path | code-audited |
| `/dev/ttyBCM` fd | closed | downloader `out:` closes `fd_tty` | code-audited |
| `/dev/bbd_sensor` | not opened at all | by design during ROM phase | code-audited + offline RPC-id recorder |
| `vdd_mcu_1p8` | **unchanged / enabled** | nobody (forbidden) | live `enabled`; no code path in `nuxel_bbd_flash` touches it |

Notes:

- `GPS_PWR_EN` restoration is only as good as the process that performs it. A
  `SIGKILL -9` of the downloader skips the `out:` label. The **kernel default** for
  the pin is output-low from probe, but there is **no kernel shutdown hook** that
  re-drives it to 0 after a userspace crash. So “crash ⇒ rail safe” is **not**
  proven; it is only true because the value written happens to be `1` and would
  *stay* `1` on a kill. This is a real limitation (see §4).
- The downloader's `out:` path writes `BBD:PassThru=0` only when
  `ret != 0` and `ret != EXIT_IDENTITY_INVALID`; on the `--flash` success path it
  writes `BBD:PassThru=0` explicitly (`nuxel_bbd_flash.c:1050`). Both covered.

## 3. Transport cleanup

- Single stream `/dev/ttyBCM`: the downloader opens it, writes, and closes it in
  `out:`. The kernel workqueue (`bcm477x_wq`, `alloc_workqueue(...,1)`) is
  single-threaded; cancelling is not needed for the fd close to be effective.
- No advisory `flock` is implemented in `nuxel_bbd_flash.c`. Exclusivity rests on
  service state (now enforced, see the service remediation report) and on the
  operator not running two tools. Adding `flock(LOCK_EX|LOCK_NB)` is a
  recommended, reversible hardening, **not** a recovery primitive.
- `nuxel-ssp-bridge.service` remains masked; `nuxel-gnss-lhd.service` is disabled
  with a start-condition. Both verified live this mission.
- The GNSS API in `nuxel-http-bridge` can open/close a rail lease (via
  `GnssProvider.power_rail`); with no location-policy file and no user request, it
  does not assert the rail at boot. Verified: no policy file, rail `0`.

## 4. Recovery verification criteria — what can and cannot be proven

**Provable by the host alone (acceptance criteria for the trial's *recovery*
portion):**

1. `GPS_PWR_EN` readback `= 0`.
2. `MCU_REQ` level `= 0` (kernel debug GPIO output line shows `lo`).
3. `/dev/ttyBCM` has no holder (`fuser`), and the downloader process exited with
   a documented code.
4. No `MemoryWrite`/`StartScratch`/`ServiceStart` was emitted in a non-trial run
   (offline RPC-id recorder).
5. `vdd_mcu_1p8` still `enabled` with no transition in the journal.
6. No BOOT/DTB/DTBO/recovery write (nothing in the tool touches those paths).

**NOT provable by the host alone (must be stated as limitation):**

- That the MCU has returned to its pre-trial internal state.
- That the boot-ROM or firmware is in a known PC/RAM state.
- That the ROM's learned autobaud rate/state is reset.
- That the receiver is electrically quiescent (only the rail pin is observable;
  internal blocks may remain powered from `vdd_mcu_1p8`).

A *physical* MCU reset (rail cycle) is the only known way to force an unknown
die state back to “reset vector”. That is exactly what this trial is forbidden to
do. This is the core recovery-safety gap.

## 5. Offline validation performed this mission

- Read every recovery-relevant function (`bbd_mcu_reset`, `bbd_common_open`,
  `bbd_control`, `bcm477x_hello/bye`, `bcm_rxtx_work_func`) at file:line.
- Confirmed the downloader never opens `/dev/bbd_sensor` and never touches the
  regulator (`grep -n "mcu_power|vdd_mcu|regulator" nuxel_bbd_flash.c` → none).
- Confirmed `bbd.lk.lhd` is only set by an open of `/dev/bbd_sensor`:
  `bbd_common_open()` `:605`, minor == `BBD_MINOR_SENSOR`.
- Live (read-only) confirmed: gpio145 `out lo`, gpio167 `out lo`, MCU_RESP input
  high, `vdd_mcu_1p8` enabled, no rail holders, services as specified.
- Confirmed `GPS_PWR_EN` is a *single-owner* kernel-provided GPIO write and
  that the sysfs export is a kernel-exported link (not an independent pin owner);
  this is why the “inactive state” restore is meaningful for that one pin.

## 6. Conclusion (what the trial authorization must say)

Recovery is **host-state recovery**: it guarantees our own outputs are off and our
own FDs are closed, on the normal exit path. It does **not** guarantee the MCU
returns to a known firmware state, and it cannot substitute for a physical reset.
Any trial authorization must therefore:

- call it “host-side restore + bounded containment”, not “recovery to known state”;
- keep `vdd_mcu_1p8` untouched by explicit prohibition;
- require a *supervised* operator who can power-cycle the handset manually if the
  GNSS rail/domain behaves unexpectedly (the only true full recovery available);
- block retry storms and any second attempt without a new authorization.

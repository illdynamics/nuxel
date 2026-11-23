# SSP-06_01 — Physical Trial Authorization (EXPLICIT OWNER APPROVAL REQUIRED)

**Date:** 2026-11-23 (final unblock pass)
**Agent:** Nuxel Stage 06_01
**Status:** `READY_AS_DOCUMENT` / **trial not authorized**
**MCU first light:** `NOT_RUN`
**Physical firmware execution performed by this mission:** **NO**
**This document is not the owner decision, and this prompt is not the owner decision.**

---

## 0. What is requested (one sentence)

Authorize **one** bounded, supervised, single-shot **boot-ROM identification** attempt
(or, as a second separately-granted scope, a full firmware-download + app-start trial)
on the handset, launched from an operator terminal with a prepared host-side
termination watchdog, under the exact scope, criteria and restrictions below.

Two scopes are defined so the owner can grant the smaller one first:

| Scope | Does | Does not |
|---|---|---|
| **S1 — ROM identity** (`--rom-probe`) | powers the GNSS domain, sends autobaud, sends GetVersion (id 0), waits ≤ 2500 ms ×2 | no MemoryWrite, no StartScratch, no ServiceStart, no `ESW:READY` |
| **S2 — Firmware + app start** (`--flash`) | S1, then 479 × MemoryWrite, StartScratch, ServiceStart, confirmation GetVersion, and only then `ESW:READY` | no rail/reset/GPIO writes, no partition write, no reboot |

**Recommended first grant: S1 only.** It answers the single open question (“does the
ROM answer at all?”) with ~3 KB of writes and no firmware execution.

## 1. Exact target

| Item | Value |
|---|---|
| Device | Samsung Galaxy S10+ `SM-G975F` |
| Serial | `R58M75KDB2X` |
| Product / SoC | `beyond2lte` / EXYNOS9820 |
| Kernel (running) | `4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT` |
| MCU controller | `BCM47752KUB1G`, rev `BR0121080900,BR010` |
| Firmware (device bytes) | blob SHA-256 `56e8b1ea4b34077f0c5c31b54c8619343d95d4f109c8ae54b99ed54a6b1e6d2d` |
| Firmware container | SHA-256 `0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72`, 897113 B |
| Records | 479 × `F1`; ASIC `0x004775B0`; entry `0x00800161`; first dest `0x00800000` |
| Stock provenance | `G975FXXS9DTK9`; vendor lhd `6362e80d…` |

Firmware identity was verified this mission **three ways**, including the exact bytes
the running kernel serves at `/dev/bbd_patch`. See
`reports/SSP-06_01-FIRMWARE-COMPATIBILITY.md`.

## 2. Verified preconditions (all checked live this mission)

| # | Precondition | Verified value |
|---|---|---|
| P1 | `nuxel-gnss-lhd.service` cannot assert the rail at boot | **disabled + start-condition**; inactive; condition unmet |
| P2 | Deployed GNSS userspace is the hardened refusal build | `nuxel_lhd.py` = `aeed416d…` (repo HEAD) |
| P3 | `nuxel-ssp-bridge.service` | masked, inactive |
| P4 | No process holds `/dev/ttyBCM` / `/dev/bbd_control` / `/dev/bbd_sensor` | `fuser` → none |
| P5 | `GPS_PWR_EN` (gpio145) | `out lo`, value `0` |
| P6 | `MCU_REQ` (gpio167) | `out lo`, value `0` |
| P7 | `MCU_RESP` (gpio168) | `in hi` — a *level*, not an ack (see §4) |
| P8 | `vdd_mcu_1p8` | enabled, use count `0`, 1800 mV (**never touched**) |
| P9 | Hub state | `mcu_probe=1 shutdown=1 resetting=1`, `sensor_state=0x3feff` |
| P10 | Firmware identity on device | container `0b53f3b0…`, blob `56e8b1ea…` (exact) |
| P11 | GNSS config preserved | `/etc/nuxel/gnss/gnss.json` `f402c54e…`, untouched |
| P12 | No location consumer auto-starts GNSS | no location-policy file; rail idle |

## 3. Exclusive hardware ownership — status and residual

**Claimed:** at trial time, no *software* owner of the GNSS domain besides the trial
process. This is now true by construction (P1–P4) and is a material improvement over
the pre-mission state, where a stale boot service asserted the rail every boot.

**Proven boundaries:**

- `/dev/ttyBCM` is a single stream; the kernel serialises `.write()` bytes into one
  circular buffer, so two concurrent writers interleave and corrupt framing. The
  trial must not run concurrently with anything else.
- `nuxel-http-bridge` can write `GPS_PWR_EN` only through an explicit API call under a
  lease, not as a boot action. If anyone uses the location API during the trial, a
  rail write is possible. **Operator instruction: do not use location features during
  the trial.**

**Residual ownership gap (honest):**

1. There is **no enforced exclusive lock**. `nuxel_bbd_flash` does not `flock()`
   `/dev/ttyBCM`; exclusivity rests on P1–P4 and on the operator. A future hardening
   should add `LOCK_EX|LOCK_NB` (reversible, userspace-only).
2. The *kernel itself* is always a co-owner: it drives MCU_REQ and calls
   `bbd_mcu_reset()` from the SSI workqueue when hello times out. The trial cannot
   stop that. It is safe only because `bbd_mcu_reset()` has no physical effect in
   this configuration (see `SSP-06_01-RECOVERY-VALIDATION.md` §1) — but it means the
   host is **not** the only driver of the handshake pin.
3. `nuxel-gnss-lhd.service` remains *present* (disabled). If a future image update
   re-enables it, the start-condition still blocks it until an authorization file is
   created. This is a deliberate, reversible guard, not a claim that the unit is gone.

## 4. Timing / readiness evidence (read before approving)

**Summary: readiness is UNRESOLVED.** The previous plan treated the
MCU_REQ→MCU_RESP handshake as an observable readiness gate. Source re-reading shows it
is a *work-item preamble*, not a readiness proof:

- `bcm_rxtx_work_func()` (`bcm_gps_spi.c:883-901`) runs `bcm477x_hello()` before
  every SSI burst and aborts if it fails.
- `bcm477x_hello()` (`:496-537`) succeeds on **one** GPIO168 HIGH read within ~100 ms.
  It does not validate *what* answered, and there is no sticky ready state.
- The only kernel ROM-autobaud helper (`bcm_gps_regs.c:46`) has **zero callers**;
  the kernel never performs ROM identification.
- Live evidence contradicts readiness: MCU_RESP was observed HIGH while MCU_REQ was
  LOW, with the GNSS domain powered ~24 s and the system still `GPS: false`.
- `GPS_PWR_EN → ROM-autobaud-ready` settle time and the 32-vs-36 byte autobaud choice
  are **not** in any authorized local source (kernel, patches, lhd analysis, docs).

**Consequence:** the trial's autobaud is a **bounded blind attempt with definitive
failure detection**, not a “we waited until ready, so it is safe” operation. Full
derivation and the exact missing evidence are in
`reports/SSP-06_01-TIMING-EVIDENCE.md`.

## 5. Recovery evidence and limitations (read before approving)

**What is true:**

- The downloader's `out:` path closes all FDs and writes `BBD:PassThru=0` on every
  non-success exit; on success it writes `BBD:PassThru=0` then `ESW:READY`.
- The downloader never opens `/dev/bbd_sensor`, never writes a regulator, and never
  writes BOOT/DTB/DTBO/recovery.
- `bbd_mcu_reset()` is **host-side only** (`bbd.c:449-473`): a SIGKILL of the host
  `lhd` task (NULL here, because `/dev/bbd_sensor` is not opened → no-op) or a string
  pushed to the host `/dev/bbd_control` node. It does **not** reset the die.
- `GPS_PWR_EN` falls back to the kernel probe default (`out lo`) after a handset
  reboot, which is the only true full reset available.

**What is NOT true / NOT proven:**

- “Recovery returns the hardware to a known state” — **withdrawn**. The MCU's internal
  state after a partial download is unobservable and cannot be restored without a
  `vdd_mcu_1p8` rail cycle, which this trial forbids.
- “A host crash is safe because the pin defaults low” — **not proven**. A `SIGKILL -9`
  skips the `out:` label; the pin would stay at whatever the host last wrote. Hence
  the required host-side watchdog below.
- “MCU_REQ returns to 0 automatically” — only after the kernel's hello timeout; it is
  not an orderly de-assert.

**Mandatory compensating control (owner/operator):** before launching, arm an
independent host-side watchdog that restores the rail if the launched process dies
without the expected exit code:

```sh
# Run on the handset as root, in the operator's terminal.
# Only ever writes "0" to the rail, on any exit of the wrapped trial process
# (success, failure, SIGINT/SIGTERM/HUP). Never writes "1"; never touches
# vdd_mcu_1p8 / mcu_power.
RAIL=/sys/devices/virtual/sec/gps/GPS_PWR_EN/value

cleanup() {
    rc=$?
    printf '0' > "$RAIL"
    printf 'watchdog: rail=%s trial_rc=%s\n' "$(cat "$RAIL")" "$rc" >&2
}
trap cleanup EXIT
trap 'exit 143' TERM INT HUP

nuxel_bbd_flash --rom-probe &        # S1; use --flash only under an S2 grant
child=$!
wait "$child"
```

Validation of this exact watchdog pattern (host simulation, with a file standing in
for the rail): normal non-zero exit → rail `0`, rc `127`; `SIGTERM` to the wrapper →
rail `0`, rc `143`; success → rail `0`, rc `0`.

A correct watchdog only ever writes `0` to the rail and only after the trial process
exits; it must never write `1`. If the rail stays `1`, the operator's recourse is a
normal handset reboot (not a rail cycle under software control).

## 6. Exact proposed trial scope — S1 (recommended first grant)

**Preflight (read-only, must all hold):** P1–P12 from §2; operator at the device;
handset on charger or > 50 % battery; screen on; no location use.

**Sequence (one attempt, one process, monotonic deadlines everywhere):**

1. Confirm `GPS_PWR_EN=0`, no `/dev/ttyBCM` holder, service disabled.
2. Arm the host watchdog (only writes `0` on abnormal exit).
3. Write `GPS_PWR_EN=1` (gpio145) — **the RF step**. Verify readback `=1`.
4. Run `nuxel_bbd_flash --rom-probe` (or the equivalent reviewed binary):
   - opens `/dev/ttyBCM` (kernel hello gates each burst),
   - `SSI:PassThru=1`,
   - 32 × `0x80` autobaud, 20 ms gap, GetVersion (id 0), 2500 ms window;
   - if no valid reply: 36 × `0x80`, 20 ms gap, GetVersion, 2500 ms window;
   - **no** MemoryWrite, StartScratch, ServiceStart or `ESW:READY` in this path.
5. Capture RAW RX bytes and decoded RPC records to evidence.
6. Unconditional cleanup: `GPS_PWR_EN=0`; verify; close fds; `BBD:PassThru=0`.
7. Confirm rail `0`, `MCU_REQ` `0`, no holders; preserve evidence; **do not retry**.

**Success:** a CRC-valid TL frame carrying RPC id 3 (3 × LE32) whose first word is
`0x004775b0`, observed while a GetVersion request was outstanding.

**Distinct negative outcomes (all are *results*, not failures to hide):**
`ROM_HANDSHAKE_TIMEOUT` (no reply), `TRANSFER_REJECTED` (NACK), `TRANSPORT_UNAVAILABLE`.

### S2 (separate grant, only after S1 succeeds)

Continue in the same process (the downloader supports `--flash`):
479 × MemoryWrite (id 5) each needing a reliable ACK (1500 ms), StartScratch (id 46,
entry + 40 ms), ServiceStart (id 55, entry + 4 zero LE32 + 100 ms), confirmation
GetVersion (2500 ms) — and `ESW:READY` **only** if that confirmation matches. Any
NACK/partial/mismatch aborts before `ESW:READY`.

## 7. Expected observables

| Step | Expected | If not |
|---|---|---|
| rail write | readback `1` | abort |
| kernel hello | no `MCU_REQ_RESP timeout` at that instant | kernel calls host-side reset (no-op) |
| autobaud 32 | valid id-3 reply (unknown if it will) | bounded fallback 36 |
| GetVersion | id 3, 3×LE32, w0 `0x4775b0` | `ROM_HANDSHAKE_TIMEOUT` |
| S2 writes | 479 reliable ACKs | `TRANSFER_REJECTED`/`INCOMPLETE` |
| S2 confirmation | id 3, w0 `0x4775b0` | `APP_START_MISSING` |

## 8. Failure termination criteria (any one → stop, restore, no retry)

1. Rail readback ≠ requested value.
2. Any NACK on any reliable RPC.
3. No valid GetVersion within the first attempt **and** the second attempt, each
   capped at 32/36 bytes + 20 ms gap + 2500 ms GetVersion window (worst-case
   bounded by the downloader's own timers; no wall-clock beyond that is claimed).
4. CRC-malformed frames or non-id-3 RPCs treated as success (must not happen).
5. Post-start GetVersion mismatch or absence (S2).
6. Any `vdd_mcu_1p8` transition, any unexpected GPIO direction/value change, any
   change to `mcu_test`/`reset` counters other than documented.
7. Any kernel warning/panic, any service restart storm, any reboot.
8. Operator observes anything unexpected physically (heat, noise, device unresponsive).
9. Watchdog fires, process killed, or terminal session lost.

On termination: evidence preserved, `GPS_PWR_EN=0` verified, no second attempt without
a **new** written authorization.

## 9. Physical-operation risks (complete list)

| Risk | Likelihood | Impact | Mitigation / accept |
|---|---|---|---|
| GNSS RF energisation (`GPS_PWR_EN=1`) | certain | radio emissions | owner must explicitly accept; keep window to seconds |
| Bytes sent to a ROM that is not listening/has wrong baud | likely (unresolved) | undefined ROM behaviour, no physical hazard identified | bounded count; abort criteria |
| Partial MemoryWrite on S2, telemetry RAM corrupted | plausible | MCU may not boot application until rail cycle | no `ESW:READY`; rail cycle forbidden → accept “MCU not running” state |
| Host process killed mid-flight → rail stays 1 | possible | battery drain, RF stays on | host watchdog + operator reboot |
| Kernel hello timeout → host-side reset storm | certain while MCU unresponsive | log spam, host state churn | one process, one attempt; close fds |
| Unknown interaction with sensor-hub driver (`initialize_mcu`) | possible | sensorhub errors/reboots | services masked; monitor `dmesg`/journal |
| Electrical/thermal event inside GNSS domain | unlikely, unquantified | hardware | supervised operator, abort on warning, manual power-off |
| Long-term internal state drift of the MCU | possible | future bring-up may need rail cycle | accepted, documented |

**No partition, bootloader, EFS/calibration, modem, or kernel image is touched by any
scope.** The working Nuxel boot, kernel, device trees and recovery images are
preserved by construction (the tools contain no such write path).

## 10. Specific owner approvals still required (tick each)

| # | Approval | Status |
|---|---|---|
| A1 | **GNSS RF energisation** for S1: `GPS_PWR_EN=1` for seconds, supervised | ☐ required |
| A2 | Accept **unresolved readiness** (autobaud is a bounded blind attempt, not gated by a ROM-ready proof) | ☐ required |
| A3 | Grant **exactly one** S1 run (ROM identity only) | ☐ required |
| A4 | S2 (firmware download + app start) — separate grant, only after S1 success | ☐ required (later) |
| A5 | Accept that “recovery” = host-side restore + operator reboot; **no** software rail-cycle reset | ☐ required |
| A6 | Assign the supervising operator and their manual power-off authority | ☐ required |
| A7 | (Optional) Provide the BCM47752 datasheet or a stock SSI trace, which would close A2 and allow a truly gated trial | ☐ optional |
| A8 | (Optional) Authorize the `flock`/watchdog code hardening before the trial | ☐ optional |

## 11. Evidence to capture during the trial

- UTC + monotonic timestamps around rail write, each autobaud prefix, each GetVersion.
- Raw RX hex dump and decoded TL/RPC records (with CRC status).
- Exit code and its name; per-write ACK/NACK (S2).
- Post-run rail/MCU_REQ/GPIO/diag snapshot; journal and `dmesg` extracts.
- Operator notes: physical observations, any abort reason.

## 12. Physically verified vs offline-only (as of this document)

| Item | Status |
|---|---|
| Deployed service hardening (fail-closed, gated) | **PHYSICALLY VERIFIED** (live) |
| Firmware identity on the device | **PHYSICALLY VERIFIED** (live read-only) |
| Exclusive *software* ownership | **PHYSICALLY VERIFIED** (live) |
| Protocol framing / RPC ids / downloader logic | OFFLINE VALIDATED |
| ROM autobaud acceptance | **NOT VERIFIED** |
| Firmware die acceptance / post-download GetVersion | **NOT VERIFIED** |
| MCU reaching `ESW:READY` | **NOT VERIFIED** |
| Recovery to “known hardware state” | **NOT VERIFIED**, and not achievable without a forbidden rail cycle |

---

**No physical execution is authorized by this document. Each ☐ in §10 requires an
explicit, separate owner decision.**

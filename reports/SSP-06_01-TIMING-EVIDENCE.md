# SSP-06_01 — Timing / Readiness Evidence (Task B, reassessed)

**Date:** 2026-11-23
**Agent:** Nuxel Stage 06_01 (final unblock)
**Supersedes** the previous `SSP-06_01-TIMING-EVIDENCE.md`, which asserted the
MCU_REQ/MCU_RESP handshake is “the observable readiness gate”. Re-reading the
sources shows that claim was **overstated**; this document corrects it.

## 0. Verdict

```
TIMING = UNRESOLVED
```

`MCU_REQ→MCU_RESP` is a **kernel wake/knock gate**, not a firmware/ROM-ready
proof. Autobaud/GetVersion readiness has **no source-backed condition** in the
repository. The previous plan of “autobaud, then 36-byte fallback, then
GetVersion” after the handshake is therefore a *bounded blind attempt*, not a
gated operation.

**Exact missing evidence (the only thing that would resolve this):**

1. The Broadcom BCM47752 GNSS/boot-ROM datasheet (or vendor BSP document) stating
   **(a)** that the host SSI interface is valid before/without the MCU application
   firmware, **(b)** the `GPS_PWR_EN` → ROM-autobaud-ready and
   `vdd_mcu_1p8` → ROM-ready settle bounds, and **(c)** the required autobaud
   prefix/timing (32 vs 36 bytes, inter-byte spacing).
2. **OR** a captured stock-hardware SSI trace (vendor `lhd`/`gpsd` boot on the
   same `G975FXXS9DTK9` build) showing when the first autobaud byte is sent after
   rail/handshake, and whether the ROM answered.
3. **OR** a driver source tree in which the kernel itself performs the ROM phase
   (the current tree has no such live path).

Until one of these exists, no delay value can be derived. None is invented here.

## 1. What the source actually proves (file:line)

Path prefix: `kernel/s10plus/.build/src.polluted.case-insensitive/drivers/sensorhub/brcm/bbdpl/`

### 1.1 Handshake is a TX/RX work-item preamble, re-run per burst

`bcm_gps_spi.c:883-901` (`bcm_rxtx_work_func`):

```c
if (!bcm477x_hello(priv)) {          /* :896 */
    pr_err("[SSPBBD]: %s[%s] timeout!!\n", ...);
    bcm4773_debug_info();
    bbd_mcu_reset(true);             /* :900  host-side reset request */
    return;                          /* aborts before any SSI I/O   */
}
```

`bcm477x_hello()` (`:496-537`):

```c
gpio_set_value(priv->mcu_req, 1);              /* :504 */
while (!gpio_get_value(priv->mcu_resp)) {      /* :505 */
    if (count++ > MAX_RESP_CHECK_COUNT) {      /* :506  MAX == 100 (:498) */
        gpio_set_value(priv->mcu_req, 0);      /* :507 */
        return false;
    }
    wait1secDelay(count);                      /* :514  mdelay(1)*100 then msleep(1) */
    if (gpio_get_value(priv->mcu_resp)) break; /* :519 */
    if (count % 20 == 0) {                     /* :522 re-toggle */
        gpio_set_value(priv->mcu_req, 0); mdelay(1);
        gpio_set_value(priv->mcu_req, 1); mdelay(1);
    }
}
...
return true;                                   /* :536 */
```

`bcm477x_bye()` (`:542-546`) drops MCU_REQ at the end of each work item.

**Consequences (source facts, not interpretation):**

- Every `/dev/ttyBCM` write is preceded by a *fresh* hello. There is no sticky
  “ready” flag. A single observed HIGH MCU_RESP says nothing about readiness 100 ms
  later; readiness must hold at the instant of each transmission burst.
- The successful exit condition is only “a GPIO input read HIGH within ~100 ms”.
  **Nothing in the kernel validates what the HIGH means** — not ROM, not
  firmware, not version.
- `MAX_RESP_CHECK_COUNT` is 100 and `wait1secDelay()` uses `mdelay(1)` for
  `count <= 100`, so the wall-clock bound is “100 × 1 ms plus re-toggle overhead”;
  the comment “100msec” is consistent but `mdelay(1)` is a *minimum*.
- A timeout triggers `bbd_mcu_reset(true)` on **every** burst, which (see Task C)
  is host-side only.

### 1.2 There is no ROM-phase path in the live kernel

`bcm_gps_regs.c:46` `bcm477x_rpc_get_version()` is the only function that sends the
ROM autobaud (`0x80` bytes). Confirm zero callers:

```
$ grep -rn "bcm477x_rpc_get_version" <tree>
bcm_gps_regs.c:46:  definition
bcm_gps_spi.h:      prototype
(no call sites)
```

It is dead code. Therefore the kernel never performs ROM identification itself;
the ROM exchange can only be driven by userspace over `/dev/ttyBCM` — and every
such write is gated by §1.1.

### 1.3 The MCU's own reported state is “not running an application”

Live read-only, this mission: `[SSP] debug_work_func ... GPS: false`,
`sensor_state=0x3feff`, `mcu_test=NG,NG,NG`, `mcu_name=BCM47752KUB1G`.

`mcu_name` is a probe-time identity (controller part), not proof that firmware is
loaded. The kernel's `initialize_mcu()` handshake (the `MSG2SSP_*` request/response
exchange in `ssp_dev.c`) is **not** the same thing as `bcm477x_hello()`: the
kernel log shows hello attempts and resets but no completed SSP initialization.

## 2. Handshake readiness vs ROM-autobaud readiness — the distinction

| Question | Answer in source | Status |
|---|---|---|
| Does MCU_RESP HIGH prove the boot-ROM is listening on SSI? | No source states this. | **UNPROVEN / contradicted by live evidence** |
| Does MCU_RESP HIGH prove the application firmware runs? | No. It precedes any firmware download. | **UNPROVEN** |
| Is GPIO168 a “ROM ready” line? | DE has only “ssp-mcu-resp” (`of_get_named_gpio`, `:1172`); no semantics documented. | **UNKNOWN** |
| Does the kernel send anything before hello succeeds? | No. `:896` returns first. | **PROVEN** |
| Is ROM access possible without the GNSS domain powered? | Not asserted anywhere; `GPS_PWR_EN` is only `gpio_direction_output(…,0)` at probe (`:1218`). | **UNKNOWN** |
| Settle time rail→ROM-autobaud | Absent from kernel, patches, and lhd analysis. | **MISSING EVIDENCE** |

Live observation from the previous mission is decisive against treating the
handshake as ready: in `SSP-05_16-GNSS-POWER-TIMELINE.md §1` the kernel logged
`pin_MCU_REQ:0 pin_MCU_RESP:1` together — i.e. **MCU_RESP was high while MCU_REQ
was low**, and the GNSS domain was powered for ~24 s. A line that is already HIGH
before the host drives MCU_REQ cannot be a “wake acknowledgement” in the
acknowledge-within-100 ms sense; it is at best a level signal with unknown meaning.
`bcm477x_hello()` returns success on that HIGH, yet the system did **not** become
GPS-ready (`GPS: false`, `ESW` path never validated). The handshake therefore
**did not discriminate** ready from not-ready on this hardware.

## 3. What `nuxel_bbd_flash --flash` actually does about readiness

Read of `tools/s10plus/ssp-native/nuxel_bbd_flash.c`:

- `:924` opens `/dev/ttyBCM`, which arms the IRQ/workqueue — the *kernel* then runs
  hello on the first write.
- `:937` writes `SSI:PassThru=1`.
- `rom_identity_probe()` `:836-880`: attempts 32 × `0x80`, then **`usleep(20 000)`**
  (`:852`), drains 50 ms, then sends GetVersion (id 0) with a 2500 ms reliable
  window; if no reply, repeats once with 36 × `0x80`.
- The 20 ms is **not** derived from the rail→ROM settle; it is the gap between
  autobaud bytes and GetVersion. It must not be presented as a power-settle delay.
- `fire_rpc()` for StartScratch/ServiceStart (`:1024`, `:1034`) uses 40 ms/100 ms
  recovered from lhd encoders (source-proven, but they are *post*-ROM delays).

So the downloader's readiness story is: “hello gate (kernel) + bounded blind
autobaud + 2500 ms reply window”. That is a **bounded attempt with a definitive
failure signal** (exit 3 `ROM_HANDSHAKE_TIMEOUT`), not a guaranteed-ready start.

**This is acceptable as a *failure-detection* mechanism. It is not a safety
guarantee** that no bytes are sprayed into a non-listening ROM, and it gives no
information about whether the ROM is “still booting”.

## 4. Autobaud count: 32 vs 36 is unresolved on hardware

- Kernel vendor helper (`bcm_gps_regs.c`, dead code): 32 × `0x80`.
- Matched stock lhd disassembly (VA 0xdfe4, hash-bound): 36 × `0x80`.
- Neither has been observed accepted or rejected on this die.

The downloader tries 32 first, then 36, each in its own bounded attempt. Because
the ROM UART auto-baud algorithm learns from the byte stream, sending a second
prefix after an unknown first sequence can be harmless *or* can move the ROM's
learned rate; this is **not** established either way. It does not create a
physical hazard (bytes only, no rail/reset), but it does mean a “single attempt”
is actually two prefix attempts.

## 5. Answer to the mission question

> Does the documented MCU_REQ/MCU_RESP handshake provide a defensible readiness
> condition for the subsequent autobaud operation?

**No.** It is a defensible *ordering* gate (nothing is sent before hello returns
true) and a defensible *abort* gate (hello failure is treated as failure), but it
is **not** a readiness condition, because:

1. its success predicate is a single unqualified GPIO HIGH;
2. the same HIGH was observed before the host drove MCU_REQ, with the system still
   not GPS-ready;
3. the kernel re-runs it per burst, so one success does not persist;
4. no source ties it to the boot-ROM listening state or to a settle bound.

Using it as “readiness” would be an unverified assumption presented as a safety
guarantee, which the mandate forbids.

## 6. What a physical trial can still legitimately do

Because there is no readiness guarantee, a trial can only be framed as:

- **bounded, single-shot, supervised observation** of whether this specific
  hardware accepts autobaud and answers GetVersion;
- with **definitive failure exits** and a hard host-side termination/restore.

It cannot be framed as “we waited until ready, so bytes are safe”. The residual
risk statement in the authorization doc must carry exactly that wording.

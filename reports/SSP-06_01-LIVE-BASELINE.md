# SSP-06_01 — Live Baseline (read-only, independently re-collected)

**Date:** 2026-11-23 (Europe/Amsterdam)
**Agent:** Nuxel Stage 06_01 (Master 06 Unblock)
**Device:** SM-G975F (beyond2lte), serial R58M75KDB2X
**Transport:** SSH nuxel@10.11.12.99
**Kernel:** `4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT`

## 0. Verdict — device HEALTHY, MCU still offline (firmware-not-downloaded)

All previously-established gates re-verified live and read-only. No hardware
state was modified during this mission. The MCU remains in its post-probe,
firmware-not-downloaded state, exactly as reported by Stage 06_00.

## 1. Live baseline capture (this mission, read-only)

| Item | Live value | Prior report | Match |
|---|---|---|---|
| Kernel | `4.14.253-gf7194c1d15ed-dirty` | same | ✅ |
| Hub diag | `mcu_probe=1 shutdown=1 resetting=1 sensor_state=0x3feff enable=0x0 shub_irq=443` | same | ✅ |
| MCU name | `BCM47752KUB1G` | same | ✅ |
| MCU rev | `BR0121080900,BR010` | same | ✅ |
| MCU test | `NG,NG,NG` | same | ✅ |
| Sensor enable | `0` | `0x0` | ✅ |
| GPS_PWR_EN (gpio145) | `0` (LOW) | `0` | ✅ |
| vdd_mcu_1p8 | `enabled`, `num_users=0` | same | ✅ |
| systemd | `running` | `running` | ✅ |
| nuxel-gnss-lhd.service | `enabled` / `inactive(dead)` | same | ✅ |
| nuxel-ssp-bridge.service | `masked` | `masked` | ✅ |

The baseline is healthy and unchanged. `mcu_probe=1` (MCU probed but no
firmware downloaded) is the expected clean state — this is NOT a fault; it is
precisely the state that a firmware-download trial is meant to transition the
MCU out of.

## 2. New finding surfaced this mission (source-proven, actionable)

### 2.1 The deployed GNSS service binary is STALE and unsafe

The repository HEAD (`cs/ssp`, commit `4175b949`, 2026-11-17) **already contains**
a hardened `nuxel_lhd.py` whose `run_session()` refuses initialization
(`INITIALIZATION_PROTOCOL_UNVERIFIED`) *before* any power/device access:

- repo HEAD `services/nuxel-gnss/src/nuxel_lhd.py` — sha256 `aeed416dd3d1bfb6e2b3c3a28cb2d1e9c425323ab618bf314903161b01540cd1`
- has `INITIALIZATION_PROTOCOL_UNVERIFIED` refusal (1 occurrence), no `set_power(True)`.

The binary **deployed on the device** is an older revision (file dated Nov 13):

- deployed `/usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py` — sha256 `6d90a2c0106fbceb333c5d0da40293a6a0258c42cd54df82f2d5653cd377a1ca`
- line 300: `pooled = self.power.set_power(True)` → **asserts GPS_PWR_EN=1 (GNSS RF domain)**
- line 330: `c2 = self.write_control(ctl.ESW_CTRL_READY)` → **writes `ESW:READY` readiness**
- line 328: writes `SSI:PassThru=1` (patch begin)

### 2.2 Why this matters

The journal confirms the deployed binary ran at EVERY boot and did both:

```
state=TRANSPORT_READY present=True power={'success': True, 'enabled': True}
  handshake={'ok': False, 'gps': False, ...}
  error=transport/handshake boundary reached ...
```

Two violations of the Stage 06 non-negotiable rules:

1. **RF energization without owner authorization.** `GPS_PWR_EN=1` energizes the
   GNSS *radio* domain (not just logic). This was done at every boot without the
   owner's explicit RF-policy grant. (The prior reports acknowledged the *need*
   for this grant but did not notice the deployed service was already performing
   the assertion.)

2. **Synthesized readiness.** `ESW:READY` ("firmware-up notify") is written
   despite no firmware having been downloaded and no MCU identity having been
   confirmed. This is precisely the "manufactured success evidence" the mandate
   prohibits.

### 2.3 Resolution status

- **Root cause:** a stale deployment; the corrected service logic already exists
  in the repository HEAD (`4175b949`).
- **Safely resolvable offline:** yes — the fix is already authored and committed.
  It requires only deploying the hardened binary (or masking the service until
  the physical trial is authorized).
- **Action taken this mission:** NONE performed on the device (the preservation
  rules require the owner to authorize *any* change to the running service;
  deployment/masking of the boot-time GNSS service is a userspace change that is
  reversible, but it still changes the boot-time behavior and is therefore left
  as an explicit, owner-approved action). Documented rather than auto-applied.

## 3. Baseline integrity

No partition, GPIO, regulator, or BOOT image was written during this mission.
Evidence preserved at `evidence/pwnage-ssp-06_01/live-baseline.txt` and
`evidence/pwnage-ssp-06_01/deployed-lhd-revision.txt`.

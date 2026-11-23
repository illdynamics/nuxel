# SSP-06_01 — GNSS Service Remediation (Task A)

**Date:** 2026-11-23 (Europe/Amsterdam)
**Agent:** Nuxel Stage 06_01 (final unblock)
**Device:** SM-G975F `beyond2lte`, serial `R58M75KDB2X`, SSH `nuxel@10.11.12.99`
**Prior commit:** `6ac11293` (finding `SSP-06_01-NF-001`, nothing applied on device)
**Scope:** userspace only. No MCU power, no firmware start, no flash, no kernel/DT/DTBO.

## 0. Verdict

`SERVICE_OWNERSHIP = REMEDIATED` — the stale boot-time GNSS service is **disabled**
and now **doubly gated** (fail-closed code + systemd condition). The hardened
repository implementation is deployed, hash-identical to repo HEAD, with a
hash-verified rollback directory on the device.

| Item | Before (commit 6ac11293) | After (this mission) |
|---|---|---|
| Deployed `nuxel_lhd.py` | `6d90a2c0…` (stale, Nov 13) | `aeed416d…` (repo HEAD, hardened) |
| Deployed `nuxel_bbd_tl.py` | `7af7cee8…` (stale) | `085096a9…` (repo HEAD) |
| Deployed `nuxel_control.py` | `72679d2e…` | `72679d2e…` (unchanged; already current) |
| Unit enabled at boot | **enabled** (wants-link present) | **disabled** (wants-link removed) + drop-in condition |
| Fails closed without authorization | no | **yes**, proven live (0 hardware calls) |
| `GPS_PWR_EN` at boot | written 1 for ~24 s by stale code | never written (gpio145 stays 0) |
| `ESW:READY` at boot | written every boot | never written (code path unreachable) |

## 1. Verification of deployed code vs repository

Independently re-hashed this mission (repo and device):

| File | Repo `services/nuxel-gnss/src` | Deployed `/usr/lib/nuxel/nuxel-gnss` |
|---|---|---|
| `nuxel_lhd.py` | `aeed416dd3d1bfb6e2b3c3a28cb2d1e9c425323ab618bf314903161b01540cd1` | same (after deploy) |
| `nuxel_bbd_tl.py` | `085096a99ebeb8de4feb9b2ab2ed5257927aa353ae7533cd2e15bc57997cd20d` | same (after deploy) |
| `nuxel_control.py` | `72679d2e9b332555854ce6e04cb2e1456528a3015c61729e05cba3588bf3f00f` | same (was already) |

- The pre-deployment stale `nuxel_lhd.py` was byte-identical to
  `git show a654d754:services/nuxel-gnss/src/nuxel_lhd.py` (sha256 `6d90a2c0…`),
  i.e. an artifact of the v0.8.5 packaging, **not** an unknown third revision.
- Neither the binary nor the unit is owned by any RPM (`rpm -qf` → “not owned by
  any package”); deployment was by file copy, which is why the hardening was never
  picked up. This is a **packaging gap**, not a source gap.

### 1.1 What the stale code did (source-proven from the deployed file)

```python
initial_rail = self.power.read()
lease = self.power.acquire()
pooled = self.power.set_power(True)          # line 300: GPS_PWR_EN=1 (GNSS RF domain)
...
c1 = self.write_control(ctl.BBD_CTRL_SSI_PATCH_BEGIN)   # SSI:PassThru=1
c2 = self.write_control(ctl.ESW_CTRL_READY)  # line 330: synthesized readiness
```

The journal confirms it executed at **every** boot (agent re-verified boots
`-1`, `-2`, `-3`, `-4`, each with exactly one `bbd_control : ESW:READY`).

### 1.2 Why the repository version is authoritative

(a) It is the only version under version control with an explicit, tested
fail-closed contract; (b) its commit `4175b949` carries the offline regression
`test_lhd_protocol_gate.py` that asserts **no** device/power call happens; (c) the
stale file corresponds to an *older* commit (`a654d754`), so it is provably
superseded. Repo HEAD wins.

## 2. Authoritative version and compatibility with the installed system

Deployed source runs on the installed `/usr/bin/python3` = **3.14.7**, syntax
compiles (`py_compile`), and imports only stdlib + the two sibling modules. No
kernel, ABI or node-name change was required: node names, rail path and control
strings are unchanged from the working installation.

## 3. Change made (exactly, and nothing else)

1. Created rollback bucket `/var/lib/nuxel/ssp-06_01/rollback/` containing
   verbatim copies + `SHA256SUMS` of the three original `.py` files and the unit.
2. Staged repo HEAD sources under `/var/lib/nuxel/ssp-06_01/staging/`, hashed them
   on-device, ran the fail-closed self-test there (see §4), then installed them by
   same-directory `install` + atomic `mv` as `root:root 0755`.
3. Removed the stale `__pycache__` (owner `501:games`, mode 755) so no old bytecode
   can be imported; Python regenerates a root-owned cache on next run.
4. `systemctl stop` + `systemctl disable nuxel-gnss-lhd.service`
   (removed `/etc/systemd/system/multi-user.target.wants/nuxel-gnss-lhd.service`).
5. Added drop-in
   `/etc/systemd/system/nuxel-gnss-lhd.service.d/90-nuxel-06_01-deny-start.conf`
   with `ConditionPathExists=/run/nuxel/ssp-06_01/gnss-owner-authorized`; the
   authorization file does **not** exist, so systemd skips the unit even if someone
   re-enables it or a stale copy of the old binary reappears.
6. `systemctl daemon-reload`.

`systemctl mask` was attempted first and refused because an `/etc` unit exists;
the disable+condition combination is the correct equivalent for this layout.

## 4. Fail-closed proof (live, on the deployed path)

| Check | Result |
|---|---|
| `nuxel_lhd.py --session --json` (staged, on device) | `blocker=INITIALIZATION_PROTOCOL_UNVERIFIED`, exit `2`, `power=None` |
| `run_session()` with stubbed hardware methods + power spy | `hardware_calls=[]`, `power_used=false` |
| `systemctl start` with no authorization file | `skipped, unmet condition check`, `ActiveState=inactive`, `GPS_PWR_EN=0` |
| `systemctl start` **with** temporary authorization file | ran only up to the refusal: `state=FIRMWARE_UNVERIFIED present=None power=None`, exit 2; `GPS_PWR_EN=0` |
| `ExecMainCode` (unit journal, new runs) | `0`, no hardware access logged |

The second row is the crucial one: even if an operator (or a future prompt) removes
the systemd gate, the code itself refuses before any power/device access.

## 5. Service ownership and exclusivity (live)

| Owner candidate | State |
|---|---|
| `nuxel-gnss-lhd.service` | disabled, inactive, condition-unmet |
| `nuxel-ssp-bridge.service` | masked, inactive |
| `fuser /dev/ttyBCM /dev/bbd_control /dev/bbd_sensor` | no holder |
| `nuxel-http-bridge` GNSS API | no rail writes at boot; rail needs an explicit lease/API call and no location policy file exists |
| `nuxel-orientationd` / accel-gyro path | untouched; no MCU traffic |

`systemctl list-dependencies --reverse nuxel-gnss-lhd.service` → no dependants.
`systemctl --failed` → 0 units.

## 6. Preserved configuration for later restoration

- `/etc/nuxel/gnss/gnss.json` (sha256 `f402c54e103ffd0162969e76d8691f24a3ecd100e47cbb911ae1ddf909cab043`) and `/etc/nuxel/gnss/README.md` untouched (mtime unchanged).
- Bind `spi17.0 -> "brcm gps spi"` re-verified after deployment.
- Firmware patch source `/dev/bbd_patch`, driver binding
  `spi17.0 -> brcm gps spi`, and all device nodes untouched.
- Original unit file `/etc/systemd/system/nuxel-gnss-lhd.service` left in place
  (hash `eb3455db…`, identical to repo); only its enablement and a drop-in changed.
- Rollback bucket hash inventory reproduced in
  `evidence/pwnage-ssp-06_01/post-hardening-live.txt`.

## 7. Rollback (exact, userspace-only)

See `reports/SSP-06_01-GNSS-SERVICE-ROLLBACK.md`. Rollback restores the *stale*
files by explicit choice only; it is documented for completeness, not recommended
while no owner RF authorization exists.

## 8. Explicitly NOT done

No `vdd_mcu_1p8` / regulator transition, no `GPS_PWR_EN` assertion, no MCU_REQ
assertion, no `/dev/ttyBCM` open by the service, no firmware write, no
`ESW:READY`, no BOOT/DTB/DTBO/recovery write, no reboot.

## 9. Final live verification (post-change snapshot)

Captured at 2026-11-23T02:10:43+01:00 in
`evidence/pwnage-ssp-06_01/final-verification.txt`:

| Check | Live result |
|---|---|
| Kernel | `4.14.253-gf7194c1d15ed-dirty` |
| `nuxel-gnss-lhd.service` | `disabled`, `inactive`, `ConditionResult=no`, wants-link absent |
| Authorization file | absent (`AUTHORIZED_FILE_ABSENT`) |
| Deployed hashes | `aeed416d…` / `085096a9…` / `72679d2e…` (exact) |
| Module syntax under Python 3.14.7 | AST parse OK |
| `GPS_PWR_EN` (gpio145) | `out lo`, value `0` |
| `MCU_REQ` (gpio167) | `out lo` |
| `MCU_RESP` (gpio168) | `in hi` |
| `vdd_mcu_1p8` | `use 0`, 1800 mV, enabled — unchanged |
| `/dev/ttyBCM`, `/dev/bbd_control`, `/dev/bbd_sensor` holders | none |
| `nuxel-ssp-bridge.service` | masked, inactive |
| `ESW:READY` this boot | **1**, at `00:46:31` — the pre-remediation boot; **none after 02:04** |
| Failed units | 0 |
| Rollback bucket `sha256sum -c` | all `OK` |
| GNSS config | `f402c54e…` unchanged |
| Driver binding | `spi17.0 -> /sys/bus/spi/drivers/brcm gps spi` |

Caveat on the regulator line: `/sys/kernel/debug/regulator/regulator_summary`
column 2 is the regulator **use count** (`0`), shown under the `use` header; it is
labeled `num_users` in older live baselines. It is unchanged (`0`) and was not
written by this mission.

# Area 17/18 — Power menu, battery modes and charging (S10+ / beyond2lte)

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED).
Owner action required? **Yes** — battery drain, real charging behaviour and the
feel of a profile under load cannot be observed without the handset, a charger
and time.

**Device truth used by this document.** Samsung Galaxy S10+ (SM-G975F, Exynos
9820), 4100 mAh, 15 W wired / 12–15 W wireless. The fuel-gauge and charger nodes
are **not** assumed: `nuxel-power-diag.sh` enumerates `/sys/class/power_supply/*`
and reports the real device name. `lpcharge`/charger-mode
(`androidboot.mode=charger`) is treated as a **distinct boot mode** — see §6.

---

## 1. Feature

Battery/power modes (area 18) and the power menu (area 17):

* `configs/nuxel/power/power.json` — boot-mode detection, fuel-gauge field map,
  three profiles (**Adaptive / Balanced / Performance**) mapped to a real
  cpufreq governor and a cgroup CPU weight, and the charge-control policy
  (`allow_writes: false`).
* `configs/nuxel/power/power-menu.json` — the long-press POWER menu table:
  **Lock screen, Restart, Power off, Recovery, Download Mode**, each with its
  trigger gate.
* `tools/s10plus/a33/nuxel-power-diag.sh` — `status`, `profiles`, `mode`,
  `apply-persisted`, `menu`, `report`, `selftest`.
* `configs/nuxel/power/nuxel-power-mode.service` — re-applies the persisted
  profile once at boot (evidence-only; never touches the reboot gate).
* `pwa/nuxel-apps/settings/power-menu.js` — the graphical Settings power surface
  reading the same menu document (one menu, not two).

## 2. Why this matters

The A32 baseline recorded that a long POWER press maps to `power-menu`, which was
**logged and refused** because no power menu existed. Area 17 closes that gap
without inventing a shutdown path. Area 18 gives the owner a real, persisted
choice of runtime profile — and the repository must not claim a longer runtime
it has not measured, which is why the profiles are a *control surface* whose
observed governor/cgroup values are what is reported.

## 3. Preparation

1. Handset powered on and booted into Nuxel (a normal boot, not charger-mode —
   check the boot-mode line first, §7).
2. Console/SSH or the on-device terminal, so `nuxel-power-diag.sh` can run.
3. A charger (wired or Qi) for the charging part of the test.
4. Take the zero-cost snapshot first — it decides whether the gauge is even
   bound before any behavioural claim is attempted:

   ```sh
   nuxel-power-diag.sh status            # boot mode, gauge, charging, profile
   nuxel-power-diag.sh status --json     # machine-readable
   nuxel-power-diag.sh menu              # the menu table + the refusal reason per entry
   ```

   If the verdict is `BLOCKED_KERNEL` (no gauge bound) or `DEGRADED_CHARGER_MODE`
   (LPCHARGE boot), **stop**: the correct next action is the bring-up/reboot path
   in `configs/nuxel/power/README.md`, not a retry loop.

## 4. Exact action

### 4a — battery read

1. `nuxel-power-diag.sh status` → record `gauge device`, `capacity`, `status`,
   `voltage_now`, `temp`, `health`, and the `state`.
2. Cross-check the truth in two places (a single node is not evidence):
   `cat /sys/class/power_supply/*/capacity` and the launcher status bar
   percentage; they must agree within 1 %.
3. Note the `state:` line and keep it for the report.

### 4b — profiles

1. `nuxel-power-diag.sh profiles` → read the three modes and what each changes.
2. Apply each in turn and record the REAL governor after each:
   `nuxel-power-diag.sh mode adaptive`   → `cat /sys/devices/system/cpu/cpufreq/policy0/scaling_governor`
   `nuxel-power-diag.sh mode balanced`   → same file
   `nuxel-power-diag.sh mode performance`→ same file
3. Confirm the cgroup weight follows (`cpu.weight` or `cpu.shares`, as reported).
4. Pick the profile you want to keep and leave it applied. Persistence is proven
   by an ordinary reboot returning to the same profile (`apply-persisted`), which
   is the same reboot procedure as area 5 — **do not** repeat the reboot on
   failure (no blind repeat reboots).

### 4c — charging behaviour

1. Plug in the charger; `nuxel-power-diag.sh status` must change `status` to
   `Charging` and capacity must rise over 10 minutes.
2. Unplug; `status` must return to `Discharging` within a few seconds.
3. Confirm the tool did **not** write charge-control limits:
   `charger.allow_writes=false` in `power.json`; check
   `journalctl -b | grep -i nuxel-power` for any unexpected write.

### 4d — power menu

1. Open Settings → Power (or long-press POWER) → the menu must show the five
   entries from `power-menu.json`.
2. Tap **Lock screen** → the display bridge locks and the screen turns off; a
   short POWER press returns to the launcher.
3. Tap **Restart** and **Power off** → both must be **refused** with the reason
   from the gate (owner absent). This is the expected result, not a bug.
4. Tap **Recovery** and **Download Mode** → both must be **refused** by the
   NO-FLASH invariant. `Recovery` and `Download Mode` are never triggered by any
   automated path in this mission.

## 5. Expected result

* `status` reports the real gauge device and a sane capacity/status pair, or an
  honest `BLOCKED_KERNEL`/`PARTIAL` verdict naming the layer.
* `mode <name>` changes the observed governor (and the cgroup weight where the
  kernel exposes it) and persists the choice; after an ordinary reboot the same
  profile is active.
* Charging raises capacity; unplugging returns to `Discharging`.
* The power menu shows all five entries; only **Lock screen** acts; every other
  entry is refused **with its reason**.
* No charger register, partition or block device is written at any point.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning |
|---|---|
| `state: BLOCKED_KERNEL` — no `*/capacity` node | No gauge driver bound. Kernel-side work (offline), never a guessed percentage. |
| `state: PARTIAL` — gauge dir exists, capacity unreadable | Driver bound but the gauge node is not exported; capture `dmesg | grep -i -E 'charger|fuel|gauge|max77'`. |
| `state: DEGRADED_CHARGER_MODE` | Charger-mode/LPCHARGE boot: `sec_ts` input is disabled for this boot. Remedy = **ordinary reboot**; there is no userspace workaround (`CONFIG_KEXEC` off, drivers not modular) and no kernel/flash change on this mission. |
| `mode` prints `governor=none` | No cpufreq policy for the requested profile; record it — the profile is persisted but no knob was written. |
| Charging state never changes when plugged | Report as unproven. Do **not** write charge-control nodes to "fix" it. |
| Menu missing / "reference" error | `power-menu.json` is not installed; the button FSM refuses `power-menu` loudly (A32 behaviour) — installation issue, not a code change. |
| Restart actually reboots | The reboot gate was opened by an external policy. Verify `tools/beta/rollback.sh` exists before allowing it and remember the pre/post-reboot checklist. |

## 7. Diagnostic command / log path

* `nuxel-power-diag.sh status | profiles | mode <name> | menu | report`
  (`tools/s10plus/a33/nuxel-power-diag.sh`)
* Evidence log: `/var/log/nuxel/power-diag.log`
* Boot mode: `tr ' ' '\n' < /proc/cmdline | grep androidboot.mode`;
  `dmesg | grep -i sec_bat_is_lpm_check`
* Kernel side: `dmesg | grep -i -E 'charger|fuel|gauge|max77|s2mps|bq2597'`
* Offline suite: `python3 tools/s10plus/a33/tests/hw-subsystems/test-power-diag.py`
  and `nuxel-power-diag.sh selftest` (4 fixtures: ok / no gauge / charger-mode /
  partial).

## 8. PASS / FAIL

* **PASS** — §4a–§4d all hold: a real gauge reading that agrees with the status
  bar, each profile changing the observed governor, the choice surviving an
  ordinary reboot, charging/discharging observed with a charger, and every menu
  entry behaving exactly as its gate says (Lock acts; all others refuse).
* **FAIL** — any of: no gauge node, capacity disagreeing with the status bar by
  more than 1 %, `mode` writing nothing while claiming a change, a refused entry
  acting anyway, or any write to a charger register/partition. Record the exact
  verdict string and the refusal text; the verdict names the layer, and a verdict
  is what a repair cycle needs — not a screenshot.

## Current automatic evidence (repository, this build group)

* `bash tools/s10plus/a33/nuxel-power-diag.sh selftest` → 4/4 fixtures PASS
  (`tools/s10plus/a33/tests/hw-subsystems/fixtures/power-*`).
* `python3 tools/s10plus/a33/tests/hw-subsystems/test-power-diag.py` → all checks
  PASS (verdict logic, menu/gate agreement, refusal reasons, NO-FLASHING
  invariant, Settings wiring, this fragment's field completeness).
* Verdict for the live battery/charging path: **unknown / not claimed** —
  `charging_behaviour_verified: false` is emitted in every `status --json`, and
  the profile state in `configs/nuxel/capabilities/hardware-subsystems.json`
  stays `OFFLINE_TESTED` until the owner observes the handset.
* Owner test registered as `NEEDS_OWNER_TEST` for the charging/behaviour half;
  the control surface is `OFFLINE_TESTED`.

# NUXEL BETA — SOAK AND RESOURCE / PERFORMANCE QUALITY

**briq:** `briq-09a-test-strategy-soak` · **component:** `bg-09-integration-release` (priority 8)
**Harness:** `tools/beta/soak.sh` (sampler) + `tools/beta/soak_lib.py` (evaluator, the single source of truth for the thresholds)
**Companion:** [`TEST-STRATEGY.md`](TEST-STRATEGY.md) (L1–L6) · [`../release/DEVICE-CAPABILITY-MANIFEST.md`](../release/DEVICE-CAPABILITY-MANIFEST.md)

---

## 1. What a soak can and cannot prove

A soak proves **stability over a sampled window**: the phone did not reboot, no
unit failed, the launcher stayed reachable, the framebuffer owner did not change
hands, the stack did not leak, and the resource picture stayed inside the
documented ceilings.

A soak **never** proves that untested hardware works, that audio is audible, that
the touch controller responds, or that a radio associates. Those are L5/L6
verdicts (`TEST-STRATEGY.md` §4) and they need their own evidence.

Three hard properties of the harness:

* **Bounded, always.** `--duration` defaults to the documented ceiling for the
  mode and is capped there. There is no unbounded mode, no "run until stopped",
  and no way to leave a sampler running past its deadline.
* **Inert on failure.** If the live console is unreachable the soak **exits 3 with
  terminal state `BLOCKED_EXTERNAL_RESOURCE`** and says so in the report. It never
  fabricates a sample and never claims a soak it did not run.
* **No device writes, no reboots, no service restarts.** The sampler is a
  read-only probe; evidence goes to the evidence directory and the report path
  only.

```json
{"status": "no samples", "terminal_state": "BLOCKED_EXTERNAL_RESOURCE",
 "mode": "device", "samples": 0,
 "findings": [{"id": "S0-no-samples", "severity": "fail",
               "detail": "no samples were collected: the sampler had no reachable resource"}]}
```

---

## 2. Modes and durations

| Mode | Command | Default duration | Ceiling | Verdict it can produce |
|---|---|---|---|---|
| `smoke` | `soak.sh --vm --duration 300` | 300 s (5 min) | — | `VERIFIED_IN_VM_ONLY` |
| `vm` | `soak.sh --vm` | 1800 s (30 min) | 30 min | `VERIFIED_IN_VM_ONLY` |
| `device` | `soak.sh --device` | 28800 s (8 h) | 8 h | `VERIFIED_ON_S10PLUS` on PASS |
| bounded nightly | `soak.sh --device --duration 1800` | 1800 s | 8 h | `VERIFIED_ON_S10PLUS` on PASS |
| `replay` | `soak.sh --replay FILE.ndjson` | recorded | — | `OFFLINE_TESTED` |
| `selftest` | `soak.sh --selftest` | — | — | `OFFLINE_TESTED` |

**The ≤30-minute bounded soak is the default for autonomous runs** (the mission
caps an unattended soak at 30 minutes); the 8 h run is the owner/live tier and is
registered as `X-live-soak` (external, never started by the release gate):

```bash
tools/beta/soak.sh --device --duration 1800 --interval 60 --checkpoint 300 \
    --evidence-dir docs/beta-finalization/live/soak-<stamp>/ \
    --json        docs/beta-finalization/live/soak-<stamp>/soak.json
```

`--checkpoint` prints a progress line every N seconds so a lost console is
noticed within a bounded time instead of after eight hours.

---

## 3. The probe (what is measured)

Two short output lines per sample — the live console drops long lines — merged
into one sample by `parse_sample`:

```
SOAK  uptime_s=... load1=... failed_units=... stack_rss_kb=... stack_cpu_pct=...
      fb_owner_pid=... http_code=... thermal_raw=... restarts=... boot_mode=...
SOAK2 disk_avail_kb=... swap_used_kb=... webkit_procs=... webkit_rss_kb=...
      phoc_rss_kb=... phoc_cpu_pct=... bridge_rss_kb=... bridge_cpu_pct=...
      bridge_io_kb=... anim_procs=... procs_running=... procs_total=...
      input_nodes=... touch_nodes=...
```

| Metric | Source | Purpose |
|---|---|---|
| `uptime_s` | `/proc/uptime` | a decrease means the phone restarted |
| `load1` | `/proc/loadavg` | **recorded, never gated** (Samsung vendor threads, see §6) |
| `mem_used_kb` / `mem_avail_kb` | `/proc/meminfo` | RAM pressure |
| `stack_rss_kb` / `stack_cpu_pct` | `ps` over the Nuxel stack | leak check + the gated CPU metric |
| `failed_units` | `systemctl --failed` | boot/graph health |
| `service_restarts` | `systemctl show -p NRestarts` | crash-loop detection |
| `fb_owner_pid` | `/var/lib/nuxel/fb-owner` | the single-framebuffer-owner contract (A32) |
| `http_ok` / `http_code` | `curl 127.0.0.1:8000` | launcher availability |
| `thermal_max_c` | `/sys/class/thermal/*/temp` | thermal envelope (advisory) |
| `cmdline_boot_mode` | `/proc/cmdline` | charger/LPM contamination |
| `disk_avail_kb` | `df -k /` | **storage** headroom and log growth |
| `swap_used_kb` | `/proc/meminfo` | **swap** / memory pressure |
| `webkit_procs` / `webkit_rss_kb` | `ps` over `WebKit*` | **browser subprocess count and memory** |
| `phoc_rss_kb` / `phoc_cpu_pct` | `ps` over `phoc` | **compositor rendering cost** |
| `bridge_rss_kb` / `bridge_cpu_pct` / `bridge_io_kb` | `ps` + `/proc/<pid>/io` | **framebuffer-bridge cost and commit volume** (a frozen panel writes nothing) |
| `anim_procs` | `ps` over `nuxel-anim*`/`nuxel-firstlight` | **leftover animation process** after the handoff |
| `procs_running` / `procs_total` | `/proc/loadavg` | **background scheduling** sanity |
| `input_nodes` / `touch_nodes` | `/proc/bus/input/devices` | input inventory (touch presence) |

Input **latency** is not measurable from a 60 s cadence probe: it needs per-event
timestamps, so it is measured by the touch capture harness on the device tier and
is reported there, not here. This document does not claim a latency figure.

---

## 4. Pass criteria (verbatim from `soak_lib.py` `THRESHOLDS`)

```python
min_coverage_ratio        = 0.90    # observed window / requested duration
max_sample_gap_factor     = 3.0     # a gap > 3x the interval is a console stall
max_allowed_gaps          = 1
allowed_failed_units      = 0
boot_settle_samples       = 2       # first N samples excluded from unit checks
min_http_availability     = 0.99    # launcher reachable share of samples
max_fb_owner_changes      = 0       # >0 = the framebuffer owner changed hands
max_fb_owner_changes_warn = 1
stack_cpu_mean_max_pct    = 150.0   # 1.5 of 8 cores, sustained
stack_cpu_peak_max_pct    = 300.0   # short spike ceiling (3 of 8 cores)
mem_growth_per_hour_max_pct = 2.0
mem_growth_total_max_pct  = 10.0
max_service_restarts      = 0
max_service_restarts_warn = 1
thermal_warn_c            = 75.0
thermal_fail_c            = 90.0
durations   = {"device": 28800, "vm": 1800, "smoke": 300}
sample_interval_s = 60
checkpoint_s      = 1800
```

Resource / performance quality additions (warn-first — none of these is a device
claim, and a metric the phone could not produce is reported as unproven):

```python
min_disk_avail_kb           = 262144   # 256 MiB free on /  -> FAIL below this
disk_avail_drop_warn_pct    = 20.0     # a >20% fall over the soak
swap_used_warn_kb           = 65536    # 64 MiB of swap in use
max_webkit_procs            = 8        # WebKit subprocess ceiling
max_webkit_procs_warn       = 6
max_webkit_rss_kb           = 1572864  # 1.5 GiB of browser memory
max_phoc_cpu_mean_pct       = 120.0
max_phoc_cpu_peak_pct       = 300.0
max_bridge_cpu_mean_pct     = 100.0
max_bridge_cpu_peak_pct     = 300.0
min_bridge_io_growth_kb     = 1        # the bridge must keep committing frames
max_anim_procs_after_settle = 0        # the animation must have stopped
max_procs_running_warn      = 24       # daemon-per-setting / idle-refresh sprawl
```

### The findings, and what each one means

| id | Severity | Meaning |
|---|---|---|
| `S1-coverage` | FAIL | the soak observed less than 90% of the requested duration |
| `S2-cadence` | WARN | sample gaps > 3× the interval → console/transport stall |
| `S3-no-reboot` | FAIL | `/proc/uptime` went backwards: the phone restarted |
| `S4-failed-units` | FAIL | `systemctl --failed` non-empty after the settle window |
| `S5-launcher-availability` | FAIL | launcher answered on `:8000` in < 99% of samples |
| `S6-fb-owner` | FAIL/WARN | the framebuffer owner changed hands (A32 floor: never) |
| `S7-stack-cpu` | FAIL | stack CPU above 150% mean / 300% peak |
| `S8-memory-leak` | FAIL | stack RSS grew > 2%/h or > 10% total |
| `S9-restarts` | FAIL/WARN | a stack service restarted during the soak |
| `S10-thermal` | FAIL/WARN | hottest zone above 90 °C (warn above 75 °C) |
| `S11-boot-mode` | WARN | a charger/LPM boot: the touchscreen is dead by design, so the soak is not representative |
| `S12-disk` | FAIL/WARN | free space on `/` fell below 256 MiB / fell > 20% |
| `S13-swap` | WARN | swap in use (the S10+ build configures none) |
| `S14-webkit` | WARN | WebKit subprocess count or memory above the ceiling |
| `S15-phoc` | WARN | the compositor's CPU above the ceiling |
| `S16-bridge` | WARN | the framebuffer bridge's CPU above the ceiling |
| `S16-bridge-commits` | WARN | the bridge committed nothing: the panel may be frozen |
| `S17-animation` | WARN | an animation process survived the display handoff |
| `S18-scheduling` | WARN | runnable-process count above the advisory ceiling |
| `S18-input` | INFO | input-node inventory, including touch-controller nodes |

A run with no FAIL and no WARN is `PASS`; any WARN makes it
`PASS_WITH_WARNINGS`; any FAIL makes it `FAIL`. **A `PASS` is `OFFLINE_TESTED`
for `replay`/`selftest` and `VERIFIED_ON_S10PLUS` for `device`; the mode is always
recorded in the report so the two can never be confused.**

---

## 5. Resource / performance quality — the standing audit

The mission requires the beta to stay maintainable on an eight-core SoC with
7.4 GiB of RAM, feeding a 1440×3040 panel through a userspace bridge. The
following rules are enforced by the design (and checked by the soak metrics
above):

* **No daemon-per-setting sprawl.** Settings live in files
  (`/etc/nuxel/**`) read by the processes that need them; the boot carries one
  compositor, one bridge, one launcher host and one button manager. `U-*`
  service-graph checks reject a unit that duplicates another's job, and the
  mission's independent test suite rejects contradictory managers (exactly one
  firewall backend, one session daemon, one launcher).
* **Consolidate where safe.** The status bar, quick settings and safe zones are
  one PWA surface, not three services. The `nuxelctl` CLI is the single control
  entry point rather than a helper binary per feature.
* **Lazy-start optional apps.** The launcher starts on demand; the store, maps,
  media and specialty apps are launched by the user, not at boot.
* **Bound decoder memory.** One WebKit web process family for the launcher,
  bounded by `max_webkit_procs` / `max_webkit_rss_kb`; media playback must not
  run a second full browser (the media apps are separate frontends, not tabs).
* **Keep the launcher responsive.** Launcher availability ≥ 99% of samples and
  bridge CPU below the ceiling: the UI is fed from a single writer and must never
  be starved by the background.
* **Preserve the live USB debug path.** Nothing in the stack may claim the
  USB gadget serial endpoint for itself, and no soak/deploy path may take the
  console away; the console is the only route back to a broken phone
  (`REBOOT-ROLLBACK.md`).
* **Idle drain.** No uncontrolled idle refresh: no animation process after the
  handoff (`S17`), no runnable-process runaway (`S18`), no busy bridge (`S16`).

---

## 6. The load-average note (do not "fix" this)

`load1` on this handset sits near 12 on an eight-core SoC. That is **not** the
Nuxel stack. Eleven Samsung *vendor kernel* tasks (TrustZone worker / interworld
socket, RPMB secure-storage work, REE time) are permanently in `D` state; the
finding is recorded in
`docs/s10plus-autonomous-boot-repair/BETA-FINALIZER/12-REMAINING-LIMITATIONS.md`
(A31). The harness therefore **records `load1` and never gates on it**; the gated
metric is `stack_cpu_pct`. Treating `load1` as a failure would be a false alarm,
and suppressing it would hide a real hardware/kernel characteristic.

---

## 7. Evidence

| Artefact | Path |
|---|---|
| Plan and criteria | `docs/beta-finalization/release/evidence/soak-plan.txt` |
| Harness self-proof | `docs/beta-finalization/release/evidence/soak-selftest.txt` |
| Replay of a recorded series | `docs/beta-finalization/release/evidence/soak-replay-*.txt` |
| Device soak (owner / live tier) | `docs/beta-finalization/live/soak-<stamp>/` (report `.json` + `.md` + `samples.ndjson`) |

Current status of the 8 h device soak:

**`BLOCKED_EXTERNAL_RESOURCE`** — the soak needs the live USB console (or the UTM
guest) for eight uninterrupted hours, which a repository-only run does not have.
The harness ships, passes `--selftest` and `--replay`, and reports the exact
blocked state instead of inventing a result. This is registered as `X-live-soak`
in the release gate (external tier: listed, never auto-run).

*Rollback: this briQ changes repository files only — `git revert`. No device
state is touched by any tier described here.*

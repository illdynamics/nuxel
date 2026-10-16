# Touch pipeline trace — sec_ts → IRQ → evdev → libinput → phoc → Wayland → WebKitGTK → Nuxel Home

**Area 1 of the beta finalization (highest priority).**
Repository side: **OFFLINE_TESTED**. Live side: **NEEDS_OWNER_TEST** (a finger is
required; see `docs/beta-finalization/manual-proof/01-touchscreen.md`).

Tool: `tools/s10plus/a33/nuxel-touch-trace.py`
Harness: `tools/s10plus/a33/nuxel-touch-capture.sh`
DOM probe: `tools/s10plus/a33/touch-probe.html`
Tests: `tools/s10plus/a33/tests/` (`run-touch-tests.sh` runs them all)

---

## 1. The chain, and what "delivered" means at each hop

| # | Layer | A pass here means | Evidence the tracer requires |
|---|---|---|---|
| 1 | `sec_ts` driver binding | the kernel registered `sec_touchscreen` and the i2c client `4-0048` is bound | `dmesg`/ram-console registration line, `/sys/bus/i2c/devices/4-0048`, `sec_ts_init` return path |
| 2 | IRQ delivery | the `sec_ts` line in `/proc/interrupts` actually counted up while the panel was exercised | two `/proc/interrupts` snapshots ≥2 s apart, delta > 0 |
| 3 | evdev node production | a **capability-selected** node exists with `INPUT_PROP_DIRECT` + `ABS_MT_POSITION_X/Y` and a non-degenerate range | `EVIOCGNAME`, `EVIOCGPROP`, `EVIOCGBIT(EV_ABS/EV_KEY)`, `EVIOCGABS`; raw events decode into a point |
| 4 | libinput acceptance | the shim handed the node to libinput and libinput returned a device | `/run/nuxel-libinput-path.state` lines with `PATH_ADD … accepted=1` |
| 5 | phoc input fds | the compositor holds the input node open | `/proc/<nuxel-wayland MainPID>/fd` targets under `/dev/input/` |
| 6 | Wayland seat / focus | the compositor produced touch events for the seat (`wl_touch`) | bounded `WAYLAND_DEBUG`/journal window, or a launcher DOM line that could only exist from a Wayland touch event |
| 7 | WebKitGTK DOM | `touchstart`/`touchmove`/`touchend` reached the document **with coordinates** | `/run/nuxel-touch-dom.log` (instrumented page) or `NUXEL_INPUT` lines in `/run/nuxel-home.state` |

Each layer prints exactly one machine-readable verdict:

```
LAYER=<n> NAME=<name> STATE=<ok|drop|blocked> EVIDENCE=<path> DETAIL=<one line>
```

* `ok` — this layer provably carried (or is ready to carry) a real event.
* `drop` — the layer exists and did **not** deliver. **The pipeline stops here.**
* `blocked` — could not be evaluated (no capture, precondition absent). **This is
  not a pass.** A missing capture is never reported as `ok`.

Then one summary:

```
FIRST_FAIL_LAYER=<n|none>
FIRST_DROP_LAYER=<n|none>
VERDICT=PIPELINE_DELIVERED | PIPELINE_STOPPED_AT_LAYER=<n> NAME=<name> STATE=<drop|blocked>
GATE=pass|fail {...machine gate JSON...}
```

## 2. Bounded by construction (the live console must never hang)

| Bound | Default | Enforced by |
|---|---|---|
| wall-clock | `--seconds 20` (1..900) | `signal.alarm(--seconds + 15)`; on expiry the bundle is flushed and the verdict for what was collected is printed |
| decoded events | `--max-events 2000` | the read loop checks the cap every iteration |
| raw bytes | `--max-bytes 262144` | same |
| every subprocess | 4–8 s | `run_cmd()` timeout |
| DOM collector | 200 requests, daemon thread | it can never keep the process alive |
| the harness | `timeout -k 5 <seconds+25>` | `nuxel-touch-capture.sh` |

Measured on a workstation (no phone): a `--seconds 2 --dry-run` session returns in
**2.1 s**, printing all seven layer verdicts. A zero or out-of-range budget is
**refused** rather than run unbounded.

## 3. No `/dev/input/eventN` anywhere (invariant, enforced)

A fixed node number is how earlier cycles measured the wrong device: node numbers
depend on probe order and change between boots and between boot modes. So:

* the **tracer** lists `/dev/input/`, opens every candidate and decides by
  capability (`EVIOCGPROP` → `INPUT_PROP_DIRECT`, `EVIOCGBIT` → `ABS_MT_POSITION_X/Y`
  + `BTN_TOUCH`, `EVIOCGABS` → non-degenerate range);
* the **shim** does the same for its own device list;
* the **harness** re-uses the tracer's selection.

`tools/s10plus/a33/tests/test-no-eventn-literal.py` greps every file in this
pipeline (code, comments, configs and docs alike) for `/dev/input/event<digit>`
and the bare `event<digit>` token and fails the build if one appears. Node names
appear only where they are *data under test* (`tests/fixtures/**`, the fixture
driver that asserts the selector's own output) and those files are named
explicitly in the gate so the exclusion stays reviewable.

## 4. The measured state (A32 baseline, and what this group adds)

Measured on a **normal** boot by the previous cycle and recorded in
`docs/s10plus-autonomous-boot-repair/BETA-HARDWARE-FINALIZER/`:

| Layer | A32 measurement | State |
|---|---|---|
| 1 | `[sec_input] sec_ts_init`; `input: sec_touchscreen as /devices/platform/104b0000.hsi2c/i2c-4/4-0048/input/input2`; `sec_ts 4-0048: ic_status_show: … lpm:0` | present |
| 2 | `/proc/interrupts`: `431: … Level sec_ts` | present |
| 3 | node present, `B: PROP=2` (= `INPUT_PROP_DIRECT`), `B: EV=2b`, `B: ABS=4263800000000003` (MT axes) | present |
| 4 | shim log: `PATH_ADD node=<capability-selected> name='sec_touchscreen' accepted=1`, `direct_devices_seen=2 added=2 db_seeded=2` | present |
| 5 | the compositor (MainPID of `nuxel-wayland.service`) holds 2 input-node fds | present |
| 6 | seat `seat0` assigned by the shim (`PATH_ASSIGN_SEAT … added=2`); output `HEADLESS-1` 720x1520 scale 2 | present |
| 7 | `nuxel-pwa-host` installs an observing user script that relays every `touchstart/touchmove/touchend/pointerdown/pointerup/click` **with coordinates** into `/run/nuxel-home.state` | instrumented, **awaiting a finger** |

This group adds the tooling that makes layer 7 *measurable and gradable*:

* `tools/s10plus/a33/touch-probe.html` — a self-contained page that logs
  `touchstart x=<int> y=<int> …` in the exact machine form the analyzer greps for and
  POSTs each line (best effort, `sendBeacon` then `XHR`) to the bounded collector;
* the tracer's **bounded local collector** (`127.0.0.1:8099`, daemon thread) which
  writes `/run/nuxel-touch-dom.log` inside the evidence bundle;
* `--stage-probe`, which copies the page into the launcher docroot and prints the one
  step a script cannot do.

**Not claimed:** touch navigation, coordinate scaling, orientation, tap accuracy,
swipe behaviour, palm rejection or ghost touches. Those need the owner's finger and
are listed in the manual-proof fragment.

## 5. The one boot flag that invalidates everything: charger/LPM mode

If the phone powered up from off with a charger attached, S-Boot passes
`androidboot.mode=charger`, `sec_bat_is_lpm_check()` sets `lpcharge=1`, and
`sec_ts_init()` returns `-ENODEV` before `i2c_add_driver()`. **No touch device exists
on that boot**, and every layer above 1 is empty by construction. Layer 1 reports
this as `blocked` with the evidence it came from, and the tracer never pretends the
capture was empty because "touch is broken".

Full analysis, evidence, the userspace mitigation (`nuxel-bootmode-guard.py`) and the
not-deployed kernel patch: `docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md`.

## 6. Two evidence-discipline bugs found and fixed by writing the tests

Both were found by grading real archived captures, and both are the kind of bug that
manufactures a pass:

1. **Kernel-timestamped lines were discarded.** The "is this a shell command listing?"
   regex began with an unescaped `#`. Because it was compiled with `re.X` (verbose),
   that `#` started a *comment*: every alternative on that line (`echo`, `cat`,
   `grep`, `ls`, `tr`, …) was silently dead, and a leading `[` was also an
   alternative, so a dmesg line captured with its own timestamp
   (`[    1.654761] input: sec_touchscreen as …`) was ranked as a shell command and
   dropped. Real kernel output was being thrown away.
2. **A checklist line was graded as libinput evidence.** `.scratch/beta/final-verify.txt`
   contains the *command* `grep -a 'accepted=1' /run/nuxel-libinput-path.state`, not
   state-file output. Layer 4 used the un-graded lookup, so it reported
   `STATE=ok` — i.e. "libinput accepted the panel" — on a boot where layer 3 said no
   panel node existed. It now uses the quality-graded lookup and reports `blocked`.

The pattern list is now built from an explicit token list (no `re.X` pitfalls) and is
**self-tested at import**: eight lines with the expected classification, including a
real state-file line (not a command) and two kernel-printk forms. A regression test
(`checklist-not-evidence` / `real-state-file` in `tests/test-touch-trace.py`) locks
both behaviours.

## 7. Grading real archived captures (the OFFLINE_TESTED acceptance)

`--analyze` accepts a bundle **or any archived capture directory**, searching the tree
for evidence patterns instead of trusting a fixed file name, and ranking real device
output above prose. Measured results (full output in
`docs/beta-finalization/touch/OFFLINE-TEST-RESULTS.md`):

| Capture | L1 | L2 | L3 | L4 | L5 | L6 | L7 | FIRST_FAIL |
|---|---|---|---|---|---|---|---|---|
| `…A17-live-run` | blocked | blocked | blocked | blocked | blocked | blocked | blocked | 1 |
| `…A18-live-run` | blocked | blocked | blocked | blocked | blocked | blocked | blocked | 1 |
| `…A19-live-run` | blocked | blocked | blocked | blocked | blocked | blocked | blocked | 1 |
| `…A20-live-run` | **ok** | blocked | **ok** | blocked | blocked | blocked | blocked | 2 |
| `…A21-live-run` | **ok** | blocked | **ok** | blocked | blocked | blocked | blocked | 2 |
| `.scratch/beta` | blocked | blocked | blocked | blocked | blocked | blocked | blocked | 1 |

Two of the six captures (`A20`, `A21`) contain real device output: the kernel's own
`input: sec_touchscreen as …` registration line, so layers 1 and 3 are `ok` and the
pipeline is named as stopping at layer 2 — those captures simply never contained a
`/proc/interrupts` delta, and nothing above layer 3 was captured at all, so those
layers are `blocked` (never `ok`). The A17–A19 captures contain no readable
`sec_ts` evidence in this form and are honestly all-`blocked`. `.scratch/beta` is a
set of *shell command listings*, not device output, and is reported as having no
usable evidence at all — which is exactly what turned up bugs 1 and 2 above.

Those captures are historical: they predate the arm-on-open fix and the DOM probe, so
they cannot show layers 2 and 4–7. They are used as *grading fixtures* — proof that the
analyzer classifies real handset output correctly — and never as proof of touch.

## 8. How to run it

```sh
# on the phone (bounded, read-only, no writes outside the bundle)
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --live --seconds 20 --out /var/lib/nuxel/touch-trace

# the owner test: bounded, self-terminating, takes an owner-test lock
nuxel-touch-capture.sh --seconds 90

# stage the DOM page and print the manual step
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --stage-probe

# grade anything, offline
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --analyze /var/lib/nuxel/touch-trace
```

Gate for a PASS (and nothing less): ≥1 `BTN_TOUCH` down **and** up, `ABS_MT`
coordinates inside the device's own reported range, **and** those coordinates observed
at layer 7. `nuxel-touch-capture.sh` prints `CAPTURE_GATE=PASS` only then — and even
then the item stays `NEEDS_OWNER_TEST` until a human confirms the UI responded.

## 9. Terminal verdicts for this area

| Item | Verdict |
|---|---|
| tracer, harness, DOM probe, shim, tests | **OFFLINE_TESTED** |
| console/LPM boot mitigation | **OFFLINE_TESTED** (effect only observable after a live normal reboot) |
| permanent kernel-level LPM fix | **BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED** |
| physical finger on the glass, end to end | **NEEDS_OWNER_TEST** |

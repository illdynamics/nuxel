# Area 1 — Touchscreen: finger on the glass, end to end

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED).
Owner action required? **Yes** — only a human finger can produce a real touch
contact, and only a human can confirm that the UI *responded* to it. This item must
**never** be auto-promoted to `VERIFIED_ON_S10PLUS` from a script run.

Bounded capture harness: `tools/s10plus/a33/nuxel-touch-capture.sh`
Layer grader: `tools/s10plus/a33/nuxel-touch-trace.py`
DOM probe: `tools/s10plus/a33/touch-probe.html`
Offline evidence: `docs/beta-finalization/touch/OFFLINE-TEST-RESULTS.md`
Live evidence from this cycle: `docs/beta-finalization/live/evidence/touch-*-p0probe-live-run/`

---

## 0. Current measured state — read this before planning the test

A **bounded, read-only** probe of the running phone over the USB CDC-ACM console was
taken this cycle (transcript and grading:
`docs/beta-finalization/live/evidence/touch-20261016T193756+0200-cycl001-p0probe-live-run/`).
It found the handset **booted in charger / low-power mode**:

| Probe | Result on the device right now |
|---|---|
| `/proc/cmdline` | `androidboot.mode=charger`, `charging_mode=0x3030` |
| `dmesg` | `[    1.638064] [sec_input] sec_ts_init: Do not load driver due to : lpm 1` |
| `grep -c sec_touchscreen /proc/bus/input/devices` | `0` |
| `/sys/class/sec/tsp` | absent |
| `/proc/interrupts` | no `sec_ts` line |
| `nuxel-touch-arm.service` | `failed` |
| fb0 panel | `U:1440x3040p-0`, virtual_size `1440,6080`, 32 bpp |

**Consequence: this test cannot pass in the current state.** On a charger-mode boot
the touch controller is not initialised, so no touch device exists and no finger can
produce an event. The first step of the procedure below fixes that (unplug + normal
reboot). Everything the tracer grades for this boot is `blocked` — never `ok` — and
`FIRST_FAIL_LAYER=1`.

The repository side of this item is `OFFLINE_TESTED`; the finger half is
`NEEDS_OWNER_TEST` and must never be auto-promoted.

---

## 1. Feature

Interactive touch input on the Samsung Galaxy S10+ (beyond2lte, SM-G975F): the
whole chain `sec_ts` → IRQ → evdev → libinput → phoc → Wayland → WebKitGTK →
Nuxel Home, proven by a real contact with real coordinates reaching the launcher
document, plus the launcher acting on it.

## 2. Why this matters

Without touch the phone is not interactive: the launcher, Settings, every app and
the whole "reliable interactive Nuxel" claim depend on it. It is also the area where
earlier cycles were misled for six cycles — by a charger-mode boot in which the
touchscreen genuinely does not exist, and by measuring a fixed input node number
that belonged to the wrong device. This test therefore **checks the boot mode first**
and selects the panel **by capability, never by node number**.

## 3. Preparation

1. Handset booted into Nuxel, screen on, and — critically — **not** in charger mode.
   Check it before anything else:

   ```sh
   tr ' ' '\n' < /proc/cmdline | grep androidboot.mode    # must print NOTHING
   ```

   If it prints `androidboot.mode=charger`, touch is disabled for this whole boot and
   nothing below can pass: unplug the charger, reboot normally, and start again
   (`docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md`).
2. Root access on the live console (or the on-device terminal).
3. The touchscreen controller must be registered — quick sanity check:

   ```sh
   grep -A5 sec_touchscreen /proc/bus/input/devices
   ```
   Expect a block with `B: PROP=2` (that bit is `INPUT_PROP_DIRECT`) and MT axes.
4. Nothing else needs to be prepared. The harness takes an owner-test lock
   (`/run/nuxel-touch-capture.lock`) so the boot-mode guard cannot reboot the phone
   mid-test, holds the reader open only for the bounded window, and releases
   everything on exit.
5. Budget: 90 s of touching. The session is hard-bounded (`--seconds` + slack, plus
   `timeout`), so it cannot hang the console.

## 4. Exact action

1. Run the bounded capture. It prints the touch sequence to perform *before* it arms:

   ```sh
   nuxel-touch-capture.sh --seconds 90
   ```
2. While it is armed, perform the sequence deliberately and slowly — the harness
   prints exactly this list at start-up:

   | # | Action | What it proves |
   |---|---|---|
   | 1 | **one tap** in the middle of the screen (~0.3 s) | down/up and a plausible coordinate |
   | 2 | **three taps** at top-left, centre, bottom-right | no swapped or inverted axis |
   | 3 | **one vertical swipe**, bottom third → top third, slowly (≥1 s) | move delivery, not just taps |
   | 4 | **two fingers down together** for ~1 s, then lift both | multi-contact / slots + tracking ids |
   | 5 | **open Settings, then return Home, then open Terminal, then scroll the launcher, then select an app** | the completion definition for the whole touch mission |
   | 6 | **type three keys on the on-screen keyboard** in a text field | the keyboard's own hit testing on the same pipeline |
3. If the harness reports that layer 7 has no evidence, open the instrumented page
   once and repeat the taps in it:

   ```sh
   python3 /usr/libexec/nuxel/nuxel-touch-trace.py --stage-probe
   # then open /touch-probe.html in a WebKit view as the staging receipt says
   ```
4. Save the bundle path it prints (`BUNDLE=…`) and the verdict block.
5. Then confirm the human half — this is the part no script can do:
   * did the tile you tapped actually open?
   * does the tap ring/dot appear under your finger on the probe page?
   * does a swipe move the UI (scroll/page change) in the direction you swiped?
6. Write down, in the report: the taps you made, the `CAPTURE_GATE=` line, the
   `FIRST_FAIL_LAYER=` line, and your answer to step 5.

## 5. Expected result

* `tr ' ' '\n' < /proc/cmdline | grep androidboot.mode` prints **nothing** (normal boot).
* `grep -A5 sec_touchscreen /proc/bus/input/devices` shows the panel with `B: PROP=2`.
* The harness prints `CAPTURE_GATE=PASS`, with `gate.json` showing `down ≥ 1`, `up ≥ 1`,
  `coords_plausible: true`, `dom_layer_state: "ok"` — i.e. coordinates observed at the
  **top** layer, inside the device's own reported range.
* `grep '^LAYER=' <BUNDLE>/trace.txt` shows `STATE=ok` for layers 1–7.
* Coordinates track your finger: top-left taps give small x/y, bottom-right taps give
  large x/y, and the swipe x stays roughly constant while y changes monotonically.
* The launcher tile you tapped opens, and the probe page draws a ring under your finger.
* `<BUNDLE>/events.jsonl` exists and contains one JSON record per input event with the
  kernel timeval (`ts`/`iso`) plus one `point` record per frame carrying both the raw
  and the mapped coordinates; `<BUNDLE>/coordinate-map.json` records the panel
  (1440x3040 from `/sys/class/graphics/fb0/modes`), the device range and its source,
  the output scale/transform, and `validation.verdict`.
* **Completion definition for the whole touch mission:** a real finger can open
  Settings, return Home, open Terminal, scroll the launcher, select an app, and use
  the on-screen keyboard. Steps 5 and 6 above are that definition; anything less is
  not a finished touch story even if the machine gate passes.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning | Next step |
|---|---|---|
| `tr … grep androidboot.mode` prints `charger` | charger/LPM boot: the touch driver was never loaded | unplug, reboot normally, redo |
| `verdict=CHARGER_MODE_TOUCH_DISABLED`, harness exits 10 | same thing, detected by the harness before arming | same |
| Layer 1 `blocked`/`drop`, no `sec_touchscreen` in `/proc/bus/input/devices` | driver did not bind (LPM, probe failure, or i2c 4-0048 not bound) | read `dmesg | grep -i sec_ts`; if it is the LPM gate, reboot normally |
| Layer 2 `drop` — IRQ delta 0 **while raw events exist below it** | events come from somewhere other than the `sec_ts` IRQ line (wrong device selected) | re-run and inspect `<BUNDLE>/evdev.txt` (capability scan) |
| Layer 3 `drop` — panel present but `INPUT_PROP_DIRECT` absent | the node is not a direct touch surface; libinput will ignore it | capture `B: PROP=` from `/proc/bus/input/devices` |
| Layer 4 `drop` — shim accepted 0 devices | the interposer rejected every candidate | read `/run/nuxel-libinput-path.state` reject reasons |
| Layer 5 `drop` — compositor holds no input fd | phoc never opened the node | check `nuxel-wayland`/`seatd` state and `/run/nuxel-libinput-path.state` |
| Layer 6 `drop`/`blocked` — no `wl_touch` | compositor did not produce Wayland touch events | enable `WAYLAND_DEBUG=1` on the compositor for the next run |
| Layer 7 `blocked`, other layers `ok` | events reached the compositor but no DOM evidence was captured | stage the probe page (`--stage-probe`) and tap in it |
| `CAPTURE_GATE=FAIL` with `points=0` and no `BTN_TOUCH` | the glass was not touched during the window, or the armed node is not the panel | redo the tap; check `<BUNDLE>/evdev.txt` selection |
| Coordinates plausible but the **UI did not react** | events reached WebKit but the launcher did not act on them | quote the `NUXEL_INPUT` lines from `/run/nuxel-home.state` — this is a launcher issue, not a driver issue |
| Taps register at the mirrored position | axis orientation (rotated/mirrored frame) | record the raw coordinates from `touch-events.log` for the fix; do not guess |

## 7. Diagnostic command / log path

The exact command set the harness embeds (also printed by
`nuxel-touch-capture.sh --commands`, and copied into
`<BUNDLE>/commands.txt`):

```sh
tr ' ' '\n' < /proc/cmdline | grep -E 'androidboot.mode|lpcharge|charging_mode'
dmesg | grep -i -E 'sec_ts|sec_touchscreen|tsp_|is_lpm' | tail -40
grep -A5 sec_touchscreen /proc/bus/input/devices
grep -i -E 'sec_ts|4-0048' /proc/interrupts
grep -a 'accepted=1' /run/nuxel-libinput-path.state | tail -3
p=$(systemctl show -p MainPID --value nuxel-wayland); find /proc/"$p"/fd -maxdepth 1 | grep -c input
grep -a NUXEL_INPUT /run/nuxel-home.state | tail -10
```

The same diagnostics as machine-runnable modes (no finger needed, all read-only):

```sh
# the tool's own logic, on any host (no phone, no /dev/input, no root)
python3 tools/s10plus/a33/nuxel-touch-trace.py --self-test

# a bounded owner-tap window with the per-event JSONL stream, if you want the
# capture without the harness wrapper (90 s, always bounded)
python3 tools/s10plus/a33/nuxel-touch-trace.py --capture 90 --out /var/lib/nuxel/touch-capture/tap

# grade anything, and land a capture in the repository archive
python3 tools/s10plus/a33/nuxel-touch-trace.py --analyze /var/lib/nuxel/touch-capture/tap
python3 tools/s10plus/a33/nuxel-touch-trace.py --archive /var/lib/nuxel/touch-capture/tap \
        --archive-dir docs/beta-finalization/live/evidence
```

Log paths:

| Path | Contents |
|---|---|
| `<BUNDLE>/gate.json` | the machine gate (`pass`, `down`, `up`, `points`, `coords_*`, `dom_layer_state`) |
| `<BUNDLE>/trace.txt` | the 7 `LAYER=` verdicts + `FIRST_FAIL_LAYER=` + `VERDICT=` |
| `<BUNDLE>/touch-events.log` | per-event decode: `TOUCH_DOWN/UP/POINT slot=… raw=(x,y)` |
| `<BUNDLE>/raw-touch.bin` | the raw `struct input_event` stream |
| `<BUNDLE>/evdev.txt` | the capability scan and the `/proc/bus/input/devices` block |
| `<BUNDLE>/libinput-path.state` | the shim's accept/reject log with reasons |
| `<BUNDLE>/compositor-fds.txt` | the compositor's open `/dev/input` fds |
| `<BUNDLE>/wayland-seat.txt` | bounded journal + seat/focus + `wl_touch` |
| `<BUNDLE>/dom.txt` | DOM lines from `touch-probe.html` and the launcher's `NUXEL_INPUT` |
| `<BUNDLE>/events.jsonl` | one JSON record per input event: kernel timestamp, decoded kind, raw + mapped coordinates |
| `<BUNDLE>/coordinate-map.json` | panel geometry, device range and its source, output scale/transform, and the validation verdict |
| `<BUNDLE>/sysfs-input.txt` | the `/sys/class/input/*/device` capability scan (identity + capability bitmaps, no node-number assumption) |
| `<BUNDLE>/panel-geometry.txt` | the framebuffer geometry the coordinate map was built from |
| `<BUNDLE>/diagnostics.txt`, `<BUNDLE>/bootmode.txt` | the human-readable snapshot above |
| `/run/nuxel-touch-dom.log` | the tracer's bounded DOM collector |
| `/run/nuxel-home.state` | the launcher's own relayed DOM events |
| `/run/nuxel-bootmode.json` | charging-mode state published to the launcher |

Offline regression for the tooling itself:

```sh
./tools/s10plus/a33/tests/run-touch-tests.sh
```

## 8. PASS / FAIL

* **PASS (owner)** — on a **normal** boot: `CAPTURE_GATE=PASS` with `down ≥ 1`, `up ≥ 1`,
  coordinates inside the device range observed at the DOM layer, **and** the owner
  confirms the UI responded correctly (tap opened the tile, swipe moved the UI, and
  the coordinates tracked the finger). Attach the bundle path and the `LAYER=` lines.
* **FAIL (owner)** — any of: charger-mode boot, no `CAPTURE_GATE=PASS`, coordinates
  outside the device range, inverted/mirrored mapping, no UI reaction, or a check that
  could not be performed. Record the exact `FIRST_FAIL_LAYER=` line — that names the
  hop to fix — and do **not** report any layer as working that was not observed.
* `CAPTURE_GATE=PASS` alone is **not** the item passing: the item passes when the
  owner confirms the UI acted on the touch.

## 8a. Log evidence vs human proof (which is which)

**Already has log/machine evidence (this cycle, reproducible offline):**

| Item | Evidence |
|---|---|
| the tool's own logic (ioctl numbers, decoder, bitmap order, coordinate mapping, gate) | `nuxel-touch-trace.py --self-test` → 40/40 assertions |
| the tracer names the first lossy layer and never promotes absence | `tests/test-touch-trace.py` |
| the panel is selected by capability, never by a node number | `tests/test-touch-trace.py` (synthetic `/sys/class/input`), `tests/test-no-eventn-literal.py` (27 files) |
| the coordinate map honours the 1440x3040 DECON panel and the 0..4095 device range | `tests/test-touch-trace.py` + `coordinate-map.json` |
| the capture harness is bounded, takes an owner-test lock and cannot litter the repo | `tests/test-capture-harness.py` (33/33) |
| the shim is preloaded the way the A32 baseline preloads it | `tests/test-libinput-shim-invocation.py` |
| a charger-mode boot is detected and explained | `tests/test-bootmode-guard.py`; live capture `touch-*-p0probe-live-run/` |
| the shim survives a zero-device boot without crashing the compositor | live capture: `PATH_ASSIGN_SEAT … direct_devices_seen=0 added=0`, phoc still active |
| the kernel's own `-ENODEV` line and `/proc/cmdline` on the device right now | live capture `boot-driver.txt`, `console-probe.txt` |

**Requires human proof — no script can produce it:**

| Item | Why a human is required |
|---|---|
| a real contact producing down/up/swipe/multi-contact | only a finger can create a touch contact |
| coordinates tracking the finger (not mirrored/rotated/offset) | needs an eye comparing screen position with where the finger landed |
| the UI *responding*: Settings opens, Home returns, Terminal opens, launcher scrolls, an app starts | a script sees DOM events, not a usable interface |
| the on-screen keyboard accepting typed keys | needs a human reading what appeared in the field |
| the DOM probe ring appearing under the finger | needs eyes on the screen at that moment |

Anything in the second table is `NEEDS_OWNER_TEST` until a human reports it, and it is
never auto-promoted to `VERIFIED_ON_S10PLUS` by a script run — no matter how green the
gate is.

## Current automatic evidence (repository, this build group)

* `./tools/s10plus/a33/tests/run-touch-tests.sh` → **ALL PASS**; `TOUCH-TESTS: ALL PASS`
  (counts per suite in `docs/beta-finalization/touch/OFFLINE-TEST-RESULTS.md` §1).
* `python3 tools/s10plus/a33/nuxel-touch-trace.py --self-test` → **SELF-TEST: PASS (40/40
  assertions)**: ioctl request numbers, the 24-byte `struct input_event`, the decoder,
  the printed-bitmap word order (cross-checked against the A32 device-validated
  decoder), the raw→panel→output mapping against 1440x3040, the JSONL records, the
  "a checklist line is not evidence" rule, the "a previous verdict is not evidence"
  rule, and the exit-code contract.
* **Live capture this cycle** (`touch-20261016T193756+0200-cycl001-p0probe-live-run/`):
  graded `FIRST_FAIL_LAYER=1 NAME=driver STATE=blocked`, cause cited from the device's
  own `/proc/cmdline` (`androidboot.mode=charger`) and `dmesg`
  (`sec_ts_init: Do not load driver due to : lpm 1`). Every other layer is `blocked`,
  none is `ok`.
  * the owner-test harness itself is covered (`tests/test-capture-harness.py`, 33/33):
    `--commands` arms nothing, `CAPTURE_GATE=PASS` can only come from `gate.json`
    `pass:true`, an empty capture is `FAIL` + NEEDS_OWNER_TEST, and the bundle can
    never be written inside the repository (default fallback is `${TMPDIR:-/tmp}`);
  * shim capability fixtures 19/19; A31/A33 byte-identity 6/6;
  * tracer: all 7 layers `ok` on a synthetic delivered bundle; `FIRST_FAIL_LAYER`
    asserted at 1 (charger), 4 (libinput reject) and 7 (no DOM); empty bundle all
    `blocked` + `GATE=fail`; a checklist line is **not** libinput evidence;
  * boot-mode guard: LPM detected from four independent markers, prose not graded as
    evidence, and every reboot gate (ack, config, lock, cooldown, uptime, charger)
    asserted to suppress;
  * the `/dev/input/eventN` grep gate: **26 files checked, 0 failing**.
* Archived-capture grading (real handset output): `A20`/`A21` → layers 1 and 3 `ok`,
  `FIRST_FAIL_LAYER=2`; `A17`–`A19` and `.scratch/beta` → no usable evidence, honestly
  all-`blocked`. Full table in `docs/beta-finalization/touch/OFFLINE-TEST-RESULTS.md`.
* A32 baseline regression guard (other group's file, cross-check):
  `REGRESSION GUARD: PASS — the A32 baseline is intact` (42 pass / 0 fail).
* Live verdict for this area: **NEEDS_OWNER_TEST** — no finger has produced a real
  contact in this cycle, and nothing here is promoted to `VERIFIED_ON_S10PLUS`.

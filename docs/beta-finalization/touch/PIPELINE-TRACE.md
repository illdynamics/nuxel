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
| 3 | evdev node production | a **capability-selected** node exists with `INPUT_PROP_DIRECT` + `ABS_MT_POSITION_X/Y`, a non-degenerate range and a contact-slot capacity | `EVIOCGID` (the node's own `struct input_id`), `EVIOCGNAME`, `EVIOCGPROP`, `EVIOCGBIT(EV_ABS/EV_KEY)`, `EVIOCGABS`, `EVIOCGBIT(EV_ABS)`+`EVIOCGABS(ABS_MT_SLOT)` for the contact-slot capacity; raw events decode into a point |
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
LAYER_EXIT=<n> NAME=<name> STATE=<state> EXIT=<10+n>      (one per layer)
EXIT_CODE=<status> (first lossy layer <n> <name> is <drop|blocked>)
```

Every layer also has its own exit code — `10 + layer number` (`11` driver … `17` DOM).
Printing `LAYER_EXIT=` for all seven is unconditional; with `--layer-exit-codes` the
**process** exit status becomes that number, so a wrapper can branch on the exact hop
instead of parsing text. Without the flag the historical `0/3/4` statuses are kept, so
nothing that already parses this tool changes behaviour.

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

## 2a. Capability discovery, from two independent identities

A node number is not an identity: it depends on probe order and changes between boots
and between boot modes. So the selection is decided by capability, and the tool reads
**two** independent identity sources and reports them next to each other:

| Source | What it provides | Role |
|---|---|---|
| `/sys/class/input/<node>/device/` | `name`, `id/bustype`+`id/vendor`+`id/product`, the capability bitmaps (`properties`, `capabilities/abs`, `capabilities/key`), and per-axis `absinfo` where the kernel exposes it | independent confirmation of identity and of the capability claims |
| the evdev ioctls `EVIOCGID` / `EVIOCGNAME` / `EVIOCGPROP` / `EVIOCGBIT` / `EVIOCGABS` on every `/dev/input` node | the node's own answer: its `struct input_id` (`bustype`/`vendor`/`product`/`version`), the absolute ranges, and the **contact-slot capacity** from `EVIOCGBIT(EV_ABS)` (is `ABS_MT_SLOT` claimed at all) plus `EVIOCGABS(ABS_MT_SLOT)` (`max + 1` = simultaneous contacts), which sysfs does not carry on this kernel | **authoritative for selection** |

The evdev identity and the sysfs identity are printed side by side, never merged: in
`evdev.txt` each candidate carries `ioctl_id=bustype=0x… vendor=0x… product=0x… version=0x…`
next to `slot_bit` / `slot_range` / `slots`, and the live log prints one
`NODE_ID ioctl EVIOCGID … | sysfs id bustype=… vendor=… product=…` line so a node whose
`EVIOCGID` and sysfs `id/*` disagree is visible. Layer 3's `DETAIL` names both the
node's `EVIOCGID` and its `contact_slots=<n>` (with the raw `ABS_MT_SLOT` range), so the
briq-named "contact slots and tracking IDs" information is *measured from the node*, not
inferred from the decoded stream.

`NUXEL_SYSFS_INPUT_ROOT` (or `--sysfs-root`) redirects the sysfs half at a synthetic
tree, which is how the offline tests drive the *same* code with the checked-in
`tests/fixtures/sec-ts-only/` tree — no phone, no `/dev/input`.

If the two disagree the tool prints `SYSFS_IOCTL_DISAGREEMENT` with both readings and
the raw `properties` value. It never silently "corrects" one to match the other: the
raw value on this handset is `properties=2`, and the deployed A31 shim uses the
`INPUT_PROP_DIRECT` constant the same way (as a bit *index*) and accepts that same
value, so the number is *reported* rather than changed. A divergence must stay
visible, not be papered over.

Bitmap decoding follows the kernel's printed-word order (highest word first —
`drivers/input/input.c:input_print_bitmap` loops from `BITS_TO_LONGS(max)-1` down), and
that decoder is cross-checked at self-test time against the A32 decoder that was
validated against the live `gpio_keys` line.

## 2b. Coordinate validation against the 1440x3040 DECON panel

Panel geometry is **read, not assumed**:

| Read | Value on this handset |
|---|---|
| `/sys/class/graphics/fb0/modes` | `U:1440x3040p-0` — the panel |
| `/sys/class/graphics/fb0/virtual_size` | `1440,6080` — two panel pages (the animation and the bridge flip between them) |
| `/sys/class/graphics/fb0/bits_per_pixel` | `32` |

`coordinate-map.json` records the panel, the framebuffer page count, the device range
**and where that range came from** (`ioctl EVIOCGABS`, `sysfs absinfo`, or an explicit
`PANEL_FALLBACK` that says it is not a measurement), the output's scale/transform as
read from the bridge/launcher state, the mapping class (`identity` when the device range
equals the panel, `scaled` otherwise) and, for the captured points, a verdict:

```
COORD_MAP mapping=scaled device_range_x=[0, 4095] device_range_y=[0, 4095] range_source=... -> panel 1440x3040
COORD_VALIDATION points=<n> inside_device_range=<bool> inside_panel_bounds=<bool> verdict=OK|OUT_OF_RANGE|NO_POINTS
```

`NO_POINTS` is never `OK`, and an out-of-range point is named as `OUT_OF_RANGE` — a
mirrored, rotated or scale-mismatched mapping shows up as a number, not an opinion.
The A32 measurement is a headless output at half the panel resolution with `scale 2`,
so the mapping is validated against both the panel pixels and the output pixels.

## 2c. The bounded owner-tap capture session (`--capture SECONDS`)

`--capture N` is `--live` for `N` seconds with two extra artifacts:

* `events.jsonl` — **one JSON object per input event**, carrying the kernel timeval of
  the event itself (`ts` and `iso`) rather than the time the tool was scheduled, the
  decoded kind (`btn_touch` / `down` / `up` / `slot` / `axis` / `frame` / `point`) and,
  for the per-frame `point` records, the raw coordinates with their mapped panel and
  output coordinates;
* `coordinate-map.json` — the map described above, with the captured points validated.

It is bounded exactly like `--live` (hard `signal.alarm` at `--seconds + 15`, an event
cap, a byte cap, `select()` polling), it always writes the `/sys/class/input` capability
scan and the panel geometry into the bundle, and it refuses `0` (or anything outside
`1..900`) instead of running unbounded.

**What `--live` / `--capture` write — the exact list, inside and outside the bundle.**
Earlier revisions of this section said "nothing written outside the bundle". That was
wrong: the *capture* is read-only (`O_RDONLY | O_NONBLOCK` on the input nodes, read-only
ioctls, no `/dev/fb0` open, no arm, no reboot), but a non-dry run also arms the layer-7
probe, so these four writes happen on the phone:

| Write | Where | When | Why |
|---|---|---|---|
| the evidence bundle (layer verdicts, `evdev.txt`, `boot-driver.txt`, `interrupts-*.txt`, `sysfs-input.txt`, `evdev.txt`, `events.jsonl`, `coordinate-map.json`, `dom-http.log`, `probe-staging.txt`, …) | `--out DIR` (default `/var/lib/nuxel/touch-trace`) | always | the evidence itself |
| `touch-probe.html` copied into the launcher docroot (`/usr/share/nuxel/nuxel-home/`, or `/usr/share/nuxel/pwa/nuxel-home/` when that is the docroot present) | the launcher docroot, **outside** the bundle | non-dry `--live`/`--capture` (`stage_probe()`), or `--stage-probe` | the instrumented DOM page that makes layer 7 measurable |
| `/run/nuxel-touch-probe.staged` — the staging note and the manual step | `/run` | same | so a later command (and the owner) can see that the page was staged |
| `/run/nuxel-touch-dom.log` — every POST the page makes, plus a bound on `127.0.0.1:<--dom-port>` (default 8099, 200 requests, daemon thread) | `/run` and the bundle's `dom-http.log` | same | layer-7 DOM evidence with coordinates |

`--dry-run` performs none of the four: it prints `DRY_RUN: no arming, no DOM collector,
no writes outside the evidence bundle` and skips the collector, the staging and the
capture. It still writes the bundle. No partition, bootloader, DTB, modem or EFS write
happens in either mode.

Because the evidence is worth more inside the repository than only on the phone:

```sh
# on the phone: bounded capture (bundle under --out; see the table above for the four writes)
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --capture 90 --out /var/lib/nuxel/touch-capture/tap

# from the host: land it in docs/beta-finalization/live/evidence/touch-<ts>/
python3 tools/s10plus/a33/nuxel-touch-trace.py --archive <bundle> \
        --archive-dir docs/beta-finalization/live/evidence
```

`--archive` copies the bundle (it never moves or deletes the original), appends a line
to `INDEX.jsonl` in the archive root, and fails **loudly** with status 4 if the bundle
does not exist — it never silently archives nothing. `--archive-dir` does the same at
the end of a `--capture`/`--live` run.

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

## 6. Evidence-discipline bugs found by grading real captures

Four, in total: two found by the earlier cycle grading archived `.scratch` notes, and
two found **this cycle by grading a live charger-mode capture taken over the console**
(`docs/beta-finalization/live/evidence/touch-*-p0probe-live-run/`). Every one of them is
a bug that would have manufactured a pass, and every one is now regression-gated.

### 6a. Fixed earlier: two bugs that manufactured a pass

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

### 6b. Fixed this cycle: a live-console command frame was read as device output

The repository's console client frames every command as the command text plus the
client's own status:

```
===== grep -c sec_touchscreen /proc/bus/input/devices; echo "secreg_rc=$?"   [rc=1 frame=1eb660d8 sha_ok=yes]
    0
    secreg_rc=1
```

The first line is a **command wrapper**, not device output. The analyzer's shell-listing
detector anchors on the first token of the line, so a header starting with `=====` went
straight through, and `ev.best("sec_touchscreen")` matched the panel name *inside the
command text*. On a charger-mode boot — where `sec_ts_init` returned `-ENODEV` and no
touch device exists — layer 3 then reported *"sec_touchscreen appears in the evidence"*.
It graded `blocked`, not `ok`, but the detail sentence was a claim the capture did not
support. A frame-marker detector now classifies such headers as commands, while the
output lines that follow a header (which carry no frame marker) stay device output.

### 6c. Fixed this cycle: the analyzer graded its own previous verdict

The same capture was graded twice, the second time with `--json-out` inside the bundle.
The second run reported:

```
LAYER=6 NAME=wayland STATE=ok EVIDENCE=analysis.json DETAIL=wl_touch present in the compositor protocol capture
```

`analysis.json` was the first run's own output. The tool had promoted **its own
sentence** to layer-6 evidence with no `wl_touch` anywhere in the capture. Name-based
exclusion is now backed by a **structural** check (a file containing `LAYER=1 NAME=…`
or the tool's own JSON tag is a conclusion, whatever it is named), and it applies to
every pattern search — `first()`, `matches()` and `best()` — not just to `matches()`.
`named()` deliberately stays unfiltered: it looks up a specific evidence file.

Both of 6b and 6c are asserted in `tests/test-touch-trace.py` (a synthetic framed
capture and a synthetic bundle carrying a previous verdict), and the live charger-mode
capture is itself a regression case: it must grade `FIRST_FAIL_LAYER=1` with no layer
promoted from prose or from a prior verdict.

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

### 7a. This cycle's live capture (not historical)

`docs/beta-finalization/live/evidence/touch-20261016T193756+0200-cycl001-p0probe-live-run/`
is a **live** capture taken this cycle over the USB CDC-ACM console with the repository's
own client, read-only and bounded (no partition, bootloader, DTB, modem or EFS write; no
reboot; no arm; no `/dev/fb0` open). Graded result:

```
FIRST_FAIL_LAYER=1 NAME=driver STATE=blocked
  cause: "androidboot.mode=charger" and "sec_ts_init: Do not load driver due to : lpm 1"
LAYER 2..7: blocked (never ok)   GATE=fail   EXIT_CODE=3
```

It is a first-party measurement of the current device state — the handset is in
charger/LPM mode, so the touchscreen does not exist on this boot — and it is also the
regression case for §6b and §6c.

## 7b. The host self-test (`--self-test`)

`python3 nuxel-touch-trace.py --self-test` asserts this tool's own logic and needs no
phone, no libinput, no `/dev/input` and no root. It is the evidence line a reviewer can
re-run anywhere. It checks, in this order:

1. the ioctl request numbers by their numeric value (`EVIOCGNAME(64)==0x80404506`,
   `EVIOCGBIT(EV_ABS,8)==0x80084523`, `EVIOCGABS(ABS_MT_POSITION_X)==0x80184575`,
   `EVIOCGPROP(8)==0x80084509`, `EVIOCGID==0x80084502`,
   `EVIOCGABS(ABS_MT_SLOT)==0x8018456f`, plus the `struct input_id` decode) — a wrong
   number reads the wrong struct **silently**;
2. `struct input_event` is 24 bytes and the evdev codes match the kernel ABI;
3. the decoder turns a known byte stream into exactly one down, one up, one point, two
   `BTN_TOUCH` events and two frames;
4. the printed-bitmap word order, cross-checked against the A32 device-validated
   decoder, including the panel's own `ABS` bitmap and the live `gpio_keys` KEY line;
5. the coordinate mapping: identity keeps panel pixels, `scale 2` halves output
   coordinates, a half-range device maps as `scaled` and lands on the last panel pixel,
   and `NO_POINTS` is never `OK`;
6. the JSONL records carry timestamps and a mapped `point`;
7. the two evidence-discipline rules — a shell command listing is not device output, and
   a **previous verdict is never re-graded as evidence**;
8. the exit-code contract (one distinct code per layer, `10 + layer`);
9. this file contains no hard-coded input node number;
10. the bound is enforced (a `0` budget is refused) and the gate cannot be passed
    without a DOM event.

It prints `SELF-TEST: PASS (43/43 assertions)` and states plainly that it is **not** a
touch verification.

## 8. How to run it

```sh
# on the phone (bounded, read-only, no writes outside the bundle)
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --live --seconds 20 --out /var/lib/nuxel/touch-trace

# the bounded owner-tap window with the per-event JSONL stream
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --capture 90 --out /var/lib/nuxel/touch-capture/tap

# the owner test: bounded, self-terminating, takes an owner-test lock
nuxel-touch-capture.sh --seconds 90

# assert the tool's own logic on any host (no phone, no /dev/input, no root)
python3 tools/s10plus/a33/nuxel-touch-trace.py --self-test

# land a finished bundle in the repository archive
python3 tools/s10plus/a33/nuxel-touch-trace.py --archive /var/lib/nuxel/touch-capture/tap \
        --archive-dir docs/beta-finalization/live/evidence

# stage the DOM page and print the manual step
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --stage-probe

# grade anything, offline
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --analyze /var/lib/nuxel/touch-trace

# the whole offline gate for this area (tracer, shim, boot-mode guard, owner-test
# harness, and the /dev/input/eventN grep gate) — no phone, no root, no /dev/input
./tools/s10plus/a33/tests/run-touch-tests.sh
```

Gate for a PASS (and nothing less): ≥1 `BTN_TOUCH` down **and** up, `ABS_MT`
coordinates inside the device's own reported range, **and** those coordinates observed
at layer 7. `nuxel-touch-capture.sh` prints `CAPTURE_GATE=PASS` only then — and even
then the item stays `NEEDS_OWNER_TEST` until a human confirms the UI responded.

## 9. Terminal verdicts for this area

| Item | Verdict |
|---|---|
| tracer (layers, gate, JSONL, coordinate map, self-test), harness, DOM probe, shim, tests | **OFFLINE_TESTED** |
| live capture this cycle (charger-mode boot, read-only console probe) | **OBSERVED ON DEVICE** — `FIRST_FAIL_LAYER=1`; it proves the boot mode and the absence of the device, and nothing about touch |
| console/LPM boot mitigation | **OFFLINE_TESTED** (effect only observable after a live normal reboot) |
| permanent kernel-level LPM fix | **BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED** |
| physical finger on the glass, end to end | **NEEDS_OWNER_TEST** |

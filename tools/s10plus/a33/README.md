# tools/s10plus/a33/ — touch pipeline, boot-mode guard and libinput shim

This directory is **shared**: several beta-finalization build groups write here.
This README documents the **touch / interactive-input** files (build group
"Priority 0 — Touchscreen & Reliable Interactive Input"). Other A33 tools
(`nuxel-wl-fb.c`, `nuxel-anim-handoff.py`, `nuxel-verbose-boot.*`,
`nuxel-time.sh`, `nuxel-wifi-diag.sh`, `verify-*.py`, …) belong to the boot,
timekeeping, connectivity and userspace groups and are documented by them.

## The pipeline this group is responsible for

```
sec_ts (S6SY761, i2c 4-0048)          kernel driver
   -> IRQ (sec_ts line in /proc/interrupts)
   -> evdev node (/dev/input/*, INPUT_PROP_DIRECT + ABS_MT)
   -> libinput (through the capability shim below)
   -> phoc (compositor; /proc/<MainPID>/fd holds the input node)
   -> Wayland seat / wl_touch
   -> WebKitGTK DOM touchstart/move/end
   -> Nuxel Home PWA
```

## Files

| File | What it is |
|---|---|
| `nuxel-touch-trace.py` | The end-to-end tracer. `--live` runs a **bounded** capture session; `--capture SECONDS` runs the bounded owner-tap window and writes the per-event JSONL stream (`events.jsonl`) plus `coordinate-map.json`; the node is identified by capability and by its own `EVIOCGID`/`EVIOCGBIT`/`EVIOCGABS` answers (including `ABS_MT_SLOT` contact-slot capacity), never by a node number; `--analyze DIR` grades a bundle *or any archived capture directory*; `--stage-probe` installs the DOM page; `--self-test` asserts the tool's own logic **on a host** (no phone, no `/dev/input`, no root); `--archive DIR` copies a finished bundle into the repository archive. Prints one `LAYER=<n> STATE=<ok\|drop\|blocked> EVIDENCE=<path>` line per layer, one `LAYER_EXIT=<n> … EXIT=<10+n>` line per layer, and `FIRST_FAIL_LAYER=` (with `--layer-exit-codes` the process status becomes `10 + first lossy layer`). |
| `touch-probe.html` | Layer 7: the self-contained instrumented page that logs `touchstart x=… y=…` and POSTs to the tracer's bounded collector. |
| `nuxel-bootmode-guard.py` | Classifies a charger/LPM boot (the state in which `sec_ts` does not exist at all), publishes `/run/nuxel-bootmode.json` for the launcher, and can request **one gated normal reboot**. Never a blind reboot; never a kernel/bootloader change. |
| `nuxel-touch-capture.sh` | The owner-test harness: takes an owner-test lock, runs the bounded tracer with `--expect-finger`, adds the diagnostics, applies the machine gate and prints `CAPTURE_GATE=PASS\|FAIL\|BLOCKED`. Verdict is always `NEEDS_OWNER_TEST` unless a human confirms the UI. |
| `nuxel-libinput-path.c` | The capability-based libinput interposer (authoritative source; the deployed copy at `tools/s10plus/a31/nuxel-libinput-path.c` must stay byte-identical — enforced by `tests/test-libinput-parity.py`). |
| `build-libinput-shim.sh` | Builds the host selftest binary (used by the offline tests) and the aarch64 `.so` (cross compiler, or the UTM guest as fallback). |
| `kernel-patches/` | **Proposals only, never applied.** `sec_ts-lpm-initcall-deferred-bind.patch` is the not-deployed fix for the LPM boot; verdict `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED`. |
| `tests/` | All offline tests (see below). `run-touch-tests.sh` runs the whole set. |
| `tests/fixtures/` | Synthetic sysfs/uevent trees for the shim, and cmdline/dmesg captures for the boot-mode guard. |
| `tests/test-capture-harness.py` | Covers `nuxel-touch-capture.sh`: `--commands` arms nothing, `CAPTURE_GATE=PASS` can only come from `gate.json`, and the bundle is never written inside the repository. |
| `tests/test-libinput-shim-invocation.py` | Pins the deployment chain the A32 baseline uses, so a hardened shim that nothing preloads cannot pass: `LD_PRELOAD=/usr/lib/nuxel/libnuxel-libinput-path.so` on `nuxel-wayland.service`, the build flags of the A31/A32/A33 build scripts, A31/A33 source identity, the single-client tracked table, `ZERO_DEVICES` on absence, and the recorded deployed `.so` SHA-256. |

### The exact invocation the A32 baseline uses

The interposer is preloaded by systemd on the compositor unit — not by a shell wrapper:

```ini
# services/nuxel-session/systemd/nuxel-wayland.service
Environment=WLR_BACKENDS=headless,libinput
Environment=LIBSEAT_BACKEND=noop
Environment=WLR_LIBINPUT_NO_DEVICES=1
Environment=LD_PRELOAD=/usr/lib/nuxel/libnuxel-libinput-path.so
```

`tests/test-libinput-shim-invocation.py` asserts that line and its companions verbatim,
so bg-02/bg-10 parity checks can verify the chain mechanically. Rollback of a deployed
object is "restore the recorded SHA-256"; the deployed hash is recorded in
`docs/s10plus-autonomous-boot-repair/BETA-FINALIZER/09-LIVE-DEPLOYMENTS.md` and is
echoed by that test.

## Run the tests (no phone, no root, no /dev/input)

```sh
./tools/s10plus/a33/tests/run-touch-tests.sh          # everything
./tools/s10plus/a33/tests/run-touch-tests.sh --quick  # skip the shim build
```

## Run the tool on the phone (bounded, read-only)

```sh
# 1. what does the pipeline look like right now?
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --live --seconds 20 --out /var/lib/nuxel/touch-trace

# 2. the owner test (finger on the glass, 90 s window, per-event JSONL)
nuxel-touch-capture.sh --seconds 90

# 3. grade a bundle, or any archived capture directory, offline
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --analyze /var/lib/nuxel/touch-trace

# 4. assert this tool's own logic anywhere (no phone, no /dev/input, no root)
python3 tools/s10plus/a33/nuxel-touch-trace.py --self-test
```

Land a finished capture in the repository instead of leaving it on the phone:

```sh
python3 tools/s10plus/a33/nuxel-touch-trace.py --archive /var/lib/nuxel/touch-capture/tap \
        --archive-dir docs/beta-finalization/live/evidence      # -> touch-<ts>/
```

## Hard rules

* **No `/dev/input/eventN` literal anywhere** in this pipeline: devices are
  selected by capability (`EVIOCGID` / `EVIOCGPROP` / `EVIOCGBIT` / `EVIOCGABS`,
  including `EVIOCGBIT(EV_ABS)`+`EVIOCGABS(ABS_MT_SLOT)` for the contact-slot
  capacity, and `EVIOCGID` for the node's own `struct input_id`). The gate is
  `tests/test-no-eventn-literal.py`.
* **What `--live` / `--capture` write.** The *capture* is read-only (input nodes
  opened `O_RDONLY|O_NONBLOCK`, read-only ioctls, no `/dev/fb0`, no arm, no reboot),
  but a non-dry run arms the layer-7 probe and so writes, in addition to the evidence
  bundle under `--out`: `touch-probe.html` into the launcher docroot
  (`/usr/share/nuxel/nuxel-home/`), the staging note `/run/nuxel-touch-probe.staged`,
  the collector log `/run/nuxel-touch-dom.log`, and it binds `127.0.0.1:8099`
  (`--dom-port`) with a bounded 200-request daemon-thread collector. `--dry-run` does
  none of the four and still writes the bundle. `--stage-probe` stages the page and
  writes the `/run` note without running a capture.
* **Absence of evidence is never a pass.** A layer with no capture is `blocked`,
  never `ok`; a shell-command checklist line is not device output.
* **No flashing, no partition writes, no bootloader interfaces.** The LPM fix that
  would need a kernel change is documented and marked `BLOCKED_KERNEL`; the
  userspace mitigation is a normal reboot.
* **The evidence bundle is never written inside this repository.** On the device it
  goes to `/var/lib/nuxel/touch-capture/<ts>`; where that is not writable the
  fallback is `${TMPDIR:-/tmp}`, and an explicit `--out` that cannot be created is a
  hard block rather than a silent relocation.
* **A passing script is not a finger test.** The harness verdict is
  `NEEDS_OWNER_TEST`; only a human confirming the on-screen result upgrades it.
* **The tool never grades its own output.** A previous verdict inside a bundle is
  recognised structurally and excluded from evidence, so a capture cannot feed itself
  into a pass (a real bug a live charger-mode capture exposed — see §6c of
  `docs/beta-finalization/touch/PIPELINE-TRACE.md`).
* **A charger-mode boot is never a touch measurement.** The live probe from this cycle
  is archived under `docs/beta-finalization/live/evidence/touch-*-p0probe-live-run/`
  and graded `FIRST_FAIL_LAYER=1`; read it before reporting anything about touch.

See `docs/beta-finalization/touch/` for the pipeline trace, the charger-mode root
cause, the offline test results and `docs/beta-finalization/manual-proof/01-touchscreen.md`
for the owner procedure.

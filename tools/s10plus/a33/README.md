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
| `nuxel-touch-trace.py` | The end-to-end tracer. `--live` runs a **bounded** capture session; `--analyze DIR` grades a bundle *or any archived capture directory*; `--stage-probe` installs the DOM page. Prints one `LAYER=<n> STATE=<ok\|drop\|blocked> EVIDENCE=<path>` line per layer plus `FIRST_FAIL_LAYER=`. |
| `touch-probe.html` | Layer 7: the self-contained instrumented page that logs `touchstart x=… y=…` and POSTs to the tracer's bounded collector. |
| `nuxel-bootmode-guard.py` | Classifies a charger/LPM boot (the state in which `sec_ts` does not exist at all), publishes `/run/nuxel-bootmode.json` for the launcher, and can request **one gated normal reboot**. Never a blind reboot; never a kernel/bootloader change. |
| `nuxel-touch-capture.sh` | The owner-test harness: takes an owner-test lock, runs the bounded tracer with `--expect-finger`, adds the diagnostics, applies the machine gate and prints `CAPTURE_GATE=PASS\|FAIL\|BLOCKED`. Verdict is always `NEEDS_OWNER_TEST` unless a human confirms the UI. |
| `nuxel-libinput-path.c` | The capability-based libinput interposer (authoritative source; the deployed copy at `tools/s10plus/a31/nuxel-libinput-path.c` must stay byte-identical — enforced by `tests/test-libinput-parity.py`). |
| `build-libinput-shim.sh` | Builds the host selftest binary (used by the offline tests) and the aarch64 `.so` (cross compiler, or the UTM guest as fallback). |
| `kernel-patches/` | **Proposals only, never applied.** `sec_ts-lpm-initcall-deferred-bind.patch` is the not-deployed fix for the LPM boot; verdict `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED`. |
| `tests/` | All offline tests (see below). |
| `tests/fixtures/` | Synthetic sysfs/uevent trees for the shim, and cmdline/dmesg captures for the boot-mode guard. |

## Run the tests (no phone, no root, no /dev/input)

```sh
./tools/s10plus/a33/tests/run-touch-tests.sh          # everything
./tools/s10plus/a33/tests/run-touch-tests.sh --quick  # skip the shim build
```

## Run the tool on the phone (bounded, read-only)

```sh
# 1. what does the pipeline look like right now?
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --live --seconds 20 --out /var/lib/nuxel/touch-trace

# 2. the owner test (finger on the glass, 90 s window)
nuxel-touch-capture.sh --seconds 90

# 3. grade a bundle, or any archived capture directory, offline
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --analyze /var/lib/nuxel/touch-trace
```

## Hard rules

* **No `/dev/input/eventN` literal anywhere** in this pipeline: devices are
  selected by capability (`EVIOCGPROP` / `EVIOCGBIT` / `EVIOCGABS`). The gate is
  `tests/test-no-eventn-literal.py`.
* **Absence of evidence is never a pass.** A layer with no capture is `blocked`,
  never `ok`; a shell-command checklist line is not device output.
* **No flashing, no partition writes, no bootloader interfaces.** The LPM fix that
  would need a kernel change is documented and marked `BLOCKED_KERNEL`; the
  userspace mitigation is a normal reboot.
* **A passing script is not a finger test.** The harness verdict is
  `NEEDS_OWNER_TEST`; only a human confirming the on-screen result upgrades it.

See `docs/beta-finalization/touch/` for the pipeline trace, the charger-mode root
cause, the offline test results and `docs/beta-finalization/manual-proof/01-touchscreen.md`
for the owner procedure.

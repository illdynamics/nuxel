# Live touch-pipeline probe — S10+ over the USB CDC-ACM console

**This capture is DEVICE OUTPUT, graded honestly, and its verdict is negative.**
It was taken this cycle with the repository's own console client
(`scripts/s10plus-debug-pack/nuxel-live.sh`) as a bounded, **read-only** probe of the
touch pipeline (area 1 / P0). No partition, bootloader, DTB, modem or EFS write; no
bootloader interface; no reboot; no arm; no `/dev/fb0` open.

## What it found

The handset is **booted in charger / low-power mode**, which is the documented P0
root cause: the kernel deliberately does not initialise the touchscreen driver, so
there is no touch device on this boot at all.

| Probe | Result |
|---|---|
| `/proc/cmdline` | `androidboot.mode=charger`, `charging_mode=0x3030` |
| `dmesg` | `[    1.638064] [sec_input] sec_ts_init: Do not load driver due to : lpm 1` |
| `grep -c sec_touchscreen /proc/bus/input/devices` | `0` |
| `/sys/class/sec/tsp` | absent |
| `/proc/interrupts` | no `sec_ts` line |
| `/sys/class/input` | only `event0..6` / `input0..6` (no panel) |
| `/sys/class/graphics/fb0/modes` | `U:1440x3040p-0` — the DECON panel |
| `/sys/class/graphics/fb0/virtual_size` | `1440,6080` — two panel pages (the bridge flips) |
| `/sys/class/graphics/fb0/bits_per_pixel` | `32` |
| `systemctl is-active nuxel-wayland nuxel-touch-arm seatd` | `active` / **`failed`** / `active` |
| `/run/nuxel-libinput-path.state` | `PATH_ASSIGN_SEAT seat='seat0' direct_devices_seen=0 added=0 db_seeded=0` |

Two things this capture proves beyond the boot-mode finding:

* **the shim's zero-device policy works live**: it logged `direct_devices_seen=0`
  and the compositor (`phoc`, main PID active) stayed up — a charger-mode boot does
  not crash the display session;
* **`nuxel-touch-arm.service` is `failed`** on this boot, which is exactly what the
  driver-absent state predicts, and is why the earlier cycles' "touch is broken"
  readings were measurements of the bootloader's power state, not of the driver.

## Files

| File | What it is |
|---|---|
| `console-probe.txt` | the raw console transcript (the kernel mirrors `/dev/kmsg` onto the same port, so unrelated telemetry is interleaved; the `===== … [rc=… frame=… sha_ok=…]` headers separate commands from output) |
| `boot-driver.txt` | `/proc/cmdline` + the `sec_ts_init` `-ENODEV` line, extracted for the layer-1 grader |
| `evdev.txt` | `/sys/class/input`, `/dev/input` and one real sysfs identity read |
| `interrupts-{before,after}.txt` | the `/proc/interrupts` probe (no `sec_ts` line exists this boot) |
| `verdict.txt`, `layer-verdicts.txt`, `analysis.json` | `nuxel-touch-trace.py --analyze` output for this capture |
| — | The *original* analyzer records (generated while the directory was named `...-p0probe`) are kept for audit **outside** this bundle, at `docs/beta-finalization/touch/live-capture-pre-rename-records/`, because a copy of `analysis.json` under another name inside the bundle would be re-graded as evidence by the analyzer (see that directory's README). `verdict.txt` and `analysis.json` here were re-generated with `--analyze` against the stored directory, so every `EVIDENCE=` / `JSON_OUT=` path in them names a file that exists; their finding is unchanged (`FIRST_FAIL_LAYER=1`, charger/LPM boot). |
| `provenance.txt` | how the capture was taken and what was **not** done |

`verdict.txt` / `layer-verdicts.txt` / `analysis.json` are the analyzer's own
conclusions; the tool refuses to grade its own output as evidence (a real bug this
capture exposed — see §6c of `docs/beta-finalization/touch/PIPELINE-TRACE.md`).

## Verdict

`FIRST_FAIL_LAYER=1` (driver, `blocked`, charger/LPM boot). **No touch evidence
exists on this boot and none is claimed.** Node names inside `evdev.txt` are device
output — *data under test*, not an assumption: every tool in this area selects the
panel by capability.

Next action: a **normal** reboot (unplug the charger), then re-run
`nuxel-touch-capture.sh` with a finger ready. See
`docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md` and
`docs/beta-finalization/manual-proof/01-touchscreen.md`.

# TOUCHSCREEN DRIVER STATE — A34

Captured 2026-10-17T10:27:25Z (12:27:25 +02:00), normal Nuxel boot.

## Current boot (normal, not charger/LPM)

| Check | Result |
|---|---|
| `/proc/cmdline` | **no `androidboot.mode=charger`**, no `lpcharge=1`; `charging_mode=0x3030` only |
| Kernel | `Linux fedora 4.14.253 #15 SMP PREEMPT ... aarch64` |
| sec_ts binding | `sec_ts 4-0048` bound to the HSI2C controller |
| input node | `/dev/input/event2`, name `sec_touchscreen`, `PROP=DIRECT`, `ABS_MT` present |
| second node | `/dev/input/event3`, `sec_touchpad` (same controller, not used as the primary touch source) |
| `/sys/class/sec/tsp` | present |
| IRQ | `431: ... exynos7_wkup_irq_chip sec_ts`, count **142** at 10:27:25Z |
| touch counts | `all_touch_count` `TTCN=12` at 10:19:39Z after the physical test |
| touch-arm helper | `ARM_DONE ... module_off_master:OK`, then `TOUCH_POINT` records (no repeated reset loop) |

The earlier 12:03 baseline was a **different boot**: `androidboot.mode=charger`
made `sec_ts_init()` return `-ENODEV` before `i2c_add_driver()` and the device
was genuinely absent. That baseline is preserved in `BASELINE.md`; it is not
the current state.

## Evidence ladder for this boot

* T1 registered: **PASS** (`sec_touchscreen`, `4-0048`, driver `sec_ts`).
* T2 interrupts: **PASS** (IRQ 431 increments during real contact; 42 → 92 → 142).
* T3 raw evdev contact: **PASS** (`TOUCH_POINT` records at 2026-10-17T10:13:01Z,
  10:13:07–09Z, 10:13:54–56Z; 67 records).
* T4 libinput: **PASS for registration** (shim `PATH_ADD event2 accepted=1`,
  `PATH_ASSIGN_SEAT seat0`).
* T5 compositor: **PASS** (phoc holds `/dev/input/event2` and receives the contact
  stream that produced the WebKit event below).
* T6–T8: see `WEBKIT-INPUT-TRACE.md`; one physical tap produced a real
  `pointerdown`/`touchstart` and the launcher's own `app:launch` for Mail.

## First failing layer

For the one correlated tap at 10:13:01Z: **none before the application action**.
The first observed product defect after that tap is UX/presentation, not a
missing input event: the launcher opened Mail as a fullscreen iframe whose
message list is empty, so the glass shows an almost blank dark app with only a
small `✕` at the top right. That is why the owner reports "frozen".

## Evidence

* `evidence/baseline-input-raw.txt` (12:03 boot, charger mode)
* `evidence/t8-app-launch-raw.txt` (12:13 physical tap)
* `evidence/a34/` (screenshots and current state)

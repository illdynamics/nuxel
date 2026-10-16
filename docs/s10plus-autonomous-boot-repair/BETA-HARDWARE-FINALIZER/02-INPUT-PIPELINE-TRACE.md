# 02 — INPUT PIPELINE TRACE (stage by stage, nothing inferred from screenshots)

Pipeline under test: controller → IRQ → evdev → libinput → phoc → Wayland → WebKit →
launcher JS → application activation.

| # | Stage | Evidence (measured) | Verdict |
|---|---|---|---|
| 1 | Samsung `sec_ts` controller | `sec_ts 4-0048: ic_status_show: mutual:1, … lpm:0` after a normal boot | present |
| 2 | Kernel driver registration + IRQ | `input: sec_touchscreen … input/input2`; `/proc/interrupts`: `431: … exynos7_wkup_irq_chip 0 Level sec_ts` | present |
| 3 | Linux evdev | `/dev/input/event2` (`crw------- 13,66`), `B: PROP=2` (INPUT_PROP_DIRECT), event3 = `sec_touchproximity` | present |
| 4 | libinput device discovery | the phone shim’s own log: `PATH_ADD node=/dev/input/event2 name='sec_touchscreen' accepted=1`, `direct_devices_seen=2 added=2 db_seeded=2` | present |
| 5 | phoc / wlroots input backend | compositor (MainPID of `nuxel-wayland.service`) holds **2** `/dev/input/event*` fds | present |
| 6 | Wayland seat/output mapping | output `HEADLESS-1` 720x1520 scale 2 (phoc.ini); seat `seat0` assigned by the shim (`PATH_ASSIGN_SEAT … added=2`) | present |
| 7 | WebKitGTK event delivery | `nuxel-pwa-host` injects an observing user script that relays every `touchstart/touchmove/touchend/pointerdown/pointerup/click` with coordinates, hit element and viewport into `/run/nuxel-home.state`.  Layout events already arrive through the same channel (`SAFEZONES … width=360 …`) | instrumented, awaiting a finger |
| 8 | Launcher JS | `js/app.js` + `js/launcher.js` bind `pointerdown/up` on the tiles; `app:launch` is relayed by the same observer | instrumented |
| 9 | Application activation | `appRegistry.launchApp()` opens the registry URL in `.pwa-frame`; the same call is used by the hardware buttons and the Settings app | present |

## The FIRST broken link (before the fix)

**Stage 1–3**: the controller had never been registered because of the boot-time LPM
gate — see `01-TOUCHSCREEN-ROOT-CAUSE.md`.  Everything downstream of stage 4 was
therefore being judged against a device that did not exist; the earlier
`TOUCH_POINT` / `EV_ABS` observations came from boots that were *not* in charger
mode, which is exactly why the user’s experience (no touch at all) and the cycle
logs disagreed.

## What an earlier cycle got wrong, in one line

`nuxel-touch-arm` (A29) tried to arm the controller through
`/sys/class/sec/tsp/…`, but in LPM mode those nodes do not exist; the unit failed
with exit 2 and the failure was read as a driver problem rather than as a boot-mode
problem.  The helper is now *not* needed for a normal boot and remains harmless.

## Reproducible trace commands

```
tr ' ' '\n' < /proc/cmdline | grep androidboot.mode     # must print nothing
grep -A5 sec_touchscreen /proc/bus/input/devices
tail -6 /run/nuxel-libinput-path.state | grep accepted=1
p=$(systemctl show -p MainPID --value nuxel-wayland); ls -l /proc/$p/fd | grep -c /dev/input/event
grep -E 'EVT (touchstart|pointerdown|click)|app:launch' /run/nuxel-home.state
```

Physical confirmation (user, on the glass): tap top-left, tap centre, tap bottom-right,
swipe vertically, then tap one launcher tile — each contact must appear as an
`EVT pointerdown/click … id=<tile>` line followed by `EVT app:launch id=<app>`.

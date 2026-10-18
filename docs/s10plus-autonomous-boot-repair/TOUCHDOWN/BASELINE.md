# TOUCHDOWN BASELINE — frozen before any change

Captured: 2026-10-17T12:03–12:07 +02:00 (Europe/Amsterdam)
Host: `dextronux`, Fedora 43, x86_64, kernel 6.17.1-300.fc43.x86_64
Console: `/dev/ttyACM0` (USB CDC-ACM, `18d1:4ee7`, SuperSpeed 5 Gbps, serial `NUXEL-S10PLUS-0001`)
Console tool: `scripts/s10plus-debug-pack/nuxel-live.sh` (exclusive flock, framed + SHA-256 verified)
Full raw transcripts: `TOUCHDOWN/evidence/baseline-input-raw.txt`, `baseline-runtime-raw.txt`, `baseline-config-raw.txt`

## Device / kernel

| Item | Value |
|---|---|
| Model | Samsung Galaxy S10+ SM-G975F, beyond2lte, Exynos 9820 |
| Kernel | `Linux fedora 4.14.253 #15 SMP PREEMPT Thu Oct 15 22:29:25 UTC 2026 aarch64` |
| Uptime at freeze | 706 s (boot ≈ 2026-10-17T11:51:57Z) |
| OS | Fedora Linux 43 (Forty Three), aarch64 |
| Framebuffer | `U:1440x3040p-0`, virtual 1440x6080, 32 bpp |
| Wayland output | phoc headless 720x1520 @ scale 2 → 360x760 CSS px |
| Display bridge | `nuxel-wl-fb`, `FRAMES_OK total=17987 fps_1s=24 failures=0 out=720x1520 scale=2` |
| Clock | 2026-10-17T12:05 +02:00 (correct this boot) |

## Boot mode — THE decisive fact

`/proc/cmdline` contains:

```
androidboot.mode=charger   charging_mode=0x3030   consoleblank=0
```

Kernel log at 1.665 s:

```
[sec_input] sec_ts_init: Do not load driver due to : lpm 1
tsp_io: disabling
tsp_avdd: disabling
```

`sec_bat_is_lpm_check()` maps `androidboot.mode=charger` → `lpcharge=1`;
`sec_ts_init()` then returns `-ENODEV` **before `i2c_add_driver()`**. The driver is
built in (`CONFIG_TOUCHSCENEEN_SEC_TS_Y771=y`), `/lib/modules/4.14.253` does not
exist and `CONFIG_KEXEC` is unset, so userspace cannot instantiate it on this boot.

**Evidence-ladder state for this boot: T0 — DEVICE ABSENT.**

## Input devices actually present (7, none is touch)

| Node | Name | Handlers | Notes |
|---|---|---|---|
| input0 | meta_event | event0 | virtual |
| input1 | gpio_keys | event1, sec_key_notifier | KEY_VOLUMEUP/DOWN, KEY_POWER, KEY_WINK (Bixby), KEY_703? |
| input2 | grip_sensor | event2 | virtual |
| input3 | ssp_context | event3 | sensor hub |
| input4 | Headset | event4, sec_key_notifier | |
| input5 | hall | event5 | |
| input6 | certify_hall | event6 | |

* `sec_touchscreen` — **absent** from `/proc/bus/input/devices`.
* `/sys/class/sec/tsp/` — **does not exist**.
* `/proc/interrupts` — **no `sec_ts` / TSP line**.
* `/dev/input/event0..6` exist, mode `0600 root:root` (phoc runs as root).

## Button / touch daemons

```
nuxel-button-manager  CONFIG_LOADED power_short=screen-toggle power_long=power-menu
                      bixby_short=open-terminal
                      KEY_DEVICE_OPEN /dev/input/event1 name=gpio_keys
                      TOUCH_DEVICE_NOT_FOUND (no DIRECT+MT device)
nuxel-touch-arm       failed, 10 restarts then StartLimit; state:
                      NO_TOUCH_DEVICE devices=7  (every 10 s)
nuxel-libinput-path   direct_devices_seen=0 added=0 db_seeded=0
```

## Running services (14)

`dbus-daemon`, `ModemManager`, `NetworkManager`, `nuxel-bridge`,
`nuxel-button-manager`, `nuxel-http-bridge`, `nuxel-notifications`,
`nuxel-portal`, `nuxel-wayland` (phoc PID 5317), `nuxel-wl-fb`, `polkit`,
`seatd`, `systemd-journald`, `systemd-logind`. Failed: `nuxel-touch-arm`.

## Process tree (relevant)

```
5317 phoc --no-xwayland -C /etc/nuxel/phoc-phone.ini -E /usr/lib/nuxel/nuxel-session.sh
5351  └ nuxel-pwa-host
5392 nuxel-wl-fb
5393 nuxel-button-manager
3505/3506 nuxel-console /newroot  (live console)
3471 sh /usr/lib/nuxel/nuxel-postboot.sh 20
```

Wayland socket: `/run/nuxel-wayland/wayland-0` (root-only, phoc owns it).
Session log: `layout=/pwa/nuxel-home bridge_ok=yes url=http://127.0.0.1:8000/pwa/nuxel-home/index.html`.
Launcher state: `NUXEL_INPUT EVT diag-ready ... w=360 h=760 dpr=2 splash=absent`, `NUXEL_HOME_READY`.

## Deployed binary hashes (SHA-256)

| Path | SHA-256 |
|---|---|
| /usr/lib/nuxel/nuxel-pwa-host | 18631d5b71eb938d821ba319ddf78ee73b403811933824d93b36dc9439f7f6b0 |
| /usr/lib/nuxel/nuxel-wl-fb | e4b4293e8d3d7d5e1c168e58c80ef23e4cb64db30313f0658498362ccaca7b9e |
| /usr/lib/nuxel/nuxel-button-manager | f0648fb7b9e95e86ab00c0f1d46b87693aedd6941244402c68801474fd95bd0f |
| /usr/lib/nuxel/nuxel-touch-arm | 2d1f6ef4d8ee835a131a6c345d2546fade8383b6007a1078efe31db4b85e58ba |
| /usr/lib/nuxel/nuxel-session.sh | 848255f54f164f70cd69440f750a76eb3f7dbf00471b2837f709eb3d38dd32ec |
| /usr/lib/nuxel/libnuxel-libinput-path.so | present (71376 B); no `/etc/ld.so.preload` |

Rollback copies on device: `nuxel-button-manager.prev` (77016 B),
`nuxel-pwa-host.prev-a32`, `nuxel-wl-fb.prev-a32`.

## Config hashes pulled to host (`backup-before-reboot/`)

| File | SHA-256 |
|---|---|
| /etc/nuxel/input/buttons.json | 52cd82a250913b4b57ef26f237d8d175c0680faf962b9ca6a4a4f078c380c361 |
| /etc/nuxel/input/button-fsm.json | ee2095dd83e118f308b0aba168ff6f7c932813bebec53e0e144f6bb53145f410 |
| /etc/nuxel/buttons/reboot-gate.json | 93917abb734900316532f3d7cbd233d615801cf0864b5aa1ad566b059cd511ac |
| /etc/nuxel/touch/bootmode-guard.json | 705d8bacf98894a0f131318cb9342902b1c8cc90e278111c0e4fe68b2ffcd418 |
| /etc/nuxel/bootmode/bootmode-guard.json | dd0028086831c7c857e1a10b4d033ccfb873efa40de3a6c7332174ea327b6ff9 |
| /etc/nuxel/phoc-phone.ini | c91f0505f1b2f7ada355b70d9ca5560ddc4e4891f8275d9967cd35fa58878f4a |
| /etc/nuxel/nuxel-beyond2lte.conf | 24c182f6c154f93af84081afa4cac1b1a99bf51efc40f9f0ebd432cf2bf12e0a |
| /usr/lib/nuxel/nuxel-postboot.sh | 8fd881944f16f52fdf433869c88c264725a70ad9daaeec15393a231f5abf6d7 |

## Power-button baseline

`/etc/nuxel/input/buttons.json` maps `power_short=screen-toggle`,
`power_long=power-menu`, `bixby_short=open-terminal`. Previous-boot journal shows
rapid repeated `FSM_ACTION source=key action=screen-toggle` (7 toggles in ~3 s) and
timer-originated `FSM_ACTION source=tick action=open-terminal`. These are recorded as
defects to investigate (POWER-BUTTON-ROOT-CAUSE.md), not yet changed.

## Console/recovery state

* Live console healthy; exclusive lock held only for the duration of each command.
* USB gadget enumerates automatically after reboot (measured in prior cycles).
* Nothing was written, flashed or rebooted before this file was written.
* Rollback material is preserved on-device and on-host (above).

## First hypothesis to test (falsifiable)

H1: This is a charger/LPM power-up; one software-initiated normal reboot with the
USB cable attached will remove `androidboot.mode=charger`, `sec_ts` will bind, and a
`sec_touchscreen` DIRECT+MT input device with EV_ABS/MT slots will appear.
Discriminating test: after reboot, `grep androidboot.mode /proc/cmdline` (must be
empty), `grep sec_touchscreen /proc/bus/input/devices`, `ls /sys/class/sec/tsp`,
`grep sec_ts /proc/interrupts`. If the device appears, proceed to T3 capture.

---

## A34 continuation (post-baseline, 12:15–12:27 +02:00)

The baseline above remains frozen as the 12:03 charger-mode boot. The phone was
later rebooted normally; the **current** boot has no `androidboot.mode=charger`
and `sec_touchscreen` is present on `/dev/input/event2`.

Current hashes (2026-10-17T10:27:25Z):

| Path | SHA-256 |
|---|---|
| `/usr/lib/nuxel/nuxel-wl-fb` (A34) | `ebe7e2455539b6363dd354cc9114b3798baccd340f40c2173bc447a60006b6d1` |
| `/usr/lib/nuxel/nuxel-pwa-host` | `18631d5b71eb938d821ba319ddf78ee73b403811933824d93b36dc9439f7f6b0` |
| `/usr/lib/nuxel/nuxel-button-manager` (A34) | `f5f9c6f88c141d667b17772dc59bbe9897271da0718b6e0fb05cc9f2bdfe0ab9` |
| `/usr/local/bin/nuxel-wl-snapshot` | `71c541006025e19ceb67edff9170ea2ee6e5878df79585faabf54616678f1c81` |
| `/usr/local/bin/nuxel-touch-trace.py` | `dc3a0d61ec4396b0bf55b58297f0801a4d773a120b945aee6bbac06e24709484` |
| status-bar.js (A34.3) | `d90b55be31954ffb221d165d50f40472c32ee8f2aefc9dbe47cbdd74a2e4ff4a` |
| app.js (A34.3) | `dc7d8fcc761bbd1b2878763f7f1fcb9db5e730241764a6f86295b6e74281e690` |
| button-manager (A34.3) | `f5f9c6f88c141d667b17772dc59bbe9897271da0718b6e0fb05cc9f2bdfe0ab9` |

Current IRQ 431 `sec_ts` count at 10:27:25Z: 142. Current frame rate: 23.67 fps.
See the topic files in this directory for the evidence ladder and verdicts.

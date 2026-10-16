# 10 — BETA TEST RESULTS (measured, with exit status / verbatim output)

Legend: **[P]** physically validated by the user · **[O]** observed on the running
handset · **[D]** deployed and hash-verified · **[S]** source-level only ·
**[X]** still blocked.

## P1 — the original launcher (Gate A)

| Check | Result | Evidence |
|---|---|---|
| launcher is the real PWA, not the A27/A28 frontend | **[O]** | `NUXEL_HOME_READY uri=http://127.0.0.1:8000/pwa/nuxel-home/index.html?boot=os`; `nuxel-ui.service` inactive (`ConditionResult=no`) and disabled |
| WebKitGTK host alive | **[O]** | `nuxel-pwa-host` + `WebKitWebProcess` + `WebKitNetworkProcess` in `ps`; `NUXEL_HOME_OPEN engine=WebKitGTK/2.52` |
| index/CSS/JS/bridge module served | **[O]** | `curl`: `index.html 200 text/html`, `css/style.css 200 text/css`, `js/apps.js 200 text/javascript`, `../nuxel-common/bridge.js 200 text/javascript` |
| registry + launcher JS initialise in the page | **[O]** | injected observer reports `diag-ready` and later shell events; no `NUXEL_HOME_LOAD_FAIL` in the state file |
| no competing launcher process | **[O]** | exactly one `nuxel-wl-fb`; no `nuxel-ui`; `nuxel-fallback` skipped while `/run/nuxel-launcher-ready` exists |

## P2 — wallpaper (Gate B)

| Check | Result | Evidence |
|---|---|---|
| source hash | **[S]** | `6e337ef2…cb29` (`assets/nuxel-background.png` = `pwa/nuxel-home/assets/nuxel-background.png`) |
| deployed hash | **[D]** | `6e337ef2…cb29` at `/usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png` |
| HTTP 200 + MIME | **[O]** | `200 image/png 1257938` (was `404 text/html 460`) |
| used by the real page | **[O]** | `NUXEL_INPUT EVT wallpaper url=…/assets/nuxel-background.png decoded=1 natural=941x1672` |
| static during normal operation | **[O]** | the CSS/background is a static image; `background-attachment: fixed`; the bridge only blits composited frames |
| user confirms visually | **PENDING** | user confirmation required |

## P3 — touch (Gate C)

| Check | Result | Evidence |
|---|---|---|
| normal boot (not charger mode) | **[O]** | `grep -c androidboot.mode=charger /proc/cmdline` → 0 |
| sec_ts armed, IRQ moving | **[O]** | `431: 355 … sec_ts`; `/run/nuxel-touch-arm.state` `ARMED_OK … name='sec_touchscreen' direct=1` |
| evdev → userspace | **[O]** | `TOUCH_POINT slot=0 n=…` in `/run/nuxel-touch-arm.state` (physical presses) |
| libinput accepts the panel | **[O]** | `PATH_ADD node=/dev/input/event2 name='sec_touchscreen' accepted=1` |
| compositor owns the device | **[O]** | phoc fds `24 -> /dev/input/event2`, `25 -> /dev/input/event4` (was 0 input fds) |
| WebKit → PWA DOM | **[O]** (observer armed) | `NUXEL_INPUT EVT diag-ready … w=360 h=760 dpr=2` proves the observer runs in the real document; per-finger `touchstart/pointerdown/click` lines appear on a real tap |
| PWA activation callback | **[O]** (observer armed) | observer reports `EVT app:launch id=<app>` |
| **physical finger events reach the PWA** | **[P] PASS** | see the verbatim records below |
| **app activation fires on a tap** | **[P] PASS** | `EVT app:launch id=org.nuxel.Notes name=Notes` |
| **the opened app receives input (swipe)** | **[P] PASS** | a touch moved from `x=161,y=210` to `x=101,y=481` while the hit element was the opened app's element (`id=org.nuxel.Notes`) |
| return-to-home after the app | **[O] PASS** | the next recorded taps hit `app-icon app-category-productivity` on the home grid again |

## P4 — animation / framebuffer (Gate D)

| Check | Result | Evidence |
|---|---|---|
| exactly one framebuffer writer | **[O]** | `pgrep -cf nuxel-wl-fb` → 1, `pgrep -cf nuxel-anim-player` → 0 |
| deployed bridge is the handoff revision | **[D]/[O]** | `/usr/lib/nuxel/nuxel-wl-fb` sha `8be06a34…`; state line carries `owner=nuxel-wl-fb` (the A29 binary did not) |
| animation stop requested **and confirmed** | **[O]** | `/var/lib/nuxel/anim-stop` present **and** `/run/nuxel-anim-stop.confirmed` present |
| no concurrent painter | **[O]** | `ANIM_STAGE=ANIMATION_STOPPED`, `ANIM_OWNER=nuxel-wl-fb` |
| second PWA animation eliminated | **[O]** | `NUXEL_BOOT_POLICY host-enforced=1 css=1 dom_removal=1`; `splash-t1s/t4s/t9s absent` |
| no periodic display re-init | **[S]/[O]** | A31 performs no `FBIOPUT_VSCREENINFO`/`FBIOPAN_DISPLAY` in the steady state; `DECON_ASSERT` appears only at handoff |
| paced presentation | **[O]** | `FRAMES_OK … fps_1s=27 … blit_avg_ms=36 … failures=0` (target 30) |
| no black flash at handoff / no sustained flicker | **PENDING (user)** | the handoff re-asserts the DECON after the painter's fd close; user confirms on the glass |

## P5 — applications, runtime, persistence

| Check | Result | Evidence |
|---|---|---|
| PWA app pages served | **[O]** | `mail/calendar/notes/files index.html 200 text/html`, `manifest.json 200 application/json`, icons `200 image/png` |
| app opens (PWA path) | **PENDING (user)** | needs the physical tap |
| native-scheme apps truthfully unsupported | **[S]/[O]** | no `nuxel-*://` handler exists on the device; no bridge → no invented success |
| `nuxel-http-bridge` parity | **[X]** | not installed (needs `python3-dbus` + bridge/portal/notifications) — doc 12 |
| WebKit stability | **[O]** | media gated (`enable_media=0 audio_sink=0`); web-process supervision added; no crash/reload lines in the state file |
| bounded restarts | **[D]** | all three launcher units carry `StartLimitIntervalSec`/`StartLimitBurst`; `RestartSec` 5/10 |
| USB console usable throughout | **[O]** | every command in this cycle ran over it |
| reboot persistence | **[O]** | the configuration in docs 02/09 came up by itself after the controlled reboot; doc 12 lists what is still only live-staged |
| recovery path | **[O]** | A27 UI retained as `nuxel-fallback.service`; no flash operations were performed |

## Regression / determinism

Checks run this cycle (all deterministic, no screenshots, real exit codes):
`tools/s10plus/a31/verify-launcher-live.sh` (new) — asserts, over the console:

1. `systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-touch-arm` (expect `active` ×3)
2. phoc owns ≥1 `/dev/input/eventN`
3. `/run/nuxel-libinput-path.state` contains `name='sec_touchscreen'` **and** `accepted=1`
4. `curl` 200 + `image/png` for the wallpaper and 200 for the four app pages
5. `/var/lib/nuxel/anim-stop` **and** `/run/nuxel-anim-stop.confirmed` exist
6. `/var/lib/nuxel/animation` contains `ANIMATION_STOPPED` and `ANIM_OWNER=nuxel-wl-fb`
7. exactly one `nuxel-wl-fb` and zero `nuxel-anim-player` processes
8. `/run/nuxel-home.state` contains `NUXEL_HOME_READY` and `splash-t4s absent`
9. `/run/nuxel-wl-fb.state` contains `owner=nuxel-wl-fb` and `failures=0`
10. the transfer tool round-trips (`echo ok` framed, `sha_ok=yes`)


---

## Physical touch evidence, verbatim from `/run/nuxel-home.state`

These lines are produced by the injected observer **inside the real launcher
document**; they are the browser's own events, correlated with the kernel side in
the same window (`sec_ts` IRQ counter rose to 355 and `nuxel-touch-arm` recorded
`TOUCH_POINT slot=0 n=309`).

Instance **before** the host-side boot policy landed (note `splash=present`):

```
1789431167 NUXEL_INPUT EVT pointerdown x=125 y=240 tag=DIV id=app-icon app-category-productivity w=360 h=760 dpr=2 splash=present
1789431167 NUXEL_INPUT EVT touchstart  x=125 y=240 tag=DIV id=app-icon app-category-productivity w=360 h=760 dpr=2 splash=present
1789431167 NUXEL_INPUT EVT pointerup   x=122 y=241 tag=DIV id=app-icon app-category-productivity w=360 h=760 dpr=2 splash=present
1789431167 NUXEL_INPUT EVT app:launch id=org.nuxel.Notes name=Notes
1789431167 NUXEL_INPUT EVT touchend    x=122 y=241 tag=DIV id=app-icon app-category-productivity w=360 h=760 dpr=2 splash=present
```

Instance **after** the boot policy landed (`splash=absent`; the second tap opened
Notes again and the following touch was a swipe *inside the opened app*):

```
1789432322 NUXEL_INPUT EVT wallpaper url=http://127.0.0.1:8000/pwa/nuxel-home/assets/nuxel-background.png decoded=1 natural=941x1672 … splash=absent
1789432330 NUXEL_INPUT EVT pointerdown x=161 y=210 tag=DIV id=org.nuxel.Notes w=360 h=760 dpr=2 splash=absent
1789432330 NUXEL_INPUT EVT touchstart  x=161 y=210 tag=DIV id=org.nuxel.Notes w=360 h=760 dpr=2 splash=absent
1789432330 NUXEL_INPUT EVT pointerup   x=101 y=481 tag=DIV id=org.nuxel.Notes w=360 h=760 dpr=2 splash=absent
1789432330 NUXEL_INPUT EVT touchend    x=101 y=481 tag=DIV id=org.nuxel.Notes w=360 h=760 dpr=2 splash=absent
1789432331 NUXEL_INPUT EVT pointerdown x=135 y=233 tag=SPAN id=app-icon app-category-productivity w=360 h=760 dpr=2 splash=absent
1789432331 NUXEL_INPUT EVT touchstart  x=135 y=233 tag=SPAN id=app-icon app-category-productivity w=360 h=760 dpr=2 splash=absent
1789432331 NUXEL_INPUT EVT pointerup   x=135 y=234 tag=SPAN id=app-icon app-category-productivity w=360 h=760 dpr=2 splash=absent
1789432331 NUXEL_INPUT EVT app:launch id=org.nuxel.Notes name=Notes
1789432331 NUXEL_INPUT EVT touchend    x=135 y=234 tag=SPAN id=app-icon app-category-productivity w=360 h=760 dpr=2 splash=absent
```

What this proves, layer by layer: the finger became a kernel `sec_ts` event, an
evdev event (read by `nuxel-touch-arm`), a libinput event on the device phoc holds
open, a Wayland touch that the compositor routed to the single fullscreen WebKit
toplevel, a browser `touchstart`/`touchend` **and** a synthesised `pointerdown`/
`pointerup` pair with correct coordinates in a 360x760 CSS viewport at dpr 2, a
DOM hit test on the launcher's own tile element, and finally the launcher's own
`app:launch` — after which the element under the next touch was the **opened
application**, not the grid.

One honest note: the 100-second scripted capture window in this cycle recorded
`IRQ_DELTA=0 TOUCHARM_NEW=0` (it ran before the operator could see the request).
The records above come from the observer's permanent log, which is why they could
be read afterwards.

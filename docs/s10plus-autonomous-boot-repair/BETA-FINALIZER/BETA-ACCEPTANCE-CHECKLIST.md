# NUXEL S10+ BETA 0.1 — ACCEPTANCE CHECKLIST

Status vocabulary: **SOURCE FIXED** · **OFFLINE TESTED** · **DEPLOYED** ·
**OBSERVED RUNNING** · **PHYSICALLY VALIDATED** · **STILL BLOCKED**

| # | Gate | Requirement | Status | Where the evidence is |
|---|---|---|---|---|
| A1 | A | The handset runs the real `pwa/nuxel-home/` PWA through WebKitGTK | OBSERVED RUNNING | `NUXEL_HOME_READY …?boot=os`, `engine=WebKitGTK/2.52` |
| A2 | A | No A27/A28 substitute frontend is presented | OBSERVED RUNNING | `nuxel-ui` inactive (`ConditionResult=no`) + disabled; `nuxel-fallback` skipped |
| A3 | A | Registry / CSS / JS / bridge module all load | OBSERVED RUNNING | `curl` 200s; observer `diag-ready` |
| A4 | A | No competing launcher process | OBSERVED RUNNING | 1 × `nuxel-wl-fb`, 0 × `nuxel-anim-player` |
| B1 | B | `assets/nuxel-background.png` installed at the expected path | DEPLOYED | `6e337ef2…cb29` at `…/pwa/nuxel-home/assets/` |
| B2 | B | Served with HTTP 200 + `image/png` | OBSERVED RUNNING | `200 image/png 1257938` |
| B3 | B | Computed CSS references it and the browser decodes it | OBSERVED RUNNING | `wallpaper url=…decoded=1 natural=941x1672` |
| B4 | B | User confirms the wallpaper on the glass | **AWAITING USER** | doc 12 item 13 |
| C1 | C | Normal (non-charger) boot | OBSERVED RUNNING | `androidboot.mode=charger` count = 0 |
| C2 | C | sec_ts armed and IRQ moving | OBSERVED RUNNING | `431: … sec_ts`; `ARMED_OK … direct=1` |
| C3 | C | evdev → userspace | OBSERVED RUNNING | `TOUCH_POINT slot=0 n=…` |
| C4 | C | libinput accepts the panel | OBSERVED RUNNING | `PATH_ADD … accepted=1` |
| C5 | C | Compositor owns the device | OBSERVED RUNNING | phoc fd → `/dev/input/event2` |
| C6 | C | WebKit/PWA receive the events | **PHYSICALLY VALIDATED** | `NUXEL_INPUT EVT touchstart/pointerdown` per finger, with coordinates |
| C7 | C | **Tap opens an app; swipe navigates** | **PHYSICALLY VALIDATED** | doc 10: `touchstart`→`app:launch id=org.nuxel.Notes`; a later touch landed inside the opened app and swiped |
| D1 | D | Exactly one OS boot animation owns the framebuffer | OBSERVED RUNNING | `ANIMATION_STOPPED`, `ANIM_OWNER=nuxel-wl-fb` |
| D2 | D | No second PWA startup video obscures the launcher | OBSERVED RUNNING | `splash-t1s/t4s/t9s absent` |
| D3 | D | Bridge takes ownership only after stop acknowledgement | DEPLOYED + OBSERVED | `/run/nuxel-anim-stop.confirmed`; A31 ordering |
| D4 | D | No concurrent painter remains | OBSERVED RUNNING | 0 × `nuxel-anim-player` |
| D5 | D | No sustained flicker / black flash at handoff | **AWAITING USER** | doc 12 item 13 |
| E1 | E | PWA registry entries (Mail/Calendar/Notes/Files) exist and are served | OBSERVED RUNNING | 4 × `200 text/html` + manifests + icons |
| E2 | E | App activation succeeds through the registry | **PHYSICALLY VALIDATED** (Notes) | `EVT app:launch id=org.nuxel.Notes name=Notes` |
| E3 | E | Unavailable hardware features report truthfully | SOURCE FIXED + OBSERVED | no `nuxel-*://` handler; no fake success path |
| E4 | E | `nuxel-http-bridge` parity | **STILL BLOCKED** | doc 12 item 6 |
| F1 | F | Fedora stable, no failed units | OBSERVED RUNNING | `systemctl --failed` empty; 3 launcher units active |
| F2 | F | No unbounded renderer/CPU use | OBSERVED RUNNING | paced 30 fps, `blit_avg_ms=36` |
| F3 | F | No repeated WebKit crashes | OBSERVED RUNNING | `enable_media=0`; no GIVEUP lines; supervision in place |
| F4 | F | USB console remains usable | OBSERVED RUNNING | all work in this cycle ran over it |
| G1 | G | All fixes expressed in the reproducible builder | SOURCE FIXED | `images/s10plus/build-phone-rootfs-inside-fedora.sh` stages A31 + wallpaper + units, with a fail-fast guard |
| G2 | G | Configuration returns after a controlled normal reboot | OBSERVED RUNNING | stack came up by itself post-reboot |
| G3 | G | A freshly built image was flashed and verified | **STILL BLOCKED** (not attempted: BOOT/userdata write) | doc 12 item 9 |
| H1 | H | Known-working fallback UI retained | OBSERVED RUNNING | `nuxel-fallback.service` → A27 UI, gated on launcher readiness |
| H2 | H | No unverified flash operations | OBSERVED | none performed |
| H3 | H | Deployment integrity (hash, atomic, rollback) | DEPLOYED | doc 09; staging keeps prior artifacts |

## Test commands

```
tools/s10plus/a31/verify-launcher-live.sh      # 17 automated live checks -> 17/17, exit 0
tools/s10plus/a31/build-a31.sh                 # reproducible aarch64 build (on the UTM VM)
tools/s10plus/a29/push-file.sh <f> <path>      # SHA-verified live deployment
```

## The one command that closes C7 / D5 / B4 (physical)

While the user taps and swipes the app grid:

```
scripts/s10plus-debug-pack/nuxel-live.sh --run \
  'a=$(grep -w sec_ts /proc/interrupts|awk "{print \$2}"); sleep 60; \
   b=$(grep -w sec_ts /proc/interrupts|awk "{print \$2}"); echo IRQ_DELTA=$((b-a)); \
   grep NUXEL_INPUT /run/nuxel-home.state | tail -20'
```

Expect: a rising `sec_ts` counter, `TOUCH_POINT` lines, `NUXEL_INPUT EVT
touchstart/pointerdown`, and `EVT app:launch id=<app>` when a tile is selected —
at which point Gates B (visually), C and D (visually) are the user's to confirm.

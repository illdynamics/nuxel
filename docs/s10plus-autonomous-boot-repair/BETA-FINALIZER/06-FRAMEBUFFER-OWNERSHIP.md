# 06 — FRAMEBUFFER OWNERSHIP (P4 / mission §10)

## 10.1 What was actually deployed — measured, not assumed

```
/run/nuxel-wl-fb.state (before)  FRAMES_OK total=128627 fps_1s=128627 failures=0 … (no owner=)
```

`fps_1s` equal to `total`, and no `owner=` field, is the **A29** state format.
The A30 handoff source existed in the tree but the *installed* binary was A29 —
which is why `/var/lib/nuxel/anim-stop` had never been created. Deployed
identity is therefore always read from the running process and its state file,
never inferred from a build directory.

## 10.2 The required ordering, as implemented (A31)

```
LAUNCHER_STARTING
  -> LAUNCHER_READY            (/run/nuxel-launcher-ready / NUXEL_HOME_READY)
  -> ANIMATION_STOP_REQUESTED  write /var/lib/nuxel/anim-stop (+ fb-hold-stop)
  -> ANIMATION_STOP_CONFIRMED  identity-verified: /proc/<pid>/comm AND /proc/<pid>/exe
  -> LAUNCHER_DISPLAY_OWNER    the FIRST scanout write: DECON re-assert + full frame
  -> OWNERSHIP_LOOP            paced presentation, single writer
```

Four measured corrections over A30:

1. **No scanout write before the stop is confirmed.** A30 called
   `frame_blit_once()` *before* writing `anim-stop`, i.e. it staged a launcher
   frame while the player was still painting — itself a concurrent write. A31
   writes only files until the panel is provably free.
2. **No "recover anyway".** A30 logged `ANIMATION_STOP_TIMEOUT … recovering
   anyway` and blitted into a live painter. A31: on timeout it performs a
   bounded, identity-verified stop (`SIGTERM`, then `SIGKILL`, the pid coming from
   a function that has already proved `comm` and `exe`), re-checks, and if the
   painter still lives it writes `HANDOFF_REFUSED … panel UNTOUCHED` and exits
   non-zero **without touching the panel**, leaving the animation/fallback as sole
   owner and the USB console usable.
3. **No periodic display reset.** A29 re-issued `FBIOPUT_VSCREENINFO` +
   `FBIOPAN_DISPLAY` every second in its reporting block. The bridge writes the
   visible buffer directly (`yoffset 0`, no double buffering), so A31 performs
   **no** `FBIOPUT_VSCREENINFO`/`FBIOPAN_DISPLAY` in the steady state; the DECON
   is re-asserted only on measured failure evidence (a run of failed captures) or
   after the painter's fd close releases it.
4. **Paced presentation.** A tight screencopy loop is replaced by a frame budget
   (`NUXEL_TARGET_FPS`, default 30, with measured `blit_avg_ms`); the blit itself
   lost its per-pixel division (precomputed x-map).

Measured end state:

```
/run/nuxel-wl-fb.state  FRAMES_OK total=5698 fps_1s=28 failures=0 blit_avg_ms=34
                        out=720x1520 src=720x1520 scale=2 panel=1440x3040 owner=nuxel-wl-fb
```

## 10.3 Exclusive ownership is a measured property, not a claim

* exactly one process has `/dev/fb0` open for scanout (`nuxel-wl-fb`);
* the animation player is gone and `/var/lib/nuxel/animation` records
  `ANIM_STAGE=ANIMATION_STOPPED  ANIM_OWNER=nuxel-wl-fb`;
* `/run/nuxel-anim-stop.confirmed` exists — written **only** after the painter is
  provably dead, so a stop *request* can never be mistaken for a handoff;
* the A27 UI cannot take the panel while `/usr/lib/nuxel/nuxel-wl-fb` exists
  (`ConditionPathExists=!` drop-in), and `nuxel-fallback.service` only runs when
  the launcher never became ready.

## 10.4 Restart storms

Two restart loops were observed contributing to a watchdog reset of the handset
during this cycle (a failing compositor re-spawning phoc every ~3 s and the bridge
every 2 s). All three launcher units now carry bounded restart policy
(`StartLimitIntervalSec`/`StartLimitBurst`, `RestartSec=5`/`10`), and the Wayland
unit also sets `WLR_LIBINPUT_NO_DEVICES=1` so a boot with no panel node (charger
mode) cannot put phoc into a failure loop.

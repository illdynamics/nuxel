# A21 POSTMORTEM — "one penguin / correct colours" (2026-10-15)

## Verdict

```
BOOT_RESULT        = FAILED_USER_RETURNED_TO_TWRP   (operator hard-reset at t=400 s)
RECOVERY_ACCESS    = RESTORED
NEXT_ACTION        = CAPTURE_FRESH_LOGS  (done)  -> A22
```

The reset was **the operator's own hard-reset hook**, not a crash of Nuxel:
`Internal error: Oops - BUG: 0 · pc : hard_reset_hook_callback+0x144/0x150` — byte-for-byte
the same signature as the A20 end-of-run (POWER+VOLUMEDOWN), and the same
`sec_reboot (0, panic)` "normal" resume into recovery. Nothing in the 400-second run
indicates a spontaneous fault.

## What A21 proved on hardware (all from the boot's own logs)

```
NUXEL_INIT_REV=A21-one-penguin-correct-colours
FIRSTLIGHT exit=0 · NUXEL_MARKER FIRSTLIGHT_FRAME_WRITTEN
NUXEL_MARKER ANIMATION_HOLD_DEFERRED                    <- resident painter NOT started
NUXEL_ANIM_OPT_HAS_STOPFILE=1 HAS_STATE=1 HAS_PIDFILE=1 <- option parsing fixed
NUXEL_ANIM_STATEDIR_FD_OK=1 STATEDIR_FD_RC=3
NUXEL_ANIM_PROC_OPEN_RC_PLAIN=6                         <- /proc opens
NUXEL_ANIM_PROC_OPEN_RC_DIRECTORY=EINVAL                <- the O_DIRECT bug, still measured
NUXEL_ANIM_FB_WIDTH=1440 HEIGHT=3040 VIRTUAL=6080 STRIDE=5760 BPP=32 BUFFERS=2
NUXEL_ANIM_FB_RED_OFF=16 LEN=8 GREEN_OFF=8 LEN=8 BLUE_OFF=0 LEN=8 TRANSP_OFF=24
NUXEL_ANIM_PAL0_SRC565=65535 PAL0_DST=16777215
NUXEL_ANIM_BG_INDEX=238 BG_SRC565=32 BG_DST=1024
NUXEL_ANIM_MARKER FIRST_FRAME_COMMITTED
nuxel-init: ANIMATION ownership: MP4 first frame committed after 1s
ANIM_STAGE=MP4_PLAYER_ACTIVE   (persisted in the Fedora rootfs)
fb-anim.pid=3500  fb-anim-ready=MP4_FIRST_FRAME_COMMITTED  fb-anim-starting=PLAYER_RUNNING
```

Playback, measured by the player's own counters over the whole run:

```
39 heartbeat lines x 240 frames = 9360+ frames, NUXEL_ANIM_HEARTBEAT_SKIPS=0 throughout
last heartbeat: FRAMES=5520 MS=229973 EXPECTED_MS=226320 -> 24.00 fps, 0 skips
earlier         FRAMES=3360 MS=140031 EXPECTED_MS=137760 -> 23.99 fps, 0 skips
NUXEL_ANIM_LOOP counted to at least 29 (29 x 8 s = 232 s of animation)
```

`pgrep -a nuxel-fb-phone` on the live system: **NO_PENGUIN_PAINTER_RUNNING**.

Live console: bidirectional root shell (see `LIVE-DEBUG-CONNECTIVITY.md`) — the console
was used to run the whole acceptance suite *while the animation played*.

## What went wrong — and it was ours, in the diagnostic, not in the boot

The operator's observation window was damaged by our own instrumentation:

1. `dd if=/dev/fb0 …` (to sample framebuffer pixels) **released the DECON**:
   `decon_release + : 0`, then **1279** × `decon_pan_display: decon0 state(6), UNBLANK missed`
   from t=321 s. `echo 0 > /sys/class/graphics/fb0/blank` re-enabled the panel
   (`panel_power_on panel_state:OFF -> ON`, `decon_enable - (state:OFF -> ON)`,
   `FRAME_DONE … display on`) but only re-enabled it — every pan kept failing until a
   `FBIOPUT_VSCREENINFO` was issued.
2. A second short-lived `nuxel-anim-player` instance (used to force that re-enable)
   closed its fb fd on exit, releasing the DECON again.

So the panel was correct from t≈7.5 s to t≈321 s (five minutes), and then intermittently
blank afterwards **because of our own reads, not because of the candidate**. Any
conclusion about the colours must come from the first five minutes, or from A22.

## Why A22 is the justified next candidate (not a blind repeat)

| A21 defect found | A22 change |
|---|---|
| A failed `FBIOPAN_DISPLAY` was ignored forever | the player now re-issues `FBIOBLANK(UNBLANK)` + `FBIOPUT_VSCREENINFO` on the first failed pan and every 240 frames unconditionally; it logs `NUXEL_ANIM_PAN_FAILED_TOTAL`, `NUXEL_ANIM_PAN_LAST_RC`, `NUXEL_ANIM_PAN_REASSERTED` |
| No way to settle the panel's channel mapping visually | opt-in `--colourtest[=secs]`: five bars (pure red, green, blue, white, black) packed with the driver's bitfields, plus logged expected/read-back u32 values |
| Stale `fb-hold.pid`/`fb-anim.pid` from a previous boot could mislead | `init.sh` clears them at boot |

`fb-anim.pid=3500` and `fb-anim-ready` are also the first proof that the state files,
the ownership handshake and the takeover subsystem now work on the Fedora rootfs rather
than silently landing in the deleted initramfs root (which is what A20 did).

## Standing corrections to the record

1. **A20's "no /proc" was not a switch_root race.** It was `O_DIRECTORY = 040000` on this
   board: `0x10000` is `O_DIRECT`, and **procfs returns `EINVAL` for `O_DIRECT`**.
   Measured three ways (kernel header, glibc header, and on the handset:
   `openat(/proc,040000)=3` vs `openat(/proc,0x10000)=-1 errno=22`).
2. **Every numeric evidence line this project ever captured was corrupt.** `wrn/wru/wrh`
   advanced a cursor past the tag without copying it, so `"  xres=1440"` reached the log
   as `\0\0\0\0\0=1440` (hexdump of a live run). All geometry, `READBACK_*`, pid and
   return-code lines were unreadable. Fixed, and every A21 value above is legible.
3. **`--secs` and `--stopfile` were never parsed** (`klen` compared 4 and 8 against 5),
   so the player's only graceful stop mechanism was dead code.
4. **`fb_release` blanks the panel.** Opening and closing `/dev/fb0` disables the DECON;
   only `FBIOPUT_VSCREENINFO` restores it. This affects `nuxel-hwprobe`, `nuxel-diag`,
   `show_boot_splash()` and any future tool, and it is the likely cause of earlier
   "the panel is black" observations that were attributed to renderer bugs.

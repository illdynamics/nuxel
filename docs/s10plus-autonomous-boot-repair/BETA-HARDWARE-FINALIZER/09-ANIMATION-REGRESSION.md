# 09 — BOOT ANIMATION AND DISPLAY REGRESSION

**Status: ownership verified clean; the reported “second half of the animation became
the static wallpaper” was reproduced from timing evidence and fixed; the fix is
deployed and will be verified on the next boot (see 11).**

## 1. What the user reported

> “the first 2 seconds of the boot animation is right, the second part of the boot
> animation is now changed to the static wallpaper, change it back to the animation”

## 2. What the evidence showed

Boot timeline from the handset’s own kmsg/journal:

```
[    2.290413] nuxel-init: FIRSTLIGHT asset present: /opt/nuxel/nuxel-firstlight.rawspl (NUXSPL01 = animation frame 0)
[    2.394901] NUXEL_FIRSTLIGHT_FRAME0_PAINTED nuxspl=animation-frame0
[    2.883886] NUXEL_ANIM_PLAYER start
[    2.883938] /newroot/usr/share/nuxel/boot/nuxel-animation.nux
1789430403    NUXEL_HOME_READY uri=http://127.0.0.1:8000/pwa/nuxel-home/index.html?boot=os
```

The animation container is 192 frames at 24 fps = **8.0 s** (verified with ffprobe, and
the pack’s own report: `frames: 192, fps: 24, psnr 38.2 dB`), and the launcher committed
its page only ~2–3 s after the player’s first frame.  The bridge’s hand-off then fired
immediately (`ANIMATION_STOP_REQUESTED → ANIMATION_STOP_CONFIRMED →
LAUNCHER_DISPLAY_OWNER`), i.e. **the animation was cut at roughly a quarter of its
length and the launcher’s static wallpaper took over** — precisely the reported symptom.
A previous boot in the same log shows the opposite case (the animation looping
`NUXEL_ANIM_LOOP=3/4` for ~30 s) when the launcher happened to be late, which is why the
symptom looked intermittent.

## 3. The fix (in the display bridge, not in the BOOT image)

`nuxel-wl-fb.c` (A32) now waits for the animation to complete at least
`NUXEL_ANIM_MIN_LOOPS` (default **1**) full cycles before it requests the stop:

* the loop count is read from the player’s own kmsg markers
  (`NUXEL_ANIM_LOOP=<n>`, `NUXEL_ANIM_HEARTBEAT_LOOPS=<n>`) via `/dev/kmsg`, which keeps
  its own read position per file descriptor and does not consume records for other
  readers — so the bridge learns the true progress instead of guessing from a timer;
* the wait is bounded (`NUXEL_ANIM_MIN_WAIT`, default 24 s) and aborts early if the player
  exits by itself, so a missing player can never delay the launcher forever;
* the verdict is published (`/run/nuxel-anim-stop.confirmed`,
  `ANIM_MIN_CYCLE_RESULT loops=… target=…`) and the state file records it;
* `NUXEL_ANIM_MIN_LOOPS=0` restores the old behaviour for A/B measurement.

The player itself is **not** modified: it lives in the initramfs (BOOT partition) and the
mission forbids rebuilding BOOT for a userspace policy problem.

## 4. Ownership and flicker checks (unchanged by this cycle, re-verified)

| Requirement | Evidence |
|---|---|
| one framebuffer owner at a time | `pgrep -cf nuxel-wl-fb` = 1, animation player gone after hand-off (`ANIM_OWNER=nuxel-wl-fb`) |
| animation stops before the launcher writes | the bridge performs **no** scanout write before `ANIMATION_STOP_CONFIRMED` (A31 rule, kept) |
| stop acknowledgement real | `/run/nuxel-anim-stop.confirmed` = `ANIMATION_STOP_CONFIRMED`, `/var/lib/nuxel/fb-owner` ends with `LAUNCHER_DISPLAY_OWNER` |
| stale pages cleared | full-frame write of every pixel after `panel_assert("post-stop")` |
| no second PWA splash | `NUXEL_HOME_BOOT_OWNER os_animation=1`, `splash=absent` at t1s/t4s/t9s |
| no periodic display reconfiguration | no `FBIOPUT_VSCREENINFO`/`FBIOPAN_DISPLAY` in the steady loop (A31); panel re-asserted only on measured capture failures |
| no second framebuffer client | `nuxel-ui.service` is skipped by condition while the bridge is present; `nuxel-fallback.service` only runs if the launcher never becomes ready |

# 05 — FLICKER, BLEED-THROUGH AND THE SECOND BOOT ANIMATION (P4 / mission §9)

There were **two independent problems** behind "animation frames appear through
the launcher" and "the boot animation flickers", and they have different fixes.

## A. Two processes painting the same scanout memory (the real flicker)

Measured on the handset at the start of this cycle:

```
ps -eo pid,pcpu,comm --sort=-pcpu
  5436 nuxel-wl-fb        65.6%
  3523 nuxel-anim-player  42.2%   --stopfile=anim-stop
/var/lib/nuxel/anim-stop            ABSENT
/var/lib/nuxel/animation            ANIM_STAGE=MP4_PLAYER_ACTIVE
```

The initramfs MP4 player loops until `/var/lib/nuxel/anim-stop` appears; the A27
`nuxel-ui.c` used to write that file, and the A29 launcher path replaced
`nuxel-ui` without taking the job over. So the player ran forever while
`nuxel-wl-fb` also wrote `/dev/fb0` → the panel alternated between an animation
frame and a launcher frame. That is the flicker/bleed-through.

Fix: the deployed bridge is now the A30/A31 single-owner handoff (doc 06), which
requests the stop by file, waits for **proof of termination**, and only then
writes scanout memory. Verified live after deploy:

```
/var/lib/nuxel/animation        ANIM_STAGE=ANIMATION_STOPPED  ANIM_OWNER=nuxel-wl-fb
/var/lib/nuxel/anim-stop        PRESENT (ANIMATION_STOP_REQUESTED)
/run/nuxel-anim-stop.confirmed  PRESENT (ANIMATION_STOP_CONFIRMED)
pgrep -f nuxel-anim-player      -> nothing
pgrep -f nuxel-wl-fb | wc -l    -> 1
```

## B. The PWA's own fullscreen splash was a second animation (mission §9)

`pwa/nuxel-home/index.html` contains

```html
<div id="boot-splash" aria-hidden="true">
    <video id="boot-splash-video" src="assets/nuxel-boot-animation.mp4"
           muted autoplay playsinline loop preload="auto"></video>
</div>
```

and `css/style.css:248` gives it `position:fixed; inset:0; z-index:99999`. On the
phone the OS has already played the authoritative animation from the initramfs,
so this is a **redundant second animation**: it can flash over the launcher, and
while it is present it is an opaque `pointer-events:auto` layer above the app
grid. `js/app.js _finishBootSplash()` only dismisses it after ~3 s of playback,
with a 12 s safety timeout — and on this image media is disabled
(`NUXEL_HOME_MEDIA enable_media=0`), so the fallback path is the timer.

### Ownership policy implemented (launch-mode signal, VM untouched)

* The phone host appends a launch-mode parameter: the launcher is opened as
  `…/pwa/nuxel-home/index.html?boot=os`
  (`NUXEL_HOME_BOOT_OWNER os_animation=1 splash_removed_by_launcher=1`).
* `pwa/nuxel-home/js/app.js` treats `boot=os` as "the OS owns the animation" and
  **removes `#boot-splash` from the DOM** (not merely fades it), then marks the
  body ready. Removal is deliberate: a faded element with `z-index:99999` can
  still intercept input.
* Any other launch mode (the UTM VM, desktop) has no such parameter and keeps the
  original splash behaviour exactly as before — nothing was deleted globally.
* `NUXEL_PWA_SPLASH=1` restores the PWA's own splash on the phone for debugging.

Verified live: `NUXEL_HOME_READY uri=…index.html?boot=os`, and the injected
observer reports `splash=absent` in the real document (doc 07).

## C. What is *not* claimed

The two MP4-derived animations are not unified into a single asset — the
initramfs player is the authoritative boot animation and the PWA never starts a
second one on this device. Frame timing is now bounded and measurable
(`fps_1s=28`, `blit_avg_ms=34`, `failures=0`), but the *visual* smoothness on the
glass is confirmed by the user, not by a software marker.

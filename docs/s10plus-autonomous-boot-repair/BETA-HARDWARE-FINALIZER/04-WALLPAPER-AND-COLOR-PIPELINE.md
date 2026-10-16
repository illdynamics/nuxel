# 04 — WALLPAPER AND COLOUR PIPELINE

**Status: asset verified, path verified, a real channel-order bug found and fixed in
the display bridge, verified numerically (unit test) and by live state; the visual
confirmation is the user’s.**

## 1. The asset and its path (mission 8.1) — already correct, now asserted

| Check | Value |
|---|---|
| Authoritative asset | `assets/nuxel-background.png`, sha256 `6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29` |
| Served copy | `/usr/share/nuxel/nuxel-home/assets/nuxel-background.png` — **same sha256** |
| CSS reference | `css/style.css`: `background-image: url('../assets/nuxel-background.png')` → resolves to the served copy |
| HTTP | `GET /pwa/nuxel-home/assets/nuxel-background.png` → `200 image/png`, `Content-Length 1257938` |
| Browser | the launcher’s own observer reports `wallpaper url=… decoded=1 natural=941x1672` |
| Repo guard | `tools/s10plus/a32/tests/wp.py` asserts both hashes and the CSS reference |

Nothing was re-generated or re-designed; the same file is used by the VM.

## 2. The colour bug that was really there (mission 8.2)

The compositor hands `nuxel-wl-fb` its screencopy buffer as
`WL_SHM_FORMAT_XRGB8888` (in-memory `0x00RRGGBB`), and A29–A31 copied those words
into scanout **unchanged**.  This panel’s DECON maps `R@0 G@8 B@16` (ABGR_8888) — the
order the boot-animation player itself overrides to, and logs:

```
NUXEL_ANIM_FB_RED_OFF=16 … NUXEL_ANIM_HW_ORDER_NAME=abgr8888 R@0 G@8 B@16 A@24
NUXEL_ANIM_HW_DECON_FMT_NAME=DECON_PIXEL_FORMAT_ABGR_8888
```

Copying XRGB8888 words into that memory therefore **swapped red and blue** on the
glass.  The same class of defect produced the “red background with circuitry”
photograph in A20; this time it was live in the launcher path, which is why the
palette and wallpaper “did not match expectations”.

### Fix

`nuxel-wl-fb.c` (A32) now converts explicitly, for every pixel, from the format the
compositor actually offers to the order the panel actually uses:

```c
cv_lo[x] = ((x & 0xff) << 16) | (x & 0xff00) | 0xff000000;  /* G stays, B -> 16..23, alpha=0xff */
cv_hi[x] = (x & 0xff);                                      /* R -> 0..7 */
dst = cv_lo[v & 0xffff] | cv_hi[v >> 16];
```

* the applied order wins over `fb_var` (which the driver never programmes), logged as
  `COLOR_ORDER declared=R@16 G@8 B@0 applied=R@0 G@8 B@16 … override=1(decon_abgr8888)`;
  `NUXEL_WLFB_FBVAR_ORDER=1` restores the old behaviour for A/B measurement;
* alpha is forced to `0xff` on every published pixel — the DECON does not blend, so a
  transparent shm pixel must never reveal the previous frame (that is also the
  “animation bleeding through the launcher” mechanism);
* unknown source formats are **logged and refused** rather than silently mis-converted.

### The unit test caught a real bug in the fix

`nuxel-wl-fb --colour-selftest` (run offline, on the aarch64 UTM guest) tests the four
primaries plus alpha.  The first version of my lookup tables dropped the green channel
(`red 0x00ff0000 → 0xff000000`), which the test failed; after the correction:

```
PASS red   src=0x00ff0000 got=0xff0000ff want=0xff0000ff
PASS green src=0x0000ff00 got=0xff00ff00 want=0xff00ff00
PASS blue  src=0x000000ff got=0xffff0000 want=0xffff0000
PASS white src=0x00ffffff got=0xffffffff want=0xffffffff
PASS black src=0x00000000 got=0xff000000 want=0xff000000
PASS alpha forced opaque on every channel pattern
```

This is exactly why the mission forbids “it compiles” as evidence.

### Live verification (no image analysis)

```
$ cat /run/nuxel-wl-fb.state
1789430578 FRAMES_OK total=3796 fps_1s=24 failures=0 blit_avg_ms=40 out=720x1520
           src=720x1520 scale=2 panel=1440x3040 owner=nuxel-wl-fb display=on
           src_format=0x00000001 colour=R@0,G@8,B@16_abgr8888_override=1
```

`src_format=0x00000001` is `WL_SHM_FORMAT_XRGB8888`, i.e. the conversion path is the
live one; 24 fps sustained with the extra per-pixel work (40–43 ms/frame vs 35 ms
before).  Cost is acceptable and bounded; no periodic `FBIOPUT_VSCREENINFO` was added.

## 3. Opaque, animation-free background (mission 8.3)

* The launcher’s `body` has an explicit `background-color` **and**
  `background-image` — a fully defined static background in every state.
* `nuxel-wl-fb` writes every destination pixel of every frame (no partial writes, no
  double-buffer panning), so no stale animation page can remain visible.
* The bridge refuses to write anything before the animation stop is *confirmed*, and
  A32 additionally lets the animation finish at least one full cycle first (see 09).
* The PWA’s own boot splash is removed for the phone launch mode (`?boot=os`), reported
  in the state file as `splash=absent` at t1s/t4s/t9s, so no second video can flash over
  or intercept input.

**P3 verdict:** implemented, offline-tested, deployed and measured on the device;
“correct colour appearance” is declared only after the user’s visual confirmation.

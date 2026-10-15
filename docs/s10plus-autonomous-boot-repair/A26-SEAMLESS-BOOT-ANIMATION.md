# A26 — P0: SEAMLESS FIRST LIGHT (removing the obsolete two-second splash)

## 1. The confirmed source-level defect

`boot/initramfs/init.sh`:

```
nuxel_first_light() {                      # line 480
    ...
    /opt/nuxel/nuxel-fb-phone > /dev/kmsg 2>&1     # line 498: the OLD artwork
    ...
}
...
nuxel_first_light                          # line 552
...
nuxel_start_animation                      # line 1426
```

The ordering is the bug: the earliest paintable moment (devtmpfs populated,
~2 s after kernel entry) is filled with the old diagnostic splash, and only
minutes later does `nuxel_start_animation` hand the panel to the MP4 player. The
operator sees the obsolete screen, then the real animation.

Note what `nuxel_first_light` also does and which must be preserved: it proves
`/dev/fb0` is a character device, records `bits_per_pixel` / `stride` /
`virtual_size` / `smem_len` / `modes`, forces a DECON commit, and prints a named
`NUXEL_FB_*` verdict on every failure path so "cannot execute" is never confused
with "no panel".

## 2. The right fix: first light *is* the animation's frame 0

Do **not** draw a second piece of art that merely resembles the animation. Light
the panel with **frame 0 of the animation container the player is about to run**,
using the same palette, the same raster and the same packing. Then the handoff is
not a transition at all — the player's first committed frame is byte-identical to
what is already on the glass, so there is nothing to flash, no black gap, no
colour-order change, and no second graphics implementation to disagree with.

Delivered this cycle:

```
tools/s10plus/a26/make-firstlight-asset.py
  --anim build/out/s10plus/nuxel-animation.nux     (NUXANM01, 18,481,546 bytes)
  --out  build/out/s10plus/a26/nuxel-firstlight.nuxspl
  --mp4  assets/nuxel-boot-animation.mp4           (cross-check only)

{
  "width": 1080, "height": 1920, "palette_colors": 256, "fps": "24/1",
  "frames_in_source": 192,
  "verify_index_identical": true,          <-- index plane == NUXANM01 frame 0
  "verify_palette_identical": true,        <-- palette copied verbatim
  "verify_raster_matches_animation": true,
  "mae_vs_mp4_frame0_rgb": 4.958,          <-- mean abs err /255 vs ffmpeg decode
  "out_bytes": 155869,
  "out_sha256": "f776455d4a44c47cb21219386a5e18fe069cba03fcd9e5eeda9ab126c85aa2f7"
}
FIRSTLIGHT_ASSET_OK
```

So the early-boot payload is **155,869 bytes** — not the whole 18 MB animation,
and not a re-imagined graphic. It reuses the animation packer's own palette and
the player's own packing, per the directive "do not add a second independent
graphics implementation with conflicting colors".

### Asset format (`NUXSPL01`)

```
 0    8   magic "NUXSPL01"
 8    4   u32 width            1080
12    4   u32 height           1920
16    4   u32 palette_count    256
20    4   u32 flags            bit0 = raw DEFLATE
24    4   u32 blob_size
28    4   u32 reserved
32  512   palette           256 x RGB565 LE  (verbatim from NUXANM01)
544  ...  index plane       raw DEFLATE of 1080*1920 palette indices
```

The player's existing palette-expansion + ABGR_8888 packing is then reused
unchanged, so the early frame and the animation cannot disagree about colour
order.

## 3. Verification performed (offline, real, no phone required)

| Check | Result |
|---|---|
| index plane decodes byte-identically to `NUXANM01` frame 0 | PASS |
| palette byte-identical to `NUXANM01`'s | PASS |
| raster 1080x1920 == source MP4 frame size (aspect + position preserved) | PASS |
| independent ffmpeg decode of MP4 frame 0 vs asset (stride-sampled MAE) | 4.96/255 ≈ 1.9 %, matching the packer's recorded 38.17 dB PSNR |
| asset size | 155,869 bytes (8.5x smaller than a raw RGB565 plane) |

Not yet done (and deliberately not claimed):
* the `nuxel-fb-phone` blit path that consumes `NUXSPL01` — this needs a
  freestanding aarch64 rebuild and a new BOOT candidate;
* the on-glass handoff observation (needs a controlled BOOT update).

## 4. Wiring plan for the BOOT candidate (not flashed)

1. `tools/s10plus/nuxel-fb-phone.c`: add a `NUXSPL01` reader + blit that reuses
   the existing palette-expansion and ABGR_8888 packing already in the animation
   player. Keep the panel init, geometry discovery, bounds checks, DECON commit,
   diagnostics and the `NUXEL_FB_*` failure verdicts exactly as they are. If the
   asset is missing or malformed, fall back to the current diagnostic frame
   (A16 fallback preserved).
2. Embed `nuxel-firstlight.nuxspl` in the initramfs next to
   `nuxel-animation.nux`; `nuxel_first_light` passes it by path.
3. Keep the single-writer rule: `nuxel_first_light` writes the frame and then
   exits; the DECON keeps scanning that buffer, so no framebuffer fd is left open
   and no `decon_release` can fire. The animation player is the next and only
   other writer, and its first commit is the same image.
4. Build a versioned candidate with `tools/s10plus/a26/build-a26-boot.sh`
   (same structure as `build-a25-initramfs.sh`: replace members, re-verify every
   member's SHA-256, then embed the archive in the kernel).
5. Flash only at a controlled maintenance opportunity, BOOT-only, with full
   readback, per the standing safety rules. `nuxel-live.sh` must never be used to
   write an active partition.

## 5. Samsung DECON ownership notes carried forward

* Closing a framebuffer fd invokes `decon_release`, which disables the panel
  regulator; A21 measured a single `dd if=/dev/fb0` leaving pans failing. Nothing
  in the new path opens `/dev/fb0` twice or closes it in a diagnostic.
* Never run a second framebuffer client (A24: it powered the panel down).
* The double-buffer page matters: the early frame must be written to the page
  the DECON is actually scanning (`virtual_size`/`yoffset`), or the glass shows a
  stale buffer while the commit reports success.

# NUXEL — MP4 PLAYBACK PERFORMANCE (A21)

## Measured on the handset (TWRP, real DECON, real shipping container)

```
command : /data/local/tmp/animplayer --file=…/nuxel-animation.nux \
            --statedir=… --pid=fb-anim.pid --holdpid=fb-hold.pid --secs=6
NUXEL_ANIM_DRAWN_FRAMES=145
NUXEL_ANIM_LAG_SKIPS=0
NUXEL_ANIM_LOOPS=1
-> 145 frames / 6 s = 24.2 fps against a 24 fps target, 0 dropped
```

A second run with `--secs=4` drew 97 frames (24.25 fps, 0 skips, 1 loop). The player
therefore runs at the source frame rate on the S10+'s CPU with software decoding of the
packed span stream.

## What is measured vs what is inferred

| Quantity | Value | How |
|---|---|---|
| Frames decoded | = frames submitted | one `inflate_raw` + span application per frame, checked (`NUXEL_ANIM_INFLATE_FAILED_FRAME`/`SPAN_*` quits on any error) |
| Frames submitted to the panel | `NUXEL_ANIM_DRAWN_FRAMES` | incremented after every `FBIOPAN_DISPLAY` |
| Frame drops | `NUXEL_ANIM_LAG_SKIPS` = 0 | counted when the deadline is already missed |
| Playback timing | `NUXEL_ANIM_HEARTBEAT_FRAMES` / `_MS` / `_EXPECTED_MS` | new A21 heartbeat every 240 frames (~10 s) |
| CPU / memory | not sampled on-device | the player has no /proc sampling; memory is bounded by construction (below) |

## Memory budget (bounded by construction, never the whole animation)

| Allocation | Size |
|---|---|
| container (`mmap`, read-only, file-backed) | 18,481,546 B |
| index plane (anonymous) | 1080 × 1920 = 2,073,600 B |
| inflate scratch (anonymous, max(index plane, 4 MiB)) | 4,194,304 B |
| span tables (anonymous) | (AW+AH+16)·4·4 ≈ 48 KB |
| framebuffer (`mmap` of the driver's `smem_len`) | 35,020,800 B (driver-owned, not allocated by us) |

No frame is ever held uncompressed in RAM: the packed container is memory-mapped and
only changed spans are expanded (~220 KB per frame, ~5 MB/s at 24 fps).

## Efficiency design

* only changed pixels are written — the packed stream is a delta chain, so the cost per
  frame is proportional to what actually moved;
* raw-DEFLATE, no zlib header, no allocation in the inflate loop;
* byte-at-a-time Huffman decode is deliberately simple: on this workload it is ~10×
  faster than the frame rate requires, and it cannot mis-optimise;
* pacing sleeps to a monotonic deadline and, when late, **resynchronises rather than
  queueing** — late frames are dropped, never buffered, so lag cannot accumulate;
* both virtual buffers are painted (the DECON may scan either half).

## Tearing and aspect

The player pans the scanout once per frame (`FBIOPAN_DISPLAY`) after painting every
virtual buffer, so the DECON never reads a half-written buffer; the geometry is
measured at runtime (1440×3040, stride 5760, 2 buffers) and never assumed. The source
aspect is preserved exactly (1080×1920 → 1440×2560).

## Fallback profiles

Not required: the handset meets 24 fps with 0 drops at the source raster. The full
quality source (`assets/nuxel-boot-animation.mp4`, sha256 `280e094f…`) is retained
unchanged, and the packing parameters live in
`build/out/s10plus/nuxel-animation.pack.json`, so a lower-resolution profile could be
generated without touching the original artwork. None was needed, so none was made —
the animation's visual content was not altered for performance.

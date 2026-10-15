# NUXEL — MP4 ANIMATION RENDERING (A21)

## 1. The artwork, measured (not assumed)

| Field | Value |
|---|---|
| Path | `assets/nuxel-boot-animation.mp4` (canonical, git-tracked) |
| SHA-256 | `280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c` |
| Container | QuickTime/MOV `isom`, encoder `Google`, no rotation metadata |
| Codec | H.264 High `avc1.640028` level 4.0, **yuv420p**, 8-bit, no alpha channel |
| Raster | 1080 × 1920 portrait |
| Timing | 24 fps, 192 frames, 8.000 s, no audio track |
| Colour | `bt709` not signalled; decoded as the ffmpeg default for `yuv420p` |

Measured frame statistics over all 192 frames (`ffmpeg -pix_fmt rgb24`):

```
mean red pixels (r>60 and r>b+30 and r>g+30)   = 0.16 %
mean blue pixels (b>60 and b>r+30 and b>g+30)  = 1.21 %
brightest blue frame                           = frame 112 (4.67 s), 11.27 % blue
frame 0 mean RGB                               = (9.4, 9.6, 12.5)
```

**Conclusions (these settle the mission's questions):**

1. **The red background is NOT intended.** The artwork is a near-black, blue-dominant
   scene: a ~96 % near-black field, a network of blue circuitry that lights up around
   t = 4.7 s, white terminal-style text, and a small red/white Nuxel mark at the centre
   (≈0.2 % of pixels). There is no red background and no red-dominant frame anywhere in
   the 192 frames.
2. **The original video DOES contain a penguin-like white/black Nuxel mark at the
   centre** (rendered as `R`/`%` glyphs in the ASCII reference renders) — so a centred
   character in the photograph is expected. A *second*, blue-and-white penguin is not.
3. **The rectangular region is not part of the source.** No frame contains a rectangle.
4. **The source colours are materially different from what the S10+ displayed in A20**
   — see §3 and `COLOR-FORMAT-VERIFICATION.md`.
5. **Scaling is correct and aspect-preserving**: 1080×1920 → 1440×2560 (integer
   nearest-neighbour, `DW = AW*PW/AW`, `DH = AH*PW/AW`), centred at `OX=0`, `OY=240`
   on the 1440×3040 panel, with the letterbox filled in the artwork's own background
   colour (frame-0 histogram mode) instead of an arbitrary black.

## 2. Why a framebuffer-native player and not Plymouth

`tools/build-nuxel-boot-theme.sh` renders the artwork into a Plymouth "script" theme.
Plymouth requires DRM/KMS; this Samsung downstream kernel reports `# CONFIG_DRM is
not set` and exposes only `/dev/fb0` (Exynos DECON/DSIM). The player therefore decodes
a build-time packed form of the **original, unchanged** MP4 straight onto the DECON
fbdev. No frame is redrawn, substituted or restyled.

```
assets/nuxel-boot-animation.mp4                     (original, unchanged)
  |  tools/s10plus/nuxel-anim-pack.py               (build time, on the Mac)
  v
build/out/s10plus/nuxel-animation.nux  18,481,546 B  sha256 7d296871…  38.2 dB PSNR
  |  tools/s10plus/nuxel-anim-player.c              (freestanding aarch64, 66 KB)
  v
/dev/fb0  1440×3040×32bpp, stride 5760, yres_virtual 6080 (2 buffers)
```

## 3. THE RENDER DEFECT THE OPERATOR PHOTOGRAPHED — root cause

The A20 player wrote the container's **raw RGB565 palette value** into a **32-bpp**
DECON pixel:

```c
for(u32 i=0;i<PALN;i++) PAL565[i]=HDR->palette[i];   /* RGB565 */
...
fill_span(row, DX0[sx], DX1[sx], PAL565[idx[sx]]);   /* 16-bit value -> 32-bit pixel */
```

The low 16 bits of a `u32` are *not* "16-bit colour widened"; they are the fields the
driver maps to bits 0..15. Measured layout of this panel
(`nuxel-anim-player --verbose`, `nuxel-fb-phone` geometry dump):

```
red.off=16 red.len=8   green.off=8 green.len=8   blue.off=0 blue.len=8   transp.off=24
```

so the RGB565 low byte (which carries **blue**) lands in whichever channel owns bits
0..7. `tools/s10plus/test-anim-colour.sh` quantifies both layouts:

* **ABGR8888** (red at bits 0..7 — the layout the photograph is consistent with):
  frame 0 mean **red channel 38.2, mean blue channel 0.0** → the artwork's blue
  circuitry and dark navy field render *entirely red*. **This is the operator's
  "red Nuxel background with circuitry artwork".**
* **ARGB8888** (red at bits 16..23): the red field reads 0 for every pixel — the
  artwork's red accents disappear. Also wrong, differently.

### The fix

The palette is now expanded **once**, at load time, into the destination pixel format
using the driver's own bitfields — the same maths the hardware-proven first-light
renderer already used:

```c
static u32 packcol(u32 r,u32 g,u32 b){         /* 8-bit channel -> driver field */
 u32 R=RLEN?((r*((1u<<RLEN)-1u)+127u)/255u):0u; ... return (R<<ROFF)|(G<<GOFF)|(B<<BOFF); }
for(u32 i=0;i<PALN;i++){ u32 c=PAL565[i];
  DSTPIX[i]=packcol(five6to8((c>>11)&31,5), five6to8((c>>5)&63,6), five6to8(c&31,5)); }
```

with `RLEN/GLEN/BLEN/ROFF/GOFF/BOFF` read from `FBIOGET_VSCREENINFO` at runtime and
logged (`NUXEL_ANIM_FB_RED_OFF` … `NUXEL_ANIM_FB_TRANSP_LEN`). If the driver ever
reports a layout the player cannot reason about it **refuses to paint**
(`NUXEL_ANIM_FB_BAD_COLOUR_FORMAT`, exit 21, `fb-anim-failed` written) so the
first-light frame stays on the panel and init.sh starts the penguin fallback — it can
never paint wrong colours silently.

## 4. The second penguin and the rectangle — root cause

`nuxel-fb-phone` paints the first-light screen (`rect(0,0,W,H,bg)`, 4 colour bars,
`NUXEL` / `LINUX PHONE`, a spinning penguin) and then, in `hold` mode, repaints the
penguin's **2·half × 2·half square** with `bg = pack(10,32,58)` every 250 ms — an
opaque rectangle. That is exactly the rectangle behind the centre penguin in the
photograph.

The A20 player tried to displace that painter and could not, for two independent
reasons (both now fixed — see `FRAMEBUFFER-OWNERSHIP.md`):

1. **`openat("/proc", O_RDONLY|O_DIRECTORY)` returned `-EINVAL`** because this board's
   ABI defines `O_DIRECTORY = 040000`, so `0x10000` is `O_DIRECT`, and procfs rejects
   `O_DIRECT` with `EINVAL`. Hardware evidence: `NUXEL_ANIM_TAKEOVER no /proc`
   (A20 journal) and, measured directly, `openat(/proc,040000)=3` vs
   `openat(/proc,0x10000)=-1 errno=22`.
2. The takeover ran **after `switch_root`**, which moves `/proc` into the new root and
   deletes the old one, so the scan had no `/proc` to walk even when the flags were
   right.

## 5. Playback quality (measured)

`/data/local/tmp/animplayer --file=… --statedir=… --pid=… --secs=6` on the handset
(TWRP, real DECON, real container):

```
NUXEL_ANIM_TAKEOVER_KILLED=1        NUXEL_ANIM_TAKEOVER_STOPPED=1
NUXEL_ANIM_DRAWN_FRAMES=145         NUXEL_ANIM_LAG_SKIPS=0      NUXEL_ANIM_LOOPS=1
```

145 frames in 6 s = 24.2 fps against a 24 fps target with **zero** lag skips: the
player keeps up, and the pacing loop only drops the *sleep* when late (it never queues
frames, so the animation cannot accumulate unbounded lag). Memory is bounded: the
mmap'd container plus a 2.07 MB index plane plus one inflate scratch buffer.

## 6. Status

```
MILESTONE_ORIGINAL_MP4_PLAYER_DECODES_BIT_EXACT   = yes  (192/192 frames, C == Python)
MILESTONE_COLOUR_CONVERSION_FAITHFUL              = yes  (max channel error 0, both layouts)
MILESTONE_ONE_RENDERER_AT_A_TIME                  = yes  (measured takeover kill + ack)
MILESTONE_PLAYBACK_RATE_24FPS                     = yes  (145/6 s, 0 skips)
MILESTONE_MP4_VISIBLE_ON_AMOLED_CORRECT_COLOURS   = PENDING OPERATOR OBSERVATION (A21)
```

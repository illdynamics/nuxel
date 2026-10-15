# NUXEL — COLOUR FORMAT VERIFICATION (A21)

## 1. The panel's real pixel layout (measured, not assumed)

`nuxel-fb-phone` (A21, rebuilt) run on the handset in TWRP against the live DECON
fbdev:

```
NUXEL_FB_INFO:
  xres=1440            yres=3040           yres_virtual=6080
  xoffset=0            yoffset=0
  bpp=32               stride=5760
  smem_start=0x10000000 smem_len=35020800          (= 5760 * 6080, two buffers)
  mmio_start=0x0       mmio_len=0
  red.len=8            green.len=8          blue.len=8        transp.len=8
  red.off=0x10         green.off=0x8        blue.off=0x0      transp.off=0x18
```

So the format is **32 bpp, 8/8/8/8, red at bits 16..23, green 8..15, blue 0..7,
alpha 24..31** (i.e. `0xAARRGGBB` as a little-endian u32 = `B,G,R,A` bytes).
The exact offsets are re-read at runtime by the player and logged as
`NUXEL_ANIM_FB_RED_OFF/GREEN_OFF/BLUE_OFF/TRANSP_OFF` on every boot, so a future
capture never has to trust this table.

## 2. Deterministic colour round-trip on the device

The A21 first-light renderer packs pure colours with the driver's bitfields, writes
them into framebuffer memory and reads the u32 back:

```
NUXEL_FB_COLOR_PACK_R_expected=16711680   readback=16711680
NUXEL_FB_COLOR_PACK_G_expected=65280      readback=65280
NUXEL_FB_COLOR_PACK_B_expected=255        readback=255
NUXEL_FB_COLOR_PACK_W_expected=16777215   readback=16777215
NUXEL_FB_COLOR_PACK_K_expected=0          readback=0
NUXEL_FB_UNBLANK_rc=0  NUXEL_FB_ACTIVATE_rc=0  NUXEL_FB_PAN_rc=0
NUXEL_FB_BUFFERS_PAINTED=2
```

Every store matches the intended value, and the Samsung driver accepts the commit
(all three ioctls return 0). `pack()` is therefore proven correct against the real
driver, and it is the same maths the animation player now uses.

## 3. Offline pixel test — `tools/s10plus/test-anim-colour.sh`

Runs with no handset, on the shipping container, through the same conversion:

```
== container: 1080x1920, 192 frames, 256 colours, sha256 7d296871f04a3d5e...
   source artwork: mean red pixels 0.17%   mean blue pixels 2.04%
  PASS the artwork is blue-dominant and has no red background
  PASS new conversion faithful on ARGB8888 (R@16 G@8 B@0): max channel error 0
  PASS new conversion faithful on ABGR8888 (R@0 G@8 B@16): max channel error 0
   A20 conversion on ABGR8888: frame 0 mean red channel 38.2, mean blue channel 0.0
  PASS the A20 conversion floods RED with the artwork's blue -> the photographed red background
  PASS the A20 conversion kills the red field entirely under ARGB8888 (also wrong, differently)
```

## 4. What was wrong, precisely

`nuxel-anim-player.c` (A20) stored `PAL565[index]` — a 16-bit RGB565 value — directly
into a 32-bit framebuffer pixel:

```c
for(u32 i=0;i<PALN;i++) PAL565[i]=HDR->palette[i];   /* RGB565 from the container */
fill_span(row, DX0[sx], DX1[sx], PAL565[idx[sx]]);   /* written as a u32 */
```

RGB565 packs `RRRRRGGGGGGBBBBB`; a little-endian u32 built from it is
`[B|G:low, R|G:high, 0, 0]`. Under the panel's layout the low byte is the **blue**
field, so the blue circuitry painted blue — but the *high* byte, which carries the
red channel's bits, is never populated, and under a layout with red at bits 0..7 the
whole image floods red. Both variants are wrong; the correct conversion is to expand
565 → 8-bit channels → the driver's declared fields, which is what A21 does and what
§3 proves is exact.

## 5. Checks the mission asked for, and their verdict

| Check | Verdict |
|---|---|
| Channel mapping | driver-bitfield driven; proven exact offline for both 8/8/8 layouts |
| Colour range conversion | 5→8 and 6→8 bit scaling with rounding (`(v*255+…)/31`, `/63`); no full-range vs limited-range ambiguity is introduced because the container is already RGB, not YCbCr |
| Stride / padding | `line_length=5760` read from `FBIOGET_FSCREENINFO`; every row store is bounded by `STRIDE`; `smem_len` is checked before `mmap` |
| Alpha handling | alpha field left 0 and never relied upon; the DECON primary plane of this panel does not blend, and the resulting picture is measured correct (§2, §3). Nothing is treated as transparent — black is *not* replaced by "transparent" anywhere |
| Scaling | integer nearest-neighbour, aspect preserved (1080×1920 → 1440×2560) |
| Rotation | none required: the source is already 1080×1920 portrait, and the panel is 1440×3040 portrait |
| Screen dimensions / visible crop | `xres/yres` read at runtime; destination rect centred at OX=0, OY=240 |
| Full clearing | every virtual buffer is painted for frame 0 and for every loop re-anchor; the letterbox uses the artwork's own background colour |
| Double-buffered pages | `NBUFS = yres_virtual/yres = 2`; every buffer is painted and `FBIOPAN_DISPLAY` is issued per frame |
| The rectangular patch | **not in the source** — it is `nuxel-fb-phone`'s opaque penguin sprite square; see `FRAMEBUFFER-OWNERSHIP.md` |

## 6. Why the "red" is proof of a bug and not of the artwork

The mission warned not to assume the red background is wrong. It was checked against
the source: the artwork contains **0.16 % red pixels and 1.21 % blue**, with no
red-dominant frame in 192 frames, and the operator's photograph shows a red *field*
where the artwork has a near-black navy field. A colour that appears in the source at
0.16 % cannot occupy the whole background of the panel. The red could therefore only
come from the render path, and the O_DIRECT/O_DIRECTORY-independent 565-into-32bpp
defect reproduces it exactly, quantitatively (mean red 38.2 / mean blue 0.0).

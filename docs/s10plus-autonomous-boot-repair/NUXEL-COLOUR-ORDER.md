# NUXEL — THE PANEL'S TRUE COLOUR ORDER (A23, 2026-10-15)

```
STATUS              = PROVEN FROM THE KERNEL SOURCE (offline), corroborated by the A20 photograph
CONSEQUENCE         = A16..A22 packed every pixel with the WRONG channel order; A23 fixes it
HARDWARE PIXEL FMT  = DECON_PIXEL_FORMAT_ABGR_8888  ->  A[31:24] B[23:16] G[15:8] R[7:0]
BEFORE A23          = fb_var's DECLARED bitfields (red@16, green@8, blue@0) -> red and blue swapped
```

## 1. The contradiction in the driver

`drivers/video/fbdev/exynos/dpu20/decon_dsi.c` (the S10+/Exynos 9820 display driver in
`/b/k15`):

`decon_check_var()` — what `FBIOGET_VSCREENINFO` reports to userspace:

```c
case 32:
case 28:
case 25:
	var->transp.length	= var->bits_per_pixel - 24;
	var->transp.offset	= 24;
case 24:
	var->bits_per_pixel	= 32;
	var->red.offset		= 16;    <-- declares RED in bits 23..16
	var->red.length		= 8;
	var->green.offset	= 8;
	var->green.length	= 8;
	var->blue.offset	= 0;     <-- declares BLUE in bits 7..0
	var->blue.length	= 8;
```

`decon_pan_display()` — the **only** path that programs a DECON window for fbdev, i.e.
the actual commit that `FBIOPAN_DISPLAY` performs:

```c
switch (var->bits_per_pixel) {
case 16:
	config.format = DECON_PIXEL_FORMAT_RGB_565;   break;
case 24:
case 32:
	config.format = DECON_PIXEL_FORMAT_ABGR_8888; break;   /* line ~1208 */
```

The two are **mutually exclusive**:

| Declared | Programmed |
|---|---|
| red = bits 23..16 | `ABGR_8888` |
| blue = bits 7..0 | `ABGR_8888` |

`include/dt-bindings/display/exynos-display.h` numbers those formats in the DRM fourcc
order:

```c
#define DECON_PIXEL_FORMAT_ARGB_8888  0
#define DECON_PIXEL_FORMAT_ABGR_8888  1
#define DECON_PIXEL_FORMAT_RGBA_8888  2
#define DECON_PIXEL_FORMAT_BGRA_8888  3
#define DECON_PIXEL_FORMAT_XRGB_8888  4
...
#define DECON_PIXEL_FORMAT_RGB_565   13
```

In that naming (the same convention as `DRM_FORMAT_*`), `ABGR8888` is the 32-bit memory
word `A[31:24] B[23:16] G[15:8] R[7:0]` — the **least significant byte is red**. A
driver that reports red@16/blue@0 cannot be programming `ABGR_8888`; one of the two is
wrong, and the hardware registers win: `decon_reg_set_window_control()` writes the
window's FMT field from `config.format` on every pan, and `decon_set_par()` (the
`FBIOPUT_VSCREENINFO` path) never programs a format at all.

**Therefore: on this panel, bits 0..7 are RED and bits 23..16 are BLUE. `fb_var`'s
colour bitfields are unusable for packing, and any renderer that trusts them draws red
and blue in each other's place.**

## 2. Corroboration from the A20 photograph

A20 wrote the animation container's raw **RGB565** value straight into a 32-bpp pixel.
The artwork is near-black with **blue** circuitry (0.16 % red, 1.21 % blue pixels).
Taking the RGB565 value of a blue pixel, `b = 31` → word `0x0000001F`:

* fb_var-honest layout (blue@0) would put those 5 bits in the **blue** field → the
  operator would have seen dark blue circuitry;
* the hardware layout (red@0) puts them in **red** → blue circuitry appears red.

The operator photographed exactly that: *"red background with circuitry"*. The pixel
data, the operator's report and the register format all agree on one conclusion.

## 3. What A21/A22 got wrong, and why their evidence looked clean

A21/A22 fixed a *different* (real) bug: they stopped writing raw RGB565 words into
32-bpp pixels and expanded the palette through bitfields. Their on-device round-trip
test (`expected == readback` for red/green/blue/white/black) **passed** — because it read
back the *memory* they had just written. Memory round-trip can never observe how the
DECON maps memory onto the glass. That is precisely the class of question the
`--colourtest` A/B screen was designed to answer, and it is also exactly the question
section 4 of this document answers offline from the driver source.

## 4. The fix (A23)

Three binaries, one rule — build the pixel from the **hardware** format, not from
`fb_var`:

| File | Change |
|---|---|
| `tools/s10plus/nuxel-anim-player.c` | `if(HW_ABGR && BPP==32){ ROFF=0; GOFF=8; BOFF=16; RLEN=GLEN=BLEN=8; }` before the palette is built into `DSTPIX[]`; logs `NUXEL_ANIM_HW_ORDER_NAME=abgr8888 R@0 G@8 B@16 A@24` and `NUXEL_ANIM_HW_DECON_FMT_NAME=DECON_PIXEL_FORMAT_ABGR_8888`. `--hworder=fbvar` restores the old behaviour for A/B. |
| `tools/s10plus/nuxel-fb-phone.c` | the same override on `V` right after `FBIOGET_VSCREENINFO`, logged as `NUXEL_FB_HW_ORDER=abgr8888 R@0 G@8 B@16 (overrides fb_var)`. `--fbvar-order` restores the old behaviour. |
| `tools/s10plus/nuxel-ui.c` | `pack_rgb()` packs for `ABGR_8888` whenever `SCR.hw_abgr` (default 1); `--hworder=fbvar` overrides. |

The declared values are still logged, so a capture always shows both numbers and the
divergence can never be forgotten again.

## 5. The one-glance confirmation (still available, now optional)

`nuxel-ui` can paint the five-colour bars (`act=ctest`, or SETTINGS → RUN COLOUR TEST):
top half = the hardware order, bottom half = the old fb_var order. With A23's default,
the **top** half must read red, green, blue, white, black left to right. If it ever
reads the opposite, the hardware format question is reopened — but the driver source
says it will not.

## 6. Residual uncertainty (stated honestly)

* The DECON register *field names* are documented by the driver's own enum ordering, not
  by a public Exynos 9820 TRM in this repository. The conclusion rests on (a) the two
  formats existing as distinct values, (b) the DRM-compatible numbering, and (c) the A20
  photograph agreeing. All three point the same way; a hardware capture in A23
  (`NUXEL_ANIM_HW_ORDER_NAME` + the operator's view of the animation) is the confirmation.
* 16-bpp (`RGB_565`) is unaffected: the channel positions of 5-6-5 are unambiguous, and
  A23 keeps the declared 11/5/0 layout for it.

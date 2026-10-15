# DISPLAY BRING-UP — Samsung S10+ (beyond2lte), AMOLED panel

*Created 2026-10-15 (cycle 5). Every statement is either marked "measured"
  (read out of a hardware capture) or "source" (read out of the kernel tree).*

## 1. What the panel is (measured)

* Panel driver: `panel-drv` / `s6e3ha9_beyond2_a3_s0_default`, panel id
  `0x00A11013`, `find_common_panel_with_name … id:0xA01011 rev:2`.
* Boot chain leaves it powered: `panel_power_on panel_state:NORMAL -> NORMAL`,
  `panel_sleep_out:ub connected`, `panel_sleep_out:panel already NORMAL state`,
  `s6e3ha9_enable_self_mask B1/2 (panel_rev:2, window_color:1)`,
  `generate_gamma_table_using_lut panel_bl-0/1 done`.
* DECON: `exynos-decon 19030000.decon_f: decon_probe start`,
  `decon0: max win6, command mode, hw trigger`,
  `decon_displayport_create_vsync_thread is needed for displayport path`;
  second controller `exynos-decon 19050000.decon_t: want 2457600 bytes for
  window[4]` with `out_type(2) doesn't support window update`.
* Framebuffer geometry the driver exposes (read from the live device's recovery
  kernel via `/sys/class/graphics` — same DECON driver, so the geometry is the
  hardware's, not TWRP's choice):

| node | virtual_size | stride | implied bpp |
|---|---|---|---|
| `/dev/graphics/fb0` | 1440,6080 | 5760 | 32 (5760 = 1440*4) |
| `/dev/graphics/fb1` | 640,960 | 2560 | 32 |

  6080 = 2 × 3040, i.e. the yres_virtual is double-buffered for a 1440×3040
  AMOLED. Stride 5760 bytes = 1440 px × 4 B.
* Bootloader framebuffer handoff is declared on the kernel command line:
  `s3cfb.bootloaderfb=0xca000000 lcdtype=10555411 … consoleblank=0`.
* DECON window allocation for the panel matches that geometry exactly:
  `exynos-decon 19030000.decon_f: want 35020800 bytes for window[5]`
  (35020800 = 1440 × 6080 × 4).

⇒ The kernel brings up the DSIM link, the panel and the DECON window, and
`/dev/fb0` exists. This is why A14's `nuxel-fb-phone` could open `/dev/fb0`,
`FBIOGET_VSCREENINFO`/`FBIOGET_FSCREENINFO` and `mmap()` it successfully and
exit 0 (`FIRSTLIGHT_FRAME_WRITTEN`).

## 2. What is NOT proven: scanout

The operator reports a black screen (Samsung logo → black). Since a successful
fbdev write is **not** evidence of a visible image, A14's result is recorded as
"first-light code executed", **not** "first-light displayed". Candidate
hypotheses, in the order A15/A16 will discriminate them:

| # | Hypothesis | Test / evidence A15 will produce |
|---|---|---|
| D1 | the DECON scans the *alternate* half of the 1440×6080 virtual buffer while the driver's `yoffset` reports 0 | A15 paints **every** buffer (`NUXEL_FB_BUFFERS_PAINTED`) and logs `yoffset`/`yres_virtual` |
| D2 | the DECON window is left disabled by the kernel probe (nothing is scanned out at all) | A15's frame is unmistakable; if the panel stays black with both buffers painted, D2 wins and A16 must look at window enable / `decon_register_window` sourcing |
| D3 | the panel is on but its MIPI/DSIM output path is not started by the kernel (S-Boot left it running; the kernel's probe may stop it) | `decon_shutdown + state:6` / `decon-0 already OFF state` were logged at shutdown — the DECON reported itself already OFF *before* the shutdown, which is consistent with D2/D3 |
| D4 | the frame *was* displayed and the operator's "black" describes the dark navy design | A15's design is bright (colour bars, large white wordmark, white-outlined penguin) — a black report after A15 falsifies D4 |

## 3. Console/DRM facts that constrain the fix

* `# CONFIG_DRM is not set` in this downstream tree (recorded in cycle 4), i.e.
  there is no KMS path: Phoc/Phosh cannot run on this kernel as-is. The fbdev
  path is the only scanout interface available today, which is exactly why the
  mission's "first light must be independent of systemd and compositors" is the
  right target for this kernel.
* `/proc/cmdline` carries `console=ram loglevel=4` (S-Boot's own line). There is
  no `console=tty0`, so nothing is drawn to the panel by the kernel console.
* The initramfs `show_boot_splash()` fallback writes 720×1280×2 B (RGB565,
  1.8 MB) into whatever fb0 is; on a 1440×3040×32 panel that is the wrong
  geometry. It is harmless (nuxel-fb-phone repaints the whole surface afterwards)
  but it must not be trusted as a "splash was displayed" signal.

## 4. Kernel-side work queued for the next cycle

* Read `drivers/video/fbdev/exynos/decon/` in the kernel tree (a fresh extraction
  is now available in the build container at `/b/k15`) and determine precisely
  which call enables a window for the DSIM/panel output path, and whether the
  bootloader framebuffer window stays enabled after probe.
* Confirm whether the driver maps the `/dev/fb0` smem over the bootloader fb
  region (`s3cfb.bootloaderfb=0xca000000`) or a private allocation — the A15 log
  now reports `smem_start`/`smem_len` so this can be compared with the DECON
  window base.
* Only after a *displayed* frame exists: animation, then Phoc/Phosh (which needs
  DRM/KMS and therefore a 5.4+ Exynos 9820 port — Option C in the mission).

## 5. Kernel-source findings (cycle 5, from a fresh extraction of the tree)

Source: `drivers/video/fbdev/exynos/dpu20/decon_core.c` in the Samsung downstream
tree (`/b/k15`, same commit as the A14/A15 kernel).

* `/dev/fb0` is `decon->win[decon->dt.dft_win]->fbinfo`, published by
  `decon_acquire_windows()` → `register_framebuffer()` (decon_core.c:4114). Its
  memory is allocated by `decon_fb_alloc_memory()` (decon_core.c:3808); the A14
  log's `want 35020800 bytes for window[5]` is the 1440×6080×4 surface for that
  window, matching the live device's `virtual_size=1440,6080`, `stride=5760`.
* The DECON output is started by the **power/blank path**, not by writing to the
  framebuffer: `decon_pwr_state[DISP_PWR_NORMAL].set_pwr_state = decon_enable`
  (decon_core.c:1086) → `decon_enable()` (688) → `_decon_enable()` (609). For the
  panel output (`decon->dt.out_type == DECON_OUT_DSI`) with
  `psr.trig_mode == DECON_HW_TRIG` — exactly what this board reports
  (`decon0: max win6, command mode, hw trigger`) — `_decon_enable()` calls
  **`decon_set_black_window(decon)` followed by `decon_reg_start(...)`**.
* `decon_state_names[] = {INIT, ON, DOZE, HIBER, DOZE_WAKE, DOZE_SUSPEND, OFF, TUI}`
  (decon_core.c:97). The A14 shutdown log says
  `decon_shutdown + state:6` / `decon-0 already OFF state` → **the DECON sat in
  `OFF` (index 6) for that boot**, i.e. the panel output was never started. A
  panel that is powered (`panel_sleep_out … NORMAL`) but whose DECON never enters
  `ON` shows no image, which is the simplest explanation of the black screen.

### Consequence for the next display cycle

Writing pixels into the fbdev buffer is necessary but **not** sufficient on this
driver: the output must be brought up through the blank/unblank path so that
`decon_enable()` → `decon_reg_start()` runs, and the window must then be latched
(the driver starts with a *black* window by design, so a `decon_set_black_window`
result is expected until a window update/pan commits the fb buffer). The next
payload should therefore, in order, (1) `FBIOGET_VSCREENINFO`/`FBIOGET_FSCREENINFO`
and log them, (2) `FBIOPUT_VSCREENINFO` + `FBIOBLANK(FB_BLANK_UNBLANK)` (or
`FB_BLANK_POWERDOWN`→`UNBLANK`) to force `decon_enable()`, (3) paint both buffers,
(4) `FBIOPAN_DISPLAY` to commit, and (5) re-read `FBIOPUT/pan` state. All of this
is still standard fbdev — no registers, no physical addresses.

---

# CYCLE 6 — display bring-up findings (A15 hardware evidence)

## What the A15 hardware log proves about the display path

The whole chain probes successfully during the Nuxel boot — this is **not** a
missing-driver problem:

```
t=1.212  PANEL:INFO:panel_parse_dt:panel-0      (s6e3ha9_beyond2_a3_s0_default/utype/preliminary)
t=1.214  PANEL:INFO:panel_drv_set_gpios: rst:1, disp_det:1 (init_at:BL, ub_con:1(CONNECTED) panel:1(USE))
t=2.019  PANEL:INFO:panel_ioctl_dsim_probe:PANEL_IOC_DSIM_PROBE  panel id : 0, dsim id : 0
t=2.020  dsim-0 dsim_enable - (state:INIT -> ON)
t=2.023  PANEL:INFO:panel_core_ioctl:PANEL_IOC_SLEEP_OUT
t=2.023  PANEL:WARN:panel_sleep_out:panel already NORMAL state      -> S-Boot already turned it on
t=2.034  decon_initial_display was called
t=2.034  common_lcd_connected panel connected / decon-0: set bypass off
t=2.034  decon0 registered successfully                ("decon0: max win6, command mode, hw trigger")
t=2.034  PANEL:INFO:panel_fb_notifier:FB Registeted
```

…and then, for the remaining **1892 s**, there is no `decon-0 UNBLANK`,
no `decon_enable`, no `decon0-fsync … FRAME_DONE`. The TWRP session in the same
capture *does* show that full sequence, so the panel and controller are functional
and the difference is on the Nuxel side.

Note the controller mode: **command mode** (`decon0: max win6, command mode, hw
trigger`). In command mode the panel keeps its own frame memory and the DECON only
latches a new frame on an explicit update, which the fbdev does through
`FBIOPUT_VSCREENINFO`/`FBIOPAN_DISPLAY`. Neither A14 nor A15 ever called them.

## A16 instrumentation (what to read in the next capture)

Look for, in order:
1. `FB_NODE /dev/fb0 is a character device` and the `FB_SYSFS /sys/class/graphics/fb0/…` block
   (or `NUXEL_FB_UNAVAILABLE no /dev/fb0` if there is no fbdev at all).
2. `NUXEL_FB_INFO:` followed by one `  field=value` line per geometry field —
   **record `smem_start`, `smem_len`, `stride`, `yres_virtual` verbatim**; comparison
   against the DECON's 35,020,800-byte window decides H-C6-F.
3. `NUXEL_FB_MAPPED_BYTES`, `NUXEL_FB_BUFFERS_PAINTED`,
   `NUXEL_FB_READBACK_px0`, `NUXEL_FB_READBACK_center` — proves the store landed.
4. `NUXEL_FB_UNBLANK_rc` / `NUXEL_FB_ACTIVATE_rc` / `NUXEL_FB_PAN_rc` — which of the
   three commits the Samsung DECON accepts.
5. `NUXEL_FB_ANIM frame=1..11`, `NUXEL_FB_ANIM_DONE frames=12`,
   `NUXEL_MARKER FIRSTLIGHT_ANIMATION_DONE`, `NUXEL_FB_DRAW_SUCCESS`.
6. `NUXEL_FB_HOLD_START` then one `NUXEL_FB_HOLD frame=N` per ~10 s while the
   penguin stays resident.

Rules: a `NUXEL_FB_DRAW_SUCCESS`-style log line is **not** proof of visible output.
Only the operator's observation of the panel counts (mission §8). If the panel is
still black with all three ioctl return codes 0, the next step is to instrument
`decon_initial_display`'s window address rather than to write any physical display
address by hand.

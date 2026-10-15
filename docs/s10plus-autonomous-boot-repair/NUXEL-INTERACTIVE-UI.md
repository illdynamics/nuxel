# NUXEL — THE INTERACTIVE PHONE UI (A23/A24)

```
INTERACTIVE_NUXEL_PHONE_UI = RUNNING ON HARDWARE (process, framebuffer commit, handoff)
COLOUR PATH                = DECON_PIXEL_FORMAT_ABGR_8888 (R@0 G@8 B@16), see NUXEL-COLOUR-ORDER.md
TOUCH                      = not yet (charger-mode boot has no touch input device)
```

## What it is

`tools/s10plus/nuxel-ui.c` — a freestanding aarch64 binary (66,136 bytes, raw syscalls, no
libc) that runs as the systemd service `nuxel-ui.service` in the Fedora rootfs and owns
`/dev/fb0` through the hardware-proven DECON fbdev path. It is *not* a frame painted
during early boot and it is *not* Phosh: this kernel has `# CONFIG_DRM is not set`, so a
Phoc/Phosh session is a separate kernel-porting track.

Screens (all rendered by the same primitives, all verified offline from PPM dumps):
home (Nuxel wordmark, clock, date, battery glyph + percentage + charge state, power/USB
status, uptime, six touch tiles), settings (panel geometry, framebuffer stride/format,
colour order, build id, animation state, touch and input node, buttons for colour test /
screenshot / restart / power menu), system (kernel, os-release, PID 1, systemd state,
cgroup controllers, uptime, root filesystem, battery, USB console, input, animation and
UI stage files), logs (tail of `/var/lib/nuxel/ui.log` or the boot report, scrollable by
button or swipe), power (two-step armed reboot / shutdown, never a single-tap action),
about. A status bar is drawn on every page, plus a toast line and a red error banner when
the UI itself has a fault to report.

## The parts that matter for correctness

* **Colour**: pixels are packed for `DECON_PIXEL_FORMAT_ABGR_8888` -- the format
  `decon_pan_display()` actually programs -- *not* from `fb_var`'s declared bitfields.
  `NUXEL_UI_HW_ABGR` is logged at startup; `--hworder=fbvar` restores the old behaviour.
* **Geometry is measured, never assumed**: 1440x3040, stride 5760, 32 bpp, 2 buffers,
  scale = width/360 (the PWA's design tokens in pixels). Out-of-range writes are clipped
  in the pixel writer, and a panel whose geometry is not understood makes the UI exit
  rather than draw wrongly.
* **Double buffering**: compose into the off-screen buffer, `FBIOPAN_DISPLAY` to it --
  one code path (`ui_frame()`), so the bookkeeping can only be wrong in one place.
* **Self-healing panel**: a failed pan re-issues `FBIOPUT_VSCREENINFO` + `FBIOBLANK`
  (UNBLANK); `FBIOBLANK` is also re-asserted every 2 s unconditionally. This is the A22
  fix carried into the UI, and it is what a third party's `fb_release` cannot survive
  (see the A24 postmortem: a *second* renderer is still fatal, hence single-instance).
* **Handoff**: the UI commits its first real frame, writes `ui-fb-ready`
  (`PHONE_UI_FRAME_COMMITTED`), *then* signals the animation (`anim-stop` file + SIGTERM
  to `fb-anim.pid`), and only then records `PHONE_UI_READY`. State machine:
  `PHONE_UI_STARTING -> PHONE_UI_FRAME_COMMITTED -> PHONE_UI_READY` in
  `/var/lib/nuxel/ui-stage`, with `boot-stage` and `ui-build` alongside.
* **Console channel**: the UI creates `/run/nuxel-ui.cmd`; writing a line into it drives
  the interface (`page=settings`, `act=ctest`, `tap X Y`, `screenshot [path]`,
  `orient N`, `status`, `quit`). This is how the UI is testable before touch works, and
  it is how the acceptance evidence for A24 was collected.
* **Evidence**: `screenshot` writes a PPM straight out of the buffer the panel is
  scanning, read back in the panel's real channel order, so a host-side image viewer sees
  what the glass shows. `ui.log` records every action and stage transition.

## Offline verification (no phone needed)

`nuxel-ui --selftest=DIR --size=1440x3040` renders every page into an anonymous buffer
and writes PPMs. Run inside the Fedora 43 aarch64 container it produced six pages that
were then checked numerically: all six tile centres are `--bg-card`, the tile gaps are
background, the status-bar text sits inside y=16..127 of a 144 px bar, no ink in the top
8 rows, no ink in the extreme right column, nothing outside the Nuxel palette, and no
pixel outside the buffer (PPM sizes are exact).

## Deployment

`scripts/s10plus-debug-pack/nuxel-live-deploy.sh <binary> --to /usr/bin/nuxel-ui` pushes a
gzip+base64 payload over the live console with an exact byte count, verifies the target's
`sha256sum` against the local hash, keeps the previous binary as `*.prev` and only then
installs. The BOOT candidate also carries the binary (`/opt/nuxel/nuxel-ui`) and `/init`
installs it into the rootfs at boot, so a BOOT-only flash can ship a new UI without
rewriting the 4 GiB rootfs.

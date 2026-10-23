# A64 evidence

- `after-fixed-full.png` — on-device `/dev/fb0` capture (360x1520, both DECON
  buffers), taken after the fix. The visible frame is the TOP half.
- `after-home-fixed.png` — the cropped visible 360x760 Home frame from the above
  capture. This is the authoritative on-device after screenshot (compact 4-column
  app grid, normal status bar, no debug telemetry).
- `host-after-home.png` / `host-before-home.png` — headless-Chromium renders for
  reference only. They are **not** authoritative: Chromium stays on the boot
  splash without the native bridge, so these frames are NOT the Home grid.
- Owner-supplied `launcher-regression-reference.jpg` was not present in the
  repository and could not be located on the host; the broken state is instead
  proven by the on-device 0-byte `launcher.css` hash, HTTP `200 0` receipt, and
  the A63 `a63-launcher-runtime-apply` rollback logs.

# A55 Orientation Matrix

## Seven stable modes (A54 canonical, preserved)
`auto`, `auto-portrait`, `auto-landscape`, `portrait`, `landscape`,
`reverse-portrait`, `reverse-landscape`.

## Live status (device)
- `nuxel-orientationd` returns the seven hyphenated keys; `do_set` rejects unknown
  values; no `undefined`.
- Menu/state/persistence: PASS_INTEGRATION (40 orientation tests + migration test).

## Physical rotation blockers (honest)
- **Compositor transform:** `wlr-randr` absent; the fixed-portrait screencopy
  (`nuxel-wl-fb` → `/dev/fb0`) has no transform backend. A CSS-only rotation that
  leaves touch coordinates unrotated is explicitly forbidden, so it is NOT shipped.
- **Sensors:** no IIO accelerometer with readable scale; `iio-sensor-proxy`
  (`monitor-sensor`) present but no auto-capable gravity source is exposed.
- Gates: **ROT-MENU PASS_INTEGRATION**; **ROT-FORCED PARTIAL** (policy correct,
  output transform blocked); **ROT-AUTO BLOCKED_HARDWARE** (no gravity sensor).

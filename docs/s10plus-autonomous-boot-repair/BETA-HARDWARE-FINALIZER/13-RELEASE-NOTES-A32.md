# 13 — RELEASE NOTES A32 (evidence-backed)

Cycle: **A32 — Galaxy S10+ beta hardware & launcher finalizer** · 2026-10-16 · live over
the USB console, no TWRP, no BOOT/USERDATA write, one controlled reboot.

## Headlines

1. **The touchscreen now exists.**  Root cause was the *boot mode*: the handset had
   booted with `androidboot.mode=charger`, which makes `sec_ts_init()` return `-ENODEV`
   before `i2c_add_driver()`.  After a normal reboot:
   `input: sec_touchscreen … PROP=2`, libinput `accepted=1`, phoc holding the device,
   `nuxel-touch-arm.service` active.  No driver patch was needed or made.
2. **The launcher is the UTM launcher.**  It always was the same code; what differed was
   a **stale service-worker cache** that kept the previous JS alive after deployment, plus
   two registry entries with no runnable frontend.  Cache invalidation is now explicit
   (SW namespace bump + network-first code assets + host-side purge with a version stamp),
   and Settings/Terminal are real PWAs under the authoritative tree.
3. **Colour was genuinely broken.**  XRGB8888 screencopy words were copied unchanged into
   a panel whose DECON order is ABGR_8888 → red and blue swapped on the glass.  Fixed with
   an explicit conversion, proven by a unit test that itself caught a dropped green
   channel in the first attempt.
4. **The animation’s second half is back.**  The bridge used to hand the panel to the
   launcher ~2–3 s in, replacing the animation with the static wallpaper.  It now waits
   for complete cycles: the last boot logged `NUXEL_ANIM_LOOP=1`, `=2`, then
   `ANIMATION_STOPPED` at 21.1 s.
5. **The buttons behave like phone buttons.**  POWER short → display off/on (verified
   live: `DISPLAY_OFF brightness=0 saved=12800` → `DISPLAY_ON brightness=12800`), volume
   → the real ALSA element `Left AMP PCM Gain` with a visible OSD, assistant key 703 →
   Nuxel Terminal (one instance), all remappable in Settings or with `nuxelctl`.
6. **Camera cutout respected, generally.**  A ten-zone safe-area system with presets for
   no/left/centre/right cutouts, per-orientation and per-device profiles, live preview,
   persistence and a console fallback; the S10+ preset moved the battery cluster 112 px
   clear of zones 9–10.

## Deployed artefacts (sha256, verified on the target)

```
e4b4293e…  /usr/lib/nuxel/nuxel-wl-fb              (colour + animation gate + screen on/off)
18631d5b…  /usr/lib/nuxel/nuxel-pwa-host           (host API, PTY terminal, cache invalidation)
5f052ef4…  /usr/lib/nuxel/nuxel-button-manager     (new)
e4281cab…  /usr/bin/nuxelctl                       (new)
d911babf…  /etc/systemd/system/nuxel-button-manager.service
```
Every replaced file has a `.prev-a32` backup; the install reports `FAILURES=0`.

## Tests

* `tools/s10plus/a32/tests/run-tests.sh` — **0 failing suites**: colour conversion selftest
  (run on the aarch64 UTM guest), key-bitmap decode, status-bar safe-zone engine
  (15 assertions), launcher registry, wallpaper asset/CSS, sources present.
* Live: services active with **0 failed units**, single framebuffer owner, hand-off
  sequence complete, HTTP 200 for every launcher/app asset, safe-zone reflow report,
  display off/on, volume + OSD, mixer element log.

## Still not claimed

Audio **output** (no player, no mixer UI beyond the amp gain — see 12), camera, modem,
WLAN, and the physical acceptance tests listed in 11 (finger taps, power/volume/Bixby
presses, visual colour/wallpaper/cutout confirmation).

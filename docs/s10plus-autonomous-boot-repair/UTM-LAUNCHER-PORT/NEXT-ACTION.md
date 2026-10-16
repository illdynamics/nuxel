# NEXT-ACTION — A28 (do this the moment the handset is on USB)

```
STATE           = A28 BUILD OK, GATES GREEN (host + ARM64 build)
BINARY          = build/out/s10plus/a28/nuxel-ui-a28.A28-nuxel-home-launcher-1
                  852,640 bytes  sha256 393619763345979f7aa83b68c1e0a1e320fb6589119258b43b818cc10f1eb84b
REV             = A28-nuxel-home-launcher-1
BLOCKED ON      = the phone is not enumerated on this host (no /dev/cu.usbmodem*)
```

## 0. Confirm the console (never assume)

```sh
ls -l /dev/cu.usbmodem*                       # the Nuxel CDC-ACM console
scripts/s10plus-debug-pack/nuxel-live.sh --run 'id; cat /var/lib/nuxel/ui-build 2>/dev/null; systemctl is-active nuxel-ui'
```

## 1. Deploy the launcher (no reflash, no TWRP)

```sh
scripts/s10plus-debug-pack/nuxel-live-deploy.sh \
    build/out/s10plus/a28/nuxel-ui-a28.A28-nuxel-home-launcher-1 \
    --to /usr/bin/nuxel-ui --restart nuxel-ui --pin A28-nuxel-home-launcher-1
```
The deploy verifies the target's `sha256sum`, keeps `/usr/bin/nuxel-ui.prev`, and
writes `/usr/lib/nuxel/ui.pinned`.

## 2. Verify the launcher took the panel

```sh
scripts/s10plus-debug-pack/nuxel-live.sh --run 'cat /var/lib/nuxel/ui-stage; cat /var/lib/nuxel/ui-build'
#   expect: PHONE_UI_READY / A28-nuxel-home-launcher-1
scripts/s10plus-debug-pack/nuxel-live.sh --run 'tail -40 /var/lib/nuxel/ui.log'
#   expect: WALLPAPER_OK path=/usr/share/nuxel/nuxel-background.png src=… panel=1440x3040
#           TOUCH_READY device=/dev/input/event2 name='"'"'sec_touchscreen'"'"' mt=1 direct=1 slots=… x=[min.max] y=[min.max]
#           PHONE_UI_READY
scripts/s10plus-debug-pack/nuxel-live.sh --run 'cat /var/lib/nuxel/ui-touch-ready'
```
If `WALLPAPER_UNAVAILABLE` appears, the log names the reason (asset path, PNG rc).

## 3. Finger tests (the only thing that closes P0)

1. Tap one visible app tile. Expect, on the console:
   `TOUCH_TAP x=… y=… act=1xx` in `/var/lib/nuxel/ui-touch` and
   `APP_LAUNCH_RESULT id=… state=…` in `/var/lib/nuxel/ui.log`.
2. Swipe up/down (log scroll) and left/right (page) — expect
   `TOUCH_SWIPE_V` / `TOUCH_SWIPE_H`.
3. Drag once across the grid — expect one `TOUCH_DOWN` and no stray taps.
4. If coordinates are rotated or offset, set it live and re-test:
   `echo 'orient 1' > /run/nuxel-ui.cmd` (0..3), then bake the value in as the
   default for the next build (one-line change in `nuxel-ui.c`, `TOUCH_ORIENT`).
5. Pull a screenshot to confirm what the glass shows:
   `echo 'screenshot small' > /run/nuxel-ui.cmd && nuxel-live.sh --pull /var/lib/nuxel/ui-small.ppm --out /tmp/ui-small.ppm`
   then `python3 tools/s10plus/a27/analyze-screenshot.py /tmp/ui-small.ppm`.

## 4. Then (unchanged from A26, in order)

1. `nuxel-fb-phone.c --firstlight` + the controlled BOOT-only update (seamless
   splash) — the launcher does not depend on it.
2. The `sd-event` child-watch compat patch (lets userdbd/dbus-broker/udevd be un-masked).
3. Stop the `asix`/`wl_cfg80211` uevent storm.
4. Only then consider Option B / the DRM track, which is what would let the real
   PWA applications open on this board (`07-LIMITATIONS.md` §1).

## 5. Rules kept

* No partition was written from the live session; no EFS/PIT/bootloader/DTBO change.
* `/dev/fb0` is never opened by a diagnostic — the UI is driven only through
  `/run/nuxel-ui.cmd`.
* Every live change this cycle is in the repository and in the builders
  (`tools/s10plus/a28/*`, `tools/s10plus/build-a25-initramfs.sh`,
  `images/s10plus/build-phone-rootfs-inside-fedora.sh`).

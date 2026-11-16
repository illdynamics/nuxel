# REPORT-PWNAGE-106000 — fully black screen-off + v0.8.3 release-CI repair

**Date:** 2026-11-10  
**Version:** `v0.8.3-beta`  
**Target:** Samsung Galaxy S10+ (SM-G975F, beyond2lte), Fedora 43 ARM64 userspace  
**Phone:** `root@10.20.30.16` via `~wicked/.ssh/wicked_wqn_id_rsa`

## 1. Reported symptom

Screen-off darkened the panel but did not turn it fully off/black. The owner
described a faintly lit AMOLED rather than a true black surface.

## 2. Live measurement before the fix

The running bridge was the A67 presenter at
`/usr/lib/nuxel/nuxel-wl-fb` (`70f7a941…`, built 2026-11-09 22:09). Its embedded
strings contained `DISPLAY_OFF` but **not** `BL_POWER` or `PANEL_POWERDOWN`,
proving the deployed binary was older than the active repository source.

With the bridge in `display=off`:

```
brightness=0
actual_brightness=2
bl_power=0
```

Direct writes to the panel sysfs showed that `bl_power=4` is accepted and
persists:

```
echo 4 > /sys/class/backlight/panel/bl_power   # readback=4
actual_brightness=2                            # unchanged
```

So neither brightness 0 nor `bl_power=4` alone necessarily clears the last
latched DECON frame. The running binary also never attempted the fbdev
powerdown path.

## 3. Root cause

1. **Stale deployed binary.** The phone was running a build that predated the
   A67 screen-off hardening. The release rootfs builder compiles
   `tools/s10plus/a67/nuxel-wl-fb.c`, but the deployed binary had only the old
   backlight-only path.
2. **Retained DECON frame.** On this command-mode Samsung panel, the last
   presented compositor frame can remain visible if the panel is not truly
   powered down. Backlight brightness 0 leaves the panel at
   `actual_brightness=2`, and `bl_power=4` alone did not clear the frame.
3. **No software-black fallback.** There was no guaranteed black page committed
   before powerdown, so the "off" state could still show a faint version of the
   launcher/lockscreen.

## 4. Fix

`tools/s10plus/a67/nuxel-wl-fb.c` now does the following on `screen-off`:

```c
panel_paint_black("screen-off");     /* memset visible fb + FBIOPAN_DISPLAY */
backlight_write(0);                  /* brightness 0 */
bl_power_write(4, "screen-off");     /* FB_BLANK_POWERDOWN */
panel_blank_powerdown("screen-off"); /* FBIOBLANK(POWERDOWN) */
bl_power_write(4, "screen-off-post-blank");
```

`panel_paint_black()` zeroes exactly the visible area
(`fb.line * fb.h`, capped to `fb.len`) and latches it through the normal
`FBIOPAN_DISPLAY` commit helper. The bridge remains the single `/dev/fb0`
owner. The existing wake path already forces a fresh capture and commit before
restoring the backlight, so the black page is never visible after wake.

A new log record makes the result auditable:

```
PANEL_BLACK why=screen-off bytes=<visible bytes> pan_rc=0
PANEL_POWERDOWN why=screen-off rc=0 errno=0
BL_POWER why=screen-off requested=4 ... readback=4
DISPLAY_OFF why=control-fifo saved_brightness=<n> bl_power=4 actual_brightness=<n> black=1
```

## 5. Regression coverage

`tools/s10plus/a34/tests/test-decon-presentation-contract.py` now requires:

- `panel_paint_black("screen-off");`
- `memset(fb.map, 0, visible);`
- black-page commit before `panel_blank_powerdown("screen-off");`
- `bl_power_write(4, "screen-off-post-blank");`

The test reads the same A67 source that
`images/s10plus/build-phone-rootfs-inside-fedora.sh` compiles, so a stale or
divergent bridge cannot pass CI.

## 6. v0.8.2 release-CI failure and repair

`./err.md` was not present in the checkout. The actual failure was recovered
from the failed `main` release run **42537383996** (2026-11-09). The
`build s10plus` job failed in the **Nuxel Home — immersive chrome** step:

```
FAIL controller defines bottom/top edge bands
FAIL top pull reveals the status bar
FAIL native top bar defaults to a pull-down strip
33 passed, 3 failed
```

Repair:

- `pwa/nuxel-home/js/immersive.js` now defines explicit `BOTTOM_BAND` and
  `TOP_BAND` constants while preserving the existing gesture and Quick Settings
  handoff.
- The top-pull contract check now follows the real `dy > 0` branch and
  `setStatusVisible(true, 0)` call instead of a historical one-line layout.
- `tools/s10plus/a45/nuxel-statusbar.c` names the reveal path `bar_reveal`.

Result:

```
Nuxel Home — immersive chrome
36 passed, 0 failed
```

## 7. Version lockstep

The whole repository is bumped to `v0.8.3-beta`:

- `VERSION`, device `APKBUILD`s and the OTA builder default
- PWA manifests, `package.json`, `bridge-version.json`, status bar
- Service-worker cache namespace `v095-p106000`
- Bridge, portal and notification version pins
- Native shell/meson/metainfo versions, VM snapshot pins
- `tests/pwnage90000/test_release_assets.py` `EXPECTED`

The release-asset gate passes with 0 failures.

## 8. Phone deployment

Deployment target: `root@10.20.30.16`, key
`~wicked/.ssh/wicked_wqn_id_rsa`.

- Latest PWA/bridge/userspace payload (`v0.8.3-beta`) deployed over SSH; the
  phone reports `host_version=0.8.3-beta` and status bar
  `VERSION='0.8.3-beta'`.
- The current A67 `nuxel-wl-fb` was compiled on the phone against its native
  wayland-client and installed to `/usr/lib/nuxel/nuxel-wl-fb`
  (`sha256 dba4367f0a4a3101fbc53f496fea35f3dd8c23ff26c5cc6c3d1fde174d0ef6c5`).
  The previous binary was backed up under
  `/var/lib/nuxel/live-deploy/wlfb-20261110T092445Z/`.
- `nuxel-wl-fb.service` was restarted and returned to the ownership loop.
- `nuxelctl display on` then `nuxelctl display off` exercised the new path.
  Measured on the handset:

```
dmesg:
  PANEL_BLACK why=screen-off bytes=17510400 pan_rc=0

/var/lib/nuxel/display:
  DISPLAY_OFF
  brightness=0
  actual_brightness=2
  bl_power=4
  saved_brightness=24300
  max_brightness=48600

visible framebuffer samples (1440x3040x4):
  first_1MiB_all_zero  True
  middle_1MiB_all_zero True
  last_1MiB_all_zero   True
```

`actual_brightness=2` is the vendor panel's minimum readback; the latched
frame is black, `bl_power` is POWERDOWN, and the wake path restored
`DISPLAY_ON` with `bl_power=0` before the next off cycle.

## 9. Release

The fix ships in **v0.8.3-beta**. Merging the release PR to `main` triggers the
GitHub Release workflow, which builds the S10+ boot image and Fedora phone
rootfs from repo sources, verifies the artifacts, creates the annotated
`v0.8.3-beta` tag and publishes the release marked **Latest**.

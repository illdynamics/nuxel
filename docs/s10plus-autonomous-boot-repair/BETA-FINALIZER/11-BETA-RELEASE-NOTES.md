# 11 — NUXEL S10+ BETA 0.1 — RELEASE NOTES (cycle A31)

## What this release is

The first genuinely usable beta of Nuxel on the Galaxy S10+ (beyond2lte): the
**original UTM Nuxel Home PWA** rendering on the AMOLED through
Phoc + Wayland + WebKitGTK + the Wayland-to-framebuffer bridge, with the original
wallpaper, one boot animation, one framebuffer owner, and a compositor that owns
the real touchscreen.

## Fixed in this cycle

| # | Defect | Fix |
|---|---|---|
| 1 | Two processes painted `/dev/fb0` for the whole session (initramfs MP4 player + bridge) → flicker and animation bleed-through | The A30 single-owner handoff is now **deployed** and hardened (A31): no scanout write before the stop is *proven*, identity-verified bounded stop, refusal instead of racing, no periodic display re-init, paced presentation |
| 2 | Wallpaper 404 — the CSS path `pwa/nuxel-home/assets/nuxel-background.png` was never staged | Staged from the authoritative asset already on the device (byte-identical); builder fixed; SW cache migrated to `v2` |
| 3 | Compositor had **zero** input devices, so touch could never reach the launcher | phoc now requests the libinput backend; `LIBSEAT_BACKEND=noop` + `nuxel-libinput-path.c` give it a working path on a kernel with no VT and no usable udev daemon; the real `sec_touchscreen` is open in phoc |
| 4 | The PWA's own fullscreen splash was a second boot animation and an input-blocking overlay | Launch-mode signal `?boot=os`; host enforces it with a user style sheet **and** DOM removal (verified `splash absent` at load, +1 s, +4 s, +9 s) |
| 5 | Application pages 404 (the registry's `/pwa/nuxel-apps/…` was never staged on the live phone) | Five app trees staged (SHA-verified transfer), shared media resolved to the canonical assets |
| 6 | WebKit permission handler granted **every** permission to **every** page | Deny-by-default, trusted-origin-only, notification-only; user-media denied because the device has no media path; every decision logged |
| 7 | A dead web process left a blank screen forever | `web-process-terminated` supervision with bounded reload |
| 8 | Restart storms (two loops) contributed to a watchdog reset of the handset | Bounded restart policy on all launcher units; `WLR_LIBINPUT_NO_DEVICES=1` so a charger-mode boot cannot fail-loop the compositor |
| 9 | `nuxel-push.py` could never converge (wrong substring for the expected length) and truncated blocks | Fixed in the repo; `push-file.sh` per-chunk verification is the documented transport |

## Beta definition — what is proven

* The launcher on the panel **is** `pwa/nuxel-home/` (no substitute frontend):
  `NUXEL_HOME_READY … engine=WebKitGTK/2.52`, `nuxel-ui` inactive and disabled.
* The wallpaper is served (`200 image/png 1257938`) and **decoded by the browser**
  at the URL the computed CSS resolves to.
* The compositor owns `sec_touchscreen`; the touch pipeline is connected from
  kernel IRQ to the PWA, with an observer in the real document reporting events
  and `app:launch`.
* One animation, one transition, one framebuffer owner:
  `ANIMATION_STOPPED`/`ANIM_OWNER=nuxel-wl-fb`, `anim-stop` + confirmed marker,
  `pgrep -cf nuxel-anim-player` → 0.
* `tools/s10plus/a31/verify-launcher-live.sh` → **17/17, exit 0**.
* The whole configuration came up by itself after a controlled normal reboot.

## What beta does NOT claim

Telephony, SMS, cellular data, Wi-Fi, audio, camera, sensors, suspend/resume and
battery life are **not** implemented or tested on this device; the native-scheme
registry entries (Phone, Messages, Contacts, Camera, Settings) have no handler and
therefore do nothing. The `nuxel-http-bridge` parity work is not done (doc 12).
See doc 12 for the full remaining-limitations list, and the acceptance checklist
for the items that still need the user's eyes and finger.

## Reproduce

```
tools/s10plus/a31/build-a31.sh                     # build on the live UTM VM (aarch64, Fedora 43)
tools/s10plus/a29/push-file.sh <artifact> <path>   # deploy over the USB console, SHA-verified
tools/s10plus/a31/verify-launcher-live.sh          # 17 automated live checks
images/s10plus/build-phone-rootfs-inside-fedora.sh # image now stages every fix above
```

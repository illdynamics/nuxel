# NEXT-ACTION — cycle 13 (A26, 2026-10-15)

```
STATE           = NUXEL IS RUNNING, FEDORA BOOT GRAPH COMPLETE
                  systemctl is-system-running = running
KERNEL          = 4.14.253 #13 (A25), booted normally (NOT charger mode)
UI              = active, pid from /var/lib/nuxel/ui.pid, owns /dev/fb0,
                  animation STOPPED (ANIM_STAGE=ANIMATION_STOPPED)
PANEL           = decon-0 UNBLANK, PAN_RC=0, 1440x3040x32 abgr8888
CONSOLE         = /dev/cu.usbmodem201, framed tool v2 (sha-verified, cancellable)
PERSISTED FIXES = tools/s10plus/a26/nuxel-rootfs-fixes.sh
                  (wired into images/s10plus/build-phone-rootfs-inside-fedora.sh)
BOOT CANDIDATE  = A26 asset staged+verified, blit withheld (see the gate)
```

## 1. One thing needs a human: a finger on the glass

A raw reader is armed on the touch device for a 900 s window:

```
/var/lib/nuxel/touch-raw.bin        <- 0 bytes means NO touch seen yet
```

Touch the Nuxel home screen a few times (and drag once). Nothing else is needed:
the file will grow and the events can be decoded offline. This is the last step
of P4 — everything else about touch is already measured (the controller is
present with multitouch caps and this is a normal boot, not charger mode).

## 2. Then, in order

1. **Decode `touch-raw.bin`** and derive the real `ABS_MT_POSITION_X/Y` range.
   Do not assume 0..1440 / 0..3040. Then wire the coordinates into
   `nuxel-ui`'s existing `tap X Y` path (already implemented and proven).
   Note: the running build logged `TOUCH_POINTING_DEVICE_NONE` even though
   `event2` exists — it looks the device up in a way that fails; enumerate by
   capability instead.
2. **`nuxel-fb-phone.c`: implement `--firstlight`** per the contract in
   `tools/s10plus/a26/build-a26-boot.sh`. Reuse the player's nearest-neighbour
   integer spans and the single existing ABGR_8888 packing. Then
   `sh tools/s10plus/a26/build-a26-boot.sh` will stop withholding the candidate.
3. **Controlled BOOT-only update** for the seamless-splash fix, at a maintenance
   opportunity, with full SHA-256 readback. Verify on the glass that the first
   lit frame is the animation opening, with no old splash and no black gap.
4. **`sd-event` child-watch compat patch** (the durable fix that lets userdbd,
   dbus-broker and udevd be un-masked), then re-verify the graph.
5. **Identify and stop the `asix` uevent storm** (`wl_cfg80211_netdev_notifier_call:
   wdev null`), so un-masking udevd later is safe.
6. `nuxel-live.sh`: handle a mid-command cable pull as `console lost` instead of
   a traceback (one `OSError` path remains).
7. Optional: add an ECM/RNDIS function alongside ACM in the next initramfs for
   bulk transfer over SSH — **only** once ACM is proven to survive the gadget
   reconfiguration, since ACM is the only lifeline today.

## 3. Rules unchanged

* Never write BOOT/USERDATA/EFS/DTBO/PIT/bootloader from the live session.
* Never run a second framebuffer client; the UI is driven via `/run/nuxel-ui.cmd`.
* Never open `/dev/fb0` from a diagnostic (closing it powers the panel down).
* Every live fix goes into the rootfs builder the same cycle it is made.

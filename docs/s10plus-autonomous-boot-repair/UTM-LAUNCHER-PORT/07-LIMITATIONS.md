# 07 — LIMITATIONS AND WHAT REMAINS

## 1. Applications cannot run on the S10+ today — and the launcher says so

Distinguishing the mission's five app states against the **measured** phone image
(`images/s10plus/build-phone-rootfs-inside-fedora.sh` package list + the A26 live
inventory):

| App | Registry | State on S10+ | Why |
|---|---|---|---|
| Calendar, Files, Mail, Notes (+ camera-gallery PWA) | `type: pwa` | **installed, missing a rendering backend** | the assets are in the image (`/usr/share/nuxel/nuxel-home`, `pwa/nuxel-apps/*`), but there is **no web engine**: no `webkitgtk`, no WPE, no Chromium/Firefox, and no display server for one to draw on |
| Phone (dialer), Messages, Contacts | `native` `/usr/bin/nuxel-dialer|messages|contacts` | **not installed** | `shell/nuxel-shell/*` are built separately (meson, GTK4) and are not part of the image; and GTK4 needs a display server in any case |
| Settings | `native` `/usr/bin/nuxel-settings` | **not installed** | same |
| Camera | `native nuxel-camera://` (apps.js) | **not installed / no implementation** | `apps.js` declares a native handler that no component implements; `app_registry.json` disagrees (it points at the camera-gallery PWA) — recorded as a registry divergence by `gen-launcher.py` |
| Telephony, camera hardware, Wi-Fi, mobile data, audio, sensors | — | **unsupported** | no radio/modem bring-up, no vendor blobs, no verified kernel drivers (per the A26 status record) |

`launch_app()` attempts the real command for every app and records the outcome;
on this image every launch therefore ends as
`state=unavailable reason=no-pwa-engine-and-server-down` (PWA) or
`reason=native-binary-not-installed` (native). Nothing is faked, and the launcher
stays up.

**What would make apps open** (all require more than a userspace deploy):

1. a web engine plus a display path — i.e. WebKitGTK/WPE on **Wayland** or **X11**
   on this board, which needs Option B or the DRM/KMS project (`PHOSH-ASSESSMENT.md`);
   or
2. shipping the native GTK4 apps **and** a display server; or
3. re-implementing the PWAs natively — which is precisely the "third launcher"
   the mission forbids.

None of these can be delivered over the CDC-ACM console: WebKitGTK's dependency
closure is tens of megabytes and the phone has no network (no wlan/radio driver),
so `dnf install` cannot run on the device either.

## 2. Kernel / graphics

* No DRM/KMS: `# CONFIG_DRM is not set` in the Samsung 4.14.253 vendor tree, so
  no `/dev/dri`, no GBM/EGL, no wlroots/Phoc/Phosh, no GTK/browser scanout.
  This is the single blocker behind §1, and it is a **kernel display-porting
  project**, not a configuration change.
* If a DECON/DSIM DRM port is ever attempted, it must not disturb the working
  fbdev path that the launcher uses today (the fbdev path is the fallback).

## 3. Presentation (forced, documented in `02-COMPATIBILITY.md` §4)

* DejaVu Sans atlas instead of the browser font stack; monochrome emoji tinted by
  app colour (the VM has no emoji font at all, so this cannot be compared 1:1);
  the status-bar centre cluster is omitted (no radio/wlan, and the punch-hole
  band must stay clear); search text is entered on the console (no Wayland OSK).

## 4. Not verified on hardware

* No physical deployment, no finger capture, no human visual confirmation in this
  session (the handset was not on USB). Everything in §1..§3 is source-, tool- and
  (for the VM) live-evidence based; every physical claim in this directory is
  explicitly marked as not run.

## 5. Explicitly not done (and why)

* No new launcher, no redesign, no replacement app grid, no new icons or theme.
* No screenshot/image inspection was used: the launcher's definition was taken
  from `apps.js`, `launcher.js`, `style.css`, `launcher.css`, `search.css`,
  `status-bar.css`, `app_registry.json`, the service files and the VM's measured
  behaviour.
* No partition was written, no recovery/bootloader/PIT/EFS/DTBO touched, no
  kernel replaced, no regulator or thermal protection modified.

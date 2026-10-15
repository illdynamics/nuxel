# P5 — PHOSH/PHOC MIGRATION ASSESSMENT (credible path, not a claim)

**Milestone vocabulary is deliberately kept separate:**

```
FRAMEBUFFER_NUXEL_PHONE_UI_READY   <- achievable now, and is the immediate deliverable
PHOSH_WAYLAND_PHONE_UI_READY       <- a kernel/display-porting project, not a config flag
```

## 1. Where the hardware actually is

| Fact | Evidence |
|---|---|
| Kernel is Samsung Linux 4.14.253 (vendor tree, Exynos 9820) | `uname -a`, `#13 SMP PREEMPT` |
| No DRM/KMS scanout path | `# CONFIG_DRM is not set` in the built `.config` |
| Display is fbdev through the vendor DECON/DSIM stack | `/dev/fb0` `crw------- 29,0`; `decon-0 UNBLANK mode: 0`; `DECON_PIXEL_FORMAT_ABGR_8888` in the commit path |
| Panel is 1440x3040, pixel order ABGR_8888 on the wire | A23 proof + `ui-fb-ready` `fb=1440x3040x32 abgr8888` |
| Mesa/EGL/GBM and libinput RPMs are *installed* | `mesa-libgbm`, `mesa-libEGL`, `libinput` in the image manifest |
| Phosh/Phoc RPMs are *installed* | `phosh phoc stevia` in `build-phone-rootfs-inside-fedora.sh` |
| No `/dev/dri` | nothing to render into |

**Installed ≠ usable.** With no DRM node there is no KMS modesetting, no GBM
buffer allocation, no EGL-PLATFORM_GBM surface, and therefore no wlroots/Phoc
output. Launching Phoc today fails in the renderer setup, and that failure is a
property of the display stack, not of Nuxel.

## 2. The migration, in dependency order

1. **DRM/KMS for DECON** — either port the Exynos DECON/DSIM drivers to modern
   DRM (`exynos_drm`, `dsim`, `decon`), or enable the vendor DRM if the tree has
   it. This also needs a `fbdev`→`drm` handover so the early framebuffer keeps
   working.
2. **Panel + DSI host + PHY** — model the S10+ panel (1080x1920 in the animation
   raster, 1440x3040 native) as a DRM panel, incl. the ABGR_8888 format quirk,
   `mdnie` scenarios and the unblank path the notifier currently owns.
3. **KMS modesetting + atomic commit** — plane, CRTC, connector; a full modeset
   must not fight the DECON power sequencing (`decon_release` disables the panel
   regulator, measured).
4. **GBM/EGL** — needs the DRM node plus a working render node; software
   rasterisation (`llvmpipe`) is the pragmatic first target on an ARM64 phone.
5. **Seat/input** — `systemd-logind` is already active on this image, which is
   the prerequisite for a `seat0`. Touchscreen, keys and power button must be
   tagged and handed to the session.
6. **Phoc + Phosh + a session manager** — only after 1–5.
7. **Scaling/rotation** — 1440x3040 at ~19.5:9 needs fractional scaling in Phosh
   to be usable; the current fbdev UI already does its own scaling.

## 3. Feasibility risks, stated plainly

* The vendor tree is 4.14. Mainline DRM/KMS work has moved on by ~10 years;
  forward-porting DECON to a modern kernel is a large project, and back-porting
  modern DRM into 4.14 is worse. This is the single biggest cost.
* Phosh on a modern Fedora userspace expects a recent kernel; that is a second,
  independent constraint.
* Everything here would be a **separate kernel track**. It must not disturb the
  working fbdev UI: the fbdev path is what the phone uses today.

## 4. Verdict

There is a credible path, and it is a kernel display-port project with a
userspace follow-up — not a package installation. Until DRM/KMS exists,
`PHOSH_WAYLAND_PHONE_UI_READY` stays explicitly unmet, and
`FRAMEBUFFER_NUXEL_PHONE_UI_READY` is the milestone being driven to completion.

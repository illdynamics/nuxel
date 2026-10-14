# Nuxel S10+ Exynos 9820 — evidence-based integration status (2026-10-14)

Nuxel is a **Fedora-based Linux PHONE OS**. Fedora's native init system is
**systemd**; the previous S10+ Alpine/OpenRC builder is deprecated. It was
incorrect to call the small ARM64 framebuffer bring-up image a finished phone
runtime. Progress percentages below are **engineering estimates**, not measured
completion and not probabilities of successful boot.

| Component | Engineering progress | Evidence available | Still unverified / blocked |
|---|---:|---|---|
| Device source configuration | 90% | Exynos S10+ overlays/config, S10+ udev, user-provided PIT with 41 entries | Exact physical hw_rev, DTBO effective merge, firmware provenance |
| Android v1 boot packaging | 88% | ARM64 4.14 kernel preserved, merged DTB, repacked newc + `/bin/sh`, USERDATA resolution, writable-root handoff | Samsung S-Boot acceptance, real boot log, DTBO board match |
| Host transfer workflow | 70% | Heimdall v2.2.2 reported both 100% | Missing EndSession confirmation and readback/boot evidence; NOT solved by rootfs changes |
| ARM64 diagnostic rootfs | 88% | Verified ext4 traversal, static Toybox, S10-specific rules, Motorola removed, ARM64 framebuffer test | Real e2fsck and PID1 running on handset |
| Fedora 43 full-runtime build automation | 65% | Docker aarch64 DNF RPM recipe, fail-closed package checks and symlink-aware verifier | Not run: no Docker/DNS/package repository in build sandbox |
| Fedora ARM64 Python3/systemd/Phosh/Phoc **inside delivered diagnostic image** | **0%** | Image explicitly contains no Fedora RPM runtime | Build on connected Mac and run strict verifier |
| Actual Phosh phone session | **0%** | No successful DRM/GPU/seat session on S10+ | Device driver bring-up, greetd/user session test, touch input |
| First-light panel probe | 35% | Static ARM64 framebuffer probe, service recipe | Compatible fbdev/DRM and panel output not tested |
| Nuxel Home app assets | 80% | PWA assets and service source included | WebKit/mobile runtime, launch and touch UI integration |
| WiFi, calls, mobile data, audio, sensors, camera | 10% | Some documented device config and mappings | Working kernel drivers, proprietary blobs and physical feature tests |
| **Verified working S10+ Nuxel phone** | **0%** | No handset booted into a complete Nuxel phone shell | All hardware tests above |

**Overall practical S10+ progress estimate: ~39%** (tracking estimate, not
validated user experience). Updating source scripts does not justify raising
phone readiness in the absence of on-device results.

## Release contents and truth in labeling

- `build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img`: latest offline-checked
  ARM64 boot v1 image; embedded **BEYOND2LTE EUR OPEN 26** overlay is **not**
  matched to user's particular board. Same downstream kernel and DTB binary
  as preceding upload, updated initramfs writable-root handoff.
- `build/out/s10plus/nuxel-beyond2lte-rootfs-diagnostic-fixed.img`: diagnostic
  first-light image, **not the full Fedora Nuxel phone rootfs**. Does not
  contain Fedora Python/systemd/Phosh/Phoc binaries.
- `images/s10plus/build-phone-rootfs-fedora.sh`: connected Mac Docker builder
  for the separate **real Fedora ARM64 runtime** image. It must run successfully
  before any full phone runtime can be claimed.
- `tools/s10plus/check-device-pit.py`: validates `LSI9820`, DTB/DTBO, BOOT and
  USERDATA; **PIT cannot determine actual board rev or block-size bytes**.
- `macbook-s10plus-flash-guide-final-full.md`: guarded instructions and
  handling for incomplete Heimdall EndSession handshake.

## Flashing-session limit

Heimdall success messages at 100% acknowledge file transmission at the host,
not a durable on-device commit. `Failed to receive session end confirmation`
is produced by an absent Odin protocol EndSession response; editing boot.img
or ext4 content cannot reliably resolve it. The wrapper now preserves logs,
returns a distinct error and never advertises that result as success.

## Hard stop / evidence to gather

1. Identify actual phone variant **and** its board revision, compare against
   `BEYOND2LTE EUR OPEN 26`; PIT alone cannot do this.
2. Verify device partition **sizes in bytes** and retain exact firmware/recovery
   path; PIT text has count=0 for USERDATA and no trustworthy byte unit.
3. Obtain a confirmed successful flash and bootloader handoff; restore known
   stock firmware if an unverified flash cannot boot.
4. Collect actual kernel boot log, PARTNAME resolution, framebuffer/DRM status.
5. Run Fedora ARM64 full-runtime builder; prove systemd, Python, Phosh and Phoc
   are real RPM binaries. Do not auto-enable graphical login until DRM verified.
6. Test visible display, touch, Nuxel Home, radio and power on hardware.

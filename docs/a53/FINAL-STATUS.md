# NUXEL A53 — Operation Pwnage 2000 · Final Status

**Date:** 2026-10-22 · **Branch/commit:** see `git log` (A53 commit on top of `7f64463`)
**Device:** SM-G975F beyond2lte, Fedora 43 ARM64, kernel 4.14.253, Phoc HEADLESS-1.

## Executive verdict: `PARTIAL` — orientation five-mode selector delivered & live; native app window proven; software-store/camera/flatpak blocked by hard, verified constraints.

## Final gate table

| # | Gate | Verdict |
|---|---|---|
| 1 | Native camera app installed | BLOCKED_NETWORK (no dnf, no network) |
| 2 | Native camera app shown on device | BLOCKED |
| 3 | Real S10+ camera frame captured | BLOCKED_HARDWARE (FIMC-IS S_FMT ENOTTY) |
| 4 | GNOME Software installed & displayed | BLOCKED_NETWORK |
| 5 | Real RPM install/launch/remove from store | BLOCKED |
| 6 | Flatpak sandbox supported | BLOCKED_KERNEL (`CONFIG_USER_NS` unset) |
| 7 | Real Flatpak install/launch/remove from store | BLOCKED |
| 8 | Five modes exposed in Settings | **PASS_PHYSICAL** |
| 9 | Five modes exposed in Quick Settings | **PASS_PHYSICAL** |
| 10 | Physical screen+touch rotation | BLOCKED_HARDWARE (headless compositor, no touch matrix) |
| 11 | Persistence | PASS (session); PARTIAL (reboot not run — no approval) |
| 12 | No regressions | PASS (observed, incl. USB console & Home) |

## The one decisive root cause behind gates 1–7

This Fedora image ships **no package manager** (`dnf`/`dnf5`/PackageKit all absent) and the handset
has **no network** (`wlan0` DORMANT, no `usb0`, no route). Flatpak is additionally **kernel-blocked**
(`# CONFIG_USER_NS is not set`). Installing Snapshot, GNOME Software, a test RPM, or a Flatpak is
therefore impossible on-device this session regardless of will; the only transport is a 115200-baud
serial console. These are precise, re-proven facts, not convenience excuses.

## What WAS delivered

1. **Orientation:** exact five primary modes (`Auto`, `Auto Portrait`, `Auto Landscape`,
   `Forced Portrait`, `Forced Landscape`) + two advanced reverse poses, reordered and relabelled in
   the daemon (`policy.py`), the config, Quick Settings and Settings; deployed and SHA-verified;
   persistence proven; single source of truth intact; 39 offline tests pass. Physical rotation is
   honestly blocked at the compositor/presenter and sensor layers.
2. **Native launch path (M1):** a genuine GTK4/Wayland app (`adwaita-1-demo`) opened a window on
   the physical panel; the bridge's trusted-launcher contract (no shell, id-only resolution) is
   documented.
3. **Camera triage (M2):** re-proven `VIDIOC_S_FMT → ENOTTY` on today's boot; deployed the V4L2
   probe/capture diagnostics on-device.
4. **Flatpak triage (M3):** re-proven `CONFIG_USER_NS` absent with `unshare`/`bwrap` failures.
5. **Store triage (M4):** proven no `dnf`/PackageKit/Flatpak/network.

## Explicitly NOT done (per contract)

No flashing, no kernel replacement, no sandbox bypass, no fake frames, no fake store UI, no raw rpmdb
hacks, no reboot without approval, no secret/PSK handling.

## Unblock path (future, owner-gated)

1. Owner enters Wi-Fi PSK (or a USB ECM gadget is added) → network.
2. Bootstrap `dnf5` + deps over that network → `dnf install gnome-software snapshot flatpak …`.
3. A future kernel with `CONFIG_USER_NS=y` → Flatpak sandbox.
4. A lawful FIMC-IS libcamera pipeline handler or a standard-V4L2 kernel rework → camera frames.
5. Presenter-side rotation in `nuxel-wl-fb` **plus** a matching Phoc/libinput touch matrix → real
   physical rotation.

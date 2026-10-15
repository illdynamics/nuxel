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
| Host transfer workflow | 85% | **The full image set (merged boot + Fedora 43 rootfs) is written to BOOT + USERDATA over ADB and read back byte-for-byte** — flashing/transfer is proven on this handset; the instrumented heimdall fork still classifies the separate EndSession outcome | Boot is unresolved: the device **bootloops on the Samsung logo**, so S-Boot handoff, kernel bring-up and the UFS root mount are still unverified |
| ARM64 diagnostic rootfs | 88% | Verified ext4 traversal, static Toybox, S10-specific rules, Motorola removed, ARM64 framebuffer test | Real e2fsck and PID1 running on handset |
| Fedora 43 full-runtime build automation | 65% | Docker aarch64 DNF RPM recipe, fail-closed package checks and symlink-aware verifier | Not run: no Docker/DNS/package repository in build sandbox |
| Fedora ARM64 Python3/systemd/Phosh/Phoc **inside delivered diagnostic image** | **0%** | Image explicitly contains no Fedora RPM runtime | Build on connected Mac and run strict verifier |
| Actual Phosh phone session | **0%** | No successful DRM/GPU/seat session on S10+ | Device driver bring-up, greetd/user session test, touch input |
| First-light panel probe | 35% | Static ARM64 framebuffer probe, service recipe | Compatible fbdev/DRM and panel output not tested |
| Nuxel Home app assets | 80% | PWA assets and service source included | WebKit/mobile runtime, launch and touch UI integration |
| WiFi, calls, mobile data, audio, sensors, camera | 10% | Some documented device config and mappings | Working kernel drivers, proprietary blobs and physical feature tests |
| **Verified working S10+ Nuxel phone** | **~8%** | Full image set flashed over ADB (byte-for-byte readback) and the handset **reaches the Samsung boot logo** before bootlooping — a real, repeatable boot attempt | No handset has booted into a complete Nuxel phone shell; S-Boot/kernel/init handoff unresolved |

**Overall practical S10+ progress estimate: ~52%** (tracking estimate, not
validated user experience). Flashing is now **hardware-proven** (both
partitions written and read back byte-for-byte) and the handset reaches the
Samsung logo; readiness beyond that still requires on-device boot results, so
the userspace/session rows stay near zero.

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

## Flashing status (updated 2026-10-14)

The current path is **ADB (TWRP `dd`/readback)** and it is now **proven on the
handset**: the merged boot image and the Fedora 43 rootfs were written to BOOT
and USERDATA and **read back byte-for-byte**, and the phone reboots into a
repeatable **Samsung-logo bootloop**. That moves the blocker off transfer and
onto the boot chain (S-Boot handoff / kernel / UFS root mount / init). The
read-only bootloop debug pack in `scripts/s10plus-debug-pack/` exists to capture
pstore/`last_kmsg`, recovery logs and partition state for that work.

The separate heimdall caveat still stands for the Download-Mode path: success
messages at 100% acknowledge file transmission at the host, not a durable
on-device commit. `Failed to receive session end confirmation` is produced by an
absent or unexpected Odin protocol EndSession response; editing boot.img or ext4
content cannot reliably resolve it.

An instrumented fork now lives in `external/heimdall-nuxel/`. It distinguishes
timeout / USB disconnect / malformed packet / rejected command / delayed
acknowledgement / still-in-Download-Mode, emits `NUXEL_*` result lines and
distinct exit codes, refuses to write to a device unless explicitly permitted,
and unit-tests all of these classes with mocked session outcomes (53 assertions,
plain + ASan/UBSan). The wrapper (`boot/s10plus/flash-heimdall.sh`) uses it and
never advertises success without a positive acknowledgement *and* confirmation
that the phone left Download Mode.

This is instrumentation, not a fix: the root cause is **UNRESOLVED** and cannot
be confirmed without the handset and (for the protocol-mismatch class) a USB
capture of a successful Odin flash of the same device. See
`docs/s10plus-heimdall-endsession-investigation.md`.

## Hard stop / evidence to gather

1. Identify actual phone variant **and** its board revision, compare against
   `BEYOND2LTE EUR OPEN 26`; PIT alone cannot do this.
2. Verify device partition **sizes in bytes** and retain exact firmware/recovery
   path; PIT text has count=0 for USERDATA and no trustworthy byte unit.
3. Transfer is confirmed (byte-for-byte readback) — now obtain the actual
   **bootloader/kernel handoff**: resolve the Samsung-logo bootloop, and if an
   image cannot be made to boot, restore known stock firmware.
4. Collect actual kernel boot log, PARTNAME resolution, framebuffer/DRM status.
5. Run Fedora ARM64 full-runtime builder; prove systemd, Python, Phosh and Phoc
   are real RPM binaries. Do not auto-enable graphical login until DRM verified.
6. Test visible display, touch, Nuxel Home, radio and power on hardware.

---

# UPDATE 2026-10-15 (cycle 5, candidate A15) — hardware-measured status

The earlier "bootloops on the Samsung logo / boot handoff unresolved" statements
above are **superseded**. The measured state on the real SM-G975F is now:

| Milestone | Status | Evidence |
|---|---|---|
| S-Boot loads and executes the Nuxel ARM64 kernel | PROVEN | S-Boot records + kernel `linux_banner` in the ram console |
| Embedded initramfs executes | PROVEN | `NUXEL_MARKER INITRAMFS_EXECUTED` |
| Persistent kernel logging (ram console + pstore) | PROVEN | `/proc/last_kmsg` 2 MiB, `/sys/fs/pstore/dmesg-ramoops-0.enc.z` |
| Nuxel `/init` executes, USERDATA discovered | PROVEN | `USERDATA_FALLBACK /dev/sda31`, `USERDATA_DISCOVERED` |
| Fedora ext4 rootfs mounts | PROVEN | `ROOTFS_MOUNTED /dev/sda31 ext4` |
| `switch_root` → Fedora systemd 258 PID 1 | PROVEN | `systemd[1]: systemd 258.11-1.fc43 … arm64` |
| systemd builds the full unit graph | PROVEN | A15: `Reached target basic.target` at t=3.579 s |
| Fedora binary execution from the real root | PROVEN (A14) | `FEDORA_EXEC_OK uid=0` |
| Kernel primitives measured on-device | PROVEN | `NUXEL-SYSCALL` / `NUXEL-SPAWN-PROBE` tables |
| **Stable boot without a spontaneous reset** | **PROVEN (A15)** | A15 ran **1892 s** with no software reboot; the reset was the operator's Samsung `sec_hard_reset_hook` (mission §5 case) |
| **Normal Fedora child service execution** | **NOT PROVEN** | A15: all **28** units die `Failed to spawn executor: Function not implemented`; A14's single `systemd-udevd` success did not repeat |
| systemd units attach to cgroups | NOT PROVEN | cgroup2 is mounted (`CGROUP2_MOUNTED`) but per-unit cgroup dirs are never created because nothing spawns |
| Functional framebuffer / DRM scanout | NOT PROVEN | panel/DSIM/DECON/fb all probe and register, but no `decon_enable`/UNBLANK/FRAME_DONE in 1892 s |
| Frame visible on the S10+ AMOLED | **NOT PROVEN** | A15's `FIRSTLIGHT_FRAME_WRITTEN` came with no `NUXEL_FB_INFO`/`ANIM` line — the shell swallowed them, so it is not display evidence. A16 (flashed, awaiting observation) fixes the logging and forces a DECON commit |
| Spinning penguin on the panel | **NOT PROVEN** | implemented and now resident in A16, needs an eye and a working scanout |
| Phoc / Phosh / touch phone UI | BLOCKED | needs visible output + real service execution; `# CONFIG_DRM is not set` in this 4.14 tree |

Progress percentages in the table at the top of this file are left as historical
estimates; the milestone table above is the evidence-based truth. Note in
particular that "no ADB after boot" is expected: the Fedora rootfs contains no
`adbd`, so ADB availability cannot be used as a boot-success signal.

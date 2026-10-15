# Nuxel S10+ Exynos 9820 — evidence-based integration status (2026-10-15, cycle 12 / candidate A25)

Nuxel is a **Fedora-based Linux PHONE OS**. Fedora's native init system is
**systemd**; the previous S10+ Alpine/OpenRC builder is deprecated. It was
incorrect to call the small ARM64 framebuffer bring-up image a finished phone
runtime. Progress percentages below are **engineering estimates**, not measured
completion and not probabilities of successful boot.

**2026-10-15 — the phone now BOOTS Nuxel.** The "bootloops on the Samsung logo"
statements below are historical and superseded: S-Boot loads the Nuxel ARM64
kernel, the **embedded** Nuxel initramfs runs, USERDATA is discovered, the
Fedora 43 ext4 rootfs mounts, `switch_root` hands over to **systemd 258 as
PID 1**, the panel shows the **boot animation** and a **live root console** runs
over USB. Per-step evidence: `docs/s10plus-autonomous-boot-repair/STATUS.md`,
`NEXT-ACTION.md` and the cycle documents next to them.

| Component | Engineering progress | Evidence available | Still unverified / blocked |
|---|---:|---|---|
| Device source configuration | 90% | Exynos S10+ overlays/config, S10+ udev, user-provided PIT with 41 entries; rev-26 board DTBO merged with `fdtoverlay` | Exact physical hw_rev vs. the merged overlay, firmware provenance |
| Android v1 boot packaging | 96% | The **A25 boot.img that is on the handset**: a **raw arm64 `Image` with the initramfs embedded** (`CONFIG_INITRAMFS_SOURCE`) + merged board DTB in a legacy v1 header, flashed BOOT-only with a full 51,718,144-byte SHA-256 readback PASS | Each newly built Image must be re-observed on hardware |
| Host transfer workflow | 95% | BOOT-only ADB `dd` flashes with full-partition SHA-256 readback; the instrumented heimdall fork classifies timeout/disconnect/malformed/rejected/delayed/still-in-Download-Mode | The heimdall EndSession protocol mismatch is **UNRESOLVED** (separate Download-Mode path) |
| ARM64 diagnostic rootfs | 95% | `/init` runs on-device: devtmpfs, toybox, watchdog leash, USERDATA discovery (`/dev/sda31`), ext4 root mount, `switch_root` | — |
| Fedora 43 full-runtime build automation | 85% | Fail-closed CI builds the Fedora 43 ARM64 phone userspace in an arm64 container (podman + qemu binfmt) and gates it with `verify-fedora-phone-rootfs.py` | The kernel-4.14 `libsystemd` patch is **carried in the initramfs** (pinned payload), not rebuilt by the rootfs job |
| Fedora ARM64 systemd inside the delivered image | 85% | `systemd[1]: systemd 258.11-1.fc43 … arm64` as PID 1, unit graph built, **services execute** (A18: spawn failures 29 → 0), cgroup2 mounted, journald active | The graph **stalls before `multi-user.target`** — root cause not yet named (`bootreport.txt` instruments it) |
| Phosh / Phoc phone session | **0%** | — | Needs DRM/KMS: this 4.14 vendor tree has `# CONFIG_DRM is not set` |
| Display / first light | 95% | First light on the DECON fbdev path (A16), the **original MP4 at 24.00 fps with 0 skipped frames** (A21/A22), ABGR_8888 colour order proven from the driver's own commit path (A23), the **UI process commits real frames** (A24) | Human-visible confirmation of the UI and of the animation colours |
| Interactive live console | 95% | Root shell over the USB CDC-ACM gadget, verified by the A21 acceptance suite; **HUP-proof and respawning** after a host disconnect (A24/A25) | — |
| Nuxel Home app assets | 90% | PWA assets + the fbdev-native `nuxel-ui` binary that runs on the panel (status bar, home, settings, logs, reboot/shutdown) | WebKit/mobile runtime on the phone; touch-driven UI integration |
| WiFi, calls, mobile data, audio, sensors, camera | 10% | Some documented device config and mappings | Working kernel drivers, proprietary blobs and physical feature tests |
| **Verified working S10+ Nuxel phone** | **~70%** | Nuxel boots on the SM-G975F as a real Fedora userspace: kernel → embedded initramfs → ext4 rootfs → systemd → panel animation → UI process → live root console, all flashed with full SHA-256 readback; A25 (single-instance UI + console-owned postboot supervisor) is on BOOT awaiting a power cycle | Not yet an **interactive** phone: no touch evidence (charger-mode boots), no human-confirmed UI, stalled systemd graph, no radio/modem, no Phosh |

**Overall practical S10+ progress estimate: ~80%** (tracking estimate, not a
validated user experience). The boot chain is now **hardware-proven end to end**
and every claim above names a device observation; what keeps this short of an
interactive phone is touch input, human-visible confirmation, the stalled systemd
job, radio/modem bring-up and DRM/Phosh.

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

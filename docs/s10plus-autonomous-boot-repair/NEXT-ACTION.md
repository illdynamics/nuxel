# NEXT-ACTION — cycle 6, candidate A16 (2026-10-15)

## Where the boot stands

A15 proved the boot chain is healthy for 1892 s with no software reset. A16 is on
the device now and targets the *only* thing between us and the penguin: getting a
frame onto the AMOLED and proving it from logs.

## Reading the A16 result

Everything lands in `/proc/last_kmsg` from TWRP. Look for, in order:

1. `FB_NODE /dev/fb0 is a character device`, the `FB_SYSFS /sys/class/graphics/fb0/…`
   block, or `NUXEL_FB_UNAVAILABLE no /dev/fb0`.
2. `NUXEL_FB_INFO:` + one `  field=value` line per geometry field. **Record
   `smem_start`, `smem_len`, `stride`, `yres_virtual` verbatim.**
3. `NUXEL_FB_MAPPED_BYTES`, `NUXEL_FB_BUFFERS_PAINTED`, `NUXEL_FB_READBACK_px0`,
   `NUXEL_FB_READBACK_center`.
4. `NUXEL_FB_UNBLANK_rc`, `NUXEL_FB_ACTIVATE_rc`, `NUXEL_FB_PAN_rc`.
5. `NUXEL_FB_ANIM frame=1..11`, `NUXEL_FB_ANIM_DONE frames=12`,
   `NUXEL_MARKER FIRSTLIGHT_ANIMATION_DONE`, `NUXEL_FB_DRAW_SUCCESS`.
6. `NUXEL_FB_HOLD_START` and periodic `NUXEL_FB_HOLD frame=N`.
7. `NUXEL_MARKER CGROUP2_MOUNTED`, `ROOTFS_HANDOFF_STARTED`, then `systemd[1]:` lines
   and the absence of any reboot request.

### Decision table

| Observation | Conclusion | Next step |
|---|---|---|
| Panel shows NUXEL + spinning penguin | Milestone 14/17 achieved | hold the frame, then Phosh work; verify with the operator which frame was seen |
| Panel black, `NUXEL_FB_DRAW_SUCCESS` present, ioctl rcs all 0 | The fbdev memory is **not** the DECON scanout (H-C6-F) | instrument `decon_initial_display`'s window address and the DT `memory-region`; do NOT write a guessed physical address |
| Panel black, `NUXEL_FB_UNAVAILABLE` | no /dev/fb0 in the initramfs (H-C6-C variant) | find which driver registers fb0 and when; the DECON fb registers at t≈2.034 s so the initramfs must open it later or use `/dev/graphics/fb0` |
| Panel black, `NUXEL_FB_UNSUPPORTED_PIXEL_FORMAT` / `SIZE_MISMATCH` | wrong format/geometry assumption | fix the painter to the measured geometry |
| A different `decon_enable`/FRAME_DONE still absent while rcs are 0 | the commit is accepted by the fbdev but the DECON window is not enabled | inspect `decon_initial_display` / the bootloader's window state |

## Operator agreement (unchanged)

`BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP` + `RECOVERY_ACCESS=RESTORED` when the
handset comes back to TWRP after a pending test; then capture `last_kmsg` + pstore
into `captures/<stamp>-A16-postfail/`, compare with A15 and continue. Do not repeat
an identical candidate.

## Priority-2 (parallel, offline-capable, do NOT flash the rootfs yet)

Resolve the systemd ENOSYS contradiction (RC-6.3 / H-C6-G):

1. Read-only USERDATA readback of the first ~64 MiB (contains the superblock and
   the systemd library inode region if it is early) or of the specific extents of
   `usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so`, then compare with
   `502507a7b6237a03cfcff49e389d2a38836916abdea40e36e5ba4653e9bc1234`.
2. Confirm *which* library systemd 258 actually loads (RPATH / `ldd` on the device
   is impossible; instead check `systemd`'s ELF `.dynamic` for `NEEDED`/`RPATH`
   locally and compare with the rootfs layout).
3. Read `src/basic/errno-util.h` in the 258.11 tree and confirm
   `ERRNO_IS_NOT_SUPPORTED()` covers the **positive** ENOSYS that glibc returns
   from `pidfd_spawn()`; if it does not, that alone explains the unchanged failure
   and is a one-line, source-exact fix.
4. Only then decide between: (a) re-cut the rootfs image with the corrected
   library (a separately versioned image, clean ext4 verification), or (b) the
   systemd-independent first-light path that A16 already provides.

## Standing risks

* No stock BOOT backup exists; RECOVERY untouched; every write BOOT-only.
* Host data volume is ~98 % used — every large artifact is hash-verified after
  copying out of the VM and the podman API/gvproxy socket path stays unused.

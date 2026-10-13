I cloned `msm8916-mainline/lk2nd` and read `platform/msm_shared/dev_tree.c`. The payload boot image's DT region **must be a QCDT table using lk2nd's own header layout**:

- `struct dt_table { magic; version; num_entries; }` → **12-byte header** (`DEV_TREE_HEADER_SIZE 12`), entries start at **offset 12**, V3 entry = **40 bytes**.
- Entry fields: `platform_id, variant_id, board_hw_subtype, soc_rev, pmic_rev[4], offset, size`.

Your two build attempts were both wrong in ways that match the logs exactly:
- `nuxel-ocean-boot-rootfix.img` — raw FDT (`0xd00dfeed`) → lk2nd `"Bad magic in device tree table"`.
- `nuxel-ocean-boot-qcdt*-sysb.img` — a **20-byte Qualcomm header** with `entry_size=0x15d` (349!) and byteswapped entry bytes → lk2nd read from the wrong offset → `"Unable to find suitable device tree for device (349/0x00010000/0x00010008/0)"`.

That last line also **gave me the device identity**: `msm-id=0x15d(349)`, `soc_version=0x10000`, `target_id=0x10008` ⇒ hw-id low byte `0x08`, subtype `0`. Our mainline DTB already has the right IDs (`msm-id=<0x15d 0x0>`, `board-id=<0x141 0xc100>`) — only the *packaging* was broken.

**Built + validated (offline):**
- New tool `tools/build-qcdt-boot.py` → `build/out/g7power/nuxel-ocean-boot-lk2nd-qcdt.img`
- Combined → `build/out/g7power/lk2nd-nuxel-qcdt-combined-boot.img` (lk2nd@0 + boot@512 KiB, 22,175,744 B)
- Embedded DTB verified byte-identical to the mainline ocean DTB; QCDT passes a faithful re-implementation of lk2nd's `dev_tree_validate()` + `platform_dt_absolute_match()` for every plausible hw-id/subtype. Cmdline kept `root=/dev/mmcblk0p64`.

## What I'll run the instant it re-appears

```
/tmp/fb getvar product ; /tmp/fb getvar securestate ; /tmp/fb getvar max-download-size
/tmp/fb flash dtbo   build/out/g7power/stock/firmware/extracted/dtbo.img
/tmp/fb flash boot_a build/out/g7power/lk2nd-nuxel-qcdt-combined-boot.img
/tmp/fb flash boot_b build/out/g7power/lk2nd-nuxel-qcdt-combined-boot.img
/tmp/fb flash userdata build/out/g7power/nuxel-ocean-rootfs.img
/tmp/fb reboot
```

Expected: Motorola logo → lk2nd → kernel (screen may stay black — DRM_MSM is a module; success = device stays up). Revert to stock: `flash dtbo <stock dtbo.img>` + `flash boot <stock boot.img>`.

Re-plug and say **ready** and I'll finish it.


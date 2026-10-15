# PATCHES

## P-A2-1 — ship the uncompressed arm64 `Image` in the S10+ BOOT container
**File:** new candidate artifact only (no source edit yet)
`build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A2-uncompressed.img`
**Built by:** `python3 boot/s10plus/pack-boot-v1.sh --kernel <raw Image> …`
(the packer is reused unchanged, so the header layout is identical to A1 —
deliberate single-variable change).

**Reason.** See `HYPOTHESES.md` H-KERNEL-GZIP + `DEVICE-EVIDENCE.md` E2/E4.

**Derivation (reproducible).**
```
A1 = nuxel-beyond2lte-boot-diag-cmdline-free.img   (sha256 eb77d658…)
  kernel (gzip)  = A1[2048 : 2048+16030259]        -> sha256 33cac63a…
  Image          = gunzip(kernel)                   -> 44980232 B, sha256 14b64847…
  ramdisk        = A1[16033792 : +6022352]          (unchanged)
  merged dtb     = A1[22056960 : +376101]           (unchanged, d00dfeed)
  cmdline        = "buildvariant=userdebug nuxel.device=s10plus root=… userdata …"
  addrs          = 0x10008000 / 0x11000000 / 0x10000100, page 2048
```

## KNOWN DEFECT (found, not yet fixed) — `pack-boot-v1.sh` header layout
`boot/s10plus/pack-boot-v1.sh` documents and writes a field it calls `dt_size` at
**header offset 40**. In a real `boot_img_hdr_v1` offset 40 is `header_version`
(must be `1`) and offset 44 is `os_version`. The same mis-layout is duplicated in
`tools/s10plus/patch-boot-from-upload.py` (it reads offset 40 as `dtlen`).
This is left unfixed on purpose for this cycle so A2 tests exactly one variable;
the fix is queued as **P-A3-1** (candidate A3) with the two dependent readers
updated together.

## Unchanged by this cycle
`boot/initramfs/init.sh` (A1's cmdline-independent init is kept; it is correct
for this device — S-Boot really does replace `/chosen/bootargs`).
Kernel binary, merged DTB, load addresses, page size, cmdline: all untouched.

## P-A3-1 — container normalised to the device's own booting format (candidate A3)
**Built by:** `python3 boot/s10plus/pack-boot-v1.sh --kernel <raw Image> --ramdisk
<uncompressed cpio> --dtb <merged.dtb> --v1-spec …`

Three concrete corrections, all in the BOOT container (kernel binary, DTB and
cmdline untouched):

1. **Ramdisk payload: gzip stream -> uncompressed `newc` cpio, zero-padded to an
   exact multiple of 2048 bytes (8,194,048 B).** Removes the decompressor from the
   path and makes any S-Boot sector-size rounding a no-op, because only trailing
   zeros can be affected (the archive's `TRAILER!!!` is followed by 1,144 zero
   bytes and the total size is already 2048-aligned).
2. **Header made spec-compliant `boot_img_hdr_v1`** (`header_version=1` at offset
   40, `os_version=0x18000171` at 44, `header_size=1648` at 1644) — byte-identical
   values to the unit's TWRP recovery image, the only image S-Boot is observed to
   boot. S-Boot logs the field (`[UFDT] BOOT IMG HDR V376101` vs `V1`).
3. **Fix to `boot/s10plus/pack-boot-v1.sh`** (opt-in `--v1-spec`; defaults
   unchanged so existing callers such as `tools/s10plus/patch-boot-from-upload.py`
   keep working). The tool previously wrote the DTB size into offset 40, which is
   `header_version` in the real header; the legacy behaviour is still the default
   and is documented as a defect.

**Still outstanding (queued):** `tools/s10plus/patch-boot-from-upload.py` reads
offset 40 as `dtlen`, so it must be taught about the v1 layout before it is used
with `--v1-spec` images. `--v1-spec` is therefore only used by the explicit
candidate build command, not by the default build path.

## P-A5-1 — remove the bogus `/chosen` initrd placeholder from the boot-image DTB (candidate A5)
**Found by:** decompiling the DTB embedded in the boot image
(`build/out/s10plus/debug-candidates/A2/merged.dtb`) with `dtc`:
```
chosen: chosen {
    bootargs = [00];
    linux,initrd-start = <0x84000000>;   /* 0x84000000 == pack-boot-v1.sh
    linux,initrd-end   = <0x841fffff>;      DEFAULT_RAMDISK_ADDR PLACEHOLDER */
    linux,phandle = <0x1e2>;
    phandle = <0x1e2>;
};
```
`0x84000000` is the S10+ packer's *documented placeholder* ramdisk load address, and
`0x841fffff` is a 2 MiB window - nothing to do with a real 6-8 MB initramfs.

**Why it matters:** on this boot path S-Boot merges the boot image's DTB
(`[UFDT] BOOT IMG HDR V1.. FINDING DTB ENTRY`, `dtb_update`, `Updating device tree
@0x8a000000`). The kernel takes its initrd from `/chosen/linux,initrd-start|end`.
A stale placeholder pair in the image is exactly the kind of thing that leaves the
kernel reading the initrd from the wrong physical address while still being told
the right *length* - which is precisely the signature observed in A2/A3/A4
(`Freeing initrd memory: 8128K` = exactly our 8,323,072 B payload, yet
`rootfs image is not initramfs (junk in compressed archive)`).

**Change:** `dtc` decompile -> delete `linux,initrd-start`, `linux,initrd-end` and
the empty `bootargs` from `/chosen` (keeping the phandles) -> recompile
(376,101 -> 376,689 B). Everything else in A5 is identical to A4.

**Candidate:** `build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A5-dtb-fix.img`
sha256 `6950241c52320688f28bfc1a0c0426f28e3884e5772934853759354aa97a88d1`.
Write + readback **VERIFIED**; reboot 2026-10-15T07:31:59Z.

## Defects found in the S10+ packer (all confirmed against a booting image)
| # | Defect | Status |
|---|---|---|
| 1 | `pack-boot-v1.sh` wrote the DTB size into header offset 40, where `boot_img_hdr_v1` requires `header_version=1`; `os_version` (offset 44) left 0. S-Boot logs the value (`BOOT IMG HDR V376101` vs `V1`) and even failed `set os_version`. | **fixed** (`--v1-spec`, used by A3+) |
| 2 | The DTB the packer embeds inherits `/chosen/linux,initrd-start/end` placeholders (`0x84000000`/`0x841fffff`) that misdescribe the initrd to the kernel. | **patching DTB in A5** |
| 3 | The packer's example/default kernel input is `Image.gz`; on this unit S-Boot jumps straight to `kernel_addr`, so a gzip payload is executed as code (7 silent loads). Only a raw `Image` works. | **fixed** (A2+); `pack-boot-v1.sh` should reject/warn on gzip kernels |
| 4 | `tools/s10plus/patch-boot-from-upload.py` reads header offset 40 as the DTB length and assumes the legacy layout, so it cannot consume `--v1-spec` images. | **open** |

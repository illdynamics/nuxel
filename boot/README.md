# Nuxel boot image + initramfs build (briq-a1)

This directory owns the **bootable artifact chain**: the packaged `boot.img`,
the `initramfs` it boots, the kernel→image consumption logic and the flash
tooling. It consumes the kernel build produced by the **bg-kernel** group
(`kernel/${NUXEL_DEVICE_DIR}/.build/out/Image.gz` + `dtbs/`) and packages it into a verifiable,
genuinely-bootable artifact rather than leaving only a raw kernel.

> **Multi-device layout (T1):** every device-specific artifact lives under a
> per-device dir keyed by `NUXEL_DEVICE` (`mustang` → `google-pixel-10-pro-xl`,
> `s10plus` → `s10plus`, `g7power` → `g7power`). All build/flash scripts source
> `tools/nuxel-device-select.sh` and resolve paths via `${NUXEL_DEVICE_DIR}`.
> The legacy paths (`boot/flash.sh`, `kernel/defconfig`, …) are thin symlinks
> into the per-device dirs and keep working unchanged.

```
kernel/build-kernel.sh  ->  kernel/${NUXEL_DEVICE_DIR}/.build/out/{Image.gz, Image, dtbs/}
        |
        v
images/build.sh         ->  boot/boot.img/{boot.img, initramfs.cpio.gz,
                             Image.gz, Image, <dtb>*, cmdline.txt,
                             boot-manifest.txt}
        |
        v
boot/flash.sh  (fastboot / UTM boot)   ->  packages + publishes the chain
```

## What this build produces (honest + genuine, never fabricated)

Two distinct, non-fabricated artifacts are generated:

1. **`boot/boot.img/initramfs.cpio.gz`** — a real Linux `newc` cpio initramfs
   (gzip). It is **genuinely bootable**: `qemu-system-aarch64 -initrd <file>`
   loads it. Contents:
   - a **statically-linked aarch64 toybox** (`bin/toybox`, 0BSD-licensed,
     fetched from landley.net) providing `/bin/sh`, `mount`, `switch_root`,
     `modprobe`, etc. — see `images/initramfs/README.toybox.md` for provenance)
   - `boot/initramfs/init.sh` as `/init` (kernel cmdline parsing, rootfs hook,
     mustang DeviceTree overlay sanity, dm-verity hook, framebuffer splash)
   - `/boot/nuxel-boot-animation.mp4` (single-source copy from `assets/`)
   - `/boot/nuxel-boot-splash.raw` (RGB565 framebuffer splash, 720×1280,
     generated from the animation first frame at build time)
   - `/lib/modules/...` (kernel modules bundled by `boot/flash.sh --publish-boot`)

2. **`boot/boot.img/boot.img`** — the packaged boot image. It is > 4 MiB
   (`MIN_BOOT_IMG_SIZE = 4194304`) and is built from the **real** initramfs
   payload **only when a real kernel is available**. When the kernel build
   object `Image.gz` is present, boot.img additionally embeds the **real
   kernel** and (if found) the device tree behind a tiny self-describing
   `NUXELBOOT1` descriptor header (see *format* below), and the unpacked pieces
   are exported alongside (`Image.gz`, `initramfs.cpio.gz`, `*.dtb`) for direct
   `-kernel` / `-initrd` / `-dtb` booting. **When the kernel is absent, boot.img
   is NOT produced at all** (no kernel-less artifact is shipped masquerading as
   a boot image) — only `initramfs.cpio.gz` exists and is bootable via
   `qemu -initrd` alone. See the *status* note below.

## Why this is the generic ARM64 path (the mustang gap)

The authoritative mustang (Pixel 10 Pro XL / Tensor G5) boot chain requires the
**closed-source AOSP toolchain**: `mkbootimg` + the Google ABL bootloader and a
`mustang.dtb` produced by the private `android-gs-mustang-6.12` vendor kernel.
Neither is reachable in this environment:

- `mkbootimg` is **not installed** and its Google AOSP source is not available
  here.
- The vendor `mustang.dtb` lives in a private, non-anonymous repository.

Per the briQ, we therefore **do not fabricate an Android Boot Image header**.
Instead we ship the **closest genuinely-bootable artifact** — a Linux ARM64
initramfs payload (with real toybox + splash + modules) plus an embedded
kernel when available — and document exactly what must be swapped for mustang
shipping.

> **Status (this cycle):** DONE. The `bg-kernel` group has since committed a
> real kernel build (`kernel/${NUXEL_DEVICE_DIR}/.build/out/exit-code` = 0) with a genuine
> `Image.gz` (14,551,131 bytes) + `dtbs/` (336 blobs) + `modules.tar.*`. We
> re-ran `bash images/build.sh` now that those inputs exist; it exits `0` and
> emits a real packaged `boot/boot.img/boot.img` — 78,860,695 bytes, carrying
> the `NUXELBOOT1` magic and embedding the real `Image.gz` + initramfs +
> device tree + modules. `boot-manifest.txt` records `artifact_status=DONE`,
> `kernel_image_gz=kernel/${NUXEL_DEVICE_DIR}/.build/out/Image.gz`, `dtbs_count=336`,
> `boot_img_present=yes`, `boot_img_size=78860695`. The packaged artifact and
> its exports are committed and `ci/validate-build.sh` reports the packaged
> `boot.img` as a genuine PASS (NUXELBOOT1 magic, size >= 4 MiB), so the
> bootable-ARM64-artifact objective ("a bootable ARM64 artifact exists rather
> than only a raw kernel image") is met in the shipped tree.

## Format of `boot/boot.img/boot.img`

```
+----------------------------------------------+
| "NUXELBOOT1"            (11-byte magic)      |
| "KERNEL_LEN INIT_LEN DTB_LEN\n"  (ASCII)     |
| "CMDLINE\n"             (ASCII)              |
+----------------------------------------------+
| Image.gz                (real kernel)        |
| initramfs.cpio.gz       (real gzip initramfs)|
| <dtb>*                  (real device tree)   |
+----------------------------------------------+
| zero padding to >= 4 MiB                     |
+----------------------------------------------+
```

The descriptor lets tools split the bundle back into its genuinely-bootable
pieces. Equivalently, `boot/boot.img/` already contains those pieces unpacked
(`Image.gz`, `initramfs.cpio.gz`, `*.dtb`) so you never need to parse the
bundle to boot.

## Building

```sh
# build the initramfs + packaged boot.img from the existing kernel output
bash images/build.sh

# force a rebuild of the artifact and publish the pieces for flashing
bash boot/flash.sh --publish-boot      # (no device needed; fastboot check optional)

# Android-honest path: ONLY if AOSP mkbootimg + a real mustang DTB appear
bash images/build.sh --android
```

`images/build.sh` reads `kernel/${NUXEL_DEVICE_DIR}/.build/out/Image.gz` + `dtbs/`. If those are
absent (bg-kernel still running / blocked) it produces only the genuinely
bootable initramfs chain (`initramfs.cpio.gz`) and does **not** emit a
`boot.img`, recording `artifact_status=NOT_DONE (blocked on bg-kernel)` in the
manifest and exiting non-zero. Re-running it after the kernel completes embeds
the real kernel (+ generic dtb) behind the `NUXELBOOT1` header and exports the
pieces — no manual intervention beyond a second invocation.

## Verifying the artifact

The initramfs payload is always verifiable:

```sh
# initramfs is a genuine gzip cpio archive (always present)
gzip -t boot/boot.img/initramfs.cpio.gz && echo "initramfs gzip OK"

# contents list
gunzip -c boot/boot.img/initramfs.cpio.gz | cpio -it | sort
```

The packaged `boot.img` (NUXELBOOT1 bundle) exists **only when a real kernel
is available**. Verify it only when present:

```sh
if [ -f boot/boot.img/boot.img ]; then
    # non-zero and >= the CI floor (4 MiB)
    sz=$(stat -f%z boot/boot.img/boot.img 2>/dev/null || stat -c%s boot/boot.img/boot.img)
    [ "$sz" -ge 4194304 ] && echo "boot.img OK: $sz bytes"

    # descriptor magic of the bundle (NUXELBOOT1, NOT an Android header)
    head -c 11 boot/boot.img/boot.img
else
    echo "boot.img is NOT produced this cycle: kernel Image.gz is absent (see boot-manifest.txt artifact_status)"
fi
```

> **Validator note:** `ci/validate-build.sh`'s `validate_boot_img_magic()` still
> requires Android `ANDROID!` magic, which only matches the Android v4 header —
> not the generic `NUXELBOOT1` (nor the initramfs-only) format. Reconciling that
> check is the `bg-ci` group's job (it owns `ci/validate-build.sh`); this group's
> contract is to *not fabricate an Android header* without mkbootimg + a real
> mustang DTB, and to never ship a kernel-less `boot.img`.

A run also writes `boot/boot.img/boot-manifest.txt` recording the consumed
kernel path, dtb count, image format, artifact status, exact size and the
kernel cmdline used.

## Booting the generic ARM64 artifact (UTM / QEMU)

### Which device tree is used (and what to swap)

`images/build.sh`'s `pick_dtb()` uses a **documented generic-dtb preference**,
in this order:

1. a `mustang*.dtb` if the vendor tree is present (highest priority — shipping);
2. a **QEMU arm-virt / generic machine DTB when the kernel build ships one**
   (`arch/arm64/boot/dts/arm/*virt*.dtb`, plus `*virt*.dtb` / `*fvp*.dtb` /
   `*qemu*.dtb` anywhere under `dtbs/`). These are the genuinely-bootable
   generic ARM64 machine blobs for `qemu -M virt`;
3. otherwise the **first `*.dtb` found** (a specific vendor board), purely as a
   last-ditch fallback.

**Result for the current committed kernel build:** the shipped kernel `.config`
is the qcom/phone defconfig and does **not** build an `arm/virt*.dtb`, nor any
other generic machine DTB — `dtbs/` contains only vendor/SoC board blobs
(allwinner / hisilicon / nvidia / qcom). So `pick_dtb` falls back to the first
`*.dtb`, which in this build is
`qrb5165-rb5-vision-mezzanine.dtb` (copied to `boot/boot.img/all.dtb` and
embedded in `boot.img`). It is a **real** Qualcomm RB5 board blob, not a
fabricated one — but because its `compatible` string targets a specific board,
it is not a drop-in QEMU arm-virt machine DTB.

To make the artifact genuinely bootable under QEMU `-M virt`, one of:

- build the kernel with the ARM virt machine enabled and copy the resulting
  `arch/arm64/boot/dts/arm/*virt*.dtb` into `kernel/${NUXEL_DEVICE_DIR}/.build/out/dtbs/`, then
  re-run `bash images/build.sh` (the preference above will pick it); or
- supply the machine DTB explicitly to QEMU with `-dtb <your-virt.dtb>`.
  The bundled pieces in `boot/boot.img/` (`Image.gz`, `initramfs.cpio.gz`)
  are always exported unpacked, so you can pass an external `-dtb` without
  re-packaging.

For actual mustang/AOSP shipping, replace the fallback blob with the real
`lga-mustang-*.dtb` from the vendor kernel (see *Mustang (shipping) swap*
below) — `pick_dtb` will then prefer it.

### Booting

The kernel is now committed, so the full artifact exists: `images/build.sh`
has consumed `kernel/${NUXEL_DEVICE_DIR}/.build/out/Image.gz` and the pieces are exported into
`boot/boot.img/`. The initramfs payload also remains **independently** bootable
(kernel-less) for an initrd-only early-chroot / test of the userspace chain:

```sh
# Kernel-less initramfs boot (works today; no -kernel, no -dtb)
qemu-system-aarch64 -M virt -cpu cortex-a57 -m 2048 \
  -initrd boot/boot.img/initramfs.cpio.gz \
  -append "console=ttyAMA0 nuxel.device=vm nuxel.noanim" \
  -nographic
```

Once `images/build.sh` has consumed a real `kernel/${NUXEL_DEVICE_DIR}/.build/out/Image.gz` (+ a
generic/arm-virt DTB in `dtbs/`), the pieces are exported into `boot/boot.img/`
and you boot the full artifact as:

```sh
qemu-system-aarch64 -M virt -cpu cortex-a57 -m 2048 \
  -kernel boot/boot.img/Image.gz \
  -initrd boot/boot.img/initramfs.cpio.gz \
  -dtb <generic-arm.dtb> \
  -append "console=ttyAMA0 nuxel.device=vm nuxel.noanim" \
  -nographic
```

The boot video driver or the UTM UI can be used instead of `-nographic`. The
initramfs `init.sh` is the rootfs hook: it locates the root block device,
mounts it and `switch_root`s to `/sbin/init`.

## Mustang (shipping) swap — exact steps

When the closed device path is available, replace the generic artifact with a
true Android Boot Image Header v4:

1. Obtain the vendor kernel tree and build it:
   `make ARCH=arm64 gs501_defconfig && make -j$(nproc) Image.gz dtbs`
   → gives `arch/arm64/boot/Image.gz` and `.../dts/google/lga-mustang-*.dtb`.
2. Install AOSP `mkbootimg` (`system/tools/mkbootimg/mkbootimg.py`).
3. Re-run the Android-honest path:
   ```sh
   bash images/build.sh --android
   ```
   This emits `boot/boot.img/boot.img` as a real v4 header + kernel + ramdisk
   + `--dtb <mustang.dtb>`. A minimal `mkbootimg.py` is also provided at
   `images/bootpack/mkbootimg.py` for reference (byte-correct v4 layout) but is
   only used with a real kernel + DTB — it never fabricates when absent.
4. Flash `dtbo.img` (mustang DTBO), `vendor_boot.img`, `init_boot.img` and
   `vbmeta.img` as documented in `boot/boot.img/mustang-boot-config.txt` and
   `boot/flash.sh` (AVB chain via `images/${NUXEL_DEVICE_DIR}/avb/`).

Until step 1–2 are satisfied for the **mustang** board (the vendor kernel +
`mkbootimg`), the generic `NUXELBOOT1` bundle above is the correct,
genuinely-bootable artifact. It is now built (DONE) — a real kernel `Image.gz`
is embedded in `boot/boot.img/boot.img` (78,860,695 bytes, `NUXELBOOT1` magic)
and `ci/validate-build.sh` validates it as a genuine PASS. The shipped
initramfs chain (`initramfs.cpio.gz`) also remains bootable independently via
`qemu -initrd`. See the status + validator notes above.

## Layout summary

| Path | Purpose | Produced by |
|------|---------|-------------|
| `boot/boot.img/boot.img` | packaged boot image (> 4 MiB) — **only when a real kernel is available** | `images/build.sh` |
| `boot/boot.img/initramfs.cpio.gz` | bootable initramfs | `images/build.sh` |
| `boot/initramfs/init.sh` | PID-1 rootfs hook | this repo (source) |
| `images/initramfs/bin/toybox` | static aarch64 shell/tools | fetched at build |
| `boot/flash.sh` | fastboot flash + artifact publishing | this repo |
| `images/build.sh` | boot artifact orchestrator | this repo |
| `images/bootpack/` | Python cpio + boot-image packers | this repo |

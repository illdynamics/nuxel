# INITRAMFS DELIVERY — ROOT CAUSE (found A20, 2026-10-15)

## The finding in one line

**BOOT-partition-only updates do NOT change `/init` on this board.** The kernel
carries a *built-in* initramfs, and the bootloader advertises an initrd to the
kernel **without actually populating the memory it points at**, so every external
ramdisk is discarded. Any change to `boot/initramfs/init.sh` only takes effect if
the **kernel is rebuilt with that initramfs embedded**.

This was already written down in A6 (`boot/s10plus/build-kernel-a7-embedded-initramfs.sh`
header) and then lost sight of: A7…A19 all rebuilt the kernel, so their changes
appeared to be delivered by the BOOT image. A20 reused `Image-A19` and therefore
ran A19's `/init` no matter what was flashed to BOOT.

## Evidence (all measured, A20)

### 1. The kernel image contains the initramfs

`build/out/s10plus/debug-candidates/A19/Image-A19`, 48,781,320 B, has a **gzip
stream at offset 33,809,680** that inflates to exactly **8,774,496 B** — the A19
`initramfs.cpio` — and `/init` extracted from it hashes to
`dbadbb09c51cb7505ec90c43618bb3185ee65c499a6554ae1ffe3a64fcff7e98`, **byte-identical
to A19's `init.sh`**. The same is true of `A18/boot.img`'s kernel (embedded
8,640,476 B = A18's cpio).

### 2. The external ramdisk is rejected

Three consecutive A20 flashes proved it, each with a full SHA-256 readback of
BOOT `PASS`:

| A20 build | external ramdisk | kernel verdict | `/init` that ran |
|---|---|---|---|
| lzma 2,424,832 B (`0a22a570…`) | `Freeing initrd memory: 2368K` | `rootfs image is not initramfs (junk in compressed archive)` | A19's |
| gzip 3,866,624 B (`b8b596e7…`) | `Freeing initrd memory: 3776K` | same junk verdict | A19's |

A19's own ramdisk was lzma too, and the A18/A19 ram console contains the same
`junk in compressed archive` / `Freeing initrd memory: 2368K` pair. **The external
ramdisk has never worked on this bootloader.**

The delivered length is correct (3776 KiB = 3,866,624 B = the exact gzip payload,
and the payload starts with `1f 8b 08` at offset 0 in the image). The bytes the
*kernel* reads are therefore not the bytes in the image — i.e. S-Boot advertises
`/chosen/linux,initrd-start|end` and does not fill that memory. `init.sh`'s own
probe agrees: `chosen linux,initrd-start: unreadable`.

### 3. The smoking-gun behaviour difference

With `Image-A19` on BOOT, every A20 flash produced **identical** runtime
behaviour, including text that only exists in A19's init:

```
nuxel-init: FIRSTLIGHT hold started pid=          <- A19 wording, removed in A20
NUXEL_MARKER ANIMATION_HOLD_PID=
... 42.33 s of dead boot time (A19's 20-iteration shell scan)
/var/lib/nuxel/fb-anim.pid  ABSENT
/var/lib/nuxel/animation     ANIM_STAGE=FIRST_LIGHT
```

After rebuilding the kernel with A20's initramfs embedded, the same BOOT image
booted and **behaved differently** (`NUXEL_INIT_REV=A20-original-mp4-animation`,
gadget bound, system stayed up for minutes).

## Consequences for the project — corrections to earlier records

1. **`build/out/s10plus/debug-candidates/A*/initramfs.cpio` alone is not a
   deliverable.** It is only a *source* for a kernel build. Every candidate must
   ship `Image-A<NN>` built with `CONFIG_INITRAMFS_SOURCE=<that cpio>`.
2. `boot/s10plus/build-candidate.sh`'s `--compress lzma|gzip` choice is, on this
   board, **cosmetic**: the external ramdisk is ignored. It is kept only because a
   future kernel with working initrd handoff may use it.
3. Any earlier claim that a change was "delivered by the BOOT partition alone"
   needs re-reading with this in mind. A18/A19 were saved by the fact that their
   kernels were rebuilt.
4. `--compress gzip` is NOT a workaround; the failure is not a decompressor
   problem.

## The corrected delivery pipeline

```
boot/initramfs/init.sh                                  (edit)
   -> tools/s10plus/aNN/build-aNN-initramfs.sh          -> initramfs.cpio
   -> podman exec nuxel-kb  sh /b/a17/kbuild-aNN.sh     -> Image-aNN      <-- REQUIRED
        (sets CONFIG_INITRAMFS_SOURCE=<that cpio> in the kernel .config, make Image)
   -> boot/s10plus/build-candidate.sh --kernel Image-aNN -> boot.img
   -> 03-flash.sh --boot-only --execute                 -> BOOT partition
```

`kbuild-a20.sh` (in the container at `/b/a17/`) is the working implementation and
is mirrored into the repo as `tools/s10plus/a20/kbuild-a20.sh`.

## Verification that a kernel really embeds the archive

```sh
python3 - <<'PY'
import zlib
d=open('build/out/s10plus/debug-candidates/A20/Image-A20','rb').read()
for i in range(len(d)-3):
    if d[i]==0x1f and d[i+1]==0x8b and d[i+2]==0x08:
        try:
            e=zlib.decompressobj(16+zlib.MAX_WBITS).decompress(d[i:i+40*1024*1024])
        except Exception: continue
        if e[:6]==b'070701':
            print("offset",i,"size",len(e),
                  "NUXEL_INIT_REV" in str(e), "nuxel-anim-player" in str(e)); break
PY
```

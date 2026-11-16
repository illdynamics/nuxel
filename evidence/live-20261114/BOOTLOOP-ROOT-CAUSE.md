# S10+ bootloop root cause — 2026-11-14

Device: SM-G975F / beyond2lte / R58M75KDB2X. Boot partition image:
`0945cc8d4aa6e80a7757c8cc8aaaa1a6de307e22f4d0465513945cb027973f38`
(`build/out/s10plus/debug-candidates/p113000-nfc-r1/boot-nfc-k95.img`),
kernel `4.14.253-gf7194c1d15ed-dirty #95 Sat Nov 14 00:18:27 CET 2026`.

## Symptom

Every boot reaches the Fedora userspace handoff (systemd PID 1 alive, udev
running, `nuxel-console` up) then, ~7-10 s in, the kernel panics and Samsung's
panic path resets the SoC (`sec_reboot (0, panic)`), so the phone returns to
TWRP: the "bootloop". It is NOT an initramfs failure and NOT TWRP being
re-entered by request.

## Evidence

`last_kmsg.txt` (from TWRP `/proc/last_kmsg`) holds three boots, three panics,
all identical:

```
nfc nfc0: Detected new firmware version
Unable to handle kernel paging request at virtual address ffffff80117ab000
pc : sha1_ce_transform+0x28/0x210
lr : sha1_ce_finup+0x1d4/0x234
Call trace:
  sha1_ce_transform -> crypto_shash_finup -> shash_digest_unaligned
  -> crypto_shash_digest -> s3fwrn5_fw_download+0xa4/0x6d8
  -> s3fwrn5_nci_open -> nci_dev_up -> nfc_dev_up
Kernel panic - not syncing: Fatal exception
```

The numeric state is completely correct up to the crash: NCI reply frame from
the bootloader (`81 00 0e 00 ...`), `bootinfo hw=82.00.01.00`, image header
parsed (`image_off=0x12c sectors=37 sig=128 custom_sig=128`), version
`0x02090045` - all matching `sec_s3nrn82_firmware.bin`
(sha256 `d315cd8b...0bfb`, 151852 bytes, shipped on the phone's own vendor
partition and verified complete: 300 + 37*4096 = 151852).

`sha1_ce_transform+0x28` disassembles to `ld1 {v8.4s-v11.4s}, [x1], #64`
(the first input-block load). `+0x1d4` in `sha1_ce_finup` is exactly the
`sha1_base_do_finalize()` path taken when the length is NOT a block multiple
(SHA1_BLOCK_SIZE is 64, image size 151552 is not). In that path the C glue
calls the asm block function with the trailing block **built on the stack**
(`sha1_base_do_finalize -> __sha1_base_do_finalize`), i.e. the digest state and
the padded block live in the crypto shash descriptor.

This kernel has `CONFIG_VMAP_STACK=y` with 4 KB pages, so
`arch/arm64/include/asm/memory.h` defines `THREAD_SIZE` as `PAGE_SIZE` =
**4096 bytes** (MIN_THREAD_SHIFT 14 > PAGE_SHIFT 12 selects PAGE_SHIFT).
`shash.c` accepts a `descsize` up to `PAGE_SIZE / 8` = 512 bytes, so the
descriptor itself cannot be the problem; what overflows is the work the
SHA-1 finalize path does on a 4 KB guard-page stack after the deep call chain
(`firmware loader -> nci -> sha1-ce`). The fault address is a kernel address
with `*pte=0`, i.e. an address that is *just past* the mapped object: the stack
dump dies exactly where the guard page starts.

TWRP's own kernel (same `CONFIG_CRYPTO_SHA1_ARM64_CE=y`) reports
`sha1-ce` selftest `passed`, so the hardware Crypto Extensions themselves are
fine; this is a stack/descriptor-size assumption, not bad silicon and not a bad
firmware file (`tools/s10plus/nfc-hash-probe` validates the image layout and
every page of the digest region on the device: PASS).

## Why NFC at all

The boot command line and the DT have no NFC node; `sec_nfc` defers to the
NUXEL `s3fwrn5_i2c` driver, which at bring-up reads the image and - because the
controller reports `controller version 0` - decides `need_update = 1` and
downloads `sec_s3nrn82_firmware.bin`. That download hashes the 148 KB image
with SHA-1 in a workqueue, and the workqueue is what panics.

## Fix direction (implemented in this run)

* Do not let a boot-blocking download depend on the buggy path: on S10+ the
  image is only downloaded when `force_fw_update` is explicitly requested, and
  a NUXEL boot flag/sysfs switch always has a safe escape route. If a download
  is genuinely needed it must hash through a safe path (streamed
  `crypto_shash_update` in bounded chunks, no stack finalize of the entire
  image and no NEON in a non-SIMD workqueue context).
* Make any crash here non-fatal: the NFC bring-up runs in a workqueue; a
  failure must log and disable itself, never panic the device (the panic comes
  from `oops=panic` on the S-Boot command line, which userspace can clear via
  `sysctl kernel.panic_on_oops` only after boot - hence the userspace
  mitigation in the boot sequence and the initramfs).

## Files

* `last_kmsg.txt` raw (2 MiB), `last_kmsg.clean.txt` (NUL-stripped)
* `dmesg-ramoops-0.txt` (pstore part 1)
* `boot-current.img` (exact image on the partition, verified sha256)
* `sec_s3nrn82_firmware.bin` (copy from the phone's vendor partition)
* `lock.json` (lockscreen credential state, see PIN report)
* `twrp-config.txt`

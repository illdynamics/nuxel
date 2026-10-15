# TEST-RESULTS

## T-A2-offline — A2 image validation (2026-10-15, Mac, no device)
| Check | Result |
|---|---|
| initramfs regression suite `boot/s10plus/tests/test-init-cmdline-independence.sh` | **8 passed, 0 failed, 0 skipped** |
| `pack-boot-v1.sh` exit status | 0 |
| header magic | `ANDROID!` |
| header fields vs A1 | **only `kernel_size` differs** (`0xf49a33` -> `0x2ae5808`); every other u32 and bytes 16..1632 identical |
| kernel payload | starts `00 c0 69 14 …`, `ARMd` at 0x38, `is_gzip = False` |
| kernel `Image` sha256 | `14b64847195dbea94b19de9765ba0306eb099a58675ade9dcf2bc83d184f87de` |
| kernel `Image` size | 44,980,232 B; `text_offset=0x80000`, `image_size=0x32bc000`, `flags=0xa` |
| ramdisk | byte-identical to A1 (`a[rso_a:+n] == b[rso_b:+n]`) |
| merged DTB | byte-identical to A1, magic `d00dfeed`, 376,101 B |
| image size / fit | 51,384,320 B; BOOT partition 57,671,680 B -> fits, 6,287,360 B slack |
| diagnostic slot (57,606,144) | left untouched by the 51 MiB write |
| trailing bytes after DTB | all zero |
| A2 sha256 | `9ba1bd210d8859ea91e90bbce19ce3a57d9b1513ece66380d7424dcdaade7738` |

Note: offline validation cannot establish that S-Boot accepts the image or that
the kernel executes. Only the hardware boot test can.

## T-A3-offline — A3 image validation (2026-10-15, Mac, no device)
| Check | Result |
|---|---|
| `pack-boot-v1.sh --v1-spec` exit status | 0 |
| header bytes [0:48] | `ANDROID!` / kernel 44,980,232 / 0x10008000 / ramdisk 8,194,048 / 0x11000000 / tags 0x10000100 / page 2048 / **version 1** / **os_version 0x18000171** |
| v1 tail @1632 | `recovery_dtbo_size=0`, `offset=0`, `header_size=1648` — same shape as the TWRP image |
| kernel payload | raw `Image`, `ARMd` @0x38, `is_gzip=False` |
| ramdisk | `070701` newc magic, 8,194,048 B, `%2048 == 0`, `%512 == 0` |
| ramdisk content | 65 records, `TRAILER!!!` at 8,192,904, remaining 1,144 B all zero, `/init` + `bin/toybox` present |
| DTB | `d00dfeed` at 53,178,368, byte-identical to the A2 merged DTB, 376,101 B |
| image size / fit | 53,555,200 B, BOOT 57,671,680 B -> fits with 4,116,480 B slack |
| diagnostics slot 57,606,144 | untouched by a 53 MiB write |
| sha256 | `57ff4d5e7064305908068c19f1beead2c33e77ecc480add7b9c6f9c910ba4f6e` |
| device write + readback | **VERIFIED BOOT: `57ff4d5e…`** via `03-flash.sh --boot-only --execute` |

---

## T-GATES — `boot/s10plus/tests/test-boot-image-gates.sh` (2026-10-15, Mac, offline)
**11 passed, 0 failed, 0 skipped.** Proves the new release gate reproduces the
hardware record rather than a description of it:

| Fixture | Expectation | Reason it is a meaningful fixture |
|---|---|---|
| `nuxel-beyond2lte-boot-diag-cmdline-free.img` (A1) | FAIL | gzip kernel + legacy header 376101 — 7 silent loads on hardware |
| `nuxel-beyond2lte-boot-merged-fixed.img` | FAIL | same two defects (the old builder's default input) |
| `nuxel-beyond2lte-boot-A2-uncompressed.img` | FAIL | raw kernel but still legacy header 376101 |
| `nuxel-beyond2lte-boot-A5-dtb-fix.img` | PASS | hardware-proven: its kernel executed and panicked in pstore |
| `twrp-recovery-original.img` | PASS | the only ramdisk S-Boot is observed to deliver AND unpack |
| synthetic gzip kernel through the packer | refused | `pack-boot-v1.sh --strict` |
| synthetic legacy header | FAIL | DTB size at offset 40 |
| ramdisk with `/init` removed | FAIL | kernel would fall back to SYSTEM |
| ramdisk truncated to 8,192,000 B | FAIL | reproduces the A3 failure mode exactly |
| image larger than the BOOT partition | FAIL | capacity gate |
| `newc.py replace` with identical bytes | identical | no silent archive corruption |

## T-A6-offline — A6 validation (2026-10-15, Mac, no device)
| Check | Result |
|---|---|
| gate (`verify-boot-image.py`) | **PASS** |
| image size / fit | 51,390,464 B vs BOOT 57,671,680 B -> 6,281,216 B slack; diag slot 57,606,144 untouched |
| header | `ANDROID!`, page 2048, `header_version=1`, `os_version=0x18000171`, `header_size=1648`, `second_size=0` |
| kernel `Image` | 44,980,232 B, `ARMd` @0x38, **byte-identical to A5/A4/A3/A2** sha256 `14b64847…` |
| appended DTB | **byte-identical to A5**, FDT totalsize 376,689 B, no `/chosen/linux,initrd-*` placeholder |
| ramdisk container | LZMA-alone, props `0x5d`, dict `0x800000`, size `0xffffffffffffffff` — **identical shape to TWRP's** |
| ramdisk size | 6,029,312 B = 92 x 65536 (= 1472 x 4096 = 2944 x 2048) -> every rounding rule is a no-op |
| ramdisk decompression | independent `lzma.LZMADecompressor(FORMAT_ALONE)` -> 8,260,060 B, `eof=True`, starts `070701` |
| cpio | 68 records, `TRAILER!!!` record at 8,194,400 (logical end 8,194,524) + 65,536 zero bytes inside the stream |
| `/init` | 26,413 B, mode 0o100755, sha256 `8aba1434…` == `boot/initramfs/init.sh` |
| initramfs additions | `dev/console` (char 5:1, 0600), `dev/null` (char 1:3, 0666), `bin/sh -> toybox` |
| sha256 | `ba4f70c6384bd018e5d7d29bf0c28db458f5d0f2671410837649c6ab548ebc49` |
| device preflight | **PREFLIGHT PASS** (BOOT -> /dev/block/sda14, 57,671,680 B, no USERDATA target) |

---

## T-A7-device — A7 hardware result (2026-10-15, Mac + handset)
| Check | Result |
|---|---|
| flash + readback | **VERIFIED `f8587521…`** (46,409,728 B) |
| S-Boot parsed the new container | `kernel size = 0x2b66000, ramdisk size = 0x80000` (524,288 = the LZMA ramdisk exactly) |
| built-in initramfs unpacks | **`NUXEL-KDIAG unpack verdict: message=(none) state=7`** -> success, twice per boot |
| external initrd | `external_initrd=1 start=ffffffc009000000 end=ffffffc009080000 len=524288`; head bytes `5b 20 20 20 20 31 2e 30 …` = kernel console text; `method=(none)`; `message=junk in compressed archive` |
| `/init` executed | `RAMDISK:`=0, `SAR_RD`=0, `init group exit`=0, `Failed to execute /init`=0 -> `/init` present, `prepare_namespace()` skipped, exec succeeded |
| `/dev/console` usability (measured live) | `echo > /dev/console` -> `No such device` (ENODEV); `echo > /dev/kmsg` -> rc=0 |
| why the boot ended | `hard_reset_hook_callback` -> `Fatal exception in interrupt` at t=37 s and t=68 s; `hung_task: blocked tasks` panic at t=242 s |
| progress vs cycle 2 | kernel lifetime 2 s (A2-A5) -> 37/68/242 s |

## T-A8-offline — A8 validation (2026-10-15, Mac + container, no device)
| Check | Result |
|---|---|
| gate | **PASS**; `A8/boot.img` 46,409,728 B, slack 11,261,952 B |
| embedded initramfs | 551,027 B sha256 `56ef85f9…`, verified **byte-for-byte inside `Image-A8`** at `0x203E510` |
| archive members | `init` (28,236 B, sha256 `28a4834d…` == `boot/initramfs/init.sh`), `bin/sh -> toybox`, `bin/toybox`, `dev/console`, **`dev/kmsg`**, `dev/null`; 67 records; no duplicates |
| `/init` content check | 5 occurrences of `nuxel_say`; `sh -n` clean; existing 8-test init suite still passes |
| kernel | `Image-A8` sha256 `f887030a…`; `ARMd` @0x38, `text_offset=0x80000`, `image_size=0x333c000`, `flags=0xa` |
| DTB | byte-identical to the hardware-proven A5 DTB (`bcdef39c…`) |
| candidate sha256 | `314d5e532f3e0a25d324c87e844110b173db20306d42ca83d67c2684fa6f026a` |
| preflight | **PREFLIGHT PASS** |


---

## T-A13-offline — A13 validation (2026-10-15, host + Podman containers, no device)

| Check | Result |
|---|---|
| systemd repair built | `systemd-258.11-1.fc43` rpmbuild from the exact SRPM; `rpmbuild -bp` verified the fallback text is present in `src/basic/process-util.c` **before** the build |
| repair present in the binary | `objdump`: `posix_spawn_wrapper` calls `pidfd_spawn@plt` **and** `posix_spawn@plt` (0x24e008 / 0x24e07c); the installed original has only the first |
| repair scope | `libsystemd-core-258.11-1.fc43.so` imports `posix_spawn_wrapper@SD_SHARED` and contains no `pidfd_spawn` → **one** library replacement is sufficient |
| syscall probe | `aarch64-linux-gnu-gcc -static -nostdlib -ffreestanding`, 67,136 B, no dynamic section, no undefined symbols |
| spawn probes | built against `glibc-2.42-17.fc43` (the rootfs generation); `nm -D` shows `pidfd_spawn@GLIBC_2.39` + `posix_spawn@GLIBC_2.17` |
| artifact transfer integrity | container → host: `libsystemd-shared-patched.so`, `nuxel-spawn-probe`, `nuxel-spawn-probe-static`, `Image-A13` all re-hashed on the host and **identical** (the host disk has truncated files before) |
| kernel rebuild | incremental, 24 s; only `usr/initramfs_data*` regenerated; source tree, defconfig and DTB **unchanged**; `Image-A13` 47,929,352 B `aa28769a…` |
| DTB | every candidate still appends `bcdef39cd37621948e9370f619022565bed2a84dc76a540d20f5165b43723671` (byte-identical to A5's rev-26 tree) |
| `/init` inside the image | extracted from `A13/initramfs.cpio` and **byte-identical** to `boot/initramfs/init.sh` (46,044 B) |
| payload inside the image | `opt/nuxel/{libsystemd-shared-258.11-1.fc43.so,nuxel-syscall-probe,nuxel-spawn-probe,nuxel-spawn-probe-static,nuxel-fb-phone}` present, modes `0100755`, sizes verified |
| archive integrity | 77 records, `TRAILER!!!` at 6,742,224, logical end 6,742,348 |
| release gate | **PASS** — 50,604,032 B, `partition_slack 7,067,648 B`, `header_field40 1`, `header_size 1648`, lzma-alone with EOS marker, dict 8 MiB |
| gate regression suite | `test-boot-image-gates.sh` — **11 passed, 0 failed** |
| init regression suite | `test-init-cmdline-independence.sh` — **8 passed, 0 failed** |
| A12 regression baseline | `A12/boot.img` sha256 re-verified `68217cdd…`; `init.sh.bak-A12` sha256 `85dba795…`; the container keeps `/b/initramfs-A12.cpio` `2beeab5e…` |
| offline-only claims | first light, Fedora execution and the ENOSYS measurement are **not** proven until A13 runs; they are listed as target, not achieved |

### Environment notes
* Host data volume ~98 % used (27 GiB free) — above the 20 GiB floor; every large
  artifact was hash-verified after copying out of the VM.
* The container build path used is `podman machine ssh` + `podman exec` inside the
  VM (the stable path). The Podman API/gvproxy socket path was not used.

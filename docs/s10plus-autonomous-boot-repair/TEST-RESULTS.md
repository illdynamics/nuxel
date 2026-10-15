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

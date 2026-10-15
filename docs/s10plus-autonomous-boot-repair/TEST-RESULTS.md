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

---

# CYCLE 5 TEST RESULTS (A14 hardware evidence)

| # | What was measured | Where | Result |
|---|---|---|---|
| T-C5-1 | A14 wrote and readback-verified byte-for-byte | `FLASH-ATTEMPTS.md` (A13/A14) | `5aff1a10…` = local `boot.img` |
| T-C5-2 | initramfs executed | `prev-boot/last_kmsg.raw` line ~2926 | `NUXEL_MARKER INITRAMFS_EXECUTED` t=2.152 s |
| T-C5-3 | first-light payload ran and exited 0 | same | `FIRSTLIGHT_FRAME_WRITTEN` t=2.363 s; no `NUXEL_FB_*` failure line |
| T-C5-4 | rootfs mounted, identity gate | same | `NUXEL_MARKER ROOTFS_MOUNTED` t=3.398 s |
| T-C5-5 | kernel primitives, on the device | same | `NUXEL-SYSCALL` table: `clone(SIGCHLD)+execve` ret=0; `waitid(P_PIDFD)` EINVAL; `pidfd_spawn` ENOSYS; `posix_spawn` rc=0 child_status=7; `cgroup2_unified=absent` |
| T-C5-6 | Fedora binary executes from the real root | same | `NUXEL_MARKER FEDORA_BINARY_EXECUTED`, `FEDORA_EXEC_OK uid=0` |
| T-C5-7 | systemd 258.11 PIC 1 up | same | `systemd[1]: systemd 258.11-1.fc43 running in system mode`, `Detected architecture arm64` |
| T-C5-8 | **a core child service really executes** | same, t=3.9–105 s | `systemd-udevd[3483/3505/3527/3539]` processing kernel uevents and logging `Using default interface naming scheme 'v258'` |
| T-C5-9 | the A12 `Failed to spawn executor: Function not implemented` error | whole capture | **absent** — the A13 pidfd_spawn repair works |
| T-C5-10 | next blocker is cgroups | t=3.820–3.915 s | 18 × `Failed to attach to cgroup /system.slice/…: No such file or directory` + `Failed at step CGROUP` |
| T-C5-11 | udevd worker creation | t=32.3–62.5 s | `systemd-udevd[…]: Failed to create worker object: Function not implemented` (pidfd/clone3 primitive missing in 4.14) |
| T-C5-12 | **reboot cause** | t=47.163–107.804 s | runconsole: `sh: 1/comm: No such file or directory` (pid 3308) → `debug-snapshot: normal reboot starting` + `sec_debug: set magic code (0x0)` from PIDs 3557/3558/3561 (comm `init`) → `Freezing user space processes` t=107.489 → `reboot: Restarting system` t=107.804. No panic, no BUG, HW watchdog petted every 10 s. |
| T-C5-13 | A14 = 3 identical Nuxel sessions in the ram console | `last_kmsg.raw` | the phone rebooted more than once before recovery (each session: first light 2.36 s, handoff 3.44 s, reboot request 47.17 s) |
| T-C5-14 | pstore record | `pstore/dmesg-ramoops-0.raw` | `Panic#2 Part1` from an older session with magic `0x66262564` (a genuine panic, not this boot) — proves the *normal* `0x0` magic in T-C5-12 is meaningful |
| T-C5-15 | device identity/partition map at capture time | `recovery/recovery-metadata.txt` | root ADB, `boot -> sda14`, `recovery -> sda15`, `userdata -> sda31`, `androidboot.dtbo_idx=9`, `sec_debug.reset_reason=7` |

---

# CYCLE 6 TEST RESULTS

## Offline / build-time tests (all on the Mac, no device writes)

| # | Test | Result |
|---|---|---|
| 1 | `sh -n boot/initramfs/init.sh` after the first-light rewrite | PASS |
| 2 | freestanding aarch64 build of `nuxel-fb-phone.c` in the aarch64 container (`gcc -O2 -static -nostdlib -nostartfiles -ffreestanding`) | PASS, 9792 B, ELF EXEC AArch64, entry `_start` |
| 3 | binary runs in the container with argv forms `-`, `hold`, `hold 5` | PASS — all three print `NUXEL_FB_UNAVAILABLE no /dev/fb0`, exit 2 (argv/entry path exercised) |
| 4 | cpio round-trip: extracted `init` and `opt/nuxel/nuxel-fb-phone` re-hash | PASS — `b209c3e9…` and `fed8f9c9…`, identical to the sources |
| 5 | embedded-initramfs staleness check: gunzip the stream at offset 33,809,680 of `Image-A16` | PASS — 6,753,220 B, sha256 `f3bd9cbe…` = `A16/initramfs.cpio`. (A15 re-checked the same way: `f31b96a5…`) |
| 6 | `build-candidate.sh` release gate on `A16/boot.img` | PASS — header_field40=1, header_size=1648, kernel_size=47,929,352, ramdisk lzma 2,293,760 B aligned, cpio `/init` 0o100755 51,833 B, partition slack 7,067,648 B |
| 7 | kernel rebuild with the A16 cpio (incremental, object reuse from the A15 build tree) | PASS — `GEN usr/initramfs_data.cpio.gz` observed, `A16_KERNEL_BUILD_OK`, Image 47,929,352 B |
| 8 | pre-flight against the live handset (`--action preflight --boot-only`) | PASS — `beyond2lte`, TWRP 3.7.0_9-2, `boot -> /dev/block/sda14` 57,671,680 B |
| 9 | flashed-image identity of A15 *before* overwriting (`dd` prefix hash) | PASS — `e23d004d…` = `A15/boot.img`, so the A15 capture is provably A15's |

## Hardware test A16

| Field | Value |
|---|---|
| Candidate | A16 (BOOT-only) |
| boot.img sha256 | `603c2e9a3fd434d451aea0b614fe5978a9ad6178ade6edc1831afc708ee36222` |
| Backup | `backups/s10plus/20261015T140626Z-R58M75KDB2X` |
| Readback | PASS — full-partition SHA256 of the written range matches the local image |
| Reboot | `2026-10-15T14:07:20Z` (`adb reboot` from TWRP, single command) |
| Partitions written | BOOT (sda14) only |
| Result | pending operator observation / post-fail capture |

## Ram-console structure of the A15 capture (method note, reusable)

`/proc/last_kmsg` from TWRP held **three** boots back to back; identify them by
`Samsung S-Boot 4.0` banners and `Starting kernel...`:

| Lines | Boot | Sentinel |
|---|---|---|
| 1–4548 | previous TWRP session | `init: Reboot start, reason: reboot,adb` |
| 4549–17571 | **NUXEL A15** | kernel banner at 5286, `#1 SMP PREEMPT Thu Oct 15 13:23:12 UTC 2026` |
| 17572–18303 | current TWRP | `recovery: Loading entire partition` |

Never attribute a `BUG`/hard-reset record to the boot until its position inside
this map is established — that mistake is exactly what RC-6.1 corrects.

---

# CYCLE 7 — A17 offline validation (2026-10-15)

No test below is a claim about visible output or hardware behaviour.

| # | Test | Result |
|---|---|---|
| 1 | A16 ram-console session segmentation (4 boots in the ram buffer) | PASS — A16 = lines 5785–21122, t = 0→170.21 s |
| 2 | A16 reset-cause classification | PASS — `kernel BUG at drivers/samsung/sec_hard_reset_hook.c:157`, `sec_reboot (0, panic)`, no watchdog/panic of Nuxel's own |
| 3 | A16 library forensics: rootfs vs initramfs `libsystemd-shared` | IDENTICAL, `502507a7b6237a03cfcff49e389d2a38836916abdea40e36e5ba4653e9bc1234` |
| 4 | A13 fallback really compiled in? (`aarch64-elf-objdump -T`) | YES — `posix_spawn@plt` + `pidref_set_pid@plt` present; absent in `.nuxel-orig` |
| 5 | Offline spawn repro, A13/A16 library, 4.14-emulating stub | `posix_spawn_wrapper rc=-38 ENOSYS`, **child ran** (`childran.txt`) — reproduces A16 |
| 6 | Offline spawn test, A17 library, same stub | `rc=0`, `pid` set, `fd=-9` (PID-only PidRef), child exited 0 — **fix confirmed** |
| 7 | `nuxel-verify` behaviour (match/mismatch/elf/non-elf/missing) | 0/1/0/1/2 as specified |
| 8 | A17 init.sh edit anchors | 6/6 applied; `sh -n` clean |
| 9 | A17 cpio round-trip (`init`, 4 payloads) | byte-identical to sources |
| 10 | `Image-A17` embedded initramfs == `A17/initramfs.cpio` | byte-identical, `3e0ca12e…` |
| 11 | `build-candidate.sh` release gate | PASS (after the gate correctly rejected a duplicate `dev/console`/`dev/null` pack) |
| 12 | BOOT write + full-partition SHA-256 readback | PASS, `911a72e9…` |

## Hardware results

Pending — `STATE=AWAITING_BOOT_RESULT` for A17 (`REBOOT_AT=2026-10-15T15:07:35Z`).

---

# CYCLE 7b — A18 offline validation and live-run result (2026-10-15)

| # | Test | Result |
|---|---|---|
| 13 | toybox `case` behaviour with an empty alternative | **BUG CONFIRMED**: `case s10plus in mustang\|vm\|"")` matches. The A17 `DEVICE` dispatch was dead code for every non-generic device |
| 14 | A17 root-resolution code under the initramfs's own toybox, Samsung cmdline | Reproduces A17: generic probe → refusal → FATAL |
| 15 | A18 root-resolution code, same harness | `dispatch: DEVICE='s10plus'` → heartbeat wait → `USERDATA via documented /dev/sda31 … after 2s` → `RESULT ROOT_DEV='/dev/sda31'` |
| 16 | A18 init.sh `sh -n`, helper-before-use ordering | PASS (an ordering mistake was caught here and fixed) |
| 17 | `Image-A18` embedded initramfs == `A18/initramfs.cpio` | byte-identical, `4e763933…` |
| 18 | `build-candidate.sh` release gate on A18 | PASS |
| 19 | A18 BOOT write + full-partition SHA-256 readback | PASS, `6a8d2587…` |
| 20 | USB gadget creation on hardware (MacBook observation) | **PASS** — `Nuxel S10+ Live Console` 0x18d1/0x4ee7, `/dev/cu.usbmodem201` |
| 21 | Live console data path | **FAIL / open** — 0 bytes both directions |
| 22 | Root resolution, switch_root, systemd services on hardware | pending TWRP return |

---

# CYCLE 7c — A19 (2026-10-15)

## What A18 proved on hardware (recorded now that the log exists)

| # | Test | Result |
|---|---|---|
| 23 | `ROOTFS_MOUNTED /dev/sda31 ext4 rw` with the A18 init.sh | **PASS** — root resolution fixed on hardware |
| 24 | `Failed to spawn executor` count in the A18 session | **0** (was 29 in A16) — the `pidfd_open()` fix works |
| 25 | `Failed at step CGROUP` count | **0** (was 61) — the cgroup2 ordering fix works |
| 26 | Units failed (`Failed with result`) | **0** (was 28) |
| 27 | A real service running | **`systemd-journald.service loaded active running`** |
| 28 | `systemctl --failed` from inside the running system | `0 loaded units listed` (persistent report) |
| 29 | cgroup2 in the final namespace | `controllers: memory pids`, `self: 0::/init.scope` |
| 30 | USB gadget enumeration | `Nuxel S10+ Live Console` 0x18d1/0x4ee7 on `/dev/cu.usbmodem201` |
| 31 | Console data path | **FAIL** — `nuxel-console: /dev/ttyGS0 did not appear` |
| 32 | Root cause of 31 (kernel source) | `u_serial.c` registers the gadget tty **in sysfs only**; the comment says "so mdev/udev make /dev/ttyGS*". Nuxel runs neither → no node. A19 mknods it from `/sys/class/tty/ttyGS0/dev` |

## A19 offline validation

| # | Test | Result |
|---|---|---|
| 33 | A19 root resolution under the initramfs's own toybox | PASS — dispatch → heartbeat wait → `RESULT ROOT_DEV='/dev/sda31'` |
| 34 | `sh -n` after de-chaining three blocks | PASS |
| 35 | `if/elif/else` chains remaining in the boot path | none (10 `elif` remain but all in dead/late paths — command provider, g7power, `find_root`, and the `exec`-guarded `switch_root` selection) |
| 36 | `Image-A19` embeds `A19/initramfs.cpio` | PASS — payload found at offset 33,809,680, content-verified |
| 37 | Release gate on `A19/boot.img` | PASS |
| 38 | BOOT write + full readback | PASS, `7a24c04a…` |

## A19 live result (pending the ram console)

`TTY-APPEARED` at 15:51:50Z — the gadget bound again. The console carried **0 bytes**
in a 45 s window with DTR asserted, so the A19 `mknod` path either did not execute
successfully or the shell/keeper are still not attached. **The ram console will say
which** (`nuxel-console: created /dev/ttyGS0 from …` vs
`waiting for /dev/ttyGS0 / /sys/class/tty/ttyGS0/dev` vs `never became available`,
plus `shell tty fd=…`). Do not guess further until that is read.

---

# CYCLE 9 — A21 (2026-10-15) — the cycle that made every number readable

## Offline (no handset)

| Test | Command | Result |
|---|---|---|
| Decoder still bit-exact after every A21/A22 edit | `cc -DNUXEL_HOST … nuxel-anim-player.c` vs an independent Python decoder, 192 frames | **PASS 192/192** (`scratch/a21-c-crc.txt == a21-py-crc.txt`) |
| Colour conversion faithful, ARGB8888 | `tools/s10plus/test-anim-colour.sh` | **PASS** max channel error 0 |
| Colour conversion faithful, ABGR8888 | same | **PASS** max channel error 0 |
| A20 conversion explains the photograph | same | **PASS** frame 0 mean red 38.2 vs mean blue 0.0 |
| Artwork has no red background | same | **PASS** 0.17 % red pixels, 2.04 % blue |
| Release gate refuses a bad image | `build-candidate.sh` on a cpio with dev nodes already present | **PASS (fail-closed)** — refused with "duplicate member 'dev/console'" |

## On hardware, in TWRP (pre-flash validation of the exact shipping binaries)

| Test | Result |
|---|---|
| First-light renderer runs, prints real geometry | PASS — `red.off=0x10 green.off=0x8 blue.off=0x0`, `stride=5760`, `smem_len=35020800`, `BUFFERS_PAINTED=2` |
| Deterministic colour round-trip in framebuffer memory | PASS — R/G/B/W/K expected == readback for all five |
| Driver accepts the commit | PASS — `UNBLANK_rc=0 ACTIVATE_rc=0 PAN_rc=0` |
| Resident painter publishes its own pid | PASS — `fb-hold.pid=5229` |
| Player finds it by identity and kills it | PASS — `TAKEOVER_PID=5229`, `KILLED=1`, `STOPPED=1` (bounded ≤1 s, re-verified via `/proc/<pid>/comm`) |
| State files land in the state directory | PASS — all five files created **in the statedir**, not in `/` |
| Playback rate | PASS — 145 frames / 6 s = 24.2 fps, `LAG_SKIPS=0`, `LOOPS=1` |
| `git`-independent proof the fix is in the binary | the shipped player's `PAL0_SRC565=65535 → DST=16777215` and the EINVAL/plain-open pair |

## On hardware, A21 boot (kernel #7) — live over the USB console

| Test | Result |
|---|---|
| `NUXEL_INIT_REV=A21-one-penguin-correct-colours` | PASS — the A21 init ran |
| First light then MP4 takeover | PASS — `FIRSTLIGHT exit=0`, `ANIMATION_HOLD_DEFERRED`, `FIRST_FRAME_COMMITTED` at t=7.60 s, `ANIM_STAGE=MP4_PLAYER_ACTIVE` |
| Exactly one renderer | PASS — `pgrep -a nuxel-fb-phone` → NO_PENGUIN_PAINTER_RUNNING throughout |
| Playback rate, whole run | PASS — 39 heartbeats × 240 frames; `SKIPS=0` every time; 5520 frames / 229.97 s = **24.00 fps** |
| Panel colour layout re-measured in Nuxel (not TWRP) | PASS — `RED_OFF=16 GREEN_OFF=8 BLUE_OFF=0 TRANSP_OFF=24` |
| `uname -a` / `id` / `/etc/os-release` / `systemctl --failed` | PASS — kernel #7, uid=0, Fedora 43, **0 failed units** |
| exit status propagation | PASS — `false; echo $?` → 1 |
| cgroup v2 in the final namespace | PASS — `cgroup2 rw,relatime,nsdelegate` |
| rootfs mounted rw | PASS — `/dev/sda31 ext4 rw,relatime,errors=remount-ro,data=ordered` |
| journald / udevd / dbus-broker | PASS — `active` |
| `/dev/ttyGS0` exists, UDC bound | PASS — char 243:0, `10c00000.dwc3` |
| **The operator's visual verdict** | **FAILED — returned to TWRP at t=400 s** (see below) |
| Cause of the run's end | operator hard-reset hook (`hard_reset_hook_callback+0x144`, `brk #0`), not a fault of the candidate |

## The one honest negative

The operator returned the phone to TWRP, so A21 is recorded as a **failed attempt** under
the standing agreement. Two facts must be kept separate:

* the candidate did what it claimed *in every measurable way* — MP4 frames at 24.00 fps,
  0 drops, one renderer, state files correct, live console working;
* the observation window was degraded **by our own diagnostics**: a `dd if=/dev/fb0`
  released the DECON and left 1279 pans failing, and a second short player instance
  released it again. The panel was verifiably correct from t≈7.5 s to t≈321 s.
* A22 therefore fixes the *observed* defect (self-healing re-assert) rather than
  re-shipping A21 unchanged.

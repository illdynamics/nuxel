# S5000AP — Round 03: Build Receipt (OFFLINE, reproducible)

**Round:** `2026-11-23T03:15Z` → `03:45Z`. **No device contact, no flash, no CP action.**

This receipt records exact toolchain, flags, source hashes, and build commands for
every artifact produced in round 03, so the work is independently reproducible.

---

## 1. Source base

| Item | Value |
|---|---|
| Nuxel worktree | `/Users/wicked/x/nuxel` @ `03cd910f6c6a3ec600d1286b3265cce917c744e2` (`cs/mob`) |
| Kernel commit (ABI source) | `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (linux 4.14.253, 2021-11-13) |
| Kernel modem_v1 path | `kernel/s10plus/.build/src.polluted.case-insensitive/drivers/misc/modem_v1/` |
| Kernel `.config` | `kernel/s10plus/.build/out/.config` (SHMEM, secure boot, S5000AP) |
| cpboot_v3 reference | `android_hardware_samsung_slsi-linaro_exynos` @ `e9816cf6…` (lineage-24.0) |
| device cbd config | `android_device_samsung_exynos9820-common` @ `38af956a…` (lineage-24.0) + `8fec7c38…` (lineage-18.1) |

## 2. Toolchains

| Tool | Version | Role |
|---|---|---|
| `aarch64-linux-gnu-gcc` | 15.2.0 (homebrew `aarch64-unknown-linux-gnu`) | target AArch64 cross (matches device kernel gcc 15.2.0) |
| `/usr/bin/gcc` | Apple clang (host) | host LP64 layout verification |
| `python3` | 3.11.9 | pytest test suite |
| `lz4` | homebrew | (round-02 only; not used here) |

## 3. Artifacts and exact build commands

### 3.1 Verified UAPI header (`s5000ap_uapi.h`)
Hand-transcribed from the pinned kernel headers, **kernel-only types removed**,
ioctl values pinned as numeric literals (Linux asm-generic encoding) to be
independent of host-libc ioctl encoding.

### 3.2 `nuxel-s5000ap-uapi-check` (fixture)
```bash
# host LP64
gcc -O2 -Wall -Wextra -Werror -o nuxel-s5000ap-uapi-check.host nuxel-s5000ap-uapi-check.c
# AArch64 static (self-contained, device-ready)
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static -o nuxel-s5000ap-uapi-check.aarch64 nuxel-s5000ap-uapi-check.c
```
Output (host) asserts: `sizeof_modem_firmware=28`, offsets `binary=0,size=8,m=12,b=16,mode=20,len=24`,
`sizeof_modem_sec_req=16`, `sizeof_sipc5_link_header=6`, ioctl `0x6F27/0x6F40/0x6F53`, state `ONLINE=4`.

### 3.3 `s5000ap-status` (read-only probe)
```bash
gcc -O2 -Wall -Wextra -Werror -o s5000ap-status.host s5000ap-status.c
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static -o s5000ap-status.aarch64 s5000ap-status.c
```
`file s5000ap-status.aarch64` → `ELF 64-bit LSB executable, ARM aarch64, statically linked`.
`_Static_assert` pins `IOCTL_MODEM_STATUS==0x6F27`, `STATE_ONLINE==4`, etc.

### 3.4 `nuxel-cpbootd` (dry-run CP boot coordinator)
```bash
# DRY-RUN ONLY (default build; DANGER compiled out)
gcc -O2 -Wall -Wextra -Werror -o nuxel-cpbootd.host nuxel-cpbootd.c
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Werror -static -o nuxel-cpbootd.aarch64 nuxel-cpbootd.c
```
The hardware-mutating code path is behind `#ifdef NUXEL_CPBOOTD_ENABLE_HW` and is
**not** compiled in these binaries. `--really-boot` on this build exits 2:
```
error: --really-boot requires a build with -DNUXEL_CPBOOTD_ENABLE_HW=1 (compile-time hardware enable). This binary is dry-run only.
```

### 3.5 Test suite
```bash
python3 -m pytest tools/s10plus/s5000ap-uapi/tests/ -v
# => 21 passed
```
Archived log: `reports/s5000ap-03/logs/round03-offline-tests.log`.

## 4. Key ABI facts verified at build time (not guessed)

- `struct modem_firmware` = **28 bytes** (packed, no tail padding).
- `struct modem_sec_req` = 16 bytes.
- `struct sipc5_link_header` = 6 bytes (`multi_frame_control` is 1 byte).
- `_IO('o',N)` = `0x6F00|N` on AArch64 (verified via `_Static_assert` on the target).
- `CONFIG_LINK_DEVICE_PCIE` is **not set** → PCIe-only `IOCTL_MODEM_DUMP_RESET (0x6F36)`
  and `IOCTL_REGISTER_PCIE (0x6F65)` are absent (Header correctly omits them).

## 5. cbd dependency/build reproducibility

A faithful glibc rebuild of `cpboot_v3` as `cbd` is **not reproducible on Nuxel**
because its `Android.bp` links Bionic `liblog`, `libcutils`, `libselinux`, and relies
on Android properties (`vendor.cbd.*`) and the Android SELinux `radio_device` label.
These require the Android vendor runtime, which Nuxel (glibc/systemd) does not
provide. Hence the architecture chose the dry-run `nuxel-cpbootd` shim, not a fresh
unverified glibc cbd.

## 6. Safety receipt

- No proprietary blob, firmware byte, or `cbd` binary was committed or logged.
- `stock-cbd/cbd` sha256 `c3e869fa…` (round-02) remains owner-local only.
- No partition write, no ioctl issued, no device contacted this round.

# S5000AP — Round 03: Kernel ABI Boot Contract (OFFLINE)

**Branch/HEAD:** `cs/mob` @ `03cd910f6c6a3ec600d1286b3265cce917c744e2`
**Round window:** `2026-11-23T03:15Z` → `2026-11-23T03:45Z`
**Handset-changing actions:** **NONE.** No flash, no CP power/reset/download ioctl, no
`/dev/umts_*` write, no DT/DTBO/DTS, no partition read/write, no reboot, no
radio/module config change.
**Governing:** `pwn-mob/00_MASTER_SAFETY_AND_TRUTH.md`, `pwn-mob/03_CBD_ABI_AND_OFFLINE_BUILD.md`,
prior reports `S5000AP-01-LIVE-GATES.md`, `S5000AP-02-CP-FIRMWARE-IDENTITY.md`.

Classification: `PROVED_LIVE`, `CAPTURED_LIVE_OLDER`, `OFFLINE_TESTED`, `SOURCE_ONLY`,
`DOCUMENTED_ONLY`, `ASSUMPTION`, `UNVERIFIED`, `BLOCKED`.

---

## 1. Headline ABI findings (all SOURCE_ONLY / OFFLINE_TESTED, none live)

The ABI was derived from the pinned kernel commit
`f7194c1d15eded1c2a1a4dc63825b26103435cc0` (2021-11-13, linux 4.14.253), present at
`kernel/s10plus/.build/src.polluted.case-insensitive/` (git confirms the same HEAD).
This commit is the exact base of the running kernel
`4.14.253-gf7194c1d15ed-dirty` observed live in round 01.

| # | Finding | Class | Corrects |
|---|---|---|---|
| 1 | **`struct modem_firmware` is 28 bytes, not 32.** `__packed` removes ALL tail padding: `u64 binary`(8) + `u32 size/m_offset/b_offset/mode/len`(5×4=20) = 28. Verified by cross-compiling for AArch64 (GCC 15.2.0) and reading the generated code (size == 28). | `OFFLINE_TESTED` | Round-02 §3.2 "32 bytes" claim |
| 2 | Field offsets (AArch64 LE): `binary@0, size@8, m_offset@12, b_offset@16, mode@20, len@24`. | `OFFLINE_TESTED` | — |
| 3 | The struct is **pointer-width independent**: `binary` is `unsigned long long` (8 bytes on both LP64 and ILP32), so 32/64-bit layout is identical (28 bytes). Verified via ILP32 `_Static_assert` compile. | `OFFLINE_TESTED` | — |
| 4 | **ioctl numeric encoding is Linux `asm-generic`, NOT the host-libc BSD encoding.** On AArch64 `_IO('o',N) == 0x6F00|N` (e.g. STATUS=0x6F27, XMIT_BOOT=0x6F40, SECURITY_REQ=0x6F53). On macOS/clang `_IO('o',N)` would be `0x20006FNN` — **wrong ABI**. The fixture pins numeric literals and cross-checks `_IO` on the Linux target. | `OFFLINE_TESTED` | Cross-platform pitfall |
| 5 | `struct modem_sec_req` = 16 bytes `{u32 mode,param2,param3,param4}` packed. | `OFFLINE_TESTED` | — |
| 6 | `struct sipc5_link_header` = **6 bytes** (1 cfg + 1 ch + 2 len + 2 union). The union member `multi_frame_control` is `{u8 id:7, more:1}` = **1 byte** (not 4). | `OFFLINE_TESTED` | Initial draft used a wrong 4-byte bitfield |
| 7 | SIPC5 channel IDs: BOOT=215–224, DUMP=225–234, FMT=235–244, RFS=245–254, PDP_0=10, CASS=35. | `SOURCE_ONLY` | — |
| 8 | **`CONFIG_LINK_DEVICE_PCIE is not set`** (running config + source); this is a **SHMEM device**. The PCIe-only ioctls `IOCTL_MODEM_DUMP_RESET (0x6F36)` and `IOCTL_REGISTER_PCIE (0x6F65)` are **correctly absent** from the SHMEM UAPI surface. | `SOURCE_ONLY` + `PROVED_LIVE` (config) | — |
| 9 | `IOCTL_MODEM_STATUS` is handled by `misc_ioctl` returning `mc->phone_state`, with a special-case: if `sim_state.changed`, it returns `STATE_SIM_ATTACH/DETACH` once and clears the flag. | `SOURCE_ONLY` | — |

---

## 2. Full annotated UAPI matrix

### 2.1 ioctl command set (Linux asm-generic `_IO('o',N)` = `0x6F00|N`)

| IoCtl | Hex | # | Direction | Arg (userspace) | Kernel handler | Pre-state → Post-state | HW-mutating? |
|---|---|---|---|---|---|---|---|
| MODEM_ON | 0x6F19 | 0x19 | none | — | `mc->ops.modem_on` → `s5000ap_on` | OFFLINE→(cal_cp_init) | **YES** |
| MODEM_OFF | 0x6F20 | 0x20 | none | — | `mc->ops.modem_off` → `s5000ap_off` | any→(cal_cp_reset_assert) | **YES** |
| MODEM_RESET | 0x6F21 | 0x21 | none | — | `mc->ops.modem_reset` → `s5000ap_reset` | any→OFFLINE | **YES** |
| MODEM_BOOT_ON | 0x6F22 | 0x22 | none | — | `mc->ops.modem_boot_on` → `s5000ap_boot_on` (polls cp_status) | OFFLINE→BOOTING | **YES** |
| MODEM_BOOT_OFF | 0x6F23 | 0x23 | none | — | `mc->ops.modem_boot_off` → `s5000ap_boot_off` (waits init_cmpl ≤15s) | BOOTING→ONLINE | **YES** |
| MODEM_BOOT_DONE | 0x6F24 | 0x24 | none | — | `mc->ops.modem_boot_done` (no-op) | ONLINE confirm | **YES** (no-op) |
| PROTOCOL_SUSPEND | 0x6F25 | 0x25 | none | — | `iodev_netif_stop` if MULTI_RAW | — | subtle |
| PROTOCOL_RESUME | 0x6F26 | 0x26 | none | — | `iodev_netif_wake` | — | subtle |
| **MODEM_STATUS** | **0x6F27** | 0x27 | **none (read)** | — | returns `mc->phone_state` (or SIM attach/detach once) | — | **NO** (read-only) |
| MODEM_DL_START | 0x6F28 | 0x28 | none | — | `ld->dload_start` + `modem_boot_confirm` | — | **YES** |
| MODEM_FW_UPDATE | 0x6F29 | 0x29 | ptr (u32[]) | *(firmware params) | `ld->firm_update` | — | **YES** |
| NET_SUSPEND/RESUME | 0x6F30/31 | — | none | — | netif ops | — | subtle |
| DUMP_START/UPDATE | 0x6F32/33 | — | none/ptr | — | `mc->ops.modem_dump_start` / `ld->dump_update` | →CRASH_EXIT | **YES** |
| FORCE_CRASH_EXIT | 0x6F34 | 0x34 | int (crash_type) | crash type | `mc->ops.modem_force_crash_exit` | →dump | **YES** |
| CP_UPLOAD | 0x6F35 | 0x35 | ptr (crash string) | cp_crash_info | `strcpy` + **`panic()`** (kernel panic) | — | **YES (kernel panic!)** |
| SET_TX_LINK | 0x6F37 | 0x37 | ptr (int) | tx link id | `copy_from_user` + `set_current_link` | — | YES |
| **XMIT_BOOT** | **0x6F40** | 0x40 | **ptr→struct modem_firmware** | `{binary,size,m_offset,b_offset,mode,len}` | `shmem_xmit_boot` (validates + `copy_from_user` into shmem) | — | **YES** |
| GET_SHMEM_INFO | 0x6F41 | 0x41 | none | — | `ld->shmem_info` | — | read |
| DPRAM_INIT_STATUS | 0x6F43 | 0x43 | none | — | — | — | read |
| LINK_DEVICE_RESET | 0x6F44 | 0x44 | none | — | — | — | YES |
| GET/SET_SHMEM_SRINFO | 0x6F45/46 | — | ptr | srinfo | `ld->srinfo` restore/save | — | read/write |
| GET/CLR_CP_BOOTLOG | 0x6F47/48 | — | none | — | bootlog | — | read |
| MIF_LOG_DUMP | 0x6F51 | 0x51 | ptr (u64 size) | log buffer | `mif_dump_log` | — | read |
| MIF_DPRAM_DUMP | 0x6F52 | 0x52 | ptr | — | — | — | read |
| **SECURITY_REQ** | **0x6F53** | 0x53 | **ptr→modem_sec_req** | `{mode,param2,param3,param4}` | `shmem_security_request` → `exynos_smc()` **TEE** | secure-boot signature check | **YES (TEE)** |
| SHMEM_FULL_DUMP | 0x6F54 | 0x54 | ptr | — | `ld->shmem_dump` | — | read |
| CRASH_REASON | 0x6F55 | 0x55 | ptr | crash_reason | `ld->crash_reason` | — | read |
| AIRPLANE_MODE | 0x6F56 | 0x56 | int | on/off | `ld->airplane_mode` | — | **YES (RF)** |
| VSS/ACPM/CPLOG/DATABUF dumps | 0x6F57/58/59/5A | — | ptr | — | `ld->*_dump` | — | read |
| RAMDUMP_START/STOP | 0x6FCE/CF | 0xCE/CF | none/ptr | — | `ld->dump_start/dump_finish` | — | **YES** |

**Not present (PCIe-only, SHMEM device):** `IOCTL_MODEM_DUMP_RESET (0x6F36)`,
`IOCTL_REGISTER_PCIE (0x6F65)`. These are `#ifdef CONFIG_LINK_DEVICE_PCIE` and
**do not compile** into this kernel.

### 2.2 Boot-state enum (modem_state) — verified order

`OFFLINE=0, CRASH_RESET=1, CRASH_EXIT=2, BOOTING=3, ONLINE=4,
NV_REBUILDING=5, LOADER_DONE=6, SIM_ATTACH=7, SIM_DETACH=8, CRASH_WATCHDOG=9`.

### 2.3 Secure boot is handled **inside the kernel**, not userspace

`IOCTL_SECURITY_REQ` → `shmem_security_request()` (link_device_shmem.c:2545). When
`CONFIG_CP_SECURE_BOOT=y` (it is), the kernel:
1. copies `struct modem_sec_req` from user;
2. `exynos_smc(SMC_ID_CLK, SSS_CLK_ENABLE, 0, 0)` to enable SSS clock;
3. if `shm_get_use_cp_memory_map_flag() && mode==0`, ORs the physical base into mode;
4. `cal_cp_init()` on first invocation;
5. `exynos_smc(SMC_ID, mode, param2, param3)` — the actual **TEE/secure-world** signature check;
6. polls `CP_CHECK_SIGN_NOT_FINISH` up to `MAX_TRY_CNT=0x1000` (4096);
7. `exynos_smc(SMC_ID_CLK, SSS_CLK_DISABLE, 0, 0)`.

**Userspace never computes or trusts the signature.** The `binary` field in
`struct modem_firmware` is a *user VA of the already-loaded image in shmem*, and
the TEE validates it against Samsung's secure roots of trust. cbd does NOT
strip/fix a signature; it streams the signed image into shared memory via
`XMIT_BOOT`/`LOAD_CP_IMAGE`, then the kernel+TEE do the check.

---

## 3. cbd / cpboot_v3 ABI-exactness verdict

### 3.1 The answer: ABI-exact **only under `-DLEGACY_SIPC_IOCTL`**

`cpboot_v3/Type.h` (LineageOS `android_hardware_samsung_slsi-linaro_exynos`
@ `e9816cf6ed8123a2f20ea334641794a0e64b1e7f`, branch `lineage-24.0`) defines two
conditional encodings:

* `IOCTL_MODEM_BOOT_ON` is `_IO('o',0x22)` **but** `IOCTL_START_CP_BOOTLOADER` is
  `_IOW('o',0x22,struct boot_mode)`.
* `IOCTL_MODEM_RESET/_IO('o',0x21)` vs `IOCTL_POWER_RESET/_IOW('o',0x21,struct boot_mode)`.
* `IOCTL_LOAD_CP_IMAGE`: `_IO('o',0x40)` under `LEGACY_SIPC_IOCTL`, else `_IOW('o',0x40,struct cp_image)`.
* `IOCTL_REQ_SECURITY`: `_IO('o',0x53)` under `LEGACY_SIPC_IOCTL`, else `_IOW('o',0x53,struct modem_sec_req)`.

`std_boot_start_cp_bootloader()` (BootDump.cpp:220) is the proof:
```c
#if defined(LEGACY_IOCTL) || defined(LEGACY_SIPC_IOCTL)
    ret = ioctl(fd, IOCTL_MODEM_BOOT_ON, NULL);   /* == _IO('o',0x22) == 0x6F22 */
#else
    ret = ioctl(fd, IOCTL_START_CP_BOOTLOADER, &mode); /* _IOW(...) => DIFFERENT value */
#endif
```

This kernel's `modem_prj.h` uses the **bare `_IO('o',0x22)`** form. Therefore cbd is
ABI-exact **only when built with `-DLEGACY_SIPC_IOCTL`** (which forces the `_IO`
path). The `_IOW` path's value differs in the `size` bits (bits 29..16), so a
non-legacy cbd would issue a *different* command number and the kernel would fall
through to `default:` → `-EINVAL`.

### 3.2 The device config forces the correct flags

`android_device_samsung_exynos9820-common` (branch `lineage-24.0`
@ `38af956a4eec889cb352b4fd42e5e801c19a51b8`), `BoardConfigCommon.mk:154-155`:
```
$(call soong_config_set,cbd,protocol,sipc)
$(call soong_config_set_bool,cbd,use_legacy_sipc_ioctl,true)
```
`protocol=sipc` → `-DCONFIG_SEC_CP_VERIFYING_ALL`; `use_legacy_sipc_ioctl=true` →
**`-DLEGACY_SIPC_IOCTL`**. This is the **exact flag set** that makes cbd match this
kernel. Note `use_legacy_ioctl` (a *separate*, older flag → `-DLEGACY_IOCTL`) is
**not set**; `LEGACY_SIPC_IOCTL` is the correct one for the SIPC/SHMEM path.

### 3.3 Historical (DTK9-era) cbd is a **proprietary blob**, not built source

On `lineage-18.1` (`8fec7c38…`, the Android-11/DTK9-era reference),
`proprietary-files.txt:165` lists `vendor/bin/cbd` as a **prebuilt**, extracted from
a stock Samsung device; there is **no cpboot_v3** build target. The `cpboot_v3`
source only entered `android_hardware_samsung_slsi-linaro_exynos` at `lineage-20`
(and even there, `lineage-20`'s tree contains **no** `cpboot_v3` — it holds only
graphics/thermal/audio HALs; `cpboot_v3` appears at `lineage-24.0`).

**Conclusion:** the ABI-exact cbd for DTK9 is the **owner-local proprietary
`/vendor/bin/cbd` blob** (sha256 `c3e869fa2f78b1e8141cac58602c2a6fb852e31d5c08349ba969c75ef78f7b83`,
round-02), which is compiled against Bionic and uses the legacy `_IO` ioctl set.
The `cpboot_v3` source is a faithful **reconstruction** of that protocol (its
`-DLEGACY_SIPC_IOCTL` path reproduces the legacy ABI), but a fresh glibc build of
`cpboot_v3` is **not** a drop-in for the Bionic-linked proprietary cbd without
porting `liblog`/`libcutils`/`libselinux` and the Android property system.

### 3.4 Why a fresh glibc cbd is NOT chosen (architecture decision)

* cpboot_v3 (`cc_binary "cbd"`, `Android.bp`) links `liblog`, `libcutils`, `libc`
  (Bionic), `libselinux` — all **Android Bionic** libraries, present on the
  Android vendor image but absent on Nuxel's glibc/systemd Linux.
* Its property reads (`vendor.cbd.*`, `persist.vendor.cbd.*`) rely on the Android
  `property_get`/`property_set` from `libcutils`, which maps to `/dev/__properties__`
  — not present in a systemd/glibc rootfs.
* SELinux: `sepolicy/vendor/cbd.te` grants `cbd radio_device:chr_file rw_file_perms`
  in Android; Nuxel uses systemd/udev, not the Android `radio_device` label.

**Therefore** the mission's preferred "isolated matching Samsung cbd under
owner-compatible runtime" is the *proprietary blob on the owner-local Android
vendor image*, and the fresh-native fallback is the **`nuxel-cpbootd` strict
dry-run coordinator** (built this round), NOT an unverified fresh loader.

---

## 4. Full boot transaction (recovered, source-proven, LEGACY_SIPC_IOCTL path)

Sequence in `BootDumpExt.cpp::boot()` + `std_boot_load_cp_bootloader()` +
`std_boot_load_cp_images()` + `ProtocolSipc::*`, matching kernel handlers:

| # | Operation (userspace) | Source/structure proof | Expected kernel state | Timeout | Abort rule |
|---|---|---|---|---|---|
| 0 | open `/dev/umts_boot0` for boot; open `umts_ipc0` for SIPC | `node_boot` from `-P .../by-name/radio`; `-tss310`→S5000AP | node exists (round-01) | — | open fail ⇒ abort |
| 1 | STATUS (0x6F27) | `status_loop()` reads `mc->phone_state` | OFFLINE(0) | — | non-OFFLINE ⇒ handled |
| 2 | POWER_ON (0x6F19) | `s5000ap_on`: `cal_cp_init`, AP2CP_CFG=1 | CP clock init | — | rc<0 ⇒ abort |
| 3 | XMIT_BOOT BOOT stage (0x6F40) | `shmem_xmit_boot` copies 7,744-byte BOOT into boot window; `size/len ≤ boot_size`, `m_offset+len` overflow checked | BOOT image in shmem | — | -EFAULT/-EINVAL ⇒ abort |
| 4 | BOOT_ON (0x6F22) | `s5000ap_boot_on` polls `cp_status` mailbox (cnt=100 × 10-20ms → ~1-2s) | OFFLINE→BOOTING; cp_status=1 | 100 polls (≤2s) | -EACCES ⇒ abort |
| 5 | DL_START (0x6F28) | `dload_start` + `modem_boot_confirm` (ap_status=1) | download armed | — | rc<0 ⇒ abort |
| 6 | MAIN/NV download | SIPC5 BOOT channel (215-224), `write()` of std_udl frames (AP2CP 0x9xxx) | MAIN (39,895,408 B) streamed in stages | per-frame | short write/read ⇒ -EFAULT |
| 7 | SECURITY_REQ (0x6F53) | `shmem_security_request` → `exynos_smc` TEE signature check, poll ≤4096 | secure boot verified by TEE | 4096 retries | sign-fail ⇒ abort (no bypass) |
| 8 | BOOT_OFF (0x6F23) | `s5000ap_boot_off` waits `init_cmpl` (MIF_INIT_TIMEOUT=15s) | BOOTING→ONLINE | 15s | -EAGAIN ⇒ abort |
| 9 | BOOT_DONE (0x6F24) | `s5000ap_boot_done` (no-op confirm) | ONLINE confirmed | — | — |
| 10 | STATUS (0x6F27) | re-read phone_state | ONLINE(4) | — | !=ONLINE ⇒ FAIL |

**No firmware pointer/offset is guessed**: BOOT load via `XMIT_BOOT` uses the
ITOC-derived `m_offset`/`size` from round-02 (`BOOT@0x420 size 7,744`, `MAIN@0x2260
size 39,895,408`, load addrs `0x40000000`/`0x40010000`). The kernel validates every
transfer length against `boot_size`/`size` windows, and the secure-boot sequence is
entirely kernel/TEE-side.

---

## 5. Deliverables built this round (all OFFLINE_TESTED, none flashed)

| Artifact | Path | Purpose |
|---|---|---|
| Verified UAPI header | `tools/s10plus/s5000ap-uapi/s5000ap_uapi.h` | single source of truth (ioctl values, structs, enums, SIPC5) |
| ABI check fixture | `tools/s10plus/s5000ap-uapi/nuxel-s5000ap-uapi-check.c` | `_Static_assert` every constant + emit JSON matrix |
| Read-only status probe | `tools/s10plus/s5000ap-uapi/s5000ap-status.c` | `IOCTL_MODEM_STATUS` only; O_RDONLY; flock SH |
| Dry-run CP boot coord | `tools/s10plus/s5000ap-uapi/nuxel-cpbootd.c` | dry-run default; DANGER compile-gated; exclusive owner |
| Kernel cross-check | `tests/test_kernel_header_crosscheck.py` | parse kernel headers ↔ extracted header |
| Firmware bounds | `tests/test_modem_firmware_bounds.py` | XMIT_BOOT arith/overflow/overlap/endian |
| UAPI tests | `tests/test_s5000ap_uapi.py` | ioctl/enum/layout/32-64 |
| Dependency manifest | `tools/s10plus/s5000ap-uapi/dependencies.json` | pinned SHAs + config |

Verified build/run:
```
gcc   -> nuxel-s5000ap-uapi-check.host      (28-byte layout, 0x6F27/0x6F40/0x6F53)
aarch64-linux-gnu-gcc (15.2.0) -static -> nuxel-s5000ap-uapi-check.aarch64
gcc   -> s5000ap-status.host
aarch64-linux-gnu-gcc -static -> s5000ap-status.aarch64
gcc   -> nuxel-cpbootd.host; aarch64 -> nuxel-cpbootd.aarch64
python3 -m pytest tools/s10plus/s5000ap-uapi/tests/  -> 21 passed
```

`nuxel-cpbootd --really-boot` on the dry-run-only build returns exit 2 with the
compile-time refusal message (negative proof that the HW ioctl surface cannot run).

---

## 6. Negative proofs and safety

- `nuxel-s5000ap-uapi-check.c` contains **no** `open/ioctl/write/O_RDWR` (asserted).
- `nuxel-cpbootd` default is dry-run; opens `O_RDONLY`, only `IOCTL_MODEM_STATUS`;
  shared flock (does not block a real owner). The HW path is compiled out unless
  `-DNUXEL_CPBOOTD_ENABLE_HW=1` AND `--really-boot`.
- `s5000ap-status` opens `O_RDONLY|O_NOCTTY|O_NONBLOCK`, `LOCK_SH|LOCK_NB`, one
  `ioctl(IOCTL_MODEM_STATUS)`, prints JSON, closes.
- No `RADIO`/`MODEM`/`CP`/`EFS` partition is written anywhere. No TEE bypass, no
  signature stripping, no guessed offset.
- Malformed `modem_firmware` inputs (overflow, over-window, overlapping, wrong
  endianness) are unit-tested and rejected by the same arithmetic the kernel uses.

---

## 7. Capability matrix (unchanged — no live action)

LTE **BLOCKED**, SMS **BLOCKED**, Voice **BLOCKED**, IMS/VoLTE **BLOCKED**.
The CP remains OFFLINE (round-01 `PROVED_LIVE`); no boot was attempted or authorized.

## 8. GO/NO-GO for round 04 (controlled CP boot)

| Criterion | Status |
|---|---|
| (a) correct firmware provenance | **NO-GO** — original `.tar.md5` still absent; derived `.bin` is `STRUCTURALLY_VALID_UNAUTHENTICATED_CANDIDATE` with a `CL`/`QB` stamp mismatch (round-02, owner input pending) |
| (b) CP UAPI verified | **GO** — this round, 28-byte layout + ioctl set + enum order, verified against pinned commit |
| (c) compatible boot transaction recovered | **GO (source)** — §4 table, cbd `LEGACY_SIPC_IOCTL` path |
| (d) bounded binary built and tested | **GO (dry-run)** — `nuxel-cpbootd` + `s5000ap-status`, 21 tests |
| (e) recovery/state-observation reviewed | **PARTIAL** — read-only probe exists; live BOOT/DT receipt is `CAPTURED_LIVE_OLDER` (not re-read, `/dev/disk/by-partlabel` empty) |
| (f) owner explicit approval of this one CP trial | **NO-GO** — not requested, not granted |

**Decision: do NOT proceed to CP boot.** Exact blockers: (a) firmware provenance
unresolved and (f) no owner approval. Continue offline; no improvisation.

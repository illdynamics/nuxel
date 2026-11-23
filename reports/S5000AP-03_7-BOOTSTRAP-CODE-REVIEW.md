# S5000AP — Prompt 03.7: Bootstrap Code Review (Gate C)

**Branch/HEAD:** `cs/mob` @ `ae26b271c144780abb748ce2fb172919abb1131d`
**Reviewed artifact:** `tools/s10plus/s5000ap-uapi/nuxel-cpbootd.c` (rewritten this round)

## 0. Architecture decision — Option B (native `nuxel-cpbootd`)

Option A (port `cpboot_v3` to glibc) is demonstrably an Android-framework dependency:
`Android.bp` links `liblog`/`libcutils`/`libc++`/`libselinux`, and the source uses
`cutils/properties.h` (property server), `Log::kprintf_init` (liblog), and a
`radio_device` SELinux domain — exactly what Nuxel forbids. **Option B is selected**:
a glibc-only native daemon that re-implements the SAME Samsung boot transaction
with source-to-implementation mapping for every message/struct/ioctl/stage.

## 1. Defects fixed (audit findings 1–10)

| # | Audit defect | Fix |
|---|---|---|
| 1 | silent-return-0 stages | every stage returns nonzero on failure; no `default: return 0` |
| 2 | XMIT_BOOT/SECURITY_REQ stubs | real `struct modem_firmware`/`struct modem_sec_req` construction from parsed EFUJ2 ITOC |
| 3 | no real SIPC UDL framing | golden transcript `0x9000/0xA000` BOOT_DONE + FIN request/response, poll-based |
| 4 | exit 0 on failure | nonzero exit + machine-readable `first_failed_stage` |
| 5 | `#ifdef` compiles HW even when 0 | value-aware `#if defined(x) && (x==1)` → `HW_ENABLED`; `-D...=0` fails closed |
| 6 | unchecked `atol`, after-the-fact deadline | `strtol` range validation (1..600000 ms); documented syscall-cancellation limits |
| 7 | `flock` alone insufficient | exclusive `LOCK_EX\|LOCK_NB` + caller-side process/node ownership preflight |
| 8 | arbitrary `--node` | physical run requires exact `/dev/umts_boot0`; separate `--mock` endpoint |
| 9 | DTK9 BOOT/MAIN constants | EFUJ2 ITOC parsed at runtime under strict bounds; no DTK9 sizes anywhere |
| 10 | stale ordering | canonical LEGACY_SIPC_IOCTL order reconstructed from source (see BOOT-PROTOCOL-CALLGRAPH) |

## 2. Safety model

- Default is FAIL-CLOSED dry-run: `O_RDONLY` + single `IOCTL_MODEM_STATUS` only.
- Hardware path compiled only when `NUXEL_CPBOOTD_ENABLE_HW == 1` **and** `--really-boot`
  **and** `--manifest-sha256` (immutable manifest required).
- Offline full-transaction testing via `--really-boot --mock` (deterministic in-memory
  fake CP; never opens `/dev/umts_*`, never RF, never block device).
- Mock `online` is tagged `"backend":"mock"` and cannot be confused with physical ONLINE.

## 3. Source-to-implementation mapping

| cpboot_v3 source | nuxel-cpbootd implementation |
|---|---|
| `std_boot_parse_toc_img` | `parse_itoc()` (bounds-checked TOC read) |
| `load_cp_image_by_stage` | `xmit_part()` (`struct modem_firmware` stream) |
| `std_security_req` | `security_req()` (`struct modem_sec_req`) |
| `std_udl_req_resp` / `std_udl_stage_*` | `do_udl_req_resp()` (0x9000/0xA000) |
| `std_boot_power_on/start_cp_bootloader/complete_normal_bootup` | `do_on/do_boot_on/do_boot_off` |
| ioctl numeric contract | `_Static_assert` pins vs `s5000ap_uapi.h` |

## 4. Verdict

**Gate C = PASS.** The physical-capable native bootstrap is now complete,
source-faithful, and tested end-to-end in the offline simulator (no stub, no
silent-success stage). It remains disabled by default and requires an immutable
manifest + owner review for any physical run.

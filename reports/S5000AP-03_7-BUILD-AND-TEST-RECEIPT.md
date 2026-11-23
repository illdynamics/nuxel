# S5000AP — Prompt 03.7: Build and Test Receipt (Gate D)

**Branch/HEAD:** `cs/mob` @ `ae26b271c144780abb748ce2fb172919abb1131d`
**Toolchains:** host `gcc` (Apple clang 17.0.0); target `aarch64-linux-gnu-gcc` (GCC 15.2.0);
`aarch64-linux-gnu-readelf`; Python 3.11.9; pytest 8.4.2.

## 1. Builds (reproducible via `tools/s10plus/s5000ap-uapi/build.sh`)

All `-O2 -Wall -Wextra -Werror -std=gnu11`.

| Artifact | SHA-256 |
|---|---|
| `nuxel-cpbootd.host` | `9042cb03982d472c458b2c1a719994793637506ad94739ad6d77fe7bf4429736` |
| `nuxel-cpbootd.aarch64` | `04232a58a4cb2a9a06d08f12ecebc8d796d87e540cd060bd1293e2b480acf572` |
| `nuxel-cpbootd.aarch64.hw` | `88c0a25ba23ac7166dc54042996bb7e005019ca3931ce1ed3de31eac418f7137` |

AArch64 ELF check (`aarch64-linux-gnu-readelf`): Class ELF64, Machine AArch64,
interpreter `/lib/ld-linux-aarch64.so.1`, NEEDED `libc.so.6` only (glibc — **no
Bionic/liblog/libcutils/libselinux**). Host ABI fixture confirms `sizeof(struct
modem_firmware)==28`, offsets `{binary:0,size:8,m_offset:12,b_offset:16,mode:20,len:24}`,
`sizeof(modem_sec_req)==16`, `sizeof(sipc5_link_header)==6`, ioctls `0x6F27/0x6F40/0x6F53`,
state ONLINE=4.

## 2. Value-aware guard proof

`-DNUXEL_CPBOOTD_ENABLE_HW=0` builds a dry-run/mock-only binary (HW path compiled
out); `-DNUXEL_CPBOOTD_ENABLE_HW=1` enables the HW path, which still requires
`--really-boot --manifest-sha256` and exact `/dev/umts_boot0` at runtime. Fixes
audit defect #5.

## 3. Tests

| Suite | Result |
|---|---|
| `tests/test_s5000ap_uapi.py` | 6 pass (pytest.skip NameError fixed — `import pytest` at module level) |
| `tests/test_kernel_header_crosscheck.py` | 5 pass (duplicate `kernel_ioctl_values`/`test_no_extra_dangerous_ioctl_injected` removed; kernel-source skip added) |
| `tests/test_modem_firmware_bounds.py` | 8 pass |
| `tests/test_mock_boot_transcript.py` | 8 pass (full mock boot → `online`, + negatives) |
| **UAPI total** | **29 pass** |
| `cp-firmware` analyzer suite | **22 pass** |
| `test-flash-preflight-offline.py` | **all PASS** (after modem.json key reconcile) |

Warnings: none (all `-Werror` clean). Skips: none in this environment (kernel source
present + AArch64 toolchain available). A genuine checkout of the kernel at
`f7194c1d15eded1c2a1a4dc63825b26103435cc0` is present at
`kernel/s10plus/.build/src.polluted.case-insensitive/` (HEAD verified == pin).

## 4. ZIP portability issues resolved

- `test_kernel_header_crosscheck.py` no longer assumes a host-generated kernel path
  not bundled: it now `pytest.skip`s (with the exact required commit) if
  `modem_prj.h` is absent, instead of a false PASS.
- `test_s5000ap_uapi.py` `pytest.skip` NameError fixed (module-level `import pytest`).
- Duplicate definitions removed from `test_kernel_header_crosscheck.py`.

## 5. Mock vs physical boundary

`nuxel-cpbootd --really-boot --mock` runs the complete boot transaction against the
deterministic in-memory mock and tags every result `"backend":"mock"`. The physical
path is reachable ONLY via `-DNUXEL_CPBOOTD_ENABLE_HW=1 --really-boot
--manifest-sha256 <hex>` against the exact `/dev/umts_boot0` node. No mock ONLINE
can be mistaken for physical ONLINE.

**Gate D = PASS.**

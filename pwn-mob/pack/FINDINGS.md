# Stage 06 Findings — Ranked by Evidential Value

## 1. VERIFIED PUBLIC: Exynos9820-common selects SIPC mode

LineageOS's Exynos9820-common `BoardConfigCommon.mk` explicitly sets:

- `ENABLE_VENDOR_RIL_SERVICE := true`
- `$(call soong_config_set,cbd,protocol,sipc)`
- `$(call soong_config_set_bool,cbd,use_legacy_sipc_ioctl,true)`

Implication: This **device-family implementation** is documented as SIPC, not merely a hypothetical generic SIT interface. It supports prioritizing the pinned SIPC5 framing and Samsung RIL vendor analysis. However, LineageOS's code need not match the exact Nuxel CP firmware/version.

Source: https://github.com/LineageOS/android_device_samsung_exynos9820-common/blob/lineage-23.2/BoardConfigCommon.mk (RIL section).

## 2. VERIFIED PUBLIC: Explicit vendor RIL component inventory exists

Exynos9820-common `proprietary-files.txt` lists:

- `vendor/lib64/libsec-ril.so`
- `vendor/lib64/libril_sem.so`
- `vendor/lib64/libsecril-client.so`
- radio transport/bridge/data/messaging/sim shared libraries
- radio HAL components and RIL daemon (depending on version)

**IMPORTANT COMPATIBILITY WARNING:** Current common manifest says its default source is `N975FXXS9HWHA` (Note10-family), unless a file is specifically pinned. This is **NOT** confirmation of S10+ EFUJ2 compatibility. Do not transplant or copy constant tables without matching version/build and verifying their provenance.

A separate historical S10-era Exynos9820 device tree explicitly lists vendor `libsec-ril.so` and `libsec-ril-dsds.so`. Compare both 32-bit and 64-bit variants. Exact model/build should take precedence over an arbitrary newer Samsung binary.

Sources:
- https://github.com/LineageOS/android_device_samsung_exynos9820-common/blob/lineage-23.2/proprietary-files.txt
- https://github.com/whatawurst/android_device_samsung_beyond1lte/blob/lineage-17.1/proprietary-files-vendor.txt (S10 sibling, not S10+)

## 3. VERIFIED PUBLIC: Correct S10+ SM-G975F stock variant reference

LineageOS's beyond2lte firmware manifest names `SM-G975F`, package `G975FXXSGHWC2`, and its modem assets. **That does not establish that G975FXXSGHWC2 is the installed EFUJ2 baseband**; it is a model-specific provenance anchor and illustrates why firmware versions must be recorded.

Source: https://github.com/LineageOS/android_device_samsung_beyond2lte/blob/lineage-23.2/proprietary-firmware.txt

**Prioritize:** locally available owner-owned `SM-G975F` stock firmware corresponding to the *actual vendor RIL/baseband pairing*. The exact stock AP build corresponding to the installed EFUJ2 RADIO remains **not verified in this pack**. Prefer a known AP+CP matched original set over a random revision.

## 4. VERIFIED PUBLIC: BaseMirror is a concrete released RIL binary static analyzer

The 2024 ACM CCS paper **BaseMirror** analyzed 28 Samsung RIL firmwares and recovered 873 unique commands across the sample. Its table includes `SM-G973F` (Galaxy S10, sibling of S10+, not `SM-G975F`). It identifies **Ipc41X** for the listed later S10 sample; other Samsung devices/versions may use different classes. The project releases `RIL_Analyzer-bw` and `RIL_Analyzer-bwfw` for *offline* static command extraction and distinguishes commands derived from write and read sinks.

- Research: https://zhiqlin.github.io/file/CCS24a.pdf
- Code: https://github.com/OSUSecLab/BaseMirror
- Documented test env: Ubuntu 20.04 x86_64, Ghidra 9.2.2, Java 11, 32 GB RAM and 10 GB disk (README); adapting to modern macOS/Linux is *unverified* here.

**Crucial:** This paper does *not* supply verified EFUJ2 S5000AP SIM IDs in this pack. Its validated command count is research-specific, not a license to send any command to Nuxel. Avoid the repo's attack-payload/automatic-testing subprojects on the phone. Restrict investigation to offline static analysis of authorized binaries.

## 5. VERIFIED PUBLIC: Independent S10 Exynos9820 kernel framing reference

A public S10 `SM-G973F` kernel tree contains `drivers/misc/modem_v1/include/sipc5.h`: link-layer configuration, channel differentiation (FMT/RFS) and lengths, separate from the inner FMT/RFS payload structures. Align with Nuxel's **pinned local kernel**, which remains authoritative.

Source: https://github.com/grant-h/SM-G973F-Kernel/blob/a6c2623ef5ce4644e701d689e60809b0553cf01d/drivers/misc/modem_v1/include/sipc5.h

## 6. USER-REPORTED LIVE: Stage 05 core is real receive-side, but not full telephony

Reported HEAD `c050c75c`: CP ONLINE, `nuxel-radiod` active, FMT `AST_POWERON` received (main 0x13, sub 0x05, type 0x03), RFS 25-byte `DELETE_ALL_VIS` observed. Total-length FMT bug corrected. 75 assertions + two fuzzer gates passed and protected hashes unchanged. These are **not independently verified** here.

**Do not claim:** SIM initialized, registered, cellular data working, Samsung telephony command IDs known, valid RFS ACK semantics, or bidirectional functional exchange.

## 7. USER-REPORTED LIVE: RFS record syntax is partially apparent; semantics UNKNOWN

Observed packet:

`19 00 00 00 0b 01 0f 00 00 00 44 45 4c 45 54 45 5f 41 4c 4c 5f 56 49 53 00`

Consistent structure: 25-byte record; first little-endian u32=25; bytes 4/5 = `0b 01`; u16 at 6=15; reserved-looking bytes 8/9 = 0; 14-byte ASCII `DELETE_ALL_VIS` plus NUL.

**Only established:** this layout matches *this packet*. It does not establish that 0x0b is always a delete operation, that 0x01 is a subcommand, that 15 is universally a path length, that the string is necessarily a filename/opcode, or that any response should be sent. Treat any potentially destructive operation as *deny with no filesystem side effect* until reference semantics and response contract are established.

The existence of RFS traffic shows that the CP *uses or attempts to use* the channel; it does not alone prove that RFS replies are mandatory for SIM or LTE.

## 8. VERIFIED PUBLIC: Legacy code is research reference, not S5000AP command dictionary

Replicant-derived `libsamsung-ipc` and `samsung-ril` show legacy RFS design and security issues, but were written for older modem generations. They are useful for identifying conceptual classes of commands and security boundaries. They must **not** be used as a one-to-one command-ID mapping for S5000AP.

Sources:
- https://github.com/LineageOS/android_external_libsamsung-ipc
- https://github.com/Ksys-labs/samsung-ril/blob/master/rfs.c
- https://www.fsf.org/blogs/community/replicant-developers-find-and-close-samsung-galaxy-backdoor

## Next engineering priority

The best next move is **not** another kernel rewrite. Verify the exact vendor RIL binary provenance, perform offline static RIL analysis, build a source-backed matrix for SIM/network/bearer message semantics, and only then implement and verify safe live bidirectional exchange. RFS/secure NV dependency remains a separate owner-controlled gate.

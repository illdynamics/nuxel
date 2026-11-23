# Source Index and Claim-to-Source Mapping

Every entry is an **external web reference reviewed on 2026-11-23**, not a locally audited Nuxel artifact. URL records are for lookup; do not import vendor ELF binaries into a public Nuxel repository.

| Rank | Source | What it establishes | What it does NOT establish |
|---|---|---|---|
| A | [LineageOS Exynos9820 `BoardConfigCommon.mk`](https://github.com/LineageOS/android_device_samsung_exynos9820-common/blob/lineage-23.2/BoardConfigCommon.mk) | Exynos9820 Lineage config selects `cbd` protocol `sipc` + `use_legacy_sipc_ioctl` | Current exact Nuxel CP version or SIM command IDs |
| A | [LineageOS Exynos9820 `proprietary-files.txt`](https://github.com/LineageOS/android_device_samsung_exynos9820-common/blob/lineage-23.2/proprietary-files.txt) | Names vendor RIL, client, bridge and radio-module artifacts; common manifest says N975F source unless pinned | That N975F binaries will work on G975F EFUJ2 |
| A | [LineageOS beyond2lte `proprietary-firmware.txt`](https://github.com/LineageOS/android_device_samsung_beyond2lte/blob/lineage-23.2/proprietary-firmware.txt) | SM-G975F target and G975FXXSGHWC2 firmware provenance in this Lineage version | Same revision as Nuxel EFUJ2 |
| A | [LineageOS beyond2lte repo](https://github.com/LineageOS/android_device_samsung_beyond2lte) | Confirmed device tree for user's S10+ device codename | Complete open Samsung radio protocol |
| B | [whatawurst S10 17.1 proprietary vendor manifest](https://github.com/whatawurst/android_device_samsung_beyond1lte/blob/lineage-17.1/proprietary-files-vendor.txt) | Historical 32/64-bit libsec-ril and RIL supporting artifact names | Exact S10+ revision equivalence |
| A | [Samsung S10 kernel `sipc5.h` pinned public commit](https://github.com/grant-h/SM-G973F-Kernel/blob/a6c2623ef5ce4644e701d689e60809b0553cf01d/drivers/misc/modem_v1/include/sipc5.h) | SIPC5 link header framing, length logic, FMT/RFS channel classes | Inner Samsung FMT telephony command meaning |
| A | [BaseMirror research paper (CCS 2024)](https://zhiqlin.github.io/file/CCS24a.pdf) | Analyzes Samsung proprietary RIL command extraction and lists a SM-G973F S10 sample, categorized Ipc41X | Verified S5000AP/EFUJ2 command mapping or safe live commands |
| A | [BaseMirror source](https://github.com/OSUSecLab/BaseMirror) | Offline RIL analyzer source and build requirements (`RIL_Analyzer-bw`, `-bwfw`) | Out-of-box compatibility with Nuxel, Apple Silicon, new Ghidra |
| B | [ShannonBaseband research issue #7](https://github.com/grant-h/ShannonBaseband/issues/7) | Independent research roadmap: RIL message tracing and RFS understanding | A completed solution or decoded command table |
| B | [Legacy libsamsung-ipc](https://github.com/LineageOS/android_external_libsamsung-ipc) | Historical Samsung IPC handling examples | S5000AP command IDs |
| B | [Legacy RFS implementation](https://github.com/Ksys-labs/samsung-ril/blob/master/rfs.c) | Old Samsung RFS concepts | Safe direct reuse on current modem |
| A | [FSF Replicant remote filesystem analysis](https://www.fsf.org/blogs/community/replicant-developers-find-and-close-samsung-galaxy-backdoor) | Historical security risk of CP-controlled AP filesystem operations | Proof the same exploit applies to S10+ |
| B | [ShannonLoader](https://github.com/FirmWire/ShannonLoader) | Ghidra loader for *CP baseband* binaries and sample S10 family firmware format | AP-side RIL interface semantics. CP baseband != AP vendor ELF |

## Component search order

1. **Local matched S10+ stock AP vendor image**: `vendor/lib64/libsec-ril.so`, older `vendor/lib/libsec-ril.so`; `libsec-ril-dsds.so`, `libril_sem.so`, `libsecril-client.so`; `vendor/bin/hw/rild`; radio `bridge/channel/sim/data` libraries. Inventory names, `sha256`, ELF machine, build fingerprint and matching vendor image. Do NOT paste binaries/strings to public tickets.
2. **Original Nuxel kernel tree**: `drivers/misc/modem_v1/include/sipc5.h`, `modem_v1.h`, `modem_prj.h`, SHMEM receive path and `io_device` device behavior.
3. **Owner-authorized local historical captures**: matching boot/session IDs, timestamps, CP kernel ONLINE status and redacted metadata. Never infer AP→CP request semantics from CP→AP unsolicited notifications alone.
4. **Public sibling S10 references** only to test candidate interpretations against exact original firmware, not to assert equality.
5. **Paper/tooling** for extracting candidate IDs and call relationships offline, not generating live inputs.

## Version matrix for the agent to fill

| Artifact | Model/build | SHA256 | Architecture | Provenance | Validated against EFUJ2? |
|---|---|---|---|---|---|
| Installed CP RADIO | SM-G975F, EFUJ2 report | `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7` (reported) | CP firmware | Existing Nuxel Stage 04/05 report | Reported yes |
| Local matching `libsec-ril.so` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | NO |
| Related Lineage 23.2 `libsec-ril.so` | Common N975F source unless pinned | Manifest uses SHA1-like 40-character hash, not SHA256; verify provenance | UNKNOWN | Public text file only | NO |
| Public research SM-G973F RIL | SM-G973F, study's Android 12 build | UNKNOWN | UNKNOWN | BaseMirror paper | NO |

**Do not mistake a 40-character manifest hash for a 64-character SHA-256.** Verify actual local files with `sha256sum` or equivalent when lawful and accessible.

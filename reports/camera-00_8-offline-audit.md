# Camera Prompt 00_8 — independent offline audit (2026-11-22)

**Source:** user-uploaded `nuxel-cs-cam (5).zip`, the attached Prompt01/Prompt02 and the user's Prompt00_7 execution summary. **No live SSH or private recovery artifacts were available here.**

- The Master Contract and Prompt00_7 instructions exist in `pwn-cam/`. Their on-device execution is *reported* in the supplied conversation, not independently verifiable from this ZIP.
- The user supplied a live FDT SHA prefix `761df64a`, rev 26 / DTBO entry9 and off-device copy hashes reported matched. Full FDT bytes, partition copies, manifests, signatures, device health logs and owner trust anchor are intentionally absent. These cannot be recreated from a public archive.
- The existing GPIO validator wrongly treated a legitimate stock flash/PMIC duplicate as necessarily dangerous. The revised validator accepts **only unchanged duplicate claims found in a hash-pinned golden merged FDT**, and continues to reject new owners, altered flags, missing/false golden hash and unrelated FDT deltas.
- BOOT apparently uses separate DTB+DTBO with no BOOT-appended FDT. The old validator wrongly made that format unrepresentable; the revised validator supports it only with SHA-bound separate base, selected overlay, merged FDT and explicit selected board/revision evidence. Mixing layouts or omitting proof remains fatal.
- The release wrapper now requires an explicit manifest `device.dt_layout` and, for `separate-dtb-dtbo`, a verified `proof.bootloader_dt_source_verified` with absent/null appended index. Owner signing remains mandatory.
- Regression suite expanded from 44 to 51 synthetic tests, with a combined signed **synthetic** separate-layout stock GPIO no-op and signed negative case. Do not interpret as a real boot pass.
- The current archive lacks complete Linux4 kernel sources and the native CSIS/CIS/AK7374 driver files required to complete Prompt02.

## Mandatory decision

`PROMPT00_7_LIVE_EVIDENCE=REPORTED_ONLY`

`PROMPT01_OFFLINE_GATES=TESTED_SYNTHETIC_ONLY`

`REAL_GOLDEN_NOOP=BLOCKED` (live signed manifest, private images and real gate run not supplied)

`PROMPT02_ENTRY=BLOCKED` pending live proof and trusted signing.

`ON_DEVICE_WRITES=0` (this offline session); `ON_DEVICE_REBOOTS=0` (this offline session).

See `pwn-cam/01_PROMPT_00_8.md` for next host + read-only live-device actions.

# PWNAGE-65000 — Kick off the Nuxel NFC bring-up mission

Read `full-pwnage-65000.md` in the repository root from beginning to end, then execute it as an implementation task. Do not return a research-only summary or merely install `neard`/`nfc-list` and declare success.

The S10+ NFC kernel work is already partly complete. Start by reading `docs/beta-finalization/live/PWNAGE-53000-REPORT.md`: it records the bound Samsung controller at I²C `7-0027`, `/dev/sec-nfc`, the generic/vendor sysfs class collision fix, and the verified `sec_s3nrn82_firmware.bin` hash. Re-check that evidence on the actual phone before changing anything.

**Critical architectural fact:** the pinned Samsung `sec_nfc` driver exposes a privileged raw I²C misc-device transport (`/dev/sec-nfc`) through `open/read/write/poll/ioctl`; it does not, by itself, register a standard Linux NCI/netlink adapter. Therefore, installing Fedora's `neard` or generic NFC utilities alone will not make this hardware work. Inspect the exact pinned `sec_nfc.c`/`sec_nfc.h`, matching Samsung vendor NFC HAL/configuration and firmware initialization path. Prove the framing and protocol; never guess commands or upload firmware speculatively.

Implement the smallest safe native Nuxel architecture: one least-privilege service owns the device, the bridge calls a versioned local API, and Quick Settings/Settings can enable NFC and run a bounded scan. Preserve default-OFF privacy, exclusive device ownership, strict timeouts, suspend/cleanup behaviour and read-only-first operation. Do not expose `/dev/sec-nfc` to apps, use raw I²C, enter bootloader/NPT/test mode, or claim payments/eSE/HCE support.

Fix the stale NFC provider/diagnostics and exact firmware candidate handling, test the transport and NDEF parser with mocks, and only mark hardware success after a real physical S10+ tag is detected and a known NDEF record is read correctly. Mocks and package presence must never count as a physical pass.

Work in phases from the big specification. Preserve pre-existing changes; do not reset/clean the repo. Do not flash a kernel or update controller firmware without explicit owner approval. Deploy user-space changes in reversible stages, provide a full change report and rollback instructions, and run the relevant repository regression gates.

**Required deliverables:** implemented source changes, tests, updated NFC policy/diagnostics/docs, build/deploy instructions, rollback procedure, and a truthful evidence matrix separating kernel, firmware, transport, protocol, physical tag, NDEF and UI verification. If matching Samsung protocol evidence is unavailable, complete all safe work and report the exact blocker rather than fabricating a working reader.

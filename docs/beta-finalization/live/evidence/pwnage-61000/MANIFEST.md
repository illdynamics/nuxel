# PWNAGE-61000 evidence manifest

Status: **IMPLEMENTED_NOT_PHYSICALLY_VERIFIED**.

| Artifact | Purpose |
|---|---|
| `live-inventory.txt` | Read-only handset snapshot: identity, nodes, DT, firmware, guard, packages. No device node opened. |
| `live-config.txt` | Live `/proc/config.gz` decompressed. 53/53 required capabilities match. |
| `live-mfc-inventory.json` | Live `nuxel-mfc-diag --inventory --json`; resolves `/dev/video6` and reports `BLOCKED_FIRMWARE_MISSING`, `safe_open_allowed=false`. |
| `live-diag-inventory.txt` | Live inventory/status text. |
| `mfc-firmware-verify.txt` | Exact upstream blob: 685832 bytes, SHA-256, ARM header, manifest contract. |
| `mfc-source-audit.txt` | Pinned source excerpts: direct loader, DT, V4L2 ops, DMA-BUF capture, timeouts. |
| `kernel-build.log` | Full patched kernel build; `BUILD_EXIT=0`, capability parity PASS. |
| `kernel-build-artifacts.txt` | Image.gz/.config/DTB hashes, 53/53 config, objdump proof of `request_firmware_direct`. |
| `mfc-decode-build.log` | Clean cross-build of the aarch64 vendor-ABI helper. |
| `pytest-pwnage61000.log` | 36/36 new tests. |
| `pytest-regression.log` | Combined regression attempt (script-style suites abort collection; pre-existing). |
| `regression-summary.txt` + `regression/` | Per-directory regression matrix. |
| `pytest-full.log` | Full-suite attempt; aborts on pre-existing import-time `sys.exit()` in `tests/pwnage44000`. |
| `SHA256SUMS` | Hashes of all mission files/evidence/build artifacts. |
| `tools/s10plus/a61/mfc-test-media.json` | Fixture manifest: software reference plus NOT_PRESENT 720p/1080p/HEVC/4K placeholders. |

Not present by design:

- no MFC decode log, frame checksum, screenshot, benchmark or thermal log;
- no live firmware install;
- no flashed kernel/DTB.

Those require the owner-approved physical test in
`docs/beta-finalization/live/PWNAGE-61000-MFC-OPERATOR.md`.

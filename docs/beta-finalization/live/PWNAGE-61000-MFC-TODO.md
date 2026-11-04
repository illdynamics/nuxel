# PWNAGE-61000 — MFC bring-up live TODO

Status legend: `DONE`, `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, `NOT_TESTED_ON_DEVICE`.

Target: Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820, Linux 4.14.253 downstream).
Mission order from `full-pwnage-61000.md` is being followed: inventory → source/IP/DT/firmware audit → firmware verification → safe kernel changes → build/tests → inventory-only diagnostic → owner-approved open → decode proof → player integration → benchmark → guard transition → regression → report/rollback.

## Live state snapshot (2026-11-03)

- [x] DONE — repository HEAD recorded (`0bed35d881ba674a21f67d31501e84f1031992b5`, branch `main`).
- [x] DONE — pinned kernel source present at `kernel/s10plus/.build/src` and exactly `f7194c1d15eded1c2a1a4dc63825b26103435cc0`.
- [x] DONE — live handset reachable by Wi-Fi SSH (`root@10.20.30.16`, key `~/.ssh/wicked_wqn_id_rsa`), boot ID `954ea1bf-732c-4274-825f-ff2788b14467`.
- [x] DONE — read-only inventory captured to `evidence/pwnage-61000/live-inventory.txt`; no `/dev/video*` node was opened.
- [x] DONE — MFC decoder identity resolved by sysfs: `/dev/video6` = `s5p-mfc-dec0`, parent `188d0000.mfc`, bound driver `s5p-mfc`, DT compatible `samsung,exynos-mfc`, `ip_ver = 0x1300`.
- [x] DONE — MFC firmware request name confirmed from source: `mfc_fw.bin` (`MFC_FW_NAME`).
- [x] DONE — firmware located at the pinned source-of-record (`Linux4/proprietary_vendor_samsung@05c9ef8f…`, `exynos9820-common/.../mfc_fw.bin`), size 685832, SHA-256 `f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f` — matches the manifest candidate.
- [x] DONE — live `/lib/firmware/mfc_fw.bin` is ABSENT. This is the exact condition that caused the old 60 s `request_firmware()` userspace-fallback wait.

## Workstream A — driver/ABI audit

- [x] PASS — driver implementation: `drivers/media/platform/exynos/mfc/` (vendor V4L2 M2M-style, not the mainline `s5p-mfc`).
- [x] PASS — built config has `CONFIG_VIDEO_EXYNOS_MFC=y`, `CONFIG_VIDEOBUF2_DMA_SG=y`, `CONFIG_EXYNOS_IOMMU=y`, `CONFIG_V4L2_MEM2MEM_DEV=y`.
- [x] PASS — DT node `mfc@188D0000` has compatible `samsung,exynos-mfc`, `ip_ver = <0x1300>`, one IRQ, `aclk_mfc`, two SysMMUs, MFC power domain, hwfc/mmcache regions and QoS tables.
- [x] PASS — API classification: **vendor-specific nonstandard V4L2 M2M-style ABI**. It exposes OUTPUT/CAPTURE mplane queues, but does **not** implement `VIDIOC_DECODER_CMD`, `V4L2_EVENT_SOURCE_CHANGE`, MMAP, Request API or `V4L2_CAP_VIDEO_M2M(_MPLANE)`.
- [x] PASS — capture buffers are DMA-BUF-only in the vendor path (`mfc_get_iovmm()` calls `dma_buf_get(vb->planes[i].m.fd)`); MMAP is rejected. OUTPUT buffers may use USERPTR or DMA-BUF.
- [x] BLOCKED — firmware-reported version can only be read after `RISC_ON`, so exact firmware ABI match is `NOT_TESTED_ON_DEVICE`.
- [x] PASS — compatibility matrix written in `PWNAGE-61000-MFC-BASELINE.md`.

## Workstream B — firmware

- [x] PASS — fetched the exact blob from the pinned upstream tree; hash matches the manifest. Evidence: `evidence/pwnage-61000/mfc-firmware-verify.txt`.
- [x] PASS — manifest provenance fields corrected/expanded and kept `required: false` (software-only images remain buildable).
- [x] PASS — `fetch-vendor-blobs.sh` already covers `exynos9820-common/proprietary/vendor/firmware/`, so a clean fetch reproduces the blob.
- [x] PASS — `install-firmware.sh --verify-mfc` added; fails closed on missing/hash mismatch; does not fabricate a file.
- [x] PASS — correct blob staged under `firmware/s10plus/blobs/vendor-firmware/` locally (gitignored) for image builds.
- [ ] NOT_RUN — live installation into `/lib/firmware` deliberately NOT done before the safe kernel is deployed. Installing it on the old kernel would turn a prompt firmware-missing failure into a possible hardware-init hang. Install only after the patched kernel is running and the owner approves the hardware test.

## Workstream C — safe kernel changes

- [x] PASS — `0008-mfc-firmware-fail-closed.patch` written; `.required` sidecar present.
- [x] PASS — `request_firmware()` replaced with `request_firmware_direct()` so a missing file returns `-ENOENT` immediately instead of waiting 60 s for the userspace fallback.
- [x] PASS — failed request no longer logs a misleading `invalid path`; exact name and error are logged.
- [x] PASS — NULL/empty/short/oversized firmware checks and clean unwinds.
- [x] PASS — unsupported DT `ip_ver` is rejected with `-ENODEV` in probe before firmware/hardware access.
- [x] PASS — existing wait paths audited: `MFC_INT_TIMEOUT=4000 ms`, one retry at `2×4000 ms`; `MFC_INT_SHORT_TIMEOUT=800 ms`; hwlock 5000 ms. No unbounded wait remains on the expected missing-firmware path.
- [x] PASS — config fragment and `live-required.config` updated with the MFC capability set.
- [x] PASS — patched kernel builds: `Image.gz` sha256 `cfc80df9…90ed7`, capability parity 53/53.
- [x] PASS — compiled `mfc_load_firmware` calls `request_firmware_direct` (objdump evidence in the report).
- [ ] NOT_RUN — patched kernel not flashed/booted. The running handset still has the pre-patch (`-dirty #5`) kernel.

## Workstream D — diagnostic

- [x] PASS — `nuxel-mfc-diag` implemented. Default/only safe mode is `--inventory`; it reads sysfs and never opens `/dev/video*`.
- [x] PASS — active mode requires an exact node (`/dev/video6` or an allow-listed sysfs identity), `--allow-hardware-open`, and a matching safety receipt.
- [x] PASS — status schema `nuxel.mfc.status/1` and read-only `status --json`.
- [x] PASS — `--self-test`, `--query-only`, `--decode-test`, `--json`, `--version` semantics implemented.
- [x] PASS — experimental `nuxel-mfc-decode` helper source added and cross-compiled; NOT executed on hardware.
- [ ] NOT_RUN — `--query-only` / `--decode-test` on the handset. Requires patched kernel + owner approval.
- [x] PASS — live inventory/status only; `/dev/video6` was never opened.

## Workstream E/F/G — player, performance, DMA-BUF

- [x] PASS — truthful policy implemented: default `software` (`mpv --hwdec=no`); `auto`/`hardware` refuse unless status is `AVAILABLE_HARDWARE_DECODE` from a real test.
- [x] PASS — boot/preload path unchanged (`--hwdec=no`).
- [x] PASS — GStreamer guard unchanged and still disables `video4linux2`, `v4l2codecs`, `kms`, `opengl`.
- [x] PASS — WirePlumber `hardware.video-capture = disabled` unchanged; audio/Bluetooth required.
- [x] PASS — `MFC_DECODE` / `MFC_DMABUF_EXPORT` / `MALI_EGL_IMPORT` / `PHOC_COMPOSE` / `FB_BRIDGE_PRESENT` / `ZERO_COPY_END_TO_END` kept as independent claims; no zero-copy claim made.
- [ ] NOT_TESTED_ON_DEVICE — codec matrix, CPU/thermal benchmark, player playback, GStreamer transition, DMA-BUF import.

## Build / tests

- [x] PASS — `pytest tests/pwnage61000` -> 36 passed.
- [x] PASS — live `nuxel-mfc-diag --inventory` resolves `/dev/video6` and reports `BLOCKED_FIRMWARE_MISSING` with `safe_open_allowed=false`.
- [x] PASS — kernel patch applies to the pinned source and MFC object compiles.
- [x] PASS — full `Image.gz` + `dtbs` build exits 0; capability parity 53/53.
- [x] PASS — image verifier script added.
- [ ] NOT_RUN — full clean `make ci` image build (not required to prove the MFC source path, and the rootfs build needs the full Fedora container).

## Safety / final

- [x] PASS — no flash, no reboot-before-test, no protected partition, no camera capture, no MFC node open so far.
- [x] PASS — rollback script added; firmware removal is narrow (`/lib/firmware/mfc_fw.bin` only).
- [x] PASS — owner-requested reboot performed at the end of the mission; new boot ID `95b82b79-3d51-4a48-955e-b446551ccffd`; SSH, phoc and WirePlumber returned.
- [x] PASS — post-reboot `nuxel-mfc-diag --status` still resolves `/dev/video6`, reports `BLOCKED_FIRMWARE_MISSING`, guard active, `safe_open_allowed=false`.
- [x] PASS — software fallback after reboot: `mpv --hwdec=no` on the preload asset returned 0.
- Final status: **IMPLEMENTED_NOT_PHYSICALLY_VERIFIED**.


## PWNAGE-71000 deployment preparation (2026-11-03)

- [x] PASS — flashable boot image built and verified with `verify-boot-image.py`; 48,596,992 bytes, 9,074,688 bytes slack.
- [x] PASS — live BOOT backup captured read-only and hash-verified on host and phone.
- [x] PASS — exact live LZMA initramfs preserved byte-for-byte; no recompression.
- [x] PASS — DTB MFC node/ip_ver verified; boot image preserves the proven no-appended-DTB layout.
- [x] PASS — 61000 tests 36/36; diag self-test 17/17; AArch64 decoder hash matches.
- [ ] OWNER_ACTION_REQUIRED — write BOOT and reboot.
- [ ] OWNER_ACTION_REQUIRED — prove patched missing-firmware timing.
- [ ] OWNER_ACTION_REQUIRED — install firmware/userspace, safety receipt, first open, decode, benchmark, guard transition.

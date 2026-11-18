# Nuxel S10+ — Camera recovery evidence audit (2026-11-17)

## Scope and reliability

The uploaded `nuxel-feat-cam.zip` was **not a complete, conventionally readable ZIP** at inspection time. `zipfile.ZipFile` and `unzip` both rejected it because the end-of-central-directory record was absent. The local file stream exposed the firmware directory and manifest; all eight firmware members used in this report were decompressed and individually checked against their ZIP CRC-32, then SHA-256-hashed. This cannot certify repository content omitted or truncated after the recoverable segment. In particular, `reports/CAMERA-FIRST-REAL-FRAME.md`, `tools/` and the two newest worktree commits could not be verified independently inside this attachment. The reported live hardware observations in the user's message are therefore treated as **agent-reported**, not re-measured.

## Independent camera firmware comparison

| Filename | Uncompressed bytes | Actual SHA-256 | Manifest SHA-256 | Matches? |
| --- | ---: | --- | --- | --- |
| `fimc_is_fw_mcu.bin` | 34,348 | `0887a6c5f2ad8b4d261473889b3b4c5e44497df4b487775e86ae9cf9e535acdf` | `0887a6c5f2ad8b4d261473889b3b4c5e44497df4b487775e86ae9cf9e535acdf` | YES |
| `fimc_is_lib.bin` | 4,432,944 | `e0bb2c36bf43e9a864037552640be4b7b57e5944a0c86f8485900152bd5fbbcd` | `08e54ac3817b4c9d4851a90a7b3ac3e5b30ba98378c217ce8ea51db0ff98f1db` | **NO** |
| `fimc_is_rta.bin` | 3,986,208 | `9ca4668a2be85edd8c14b5243db235fd145db526915216dab17fae2c8e3ffc30` | `12809be7b38919b7f98ad14c85d55d3b6d2b029304e7baef1141aca7dd94b1e9` | **NO** |
| `setfile_2l4.bin` | 4,080,120 | `bd32765a5afea316e6e4a5dc466ee07e7f4767d90c4a07ea9823fd85d7e86863` | `876638f09d7ec4ad4ca695d7219267f236c9ea832252fd93296724c176a6b0f3` | **NO** |
| `setfile_3j1.bin` | 3,944,440 | `dc352608088d409dfc9faf3c5475d045220f5316f49cee4d6619dd98ce076876` | `4e68f97def312d9b4827d9eab3c3a10f2d476ed4aa76a9c42d4b7b84ef571bb9` | **NO** |
| `setfile_3m3.bin` | 2,858,784 | `a696783eec88515b2e14e21c1288baeb61e402ec245a9b2a7e88084139cd0abf` | `92c4bf1c197215d9a870e27051c04ff677c58dafc530355ecff69b85fddac1cd` | **NO** |
| `setfile_3p9.bin` | 3,265,896 | `226987e49b416ad6a5548069a6abe370ddd8b1ab49bf5005731950fca450100f` | `6e774bc773833d49046d3d3cb750181a990fb10ea76654d8b87501b23e1883fd` | **NO** |
| `setfile_4ha.bin` | 3,944,440 | `dc352608088d409dfc9faf3c5475d045220f5316f49cee4d6619dd98ce076876` | `4e68f97def312d9b4827d9eab3c3a10f2d476ed4aa76a9c42d4b7b84ef571bb9` | **NO** |

**Independent result: 1 / 8 match.** `fimc_is_fw_mcu.bin` alone matches the SHA-256 recorded in `firmware/s10plus/manifest.yml`. The IS library, RTA and all five setfiles do not. The bundled `setfile_3j1.bin` and `setfile_4ha.bin` share a SHA-256; the old manifest ALSO assigns them the same SHA-256. Identical contents are therefore suspicious only in context, not independent proof of corruption. Do **not** change the manifest to match whichever binaries happen to be on disk without a trustworthy provenance reconciliation.

The manifest explicitly identifies `Linux4/proprietary_vendor_samsung` at `05c9ef8f16e0ad5ab274e408c120dfd99fd5c628` as its source. The original repository already includes `firmware/s10plus/fetch-vendor-blobs.sh`, but that script's download path itself does not verify the expected camera hashes before placing files in the destination. The accompanying original `verify-firmware.sh` categorizes camera firmware as `required: false` and skips optional entries, so **a green generic firmware verification is not evidence these camera blobs match**. The new `camera_firmware_audit.py` and `fetch_pinned_camera_reference.py` address this blind spot **on the host only**.

## What the agent's latest camera report establishes

This section is from the user's pasted `codex` output and is **not independently verified against a live handset**:

- `SM-G975F`, hardware revision 26; Exynos9820 kernel `4.14.253-gf7194c1d15ed-dirty`.
- 68 FIMC-IS video nodes; no `media`/`v4l-subdev` nodes were reported.
- Bounded rear-main `2L4` sensor enum 37 selection caused EEPROM-calibration reading and terminated at `Camera: Failed open phone firmware` / `fimc_is_sec_run_fw_sel ... (-5)`.
- No real frame, queueing/streaming, persistent deployment, ISP install, reboot or flashing.
- Commits `180d9839` and `a4ad813c` reportedly fix zeroed-`G_FMT` false success and document the firmware gate in a separate `/tmp/nuxel-camera-endgame-audit` worktree.
- A safe single-frame capture remains unverified.  `-5` is an errno-code clue, not an independently proven missing-file diagnosis; inspect the actual kernel branch to identify the exact failed operation.

### Progress comparison

| Stage | Earlier position | Latest report |
| --- | --- | --- |
| Sensor presence | Bound sensors and V4L2 nodes | 2L4 physically selected once |
| Calibration | Unproven | EEPROM read reached |
| Firmware selection | Untested | Reproducible error location observed |
| Firmware provenance | Eight blobs assumed present | Seven manifest mismatches independently confirmed here |
| V4L2 probe | Could mistakenly accept empty G_FMT | Agent-reported fail-closed change |
| Actual frame | None | **Still none** |
| Apps/portals/recording | Unverified | Still unverified |

## Reuse-first research

1. **Your owner-held SM-G975F G975FXXS9DTK9 Android 10 AP/vendor archive, already acquired for SSP:** highest-priority source candidate. Locate it; inspect vendor firmware and build props read-only. Compare all eight files and stock-camera HAL revisions, then correlate with `kernel/s10plus` loader build configuration, sensor ID/EEPROM and paths. Do not assume "stock" always equals the current kernel revision, but it is a better lead than random blobs.
2. [Linux4/proprietary_vendor_samsung](https://github.com/Linux4/proprietary_vendor_samsung), pinned by the existing Nuxel manifest. The included downloader **only downloads reference candidates if explicitly opted in and their SHA-256 equals the manifest**. Public vendor files are not thereby proven compatible with G975FXXS9DTK9.
3. [Evolution-X beyond2lte vendor manifest](https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk). Independently lists `fimc_is_lib.bin`, `fimc_is_rta.bin`, `fimc_is_fw_mcu.bin`, `setfile_2l4.bin`, `setfile_3j1.bin`, `setfile_3m3.bin`, `setfile_3p9.bin`, `setfile_4ha.bin`. Its published versions are **cross-check candidates**, not matched installation packages.
4. [libcamera supported pipelines](https://libcamera.org/faq.html) and [pipeline handler guide](https://docs.libcamera.org/master/guides/pipeline-handler.html): current upstream does not list this Samsung Exynos9820 FIMC-IS2 hardware. Do not build a generic `libcamera` layer before getting a single physical V4L2 frame. Samsung legacy V4L2 nodes may work without `/dev/media*` endpoints.

## Decisive next investigation

1. Find the **original kernel-side exact filename and search path** that produced “Failed open phone firmware”. Inspect the source string/function path, error mapping, and preceding logs; distinguish missing path, corrupted blob, rejected version, module-calibration mismatch and permissions.
2. Reconstruct the owner-held stock `vendor/firmware` directory from the same AP used for SSP. Compare its eight relevant camera files with both the Nuxel manifest and current untrusted bundles. Validate owner-held archive provenance and build identity. Keep stock data outside Git.
3. Choose **one verified mutually compatible firmware/lib/RTA/setfile group**, matching the camera module and kernel selection logic. Stage host-side only. Do not mix random upstream binaries or regenerate checksums merely to suppress failure.
4. Prepare bounded, owner-reviewed physical first-frame trial only after selecting exactly which files the kernel expects. Capture one nonzero, actually dequeued frame with valid format, dimensions, stride, buffer lengths, timestamps and content. Then expand to multiple sensors and PipeWire/portal/app integrations.

## Limits

No physical camera connection or device write was performed in this independent audit. None of the new tools can substitute for an OEM blob or guarantee a first frame. Do not call any step 100% functional until the handset passes the physical acceptance matrix.

# Nuxel S10+ SSP first-light — continuation kit

## What this kit is / is not

This is **original host-side investigation code + one actionable agent prompt**, not new firmware, a Linux kernel driver, an Android runtime, or a flashable ZIP. The sensible next step is to reuse the matching Samsung vendor `lhd` daemon and the repository's already-implemented BBD transport rather than guessing at a proprietary firmware protocol.

**This pack contains no proprietary binaries and requires no device access to audit the existing archive.** It does not recover a missing Android system image. Obtain the exact matching stock Android `system` / `vendor` / `apex` files from the owner's authorized backup or official model/build and keep them in an owner-local working directory.

The uploaded ZIP already has `packs/sensors/scripts/extract-s10plus-ssp-runtime.sh`, `collect-elf-deps.py`, and `verify-s10plus-ssp-runtime.py`, plus existing `lhd`/sensor HALs. The new helper here is an **offline complement**, not a reimplementation of those ADB scripts.

## Files

- `AGENT_CONTINUATION_PROMPT.md`: hand this exact standalone prompt to the agent; includes safety, investigations, implementation, hardware acceptance and rollback.
- `ssp_runtime_audit.py`: original stdlib-only Python 3.9+ tool. Inspects owner Nuxel ZIP or extracted repo, parses ELF dynamic dependencies, optionally searches a matching extracted stock Android tree, writes JSON/Markdown manifests, and can locally stage files in a new directory. No ADB, reboot, firmware write, or binary execution.
- `test_ssp_runtime_audit.py`: seven offline tests; builds synthetic ELF data rather than shipping vendor binaries.
- `ARCHIVE_FINDINGS.md`: sourced findings from the provided ZIP and agent report, including the snapshot mismatch.
- `SOURCES.md`: upstream starting points.
- `baseline/`: offline inspection report from the four uploaded vendor components; not proof of compatibility or hardware success.

## Quick start: Mac/Linux host

From this pack's folder:

```bash
python3 -S test_ssp_runtime_audit.py
python3 -S ssp_runtime_audit.py \
  --repo-zip "/path/to/nuxel-main (2).zip" \
  --report-dir ./my-ssp-report
```

If your local ZIP cannot be opened, use the extracted repo folder:

```bash
python3 -S ssp_runtime_audit.py \
  --repo-root "/path/to/nuxel-main" \
  --report-dir ./my-ssp-report
```

Optional, after the agent has identified an owner-supplied **matching** stock Android filesystem tree:

```bash
python3 -S ssp_runtime_audit.py \
  --repo-root "/path/to/nuxel-main" \
  --android-root "/path/to/EXTRACTED_STOCK_ANDROID_ROOT" \
  --report-dir ./stock-audit \
  --stage-runtime "./OWNER-LOCAL-SSP-STAGED"
```

`--stage-runtime` **copies files to a new local host directory**, refuses to overwrite prior staged files, and never creates a boot image. It does **not** run `lhd` and does not prove Android linker namespace, services, or kernel device compatibility. The tool exits code `3` if dependencies/linker/seeds are missing, `0` if the limited static checks pass, or `4` on a staging/source failure.

The expected extracted tree contains paths such as `system/bin/linker64`, `system/lib64/*.so`, `vendor/lib64/*.so`, and where appropriate `apex/...` or VNDK directories. It also accepts common nested `system/system/...` and `system_root/system/...` layouts. Fully unpack any needed APEX packages yourself/through the agent's reviewed extraction method before static inspection. No raw sparse Android image parsing is included.

## Why not write firmware now?

The user-provided agent report says a 438,895-byte embedded patch exists, but real SSP motion samples are still `0,0,0`; the report also notes the ACK state machine is not yet proven. Writing replacement firmware or blind hub-memory upload would be premature. The matching vendor `lhd` plus Bionic runtime, or a carefully tested continuation of the native downloader, are the two evidence-led alternatives.

## Things the agent must verify before acting

- Actual active git branch/commit and **live** kernel, because the ZIP/report and first-light agent message describe different snapshots.
- Exact stock Android build, device/SoC, AArch64 Bionic linker, VNDK/APEX mappings, and recursive library closure.
- Device-node access and reset hazards before any isolated vendor daemon trial: the older repository reports a hard-reset hazard on the GPS standby/power GPIO.
- True hub communication and changing physical gyro/accel data through sensor class/IIO, plus suspend/resume.
- Auto-rotation performance only *after* sensor data exists.

**No 100% hardware guarantee:** without a working phone connection and matching stock runtime, the remaining device-level fix cannot be implemented or validated in this chat.

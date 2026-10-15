# Patches applied

All changes are in the Nuxel repo (working tree, not committed). Nothing was
written to the phone.

## P1 — `boot/initramfs/init.sh`: remove the cmdline dependency, add persistent diagnostics

Source of the problem: the whole S10+ boot flow was configured through the Android
boot image header `cmdline` (`boot/s10plus/boot-config.txt`,
`tools/s10plus/patch-boot-from-upload.py` copies `header_cmdline` verbatim), but
Samsung S-Boot replaces `/chosen/bootargs` and never forwards that field
(proven on this unit — see DEVICE-EVIDENCE.md §5).

Changes (all inside the existing file; no new boot stages):

1. **Device auto-detection.** When `nuxel.device=` is absent, `DEVICE` is derived
   from `/proc/device-tree/model` (`*BEYOND2LTE*`, `*beyond2lte*`, `*beyond1lte*`)
   or `/proc/device-tree/compatible` (`*exynos9820*`) ⇒ `s10plus`. Without this,
   `DEVICE=""` selected the generic A/B branch, which cannot resolve this root.
2. **Persistent diagnostics framework** (`diag`, `diag_environment`,
   `diag_dump_kmsg`, `diag_persist`, `fail_boot`, `block_by_partname`,
   `diag_raw_slot`). Records `/proc/version`, `/proc/cmdline`, the device-tree
   model/compatibility, the block-device map and `dmesg`, written to:
   - `<rootfs>/nuxel-boot-diag.log` (primary), and
   - the unused tail of the BOOT partition (mount-free, `dd`-readable).
   Rationale: S-Boot clears the Samsung log buffer on the *next* boot
   (`sec_debug_init_buffer: this is PIN RESET, clear all`) and ramoops has
   `console_size=0`, so a failed attempt otherwise leaves zero evidence.
3. **`rw` default for s10plus** (was: only if the cmdline contained `rw`, which
   never arrives). Fedora/systemd needs a writable root, and the diagnostic
   record is written there; an explicit `ro` on the cmdline still wins.
4. **No silent failure.** Every failure path now calls `fail_boot` (log + dmesg +
   persist + `sync`) before the `sleep`/`reboot -f`; the s10plus
   "USERDATA not found" path no longer hangs forever without evidence.
5. **Testability hooks**: `NUXEL_DT`, `NUXEL_BLOCK_SYS`, `NUXEL_DEV` default to
   the real kernel paths but can be pointed at a fixture by the regression test.
   `s10plus_userdata_device()` now uses the same hooks.
6. Header comment documents cmdline independence.

Deliberately **not** changed: the kernel (`Image.gz`, byte-identical), the merged
DTB (byte-identical; DTBO re-application proven idempotent), the load addresses,
the Fedora rootfs, the DTBO/`dtb` partitions, and the partition mapping.

## P2 — `boot/s10plus/tests/test-init-cmdline-independence.sh` (new)

Regression test, 8 assertions. It extracts `block_by_partname`,
`s10plus_userdata_device`, `diag_raw_slot` and the detection block **from the
shipped `init.sh`** and runs them against fixtures carrying the real handset
values (`Samsung BEYOND2LTE EUR OPEN 26 …`, `PARTNAME=userdata`,
`PARTNAME=boot`) with the exact S-Boot command line that was captured on device.
It fails if the fix regresses (e.g. foreign device trees must not be claimed).

## P3 — `boot/s10plus/build-debug-candidate.sh` (new)

Reproducible candidate builder: runs P2, then repacks the BOOT candidate with
`tools/s10plus/patch-boot-from-upload.py` (kernel + DTB preserved, only `/init`
replaced). Deterministic: two runs produced the identical SHA-256.

## Artifacts changed / created

| Path | Status |
|---|---|
| `boot/initramfs/init.sh` | modified (18,256 → ~24.7 KB) |
| `boot/s10plus/tests/test-init-cmdline-independence.sh` | new |
| `boot/s10plus/build-debug-candidate.sh` | new |
| `build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-diag-cmdline-free.img` | new candidate (BOOT only) |
| `build/out/s10plus/debug-candidates/SHA256SUMS.txt` | new manifest |
| `docs/s10plus-bootloop-repair/*` | new journal |
| `scripts/s10plus-debug-pack/captures/20261015T*` | new evidence captures (2 dirs) |

Originals preserved untouched: `build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img`
(`ceba64ab…`) and `build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img`
(`d4f8d632…`).

## Independent review of the patch (self-check)

- *Could auto-detection misfire on another device?* Only `BEYOND2LTE`/
  `beyond1lte`/`exynos9820` strings select s10plus; test T3 asserts a foreign DTB
  (`Google Mustang` / `google,gs501`) stays undetected. `mustang`, `vm` and
  `g7power` behaviour is unchanged (their case arms are untouched).
- *Is the root resolution still safe?* Yes: verified identity via the kernel's
  `PARTNAME=userdata` (present on this unit, D8 below), and the code still
  refuses to fall back to SYSTEM.
- *Can the diagnostics damage anything?* The rootfs write is a single new file.
  The BOOT-slack write lands at `(sectors−128)*512 = 57,606,144`, i.e. ≥ 33 MiB
  past the end of the 22.4 MB image, inside `boot`'s own free space — S-Boot only
  reads the lengths declared in the header.
- *Does the fix depend on the S-Boot cmdline at all?* No. If S-Boot ever *does*
  forward the header cmdline, `nuxel.device=s10plus`, `root=` and `rw` are still
  honoured (the explicit-root branch runs first) — the change is forward
  compatible.

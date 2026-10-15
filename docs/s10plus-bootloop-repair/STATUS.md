# S10+ bootloop repair — mission status

**Mission:** Cyber-Tiel autonomous bootloop repair (evidence-first).
**Started:** 2026-10-15 (UTC).
**Device:** SM-G975F beyond2lte, Exynos 9820, rev 26, bootloader G975FXXSEFUL1,
Android VB state orange, TWRP 3.7.0_9-2 (root ADB), currently in recovery.
**Agent:** Cyber-Tiel. **Writes to device:** none performed.

## Phase tracker

| Phase | Description | Status |
|---|---|---|
| 0 | Recon: packs, tools, ADB, journal | DONE |
| 1 | Capture real device evidence | DONE (2 capture dirs) |
| 2 | Identify failing boot stage | DONE — Stage C triggered by Stage A |
| 3 | Offline image/source audit | DONE |
| 4 | Root-cause repair / observability | **DONE** — `boot/initramfs/init.sh` patched |
| 5 | Build + offline verification | **DONE** — candidate built, 8/8 tests, preflight PASS |
| 6 | Hardware test prep (no flash) | **DONE** — NEXT-HARDWARE-TEST.md; awaiting user approval |

## Headline result

**Root cause (high confidence):** Nuxel passes device identity + root selection
**only** via the Android boot-image v1 header `cmdline` field
(`buildvariant=userdebug nuxel.device=s10plus root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw`).
Samsung S-Boot **discards that field** and writes its own command line into
`/chosen/bootargs`. The Nuxel initramfs therefore sees no `nuxel.device=`/`root=`,
takes the generic branch, cannot find a mountable root, and PID 1 fails then
`reboot -f` (or hangs until the Samsung softdog fires, `softdog.soft_margin=100`).
Both produce the observed Samsung-logo bootloop.

Key proof files: capture `20261015T063659Z-full-collection-5886/`
(`device/boot-properties.txt`, `kernel/cmdline.txt`, `previous-boot/last_kmsg.txt`,
`boot-image/INITRAMFS-init.txt`) plus mission capture
`20261015T063922Z-mission-cybertiel/device/{boot_hdr.bin,recovery_hdr.bin,uevent-partname.txt,chosen-bootargs.txt}`.

## Milestones

| # | Milestone | State |
|---|---|---|
| 1 | Boot failure localized | **ACHIEVED** (Stage A→C, evidence-backed) |
| 2 | Root cause corrected / observability restored | IN PROGRESS |
| 3 | Offline verification passed | PENDING |
| 4 | Linux kernel starts on hardware | NOT OBSERVED (no Nuxel kernel log available) |
| 5 | Fedora systemd starts | NOT OBSERVED |
| 6 | Nuxel interface displayed | NOT OBSERVED |

## Blockers / risks

- **No stock BOOT backup.** `backups/s10plus/boot-original.img` is a 57,671,680-byte
  zero-filled placeholder whose first 8 bytes are `DUMMY\0\0\0` — it is NOT a real
  BOOT dump. Stock Android can only be restored by flashing Odin firmware.
- TWRP recovery backup **is** valid (matches on-device `sda15`).
- Samsung persistent kernel log is wiped on PIN reset, so the failed Nuxel boot
  left no retrievable kernel log. New instrumentation writes diagnostics to
  USERDATA + BOOT slack so the next attempt yields real evidence.
- Stage E risk: TWRP's Samsung 4.14 kernel exposes **fbdev only**
  (`/dev/graphics/fb0`); there is no `/dev/dri`, no `/sys/class/drm`. Phosh/Phoc
  (Wayland/DRM) cannot run on this kernel unmodified.

## Deliverables produced

- `boot/initramfs/init.sh` — cmdline-independent device detection + persistent
  diagnostics (patch log: `PATCHES.md`).
- `boot/s10plus/tests/test-init-cmdline-independence.sh` — 8/8 passing.
- `boot/s10plus/build-debug-candidate.sh` — deterministic candidate builder.
- `build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-diag-cmdline-free.img`
  (22,433,792 B, sha256 `e99c1cbb…`) + `SHA256SUMS.txt`.
- Evidence: `scripts/s10plus-debug-pack/captures/20261015T063659Z-full-collection-5886/`
  and `…/20261015T063922Z-mission-cybertiel/`.
- Journal: DEVICE-EVIDENCE.md, BOOT-FAILURE-ANALYSIS.md, HYPOTHESES.md,
  PATCHES.md, TEST-RESULTS.md, NEXT-HARDWARE-TEST.md, RAW-LOG-INDEX.md.

## Next action (needs user approval)

Flash **BOOT only** (`/dev/block/sda14`) with the diagnostic candidate and read
back `/nuxel-boot-diag.log` from USERDATA — full procedure, observations and
rollback in NEXT-HARDWARE-TEST.md. **Nothing has been flashed; the phone is
untouched and still in TWRP.**

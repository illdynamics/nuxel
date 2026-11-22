# Camera Prompt 00_8 — REAL golden no-op qualification (2026-11-22)

**Verdict: BLOCKED. NO signed real golden no-op possible. READY_FOR_PROMPT_02=NO.**

This run established a fresh, live, read-only baseline and executed the offline
regression suites. The two offline compatibility fixes in the revised tools were
reviewed and are present and fail-closed. However, the owner-trusted signing key,
the signed Prompt00 artifact manifest, and the complete off-device BOOT/DTB/DTBO/
RECOVERY readback backups are **not present** on this host, so the real signed
golden no-op (Phase 3) cannot be executed and is BLOCKED.

## Verified live evidence (read-only SSH, zero writes)

| Field | Value | Source |
|---|---|---|
| Device reachable | YES | SSH root@10.11.12.99 |
| Healthy / normally booted | YES | `up 1 day, 30 min` |
| Kernel | `4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT ... 2026` | `/proc/version` |
| Live FDT SHA-256 | `761df64ac4417f6dd5bbb468eeb6dc2305cbf45f8541d3639d5a50ca2ffc7cad` | `sha256sum /sys/firmware/fdt` (372657 bytes) |
| Board revision | `26` | `androidboot.revision=26` in `/proc/cmdline` |
| DTBO selection index | `9` | `androidboot.dtbo_idx=9` in `/proc/cmdline` |
| Model | `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820` | `/sys/firmware/devicetree/base/model` |
| Product | `SM-G975F` | `androidboot.em.model=SM-G975F` |
| bootloader | `G975FXXSEFUL1` | `androidboot.bootloader=...` |
| Camera STREAMON | NONE observed | dmesg shows only watchdog keepalive |
| pstore | `dmesg-ramoops-0.enc.z` (Samsung-encrypted, 5152 bytes) | `/sys/fs/pstore/` |

The full live FDT hash matches the `761df64a` prefix recorded in the Prompt 00_7
operator summary. This is a full SHA-256, independent of any report claim.

## Offline regression results (Phase 1)

- `bash tools/s10plus/tests/test-camera-dt-gate.sh` → **exit 0, 51/51 PASS**
  (self-contained synthetic fixtures; explicitly labels live Prompt00 = NOT VERIFIED).
- `bash boot/s10plus/tests/test-boot-image-gates.sh` → **exit 3 = SKIP-PREREQ**
  (gitignored historical A5/A25 build artefacts absent; correctly NOT a pass, NOT a regression).

The revised `camera-dt-gate.py` `--golden-merged`/`--golden-merged-sha256` exception
and the `verify-boot-image.py` separate-DTB/DTBO evidence mode are present and
fail-closed. The GPIO exception is hash-pinned, not a pin waiver (confirmed by source
review and negative fixtures test_45–test_48).

## Why the real golden no-op is BLOCKED (exact missing evidence)

1. **No private off-device BOOT/DTB/DTBO/RECOVERY images.** The only current-date
   host artifacts are `pwn/recovery-artifacts/current/config-20261122.gz` and
   `dmesg-ramoops-0-20261122.enc.z`. No `current-boot.img`, `current-dtb.img`,
   `current-dtbo.img`, `active-merged.fdt`, or recovery image with matching
   readback hashes exist anywhere on this host (`/PRIVATE` is the macOS system
   directory containing only `etc/tmp/var/tftpboot`; no dedicated evidence dir).
2. **No owner-approved trust anchor / signing key.** The only `.pem` in the tree is
   `services/nuxel-penguru/keys/owner-release-public.pem` (an Ed25519 public key for
   the unrelated penguru service). There is no matching private signing key, no
   camera-audit trust anchor, and no owner approval recorded for this purpose.
   Self-generating a key and calling it "trusted" is prohibited.
3. **No signed Prompt00 artifact manifest.** `camera-00-artifact-manifest.NOT_SIGNED.template.json`
   is a template with all placeholders (null/0/UNVERIFIED) and no signature.
4. **Partition name → sdaN mapping not independently established.** The device runs
   native Fedora on `/dev/sda31` and has **no** `/dev/block/by-name` symlinks.
   BOOT/DTB/DTBO/RECOVERY by-name → block-device mapping is unproven in this run;
   the prior report's mapping could not be independently reproduced from live evidence.
5. **TWRP rollback not verified as current.** `evidence/live-20261114/twrp-config.txt`
   is dated 2026-11-14 (pre-incident) and is not evidence of a current working
   TWRP restore path for the exact present partition layout.

## Declaration (mandatory)

- DEVICE_REACHED = YES
- CURRENT_NUXEL_HEALTHY = YES
- LIVE_FDT_HASH_MATCH = YES (`761df64a...` full hash verified versus `/sys/firmware/fdt`)
- PARTITION_BACKUPS_MATCH = UNVERIFIED (complete off-device readback set absent)
- BOARD_REV = 26
- DTBO_INDEX = 9
- BOOT_DT_LAYOUT = REPORTED `separate-dtb-dtbo` (NOT independently re-verified end-to-end; appended-BOOT absent is unproven without current BOOT image)
- OWNER_SIGNING_TRUST = BLOCKED (no owner-approved key available)
- ROLLBACK_READY = UNKNOWN (not demonstrated for current layout)
- REAL_GOLDEN_NOOP = BLOCKED (required signed manifest + private images + trusted key absent)
- NEGATIVE_GATE_TESTS = 51/51 synthetic PASS; live negative cases not run (no baseline images)
- DEVICE_WRITES = ZERO
- DEVICE_REBOOTS = ZERO
- PROMPT00_PASS = NO (full off-device backup + recovery proof not verified)
- PROMPT01_PASS = NO (real signed golden no-op could not run)
- READY_FOR_PROMPT_02 = NO

## Smallest safe next steps (read-only)

1. Owner supplies/approves a camera-audit signing key (public fingerprint recorded
   out-of-band), or approves a documented NEW trust-anchor creation procedure.
2. Complete off-device readback of current BOOT/DTB/DTBO/RECOVERY with two
   independent SHA-256 checks and the by-name→sdaN partition map, into a true
   private directory outside Git.
3. Confirm the live separate-DTB/DTBO layout and selected overlay from a current
   BOOT image (which is what makes `appended_dtb_index=null` provable).
4. Re-run the same negative matrix against real (not synthetic) captured images.

No on-device write, reboot, STREAMON, or TWRP entry was performed.

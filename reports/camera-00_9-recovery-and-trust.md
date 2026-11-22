# Camera Prompt 00_9 — Recovery readiness and owner trust (2026-11-22)

**Verdict: OWNER_SIGNING_TRUST = BLOCKED; ROLLBACK_READY = UNKNOWN.**
**No on-device writes. No reboots. No TWRP entry.**

## Owner signing identity — BLOCKED (awaiting owner action)

The owner has **NOT** authorized a camera trust anchor for this workflow. The
prompt requires one of two owner actions before any manifest can be signed:

- **Option A:** owner supplies a pre-existing dedicated public verification
  key + fingerprint and identifies the authorized private key.
- **Option B:** owner expressly approves creating a NEW dedicated local
  EC P-256 trust anchor via `scripts/owner_init_camera_trust.sh`.

Neither has occurred in this (unattended) run. I will not self-generate a key
and call it "trusted", reuse the unrelated `penguru-service` Ed25519 key, or
fabricate an approval. The `owner_init_camera_trust.sh` and
`owner_sign_camera_manifest.sh` scripts were source-reviewed: both correctly
require interactive owner confirmation (`CREATE_CAMERA_TRUST`,
`SIGN_CAMERA_MANIFEST`), refuse template manifests, enforce absolute non-Git
paths, `umask 077`, and 0600/0700 perms. They do not upload private material.

## TWRP / Download Mode rollback readiness — UNKNOWN (requires permissioned check)

Historically-proven evidence (NOT re-booted in this session):

- `boot -> /dev/block/sda14` (57,671,680 B) matches the live `blkid` map exactly.
- `recovery -> /dev/block/sda15`, `dtb=sda12`, `dtbo=sda13`, `userdata=sda31`,
  `system=sda25` all match live `blkid` (see partition-map report).
- Multiple dated TWRP sessions and boot-repair receipts exist in
  `docs/s10plus-autonomous-boot-repair/` (FLASH-ATTEMPTS.md, A27-BOOT-FLASH-RECEIPT.md),
  with `03-flash.sh --boot-only`, `05-preflight.sh --profile s10plus --boot-only`,
  and `dd of=/dev/block/sda14` write path proven working historically.
- The S10+ is A-only; no fastboot use. Restore target = BOOT (`sda14`) only for
  camera candidate; DTB/DTBO writes require a separate explicit owner go-ahead.

What is **NOT** established in this session: that the TWRP path works for the
*exact present* partition layout and current bootloader, without actually
rebooting to TWRP. The prior evidence is dated 2026-11-14 (pre-incident) and is
credible but not a current-layout reverification.

**Consequence:** `ROLLBACK_READY = UNKNOWN` (not FALSE, not faked-TRUE). A real
rollback proof requires either (a) credible current-layout TWRP session evidence
or supervised owner confirmation, or (b) a **separate, explicitly permissioned,
read-only TWRP access check** in a future session *after* the verified backups
(the backups ARE captured; see partition-map report). That access check must NOT
be silently executed within this no-reboot stage.

## Known-good restore procedure (documented only; NOT executed)

Recovery host holds (private, off-Git, hash-verified):
`current-boot.img`, `current-dtb.img`, `current-dtbo.img`, `current-recovery.img`,
`active-merged.fdt`, plus `raw-capture.NOT_SIGNED.json` with source/host SHAs.

Restore (owner-only, future, after permission, when actually needed):
1. Enter TWRP/Download Mode via the owner-approved key combo / `adb reboot recovery`.
2. Verify ADB sees TWRP (`adb devices`, expected `recovery` state).
3. Verify target: `boot -> /dev/block/sda14` (57,671,680 B) via TWRP shell.
4. Preflight: confirm `current-boot.img` SHA = `0e6aa34c...` (private dir).
5. Restore BOOT only: `adb shell dd if=/dev/block/sda14 of=/sdcard/preflash-boot.img`
   (optional extra safety copy), then `adb push current-boot.img /tmp/` and
   `adb shell dd if=/tmp/current-boot.img of=/dev/block/sda14` (boot only).
6. Post-restore readback + SHA compare, then reboot and confirm Nuxel boots
   (kernel `4.14.253-gf7194c1d15ed-dirty`, SSH reachable, `/sys/firmware/fdt`
   SHA = `761df64a...`).

This procedure is NOT run and does NOT grant flash approval. DTB/DTBO restore
(only if a future camera candidate changes them) requires its own separate
owner go-ahead per the Master Contract.

## Declaration

- OWNER_SIGNING_TRUST = BLOCKED (no owner-approved key; not self-generated)
- MANIFEST_SIGNED_AND_VERIFIED = NO (depends on above)
- ROLLBACK_READY = UNKNOWN (credible historical TWRP, but not current-layout reverified)
- DEVICE_PARTITION_WRITES = 0
- DEVICE_REBOOTS = 0

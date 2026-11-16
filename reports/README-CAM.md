# Nuxel Camera Pwnage Pack — S10+ Exynos 9820

This pack contains the full camera mission prompt, the short agent kickstarter, a read-only vendor asset acquisition helper, and selected repository evidence/source snapshots from the uploaded `nuxel-main (5).zip`.

## Contents

- `full-pwnage-cam.md` — detailed implementation, flashing, boot-repair, SSH, permission, portal, app-interoperability and physical acceptance specification.
- `pwnage-cam.md` — short prompt to launch the agent; it instructs the agent to read the full specification.
- `scripts/acquire-s10plus-camera-assets.py` — read-only ADB inventory/acquisition helper for camera files from already-mounted stock vendor/system/odm filesystem directories.
- `reference/REPOSITORY-FINDINGS.md` — analysis of current code/evidence and exact issues found.
- `reference/` — selected copies of the camera report, reflash plan, camera policy, permissions, bridge/API, app, portal, kernel/flash helpers and camera tests to help the agent orient quickly.

## Firmware status — no binary blobs fabricated or included

The uploaded repository does **not** contain a usable OEM Samsung S10+ camera firmware bundle. The tiny `camera-ready` test fixture `s5k2l4_setfile.bin` is only 3 bytes and is explicitly placeholder data. It is not camera firmware.

This pack intentionally does not invent, substitute, download, patch or re-sign Samsung ISP firmware, sensor setfiles, camera tuning/calibration or HAL binaries. The full prompt explains how to acquire legitimate exact-target files from the owner's own matching stock vendor/system files and how to verify their provenance, ABI and hashes. If the required exact Samsung files are unavailable, the agent must identify the missing input rather than claim success.

## Read-only acquisition helper

Run this from the repository root while the exact S10+ is connected in TWRP over ADB:

```sh
python3 scripts/acquire-s10plus-camera-assets.py --output ./camera-acquisition
```

That first command is inventory-only. To copy matched ordinary files to the host after reviewing the manifest:

```sh
python3 scripts/acquire-s10plus-camera-assets.py --pull --output ./camera-acquisition
```

Optional owner-authorized vendor calibration filenames:

```sh
python3 scripts/acquire-s10plus-camera-assets.py --pull --include-vendor-calibration --output ./camera-acquisition
```

The helper does not mount partitions, flash, reboot, run `dd`, or write to the handset. It searches only hard-coded vendor/system/odm filesystem roots and excludes `/data`, `/efs`, `/persist`, RPMB, raw EEPROM, TEE memory, keystore material and user biometric/media data. If the vendor filesystem is not already mounted, the helper reports that; it does not mount it.

## Critical task-specific points

- Start with TWRP connected over USB as directed by the owner.
- Build from the exact pinned 4.14.253 kernel source, not a random kernel.
- Use the existing boot-candidate and flash scripts only after the actual partition map and backup are verified.
- The TWRP flash helper's `--rootfs` default is `userdata`; do not overwrite it blindly.
- The reflash plan's A/B wording must be checked against the actual S10+ partition layout.
- Returning to TWRP automatically after reboot means Nuxel failed to boot; debug and repair rather than reporting success.
- Once Nuxel has booted, connect to `root@192.168.178.167` with `~wicked/.ssh/wicked_wqn_id_rsa` and keep private-key contents secret.
- The owner wants the native Camera app open with a real live frame visible, and ZapZap/Ferdium compatibility tested through the standard portal where those apps support it.
- The existing `camera` permission already exists in the canonical registry/UI; complete its real enforcement rather than duplicating it.

## Source snapshot note

The `reference/` files are copies from the uploaded archive dated 2026-11-10. They are for context only. The active Nuxel checkout and live device state are authoritative. Do not overwrite newer files with these snapshots.


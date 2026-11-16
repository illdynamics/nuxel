# PWNAGE-SSP — Final boot image manifest

| Field | Value |
|---|---|
| Image | `build/out/s10plus/ssp/images/boot-ssp-v14.img` |
| SHA256 | `7ad5183acbfeb88c0f2232c5ebbcaaa3c087039a04be51f94bb5417b27505e2a` |
| Size | 57 671 680 bytes (exact boot partition size) |
| Kernel | `4.14.253-gf7194c1d15ed-dirty`, build **#48**, 45 783 688 B |
| Kernel SHA256 | `f6b5830a825ba3ecb2673a7b5c1e6b6682bc3a53b0c21587f9fd80d42826e643` |
| Ramdisk | unchanged LZMA-alone copy of the donor, `0dd0fb5a…b290f407` |
| DTB/hash tail | unchanged, `043b20bf…c49f43d865` (`sec-nfc@27` intact) |
| Target partition | `/dev/block/by-name/boot` → `/dev/block/sda14` (only) |
| Gate | `tools/s10plus/verify-boot-image.py` → PASS |
| Kernel config gate | PASS (capability parity) |
| userns gate | PASS (incl. reachable-chroot refinement) |
| Live on device | yes — flashed and booted, then verified over SSH |
| Rollback | `backups/boot/boot-orig-20261113.img` `7ca7cc70…20359abf8` |

## Kernel patches in this image

| Patch | Purpose |
|---|---|
| `0013-nuxel-sensorhub-bringup-native-bbd.patch` | native bring-up, BBD peer transport, power-cycle retry, diagnostics |
| `0014-nuxel-ucount-inc-user-namespaces-fix.patch` | `inc_ucount()` uninitialised pointer + diagnostics |
| `0016-nuxel-chroot-false-positive-userns.patch` | `current_chrooted()` accepts a chroot inside the mount namespace (Nuxel PID1 layout) |
| `0008-nuxel-userns-flatpak.patch` | unprivileged-userns opt-in sysctl (extended with diagnostics) |

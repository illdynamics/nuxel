# firmware/s10plus/blobs/

Raw firmware pulled from a physical Samsung Galaxy S10+ (beyond2lte) that is
already in TWRP. **Nothing in this directory is committed except this README
and `.gitkeep`** — the actual blobs are device-proprietary and stay untracked.

## Layout (created by `install-firmware.sh --twrp-pull`)

```
blobs/
  vendor-firmware/      <- adb pull /vendor/firmware
  vendor-modules/       <- adb pull /vendor/lib/modules
  vendor-etc-firmware/  <- adb pull /vendor/etc/firmware
  system-lib64/         <- adb pull /system/lib64
```

## How to fill this directory (Phase 0)

1. Boot the S10+ into TWRP (Vol Up + Bixby + Power) and connect USB.
2. Run:  NUXEL_DEVICE=s10plus firmware/s10plus/install-firmware.sh --twrp-pull
   (identity-checks ro.product.device == beyond2lte and ro.product.name
   matches beyond2ltexx before pulling anything).
3. Run:  NUXEL_DEVICE=s10plus firmware/s10plus/install-firmware.sh --checksums
   and paste the resulting sha256 values into the `checksum` fields of
   firmware/s10plus/manifest.yml, replacing the UNKNOWN placeholders.
4. Never fabricate a checksum, filename, or driver status. Anything not yet
   collected from the device stays UNKNOWN/TBD.

## Safety

- No partition is ever written by any script in this tree. Acquisition is
  read-only (adb pull).
- Never flash the modem CP from here — modem bring-up is Phase 7, and the
  CP belongs to the modem partition, not to /lib/firmware.
- Never touch efs / efsg / persist / param / up_param / steady / keystorage /
  carrier / cp_debug / misc on the device.

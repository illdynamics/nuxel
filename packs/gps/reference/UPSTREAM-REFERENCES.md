# External research references

These are engineering references used to identify the Android vendor package shape. They are not redistributable firmware payloads and do not authenticate an extracted patch.

1. **Evolution-X `vendor_samsung_beyond2lte` vendor recipe** (exact target family):
   https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk
   It lists `gps.xml`, GPS init RC files, `lhd.conf`, and package names `gps.default`, `vendor.samsung.hardware.gnss@2.0-impl`, `libwrappergps`, `gpsd`, `lhd`, and `vendor.samsung.hardware.gnss@2.0-service`.
2. **LineageOS `android_device_samsung_beyond2lte` proprietary firmware manifest**:
   https://github.com/LineageOS/android_device_samsung_beyond2lte/blob/lineage-23.2/proprietary-firmware.txt
   For `SM-G975F`, it enumerates boot/modem-related firmware partitions for package `G975FXXSGHWC2`; it does not list a Broadcom sensor-hub patch. This is not proof that no patch exists in a stock system/vendor image, only that this particular manifest does not identify one.
3. **S10-family GNSS proprietary file list** (adjacent S10 family target, not exact SM-G975F proof):
   https://github.com/whatawurst/android_device_samsung_beyond1lte/blob/lineage-17.1/proprietary-files-vendor.txt
   Shows typical GNSS file names and paths (`lhd`, `gpsd`, Samsung GNSS service, configs, HALs, wrapper); use for candidate discovery only, not as a replacement for beyond2lte extraction.

The Nuxel-specific evidence is in `../repo-evidence/` and must take precedence over assumptions from other device families.

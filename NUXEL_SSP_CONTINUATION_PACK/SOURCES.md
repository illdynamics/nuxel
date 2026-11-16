# Public upstream reference starting points

- Android Bionic (official platform source, ELF loader): https://android.googlesource.com/platform/bionic/
- Android Bionic linker documentation (`DT_INTERP` and `/system/bin/linker64`): https://android.googlesource.com/platform/bionic/+/HEAD/README.md
- Android VNDK linker namespaces: https://source.android.com/docs/core/architecture/images/VNDK.pdf
- Device-matching Samsung Galaxy S10+ beyond2lte vendor metadata: https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk
- Device-matching published lhd.conf: https://raw.githubusercontent.com/Evolution-X-Devices/vendor_samsung_beyond2lte/bka/proprietary/vendor/etc/sensor/lhd.conf

These references are for technical comparison and documentation. Never infer binary ABI compatibility or redistribution rights from a public index. Match runtime to the exact device build before staging or execution. Do not substitute Pixel BCM47765 firmware for Samsung BCM47752.

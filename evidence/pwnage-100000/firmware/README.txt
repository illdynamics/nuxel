Firmware findings for the USB-C -> DP/HDMI path.
No firmware file is requested by the exynos-displayport, decon_t, max77705
CCIC or ION code paths exercised by this fix.  The DP link training and DPCD
reads succeeded with the firmware already present on the device.  No firmware
change, substitution or reflash is required.

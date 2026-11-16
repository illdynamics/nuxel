# Public technical references

- `beyond2lte-vendor.mk` for Samsung Galaxy S10+ lists the `vendor/etc/sensor/lhd.conf` config, sensor hub HAL package (`sensors.sensorhub`), and `lhd` binary: https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk
- The corresponding `lhd.conf` from the same public vendor tree sets `LhePatch=/dev/bbd_patch`, `LheBbdPacket=/dev/ttyBCM`, `LheBbdControl=/dev/bbd_control`, `LheBbdSensor=/dev/bbd_sensor`, and the sensor-hub power sysfs path: https://raw.githubusercontent.com/Evolution-X-Devices/vendor_samsung_beyond2lte/bka/proprietary/vendor/etc/sensor/lhd.conf
- The Broadcom BCM4775x brief lists BCM47752KUB1G as a member of the BCM4775x family: https://www.gpsrchive.com/Shared/GNSS%20Chipset/BCM4775x/BCM4775x.pdf
- Android's Google GS101 package shows a separate `SensorHub.patch` plus `lhd` for its BCM47765 GNSS stack; that is a different platform and must not be transplanted to BCM47752 without proof: https://android.googlesource.com/device/google/gs101/%2B/cf110374275ec64dd647b4a2c1477cdd824f2b2c/gnss/device-gnss.mk

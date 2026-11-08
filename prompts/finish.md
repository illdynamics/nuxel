## Exact next steps once the phone shows up

```bash
adb devices          # expect recovery / device
adb push /tmp/nuxel-boot.img /tmp/
adb push /tmp/up_param_new.bin /tmp/
adb push /tmp/nuxel-rootfs-patch.tar /tmp/
adb push /tmp/apply-in-twrp.sh /tmp/
adb shell sh /tmp/apply-in-twrp.sh
adb reboot
# wait for Nuxel, then:
adb push /tmp/nuxel-postboot-fixes.sh /tmp/
adb shell sh /tmp/nuxel-postboot-fixes.sh
```

**Please reconnect the S10+ with a USB data cable and confirm TWRP is on the Install/main screen.** Then tell me it’s reconnected (or just say “go”) and I’ll run the
 flash, boot, and the Bluetooth/Audio/GPS fixes end to end.


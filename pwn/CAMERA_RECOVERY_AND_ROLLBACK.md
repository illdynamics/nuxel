# NUXEL S10+ Camera — Recovery and Rollback (UPDATED 2026-11-20, Session 7)

**Target:** SM-G975F beyond2lte, Exynos9820, 4.14.253

## CURRENT STATE (2026-11-20, ~20:30 CET) — DEVICE UNREACHABLE, REQUIRES PHYSICAL RECOVERY

The device is currently in a hard boot-loop/hang state after flashing a 3-partition
camera bring-up (base DTB replaced with full board+camera merge + no-op dtbo +
correct-config camera kernel). After reboot the device did NOT enter TWRP or
Nuxel and does NOT enumerate on USB/adb (empty `adb devices`, empty
`system_profiler SPUSBDataType` for ~13 minutes of polling).

### Immediate recovery (requires human physical action):
1. **Hard power-cycle**: hold Volume-Down + Power for ~10 seconds until the
   device force-reboots (or long-press Power 15s if the screen is black).
2. When it reaches TWRP (hold Volume-Up + Bixby/Power on the S10+ during boot,
   or let it settle into the existing recovery), reconnect USB and confirm
   `adb devices` shows `R58M75KDB2X recovery`.
3. Restore the three known-good partitions (images are on this Mac AND on the
   device's Nuxel rootfs sda31 at /root/kbuild/flash/ + /root/camwork):

   From a TWRP root adb shell (mkdir -p /nuxel; mount -o rw /dev/block/sda31 /nuxel):
   ```
   dd if=/nuxel/root/kbuild/flash/boot-before.img of=/dev/block/sda14 bs=1M
   # OR push from this Mac (verified SHA-256 below):
   #   adb push backup/boot-before.img /sdcard/ ; adb shell dd if=/sdcard/boot-before.img of=/dev/block/sda14 bs=1M
   #   adb push dtb-sda12.img /sdcard/  ; adb shell dd if=/sdcard/dtb-sda12.img of=/dev/block/sda12 bs=1M
   #   adb push dtbo-before.img /sdcard/ ; adb shell dd if=/sdcard/dtbo-before.img of=/dev/block/sda13 bs=1M
   sync; reboot
   ```
4. Confirm Nuxel boots: `ssh root@10.11.12.99 "uname -a"` → 4.14.253-gf7194c1d15ed-dirty #3.

### Known-good backup SHA-256 (on macOS, /tmp/camwork/):
- boot-before.img   (57,671,680 B)  sha256 79e4d5e35527e5dfc56f1a141c7c89f64fe683b87ed3821498e83fb77d607c73
- dtb-sda12.img     (8,388,608 B)   sha256 cbec1ecac4da2296e1deb0565cfd6a787dfa1f9880dc405b6504d009bef9da13
- dtbo-before.img   (8,388,608 B)   (backup/dtbo-before.img)

## WHAT WENT WRONG (root cause of the current hang — most probable)

Session 7 flashed triple partition set:
- sda12 (dtb)  = fully-merged board+camera DTB (382,239 B valid FDT, 1 entry)
- sda13 (dtbo) = 10-entry, entry[9] replaced with 207-byte NO-OP overlay
- sda14 (boot) = correct-config camera kernel (ABOX+NFC patches applied, verified)

The most probable failure is the **base-DTB replacement** (sda12): the Samsung
bootloader may not accept a non-stock base DTB (size/chksum/format/version guard),
OR the 207-byte no-op dtbo entry looped its overlay parser. The kernel BOOT image
itself was verified good earlier (same-size raw Image, camera+media framework
built, ABOX/NFC vendor crashes fixed by patches 0004/0007).

## Session 7 achievements (preserved, NOT lost)
- DTBO structural bug FIXED (CSIS/hold/clock nodes were top-level -> dropped;
  now wrapped in fragment@100 target-path="/").
- Vendor FIMC-IS2 coexistence solved (status=disabled on fimc_is + 6 sensor nodes).
- Merged overlay built + verified (all 8 endpoint links bidirectional, all 4
  CSIS + 4 sensor compatibles present).
- Root cause of prior kernel crashes found: MISSING Nuxel patches (0004 abox
  boot-done, 0007 sec-nfc class-name, + 20 others). Applied all patches; the
  correct-config kernel with patches BUILT SUCCESSFULLY (Image 45,848,584 B,
  5 camera .ko modules).
- Full recovery/rollback images preserved on-device + macOS.

## NEXT (once device is back in TWRP)
Restore the 3 known-good partitions above; verify stable boot FIRST.
Then investigate the bootloader DTB acceptance separately — do NOT re-flash a
replaced sda12 without first confirming how this bootloader validates the DTB
partition (chksum/size/version) against a known working DTB.

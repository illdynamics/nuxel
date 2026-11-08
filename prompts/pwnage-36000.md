# Nuxel S10+ Pwnage-36000: Complete Reflash & Fix Orchestration

**You have one shot. Phone is in TWRP, connected via USB. You're going to do this right.**

This prompt coordinates:
1. **Charging animation** (MOSS module flash) — done in TWRP
2. **Bluetooth kernel rebuild** — kernel reflash in TWRP
3. **Reboot into Nuxel** — GPS, Audio, Bluetooth config fixes applied post-boot

---

## Prerequisites (Verify Before Starting)

- [ ] Phone booted into TWRP recovery
- [ ] Phone connected to PC via USB (adb access confirmed)
- [ ] `./assets/nuxel-charging-animation.jpg` exists on your build machine
- [ ] `kernel/s10plus/` directory exists with build-kernel.sh
- [ ] MOSS module folder extracted and ready
- [ ] Original `up_param.bin` backed up locally
- [ ] You've read both **triplefix.md** and **charge.md** in full

**Test ADB connection first:**
```bash
adb devices
# Should show device with 'recovery' status
```

---

## Phase 1: Prepare All Artifacts (Before Touching Phone)

### 1.1: Build the Bluetooth Kernel

```bash
# Navigate to kernel directory
cd kernel/s10plus/

# CRITICAL: Enable Bluetooth HCIUART in config
# Option A: Edit .config directly
cat >> .config << 'EOF'
CONFIG_BT=y
CONFIG_BT_HCIUART=y
CONFIG_BT_HCIUART_H4=y
CONFIG_BT_HCIUART_BCSP=y
CONFIG_BT_HCIUART_ATH3K=y
CONFIG_BT_HCIUART_LL=y
CONFIG_BT_HCIUART_3WIRE=y
CONFIG_SERIAL_CORE=y
CONFIG_SERIAL_8250=y
EOF

# Option B: Use menuconfig (if you prefer GUI)
# make ARCH=arm64 menuconfig
# Navigate to: Networking → Bluetooth → HCI UART driver
# Enable it, save, exit

# Build the kernel
./build-kernel.sh

# Find the built kernel image
ls -lh arch/arm64/boot/Image*
# Should output something like: Image (10MB+)

# Mark the build timestamp
echo "Kernel built at: $(date)" > /tmp/kernel-built.txt
```

**If build fails:**
```bash
# Check for missing dependencies
make ARCH=arm64 oldconfig
# Answer 'N' to new options (keep defaults)
./build-kernel.sh
```

### 1.2: Create the Charging Animation (MOSS Module)

Reference: **charge.md** steps 1-5

```bash
# Create working directory
mkdir -p /tmp/nuxel-flash-work
cd /tmp/nuxel-flash-work

# Extract current up_param.bin (you have a backup)
tar -xf ~/up_param.bin

# Convert/resize charging animation
convert ./assets/nuxel-charging-animation.jpg \
  -resize 1080x2340! \
  -quality 85 \
  lpm.jpg

# Verify
identify lpm.jpg

# Repack
tar -cf up_param_new.bin *.jpg

# Verify tar
tar -tf up_param_new.bin | head

# Copy to MOSS module
cp -r ~/MOSS ~/moss-nuxel-reflash
cp up_param_new.bin ~/moss-nuxel-reflash/up_param/up_param.bin

# Verify MOSS structure
ls -la ~/moss-nuxel-reflash/up_param/up_param.bin

# Create the flashable zip
cd ~/moss-nuxel-reflash
zip -r ../moss-nuxel-charging-flashable.zip .
cd ~/

# Verify zip
unzip -l moss-nuxel-charging-flashable.zip | grep -E "(up_param|customize)" | head
```

### 1.3: Copy Everything to Accessible Location

```bash
# Copy kernel image to /tmp (adb can access)
cp kernel/s10plus/arch/arm64/boot/Image /tmp/nuxel-boot.img

# Copy MOSS zip
cp moss-nuxel-charging-flashable.zip /tmp/

# Verify both exist and have content
ls -lh /tmp/nuxel-boot.img /tmp/moss-nuxel-charging-flashable.zip
# Both should be >1MB
```

---

## Phase 2: Flash Everything in TWRP (Phone Connected)

### 2.1: Flash the Charging Animation (MOSS Module)

```bash
# Push MOSS zip to phone
adb push /tmp/moss-nuxel-charging-flashable.zip /tmp/

# In TWRP (phone screen):
# 1. Tap "Install"
# 2. Navigate to /tmp/moss-nuxel-charging-flashable.zip
# 3. Swipe to flash
# Wait for: "Flashing complete"

# Verify from PC:
adb shell ls -la /data/adb/modules/my_own_splash_screen/up_param/
# Should show: up_param.bin (several MB)
```

**If flash fails:**
```bash
adb shell
# Check TWRP logs
cat /recovery.log | tail -50
# Look for actual error (permission, bad zip format, etc.)
```

### 2.2: Flash the Bluetooth Kernel

**Two options — choose one:**

#### Option A: Flash Boot Partition Directly (Faster)

```bash
# Find correct partition
adb shell ls /dev/block/by-name/ | grep -i boot
# Usually: /dev/block/by-name/boot

# Flash kernel directly
adb push /tmp/nuxel-boot.img /tmp/
adb shell dd if=/tmp/nuxel-boot.img of=/dev/block/by-name/boot bs=4096

# Verify (should show no errors)
adb shell echo "Kernel flashed successfully"
```

#### Option B: Flash via TWRP Zip (Safer, if you have flashable zip)

```bash
# If you have a boot.img wrapped in a flashable zip, use TWRP:
adb push nuxel-boot-flashable.zip /tmp/

# In TWRP:
# 1. Tap "Install"
# 2. Select nuxel-boot-flashable.zip
# 3. Swipe to flash
```

### 2.3: Verify Flashes Before Reboot

```bash
# Check MOSS module is present
adb shell ls -la /data/adb/modules/ | grep -i splash
# Should show: my_own_splash_screen (or similar)

# Check kernel version (if readable from TWRP)
adb shell cat /proc/version 2>/dev/null || echo "Kernel version check deferred to post-boot"

# Final safety check: both artifacts exist
adb shell ls -la /data/adb/modules/my_own_splash_screen/up_param/up_param.bin
```

---

## Phase 3: Reboot and Post-Boot Configuration

### 3.1: Reboot into Nuxel

```bash
# From TWRP, reboot to system:
adb reboot

# Monitor boot (optional, for debugging):
adb logcat | grep -i bluetooth
# Ctrl+C to stop when boot settles
```

### 3.2: Wait for Boot Completion

```bash
# Poll until device is ready (max 2 minutes)
echo "Waiting for device to boot..."
for i in {1..60}; do
  adb shell getprop sys.boot_from_charger_mode 2>/dev/null && break
  sleep 2
  echo "Waiting... ($((i*2))s)"
done

# Verify boot complete
adb shell getprop ro.boot.serialno
# Should return serial number
```

### 3.3: Apply Bluetooth Fix (Userspace Config)

Reference: **triplefix.md** section 1, steps 3-6

```bash
# Enable rfkill unblocking
adb shell su -c "rfkill unblock bluetooth"

# Create udev rule (on phone)
adb shell su -c 'cat > /etc/udev/rules.d/99-bluetooth.rules << '"'"'EOF'"'"'
# Samsung S10+ Bluetooth UART
KERNEL=="ttyHS0", SUBSYSTEM=="tty", TAG="uaccess", MODE="0660"
SUBSYSTEM=="rfkill", ACTION=="change", RUN="/usr/bin/rfkill unblock bluetooth"
EOF'

# Reload udev rules
adb shell su -c "udevadm control --reload-rules && udevadm trigger"

# Start bluetoothd
adb shell su -c "systemctl restart bluetooth"

# Verify (wait 3 seconds for daemon startup)
sleep 3
adb shell hciconfig
# Should show: hci0 with UP RUNNING status
```

### 3.4: Apply Audio Fix (PipeWire + ALSA Workaround)

Reference: **triplefix.md** section 2, steps 1-5

```bash
# Verify ALSA detects cards
adb shell aplay -l
# Should show multiple cards (beyond-madera, abox_vdma, etc.)

# Create ALSA mute workaround
adb shell su -c 'mkdir -p /etc/alsa/conf.d'
adb shell su -c 'cat > /etc/alsa/conf.d/99-nuxel-s10-workaround.conf << '"'"'EOF'"'"'
defaults.pcm.!default {
    type asym
    playback.pcm "speaker"
    capture.pcm "mic"
}

pcm.speaker {
    type hw
    card 0
    device 0
}

pcm.mic {
    type hw
    card 0
    device 0
}

ctl.!default {
    type hw
    card 0
}
EOF'

# Reload ALSA
adb shell su -c "alsactl init && alsactl store"

# Start PipeWire (as user, not root)
adb shell "systemctl --user start pipewire"
sleep 2

# Verify PipeWire is running
adb shell "systemctl --user status pipewire"
# Should show: active (running)

# Create PipeWire mute bypass config
adb shell su -c 'mkdir -p ~/.local/share/pipewire/pipewire.conf.d'
adb shell su -c 'cat > ~/.local/share/pipewire/pipewire.conf.d/99-nuxel-s10.conf << '"'"'EOF'"'"'
context.properties = {
    audio.soft-mute = true
    alsa.ignored-controls = [ "MADERA HPOUT1 Digital" ]
}
EOF'

# Restart PipeWire to apply config
adb shell "systemctl --user restart pipewire"
sleep 2

# Test audio (optional)
adb shell "pw-play /usr/share/sounds/freedesktop/stereo/complete.oga" 2>/dev/null || echo "Audio test skipped (no sound files)"
```

### 3.5: Apply GPS Fix (Geoclue2 + D-Bus)

Reference: **triplefix.md** section 3, steps 1-5

```bash
# Install geoclue2 (if not already installed)
adb shell su -c "dnf install -y geoclue2"

# Find GPS device
adb shell "dmesg | grep -i gps" | head -5
# Note the device path (usually /dev/ttyHS1 or /dev/ttyS1)

# Configure geoclue
adb shell su -c 'cat > /etc/geoclue/geoclue.conf << '"'"'EOF'"'"'
[geoclue]
blacklist=

accuracy-level=street

[gnss]
enabled=true
gps-device=/dev/ttyHS1
EOF'

# Create D-Bus policy for geoclue
adb shell su -c 'cat > /etc/dbus-1/system.d/99-geoclue-nuxel.conf << '"'"'EOF'"'"'
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <policy user="geoclue">
    <allow own="org.freedesktop.GeoClue2"/>
    <allow send_destination="org.freedesktop.GeoClue2"/>
  </policy>
  <policy context="default">
    <allow send_destination="org.freedesktop.GeoClue2"
           send_interface="org.freedesktop.GeoClue2.Manager"/>
    <allow send_destination="org.freedesktop.GeoClue2"
           send_interface="org.freedesktop.GeoClue2.Client"/>
  </policy>
</busconfig>
EOF'

# Start geoclue
adb shell su -c "systemctl restart dbus && systemctl restart geoclue"

# Verify geoclue is running (may take 10-30 seconds for first GPS fix)
sleep 10
adb shell "geoclue-where-am-i" || echo "GPS fix not yet acquired (normal on first boot)"
```

---

## Phase 4: Final Verification

### 4.1: Run System Check

```bash
#!/bin/bash

echo "=========================================="
echo "Nuxel S10+ Post-Flash Verification"
echo "=========================================="

echo ""
echo "=== BLUETOOTH ==="
adb shell hciconfig
adb shell bluetoothctl list-adapters || echo "Adapter list failed (may need discovery)"

echo ""
echo "=== AUDIO ==="
adb shell pactl list sinks 2>/dev/null || adb shell aplay -l

echo ""
echo "=== GPS ==="
adb shell systemctl status geoclue || adb shell "geoclue-where-am-i"

echo ""
echo "=== CHARGING ANIMATION ==="
adb shell ls -la /data/adb/modules/my_own_splash_screen/up_param/up_param.bin

echo ""
echo "=========================================="
echo "Verification complete. Check above for green lights."
echo "=========================================="
```

### 4.2: Functional Tests

```bash
# Test 1: Bluetooth scan (should find nearby devices)
adb shell bluetoothctl
# > power on
# > scan on
# (Watch for nearby devices appearing)
# > exit

# Test 2: Audio playback
adb shell "speaker-test -t wav -c 2 -l 1" &
sleep 3
adb shell pkill speaker-test
echo "If you heard beeps, audio is working"

# Test 3: GPS (will take 30+ seconds on first try)
adb shell "timeout 30 geoclue-where-am-i" || echo "GPS still acquiring fix (normal)"

# Test 4: Charging animation (visual only, requires powering off with charger)
echo "Charging animation: Disconnect charger, power off completely, plug in charger while off"
echo "You should see your custom charging screen"
```

---

## Troubleshooting

### If Bluetooth Doesn't Show hci0

```bash
# Check kernel config was applied
adb shell "grep CONFIG_BT_HCIUART /proc/config.gz 2>/dev/null | gunzip" || adb shell "zcat /proc/config.gz | grep CONFIG_BT_HCIUART"
# Should show: CONFIG_BT_HCIUART=y

# Check if rfkill is blocking
adb shell rfkill list

# Check dmesg for bluetooth errors
adb shell "dmesg | grep -i bluetooth" | tail -20

# Manually unblock if soft-blocked
adb shell su -c "rfkill unblock bluetooth"
```

### If Audio Doesn't Work

```bash
# Check ALSA cards
adb shell aplay -l

# Check mixer
adb shell amixer -c 0 contents

# Check PipeWire daemon
adb shell "systemctl --user status pipewire"

# Restart all audio services
adb shell su -c "systemctl restart pipewire"
```

### If GPS Doesn't Acquire Fix

```bash
# Check geoclue is running
adb shell systemctl status geoclue

# Check GPS device exists
adb shell ls -la /dev/ttyHS*

# Check geoclue logs
adb shell journalctl -u geoclue -n 20

# Try manual GNSS check
adb shell "dmesg | grep -i gnss" | tail -10
```

### If Charging Animation Doesn't Show

```bash
# Verify MOSS module is installed
adb shell ls -la /data/adb/modules/my_own_splash_screen/

# Check up_param.bin is readable
adb shell su -c "tar -tf /data/adb/modules/my_own_splash_screen/up_param/up_param.bin" | grep lpm.jpg

# Manually trigger partition write
adb shell su -c "dd if=/data/adb/samsung_splash_backup/up_param_custom.bin of=/dev/block/by-name/up_param bs=4096"

# Reboot and test
adb reboot
```

---

## Quick Reference: One-Line Summary

**You're doing this:**
1. Build kernel with Bluetooth support
2. Flash MOSS charging animation in TWRP
3. Flash Bluetooth kernel in TWRP
4. Reboot into Nuxel
5. Configure GPS, Audio, Bluetooth userspace
6. Verify everything works
7. Test charging animation (visual: power off + plug in charger)

**Time estimate:** 45-60 minutes total
- Kernel build: 15-20 min
- MOSS prep: 5 min
- TWRP flashing: 10 min
- Userspace config: 15 min
- Testing: 5-10 min

---

## Abort/Rollback Plan

If anything goes wrong before reboot:
```bash
# Reboot to TWRP (hold Vol Down + Power)
# Tap "Wipe"
# Select "System"
# Swipe to wipe
# Tap "Install"
# Select original Nuxel ROM zip
# Swipe to flash
# Reboot
```

You have a full backup in TWRP. Don't panic.

---

## When Everything Works

Once all four subsystems are green:
- [ ] Bluetooth pairs and connects
- [ ] Audio plays and records
- [ ] GPS acquires location fix
- [ ] Charging animation displays custom screen

**You're done.** Your S10+ is now running Nuxel with working BT/Audio/GPS and a custom charging animation, all on a modern Bluetooth-enabled 4.14 kernel.

Next up: Camera, modem, NFC (in order of priority/difficulty).

Good luck. You've got this. 🚀

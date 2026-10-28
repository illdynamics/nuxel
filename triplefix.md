# Nuxel S10+ 4.14: GPS, Bluetooth & Audio Debug & Fix Guide

Your phone is closer than you think. These three subsystems have driver support but need userspace wiring and config fixes. This is a **systematic debug guide** — work through each section methodically.

---

## 1. BLUETOOTH: Fix CONFIG_BT_HCIUART + HCI Transport

### The Problem (From Your Screenshot)

```
state            : service_unavailable
controller       : no hci0 registered
HCI transport    : MISSING (CONFIG_BT_HCIUART is not set)
kernel driver    : bcm43xx
ifkill           : present, soft-blocked
```

**Translation:** The BCM4375 Bluetooth radio is powered, but the kernel can't talk to it because the UART transport layer isn't compiled in.

### The Fix

#### Step 1: Enable HCIUART in Kernel Config

```bash
# In your kernel build directory (kernel/s10plus/)
# Edit .config or use menuconfig

# Find and enable these:
CONFIG_BT=y
CONFIG_BT_HCIUART=y
CONFIG_BT_HCIUART_H4=y
CONFIG_BT_HCIUART_BCSP=y
CONFIG_BT_HCIUART_ATH3K=y
CONFIG_BT_HCIUART_LL=y
CONFIG_BT_HCIUART_3WIRE=y

# Also ensure:
CONFIG_SERIAL_CORE=y
CONFIG_SERIAL_8250=y
```

Or use menuconfig:
```bash
cd kernel/s10plus/
make ARCH=arm64 menuconfig
# Navigate to: Networking → Bluetooth → HT Bluetooth device drivers
# Enable: "HCI UART driver"
```

#### Step 2: Rebuild Kernel

```bash
cd kernel/s10plus/
./build-kernel.sh
# Flash the new kernel to your phone
```

#### Step 3: Verify HCI0 Shows Up

```bash
# On the phone, after reboot:
hciconfig
# Should show:
# hci0:	Type: Primary  Bus: UART
#	UP RUNNING PSCAN 
#	BD Address: XX:XX:XX:XX:XX:XX  ACL MTU: 1021:4  SCO MTU: 63:1

# If not:
dmesg | grep -i bluetooth
dmesg | grep -i hci
```

#### Step 4: Check Device Permissions

```bash
# Verify rfkill isn't blocking
rfkill list
# Should show: soft blocked: no

# If soft-blocked, unblock:
rfkill unblock bluetooth

# Check udev permissions
ls -la /dev/ttyHS0  # or /dev/ttyS0, depending on your UART device
# Should be readable/writable by bluetooth user

# If not, add udev rule:
cat > /etc/udev/rules.d/99-bluetooth.rules << 'EOF'
# Samsung S10+ Bluetooth UART
KERNEL=="ttyHS0", SUBSYSTEM=="tty", TAG="uaccess", MODE="0660"
SUBSYSTEM=="rfkill", ACTION=="change", RUN="/usr/bin/rfkill unblock bluetooth"
EOF

udevadm control --reload-rules
udevadm trigger
```

#### Step 5: Start Bluetooth Daemon

```bash
# Make sure bluetoothd is running and enabled:
systemctl status bluetooth
systemctl enable bluetooth
systemctl start bluetooth

# Check logs:
journalctl -u bluetooth -f
# Should show: Bluetooth management interface initialized
```

#### Step 6: Test Pairing

```bash
# Use bluetoothctl (interactive)
bluetoothctl
> power on
> discoverable on
> scan on
# Should now appear in other devices' Bluetooth lists

# Or pair with something:
> scan on
> pair XX:XX:XX:XX:XX:XX
> connect XX:XX:XX:XX:XX:XX
```

---

## 2. AUDIO: Fix ALSA Backend + PipeWire Volume Control

### The Problem (From Your Screenshot)

```
backend          : alsa-direct (sound server: unavailable)
cards            : 0: beyond-madera | 1: abox_vdma | 2: abox_dump
playback         : RDMA0, RDMA1, ... (multiple endpoints)
volume_control   : HPOUT1 Digital Volume
Mute unavailable : MADERA HPOUT1 Digital unmute hangs the kernel I2C control
```

**Translation:** The audio hardware is detected, but:
1. The sound server daemon (PipeWire) isn't running
2. Mute control is hanging the I2C bus (firmware bug in Samsung's code)

### The Fix

#### Step 1: Verify ALSA Detects Cards

```bash
# On the phone:
arecord -l          # List recording devices
aplay -l            # List playback devices
amixer controls     # List mixer controls

# Should show multiple cards and controls. If blank, audio driver isn't loaded.
# Check:
dmesg | grep -i alsa
dmesg | grep -i madera
lsmod | grep snd
```

#### Step 2: Start PipeWire (Sound Server)

```bash
# Check if PipeWire is installed:
which pipewire
which pipewire-pulse

# If missing, install:
sudo dnf install pipewire pipewire-pulseaudio pipewire-alsa

# Start and enable:
systemctl --user status pipewire
systemctl --user enable pipewire
systemctl --user start pipewire

# Verify it's running:
journalctl --user -u pipewire -f
# Should show: PipeWire started
```

#### Step 3: Work Around I2C Mute Hang

The kernel I2C control for mute is broken on Samsung's 4.14. Disable it:

```bash
# Create ALSA config override:
cat > /etc/alsa/conf.d/99-nuxel-s10-workaround.conf << 'EOF'
# Samsung S10+ Exynos9820 workaround
# The MADERA HPOUT1 mute control hangs I2C on 4.14
# Comment out mute control in mixer

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

# In PipeWire: disable mute control
ctl.!default {
    type hw
    card 0
}
EOF

# Reload ALSA:
alsactl init
alsactl store
```

#### Step 4: Configure PipeWire Audio Routes

```bash
# Check current routes:
pactl list sinks
pactl list sources

# Set default audio output (speaker/headphone):
pactl set-default-sink alsa_output.platform-fm_clock_gate1_np.stereo-fallback

# Test audio:
speaker-test -t wav -c 2 -l 1

# Test microphone:
arecord -D hw:0,0 -f S16_LE -r 44100 -d 5 /tmp/test.wav
aplay /tmp/test.wav
```

#### Step 5: Handle Volume Controls (Without Mute)

Since mute hangs the kernel, you'll need to work around it:

```bash
# Create a PipeWire profile that avoids mute:
cat > ~/.local/share/pipewire/pipewire.conf.d/99-noxel-s10.conf << 'EOF'
context.properties = {
    audio.soft-mute = true
    # Avoid hardware mute on MADERA HPOUT1
    alsa.ignored-controls = [ "MADERA HPOUT1 Digital" ]
}
EOF

# Restart PipeWire:
systemctl --user restart pipewire
```

#### Step 6: Verify Audio Works

```bash
# Play a sound:
ffplay /usr/share/sounds/freedesktop/stereo/complete.oga

# Or use PipeWire's test:
pw-play /usr/share/sounds/freedesktop/stereo/complete.oga

# Check recording:
pw-record -p audio/raw /tmp/test.wav
```

---

## 3. GPS: Fix D-Bus Location Service

### The Problem (From Your Screenshot)

```
unavailable:
org.freedesktop.DBus.Error.NoReply: Did not receive a reply.
Possible causes include:
  - the remote application did not send a reply
  - the message bus security policy blocked the reply
```

**Translation:** The GPS hardware works, but:
1. The geolocation service daemon isn't running or responding
2. D-Bus security policy might be blocking it

### The Fix

#### Step 1: Verify GPS Hardware is Detected

```bash
# Check if GPS device is visible:
ls -la /dev/ttyHS*
dmesg | grep -i gps
dmesg | grep -i gnss

# Should show something like /dev/ttyHS1 or similar for GPS UART
```

#### Step 2: Install & Start Geolocation Service

You need **geoclue2** — the standard Linux geolocation provider:

```bash
# Install:
sudo dnf install geoclue2

# Start and enable:
systemctl enable geoclue
systemctl start geoclue

# Verify it's running:
systemctl status geoclue
journalctl -u geoclue -f
```

#### Step 3: Configure GPS Device

Geoclue needs to know which device is the GPS:

```bash
# Edit geoclue config:
sudo cat > /etc/geoclue/geoclue.conf << 'EOF'
[geoclue]
blacklist=

# Accuracy threshold (meters)
accuracy-level=street

[gnss]
# Samsung S10+ GPS UART device
enabled=true
# Try these in order:
# /dev/ttyHS1 (high-speed UART 1)
# /dev/ttyS1 (standard UART 1)
# Check `dmesg | grep -i gps` to find yours
gps-device=/dev/ttyHS1

# Chipset (check dmesg for actual chipset)
# Common on Samsung: Broadcom BCM47XX
EOF

sudo systemctl restart geoclue
```

#### Step 4: Find the Actual GPS Device

If geoclue doesn't start, you need to find which /dev/tty* is GPS:

```bash
# Method 1: Check kernel logs
dmesg | grep -i gps
dmesg | grep -i gnss
dmesg | grep -i serial

# Method 2: Check device tree
cat /proc/device-tree/model
# Look for GNSS or GPS entries

# Method 3: Try each serial device
for device in /dev/ttyHS* /dev/ttyS*; do
    echo "Checking $device..."
    strace -e open,openat geoclue -D 2>&1 | grep $device
done

# Method 4: Check Samsung device-specific docs
# Samsung S10+ usually: /dev/ttyHS1 or /dev/ttyS9
```

Once you find it, update `/etc/geoclue/geoclue.conf` with the correct device.

#### Step 5: Fix D-Bus Permissions

The geoclue service might not have permission to reply on D-Bus:

```bash
# Check D-Bus policy:
cat /usr/share/dbus-1/system.d/geoclue.conf

# If missing or restrictive, create permissive config:
sudo cat > /etc/dbus-1/system.d/99-geoclue-nuxel.conf << 'EOF'
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
EOF

sudo systemctl restart dbus
sudo systemctl restart geoclue
```

#### Step 6: Test GPS

```bash
# Use geoclue's test client:
geoclue-where-am-i

# Or use D-Bus directly:
gdbus call --system \
    --dest org.freedesktop.GeoClue2 \
    --object-path /org/freedesktop/GeoClue2/Manager \
    --method org.freedesktop.GeoClue2.Manager.CreateClient

# Check if you get a response (may take 10-30 seconds for first fix)
journalctl -u geoclue -f
# Should show: "Got location fix" or similar
```

---

## 4. Integration: Verify All Three Together

### System Check

```bash
#!/bin/bash
echo "=== Bluetooth ==="
systemctl status bluetooth
hciconfig

echo "=== Audio ==="
systemctl --user status pipewire
aplay -l

echo "=== GPS ==="
systemctl status geoclue
geoclue-where-am-i

echo "=== D-Bus ==="
dbus-send --system --print-reply \
    --dest=org.freedesktop.DBus \
    /org/freedesktop/DBus \
    org.freedesktop.DBus.ListNames
```

### Full Boot Check

```bash
# After rebooting, verify everything starts automatically:

# 1. Bluetooth should be ready in ~5 seconds
sleep 5 && hciconfig

# 2. Audio should be available
pactl list sinks | head -5

# 3. GPS should start acquiring (may take 30 seconds on first boot)
sleep 30 && geoclue-where-am-i
```

---

## 5. Debugging Tips

### For Bluetooth Issues

```bash
# Enable debug logging:
echo "module btusb +p" > /sys/kernel/debug/dynamic_debug/control
modprobe -r btusb
modprobe btusb

# Check actual UART device:
ls -la /dev/ttyHS*
cat /proc/tty/drivers | grep HS

# Monitor HCI traffic (if hcidump installed):
hcidump -i hci0
```

### For Audio Issues

```bash
# Test each ALSA card individually:
aplay -D hw:0,0 /usr/share/sounds/freedesktop/stereo/complete.oga
aplay -D hw:1,0 /usr/share/sounds/freedesktop/stereo/complete.oga

# Check mixer state:
amixer -c 0 contents
amixer -c 0 cset numid=1 70%  # Set volume

# Monitor PipeWire:
pw-mon
pw-dump
```

### For GPS Issues

```bash
# Monitor GPS daemon:
journalctl -u geoclue -f

# Test GNSS data directly (if gpsd installed):
gpsd /dev/ttyHS1
gpsctl -x
cgps

# Check D-Bus methods available:
dbus-send --system --print-reply \
    --dest org.freedesktop.GeoClue2 \
    /org/freedesktop/GeoClue2/Manager \
    --method org.freedesktop.DBus.Introspectable.Introspect
```

---

## 6. Known Samsung 4.14 Quirks to Watch For

1. **Bluetooth UART port changes** — May be `/dev/ttyHS0`, `/dev/ttyS1`, or custom. Check `dmesg` after boot.
2. **Audio I2C mute control** — Confirmed hang on 4.14. Disable in ALSA config (see step 3.3 above).
3. **GPS UART baud rate** — Samsung firmware may expect non-standard baud (check `/sys/class/tty/ttyHS1/speed` or similar).
4. **D-Bus security** — Geoclue might be blocked by system D-Bus policy. Whitelist explicitly.
5. **HCIUART initialization order** — If `hci0` doesn't appear, check if rfkill is blocking before UART probe.

---

## 7. Final Checklist

- [ ] Kernel has `CONFIG_BT_HCIUART=y` and related options
- [ ] `hciconfig` shows `hci0` with `UP RUNNING` status
- [ ] `bluetoothctl` can scan and pair devices
- [ ] `systemctl --user status pipewire` shows active
- [ ] `pactl list sinks` shows at least one playback device
- [ ] `speaker-test -t wav -c 2 -l 1` produces sound
- [ ] `/etc/geoclue/geoclue.conf` points to correct GPS device
- [ ] `geoclue-where-am-i` returns location (may take 30 sec)
- [ ] D-Bus policy allows geoclue replies
- [ ] All three services start automatically on boot

Once these are all green, you have a working BT/Audio/GPS stack. Then you can integrate them into Nuxel's UI and move on to the next subsystem.

---

## 8. If You Get Stuck

Post the output of:

```bash
# Full system state dump
hciconfig
pactl list sinks
geoclue-where-am-i
dmesg | tail -100
journalctl -b | grep -i bluetooth
journalctl --user -b | grep -i pipewire
journalctl -b | grep -i geoclue
```

This will show exactly what's running and what's failing.

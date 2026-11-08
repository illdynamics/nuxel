# Nuxel S10+ Charging Animation: MOSS + Custom PNG Guide

You're going to use MOSS to repackage your charging animation. The charging screen is stored in the `up_param` partition as `lpm.jpg` (Low Power Mode).

---

## What You Need

1. **Your custom JPG image** saved as `./assets/nuxel-charging-animation.jpg`
2. **Original S10+ up_param.bin** (backup or extract from your current system)
3. **ImageMagick** or similar to resize/optimize JPEG
4. **MOSS Magisk module** (you already have it)
5. **tar command** to repack the images

---

## Step 1: Extract Your Current up_param.bin

### Option A: Extract from Your S10+ (Easiest)

```bash
# On your S10+ (in Termux with root):
su
dd if=/dev/block/by-name/up_param of=/sdcard/up_param.bin bs=4096

# Verify:
tar -tf /sdcard/up_param.bin
# Should show: logo.jpg, lpm.jpg, download.jpg, etc.
```

Then pull it to your desktop:
```bash
adb pull /sdcard/up_param.bin
```

### Option B: Extract from MOSS Module (If Already Flashed)

If you already have MOSS flashed, the backup is stored here:
```bash
adb pull /data/adb/samsung_splash_backup/up_param_original.bin
mv up_param_original.bin up_param.bin
```

---

## Step 2: Extract Images from up_param.bin

On your **desktop/build machine**:

```bash
# Create working directory
mkdir -p nuxel-charging-work
cd nuxel-charging-work

# Extract the tar archive
tar -xf up_param.bin

# List what you extracted
ls -lh
```

You should see:
```
logo.jpg              (main boot splash)
lpm.jpg               (charging screen — THIS ONE WE'RE CHANGING)
android_logo.jpg
download.jpg
device_lock.jpg
device_unlock.jpg
etc.
```

---

## Step 3: Prepare Your Custom Charging Animation

### Understand the lpm.jpg Requirements

- **Format:** JPEG only (not PNG, not WEBP, not WebP)
- **Resolution:** Must match S10+ screen: **1080×2340 pixels** (or 1440×3120 if using max resolution)
- **File size:** Keep under 500KB (will fit in up_param)
- **Quality:** Use standard JPEG (not progressive)

### Check Current lpm.jpg Resolution

```bash
identify lpm.jpg
# Output example: lpm.jpg JPEG 1080x2340 1080x2340 8-bit sRGB 89.5KB

# Note the resolution (1080x2340 in this example)
```

### Resize and Optimize Your JPG

Since you already have a JPG file, you just need to resize it to match the S10+ screen and optimize it:

```bash
# Using ImageMagick (install if needed: apt install imagemagick)
convert ./assets/nuxel-charging-animation.jpg \
  -resize 1080x2340! \
  -quality 85 \
  lpm.jpg

# Verify it matches the original resolution
identify lpm.jpg
# Should output: lpm.jpg JPEG 1080x2340 ...
```

**Quality parameter:** 85 is a good balance. Use 80-90 for good-looking results.

**Note:** The `!` in `-resize 1080x2340!` forces exact dimensions, stretching if needed. If you want to preserve aspect ratio and add black bars instead:

```bash
# Aspect-ratio preserving (centered with black bars)
convert ./assets/nuxel-charging-animation.jpg \
  -resize 1080x2340 \
  -background black \
  -gravity center \
  -extent 1080x2340 \
  -quality 85 \
  lpm.jpg
```

### Verify the Image Looks Good

```bash
# Display it (on Linux with a GUI)
display lpm.jpg

# Or check size
ls -lh lpm.jpg
# Should be reasonable (under 500KB)
```

---

## Step 4: Repack into up_param.bin

Now that you've replaced `lpm.jpg`, repack everything:

```bash
cd nuxel-charging-work

# List files to make sure lpm.jpg is there
ls -1

# Repack as tar (uncompressed — IMPORTANT)
tar -cf up_param_new.bin *.jpg

# Verify the tar is valid
tar -tf up_param_new.bin
# Should list: logo.jpg, lpm.jpg, android_logo.jpg, etc.

# Check size
ls -lh up_param_new.bin
```

**Important:** The tar must be uncompressed. If you use `tar -czf` (with gzip), it will fail.

---

## Step 5: Prepare the MOSS Module

Now you need to put your new `up_param_new.bin` into the MOSS Magisk module and flash it.

### Method 1: Using a GUI Archive Manager (Easiest)

1. **Extract the MOSS module zip** to a folder on your desktop
2. **Navigate to** `MOSS/up_param/` folder
3. **Delete or backup** any existing `up_param.bin` in that folder
4. **Copy your `up_param_new.bin`** into `MOSS/up_param/` and **rename it to `up_param.bin`**
5. **Repack the MOSS folder** back into a ZIP file
   - Select all files in MOSS folder (Ctrl+A)
   - Compress as ZIP
   - Name it `moss-nuxel-charging.zip` or similar

### Method 2: Using Command Line

```bash
# Copy MOSS module
cp -r MOSS moss-nuxel-charging

# Replace the up_param.bin
cp up_param_new.bin moss-nuxel-charging/up_param/up_param.bin

# Verify it's there and correct size
ls -lh moss-nuxel-charging/up_param/up_param.bin

# Repack as zip
cd moss-nuxel-charging
zip -r ../moss-nuxel-charging.zip .
cd ..

# Verify zip contents
unzip -l moss-nuxel-charging.zip | grep up_param.bin
```

---

## Step 6: Flash the Module to Your S10+

You have two options:

### Option A: Magisk App (Easiest)

1. **Copy** `moss-nuxel-charging.zip` to your S10+ storage (USB or ADB)
   ```bash
   adb push moss-nuxel-charging.zip /sdcard/
   ```

2. **On your S10+:**
   - Open **Magisk app**
   - Tap **Modules** (bottom menu)
   - Tap **Install from storage** (the + icon)
   - Select `moss-nuxel-charging.zip`
   - Tap **Install**
   - Wait for it to finish → **Reboot**

3. **After reboot:** You should see your custom charging animation when you plug in the charger while the phone is off

### Option B: TWRP Recovery (If Magisk Fails)

```bash
# Boot into TWRP recovery (usually Volume Down + Power)
# Then in TWRP:
# 1. Tap Install
# 2. Select moss-nuxel-charging.zip
# 3. Swipe to flash
# 4. Reboot
```

---

## Step 7: Verify It Works

### Test 1: Check Module Installation

```bash
adb shell
su
ls -l /data/adb/modules/my_own_splash_screen/up_param/
# Should show: device_path.txt, up_param.bin
```

### Test 2: Trigger the Charging Screen

1. **Power off your S10+** completely
2. **Plug in USB charger**
3. You should see your custom charging animation

If the screen doesn't turn on or you see the old animation:
- The module may not have written properly
- Try flashing from TWRP instead
- Check Magisk logs: `adb shell su -c "tail -50 /data/adb/modules/my_own_splash_screen/post-fs-data.sh"` (or similar)

---

## Step 8: Troubleshooting

### Animation Still Shows Old Image

**Cause:** Module didn't write to partition

**Fix:**
```bash
# Manually write with dd
adb shell su -c "dd if=/data/adb/samsung_splash_backup/up_param_custom.bin of=/dev/block/by-name/up_param bs=4096"
adb shell reboot
```

### "up_param.bin is not a valid tar archive"

**Cause:** You compressed the tar with gzip or used wrong format

**Fix:**
```bash
# Verify the tar is NOT gzipped
file up_param_new.bin
# Should output: "POSIX tar archive"
# NOT: "gzip compressed data"

# If it's gzipped, repack correctly:
tar -cf up_param_new.bin *.jpg
```

### MOSS Installation Fails with "dd write failed"

**Cause:** Magisk module installation permissions issue

**Fix:**
1. Flash from **TWRP recovery** instead of Magisk app
2. Or disable SELinux temporarily:
   ```bash
   adb shell su -c "setenforce 0"
   # (Re-enable after: setenforce 1)
   ```

### Image Looks Stretched or Pixelated

**Cause:** Wrong resolution or quality settings

**Fix:**
```bash
# Check current screen resolution
adb shell wm size
# Should show: 1080x2340 or similar

# Resize with exact match:
convert ./assets/nuxel-charging-animation.jpg \
  -resize 1080x2340! \
  -quality 90 \
  lpm.jpg

# Repack and reflash
tar -cf up_param_new.bin *.jpg
```

---

## Complete Workflow (Quick Reference)

```bash
# 1. Extract original up_param.bin from S10+
adb shell su -c "dd if=/dev/block/by-name/up_param of=/sdcard/up_param.bin bs=4096"
adb pull /sdcard/up_param.bin

# 2. Extract images
mkdir charging-animation
cd charging-animation
tar -xf ../up_param.bin

# 3. Resize your JPG to match S10+ screen
convert ../assets/nuxel-charging-animation.jpg -resize 1080x2340! -quality 85 lpm.jpg

# 4. Repack
tar -cf up_param_new.bin *.jpg

# 5. Update MOSS module
cp up_param_new.bin ../MOSS/up_param/up_param.bin

# 6. Rezip MOSS
cd ../MOSS
zip -r ../moss-nuxel-charging.zip .

# 7. Flash to device
adb push ../moss-nuxel-charging.zip /sdcard/
# Then: Magisk > Modules > Install from storage > select zip > Reboot
```

---

## Bonus: Create Your Own Charging Animation Frames

Want an **animated** charging screen instead of static?

Samsung 4.14 doesn't support animated sequences in the standard `lpm.jpg`, but you can:

1. **Create a flipbook-style animation** as a single JPEG (multiple frames side-by-side)
2. **Use ImageMagick to compose** multiple PNGs into one:
   ```bash
   montage frame_0.png frame_1.png frame_2.png frame_3.png \
     -tile 2x2 \
     -geometry 540x1170+0+0 \
     -background black \
     charging_animation.jpg
   # Then resize to 1080x2340 to fit screen
   ```

3. **Or keep it simple:** Just use a cool static image that looks nice on the lock screen while charging

For Nuxel's retro aesthetic, a simple pixel-art style charging indicator (battery percentage + animation visual) would look awesome.

---

## Summary

**You'll do this every time you want to change the charging animation:**

1. Extract `up_param.bin` from S10+
2. Untar it → edit `lpm.jpg` → retar
3. Put new tar in MOSS module
4. Flash MOSS via Magisk or TWRP
5. Reboot and test

**The whole process takes ~10 minutes once you have the tools set up.**

Good luck! Let me know if you hit any snags.

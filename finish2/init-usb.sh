#!/bin/sh
# Nuxel initramfs init (g7power/ocean) — USB SERIAL CONSOLE bring-up build.
# Brings up the DWC3 gadget (dr_mode=peripheral in DT) as a CDC-ACM serial
# console, then reports + hands over an interactive shell over USB.
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

mount -t proc  -o noexec,nosuid,nodev none /proc 2>/dev/null
mount -t sysfs -o noexec,nosuid,nodev none /sys  2>/dev/null
mount -t devtmpfs none /dev 2>/dev/null
mkdir -p /dev/pts /dev/mapper /dev/disk/by-partlabel /run /tmp /sys/kernel/config
mount -t devpts none /dev/pts 2>/dev/null

if [ ! -e /bin/sh ] && [ -x /bin/toybox ]; then
    ln -sf toybox /bin/sh
    for cmd in mount umount switch_root modprobe mknod mkswap mkfs.ext4 \
               tar gzip ls cat printf echo sed grep awk find sleep date ps insmod \
               df du sh sync reboot poweroff dd cp mv rm mkdir ln chown \
               chmod dmesg blkid losetup head tail tr cut wc uname; do
        ln -sf toybox "/bin/${cmd}" 2>/dev/null
    done
fi

CON=/dev/console
say() { echo "nuxel: $*" > "$CON" 2>/dev/null; echo "<6>nuxel: $*" > /dev/kmsg 2>/dev/null; }

say "=== Nuxel g7power USB-console bring-up ==="
say "cmdline: $(cat /proc/cmdline 2>/dev/null)"
say "uname: $(uname -a 2>/dev/null)"

# --- bring up the USB peripheral controller --------------------------------
say "mounting configfs"
mount -t configfs none /sys/kernel/config 2>/dev/null
say "loading qusb2 phy: $( (modprobe phy-qcom-qusb2 2>&1) || (insmod /lib/modules/6.19.0-g05f7e89ab973/kernel/drivers/phy/qualcomm/phy-qcom-qusb2.ko 2>&1) || echo FAILED)"
i=0; while [ ! -e /sys/class/udc ] || [ -z "$(ls /sys/class/udc 2>/dev/null)" ]; do
    i=$((i+1)); [ "$i" -gt 20 ] && break; sleep 1
done
say "udc list: [$(ls /sys/class/udc 2>/dev/null)]"

G=/sys/kernel/config/usb_gadget/g1
mkdir -p "$G" 2>/dev/null
echo 0x1d6b   > "$G/idVendor"  2>/dev/null
echo 0x0104   > "$G/idProduct" 2>/dev/null
echo 0x0100   > "$G/bcdDevice" 2>/dev/null
echo 0x0200   > "$G/bcdUSB"    2>/dev/null
mkdir -p "$G/strings/0x409" 2>/dev/null
echo "0123456789"      > "$G/strings/0x409/serialnumber" 2>/dev/null
echo "Nuxel"           > "$G/strings/0x409/manufacturer" 2>/dev/null
echo "G7Power Nuxel"   > "$G/strings/0x409/product"      2>/dev/null
mkdir -p "$G/configs/c.1/strings/0x409" 2>/dev/null
echo "ACM" > "$G/configs/c.1/strings/0x409/configuration" 2>/dev/null
echo 250  > "$G/configs/c.1/MaxPower" 2>/dev/null
mkdir -p "$G/functions/acm.gs0" 2>/dev/null
ln -sf "$G/functions/acm.gs0" "$G/configs/c.1/" 2>/dev/null
UDC="$(ls /sys/class/udc 2>/dev/null | head -1)"
if [ -n "$UDC" ]; then
    say "binding udc $UDC"
    echo "$UDC" > "$G/UDC" 2>/dev/null || say "UDC bind failed"
else
    say "NO UDC available (dwc3/qusb2 did not come up)"
fi

# wait for the gadget's serial tty
i=0; while [ ! -c /dev/ttyGS0 ]; do i=$((i+1)); [ "$i" -gt 20 ] && break; sleep 1; done
if [ -c /dev/ttyGS0 ]; then
    say "ttyGS0 present -> USB serial console active"
    CON=/dev/ttyGS0
    exec 0<"$CON" 1>"$CON" 2>"$CON"
else
    say "ttyGS0 NOT present; continuing on /dev/console only"
fi

# --- now report -------------------------------------------------------------
echo "=== Nuxel g7power live console ==="
echo "cmdline: $(cat /proc/cmdline)"
echo "--- block devices ---"; ls -l /dev/mmcblk* 2>&1
echo "--- /dev ---"; ls /dev 2>&1
echo "--- mmc/sdhci dmesg ---"; dmesg 2>/dev/null | grep -iE 'mmc|sdhci|ext4|dwc3|qusb2|phy|udc|gadget|pstore|ramoops' | tail -60
echo "--- dmesg tail ---"; dmesg 2>/dev/null | tail -40
echo "--- /proc/filesystems ---"; cat /proc/filesystems 2>&1

# --- attempt root discovery (report only; do not switch_root here) ----------
FS=ext4; MNT=/newroot; mkdir -p $MNT
for d in /dev/mmcblk0p63 /dev/mmcblk0p64 /dev/mmcblk0p62 /dev/mmcblk0p*; do
    [ -b "$d" ] || continue
    if mount -t $FS -o ro "$d" "$MNT" 2>/dev/null; then
        if [ -d "$MNT/etc/nuxel" ] || [ -f "$MNT/sbin/init" ]; then
            echo "ROOT-FOUND: $d label=$(blkid -s LABEL -o value $d 2>/dev/null)"; umount "$MNT"; break
        fi
        umount "$MNT" 2>/dev/null
    fi
done
echo "=== dropping to interactive shell (PID1) over USB ==="
exec sh -i

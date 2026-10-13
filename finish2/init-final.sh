#!/bin/sh
# Nuxel initramfs init — g7power/ocean FINAL bring-up.
#  * robust root discovery (label scan + expected GPT numbers + brute force)
#  * best-effort USB CDC-ACM console (DWC3 dr_mode=peripheral)
#  * never reboot-loops: on failure it stays up and keeps retrying
export PATH=/sbin:/bin:/usr/sbin:/usr/bin
mount -t proc  -o noexec,nosuid,nodev none /proc 2>/dev/null
mount -t sysfs -o noexec,nosuid,nodev none /sys  2>/dev/null
mount -t devtmpfs none /dev 2>/dev/null
mkdir -p /dev/pts /dev/mapper /dev/disk/by-partlabel /run /tmp /sys/kernel/config
mount -t devpts none /dev/pts 2>/dev/null
if [ ! -e /bin/sh ] && [ -x /bin/toybox ]; then
    ln -sf toybox /bin/sh
    for c in mount umount switch_root modprobe insmod mknod ls cat printf echo \
             sed grep awk find sleep date ps df du sh sync reboot poweroff dd cp \
             mv rm mkdir ln chown chmod dmesg blkid head tail tr cut wc uname; do
        ln -sf toybox "/bin/$c" 2>/dev/null
    done
fi
CON=/dev/console
say(){ echo "nuxel: $*" > "$CON" 2>/dev/null; echo "<6>nuxel: $*" > /dev/kmsg 2>/dev/null; }

# ---- best-effort USB serial console ----
mount -t configfs none /sys/kernel/config 2>/dev/null
modprobe phy-qcom-qusb2 2>/dev/null || insmod /lib/modules/6.19.0-g05f7e89ab973/kernel/drivers/phy/qualcomm/phy-qcom-qusb2.ko 2>/dev/null
i=0; while [ -z "$(ls /sys/class/udc 2>/dev/null)" ]; do i=$((i+1)); [ $i -gt 8 ] && break; sleep 1; done
G=/sys/kernel/config/usb_gadget/g1
if [ -n "$(ls /sys/class/udc 2>/dev/null)" ] && mkdir -p "$G" 2>/dev/null; then
    echo 0x1d6b > "$G/idVendor"; echo 0x0104 > "$G/idProduct"
    mkdir -p "$G/strings/0x409"; echo "Nuxel" > "$G/strings/0x409/manufacturer"
    echo "G7Power Nuxel" > "$G/strings/0x409/product"; echo "ZY326RGXCM" > "$G/strings/0x409/serialnumber"
    mkdir -p "$G/configs/c.1/strings/0x409"; echo "ACM" > "$G/configs/c.1/strings/0x409/configuration"
    mkdir -p "$G/functions/acm.gs0"; ln -sf "$G/functions/acm.gs0" "$G/configs/c.1/" 2>/dev/null
    echo "$(ls /sys/class/udc | head -1)" > "$G/UDC" 2>/dev/null
    i=0; while [ ! -c /dev/ttyGS0 ]; do i=$((i+1)); [ $i -gt 8 ] && break; sleep 1; done
fi
if [ -c /dev/ttyGS0 ]; then CON=/dev/ttyGS0; exec 0<"$CON" 1>"$CON" 2>"$CON"; say "USB console up on ttyGS0"; fi
echo "=== Nuxel g7power bring-up ==="
echo "cmdline: $(cat /proc/cmdline 2>/dev/null)"
echo "uname: $(uname -a 2>/dev/null)"
echo "udc=[$(ls /sys/class/udc 2>/dev/null)]"

FS=ext4; MNT=/newroot; mkdir -p $MNT
is_root(){ [ -d "$1/etc/nuxel" ] && return 0; [ -f "$1/sbin/init" ] && [ -f "$1/bin/toybox" ] && return 0; return 1; }
i=0; while [ $i -lt 20 ]; do ls /dev/mmcblk0p* >/dev/null 2>&1 && break; i=$((i+1)); sleep 1; done
echo "block devices: $(ls /dev/mmcblk* 2>/dev/null | tr '\n' ' ')"

FOUND=""
for attempt in 1 2 3; do
  CAND=""
  for d in /dev/mmcblk0p* ; do
    [ -b "$d" ] || continue
    L="$(blkid -s LABEL -o value "$d" 2>/dev/null | head -1)"
    [ "$L" = "nuxel-ocean" ] && CAND="$CAND $d"
  done
  CAND="$CAND /dev/mmcblk0p63 /dev/mmcblk0p64 /dev/mmcblk0p62"
  for d in /dev/mmcblk0p*; do [ -b "$d" ] && CAND="$CAND $d"; done
  SEEN=""
  for c in $CAND; do
    case " $SEEN " in *" $c "*) continue;; esac; SEEN="$SEEN $c"
    if mount -t $FS -o ro "$c" "$MNT" 2>/dev/null; then
      if is_root "$MNT"; then FOUND="$c"; echo "ROOT OK: $c label=$(blkid -s LABEL -o value $c 2>/dev/null)"; break
      else umount "$MNT" 2>/dev/null; fi
    fi
  done
  [ -n "$FOUND" ] && break
  echo "attempt $attempt: no Nuxel root yet; retrying"
  sleep 5
done

if [ -z "$FOUND" ]; then
  echo "=== NUXEL: no root found; dmesg (mmc/ext4) ==="
  dmesg 2>/dev/null | grep -iE 'mmc|sdhci|ext4|part' | tail -40
  echo "=== staying up (no reboot loop). Interactive shell follows. ==="
  exec sh -i
fi

if mount -o remount,rw "$MNT" 2>/dev/null; then :; else umount "$MNT" 2>/dev/null; mount -t $FS -o rw "$FOUND" "$MNT"; fi
echo "<6>NUXEL_STATUS: ROOT_OK $FOUND" > /dev/kmsg 2>/dev/null
for m in sys proc dev; do mount --move "/$m" "$MNT/$m" 2>/dev/null; done
echo "switch_root -> $MNT"
if [ -x "$MNT/sbin/init" ]; then exec switch_root "$MNT" /sbin/init; fi
if [ -x "$MNT/init" ]; then exec switch_root "$MNT" /init; fi
exec switch_root "$MNT" /bin/sh

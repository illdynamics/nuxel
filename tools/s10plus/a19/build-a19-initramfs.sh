#!/bin/sh
# A19 initramfs: A18's archive (hardware-proven root resolution + bound USB gadget)
# with the A19 /init and the A19 nuxel-console (mknod of /dev/ttyGS0).
set -eu
ROOT=/Users/wicked/x/nuxel
CAND=A19
BASE=$ROOT/build/out/s10plus/debug-candidates/A18/initramfs.cpio
W=$ROOT/build/out/s10plus/debug-candidates/$CAND
NEWC=$ROOT/tools/s10plus/newc.py
mkdir -p "$W"
STAGE=$W/initramfs.cpio
cp "$BASE" "$STAGE"
echo "base sha : $(shasum -a 256 "$STAGE" | cut -d' ' -f1)"
swap() { mv -f "$STAGE.t" "$STAGE"; }

echo "1. /init <- boot/initramfs/init.sh (A19)"
python3 "$NEWC" replace "$STAGE" init "$ROOT/boot/initramfs/init.sh" "$STAGE.t" --mode=0100755
swap

echo "2. opt/nuxel/nuxel-console <- A19 build (creates /dev/ttyGS0 from sysfs)"
python3 "$NEWC" replace "$STAGE" opt/nuxel/nuxel-console \
    "$W/nuxel-console" "$STAGE.t" --mode=0100755
swap

echo "3. layout"
python3 "$NEWC" list "$STAGE" | grep -E " init$|opt/nuxel/"
echo "cpio size  : $(wc -c <"$STAGE" | tr -d ' ')"
echo "cpio sha256: $(shasum -a 256 "$STAGE" | cut -d' ' -f1)"

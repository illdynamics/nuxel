#!/bin/sh
# A20 initramfs — A19's hardware-proven archive plus the ORIGINAL Nuxel MP4
# animation player.
#
#   * /init                      <- boot/initramfs/init.sh (adds nuxel_start_animation)
#   * opt/nuxel/nuxel-anim-player <- freestanding aarch64 NUXANM01 decoder (66 KB)
#
# Everything A19 proved (root resolution, cgroup2 ordering, bound USB gadget,
# Fedora service execution) is carried over untouched.  The ~18.5 MB animation
# container deliberately does NOT live here: it goes into the Fedora rootfs so
# the kernel image is not enlarged by animation data (mission section 2/Step D).
set -eu
ROOT=/Users/wicked/x/nuxel
CAND=${CAND:-A20}
BASE=${BASE:-$ROOT/build/out/s10plus/debug-candidates/A19/initramfs.cpio}
W=$ROOT/build/out/s10plus/debug-candidates/$CAND
NEWC=$ROOT/tools/s10plus/newc.py
PLAYER=$ROOT/build/out/s10plus/nuxel-anim-player

mkdir -p "$W"
STAGE=$W/initramfs.cpio
cp "$BASE" "$STAGE"
echo "base cpio : $BASE"
echo "base sha  : $(shasum -a 256 "$STAGE" | cut -d' ' -f1)  ($(wc -c <"$STAGE" | tr -d ' ') bytes)"
swap() { mv -f "$STAGE.t" "$STAGE"; }

echo "1. /init <- boot/initramfs/init.sh"
python3 "$NEWC" replace "$STAGE" init "$ROOT/boot/initramfs/init.sh" "$STAGE.t" --mode=0100755
swap

echo "2. opt/nuxel/nuxel-anim-player (original-MP4 framebuffer player)"
[ -f "$PLAYER" ] || { echo "MISSING $PLAYER (build tools/s10plus/nuxel-anim-player.c)" >&2; exit 1; }
python3 "$NEWC" insert "$STAGE" "$STAGE.t" --after opt/nuxel \
    --name opt/nuxel/nuxel-anim-player --mode 0100755 --type file --file "$PLAYER"
swap
printf '   %-32s %s bytes\n' nuxel-anim-player "$(wc -c <"$PLAYER" | tr -d ' ')"

echo "3. layout"
python3 "$NEWC" list "$STAGE" | grep -E "opt/nuxel/|^[0-9]+ +file.* init$"
echo "logical end: $(python3 "$NEWC" trailer "$STAGE")"
echo "cpio size  : $(wc -c <"$STAGE" | tr -d ' ')"
echo "cpio sha256: $(shasum -a 256 "$STAGE" | cut -d' ' -f1)"

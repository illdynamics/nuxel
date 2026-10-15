#!/bin/sh
# A21 initramfs — A20's hardware-proven archive with the ONE-PENGUIN / CORRECT-COLOUR
# display fixes and the fixed evidence channel.
#
#   * /init                          <- boot/initramfs/init.sh
#        renderer-ownership state machine: EARLY_FIRST_LIGHT -> MP4_PLAYER_STARTING
#        -> MP4_FIRST_FRAME_READY -> MP4_PLAYER_ACTIVE (or FIRST_LIGHT_FALLBACK),
#        with a bounded handshake so init does not switch_root under the player.
#   * opt/nuxel/nuxel-anim-player    <- corrected colour conversion + takeover
#   * opt/nuxel/nuxel-fb-phone       <- fixed evidence channel + stoppable painter
#
# Everything A19/A20 proved (root resolution, cgroup2 ordering, bound USB gadget,
# Fedora service execution, kernel-embedded initramfs delivery) is carried over
# untouched.  The ~18.5 MB animation container still lives in the Fedora rootfs.
set -eu
ROOT=/Users/wicked/x/nuxel
CAND=${CAND:-A21}
BASE=${BASE:-$ROOT/build/out/s10plus/debug-candidates/A20/initramfs.cpio}
W=$ROOT/build/out/s10plus/debug-candidates/$CAND
NEWC=$ROOT/tools/s10plus/newc.py
PLAYER=$ROOT/build/out/s10plus/nuxel-anim-player
FBPHONE=$ROOT/build/out/s10plus/nuxel-fb-phone

mkdir -p "$W"
STAGE=$W/initramfs.cpio
cp "$BASE" "$STAGE"
echo "base cpio : $BASE"
echo "base sha  : $(shasum -a 256 "$STAGE" | cut -d' ' -f1)  ($(wc -c <"$STAGE" | tr -d ' ') bytes)"
swap() { mv -f "$STAGE.t" "$STAGE"; }

echo "1. /init <- boot/initramfs/init.sh"
python3 "$NEWC" replace "$STAGE" init "$ROOT/boot/initramfs/init.sh" "$STAGE.t" --mode=0100755
swap

for pair in "$PLAYER:opt/nuxel/nuxel-anim-player" "$FBPHONE:opt/nuxel/nuxel-fb-phone"; do
    src=${pair%%:*}; name=${pair#*:}
    [ -f "$src" ] || { echo "MISSING $src" >&2; exit 1; }
    echo "2. $name"
    python3 "$NEWC" replace "$STAGE" "$name" "$src" "$STAGE.t" --mode=0100755
    swap
    printf '   %-34s %s bytes  sha256 %s\n' "$name" \
        "$(wc -c <"$src" | tr -d ' ')" "$(shasum -a 256 "$src" | cut -d' ' -f1)"
done

echo "3. layout"
python3 "$NEWC" list "$STAGE" | grep -E "opt/nuxel/|^[0-9]+ +file.* init$"
echo "logical end: $(python3 "$NEWC" trailer "$STAGE")"
echo "cpio size  : $(wc -c <"$STAGE" | tr -d ' ')"
echo "cpio sha256: $(shasum -a 256 "$STAGE" | cut -d' ' -f1)"

echo "4. verify the members really are the new files"
for pair in "init:$ROOT/boot/initramfs/init.sh" \
            "opt/nuxel/nuxel-anim-player:$PLAYER" \
            "opt/nuxel/nuxel-fb-phone:$FBPHONE"; do
    name=${pair%%:*}; src=${pair#*:}
    python3 "$NEWC" extract "$STAGE" "$name" "$W/verify.tmp"
    a=$(shasum -a 256 "$W/verify.tmp" | cut -d' ' -f1)
    b=$(shasum -a 256 "$src" | cut -d' ' -f1)
    if [ "$a" = "$b" ]; then echo "   OK   $name == $(basename "$src")  ($a)";
    else echo "   FAIL $name differs ($a != $b)"; exit 1; fi
done
rm -f "$W/verify.tmp"
echo A21_INITRAMFS_BUILD_OK

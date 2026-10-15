#!/bin/sh
# A17 initramfs: A16's hardware-proven archive + the A17 /init, the rebuilt
# (content-verified) systemd library, and the two new static helpers.
set -eu
ROOT=/Users/wicked/x/nuxel
BASE=$ROOT/build/out/s10plus/debug-candidates/A16/initramfs.cpio
W=$ROOT/build/out/s10plus/debug-candidates/A17
NEWC=$ROOT/tools/s10plus/newc.py
PAY=$W

mkdir -p "$W"
STAGE=$W/initramfs.cpio
cp "$BASE" "$STAGE"
echo "base cpio: $(wc -c <"$STAGE" | tr -d ' ') bytes  sha256 $(shasum -a 256 "$STAGE" | cut -d' ' -f1)"

swap() { mv -f "$STAGE.t" "$STAGE"; }

echo "1. /init <- boot/initramfs/init.sh (A17)"
python3 "$NEWC" replace "$STAGE" init "$ROOT/boot/initramfs/init.sh" "$STAGE.t" --mode=0100755
swap

echo "2. opt/nuxel/libsystemd-shared-258.11-1.fc43.so <- A17 rebuilt library"
python3 "$NEWC" replace "$STAGE" opt/nuxel/libsystemd-shared-258.11-1.fc43.so \
    "$PAY/libsystemd-shared-258.11-1.fc43.so" "$STAGE.t" --mode=0100755
swap

add() { # add <src-file> <member-name>
  [ -f "$1" ] || { echo "MISSING PAYLOAD $1" >&2; exit 1; }
  python3 "$NEWC" insert "$STAGE" "$STAGE.t" --after opt/nuxel --name "opt/nuxel/$2" \
      --mode 0100755 --type file --file "$1"
  swap
  printf '   %-36s %s bytes\n' "$2" "$(wc -c <"$1" | tr -d ' ')"
}

echo "3. new helpers"
add "$PAY/nuxel-verify"  nuxel-verify
add "$PAY/nuxel-console" nuxel-console

echo "4. layout check"
python3 "$NEWC" list "$STAGE" | grep -E "init$|opt/nuxel/|dev/kmsg|bin/toybox|bin/switch_root"
echo "logical end : $(python3 "$NEWC" trailer "$STAGE")"
echo "cpio size   : $(wc -c <"$STAGE" | tr -d ' ')"
shasum -a 256 "$STAGE" | awk '{print "cpio sha256 : "$1}'

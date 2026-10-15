#!/bin/sh
# A18 initramfs builder — A17 (hardware-flashed) + the hardware probe.
# This is deliberately parameterised so the next change set is one edit away.
#
#   BASE      : the archive to start from (default: A17's, which is what is on
#               the handset's BOOT partition right now)
#   PAYLOADS  : extra opt/nuxel/<name> files to insert (default: nuxel-hwprobe)
set -eu
ROOT=/Users/wicked/x/nuxel
CAND=${CAND:-A18}
BASE=${BASE:-$ROOT/build/out/s10plus/debug-candidates/A17/initramfs.cpio}
W=$ROOT/build/out/s10plus/debug-candidates/$CAND
NEWC=$ROOT/tools/s10plus/newc.py

mkdir -p "$W"
STAGE=$W/initramfs.cpio
cp "$BASE" "$STAGE"
echo "base cpio : $BASE"
echo "base sha  : $(shasum -a 256 "$STAGE" | cut -d' ' -f1)  ($(wc -c <"$STAGE" | tr -d ' ') bytes)"
swap() { mv -f "$STAGE.t" "$STAGE"; }

echo "1. /init <- boot/initramfs/init.sh"
python3 "$NEWC" replace "$STAGE" init "$ROOT/boot/initramfs/init.sh" "$STAGE.t" --mode=0100755
swap

add() { # add <src> <name>; skip if the member already exists
  name="$2"
  if python3 "$NEWC" list "$STAGE" | grep -q "opt/nuxel/$name\$"; then
    echo "   $name already present (kept)"
    return 0
  fi
  [ -f "$1" ] || { echo "MISSING PAYLOAD $1" >&2; exit 1; }
  python3 "$NEWC" insert "$STAGE" "$STAGE.t" --after opt/nuxel --name "opt/nuxel/$name" \
      --mode 0100755 --type file --file "$1"
  swap
  printf '   %-24s %s bytes\n' "$name" "$(wc -c <"$1" | tr -d ' ')"
}

echo "2. payloads"
add "$ROOT/build/out/s10plus/debug-candidates/A18/nuxel-hwprobe" nuxel-hwprobe

echo "2b. replace opt/nuxel/nuxel-console with the A18 build (adds the persistent
    rootfs boot reporter: it starts BEFORE the gadget bind so it survives a
    failed UDC bind, a missing ttyGS0 and a broken USB link)"
python3 "$NEWC" replace "$STAGE" opt/nuxel/nuxel-console \
    "$ROOT/build/out/s10plus/debug-candidates/A18/nuxel-console" "$STAGE.t" --mode=0100755
swap

echo "3. layout"
python3 "$NEWC" list "$STAGE" | grep -E "opt/nuxel/|^[0-9]+ +file.* init$" | head -20
echo "logical end: $(python3 "$NEWC" trailer "$STAGE")"
echo "cpio size  : $(wc -c <"$STAGE" | tr -d ' ')"
echo "cpio sha256: $(shasum -a 256 "$STAGE" | cut -d' ' -f1)"

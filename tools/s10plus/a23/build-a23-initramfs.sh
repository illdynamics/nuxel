#!/bin/sh
# A23 initramfs — A22's hardware-proven archive plus:
#   * /init                              <- boot/initramfs/init.sh (installs and enables the UI)
#   * opt/nuxel/nuxel-anim-player        <- A23 player (HARDWARE colour order: ABGR8888)
#   * opt/nuxel/nuxel-fb-phone           <- A23 first-light renderer (same colour fix)
#   * opt/nuxel/nuxel-ui                 <- the fbdev-native interactive phone UI
#   * opt/nuxel/nuxel-ui.rev             <- the UI build identity (install gate + evidence)
#   * opt/nuxel/nuxel-ui.service         <- systemd unit for the UI
#   * opt/nuxel/nuxel-ui-fallback.service<- systemd unit for the MP4 fallback screen
#
# A BOOT-only flash therefore carries the WHOLE user interface; the 4 GiB rootfs
# is not rewritten, and later iterations are deployed live over the CDC-ACM shell.
set -eu
ROOT=/Users/wicked/x/nuxel
CAND=${CAND:-A23}
BASE=${BASE:-$ROOT/build/out/s10plus/debug-candidates/A22/initramfs.cpio}
W=$ROOT/build/out/s10plus/debug-candidates/$CAND
NEWC=$ROOT/tools/s10plus/newc.py
PLAYER=$ROOT/build/out/s10plus/nuxel-anim-player
FBPHONE=$ROOT/build/out/s10plus/nuxel-fb-phone
UI=$ROOT/build/out/s10plus/nuxel-ui

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
    echo "2. $name (replace)"
    python3 "$NEWC" replace "$STAGE" "$name" "$src" "$STAGE.t" --mode=0100755
    swap
done

echo "3. insert the UI + its units"
python3 "$NEWC" insert "$STAGE" "$STAGE.t" --after opt/nuxel/nuxel-anim-player \
    --name opt/nuxel/nuxel-ui --file "$UI" --mode 0100755
swap
python3 "$NEWC" insert "$STAGE" "$STAGE.t" --after opt/nuxel/nuxel-ui \
    --name opt/nuxel/nuxel-ui.rev --file "$ROOT/tools/s10plus/a23/nuxel-ui.rev" --mode 0100644
swap
python3 "$NEWC" insert "$STAGE" "$STAGE.t" --after opt/nuxel/nuxel-ui.rev \
    --name opt/nuxel/nuxel-ui.service --file "$ROOT/tools/s10plus/a23/nuxel-ui.service" --mode 0100644
swap
python3 "$NEWC" insert "$STAGE" "$STAGE.t" --after opt/nuxel/nuxel-ui.service \
    --name opt/nuxel/nuxel-ui-fallback.service --file "$ROOT/tools/s10plus/a23/nuxel-ui-fallback.service" --mode 0100644
swap

echo "4. layout"
python3 "$NEWC" list "$STAGE" | grep -E "opt/nuxel/|^[0-9]+ +file.* init$" || true

echo "5. verify every member really is the intended file"
for pair in "init:$ROOT/boot/initramfs/init.sh" \
            "opt/nuxel/nuxel-anim-player:$PLAYER" \
            "opt/nuxel/nuxel-fb-phone:$FBPHONE" \
            "opt/nuxel/nuxel-ui:$UI" \
            "opt/nuxel/nuxel-ui.rev:$ROOT/tools/s10plus/a23/nuxel-ui.rev" \
            "opt/nuxel/nuxel-ui.service:$ROOT/tools/s10plus/a23/nuxel-ui.service"; do
    name=${pair%%:*}; src=${pair#*:}
    python3 "$NEWC" extract "$STAGE" "$name" "$W/verify.tmp"
    a=$(shasum -a 256 "$W/verify.tmp" | cut -d' ' -f1)
    b=$(shasum -a 256 "$src" | cut -d' ' -f1)
    if [ "$a" = "$b" ]; then echo "   OK   $name  $a";
    else echo "   FAIL $name differs ($a != $b)"; exit 1; fi
done
rm -f "$W/verify.tmp"
printf '   %-34s %s bytes  sha256 %s\n' "opt/nuxel/nuxel-ui" "$(wc -c <"$UI" | tr -d ' ')" "$(shasum -a 256 "$UI" | cut -d' ' -f1)"
echo "cpio size  : $(wc -c <"$STAGE" | tr -d ' ')"
echo "cpio sha256: $(shasum -a 256 "$STAGE" | cut -d' ' -f1)"
echo "trailer    : $(python3 "$NEWC" trailer "$STAGE")"
echo A23_INITRAMFS_BUILD_OK

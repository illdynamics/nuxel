#!/bin/sh
# A24 initramfs — A23's archive (which already carries the fbdev phone UI) plus the
# three things A23's hardware run proved are needed:
#
#   * opt/nuxel/nuxel-console      <- HUP-proof live console (shell supervisor: the
#                                     channel re-arms after a host disconnect; on A23 a
#                                     single disconnect killed it for the rest of the boot)
#   * opt/nuxel/nuxel-postboot.sh  <- post-handoff supervisor: writes
#                                     /var/lib/nuxel/bootreport.txt and starts the UI
#                                     directly, bypassing the stalled systemd graph
#   * opt/nuxel/nuxel-ui.service   <- no ordering dependencies / no ConditionPathExists
#                                     (A23: ConditionResult=no even though /dev/fb0 exists,
#                                     and the job blocked forever behind local-fs.target)
# plus the usual /init and the three display binaries.
set -eu
ROOT=/Users/wicked/x/nuxel
CAND=${CAND:-A24}
BASE=${BASE:-$ROOT/build/out/s10plus/debug-candidates/A23/initramfs.cpio}
W=$ROOT/build/out/s10plus/debug-candidates/$CAND
NEWC=$ROOT/tools/s10plus/newc.py
PLAYER=$ROOT/build/out/s10plus/nuxel-anim-player
FBPHONE=$ROOT/build/out/s10plus/nuxel-fb-phone
UI=$ROOT/build/out/s10plus/nuxel-ui
CONSOLE=$ROOT/build/out/s10plus/nuxel-console
POSTBOOT=$ROOT/tools/s10plus/a24/nuxel-postboot.sh
REV=$ROOT/tools/s10plus/a24/nuxel-ui.rev
UNIT=$ROOT/tools/s10plus/a24/nuxel-ui.service
UNITFB=$ROOT/tools/s10plus/a23/nuxel-ui-fallback.service

mkdir -p "$W"
STAGE=$W/initramfs.cpio
cp "$BASE" "$STAGE"
echo "base cpio : $BASE"
echo "base sha  : $(shasum -a 256 "$STAGE" | cut -d' ' -f1)  ($(wc -c <"$STAGE" | tr -d ' ') bytes)"
swap() { mv -f "$STAGE.t" "$STAGE"; }

echo "1. /init"
python3 "$NEWC" replace "$STAGE" init "$ROOT/boot/initramfs/init.sh" "$STAGE.t" --mode=0100755; swap

echo "2. replace (existing members)"
for pair in "$PLAYER:opt/nuxel/nuxel-anim-player" \
            "$FBPHONE:opt/nuxel/nuxel-fb-phone" \
            "$UI:opt/nuxel/nuxel-ui" \
            "$CONSOLE:opt/nuxel/nuxel-console" \
            "$REV:opt/nuxel/nuxel-ui.rev" \
            "$UNIT:opt/nuxel/nuxel-ui.service" \
            "$UNITFB:opt/nuxel/nuxel-ui-fallback.service"; do
    src=${pair%%:*}; name=${pair#*:}
    [ -f "$src" ] || { echo "MISSING $src" >&2; exit 1; }
    python3 "$NEWC" replace "$STAGE" "$name" "$src" "$STAGE.t" --mode=0100755; swap
done

echo "3. insert the post-handoff supervisor"
python3 "$NEWC" insert "$STAGE" "$STAGE.t" --after opt/nuxel/nuxel-console \
    --name opt/nuxel/nuxel-postboot.sh --file "$POSTBOOT" --mode 0100755; swap

echo "4. layout"
python3 "$NEWC" list "$STAGE" | grep -E "opt/nuxel/|^[0-9]+ +file.* init$" || true

echo "5. verify every member really is the intended file"
for pair in "init:$ROOT/boot/initramfs/init.sh" \
            "opt/nuxel/nuxel-anim-player:$PLAYER" \
            "opt/nuxel/nuxel-fb-phone:$FBPHONE" \
            "opt/nuxel/nuxel-ui:$UI" \
            "opt/nuxel/nuxel-console:$CONSOLE" \
            "opt/nuxel/nuxel-postboot.sh:$POSTBOOT" \
            "opt/nuxel/nuxel-ui.rev:$REV" \
            "opt/nuxel/nuxel-ui.service:$UNIT" \
            "opt/nuxel/nuxel-ui-fallback.service:$UNITFB"; do
    name=${pair%%:*}; src=${pair#*:}
    python3 "$NEWC" extract "$STAGE" "$name" "$W/verify.tmp"
    a=$(shasum -a 256 "$W/verify.tmp" | cut -d' ' -f1)
    b=$(shasum -a 256 "$src" | cut -d' ' -f1)
    if [ "$a" = "$b" ]; then echo "   OK   $name  $a"; else echo "   FAIL $name ($a != $b)"; exit 1; fi
done
rm -f "$W/verify.tmp"
echo "cpio size  : $(wc -c <"$STAGE" | tr -d ' ')"
echo "cpio sha256: $(shasum -a 256 "$STAGE" | cut -d' ' -f1)"
echo A24_INITRAMFS_BUILD_OK

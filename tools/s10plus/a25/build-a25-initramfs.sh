#!/bin/sh
# A25 initramfs — A24's archive plus the two fixes A24's hardware run proved necessary:
#   * the UI is now SINGLE-INSTANCE (a second renderer power-cycled the panel via
#     fb_release and left the operator with a dark screen), and
#   * the post-handoff supervisor is spawned by nuxel-console, which chroots into the new
#     root deliberately, instead of by /init's detached subshell (which died).
# (A24 already carries: HUP-proof console, UI unit with no ordering/conditions,
#  sysinit.target enable, /opt/nuxel/nuxel-postboot.sh.)
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
CAND=${CAND:-A25}
BASE=${BASE:-$ROOT/build/out/s10plus/debug-candidates/A24/initramfs.cpio}
W=$ROOT/build/out/s10plus/debug-candidates/$CAND
NEWC=$ROOT/tools/s10plus/newc.py
PLAYER=$ROOT/build/out/s10plus/nuxel-anim-player
FBPHONE=$ROOT/build/out/s10plus/nuxel-fb-phone
UI=$ROOT/build/out/s10plus/nuxel-ui
CONSOLE=$ROOT/build/out/s10plus/nuxel-console
POSTBOOT=$ROOT/tools/s10plus/a24/nuxel-postboot.sh
REV=$ROOT/tools/s10plus/a25/nuxel-ui.rev
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

echo "3. refresh the post-handoff supervisor (already present in the A24 base)"
python3 "$NEWC" replace "$STAGE" opt/nuxel/nuxel-postboot.sh "$POSTBOOT" "$STAGE.t" --mode=0100755; swap

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
echo A25_INITRAMFS_BUILD_OK

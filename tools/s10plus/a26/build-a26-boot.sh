#!/bin/sh
# ============================================================================
# build-a26-boot.sh — prepare the A26 BOOT candidate (NOT flashed by this script)
#
# Scope of A26's BOOT-side change (mission P0):
#   replace the obsolete two-second diagnostic splash painted by
#   nuxel_first_light -> /opt/nuxel/nuxel-fb-phone with **frame 0 of the original
#   animation**, so the first thing the panel shows IS the animation's opening
#   frame and the handoff to nuxel-anim-player is not a transition at all.
#
# This script assembles and STRUCTURALLY VERIFIES a versioned candidate.  It
# never touches a device.  Flashing is a separate, operator-gated step
# (BOOT-only, full readback), per the standing safety rules.
#
# ---------------------------------------------------------------------------
# INTEGRATION CONTRACT (what the next edit to nuxel-fb-phone.c must satisfy)
#
#  1. Read /opt/nuxel/nuxel-firstlight.rawspl (NUXSPL01, flags bit0 = 0, so no
#     DEFLATE decoder is needed in the freestanding binary).  Accept an
#     override --firstlight=<path>.  If it is missing or malformed, fall back to
#     the current diagnostic frame -- the A16 fallback is preserved.
#  2. Expand the 256-entry RGB565 palette to the panel's real channel order.
#     The DECON commit path hard-codes DECON_PIXEL_FORMAT_ABGR_8888 while the
#     driver declares red@16, so pack with R on bits 0..7 (A23).  Use the SAME
#     packing function the animation player already uses -- do not add a second
#     colour implementation.
#  3. Scale 1080x1920 -> the panel raster with **nearest-neighbour integer
#     spans**, NOT bilinear: nuxel-anim-player.c builds DX0/DX1/DY0/DY1
#     ("Per-source-pixel destination spans (nearest-neighbour, integer maths)")
#     and the early frame must land on exactly the same pixels as the player's
#     first commit, or the handoff is not seamless.
#  4. Write into EVERY buffer the DECON might be scanning (the A14 lesson:
#     yres_virtual is 2x yres).  Reuse paint_all_buffers()'s loop.
#  5. Keep the whole existing prelude: panel init, geometry discovery, mmap
#     bounds checks, FBIOBLANK/FBIOPUT_VSCREENINFO reassert, DECON commit, the
#     FB_NODE/FB_SYSFS diagnostics and every NUXEL_FB_* verdict.
#  6. Open /dev/fb0 exactly ONCE.  Closing a framebuffer fd runs decon_release,
#     which disables the panel regulator (A21/A24).  Nothing may open or close
#     /dev/fb0 a second time.
#  7. Never run a second framebuffer client; exactly one writer at a time.
# ============================================================================
set -eu
ROOT=/Users/wicked/x/nuxel
CAND=${CAND:-A26}
BASE=${BASE:-$ROOT/build/out/s10plus/debug-candidates/A25/initramfs.cpio}
W=$ROOT/build/out/s10plus/debug-candidates/$CAND
NEWC=$ROOT/tools/s10plus/newc.py
ANIM=$ROOT/build/out/s10plus/nuxel-animation.nux
SPL=$ROOT/build/out/s10plus/a26/nuxel-firstlight.rawspl

mkdir -p "$W"
echo "== A26 BOOT candidate =="
echo "base cpio : $BASE"

[ -f "$BASE" ] || { echo "MISSING base initramfs: $BASE" >&2; exit 1; }

# 1. the asset itself, regenerated from the ORIGINAL MP4-derived container and
#    re-verified (index plane + palette identical to NUXANM01 frame 0).
echo "-- step 1: first-light asset from the original animation"
python3 "$ROOT/tools/s10plus/a26/make-firstlight-asset.py" \
    --anim "$ANIM" \
    --out  "$ROOT/build/out/s10plus/a26/nuxel-firstlight.nuxspl" \
    --raw-out "$SPL" \
    --mp4  "$ROOT/assets/nuxel-boot-animation.mp4" \
    --report "$ROOT/build/out/s10plus/a26/nuxel-firstlight.report.json" | tail -12

# 2. stage the initramfs
STAGE=$W/initramfs.cpio
cp "$BASE" "$STAGE"
echo "-- step 2: staged $(wc -c <"$STAGE" | tr -d ' ') bytes"

add() { # add <host-file> <cpio-member>  (new member: insert before TRAILER!!!)
    echo "   add $2"
    python3 "$NEWC" insert "$STAGE" "$STAGE.t" --after opt/nuxel/nuxel-anim-player \
        --name "$2" --mode 0100644 --type file --file "$1" && mv -f "$STAGE.t" "$STAGE"
}
add "$SPL" opt/nuxel/nuxel-firstlight.rawspl

# 3. the two members the P0 fix changes.  Gated: if the source has not been
#    edited yet, STOP rather than ship a candidate that claims a fix it does
#    not contain.
echo "-- step 3: gate on the fb-phone change"
if ! grep -q -- "--firstlight" "$ROOT/tools/s10plus/nuxel-fb-phone.c" 2>/dev/null; then
    echo "   [GATE] tools/s10plus/nuxel-fb-phone.c does not implement --firstlight yet."
    echo "   [GATE] The asset is staged and verified, but the blit is not in place."
    echo "   [GATE] Refusing to build a candidate that would still paint the old splash."
    echo "   [GATE] See the integration contract in this script's header."
    ls -l "$SPL" "$ROOT/build/out/s10plus/a26/nuxel-firstlight.nuxspl"
    echo "A26_ASSET_READY_CANDIDATE_WITHHELD"
    exit 0
fi
python3 "$NEWC" replace "$STAGE" init "$ROOT/boot/initramfs/init.sh" "$STAGE.t" --mode=0100755 && mv -f "$STAGE.t" "$STAGE"
add "$ROOT/build/out/s10plus/nuxel-fb-phone" opt/nuxel/nuxel-fb-phone

# 4. verify every member by SHA-256
echo "-- step 4: member verification"
for pair in "opt/nuxel/nuxel-firstlight.rawspl:$SPL" \
            "opt/nuxel/nuxel-fb-phone:$ROOT/build/out/s10plus/nuxel-fb-phone"; do
    name=${pair%%:*}; src=${pair#*:}
    python3 "$NEWC" extract "$STAGE" "$name" "$W/verify.tmp"
    a=$(shasum -a 256 "$W/verify.tmp" | cut -d' ' -f1)
    b=$(shasum -a 256 "$src" | cut -d' ' -f1)
    if [ "$a" = "$b" ]; then echo "   OK   $name $a"; else echo "   FAIL $name"; exit 1; fi
done
rm -f "$W/verify.tmp"

{
  echo "candidate=$CAND"
  echo "purpose=seamless first light: animation frame 0 replaces the obsolete splash"
  echo "base=$BASE"
  echo "firstlight_asset=$SPL"
  echo "firstlight_sha256=$(shasum -a 256 "$SPL" | cut -d' ' -f1)"
  echo "initramfs_sha256=$(shasum -a 256 "$STAGE" | cut -d' ' -f1)"
  echo "initramfs_bytes=$(wc -c <"$STAGE" | tr -d ' ')"
  echo "flashed=false"
} > "$W/A26-CANDIDATE.txt"
cat "$W/A26-CANDIDATE.txt"
echo "A26_BOOT_CANDIDATE_PREPARED (not flashed)"

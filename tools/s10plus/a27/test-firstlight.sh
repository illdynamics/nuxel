#!/bin/sh
# ============================================================================
# test-firstlight.sh — the A27 release gate for the seamless first light.
#
# Proves, off-device, that the frame nuxel-fb-phone paints at first light is the
# animation player's own frame 0:
#
#   1. the C renderer's buffer is byte-identical to ref-firstlight.py's, which is
#      an independent implementation of nuxel-anim-player.c's maths;
#   2. the asset's index plane and palette are byte-identical to NUXANM01 frame 0
#      (make-firstlight-asset.py re-runs this from the original container);
#   3. the reconstructed frame agrees with an ffmpeg decode of the ORIGINAL MP4's
#      frame 0 (mean absolute error / channel), i.e. the artwork is the original
#      one and the palette byte order is the correct one;
#   4. byte-swapping the palette (the "incorrect pixel order" failure mode) makes
#      that agreement collapse -- so an R/B-or-endian swap cannot pass silently;
#   5. every malformed asset is REJECTED BY NAME: short header, bad magic,
#      reserved set, unsupported flags (compressed), bad palette count, bad
#      dimensions, size overflow, truncated plane, trailing bytes.
#
# Usage: sh tools/s10plus/a27/test-firstlight.sh [asset.rawspl]
# Exit: 0 = all checks passed, 1 = a check failed, 2 = missing input.
# ============================================================================
set -eu
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
A27="$ROOT/tools/s10plus/a27"
ASSET=${1:-$ROOT/build/out/s10plus/a26/nuxel-firstlight.rawspl}
WORK="$ROOT/build/out/s10plus/a27/tests"
CC=${CC:-cc}
mkdir -p "$WORK"
[ -s "$ASSET" ] || { echo "MISSING asset: $ASSET" >&2; exit 2; }

echo "== 0. build the host harness from the SAME source the handset runs =="
"$CC" -O1 -w -o "$WORK/test-firstlight" "$A27/test-firstlight.c"
echo "   ok  $WORK/test-firstlight"

echo "== 1. C renderer vs independent python reference =="
"$WORK/test-firstlight" "$ASSET" "$WORK/c.raw" >"$WORK/c.txt"
python3 "$A27/ref-firstlight.py" "$ASSET" "$WORK/py.raw" >"$WORK/py.txt"
grep '^RENDER_RC=0$' "$WORK/c.txt" >/dev/null || { echo "   FAIL render"; exit 1; }
if cmp -s "$WORK/c.raw" "$WORK/py.raw"; then
    echo "   PASS byte-identical ($(shasum -a 256 "$WORK/c.raw" | cut -c1-16)…, $(wc -c <"$WORK/c.raw" | tr -d ' ') bytes)"
else
    echo "   FAIL C and python renders differ"; exit 1
fi

echo "== 2. asset == NUXANM01 frame 0 (from the ORIGINAL MP4-derived container) =="
python3 "$ROOT/tools/s10plus/a26/make-firstlight-asset.py" \
    --anim "$ROOT/build/out/s10plus/nuxel-animation.nux" \
    --out "$WORK/regen.nuxspl" --raw-out "$WORK/regen.rawspl" | tail -2
cmp -s "$ASSET" "$WORK/regen.rawspl" && echo "   PASS asset is reproducible byte-for-byte" \
    || { echo "   FAIL asset is not reproducible"; exit 1; }

echo "== 3+4. artwork + palette byte order vs an ffmpeg decode of the MP4 frame 0 =="
python3 - "$ASSET" "$ROOT/assets/nuxel-boot-animation.mp4" "$WORK" <<'PY'
import struct, subprocess, sys, os
asset, mp4, work = sys.argv[1], sys.argv[2], sys.argv[3]
d = open(asset, "rb").read()
w, h, paln, flags, blobsz, _ = struct.unpack_from("<IIIIII", d, 8)
pal = list(struct.unpack_from("<%dH" % paln, d, 32))
idx = d[32 + paln * 2:]
def frame0(w, h):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vf",
                          "select=eq(n\\,0),scale=%d:%d:flags=neighbor" % (w, h),
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return out
true = frame0(w, h)
if len(true) != w * h * 3:
    sys.exit("ffmpeg gave %d bytes" % len(true))
def expand(p):
    r = ((p >> 11) & 31) * 255 // 31
    g = ((p >> 5) & 63) * 255 // 63
    b = (p & 31) * 255 // 31
    return (r, g, b)
def mae(palette):
    exp = [expand(p) for p in palette]
    tot = n = 0
    for i in range(0, len(idx), 397):
        r, g, b = exp[idx[i]]
        tot += abs(r - true[i * 3]) + abs(g - true[i * 3 + 1]) + abs(b - true[i * 3 + 2])
        n += 3
    return tot / n
ok = mae(pal)
swapped = []
for p in pal:
    swapped.append(((p & 0xFF) << 8) | (p >> 8))       # byte order reversed
bad = mae(swapped)
print("   as stored   MAE vs MP4 frame 0 = %.3f / 255" % ok)
print("   byte-swapped MAE vs MP4 frame 0 = %.3f / 255" % bad)
assert ok < 12.0, "stored palette does not match the original artwork (MAE %.2f)" % ok
assert bad > ok * 1.5, "an R/B or endian swap would pass unnoticed (MAE %.2f vs %.2f)" % (bad, ok)
print("   PASS palette byte order is the original's, and a swap is detectable")
PY

echo "== 5. malformed assets are rejected BY NAME =="
python3 - "$ASSET" "$WORK" "$A27" <<'PY'
import os, subprocess, sys
asset, work, a27 = sys.argv[1], sys.argv[2], sys.argv[3]
raw = open(asset, "rb").read()
harness = os.path.join(work, "test-firstlight")
def expect(name, blob, want):
    p = os.path.join(work, "bad-" + name + ".rawspl")
    open(p, "wb").write(blob)
    r = subprocess.run([harness, p, os.path.join(work, "out.tmp")],
                       capture_output=True, text=True)
    got = ""
    for line in r.stdout.splitlines():
        if line.startswith("PARSE_NAME="):
            got = line.split("=", 1)[1]
    ok = (r.returncode != 0 and got == want)
    print("   %s %-22s exit=%d name=%s (want %s)" %
          ("PASS" if ok else "FAIL", name, r.returncode, got or "-", want))
    return ok
allok = True
allok &= expect("short_header", raw[:24], "SHORT_HEADER")
allok &= expect("bad_magic", b"NUXSPLXX" + raw[8:], "BAD_MAGIC")
allok &= expect("reserved", raw[:28] + b"\x01\x00\x00\x00" + raw[32:], "RESERVED_NOT_ZERO")
allok &= expect("flags_deflate", raw[:20] + b"\x01\x00\x00\x00" + raw[24:], "UNSUPPORTED_FLAGS")
allok &= expect("palette_count", raw[:16] + b"\x01\x00\x00\x00" + raw[20:], "BAD_PALETTE")
def hdr(w, h, paln, flags, blob):
    return raw[:8] + (w.to_bytes(4, "little") + h.to_bytes(4, "little") +
                      paln.to_bytes(4, "little") + flags.to_bytes(4, "little") +
                      blob.to_bytes(4, "little") + b"\x00" * 4) + raw[32:]
allok &= expect("bad_dimensions", hdr(0, 1920, 256, 0, 0), "BAD_DIMENSIONS")
allok &= expect("size_overflow", hdr(8000, 8001, 256, 0, 64008000), "BUFFER_SIZE_OVERFLOW")
allok &= expect("absurd_dimensions", hdr(9000, 9000, 256, 0, 81000000), "BAD_DIMENSIONS")
allok &= expect("truncated_plane", raw[:-1000], "TRUNCATED_PIXEL_PLANE")
allok &= expect("trailing_bytes", raw + b"\x00" * 8, "TRAILING_BYTES")
allok &= expect("flat_palette", raw[:32] + b"\x00" * 512 + raw[544:], "BAD_PALETTE")
sys.exit(0 if allok else 1)
PY

echo "== 6. the ARM64 binary really carries the renderer =="
BIN="$ROOT/build/out/s10plus/nuxel-fb-phone"
if [ -s "$BIN" ]; then
    if strings -a "$BIN" | grep -q "NUXEL_FIRSTLIGHT_FRAME0_PAINTED"; then
        echo "   PASS $BIN contains the NUXSPL01 renderer"
    else
        echo "   FAIL $BIN has no first-light renderer (stale binary!)"; exit 1
    fi
    file -b "$BIN" | grep -q aarch64 && echo "   PASS ELF aarch64" || { echo "   FAIL not aarch64"; exit 1; }
else
    echo "   (release binary not built yet: $BIN)"
fi
echo "A27_FIRSTLIGHT_TESTS_OK"

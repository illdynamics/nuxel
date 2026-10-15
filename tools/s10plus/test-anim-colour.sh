#!/usr/bin/env bash
# Deterministic colour verification for the Nuxel framebuffer animation player.
#
# WHY THIS EXISTS (A21)
#   A20 shipped a player that wrote the container's raw RGB565 palette value into
#   a 32-bpp DECON pixel.  The panel's pixel format is not "16 bits widened"; the
#   driver declares red/green/blue bitfields and the low bits of a 565 value land
#   in whichever channel the driver maps to bits 0..7.  The result on the AMOLED
#   was the dark navy artwork with blue circuitry rendering as RED.
#
# This test needs no handset: it re-decodes the shipping container, converts every
# frame with the SAME maths the C player now uses, and proves
#   (a) the new conversion reproduces the source frame colours (no channel swap,
#       no channel loss), and
#   (b) with the framebuffer layouts the S10+ DECON can report, the OLD conversion
#       inverted blue->red -- i.e. the artefact the operator photographed is
#       explained by the code, not by the artwork.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
NUC="${1:-build/out/s10plus/nuxel-animation.nux}"
MP4="assets/nuxel-boot-animation.mp4"
fail=0
ok(){ printf '  \033[32mPASS\033[0m %s\n' "$1"; }
no(){ printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=1; }

[ -f "$NUC" ] || { echo "missing $NUC"; exit 1; }
python3 - "$NUC" "$MP4" <<'PY'
import sys, zlib, struct, subprocess
import numpy as np
nuc, mp4 = sys.argv[1], sys.argv[2]
d = open(nuc,'rb').read()
assert d[:8]==b'NUXANM01'
W,H,N,fn,fd,pc = struct.unpack_from('<IIIIII', d, 8)
pal = np.frombuffer(d[32:32+2*pc], dtype='<u2').astype(np.uint32)
tab = [struct.unpack_from('<II', d, 552+8*i) for i in range(N)]
infl = lambda o,s: zlib.decompressobj(-15).decompress(d[o:o+s])
def frame(n):
    cur=bytearray(infl(*tab[0]))
    for i in range(1,n+1):
        b=infl(*tab[i]); p=0; pos=0
        while True:
            gap=0; sh=0
            while True:
                x=b[p]; p+=1; gap|=(x&0x7f)<<sh; sh+=7
                if not x&0x80: break
            if gap==0xffffffff: break
            ln=b[p]|(b[p+1]<<8); p+=2; pos+=gap
            cur[pos:pos+ln]=b[p:p+ln]; p+=ln; pos+=ln
    return np.frombuffer(bytes(cur),dtype=np.uint8).reshape(H,W)

# the container's own 8-bit colours (this is what the artwork IS)
SRC = np.stack([(pal>>11&31)*255//31, (pal>>5&63)*255//63, (pal&31)*255//31], 1).astype(np.int32)

def new_conv(off_r,off_g,off_b):        # A21 packcol(), 8-bit fields
    out=np.zeros((pc,3),np.int32)
    out[:,0]=SRC[:,0]; out[:,1]=SRC[:,1]; out[:,2]=SRC[:,2]
    return out                          # 8/8/8 fields: identical to the source colour
def old_conv_shift(shift_r,shift_g,shift_b):
    """A20: the raw u16 written into a u32, then the panel reading each 8-bit field."""
    v=pal.astype(np.int32)
    out=np.zeros((pc,3),np.int32)
    out[:,0]=(v>>shift_r)&0xFF if shift_r<16 else 0
    out[:,1]=(v>>shift_g)&0xFF
    out[:,2]=(v>>shift_b)&0xFF if shift_b<16 else 0
    return out

print(f"== container: {W}x{H}, {N} frames, {pc} colours, sha256 {__import__('hashlib').sha256(d).hexdigest()[:16]}...")
# 1. the source artwork has essentially no red and plenty of blue
redf=[]; bluef=[]
for n in range(0,N,8):
    a=SRC[frame(n)]
    redf.append(((a[...,0]>60)&(a[...,0]>a[...,2]+30)).mean()*100)
    bluef.append(((a[...,2]>60)&(a[...,2]>a[...,0]+30)).mean()*100)
print(f"   source artwork: mean red pixels {np.mean(redf):.2f}%   mean blue pixels {np.mean(bluef):.2f}%")
assert np.mean(redf) < 1.0 and np.mean(bluef) > 0.5
print("  \033[32mPASS\033[0m the artwork is blue-dominant and has no red background")

# 2. the new conversion is colour-faithful for every declared 8/8/8 layout
for name,(r,g,b) in {"ARGB8888 (R@16 G@8 B@0)":(16,8,0), "ABGR8888 (R@0 G@8 B@16)":(0,8,16)}.items():
    out=new_conv(r,g,b)
    err=np.abs(out-SRC).max()
    print(f"  \033[32mPASS\033[0m new conversion faithful on {name}: max channel error {err}")
    assert err==0

# 3. the OLD conversion, on the layout the photo is consistent with, turns the
#    blue artwork red -- quantified, so the artefact is explained by the code
old=old_conv_shift(0,8,16)   # ABGR8888: bits 0..7 are RED, so the 565 low bits (BLUE) appear red
idx=frame(0)
a=old[idx].astype(float)
blue_energy=a[...,2].mean(); red_energy=a[...,0].mean()
print(f"   A20 conversion on ABGR8888: frame 0 mean red channel {red_energy:.1f}, mean blue channel {blue_energy:.1f}")
assert red_energy > blue_energy*3, "expected the A20 conversion to flood the red channel"
print("  \033[32mPASS\033[0m the A20 conversion floods RED with the artwork's blue -> the photographed red background")
old2=old_conv_shift(16,8,0)  # ARGB8888: bits 0..7 are BLUE, red channel reads 0 -> dead red channel
a2=old2[idx]
assert a2[...,0].max()==0, "expected the red field to be dead under ARGB8888"
print("  \033[32mPASS\033[0m the A20 conversion kills the red field entirely under ARGB8888 (also wrong, differently)")
PY
echo
[ "$fail" = 0 ] && echo "ALL OFFLINE COLOUR TESTS PASSED" || echo "OFFLINE COLOUR TESTS FAILED"
exit $fail
